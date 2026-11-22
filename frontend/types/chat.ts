/** Shared chat domain types; independent of React hooks and storage helpers. */
export interface ThoughtNode {
  id: string;
  type: "agent_state" | "tool_call" | "tool_result";
  name: string;
  input?: unknown;
  output?: string;
  timestamp: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  error?: string;
  thoughts: ThoughtNode[];
  timestamp?: number;
}
export type ActiveAgent = "supervisor" | "tool_agent" | "responder" | "idle";
export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}
