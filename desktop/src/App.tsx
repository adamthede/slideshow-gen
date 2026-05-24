import { useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSidecar } from "@/hooks/useSidecar";
import type { SidecarEvent } from "@/lib/sidecar-events";

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m ${s}s`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

function summarize(event: SidecarEvent): string {
  switch (event.type) {
    case "started":
      return `started · ${event.config.resolution ?? "?"} · slide ${event.config.slide_duration}s`;
    case "phase_started":
      return `phase: ${event.phase}${event.total !== null ? ` (${event.total})` : ""}`;
    case "phase_complete":
      return `phase complete: ${event.phase}${event.message ? ` — ${event.message}` : ""}`;
    case "discovery_complete":
      return `discovery: ${event.images} images, ${event.videos} videos`;
    case "estimate":
      return `estimate: ${formatDuration(event.duration_s)} · ${formatSize(event.size_bytes)}`;
    case "progress":
      return `progress: ${event.phase} ${event.done}/${event.total}`;
    case "info":
      return `info: ${event.message}`;
    case "warning":
      return `warning: ${event.message}`;
    case "error":
      return `error: ${event.message}`;
    case "complete":
      return `complete: ${event.outputs.length} output(s), ${formatDuration(event.elapsed_s)}`;
  }
}

function App() {
  const { state, start, reset } = useSidecar();
  const [folder, setFolder] = useState<string | null>(null);

  async function pickFolder() {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected === "string") {
      setFolder(selected);
      reset();
    }
  }

  async function runScan() {
    if (folder) await start(folder);
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Marquee</h1>
          <p className="text-sm text-muted-foreground">
            Hello, Marquee — Epic 1 sidecar pipe verification.
          </p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Folder</CardTitle>
            <CardDescription>
              Pick a folder of photos. Marquee runs the sidecar in{" "}
              <code className="text-xs">--estimate-only</code> mode and streams
              the IPC events back into the app.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <Button onClick={pickFolder} variant="outline">
                Choose folder
              </Button>
              <Button
                onClick={runScan}
                disabled={!folder || state.running}
              >
                {state.running ? "Scanning…" : "Run scan"}
              </Button>
            </div>
            {folder && (
              <p className="text-xs text-muted-foreground break-all">
                {folder}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
            <CardDescription>
              Live state derived from the sidecar event stream.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>
              <span className="text-muted-foreground">Phase:</span>{" "}
              <span className="font-mono">{state.phase ?? "—"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Progress:</span>{" "}
              <span className="font-mono">
                {state.progress
                  ? `${state.progress.phase} ${state.progress.done}/${state.progress.total}`
                  : "—"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Estimate:</span>{" "}
              <span className="font-mono">
                {state.estimate
                  ? `${formatDuration(state.estimate.duration_s)} · ${formatSize(state.estimate.size_bytes)}`
                  : "—"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Done:</span>{" "}
              <span className="font-mono">
                {state.done ? "yes" : "no"}
                {state.exitCode !== null && ` (exit ${state.exitCode})`}
              </span>
            </div>
            {state.error && (
              <div className="text-destructive">
                <span className="text-muted-foreground">Error:</span>{" "}
                <span className="font-mono">{state.error}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Event log</CardTitle>
            <CardDescription>
              Raw JSON-line stream from the sidecar.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              role="log"
              aria-live="polite"
              className="text-xs bg-muted/40 rounded-md p-3 max-h-96 overflow-auto font-mono whitespace-pre-wrap"
            >
              {state.events.length === 0
                ? "(no events yet — pick a folder and click Run scan)"
                : state.events.map((e, i) => (
                    <div key={i}>{summarize(e)}</div>
                  ))}
            </div>
            {state.diagnostics.length > 0 && (
              <details className="mt-3 text-xs">
                <summary className="cursor-pointer text-muted-foreground">
                  Diagnostics ({state.diagnostics.length})
                </summary>
                <div className="mt-2 bg-muted/40 rounded-md p-3 max-h-48 overflow-auto font-mono whitespace-pre-wrap">
                  {state.diagnostics.map((d, i) => (
                    <div key={i}>
                      [{d.source}] {d.line}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

export default App;
