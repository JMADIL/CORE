import Image from "next/image";
import { cn } from "@/lib/utils";

export function CoreMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative inline-flex size-8 shrink-0 overflow-hidden rounded-full border border-border bg-muted",
        className,
      )}
    >
      <Image
        src="/avatars/core-character.png"
        alt=""
        fill
        sizes="32px"
        className="object-cover"
      />
    </span>
  );
}
