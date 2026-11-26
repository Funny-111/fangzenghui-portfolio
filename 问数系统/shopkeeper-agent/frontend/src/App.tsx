/**
 * 前端应用主组件
 * 负责聊天会话状态、SSE 事件消费、会话持久化与整体页面布局
 */
import { useEffect, useRef, useState } from "react";
import { Composer } from "./components/Composer";
import { MessageBubble } from "./components/MessageBubble";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { WelcomeHero } from "./components/WelcomeHero";
import { streamQuery } from "./lib/agentApi";
import { summarizeResult } from "./lib/format";
import { ALL_QUESTIONS } from "./lib/recommend";
import {
  loadStore,
  saveStore,
  type SessionMeta,
  type StoreShape,
  type StoredSession,
} from "./lib/storage";
import type { AgentEvent, ChatMessage, StepState } from "./types/agent";

function makeId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertStep(steps: StepState[] = [], event: Extract<AgentEvent, { type: "progress" }>) {
  const next = steps.filter((item) => item.step !== event.step);
  next.push({
    step: event.step,
    status: event.status,
    updatedAt: Date.now(),
  });
  return next;
}

/** 会话标题：首条用户问题截断 20 字，无则「新会话」 */
function sessionTitleOf(messages: ChatMessage[]): string {
  const query = messages.find((message) => message.role === "user")?.content;
  if (!query) return "新会话";
  return query.length > 20 ? `${query.slice(0, 20)}…` : query;
}

function toMetas(store: StoreShape): SessionMeta[] {
  return [...store.sessions]
    .sort((a, b) => b.meta.updatedAt - a.meta.updatedAt)
    .map((item) => ({
      id: item.meta.id,
      title: item.meta.title,
      updatedAt: item.meta.updatedAt,
    }));
}

export default function App() {
  /** 持久化数据源（ref：不参与渲染，读写都同步进 localStorage） */
  const storeRef = useRef<StoreShape | null>(null);
  if (storeRef.current === null) storeRef.current = loadStore();

  const [activeId, setActiveId] = useState<string>(() => {
    const store = storeRef.current as StoreShape;
    const valid = store.activeId && store.sessions.some((item) => item.meta.id === store.activeId);
    return valid ? (store.activeId as string) : makeId();
  });
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const store = storeRef.current as StoreShape;
    return store.sessions.find((item) => item.meta.id === store.activeId)?.messages ?? [];
  });
  /** 简易模式横幅（PRD 八.3）：随会话持久化 */
  const [degraded, setDegraded] = useState<boolean>(() => {
    const store = storeRef.current as StoreShape;
    return store.sessions.find((item) => item.meta.id === store.activeId)?.meta.degraded ?? false;
  });
  const [metas, setMetas] = useState<SessionMeta[]>(() => toMetas(storeRef.current as StoreShape));
  const [draft, setDraft] = useState("");
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  const controllerRef = useRef<AbortController | null>(null);
  /** 最新 UI 状态镜像：持久化回调读它，避免闭包拿到过期值 */
  const uiRef = useRef({ messages, degraded });
  uiRef.current = { messages, degraded };
  const persistTimerRef = useRef<number | null>(null);

  const isStreaming = Boolean(activeController);
  const canSubmit = draft.trim().length > 0 && !isStreaming;
  const sessionTitle = sessionTitleOf(messages);

  /** 把当前会话 UI 状态写回 store（空会话不落盘） */
  const syncActiveIntoStore = () => {
    const store = storeRef.current as StoreShape;
    const id = activeIdRef.current;
    const { messages: current, degraded: currentDegraded } = uiRef.current;
    const index = store.sessions.findIndex((item) => item.meta.id === id);
    if (current.length === 0) {
      if (index >= 0) store.sessions.splice(index, 1);
      return;
    }
    const now = Date.now();
    const entry: StoredSession = {
      meta: {
        id,
        title: sessionTitleOf(current),
        createdAt: index >= 0 ? store.sessions[index].meta.createdAt : now,
        updatedAt: now,
        degraded: currentDegraded,
      },
      messages: current,
    };
    if (index >= 0) store.sessions[index] = entry;
    else store.sessions.push(entry);
    store.activeId = id;
  };

  const persistNow = () => {
    syncActiveIntoStore();
    saveStore(storeRef.current as StoreShape);
    setMetas(toMetas(storeRef.current as StoreShape));
  };

  const schedulePersist = () => {
    if (persistTimerRef.current !== null) window.clearTimeout(persistTimerRef.current);
    persistTimerRef.current = window.setTimeout(() => {
      persistTimerRef.current = null;
      persistNow();
    }, 500);
  };

  // 消息/会话/降级变化 → 500ms 防抖落盘（progress 每 120ms 一次也不会高频写盘）
  useEffect(() => {
    schedulePersist();
  }, [messages, activeId, degraded]);

  // 关闭/刷新前同步 flush（uiRef 保证读到最新值）
  useEffect(() => {
    const flush = () => {
      if (persistTimerRef.current !== null) window.clearTimeout(persistTimerRef.current);
      persistNow();
    };
    window.addEventListener("beforeunload", flush);
    return () => {
      window.removeEventListener("beforeunload", flush);
      flush();
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const startQuery = async (rawQuery = draft) => {
    const query = rawQuery.trim();
    if (!query || isStreaming) return;
    /** 本次流所属会话：切走后旧事件不再污染新会话状态 */
    const sid = activeIdRef.current;

    const userMessage: ChatMessage = {
      id: makeId(),
      role: "user",
      content: query,
      createdAt: Date.now(),
    };

    const assistantId = makeId();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "正在连接问数智能体...",
      createdAt: Date.now(),
      status: "streaming",
      steps: [],
      originalQuery: query,
    };

    const controller = new AbortController();
    controllerRef.current = controller;
    setActiveController(controller);
    setDraft("");
    setMessages((current) => [...current, userMessage, assistantMessage]);

    const onEvent = (event: AgentEvent) => {
      if (event.degraded && sid === activeIdRef.current) setDegraded(true);
      setMessages((current) =>
        current.map((message) => {
          if (message.id !== assistantId) return message;

          if (event.type === "progress") {
            return {
              ...message,
              content: event.status === "running" ? `正在执行：${event.step}` : message.content,
              steps: upsertStep(message.steps, event),
            };
          }

          if (event.type === "result") {
            return {
              ...message,
              status: "done",
              content: summarizeResult(event.data),
              result: event.data,
              resultPayload: event,
            };
          }

          if (event.type === "error") {
            // 澄清追问（PRD 四.4）：need_clarification=true 渲染补充信息面板，不当作失败
            if (event.need_clarification) {
              return {
                ...message,
                status: "clarifying",
                content: "需要补充一点信息才能继续查询。",
                clarification: event.message,
                error: undefined,
              };
            }
            return {
              ...message,
              status: "error",
              content: "这次查询没有成功。",
              error: event.message,
            };
          }

          return message;
        }),
      );
    };

    try {
      await streamQuery(query, { signal: controller.signal, onEvent });
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId && message.status === "streaming"
            ? { ...message, status: "done", content: "流程已结束，后端未返回查询结果。" }
            : message,
        ),
      );
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === "AbortError";
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                status: isAbort ? "done" : "error",
                content: isAbort ? "已停止本次查询。" : "无法连接问数接口。",
                error: isAbort ? undefined : error instanceof Error ? error.message : String(error),
              }
            : message,
        ),
      );
    } finally {
      // 只清理自己的 controller，避免误清期间启动的新流
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setActiveController(null);
      }
    }
  };

  const stopQuery = () => {
    activeController?.abort();
  };

  /** 澄清面板提交：把补充信息与该轮原问题合并后重新提问（原问题保留在会话中） */
  const clarifyFrom = (assistantId: string, supplement: string) => {
    if (isStreaming) return;
    const index = messages.findIndex((item) => item.id === assistantId);
    if (index <= 0) return;
    const userMessage = messages
      .slice(0, index)
      .reverse()
      .find((item) => item.role === "user");
    if (!userMessage) return;
    startQuery(`${userMessage.content}；补充信息：${supplement}`);
  };

  /** 新会话：当前会话先落盘，再开空白会话（历史保留） */
  const createSession = () => {
    if (isStreaming) return;
    persistNow();
    const id = makeId();
    activeIdRef.current = id;
    (storeRef.current as StoreShape).activeId = id;
    saveStore(storeRef.current as StoreShape);
    setActiveId(id);
    setMessages([]);
    setDegraded(false);
    setDraft("");
  };

  /** 清空：删除当前会话（含历史条目），回到全新空白会话 */
  const clearConversation = () => {
    if (isStreaming) return;
    const store = storeRef.current as StoreShape;
    store.sessions = store.sessions.filter((item) => item.meta.id !== activeIdRef.current);
    const id = makeId();
    activeIdRef.current = id;
    store.activeId = id;
    saveStore(store);
    setMetas(toMetas(store));
    setActiveId(id);
    setMessages([]);
    setDegraded(false);
    setDraft("");
  };

  /** 切换历史会话：先存当前，再载目标（流式中由侧栏禁用，双保险） */
  const selectSession = (id: string) => {
    if (isStreaming || id === activeIdRef.current) return;
    persistNow();
    const target = (storeRef.current as StoreShape).sessions.find((item) => item.meta.id === id);
    if (!target) return;
    activeIdRef.current = id;
    (storeRef.current as StoreShape).activeId = id;
    setActiveId(id);
    setMessages(target.messages);
    setDegraded(target.meta.degraded);
  };

  return (
    <div className="h-dvh overflow-hidden bg-parchment text-ink">
      <div className="relative grid h-full min-h-0 overflow-hidden lg:grid-cols-[264px_minmax(0,1fr)]">
        <Sidebar
          examples={ALL_QUESTIONS}
          sessions={metas}
          activeId={activeId}
          isStreaming={isStreaming}
          onNewSession={createSession}
          onUseExample={(question) => void startQuery(question)}
          onSelectSession={selectSession}
        />

        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <TopBar
            sessionTitle={sessionTitle}
            isStreaming={isStreaming}
            canClear={messages.length > 0}
            onClear={clearConversation}
          />

          {degraded && (
            <div
              role="status"
              className="border-b border-warning/40 bg-warning/15 px-4 py-2 text-center text-sm font-medium text-warning"
            >
              当前为简易模式
              <span className="ml-2 text-xs font-normal opacity-80">规则模板直出，结果仅供参考</span>
            </div>
          )}

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {messages.length === 0 ? (
              <WelcomeHero
                value={draft}
                disabled={!canSubmit}
                isStreaming={isStreaming}
                onChange={setDraft}
                onSubmit={() => startQuery()}
                onStop={stopQuery}
                onPick={(question) => void startQuery(question)}
              />
            ) : (
              <div className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-6 lg:px-8">
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    onClarify={(supplement) => clarifyFrom(message.id, supplement)}
                  />
                ))}
              </div>
            )}
          </div>

          {messages.length > 0 && (
            <Composer
              value={draft}
              disabled={!canSubmit}
              isStreaming={isStreaming}
              onChange={setDraft}
              onSubmit={() => startQuery()}
              onStop={stopQuery}
            />
          )}
        </main>
      </div>
    </div>
  );
}
