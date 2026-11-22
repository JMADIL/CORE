import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

export function useBackendHealth() {
  const [health, setHealth] = useState<{
    model: string;
    status: "connecting" | "online" | "offline";
  }>({ model: "", status: "connecting" });
  useEffect(() => {
    const controller = new AbortController();
    let inFlight = false;
    const refresh = async () => {
      if (inFlight || controller.signal.aborted) return;
      inFlight = true;
      try {
        const result = await checkHealth(
          AbortSignal.any([controller.signal, AbortSignal.timeout(5000)]),
        );
        if (!controller.signal.aborted)
          setHealth({
            model: result.model,
            status: result.status === "ok" ? "online" : "offline",
          });
      } catch {
        if (!controller.signal.aborted)
          setHealth((previous) => ({ ...previous, status: "offline" }));
      } finally {
        inFlight = false;
      }
    };
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, 10000);
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    window.addEventListener("focus", refreshWhenVisible);
    window.addEventListener("online", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      controller.abort();
      clearInterval(timer);
      window.removeEventListener("focus", refreshWhenVisible);
      window.removeEventListener("online", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);
  return health;
}
