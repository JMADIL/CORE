"use client";

import { useState } from "react";

export function AudioPreview({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="my-4 max-w-xl rounded-2xl border border-border bg-muted/20 p-4">
      <p className="mb-3 text-sm font-medium">Generated audio</p>
      {failed ? (
        <p role="status" className="text-sm text-muted-foreground">Audio unavailable. The file link may have expired. Ask Core to check the existing generation.</p>
      ) : (
        <audio controls preload="none" src={src} aria-label="Generated audio" onError={() => setFailed(true)} className="w-full">
          Your browser does not support audio playback.
        </audio>
      )}
      <a href={src} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-medium">Open audio</a>
    </div>
  );
}
