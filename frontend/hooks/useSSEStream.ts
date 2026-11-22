import { useState, useCallback, useRef, useEffect } from "react";
import { sendChatMessage, cancelChatRequest } from "../lib/api";
import { readSSE } from "../lib/sse";

import type { Message, ThoughtNode, ActiveAgent } from "../types/chat";

const agents: string[] = ["supervisor", "tool_agent", "responder"];

interface PendingTurn {
  sessionId: string;
  requestId: string;
  response: Promise<Response>;
  stopping: boolean;
  finished: boolean;
}

function cancelDetachedTurn(
  turn: PendingTurn | null,
  controller: AbortController | null,
) {
  if (!controller) return;
  if (!turn) {
    controller.abort();
    return;
  }
  // Wait for response headers: the backend has then claimed the request lease.
  void turn.response
    .then(() => cancelChatRequest(turn.sessionId, turn.requestId))
    .catch(() => {})
    .finally(() => controller.abort());
}

export function useSSEStream() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeAgent, setActiveAgent] = useState<ActiveAgent>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [stopError, setStopError] = useState("");
  // Allocate IDs only in event handlers, avoiding server/client hydration differences.
  const [sessionId, setSessionId] = useState("");
  const sessionRef = useRef("");
  const controllerRef = useRef<AbortController | null>(null);
  const turnRef = useRef<PendingTurn | null>(null);

  useEffect(
    () => () => {
      const previous = controllerRef.current;
      const turn = turnRef.current;
      controllerRef.current = null;
      turnRef.current = null;
      cancelDetachedTurn(turn, previous);
    },
    [],
  );

  const loadSession = useCallback((id: string, initial: Message[]) => {
    const previous = controllerRef.current;
    const turn = turnRef.current;
    controllerRef.current = null;
    turnRef.current = null;
    cancelDetachedTurn(turn, previous);
    sessionRef.current = id;
    setSessionId(id);
    setMessages(initial);
    setActiveAgent("idle");
    setIsStreaming(false);
    setIsStopping(false);
    setStopError("");
  }, []);

  const clearChat = useCallback(() => loadSession("", []), [loadSession]);

  const stopStream = useCallback(async () => {
    const previous = controllerRef.current;
    const turn = turnRef.current;
    if (!previous || !turn || turn.stopping) return;
    turn.stopping = true;
    setIsStopping(true);
    setStopError("");
    let accepted = false;
    try {
      await turn.response;
      accepted = true;
      await cancelChatRequest(turn.sessionId, turn.requestId);
    } catch {
      if (accepted && !turn.finished && controllerRef.current === previous) {
        turn.stopping = false;
        setIsStopping(false);
        setStopError("Could not stop the response. Please try again.");
        return;
      }
    }
    if (controllerRef.current === previous) {
      controllerRef.current = null;
      turnRef.current = null;
      previous.abort();
      setActiveAgent("idle");
      setIsStreaming(false);
      setIsStopping(false);
    }
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    // Ref guards duplicate submissions before React's next render.
    if (!text.trim() || controllerRef.current) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    if (!sessionRef.current) {
      sessionRef.current = crypto.randomUUID();
      setSessionId(sessionRef.current);
    }
    const id = sessionRef.current;
    const assistantId = crypto.randomUUID();
    const timestamp = Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        thoughts: [],
        timestamp,
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        thoughts: [],
        timestamp,
      },
    ]);
    setIsStreaming(true);
    setStopError("");
    setActiveAgent("supervisor");
    const turn: PendingTurn = {
      sessionId: id,
      requestId: assistantId,
      response: sendChatMessage(text, id, controller.signal, assistantId),
      stopping: false,
      finished: false,
    };
    turnRef.current = turn;
    const current = () => controllerRef.current === controller;
    const timeout = setTimeout(
      () =>
        controller.abort(
          new Error("The response timed out. Please try again."),
        ),
      150_000,
    );
    try {
      const response = await turn.response;
      for await (const { event, data } of readSSE(
        response,
        controller.signal,
      )) {
        if (!current()) break;
        let thought: ThoughtNode | undefined;
        if (
          event === "agent_state" &&
          typeof data.active_agent === "string" &&
          agents.includes(data.active_agent)
        ) {
          setActiveAgent(data.active_agent as ActiveAgent);
          thought = {
            id: crypto.randomUUID(),
            type: "agent_state",
            name: data.active_agent,
            timestamp: Date.now(),
          };
        } else if (
          (event === "tool_call" || event === "tool_result") &&
          typeof data.tool === "string"
        ) {
          thought = {
            id: crypto.randomUUID(),
            type: event,
            name: data.tool,
            input: data.input,
            output: typeof data.output === "string" ? data.output : undefined,
            timestamp: Date.now(),
          };
        } else if (event === "error") {
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "The response failed.",
          );
        }
        if (event === "token" && typeof data.token !== "string")
          throw new Error("Invalid text received from server.");
        if (thought || event === "token") {
          const nextThought = thought;
          const token = event === "token" ? (data.token as string) : "";
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: message.content + token,
                    thoughts: nextThought
                      ? [...message.thoughts, nextThought]
                      : message.thoughts,
                  }
                : message,
            ),
          );
        }
      }
    } catch (error: unknown) {
      if (current()) {
        const reason = controller.signal.aborted
          ? controller.signal.reason
          : error;
        const detail =
          reason instanceof Error
            ? reason.message
            : "Connection failed. Please try again.";
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content: `${message.content}\n\n[Error: ${detail}]`,
                }
              : message,
          ),
        );
      }
    } finally {
      clearTimeout(timeout);
      turn.finished = true;
      if (current() && !turn.stopping) {
        controllerRef.current = null;
        turnRef.current = null;
        setIsStreaming(false);
        setActiveAgent("idle");
      }
    }
  }, []);

  return {
    messages,
    activeAgent,
    isStreaming,
    isStopping,
    stopError,
    sessionId,
    sendMessage,
    clearChat,
    loadSession,
    stopStream,
  };
}
