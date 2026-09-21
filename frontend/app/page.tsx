"use client";

import React, { useEffect, useRef } from "react";
import { useSSEStream } from "../hooks/useSSEStream";
import { Navigation } from "../components/Navigation";
import { ChatWindow } from "../components/ChatWindow";
import { MessageBubble } from "../components/MessageBubble";
import { ChatInput } from "../components/ChatInput";
import { ArrowUpRight } from "lucide-react";

export default function Home() {
  const {
    messages,
    activeAgent,
    isStreaming,
    sessionId,
    sendMessage,
    clearChat,
  } = useSSEStream();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeAgent]);

  // Suggested questions
  const suggestions = [
    "What is the current time in Tokyo?",
    "Search arXiv for recent papers on LLM agents.",
    "Can you explain the sequential thinking process?",
    "Check the weather forecast for Chicago.",
  ];

  return (
    <div className="flex flex-col min-h-screen bg-black font-sans antialiased text-[#ECECED] relative select-none">
      {/* Navigation */}
      <Navigation sessionId={sessionId} onReset={clearChat} />

      {/* Main Container */}
      <main className="flex-grow flex flex-col pt-16 pb-40">


        {/* Message Thread or Zero State */}
        <ChatWindow hasMessages={messages.length > 0}>
          {messages.length === 0 ? (
            /* Welcome / Zero State Screen — Editorial Minimalist Layout (tingyan.me) */
            <div className="flex-grow flex items-center justify-center max-w-2xl mx-auto px-6 py-12 md:py-24">
              <div className="space-y-6 text-left">
                {/* Paragraph 1 — introduction */}
                <p className="font-display text-[15px] md:text-[17px] font-light leading-relaxed text-[#e3e0da]/80">
                  A multi-agent orchestrator built end-to-end with LangGraph, FastAPI, and MCP servers — working from concept to production
                </p>

                {/* Paragraph 2 — capabilities */}
                <p className="font-display text-[15px] md:text-[17px] font-light leading-relaxed text-[#e3e0da]/80">
                  In the active session, I coordinate routing decisions at the{" "}
                  <span className="font-display font-medium text-[#e3e0da] border-b border-transparent hover:border-accent-yellow transition-colors duration-150 cursor-default">
                    Supervisor Node
                  </span>
                  , execute actions through the{" "}
                  <span className="font-display font-medium text-[#e3e0da] border-b border-transparent hover:border-accent-yellow transition-colors duration-150 cursor-default">
                    Tool Agent
                  </span>
                  {" "}with live MCP connections to{" "}
                  <span className="font-display font-medium text-[#e3e0da] border-b border-transparent hover:border-accent-yellow transition-colors duration-150 cursor-default">
                    Weather
                  </span>
                  ,{" "}
                  <span className="font-display font-medium text-[#e3e0da] border-b border-transparent hover:border-accent-yellow transition-colors duration-150 cursor-default">
                    Time
                  </span>
                  ,{" "}
                  <span className="font-display font-medium text-[#e3e0da] border-b border-transparent hover:border-accent-yellow transition-colors duration-150 cursor-default">
                    Research
                  </span>
                  , and{" "}
                  <span className="font-display font-medium text-[#e3e0da] border-b border-transparent hover:border-accent-yellow transition-colors duration-150 cursor-default">
                    Sequential Thinking
                  </span>
                  {" "}servers
                </p>

                {/* Paragraph 3 — invitation */}
                <p className="font-display text-[15px] md:text-[17px] font-light leading-relaxed text-[#e3e0da]/80">
                  Start by selecting a thread below, or type your request directly in the prompt bar
                </p>

                {/* Suggestions Block */}
                <div className="pt-8 space-y-4">
                  <span className="text-[12px] font-sans font-semibold tracking-[0.15em] text-[#e3e0da]/60 uppercase block">
                    Suggested Threads
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => sendMessage(q)}
                        disabled={isStreaming}
                        className="px-4 py-2 rounded-full border border-[#e3e0da]/20 hover:border-[#e3e0da]/50 bg-[#e3e0da]/5 hover:bg-[#e3e0da]/10 text-[13px] text-[#e3e0da]/80 hover:text-[#e3e0da] font-sans font-light tracking-normal transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed text-left active:scale-[0.98] flex items-center gap-2"
                      >
                        <span>{q}</span>
                        <ArrowUpRight className="w-3.5 h-3.5 text-[#e3e0da]/50 flex-shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Active Message List */
            <div className="flex flex-col w-full">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  isStreamingActive={isStreaming && msg.id === messages[messages.length - 1].id}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </ChatWindow>
      </main>

      {/* Floating Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
