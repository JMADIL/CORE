"use client";

import { useState } from "react";
import { Check, ChevronDown, GitBranch, Wrench } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { ThoughtNode } from "@/types/chat";

const agentLabels: Record<string, string> = {
  supervisor: "Considered your request",
  tool_agent: "Worked with available tools",
  responder: "Composed a response",
};

export function ThoughtProcess({ thoughts }: { thoughts: ThoughtNode[] }) {
  const [open, setOpen] = useState(false);
  if (!thoughts.length) return null;
  const toolCount = thoughts.filter(
    (thought) => thought.type === "tool_call",
  ).length;
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mt-4">
      <CollapsibleTrigger className="flex items-center gap-2 rounded-md py-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
        <GitBranch className="size-3" />
        <span>How Core worked</span>
        {toolCount > 0 && (
          <span className="rounded bg-muted px-1.5 py-0.5 text-[9px]">
            {toolCount} {toolCount === 1 ? "tool" : "tools"}
          </span>
        )}
        <ChevronDown
          className={`size-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden">
        <div className="mt-3 space-y-3 border-l border-border pl-4 text-xs text-muted-foreground">
          {thoughts.map((thought) => (
            <div key={thought.id} className="flex items-start gap-2">
              <span className="pt-0.5">
                {thought.type === "agent_state" ? (
                  <Check className="size-3" />
                ) : (
                  <Wrench className="size-3 text-brand" />
                )}
              </span>
              <div className="min-w-0 flex-1">
                {thought.type === "agent_state" ? (
                  <span>{agentLabels[thought.name] || thought.name}</span>
                ) : (
                  <details className="group">
                    <summary className="cursor-pointer select-none break-words">
                      {thought.type === "tool_call"
                        ? "Used "
                        : "Received results from "}
                      <span className="font-medium text-foreground/75">
                        {thought.name.replaceAll("_", " ")}
                      </span>
                    </summary>
                    <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap break-all rounded-lg border bg-muted/60 p-3 font-mono text-[10px] leading-5">
                      {thought.type === "tool_call"
                        ? JSON.stringify(thought.input, null, 2)
                        : thought.output}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
