"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useSSEStream } from "@/hooks/useSSEStream";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { AppSidebar } from "@/components/Sidebar";
import { Navigation } from "@/components/Navigation";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatWindow } from "@/components/ChatWindow";
import { MessageBubble } from "@/components/MessageBubble";
import { ChatInput } from "@/components/ChatInput";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { parseSessions, mergeSession } from "@/lib/history";
import { deleteChatSession } from "@/lib/api";
import type { ChatSession } from "@/types/chat";

const SESSIONS_STORAGE_KEY = "core_chat_sessions_v1";

export default function Home() {
  const {
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
  } = useSSEStream();

  const [savedSessions, setSavedSessions] = useState<ChatSession[]>([]);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const health = useBackendHealth();
  const [isStorageInitialized, setIsStorageInitialized] = useState(false);
  const [storageError, setStorageError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentSessionRef = useRef(sessionId);
  const followScrollRef = useRef(true);
  const [deletingId, setDeletingId] = useState("");
  useEffect(() => {
    currentSessionRef.current = sessionId;
  }, [sessionId]);
  const sessions = useMemo(
    () => mergeSession(savedSessions, sessionId, messages),
    [savedSessions, sessionId, messages],
  );

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      try {
        const stored = parseSessions(
          localStorage.getItem(SESSIONS_STORAGE_KEY),
        );
        // Restore sidebar history; a visit always starts with an empty chat.
        setSavedSessions(stored);
      } catch {
        setStorageError(
          "Browser storage is unavailable. Threads will only be kept in this tab.",
        );
      }
      setIsStorageInitialized(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isStorageInitialized) return;
    const save = () => {
      try {
        localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
      } catch {
        setStorageError(
          "Thread history could not be saved. Browser storage may be full or disabled.",
        );
      }
    };
    // Save after streaming settles, and flush on reload/navigation.
    const timer = setTimeout(save, 500);
    window.addEventListener("pagehide", save);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("pagehide", save);
    };
  }, [sessions, isStorageInitialized]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (followScrollRef.current)
        messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
    });
    return () => cancelAnimationFrame(frame);
  }, [messages, activeAgent]);

  const handleSelectSession = (session: ChatSession) => {
    if (session.id === sessionId) return;
    followScrollRef.current = true;
    setSavedSessions(sessions);
    loadSession(session.id, session.messages);
  };

  const handleNewChat = () => {
    followScrollRef.current = true;
    setSavedSessions(sessions);
    clearChat();
    setDraft("");
    inputRef.current?.focus();
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (deletingId) return;
    if (isStreaming && id === sessionId) {
      setStorageError(
        "Wait for the response to finish before deleting this thread.",
      );
      return;
    }
    setDeletingId(id);
    try {
      await deleteChatSession(id);
      setSavedSessions((previous) =>
        previous.filter((session) => session.id !== id),
      );
      if (currentSessionRef.current === id) clearChat();
      setStorageError("");
    } catch (error) {
      setStorageError(
        error instanceof Error
          ? error.message
          : "Unable to delete this thread.",
      );
    } finally {
      setDeletingId("");
    }
  };

  const suggest = (prompt: string) => {
    setDraft(prompt);
    requestAnimationFrame(() => inputRef.current?.focus());
  };
  const busy =
    isStreaming || isStopping || !isStorageInitialized || !!deletingId;
  const title =
    sessions.find((session) => session.id === sessionId)?.title ||
    "New conversation";

  return (
    <SidebarProvider
      defaultOpen
      className="h-dvh min-h-0 overflow-hidden"
      style={{ "--sidebar-width": "15rem" } as React.CSSProperties}
    >
      <AppSidebar
        onNewChat={handleNewChat}
        currentSessionId={sessionId}
        sessions={sessions}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onSuggestion={suggest}
        deletingId={deletingId}
      />
      <SidebarInset className="min-w-0 overflow-hidden">
        <Navigation
          title={title}
          activeAgent={activeAgent}
          model={health.model}
          status={health.status}
        />
        {storageError && (
          <div
            role="status"
            className="mx-5 mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-2 text-xs text-amber-700 dark:text-amber-300"
          >
            {storageError}
          </div>
        )}
        <div
          className="flex min-h-0 flex-1 flex-col overflow-y-auto"
          aria-label="Conversation"
          onScroll={(event) => {
            const element = event.currentTarget;
            followScrollRef.current =
              element.scrollHeight - element.scrollTop - element.clientHeight <
              120;
          }}
        >
          {messages.length === 0 ? (
            <WelcomeScreen disabled={busy} onSuggestion={suggest} />
          ) : (
            <ChatWindow>
              {messages.map((message, index) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isStreamingActive={
                    isStreaming && index === messages.length - 1
                  }
                />
              ))}
              <div ref={messagesEndRef} />
            </ChatWindow>
          )}
        </div>
        <div className="shrink-0 bg-background px-5 pb-5 pt-3 sm:px-8 sm:pb-6">
          <div className="mx-auto max-w-[680px]">
            <ChatInput
              onSend={sendMessage}
              disabled={busy}
              isStreaming={isStreaming}
              isStopping={isStopping}
              stopError={stopError}
              onStop={stopStream}
              value={draft}
              onChange={setDraft}
              inputRef={inputRef}
            />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
