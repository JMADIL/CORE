import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ActiveAgent } from "../hooks/useSSEStream";

interface AgentBadgeProps {
  activeAgent: ActiveAgent;
}

export function AgentBadge({ activeAgent }: AgentBadgeProps) {
  const getAgentStyles = (agent: ActiveAgent) => {
    switch (agent) {
      case "supervisor":
        return {
          label: "supervisor",
          dotColor: "bg-accent-green",
        };
      case "tool_agent":
        return {
          label: "tool agent",
          dotColor: "bg-accent-blue",
        };
      case "responder":
        return {
          label: "responder",
          dotColor: "bg-accent-purple",
        };
      default:
        return {
          label: "system idle",
          dotColor: "bg-text-muted",
        };
    }
  };

  const current = getAgentStyles(activeAgent);

  return (
    <div className="flex items-center justify-center select-none py-1">
      <AnimatePresence mode="wait">
        <motion.div
          key={activeAgent}
          initial={{ opacity: 0, y: -2 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 2 }}
          transition={{ duration: 0.15 }}
          className="flex items-center gap-2 px-3 py-1 bg-surface/20 border border-border-subtle/50 rounded-full text-[9px] font-mono tracking-[0.2em] uppercase font-semibold text-text-secondary"
        >
          {/* Pulsing indicator dot */}
          <span className="relative flex h-1.5 w-1.5">
            {activeAgent !== "idle" && (
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${current.dotColor}`}></span>
            )}
            <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${current.dotColor}`}></span>
          </span>
          <span>{current.label}</span>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
