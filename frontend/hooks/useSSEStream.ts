import { useState, useCallback, useRef, useEffect } from "react";
import { sendChatMessage } from "../lib/api";

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
  thoughts: ThoughtNode[];
}

export type ActiveAgent = "supervisor" | "tool_agent" | "responder" | "idle";

export function useSSEStream() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeAgent, setActiveAgent] = useState<ActiveAgent>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() =>
    Math.random().toString(36).substring(2, 15)
  );

  const sessionIdRef = useRef<string>(sessionId);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Abort active connections on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const clearChat = useCallback(() => {
    // Abort any active SSE stream request
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    setMessages([]);
    setActiveAgent("idle");
    setIsStreaming(false);
    const newSessionId = Math.random().toString(36).substring(2, 15);
    sessionIdRef.current = newSessionId;
    setSessionId(newSessionId);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return;

    // Abort any previous active stream just in case
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsStreaming(true);
    setActiveAgent("supervisor");

    // 1. Add the user message
    const userMsgId = Math.random().toString(36).substring(7);
    const userMsg: Message = {
      id: userMsgId,
      role: "user",
      content: text,
      thoughts: [],
    };

    // 2. Add placeholder assistant message
    const assistantMsgId = Math.random().toString(36).substring(7);
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      thoughts: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      const response = await sendChatMessage(text, sessionIdRef.current, controller.signal);

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable.");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let eventName = "";
      let dataBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();

          if (trimmed === "") {
            // End of SSE block: dispatch message
            if (dataBuffer) {
              try {
                const parsedData = JSON.parse(dataBuffer);
                const currentEvent = eventName;
                console.log("[SSE Hook] Received Event:", currentEvent, parsedData);
                
                // 1. Handle side-effects (state changes) outside of the messages state updater
                if (currentEvent === "agent_state") {
                  setActiveAgent(parsedData.active_agent as ActiveAgent);
                } else if (currentEvent === "done" || currentEvent === "error") {
                  setIsStreaming(false);
                  setActiveAgent("idle");
                }

                // 2. Perform pure messages array update
                setMessages((prev) => {
                  const updated = [...prev];
                  const targetIdx = updated.findIndex((m) => m.id === assistantMsgId);
                  console.log("[SSE Hook Callback] event:", currentEvent, "assistantMsgId:", assistantMsgId, "targetIdx:", targetIdx, "current messages:", JSON.stringify(prev));
                  if (targetIdx === -1) return prev;
                  
                  const targetMsg = { ...updated[targetIdx] };
                  const newThoughts = [...targetMsg.thoughts];
 
                  switch (currentEvent) {
                    case "agent_state":
                      const agent = parsedData.active_agent as ActiveAgent;
                      newThoughts.push({
                        id: Math.random().toString(36).substring(7),
                        type: "agent_state",
                        name: agent,
                        timestamp: Date.now(),
                      });
                      break;
 
                    case "tool_call":
                      newThoughts.push({
                        id: Math.random().toString(36).substring(7),
                        type: "tool_call",
                        name: parsedData.tool,
                        input: parsedData.input,
                        timestamp: Date.now(),
                      });
                      break;
 
                    case "tool_result":
                      newThoughts.push({
                        id: Math.random().toString(36).substring(7),
                        type: "tool_result",
                        name: parsedData.tool,
                        output: parsedData.output,
                        timestamp: Date.now(),
                      });
                      break;
 
                    case "token":
                      targetMsg.content += parsedData.token;
                      console.log("[SSE Hook] Updated message content to:", targetMsg.content);
                      break;
 
                    case "done":
                      break;
 
                    case "error":
                      targetMsg.content += `\n\n[Error: ${parsedData.detail}]`;
                      break;
                  }
 
                  targetMsg.thoughts = newThoughts;
                  updated[targetIdx] = targetMsg;
                  console.log("[SSE Hook Callback] returning updated:", JSON.stringify(updated));
                  return updated;
                });
              } catch (e) {
                console.error("Failed to parse SSE JSON:", e);
              }
            }
            eventName = "";
            dataBuffer = "";
          } else if (trimmed.startsWith("event:")) {
            eventName = trimmed.substring(6).trim();
          } else if (trimmed.startsWith("data:")) {
            dataBuffer += trimmed.substring(5).trim();
          }
        }
      }
    } catch (err: unknown) {
      const error = err instanceof Error ? err : new Error(String(err));
      if (error.name === "AbortError") {
        console.log("[SSE Hook] SSE stream connection aborted by client.");
        return;
      }
      console.error("SSE stream connection error:", err);
      setMessages((prev) => {
        const updated = [...prev];
        const targetIdx = updated.findIndex((m) => m.id === assistantMsgId);
        if (targetIdx !== -1) {
          updated[targetIdx] = {
            ...updated[targetIdx],
            content: updated[targetIdx].content + `\n\n[Connection Error: ${error.message}]`,
          };
        }
        return updated;
      });
      setIsStreaming(false);
      setActiveAgent("idle");
    }
  }, [isStreaming]);

  return {
    messages,
    activeAgent,
    isStreaming,
    sessionId,
    sendMessage,
    clearChat,
  };
}
