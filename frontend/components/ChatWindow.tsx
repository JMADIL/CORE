import type { ReactNode } from "react";

export function ChatWindow({ children }: { children: ReactNode }) {
  return (
    <div
      id="chat-window"
      className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-5 py-8 sm:px-8 sm:py-10"
    >
      {children}
    </div>
  );
}
