"use client";

import { ArrowUp, Square, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { RefObject } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
  isStreaming: boolean;
  isStopping?: boolean;
  stopError?: string;
  onStop: () => void;
  value: string;
  onChange: (text: string) => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
}

export function ChatInput({
  onSend,
  disabled,
  isStreaming,
  isStopping = false,
  stopError = "",
  onStop,
  value,
  onChange,
  inputRef,
}: ChatInputProps) {
  const submit = () => {
    if (value.trim() && !disabled) {
      onSend(value);
      onChange("");
    }
  };
  return (
    <div className="w-full">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="chat-composer flex items-end gap-3 rounded-[22px] p-2.5"
      >
        <Textarea
          ref={inputRef}
          aria-label="Message Core"
          placeholder="Message Core…"
          maxLength={12000}
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              submit();
            }
          }}
          rows={1}
          className="max-h-40 min-h-11 min-w-0 flex-1 resize-none rounded-none border-0 bg-transparent! px-3 py-2.5 text-base leading-6 shadow-none placeholder:text-muted-foreground/80 focus-visible:ring-0 disabled:bg-transparent disabled:opacity-60 md:text-[15px]"
        />
        {isStreaming || isStopping ? (
          <Button
            type="button"
            size="icon"
            variant="secondary"
            onClick={onStop}
            aria-label={isStopping ? "Stopping response" : "Stop response"}
            disabled={isStopping}
            className="mb-1 size-9 shrink-0 rounded-full transition-[background-color,color,box-shadow,transform] duration-200 ease-out active:scale-95"
          >
            {isStopping ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <Square className="size-3.5 fill-current" />
            )}
          </Button>
        ) : (
          <Button
            type="submit"
            size="icon"
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className="mb-1 size-9 shrink-0 rounded-full bg-primary text-primary-foreground transition-[background-color,color,box-shadow,transform] duration-200 ease-out hover:bg-primary/90 hover:shadow-sm active:scale-95 disabled:bg-muted disabled:text-muted-foreground/60 disabled:opacity-100"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </form>
      {stopError && (
        <p role="status" className="mt-2 px-2 text-xs text-destructive">
          {stopError}
        </p>
      )}
      <div className="mt-2.5 hidden items-center justify-end px-2 text-[11px] text-muted-foreground/80 sm:flex">
        <span>
          Enter to send<span className="mx-2">·</span>Shift + Enter for a new
          line
        </span>
      </div>
    </div>
  );
}
