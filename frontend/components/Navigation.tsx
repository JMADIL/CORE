import React from "react";
import { RotateCcw } from "lucide-react";

interface NavigationProps {
  sessionId: string;
  onReset: () => void;
}

export function Navigation({ sessionId, onReset }: NavigationProps) {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-canvas/60 backdrop-blur-md z-50 flex items-center justify-between px-6 md:px-12 transition-all duration-300">
      {/* Logo */}
      <div className="flex items-center">
        <a href="/" className="hover:opacity-85 transition-opacity block overflow-hidden h-16 flex items-center justify-center">
          <img
            src="/logo.png"
            alt="Core"
            className="h-40 w-auto object-contain -my-10 select-none pointer-events-none"
          />
        </a>
      </div>

      {/* Reset Thread with Icon Animation */}
      <div className="flex items-center select-none">
        <button
          onClick={onReset}
          className="group flex items-center gap-1.5 text-sm font-sans font-medium text-[#e3e0da] hover:opacity-80 transition-all duration-200 cursor-pointer active:scale-95"
          title="Reset thread and session"
        >
          <RotateCcw className="w-3.5 h-3.5 text-[#e3e0da]/85 transition-transform duration-500 ease-out group-hover:rotate-[360deg]" />
          <span>Reset</span>
        </button>
      </div>
    </header>
  );
}
