import { Button } from "@/components/ui/button";
import { NotebookPen, Telescope, Waypoints } from "lucide-react";

const suggestions = [
  {
    title: "Write",
    icon: NotebookPen,
    tone: "write",
    prompt: "Help me turn a rough idea into a clear first draft.",
  },
  {
    title: "Research",
    icon: Telescope,
    tone: "research",
    prompt:
      "Search arXiv for recent papers about AI agents and summarize the key findings.",
  },
  {
    title: "Plan",
    icon: Waypoints,
    tone: "plan",
    prompt:
      "Help me plan a project step-by-step, starting with the right questions.",
  },
];

export function WelcomeScreen({
  disabled,
  onSuggestion,
}: {
  disabled: boolean;
  onSuggestion: (prompt: string) => void;
}) {
  return (
    <section
      className="flex flex-1 flex-col items-center justify-center px-5 py-12 text-center"
      aria-labelledby="welcome-title"
    >
      <h1
        id="welcome-title"
        className="welcome-reveal text-[76px] font-semibold leading-none tracking-[-0.055em] text-brand sm:text-[104px]"
      >
        <span className="welcome-logo">Core</span>
      </h1>
      <p
        className="welcome-reveal mt-5 max-w-sm text-base font-medium leading-6 text-foreground sm:max-w-none sm:text-lg"
        style={{ animationDelay: "70ms" }}
      >
        Collaborative Orchestration &amp; Reasoning Engine
      </p>
      <p
        className="welcome-reveal mt-3 max-w-md text-[15px] leading-7 text-muted-foreground"
        style={{ animationDelay: "140ms" }}
      >
        One conversation for research, writing, and planning. Core coordinates
        AI agents and tools to find information, work through ideas, and bring
        the results together.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {suggestions.map(({ title, prompt, icon: Icon, tone }, index) => (
          <Button
            key={title}
            variant="outline"
            disabled={disabled}
            onClick={() => onSuggestion(prompt)}
            data-tone={tone}
            className="welcome-shortcut welcome-reveal h-11 gap-2.5 rounded-[14px] pl-2.5 pr-3.5 text-[13px] font-medium shadow-none"
            style={{ animationDelay: `${210 + index * 60}ms` }}
          >
            <span className="welcome-icon-badge" aria-hidden="true">
              <Icon className="welcome-shortcut-icon size-4!" strokeWidth={1.7} />
            </span>
            {title}
          </Button>
        ))}
      </div>
    </section>
  );
}
