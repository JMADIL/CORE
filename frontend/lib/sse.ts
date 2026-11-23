export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/** Reconcile a completed answer even if its token events never arrived. */
export function completedText(streamed: string, content: unknown): string {
  if (content !== undefined && typeof content !== "string") throw new Error("Invalid final answer received from server.");
  const final = typeof content === "string" ? content : streamed;
  if (!final.trim()) throw new Error("Core finished without returning an answer. If media generation started, ask to check its status before generating again.");
  return final;
}

/** Parse chunks independently of network boundaries and reject incomplete responses. */
export async function* readSSE(response: Response, signal: AbortSignal): AsyncGenerator<SSEEvent> {
  if (!response.headers.get("content-type")?.includes("text/event-stream")) {
    throw new Error("The server did not return an event stream.");
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Response body is not readable.");
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";
  let data: string[] = [];
  let dataSize = 0;
  let terminal = false;
  const cancel = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener("abort", cancel, { once: true });
  try {
    while (true) {
      signal.throwIfAborted();
      const { done, value } = await reader.read();
      signal.throwIfAborted();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      // Split only on complete newlines, supporting LF, CRLF and CR delimiters.
      let match: RegExpExecArray | null;
      const delimiter = done ? /\r\n|\r|\n/ : /\r\n|\r(?!$)|\n/;
      while ((match = delimiter.exec(buffer)) !== null) {
        const line = buffer.slice(0, match.index);
        if (line.length > 1_000_000) throw new Error("Stream event is too large.");
        buffer = buffer.slice(match.index + match[0].length);
        if (line === "") {
          if (data.length) {
            const parsed: unknown = JSON.parse(data.join("\n"));
            if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
              throw new Error("Invalid stream event.");
            }
            if (event === "done" || event === "error") terminal = true;
            yield { event, data: parsed as Record<string, unknown> };
            if (terminal) return;
          }
          event = "message";
          data = [];
          dataSize = 0;
        } else if (!line.startsWith(":")) {
          const separator = line.indexOf(":");
          const field = separator < 0 ? line : line.slice(0, separator);
          const raw = separator < 0 ? "" : line.slice(separator + 1);
          const value = raw.startsWith(" ") ? raw.slice(1) : raw;
          if (field === "event") event = value;
          if (field === "data") {
            dataSize += value.length + 1;
            if (dataSize > 1_000_000) throw new Error("Stream event is too large.");
            data.push(value);
          }
        }
      }
      if (buffer.length > 1_000_000) {
        throw new Error("Stream event is too large.");
      }
      if (done) break;
    }
    if (!terminal) throw new Error("The response ended unexpectedly. Please try again.");
  } finally {
    signal.removeEventListener("abort", cancel);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
