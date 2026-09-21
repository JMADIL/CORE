"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message } from "../hooks/useSSEStream";
import { ThoughtProcess } from "./ThoughtProcess";

interface MessageBubbleProps {
  message: Message;
  isStreamingActive: boolean;
}

export function MessageBubble({ message, isStreamingActive }: MessageBubbleProps) {
  const isUser = message.role === "user";
  console.log("[MessageBubble] Rendering message:", message.id, "content:", JSON.stringify(message.content), "role:", message.role);

  return (
    <div className={`w-full max-w-3xl mx-auto px-4 md:px-6 py-4 flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      {/* Role label */}
      <span className="text-[11px] font-sans font-semibold tracking-[0.1em] text-[#e3e0da]/40 mb-1.5 uppercase select-none">
        {isUser ? "User" : "Core"}
      </span>

      <div
        className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-[15.5px] leading-relaxed font-display ${
          isUser
            ? "bg-[#e3e0da] text-[#121212] font-normal rounded-tr-sm"
            : "bg-[#e3e0da]/5 text-[#e3e0da]/95 rounded-tl-sm border border-[#e3e0da]/15"
        }`}
      >
        {/* Thoughts section (for assistant messages only) */}
        {!isUser && message.thoughts && message.thoughts.length > 0 && (
          <div className="mb-3.5">
            <ThoughtProcess thoughts={message.thoughts} />
          </div>
        )}

        {/* Message body */}
        <div className="min-w-0">
          {message.content === "" && !isUser && isStreamingActive ? (
            <div className="flex items-center gap-1.5 py-1 px-0.5 select-none" title="orchestrating agents...">
              <span className="w-1.5 h-1.5 rounded-full bg-[#e3e0da]/60 animate-bounce [animation-delay:-0.3s]"></span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#e3e0da]/60 animate-bounce [animation-delay:-0.15s]"></span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#e3e0da]/60 animate-bounce"></span>
            </div>
          ) : isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <div className={`prose-editorial ${isStreamingActive ? "streaming-cursor" : ""}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
