"use client";

import { useState } from "react";
import { AudioLines, Check, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { elevenLabsConnection } from "@/lib/api";

export function ElevenLabsConnection() {
  const [connected, setConnected] = useState(false);
  const [shared, setShared] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function update(method: "GET" | "POST" | "DELETE" = "GET") {
    setBusy(true);
    setError("");
    try {
      const result = await elevenLabsConnection(method);
      if (result.url) {
        window.location.assign(result.url);
        return;
      }
      setConnected(!!result.connected);
      setShared(result.mode === "shared");
      setEnabled(!!result.enabled);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not connect to ElevenLabs.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      onOpenChange={(open) => {
        if (open) void update();
      }}
    >
      <DialogTrigger
        render={
          <Button
            variant="ghost"
            className="w-full justify-start gap-2.5 px-2 text-[13px] text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground dark:hover:bg-sidebar-accent"
          />
        }
      >
        <AudioLines className="size-3.5" />
        ElevenLabs
      </DialogTrigger>
      <DialogContent className="p-6 sm:max-w-md">
        <DialogHeader>
          <DialogTitle>ElevenLabs</DialogTitle>
          <DialogDescription>
            {shared
              ? "Try media generation using Core’s shared ElevenLabs credits."
              : "Create images, speech, music, sound effects, and video through your ElevenLabs account."}
          </DialogDescription>
        </DialogHeader>
        <p className="text-sm leading-6 text-muted-foreground">
          {shared
            ? "No ElevenLabs account or sign-in is needed. Ask Core to create media. Public demo limits apply."
            : "Generations use your ElevenLabs credits. Sign-in alone does not generate media. This connection belongs to this browser; other users connect their own accounts."}
        </p>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          {busy ? (
            <p
              role="status"
              className="flex items-center gap-2 text-sm text-muted-foreground"
            >
              <LoaderCircle className="size-4 animate-spin" />
              Checking connection…
            </p>
          ) : shared ? (
            <p role="status" className="flex items-center gap-2 text-sm">
              {connected && <Check className="size-4 text-emerald-600" />}
              {connected
                ? "Shared demo ready"
                : "The shared demo is being prepared. Please try again later."}
            </p>
          ) : connected ? (
            <>
              <span role="status" className="flex items-center gap-2 text-sm">
                <Check className="size-4 text-emerald-600" />
                Connected
              </span>
              <Button
                variant="outline"
                className="ml-auto"
                onClick={() => void update("DELETE")}
              >
                Disconnect ElevenLabs
              </Button>
            </>
          ) : enabled ? (
            <Button onClick={() => void update("POST")}>
              Connect ElevenLabs
            </Button>
          ) : !error ? (
            <p role="status" className="text-sm text-muted-foreground">
              ElevenLabs is not configured on this deployment.
            </p>
          ) : null}
        </div>
        {!busy && error && (
          <Button variant="outline" onClick={() => void update()}>
            Check again
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}
