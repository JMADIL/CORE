import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronRight } from "lucide-react";
import { ThoughtNode } from "../hooks/useSSEStream";

interface ThoughtProcessProps {
  thoughts: ThoughtNode[];
}

export function ThoughtProcess({ thoughts }: ThoughtProcessProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  if (!thoughts || thoughts.length === 0) return null;

  const toggleNode = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedNodes((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="border border-[#e3e0da]/15 bg-[#e3e0da]/5 rounded-xl overflow-hidden my-4 max-w-xl transition-all duration-200">
      {/* Header Accordion Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[#e3e0da]/5 transition-colors duration-150 cursor-pointer text-[12px] font-display tracking-wide text-[#e3e0da]/80 hover:text-[#e3e0da] select-none font-medium"
      >
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#e3e0da]/60"></span>
          <span>Thought Process ({thoughts.length} events)</span>
        </div>
        {isOpen ? <ChevronDown className="w-3.5 h-3.5 opacity-60" /> : <ChevronRight className="w-3.5 h-3.5 opacity-60" />}
      </button>

      {/* Accordion Content */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden border-t border-[#e3e0da]/10"
          >
            <div className="p-4 font-display text-[12px] text-[#e3e0da]/80 flex flex-col gap-3 leading-relaxed">
              {thoughts.map((node, index) => {
                const isExpanded = expandedNodes[node.id];

                if (node.type === "agent_state") {
                  return (
                    <div key={node.id} className="flex items-center gap-2 text-[12px] text-[#e3e0da]/70">
                      <span className="text-[#e3e0da]/30 select-none">●</span>
                      <span>routed to agent</span>
                      <span className="px-2 py-0.5 rounded-full border border-[#e3e0da]/20 bg-[#e3e0da]/5 text-[11px] font-medium text-[#e3e0da]">
                        {node.name}
                      </span>
                    </div>
                  );
                }

                if (node.type === "tool_call") {
                  return (
                    <div key={node.id} className="flex flex-col gap-1.5">
                      <div
                        onClick={(e) => toggleNode(node.id, e)}
                        className="flex items-center gap-2 cursor-pointer text-[12px] text-[#e3e0da]/70 hover:text-[#e3e0da] transition-colors"
                      >
                        <span className="text-[#e3e0da]/30 select-none">○</span>
                        <span>invoking tool</span>
                        <span className="px-2 py-0.5 rounded-full border border-[#e3e0da]/20 bg-[#e3e0da]/5 text-[11px] font-medium text-[#e3e0da]">
                          {node.name}
                        </span>
                        <span className="text-[#e3e0da]/40 text-[10px] hover:underline flex items-center gap-1 ml-1 select-none">
                          ({isExpanded ? "hide parameters" : "show parameters"})
                        </span>
                      </div>
                      
                      {isExpanded && node.input && (
                        <div className="ml-4 pl-3 border-l border-[#e3e0da]/10 py-1">
                          <pre className="bg-black/30 p-2.5 rounded border border-[#e3e0da]/10 text-[10px] overflow-x-auto text-[#e3e0da]/90 max-w-full font-mono">
                            {JSON.stringify(node.input, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                }

                if (node.type === "tool_result") {
                  return (
                    <div key={node.id} className="flex flex-col gap-1.5">
                      <div
                        onClick={(e) => toggleNode(node.id, e)}
                        className="flex items-center gap-2 cursor-pointer text-[12px] text-[#e3e0da]/70 hover:text-[#e3e0da] transition-colors"
                      >
                        <span className="text-[#e3e0da]/30 select-none">✓</span>
                        <span>received output</span>
                        <span className="px-2 py-0.5 rounded-full border border-[#e3e0da]/20 bg-[#e3e0da]/5 text-[11px] font-medium text-[#e3e0da]">
                          {node.name}
                        </span>
                        <span className="text-[#e3e0da]/40 text-[10px] hover:underline flex items-center gap-1 ml-1 select-none">
                          ({isExpanded ? "hide log" : "show log"})
                        </span>
                      </div>
                      
                      {isExpanded && node.output && (
                        <div className="ml-4 pl-3 border-l border-[#e3e0da]/10 py-1">
                          <pre className="bg-black/30 p-2.5 rounded border border-[#e3e0da]/10 text-[10px] overflow-x-auto text-[#e3e0da]/90 whitespace-pre-wrap max-w-full font-mono">
                            {node.output}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                }

                return null;
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
