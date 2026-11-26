/**
 * 智能体类型定义
 * 定义问数智能体前端使用的 SSE 事件、流程步骤和聊天消息类型
 */
export type ProgressStatus = "running" | "success" | "error";

export type ProgressEvent = {
  type: "progress";
  step: string;
  status: ProgressStatus;
  /** 降级标记（PRD 八.3）：与 result/error 同源下发，任一事件即可点亮横幅 */
  degraded?: boolean;
};

export type ResultPayload = {
  type: "result";
  /** 本次查询全局 ID：反馈按钮回传时带上（PRD 七.2 采纳率埋点） */
  query_id?: string;
  /** 降级标记（PRD 八.3）：LLM 不可用/演示开关触发，前端亮简易模式横幅 */
  degraded?: boolean;
  data: unknown;
  generated_sql?: string;
  validation_status?: string;
  execution_status?: string;
  correction_count?: number;
  keywords?: string[];
  matched_tables?: string[];
  matched_columns?: string[];
  matched_metrics?: Array<{ name: string; source?: string }>;
  matched_values?: Array<{ value: string; column?: string }>;
  confidence?: string;
  unclear?: string[];
  need_clarification?: boolean;
};

export type ResultEvent = ResultPayload;

export type ErrorEvent = {
  type: "error";
  message: string;
  code?: string;
  need_clarification?: boolean;
  correction_count?: number;
  /** 降级标记（PRD 八.3）：LLM 供应商不可用时下发 */
  degraded?: boolean;
};

export type AgentEvent = ProgressEvent | ResultEvent | ErrorEvent;

export type StepState = {
  step: string;
  status: ProgressStatus;
  updatedAt: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  status?: "streaming" | "done" | "error" | "clarifying";
  steps?: StepState[];
  result?: unknown;
  /** result 事件的完整载荷：生成的 SQL、校验状态、检索证据等（PRD 五a.3 输出格式） */
  resultPayload?: ResultPayload;
  /** need_clarification=true 时的追问话术，前端据此渲染补充信息面板 */
  clarification?: string;
  /** 该轮回答对应的用户原始问题，反馈落盘时回传（PRD 七.2） */
  originalQuery?: string;
  error?: string;
};
