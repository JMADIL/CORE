"use client";

import { useState } from "react";
import {
  ChevronDown,
  BookOpen,
  BrainCircuit,
  CircleHelp,
  Clock3,
  CloudSun,
  MessageSquare,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GitHubCredit } from "@/components/GitHubCredit";
import { ElevenLabsConnection } from "@/components/ElevenLabsConnection";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
  useSidebar,
} from "@/components/ui/sidebar";
import type { ChatSession } from "@/types/chat";

interface AppSidebarProps {
  onNewChat: () => void;
  currentSessionId: string;
  sessions: ChatSession[];
  onSelectSession: (session: ChatSession) => void;
  onDeleteSession: (id: string, event: React.MouseEvent) => void;
  onSuggestion: (prompt: string) => void;
  deletingId: string;
}

const capabilities = [
  {
    name: "Research",
    icon: BookOpen,
    prompt:
      "Search arXiv for recent papers about AI agents and summarize the main findings.",
  },
  {
    name: "Weather",
    icon: CloudSun,
    prompt: "What is the weather forecast for Chicago?",
  },
  {
    name: "World time",
    icon: Clock3,
    prompt: "What is the current time in Tokyo?",
  },
  {
    name: "Work through an idea",
    icon: BrainCircuit,
    prompt: "Help me think through an idea step-by-step.",
  },
];

export function AppSidebar({
  onNewChat,
  currentSessionId,
  sessions,
  onSelectSession,
  onDeleteSession,
  onSuggestion,
  deletingId,
}: AppSidebarProps) {
  const [query, setQuery] = useState("");
  const { isMobile, setOpenMobile } = useSidebar();
  const closeMobile = () => {
    if (isMobile) setOpenMobile(false);
  };
  const filtered = sessions.filter((session) =>
    session.title.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <Sidebar variant="sidebar">
      <SidebarHeader className="gap-5 px-4 pb-4 pt-5">
        <div className="flex items-center gap-2.5 px-1">
          <span className="text-[28px] font-semibold leading-9 tracking-[-0.03em] text-sidebar-foreground">Core</span>
          <Button
            variant="ghost"
            size="icon-sm"
            className="ml-auto text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground dark:hover:bg-sidebar-accent md:hidden"
            onClick={closeMobile}
            aria-label="Close sidebar"
          >
            <X />
          </Button>
        </div>
        <div className="space-y-3">
          <Button
            onClick={() => {
              onNewChat();
              closeMobile();
            }}
            variant="outline"
            className="h-9 w-full justify-start rounded-xl border-sidebar-border bg-sidebar-accent px-3 text-[13px] text-sidebar-foreground shadow-none hover:bg-white/20 hover:text-sidebar-foreground dark:border-sidebar-border dark:bg-sidebar-accent dark:hover:bg-white/20"
          >
            <span className="flex items-center gap-2">
              <Plus className="size-4" />
              New conversation
            </span>
          </Button>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 z-10 size-3.5 -translate-y-1/2 text-sidebar-foreground/80" />
            <Input
              aria-label="Search conversations"
              placeholder="Search conversations"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="h-8 border-transparent bg-transparent pl-9 text-[13px] text-sidebar-foreground shadow-none placeholder:text-sidebar-foreground/80 focus-visible:border-sidebar-border focus-visible:ring-sidebar-ring/50 dark:bg-transparent"
            />
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent className="px-1">
        <SidebarGroup className="px-2">
          <SidebarGroupLabel className="mb-2 flex justify-between text-[13px] font-normal text-sidebar-foreground/80">
            <span>Conversations</span>
            <span className="font-mono text-[10px] opacity-70">
              {sessions.length}
            </span>
          </SidebarGroupLabel>
          <SidebarMenu className="gap-1">
            {filtered.map((session) => (
              <SidebarMenuItem key={session.id}>
                <SidebarMenuButton
                  isActive={session.id === currentSessionId}
                  onClick={() => {
                    onSelectSession(session);
                    closeMobile();
                  }}
                  className="h-9 gap-2.5 px-3 text-[13px] data-active:bg-sidebar-accent data-active:text-sidebar-accent-foreground"
                >
                  <MessageSquare className="size-3.5 text-sidebar-foreground/80" />
                  <span>{session.title || "Untitled conversation"}</span>
                </SidebarMenuButton>
                <SidebarMenuAction
                  disabled={!!deletingId}
                  showOnHover
                  onClick={(event) => onDeleteSession(session.id, event)}
                  aria-label={`Delete ${session.title || "conversation"}`}
                  title="Delete conversation"
                  className="right-2 top-2.5 text-sidebar-foreground/80 hover:bg-white/15 hover:text-white"
                >
                  <Trash2 className="size-3.5" />
                </SidebarMenuAction>
              </SidebarMenuItem>
            ))}
            {filtered.length === 0 && (
              <li className="px-3 py-6 text-[13px] leading-5 text-sidebar-foreground/80">
                {query ? "No matching conversations." : "No conversations yet."}
              </li>
            )}
          </SidebarMenu>
        </SidebarGroup>
        <SidebarGroup className="mt-auto px-2 pb-3 pt-6">
          <Collapsible className="group/tools">
            <CollapsibleTrigger className="flex h-9 w-full items-center justify-between rounded-xl px-3 transition-colors duration-200 ease-out text-[13px] text-sidebar-foreground/80 hover:bg-sidebar-accent focus-visible:outline-2 focus-visible:outline-ring">
              Tools
              <ChevronDown className="size-3 transition-transform group-data-open/tools:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarMenu className="mt-1 gap-0.5">
                {capabilities.map(({ name, icon: Icon, prompt }) => (
                  <SidebarMenuItem key={name}>
                    <SidebarMenuButton
                      onClick={() => {
                        onSuggestion(prompt);
                        closeMobile();
                      }}
                      className="h-9 gap-2.5 px-3 text-[13px] text-sidebar-foreground/80"
                    >
                      <Icon className="size-3.5" />
                      <span>{name}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </CollapsibleContent>
          </Collapsible>
        </SidebarGroup>
      </SidebarContent>
      <SidebarSeparator className="bg-sidebar-border mx-4 data-[orientation=horizontal]:w-[calc(100%-2rem)]" />
      <SidebarFooter className="gap-3 px-3 pb-3 pt-3">
        <ElevenLabsConnection />
        <Dialog>
          <DialogTrigger
            render={
              <Button
                variant="ghost"
                className="w-full justify-start gap-2.5 px-2 text-[13px] text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground dark:hover:bg-sidebar-accent"
              />
            }
          >
            <CircleHelp className="size-3.5" />
            Quick guide
          </DialogTrigger>
          <DialogContent className="p-6 sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-lg">Using Core</DialogTitle>
              <DialogDescription>
                Start with a question, a rough idea, or a task you want to work
                through.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2 text-sm leading-6">
              <p>
                <strong>Pick up where you left off.</strong> Conversations are
                saved in this browser. Search or select one in the sidebar.
              </p>
              <p>
                <strong>Let Core do the legwork.</strong> Ask for research,
                weather, or the time. Open the activity details under a response
                to see the tools used.
              </p>
              <p>
                <strong>Stay in control.</strong> Press Enter to send, Shift +
                Enter for a new line, or stop a response at any time.
              </p>
              <p className="text-[13px] text-muted-foreground">
                Tip: Ctrl / ⌘ + B toggles the sidebar.
              </p>
            </div>
          </DialogContent>
        </Dialog>
        <GitHubCredit />
        <p className="px-2 text-[10px] leading-4 text-sidebar-foreground/80">
          Conversations are saved in this browser.
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}
