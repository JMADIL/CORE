import React, { useRef, useEffect, ReactNode } from "react";

interface ChatWindowProps {
  children: ReactNode;
  /** Whether there are any messages to display */
  hasMessages: boolean;
}

/**
 * ChatWindow — Centered, scrollable message area container.
 * Matches the editorial minimalist layout of tingyan.me.
 */
export function ChatWindow({ children, hasMessages }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when children change
  useEffect(() => {
    if (scrollRef.current && hasMessages) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [children, hasMessages]);

  return (
    <div
      ref={scrollRef}
      className="flex-grow flex flex-col w-full overflow-y-auto"
      id="chat-window"
    >
      {children}
    </div>
  );
}
