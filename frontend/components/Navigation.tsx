"use client";

import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AgentBadge } from "@/components/AgentBadge";
import type { ActiveAgent } from "@/types/chat";

export function Navigation({
  title,
  activeAgent,
  model,
  status,
}: {
  title: string;
  activeAgent: ActiveAgent;
  model: string;
  status: "connecting" | "online" | "offline";
}) {
  const { setTheme } = useTheme();
  const label = model.startsWith("nvidia/")
    ? "NVIDIA Nemotron"
    : model
        .replace(/:free$/, "")
        .split("/")
        .pop() || "Connecting…";
  const connectionLabel =
    status === "online"
      ? "API connected"
      : status === "offline"
        ? "API offline"
        : "Connecting to API";
  const connectionColor =
    status === "online"
      ? "bg-emerald-500"
      : status === "offline"
        ? "bg-destructive"
        : "bg-muted-foreground animate-pulse";
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border/70 px-4 sm:px-7">
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger className="text-muted-foreground" />
        <span className="truncate text-[13px] font-medium">{title}</span>
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        {activeAgent !== "idle" && (
          <div className="hidden lg:block">
            <AgentBadge activeAgent={activeAgent} />
          </div>
        )}
        <Tooltip>
          <TooltipTrigger
            render={
              <span
                tabIndex={0}
                aria-label={`Backend status: ${connectionLabel}`}
                className="hidden items-center gap-1.5 text-xs text-muted-foreground md:flex"
              />
            }
          >
            <span
              aria-hidden="true"
              title={connectionLabel}
              className={`mr-0.5 size-1.5 rounded-full ${connectionColor}`}
            />
            {label}
            {status === "offline" && (
              <span className="text-[10px] text-destructive">API offline</span>
            )}
            {model.endsWith(":free") && (
              <Badge
                variant="secondary"
                className="ml-1 h-5 px-1.5 text-[9px] text-muted-foreground"
              >
                Free
              </Badge>
            )}
          </TooltipTrigger>
          <TooltipContent>
            {status === "online"
              ? `Backend connected · ${model}`
              : status === "offline"
                ? "Backend offline. The chat server is not reachable."
                : "Checking the backend connection"}
          </TooltipContent>
        </Tooltip>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                aria-label="Change color theme"
                title="Change color theme"
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground"
              />
            }
          >
            <Sun className="hidden size-4 dark:block" />
            <Moon className="size-4 dark:hidden" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-36">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Appearance</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setTheme("light")}>
                <Sun />
                Light
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("dark")}>
                <Moon />
                Dark
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("system")}>
                <Monitor />
                System
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
