import { createServer } from "node:http";
import { randomUUID } from "node:crypto";
import { WebSocketServer } from "ws";

const PORT = Number(process.argv[2] || 8000);

const socketsByThread = new Map();
const timersByThread = new Map();

const RESULT_MARKDOWN = `## 2026 跨境电商 AI 客服趋势研判

### 核心结论

1. **多语种实时翻译成为出海客服标配** — 头部平台已把小语种覆盖从"加分项"变成"准入项"，东南亚、拉美市场诉求最强烈。
2. **从"答得准"升级到"办得成"** — 客服机器人不再止步于问答，开始直连订单、物流系统执行改单、催办、退款等闭环操作。
3. **人工客服转向"AI 副驾驶"模式** — 坐席侧实时话术建议、摘要自动生成渗透率快速提升，新人培训周期显著缩短。
4. **合规与数据主权约束加深** — 欧盟 AI Act 与各国数据出境规则，推动客服数据本地化部署需求上升。
5. **效果度量从"解决率"转向"节省成本 + NPS 双指标"** — 企业采购决策更关注可量化 ROI。

### 关键变化速览

| 趋势 | 业务影响 | 关注厂商 |
| --- | --- | --- |
| 多语种实时翻译 | 小语种市场服务成本下降约 40% | Zendesk、Intercom |
| 工作流闭环执行 | 首次解决率提升 15-25% | Ada、Forethought |
| 坐席 AI 副驾驶 | 新人上手周期缩短一半 | Gong、Salesforce |
| 数据本地化部署 | 欧盟/中东项目必选项 | 本地化私有方案 |

### 信息来源

- Freshworks《2026 客服自动化趋势报告》
- Gartner《Customer Service Hype Cycle, 2026》
- Zendesk CX Trends 2026（亚太章节）
- 行业访谈：3 家年 GMV 10 亿+ 跨境卖家客服负责人

---
*由深度研搜多智能体自动汇编，共检索 14 个信源，置信度：高*`;

function now() {
  return new Date().toISOString();
}

function emit(threadId, event, message, data = {}) {
  const payload = JSON.stringify({
    type: "monitor_event",
    event,
    message,
    data,
    timestamp: now()
  });
  const sockets = socketsByThread.get(threadId);
  if (!sockets) {
    return;
  }
  for (const socket of sockets) {
    if (socket.readyState === socket.OPEN) {
      socket.send(payload);
    }
  }
}

function clearThreadTimers(threadId) {
  const timers = timersByThread.get(threadId);
  if (timers) {
    for (const timer of timers) {
      clearTimeout(timer);
    }
    timersByThread.delete(threadId);
  }
}

function schedule(threadId, delayMs, fn) {
  let timers = timersByThread.get(threadId);
  if (!timers) {
    timers = [];
    timersByThread.set(threadId, timers);
  }
  timers.push(setTimeout(fn, delayMs));
}

function runTaskScript(threadId, query) {
  clearThreadTimers(threadId);

  const slow = query.includes("慢放");
  const fail = query.includes("异常") || query.includes("报错");
  const factor = slow ? 10 : 1;
  const at = (baseMs) => baseMs * factor;

  const sessionPath = `/sessions/${threadId}`;

  schedule(threadId, at(150), () => {
    emit(threadId, "session_created", "会话已创建，工作目录已就绪", {
      path: sessionPath
    });
  });

  schedule(threadId, at(500), () => {
    emit(threadId, "assistant_call", "主智能体正在拆解任务并规划检索路径", {
      plan: ["联网检索", "交叉验证", "汇编结论"]
    });
  });

  schedule(threadId, at(1100), () => {
    if (fail) {
      emit(threadId, "error", "网络搜索工具连接超时，任务已中断", {
        tool: "tavily_search",
        code: "TOOL_TIMEOUT"
      });
      clearThreadTimers(threadId);
      return;
    }
    emit(threadId, "tool_start", "调用网络搜索工具检索信源", {
      tool: "tavily_search",
      query: query.slice(0, 60)
    });
  });

  schedule(threadId, at(2000), () => {
    emit(threadId, "tool_start", "二次检索补充交叉验证信源", {
      tool: "tavily_search",
      round: 2
    });
  });

  schedule(threadId, at(2800), () => {
    emit(threadId, "assistant_call", "正在汇总多源信息并生成结构化结论", {
      sources: 14
    });
  });

  schedule(threadId, at(3400), () => {
    emit(threadId, "assistant_call", "整理引用来源与置信度标注", {
      sources: 14
    });
  });

  schedule(threadId, at(4000), () => {
    emit(threadId, "task_result", "研搜完成，已生成结论", {
      result: RESULT_MARKDOWN
    });
    clearThreadTimers(threadId);
  });
}

function sendJson(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function extractFilenames(body) {
  const matches = body.toString("latin1").matchAll(/filename="([^"]+)"/g);
  const names = Array.from(matches, (match) => match[1]).filter(Boolean);
  return names.length > 0 ? names : ["uploaded-file.txt"];
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (req.method === "OPTIONS") {
    sendJson(res, 204, {});
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/task") {
    const body = await readBody(req);
    let query = "";
    let threadId = randomUUID();
    try {
      const parsed = JSON.parse(body.toString("utf8"));
      query = typeof parsed.query === "string" ? parsed.query : "";
      if (typeof parsed.thread_id === "string" && parsed.thread_id) {
        threadId = parsed.thread_id;
      }
    } catch {
      sendJson(res, 400, { code: "BAD_REQUEST", message: "请求体不是合法 JSON" });
      return;
    }
    runTaskScript(threadId, query);
    sendJson(res, 200, { status: "started", thread_id: threadId });
    return;
  }

  const cancelMatch = url.pathname.match(/^\/api\/task\/([^/]+)\/cancel$/);
  if (req.method === "POST" && cancelMatch) {
    const threadId = decodeURIComponent(cancelMatch[1]);
    clearThreadTimers(threadId);
    emit(threadId, "task_cancelled", "任务已取消", {});
    sendJson(res, 200, { status: "cancelled", thread_id: threadId, message: "任务已取消" });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/upload") {
    const body = await readBody(req);
    const files = extractFilenames(body);
    sendJson(res, 200, { status: "uploaded", files });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/files") {
    const path = url.searchParams.get("path") || "";
    const base = path || "/sessions/unknown";
    sendJson(res, 200, {
      files: [
        {
          name: "AI客服趋势研判报告.md",
          type: "file",
          path: `${base}/AI客服趋势研判报告.md`,
          size: 18432,
          mtime: Date.now()
        },
        {
          name: "关键变化速览.pdf",
          type: "file",
          path: `${base}/关键变化速览.pdf`,
          size: 512000,
          mtime: Date.now()
        }
      ]
    });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/download") {
    res.writeHead(200, {
      "Content-Type": "text/markdown; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Content-Disposition": 'attachment; filename="report.md"'
    });
    res.end(RESULT_MARKDOWN);
    return;
  }

  sendJson(res, 404, { code: "NOT_FOUND", message: `未实现的接口: ${url.pathname}` });
});

const wss = new WebSocketServer({ noServer: true });

server.on("upgrade", (req, socket, head) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const match = url.pathname.match(/^\/ws\/([^/]+)$/);
  if (!match) {
    socket.destroy();
    return;
  }
  const threadId = decodeURIComponent(match[1]);
  wss.handleUpgrade(req, socket, head, (ws) => {
    let sockets = socketsByThread.get(threadId);
    if (!sockets) {
      sockets = new Set();
      socketsByThread.set(threadId, sockets);
    }
    sockets.add(ws);

    ws.on("message", (raw) => {
      if (raw.toString() === "ping") {
        ws.send(JSON.stringify({ type: "pong", message: "pong" }));
      }
    });

    ws.on("close", () => {
      sockets.delete(ws);
      if (sockets.size === 0) {
        socketsByThread.delete(threadId);
      }
    });
  });
});

server.listen(PORT, () => {
  console.log(`[mock] deepsearch mock server on http://localhost:${PORT}`);
  console.log(`[mock] ws endpoint: ws://localhost:${PORT}/ws/{threadId}`);
  console.log(`[mock] 剧本: 含「慢放」延时×10；含「异常/报错」触发错误态`);
});
