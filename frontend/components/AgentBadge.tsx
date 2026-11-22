import { LoaderCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ActiveAgent } from "@/types/chat";

const labels: Record<ActiveAgent, string> = {
  idle: "Ready when you are",
  supervisor: "Thinking",
  tool_agent: "Working with tools",
  responder: "Writing a response",
};
export function AgentBadge({ activeAgent }: { activeAgent: ActiveAgent }) {
  return (
    <Badge
      variant="outline"
      className="h-6 gap-1.5 border-border text-[10px] font-normal text-muted-foreground"
      role="status"
    >
      {activeAgent !== "idle" ? (
        <LoaderCircle className="size-3 animate-spin" />
      ) : (
        <span className="size-1.5 rounded-full bg-emerald-500" />
      )}
      {labels[activeAgent]}
    </Badge>
  );
}
