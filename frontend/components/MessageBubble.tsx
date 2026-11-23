"use client";

import { memo, useEffect, useMemo, useRef, useState } from "react";
import { Check, Copy, Info } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ThoughtProcess } from "@/components/ThoughtProcess";
import { Button } from "@/components/ui/button";
import type { Message } from "@/types/chat";
import { responseWords } from "@/lib/responseWords";
import { generatedImages, imageLink } from "@/lib/media";
import { ImagePreview } from "@/components/ImagePreview";

const responsePlugins = [responseWords];

export const MessageBubble = memo(function MessageBubble({
  message,
  isStreamingActive,
}: {
  message: Message;
  isStreamingActive: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const images = useMemo(() => generatedImages(message.thoughts), [message.thoughts]);
  const imageContext = message.thoughts.some(thought => /elevenlabs_creative_(generate|edit)_image$/.test(thought.name));
  useEffect(() => () => clearTimeout(timer.current), []);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setCopyError(false);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError(true);
    }
  };
  if (message.role === "user")
    return (
      <article
        aria-label="Your message"
        className="ml-auto max-w-[90%] rounded-lg border border-brand/10 bg-brand-soft px-5 py-3.5 text-[15px] leading-[1.75] [overflow-wrap:anywhere] sm:max-w-[82%]"
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </article>
    );
  return (
    <article aria-label="Core response" className="min-w-0">
      <div className="mb-4 flex items-center gap-2">
        <span
          className="core-wordmark"
          data-active={isStreamingActive || undefined}
        >
          Core
        </span>
        {isStreamingActive && (
          <span className="text-[10px] text-muted-foreground">Working…</span>
        )}
      </div>
      {message.content ? (
        <div
          className="chat-prose response-text"
          data-streaming={isStreamingActive || undefined}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={responsePlugins}
            components={{
              table: ({ children }) => (
                <div className="my-4 max-w-full overflow-x-auto">
                  <table>{children}</table>
                </div>
              ),
              a: ({ href, children }) => (
                href && imageLink(href, imageContext) && !images.some(image => image.url === href) ?
                <ImagePreview key={href} src={href} /> :
                <a href={href} target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              img: ({ src, alt }) => typeof src === "string" && !images.some(image => image.url === src)
                ? <ImagePreview key={src} src={src} alt={alt} /> : null,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      ) : message.error ? null : isStreamingActive ? (
        <div role="status" className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
          <span className="response-typing" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Preparing a response…</span>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Response stopped.</p>
      )}
      {images.map(image => <ImagePreview key={image.url} src={image.url} />)}
      {message.error && (
        <div
          role="alert"
          className="mt-3 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100"
        >
          <Info className="mt-1 size-4 shrink-0" aria-hidden="true" />
          <p>{message.error}</p>
        </div>
      )}
      <ThoughtProcess thoughts={message.thoughts} />
      {!!message.content && !isStreamingActive && (
        <div className="mt-3 flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon-xs"
            className="text-muted-foreground"
            onClick={copy}
            aria-label={copied ? "Response copied" : "Copy response"}
            title={copied ? "Copied" : "Copy response"}
          >
            {copied ? (
              <Check className="size-3 text-emerald-600" />
            ) : (
              <Copy className="size-3" />
            )}
          </Button>
          {(copied || copyError) && (
            <span role="status" className="text-[10px] text-muted-foreground">
              {copied ? "Copied" : "Could not access clipboard"}
            </span>
          )}
        </div>
      )}
    </article>
  );
});
