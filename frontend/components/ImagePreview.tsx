"use client";

import { useState } from "react";

export function ImagePreview({ src, alt = "Generated image" }: { src: string; alt?: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className="my-4 block max-w-xl overflow-hidden rounded-2xl border border-border bg-muted/20">
      {!failed ? (
        <a href={src} target="_blank" rel="noopener noreferrer" className="block" aria-label="Open generated image">
          {/* Signed provider files must load directly, without an image optimization proxy. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt={alt} loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} className="block max-h-[32rem] w-full object-contain" />
        </a>
      ) : (
        <span role="status" className="block px-4 pt-4 text-sm text-muted-foreground">Preview unavailable. The image link may have expired.</span>
      )}
      <a href={src} target="_blank" rel="noopener noreferrer" className="block px-4 py-3 text-xs font-medium">Open image</a>
    </span>
  );
}
