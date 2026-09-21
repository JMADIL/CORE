import React, { useState, useRef, useEffect } from "react";
import { ArrowUp } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  };

  // Auto-resize textarea height
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [text]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black via-black/95 to-transparent z-40">
      {/* Blurred fade line above control deck */}
      <div
        className="pointer-events-none absolute bottom-0 inset-x-0 h-44 z-[1] transition-[height] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]"
        style={{
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
          background: "transparent",
          maskImage: "linear-gradient(to top, rgb(0 0 0 / 1) 0%, rgb(0 0 0 / 0.9) 30%, rgb(0 0 0 / 0.8) 68%, transparent 100%)",
          WebkitMaskImage: "linear-gradient(to top, rgb(0 0 0 / 1) 0%, rgb(0 0 0 / 0.9) 30%, rgb(0 0 0 / 0.8) 68%, transparent 100%)",
        }}
      />

      <form
        onSubmit={handleSubmit}
        className="max-w-3xl mx-auto relative z-10 flex items-center bg-[#e3e0da]/5 border border-[#e3e0da]/20 rounded-full focus-within:border-[#e3e0da]/50 backdrop-blur-md transition-all duration-200"
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Orchestrating agents..." : "Ask Core..."}
          disabled={disabled}
          rows={1}
          className="w-full pl-6 pr-14 py-4 bg-transparent border-0 focus:ring-0 outline-none text-sm text-[#e3e0da] placeholder-[#e3e0da]/40 resize-none max-h-[180px] font-sans"
        />

        {/* Submit button & shortcut indicator */}
        <div className="absolute right-3.5 top-1/2 -translate-y-1/2 flex items-center">
          <button
            type="submit"
            disabled={!text.trim() || disabled}
            className={`p-2 rounded-full transition-all duration-150 flex items-center justify-center cursor-pointer active:scale-95 ${text.trim() && !disabled
              ? "bg-[#e3e0da] text-black hover:bg-[#e3e0da]/90"
              : "bg-[#e3e0da]/5 border border-[#e3e0da]/10 text-[#e3e0da]/30"
              }`}
          >
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
      <div className="max-w-3xl mx-auto text-center mt-3 relative z-10 select-none">
        <span className="text-[8px] font-mono tracking-[0.2em] text-[#e3e0da]/40 uppercase">
          LangGraph Multi-Agent Core • MCP Servers
        </span>
      </div>
    </div>
  );
}
