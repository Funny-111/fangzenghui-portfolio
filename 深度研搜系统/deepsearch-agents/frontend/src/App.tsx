import { PlusOutlined } from "@ant-design/icons";
import { Alert, App as AntApp, Button } from "antd";
import { useEffect, useRef, useState } from "react";
import { ChatComposer } from "./components/ChatComposer";
import { ConversationThread } from "./components/ConversationThread";
import type { ChatTurn } from "./components/ConversationThread";
import { useDeepAgentSession } from "./hooks/useDeepAgentSession";
import type { ConnectionState, UploadedItem } from "./types";

const HISTORY_GROUPS = [
  {
    label: "今天",
    items: [
      {
        title: "跨境电商 AI 客服趋势研判",
        prompt:
          "请使用网络搜索工具，检索 2026 年跨境电商 AI 客服趋势，列出 5 条关键变化，并附上来源链接。"
      },
      {
        title: "药品库存异常排查",
        prompt:
          "请使用数据库查询工具，查询库存大于 100 的药品，按库存量升序列出药品名称、批次号、仓库位置和过期日期。"
      }
    ]
  },
  {
    label: "过去 7 天",
    items: [
      {
        title: "内部白皮书品类策略问答",
        prompt:
          "请使用 RAGFlow 助手，查询公司内部白皮书中关于品类策略的内容，并整理成三条可执行建议。"
      },
      {
        title: "竞品定价策略对比",
        prompt:
          "请使用网络搜索工具，对比三家头部竞品近半年的定价策略变化，输出差异点和可借鉴之处。"
      },
      {
        title: "周度研报速览与要点提炼",
        prompt:
          "请使用网络搜索工具，汇总本周行业研报核心观点，提炼成五条要点并标注信息来源。"
      }
    ]
  }
];

function connectionLabel(state: ConnectionState): string {
  const labels: Record<ConnectionState, string> = {
    connecting: "连接中",
    connected: "已连接",
    reconnecting: "重连中",
    closed: "未连接"
  };
  return labels[state];
}

function createTurn(content: string): ChatTurn {
  return {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
    content,
    events: [],
    files: [],
    isRunning: true,
    result: "",
    timestamp: new Date().toISOString()
  };
}

export default function App() {
  const { message } = AntApp.useApp();
  const [query, setQuery] = useState("");
  const [stagedItems, setStagedItems] = useState<UploadedItem[]>([]);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const streamRef = useRef<HTMLElement | null>(null);
  const session = useDeepAgentSession();

  useEffect(() => {
    setTurns((previous) => {
      if (previous.length === 0) {
        return previous;
      }

      const latestTurn = previous[previous.length - 1];
      const nextLatestTurn = {
        ...latestTurn,
        events: session.events,
        files: session.files,
        isRunning: session.isRunning,
        result: session.result
      };

      return [...previous.slice(0, -1), nextLatestTurn];
    });
  }, [session.events, session.files, session.isRunning, session.result]);

  useEffect(() => {
    const streamNode = streamRef.current;
    if (!streamNode) {
      return;
    }

    window.requestAnimationFrame(() => {
      streamNode.scrollTo({
        top: streamNode.scrollHeight,
        behavior: "smooth"
      });
    });
  }, [turns]);

  async function handleSubmit() {
    const cleanQuery = query.trim();
    if (!cleanQuery) {
      message.warning("请输入研搜任务");
      return;
    }

    const nextTurn = createTurn(cleanQuery);
    setTurns((previous) => [...previous, nextTurn]);
    setQuery("");

    try {
      await session.submitTask(cleanQuery);
      message.success("任务已启动，执行过程会显示在对话中");
    } catch (error) {
      setTurns((previous) =>
        previous.map((turn) =>
          turn.id === nextTurn.id
            ? {
                ...turn,
                isRunning: false,
                result: error instanceof Error ? error.message : "任务启动失败"
              }
            : turn
        )
      );
      message.error(error instanceof Error ? error.message : "任务启动失败");
    }
  }

  async function handleCancel() {
    try {
      const response = await session.cancelCurrentTask();
      message.info(response.status === "cancelling" ? "取消请求已发送，正在等待当前调用结束" : "任务已取消");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "取消任务失败");
    }
  }

  async function handleUpload(items: UploadedItem[]) {
    try {
      const response = await session.uploadFiles(items);
      setStagedItems([]);
      message.success(`已上传 ${response.files.length} 个文件`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "上传失败");
    }
  }

  function handleNewSession() {
    session.resetSession();
    setTurns([]);
    setQuery("");
    setStagedItems([]);
  }

  const online = session.connectionState === "connected";

  return (
    <div className="chat-app-shell min-h-dvh">
      <aside className="chat-sidebar" aria-label="主导航">
        <div className="sidebar-brand">
          <span className="brand-mark" aria-hidden>
            研
          </span>
          <span className="brand-name">深度研搜</span>
        </div>

        {HISTORY_GROUPS.map((group) => (
          <div className="sidebar-section" key={group.label}>
            <span className="sidebar-label">{group.label}</span>
            <div className="history-list">
              {group.items.map((item) => (
                <button
                  className="history-item"
                  key={item.title}
                  onClick={() => setQuery(item.prompt)}
                  title={item.title}
                  type="button"
                >
                  {item.title}
                </button>
              ))}
            </div>
          </div>
        ))}

        <div className="sidebar-footer">
          <span
            className={`status-dot ${online ? "status-dot--online" : ""}`}
            aria-hidden
          />
          <span>{connectionLabel(session.connectionState)}</span>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-topbar">
          <div className="topbar-actions">
            <span
              className={`run-indicator ${session.isRunning ? "run-indicator--live" : ""}`}
            >
              <span className="run-dot" aria-hidden />
              研搜中
            </span>
            <Button
              className="new-chat-button"
              onClick={handleNewSession}
              icon={<PlusOutlined />}
            >
              <span>新建研搜</span>
            </Button>
          </div>
        </header>

        {session.lastError ? (
          <Alert
            className="chat-alert"
            message={session.lastError}
            showIcon
            type="error"
          />
        ) : null}

        <section className="chat-stream-panel" ref={streamRef}>
          <ConversationThread
            onUseExample={setQuery}
            turns={turns}
          />
        </section>

        <ChatComposer
          isCancelling={session.isCancelling}
          isRunning={session.isRunning}
          isUploading={session.isUploading}
          onCancel={handleCancel}
          onQueryChange={setQuery}
          onStagedItemsChange={setStagedItems}
          onSubmit={handleSubmit}
          onUpload={handleUpload}
          query={query}
          stagedItems={stagedItems}
          uploadedItems={session.uploadedItems}
        />
      </main>
    </div>
  );
}
