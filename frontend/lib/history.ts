import type { Message, ThoughtNode, ChatSession } from "../types/chat";

/** Treat browser storage as untrusted; migrate valid older threads without crashing. */
export function parseSessions(raw: string | null): ChatSession[] {
  if (!raw) return [];
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    return value.slice(0, 50).flatMap((entry): ChatSession[] => {
      if (!entry || typeof entry !== "object" || typeof entry.id !== "string" ||
          !/^[a-zA-Z0-9_-]{1,128}$/.test(entry.id) || !Array.isArray(entry.messages)) return [];
      const messages = entry.messages.slice(-100).flatMap((message: unknown): Message[] => {
        if (!message || typeof message !== "object") return [];
        const m = message as Record<string, unknown>;
        if (typeof m.id !== "string" || (m.role !== "user" && m.role !== "assistant") || typeof m.content !== "string") return [];
        const thoughts: ThoughtNode[] = Array.isArray(m.thoughts) ? m.thoughts.filter((t): t is ThoughtNode =>
          !!t && typeof t === "object" && typeof t.id === "string" && typeof t.name === "string" &&
          ["agent_state", "tool_call", "tool_result"].includes(t.type) && typeof t.timestamp === "number" &&
          (t.output === undefined || typeof t.output === "string")
        ).slice(-100) : [];
        return [{ id: m.id, role: m.role, content: m.content.slice(0, 100000), thoughts,
          timestamp: typeof m.timestamp === "number" ? m.timestamp : undefined,
          error: typeof m.error === "string" ? m.error.slice(0, 2000) : undefined }];
      });
      return [{ id: entry.id, title: typeof entry.title === "string" ? entry.title.slice(0, 100) : "Untitled Thread",
        createdAt: typeof entry.createdAt === "number" ? entry.createdAt : 0,
        updatedAt: typeof entry.updatedAt === "number" ? entry.updatedAt : 0, messages }];
    });
  } catch { return []; }
}

export function mergeSession(saved: ChatSession[], id: string, messages: Message[]): ChatSession[] {
  if (!id || !messages.length) return saved;
  const previous = saved.find((session) => session.id === id);
  const title = messages.find((message) => message.role === "user")?.content.trim() || "New Thread";
  const session: ChatSession = {
    id, title: previous?.title || (title.length > 38 ? title.slice(0, 38) + "..." : title),
    createdAt: previous?.createdAt || messages[0].timestamp || 0,
    updatedAt: messages[messages.length - 1].timestamp || previous?.updatedAt || 0,
    messages,
  };
  return [session, ...saved.filter((entry) => entry.id !== id)]
    .sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 50);
}
