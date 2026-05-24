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
import {
  DEFAULT_SETTINGS,
  useSettings,
  type RenderSettings,
} from "@/lib/settings";

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

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}

function settingsSummary(s: RenderSettings): string {
  const parts = [
    s.resolution,
    `${s.slideDuration}s slides`,
    `${s.fadeDuration}s fades`,
    `${s.fps}fps`,
  ];
  if (s.recursive) parts.push("recursive");
  return parts.join(" · ");
}

function App() {
  const { state, start, reset } = useSidecar();
  const [settings, setSettings] = useSettings();
  const [folder, setFolder] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  function update<K extends keyof RenderSettings>(
    key: K,
    value: RenderSettings[K],
  ) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

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
    if (!folder) return;
    // Only send fields that differ from default — keeps the CLI args
    // small and lets us evolve defaults without bumping persisted state.
    const overrides: Record<string, unknown> = {};
    if (settings.resolution !== DEFAULT_SETTINGS.resolution) {
      overrides.resolution = settings.resolution;
    }
    if (settings.slideDuration !== DEFAULT_SETTINGS.slideDuration) {
      overrides.slideDuration = settings.slideDuration;
    }
    if (settings.fadeDuration !== DEFAULT_SETTINGS.fadeDuration) {
      overrides.fadeDuration = settings.fadeDuration;
    }
    if (settings.fps !== DEFAULT_SETTINGS.fps) {
      overrides.fps = settings.fps;
    }
    if (settings.recursive !== DEFAULT_SETTINGS.recursive) {
      overrides.recursive = settings.recursive;
    }
    await start(folder, Object.keys(overrides).length ? overrides : undefined);
  }

  const { discovery, estimate, progress, phase, error, running } = state;
  const hasResults = discovery !== null || estimate !== null;

  function truncateMiddle(path: string, max = 80): string {
    if (path.length <= max) return path;
    const half = Math.floor((max - 1) / 2);
    return `${path.slice(0, half)}…${path.slice(-half)}`;
  }

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
                {running ? "Scanning…" : hasResults ? "Re-scan" : "Scan"}
              </Button>
            </div>
            {folder && (
              <p
                className="text-xs text-muted-foreground font-mono truncate"
                title={folder}
              >
                {truncateMiddle(folder)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <button
            type="button"
            onClick={() => setSettingsOpen((v) => !v)}
            className="w-full text-left p-6 flex items-center justify-between hover:bg-muted/30 transition-colors rounded-xl"
            aria-expanded={settingsOpen}
            aria-controls="settings-body"
          >
            <div className="space-y-1">
              <div className="font-semibold leading-none tracking-tight">
                Settings
              </div>
              <div className="text-sm text-muted-foreground">
                {settingsSummary(settings)}
              </div>
            </div>
            <span className="text-muted-foreground text-sm">
              {settingsOpen ? "Hide" : "Edit"}
            </span>
          </button>
          {settingsOpen && (
            <CardContent
              id="settings-body"
              className="border-t pt-6 grid grid-cols-1 md:grid-cols-2 gap-5"
            >
              <Field label="Resolution">
                <select
                  value={settings.resolution}
                  onChange={(e) =>
                    update("resolution", e.target.value as RenderSettings["resolution"])
                  }
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                >
                  <option value="1080p">1080p (1920×1080)</option>
                  <option value="4k">4K (3840×2160)</option>
                </select>
              </Field>
              <Field label="FPS">
                <input
                  type="number"
                  min={15}
                  max={60}
                  step={1}
                  value={settings.fps}
                  onChange={(e) =>
                    update("fps", Number(e.target.value) || DEFAULT_SETTINGS.fps)
                  }
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm tabular-nums"
                />
              </Field>
              <Field label="Slide duration (s)">
                <input
                  type="number"
                  min={0.5}
                  max={30}
                  step={0.5}
                  value={settings.slideDuration}
                  onChange={(e) =>
                    update(
                      "slideDuration",
                      Number(e.target.value) || DEFAULT_SETTINGS.slideDuration,
                    )
                  }
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm tabular-nums"
                />
              </Field>
              <Field label="Fade duration (s)">
                <input
                  type="number"
                  min={0}
                  max={5}
                  step={0.1}
                  value={settings.fadeDuration}
                  onChange={(e) =>
                    update(
                      "fadeDuration",
                      Number(e.target.value) || DEFAULT_SETTINGS.fadeDuration,
                    )
                  }
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm tabular-nums"
                />
              </Field>
              <label className="flex items-center gap-3 md:col-span-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.recursive}
                  onChange={(e) => update("recursive", e.target.checked)}
                  className="h-4 w-4"
                />
                <span>Scan subfolders (recursive)</span>
              </label>
              <div className="md:col-span-2 flex justify-end">
                <Button
                  variant="outline"
                  onClick={() => setSettings(DEFAULT_SETTINGS)}
                >
                  Reset to defaults
                </Button>
              </div>
            </CardContent>
          )}
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
            <CardContent className="grid grid-cols-2 gap-6">
              <Stat
                label="Duration"
                value={formatDuration(estimate.duration_s)}
              />
              <Stat
                label="File size"
                value={formatSize(estimate.size_bytes)}
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
