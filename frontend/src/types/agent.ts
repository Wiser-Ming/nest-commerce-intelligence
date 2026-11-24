export type ProgressStatus = "running" | "success" | "error";

export type ProgressEvent = {
  type: "progress";
  step: string;
  status: ProgressStatus;
};

export type ResultEvent = {
  type: "result";
  data: unknown;
};

export type Intent = "database_query" | "non_database" | "clarification";

export type RouteEvent = {
  type: "route";
  intent: Intent;
  confidence: number;
  probabilities?: Record<string, number>;
  model?: string;
};

export type TextEvent = {
  type: "text";
  content: string;
};

export type DoneEvent = {
  type: "done";
  intent: Intent;
};

export type ErrorEvent = {
  type: "error";
  message: string;
};

export type AgentEvent = ProgressEvent | RouteEvent | TextEvent | DoneEvent | ResultEvent | ErrorEvent;

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
  status?: "streaming" | "done" | "error";
  steps?: StepState[];
  result?: unknown;
  error?: string;
  route?: RouteEvent;
};
