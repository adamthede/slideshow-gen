import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWebview } from "@tauri-apps/api/webview";
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

function formatDate(iso: string): string {
  // Accept "2020-01-15" or "2020-01-15T15:54:41" — drop the time portion.
  return iso.slice(0, 10);
}

function summarize(event: SidecarEvent): string {
  switch (event.type) {
    case "started": {
      const res = event.config.resolution ?? "?";
      const slide = event.config.slide_duration;
      const slideStr = typeof slide === "number" ? `${slide}s` : "?";
      return `started · ${res} · slide ${slideStr}`;
    }
    case "phase_started":
      return `phase: ${event.phase}${event.total != null ? ` (${event.total})` : ""}`;
    case "phase_complete":
      return `phase complete: ${event.phase}${event.message ? ` — ${event.message}` : ""}`;
    case "discovery_complete": {
      let msg = `discovery: ${event.images} images, ${event.videos} videos`;
      if (event.date_range) {
        msg += ` · ${formatDate(event.date_range.earliest)} to ${formatDate(event.date_range.latest)}`;
      }
      if (event.gps_coverage_percent !== undefined) {
        msg += ` · ${event.gps_coverage_percent.toFixed(0)}% GPS`;
      }
      if (event.duplicates_removed !== undefined && event.duplicates_removed > 0) {
        msg += ` · ${event.duplicates_removed} dupes`;
      }
      return msg;
    }
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
    default: {
      const unknown = event as { type?: unknown };
      return `unknown event: ${JSON.stringify(unknown)}`;
    }
  }
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-2xl font-semibold tabular-nums">{value}</span>
    </div>
  );
}

function App() {
  const { state, start, reset } = useSidecar();
  const [folder, setFolder] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    getCurrentWebview()
      .onDragDropEvent((event) => {
        if (event.payload.type === "over") {
          setDragging(true);
        } else if (event.payload.type === "leave") {
          setDragging(false);
        } else if (event.payload.type === "drop") {
          setDragging(false);
          const first = event.payload.paths[0];
          if (first) {
            setFolder(first);
            reset();
          }
        }
      })
      .then((fn) => {
        unlisten = fn;
      });
    return () => {
      unlisten?.();
    };
  }, [reset]);

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

  const { discovery, estimate, progress, phase, error, running, done } = state;
  const hasResults = discovery !== null || estimate !== null;

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Marquee</h1>
          <p className="text-sm text-muted-foreground">
            Pick a folder of photos to see a pre-render summary.
          </p>
        </header>

        <Card
          className={
            dragging
              ? "border-primary border-2 border-dashed bg-primary/5 transition-colors"
              : "border-dashed transition-colors"
          }
        >
          <CardHeader>
            <CardTitle>Folder</CardTitle>
            <CardDescription>
              Drop a folder anywhere on the window, or click below to choose one.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <Button onClick={pickFolder} variant="outline">
                Choose folder
              </Button>
              <Button onClick={runScan} disabled={!folder || running}>
                {running ? "Scanning…" : "Scan"}
              </Button>
            </div>
            {folder && (
              <p className="text-xs text-muted-foreground break-all font-mono">
                {folder}
              </p>
            )}
          </CardContent>
        </Card>

        {running && !hasResults && (
          <Card>
            <CardHeader>
              <CardTitle>Scanning…</CardTitle>
              <CardDescription>
                {phase
                  ? `Phase: ${phase}${progress ? ` (${progress.done}/${progress.total})` : ""}`
                  : "Starting up…"}
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {error && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Error</CardTitle>
              <CardDescription className="font-mono">{error}</CardDescription>
            </CardHeader>
          </Card>
        )}

        {discovery && (
          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <CardDescription>
                What we found in the folder.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <Stat label="Images" value={discovery.images.toLocaleString()} />
              <Stat label="Videos" value={discovery.videos.toLocaleString()} />
              <Stat
                label="GPS coverage"
                value={
                  discovery.gps_coverage_percent !== undefined
                    ? `${discovery.gps_coverage_percent.toFixed(0)}%`
                    : "—"
                }
              />
              <Stat
                label="Duplicates"
                value={
                  discovery.duplicates_removed !== undefined
                    ? discovery.duplicates_removed.toLocaleString()
                    : "—"
                }
              />
              {discovery.date_range && (
                <div className="col-span-2 md:col-span-4 flex flex-col gap-1 pt-2 border-t">
                  <span className="text-xs uppercase tracking-wide text-muted-foreground">
                    Date range
                  </span>
                  <span className="text-sm font-mono">
                    {formatDate(discovery.date_range.earliest)} →{" "}
                    {formatDate(discovery.date_range.latest)}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {estimate && (
          <Card>
            <CardHeader>
              <CardTitle>Estimates</CardTitle>
              <CardDescription>
                Predicted output (within ±20% on typical inputs).
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-6">
              <Stat
                label="Duration"
                value={formatDuration(estimate.duration_s)}
              />
              <Stat
                label="File size"
                value={formatSize(estimate.size_bytes)}
              />
              <Stat
                label="Status"
                value={done ? "ready" : running ? "scanning" : "idle"}
              />
            </CardContent>
          </Card>
        )}

        {(state.events.length > 0 || state.diagnostics.length > 0) && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground py-2">
              Diagnostics ({state.events.length} events
              {state.diagnostics.length > 0
                ? `, ${state.diagnostics.length} raw lines`
                : ""}
              )
            </summary>
            <div className="mt-2 space-y-2">
              <div
                role="log"
                aria-live="polite"
                className="bg-muted/40 rounded-md p-3 max-h-64 overflow-auto font-mono whitespace-pre-wrap"
              >
                {state.events.map((e, i) => (
                  <div key={i}>{summarize(e)}</div>
                ))}
              </div>
              {state.diagnostics.length > 0 && (
                <div className="bg-muted/40 rounded-md p-3 max-h-48 overflow-auto font-mono whitespace-pre-wrap">
                  {state.diagnostics.map((d, i) => (
                    <div key={i}>
                      [{d.source}] {d.line}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </details>
        )}
      </div>
    </main>
  );
}

export default App;
