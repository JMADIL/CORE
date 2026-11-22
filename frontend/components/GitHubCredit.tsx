import { ArrowUpRight, GitBranch } from "lucide-react";

export function GitHubCredit() {
  return (
    <a
      href="https://github.com/JMADIL"
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Built by JMADIL — view GitHub profile (opens in a new tab)"
      className="group flex items-center gap-2.5 rounded-xl px-2 py-2 text-sidebar-foreground/80 transition-colors duration-200 hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sidebar-ring"
    >
      <GitBranch className="size-4 shrink-0" aria-hidden="true" />
      <span className="text-xs">
        Built by <span className="font-medium">@JMADIL</span>
      </span>
      <ArrowUpRight
        className="ml-auto size-3.5 shrink-0 motion-safe:transition-transform motion-safe:group-hover:-translate-y-0.5 motion-safe:group-hover:translate-x-0.5"
        aria-hidden="true"
      />
    </a>
  );
}
