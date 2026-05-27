import { useEffect, useState } from "react";
import { open, save } from "@tauri-apps/plugin-dialog";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
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
import { deriveDefaultBaseName } from "@/lib/output-name";
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
      if (event.duplicates_detected !== undefined && event.duplicates_detected > 0) {
        msg += ` · ${event.duplicates_detected} dupes`;
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

function Toggle({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label
      className={
        "flex items-center gap-3 text-sm " +
        (disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer")
      }
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="h-4 w-4"
      />
      <span>{label}</span>
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
  if (s.staticMode) parts.push("static");
  if (s.randomOrder) parts.push("random");
  if (s.noOverlays) parts.push("no overlays");
  else {
    if (s.noDate) parts.push("no date");
    if (s.noLocation) parts.push("no location");
  }
  if (s.audioTrack) {
    const name = s.audioTrack.split("/").pop() ?? "audio";
    parts.push(`audio: ${name}`);
  }
  return parts.join(" · ");
}

function App() {
  const { state, start, startRender, reset } = useSidecar();
  const [settings, setSettings] = useSettings();
  const [folders, setFolders] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Output destination is transient session state, not persisted: a stale
  // absolute path surviving across launches would be a footgun.
  const [outputPath, setOutputPath] = useState<string | null>(null);
  // Tracks whether the in-flight (or last) run was a real render vs a
  // pre-render scan, so the UI shows the right progress/result copy.
  const [isRendering, setIsRendering] = useState(false);
  // User-facing output name (no extension). Empty + untouched means "follow
  // the folder-derived default"; once the user types, `nameTouched` pins
  // their value so it stops tracking the folders.
  const [name, setName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);

  // The default base name derived from the source folders (folder name for a
  // single folder, date-stamped otherwise). Stable per render: a single
  // folder yields a constant string; the date case is constant within a day.
  const derivedBaseName = deriveDefaultBaseName(folders);
  // What we actually save as: the user's name if they typed one, else the
  // derived default. Never empty.
  const effectiveBaseName = name.trim() || derivedBaseName;

  // Keep the field showing the folder-derived default until the user edits it.
  useEffect(() => {
    if (!nameTouched) setName(derivedBaseName);
  }, [derivedBaseName, nameTouched]);

  function update<K extends keyof RenderSettings>(
    key: K,
    value: RenderSettings[K],
  ) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  function addFolders(paths: string[]) {
    if (paths.length === 0) return;
    // No-op while a scan is running. Both the drop handler and the
    // picker call into here; without this guard the in-flight scan's
    // results would be reset() out from under the user.
    if (state.running) return;
    setFolders((prev) => {
      const seen = new Set(prev);
      const next = [...prev];
      for (const p of paths) {
        if (!seen.has(p)) {
          next.push(p);
          seen.add(p);
        }
      }
      return next;
    });
    reset();
  }

  function removeFolder(path: string) {
    setFolders((prev) => prev.filter((p) => p !== path));
    reset();
  }

  useEffect(() => {
    // Guard against the unmount-before-listener-registered race: if cleanup
    // runs before the onDragDropEvent promise resolves, set a flag and
    // invoke the unlisten as soon as we receive it.
    let cancelled = false;
    let unlisten: (() => void) | null = null;
    getCurrentWebview()
      .onDragDropEvent((event) => {
        if (event.payload.type === "over") {
          setDragging(true);
        } else if (event.payload.type === "leave") {
          setDragging(false);
        } else if (event.payload.type === "drop") {
          setDragging(false);
          addFolders(event.payload.paths);
        }
      })
      .then((fn) => {
        if (cancelled) {
          fn();
        } else {
          unlisten = fn;
        }
      })
      .catch((err) => {
        // Registration failure (e.g. webview API not ready) shouldn't be
        // a silent unhandled rejection. Log it; drag-drop will be unavailable
        // but the picker button still works.
        console.error("[marquee] failed to register drag-drop listener:", err);
      });
    return () => {
      cancelled = true;
      unlisten?.();
    };
    // addFolders/reset are stable enough — re-running this effect on
    // every render would re-register the webview listener.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function pickFolder() {
    const selected = await open({ directory: true, multiple: true });
    if (Array.isArray(selected)) {
      addFolders(selected);
    } else if (typeof selected === "string") {
      addFolders([selected]);
    }
  }

  async function pickAudio() {
    const selected = await open({
      directory: false,
      multiple: false,
      filters: [
        { name: "Audio", extensions: ["mp3", "m4a", "wav", "aac", "flac", "ogg"] },
      ],
    });
    if (typeof selected === "string") {
      update("audioTrack", selected);
    }
  }

  // Only send fields that differ from default — keeps the CLI args small
  // and lets us evolve defaults without bumping persisted state. Shared by
  // the scan (estimate-only) and render paths.
  function buildOverrides(): Record<string, unknown> | undefined {
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
    if (settings.audioTrack) {
      overrides.audioTrack = settings.audioTrack;
      if (settings.audioVolume !== DEFAULT_SETTINGS.audioVolume) {
        overrides.audioVolume = settings.audioVolume;
      }
    }
    if (settings.staticMode) overrides.staticMode = true;
    if (settings.randomOrder) overrides.randomOrder = true;
    if (settings.noOverlays) overrides.noOverlays = true;
    if (settings.noDate) overrides.noDate = true;
    if (settings.noLocation) overrides.noLocation = true;
    return Object.keys(overrides).length ? overrides : undefined;
  }

  async function runScan() {
    if (folders.length === 0 || state.running) return;
    setIsRendering(false);
    await start(folders, buildOverrides());
  }

  async function pickOutput(): Promise<string | null> {
    // Filename comes from the name field; reuse the last-used directory (if
    // any) so repeat renders stay put. A unique name means no overwrite
    // prompt; reusing a name still surfaces the OS overwrite warning.
    const fileName = `${effectiveBaseName}.mp4`;
    let defaultPath = fileName;
    if (outputPath) {
      const slash = outputPath.lastIndexOf("/");
      if (slash !== -1) defaultPath = outputPath.slice(0, slash + 1) + fileName;
    }
    const selected = await save({
      title: "Save slideshow as",
      defaultPath,
      filters: [{ name: "Video", extensions: ["mp4"] }],
    });
    if (typeof selected === "string") {
      setOutputPath(selected);
      return selected;
    }
    return null;
  }

  async function runRender() {
    if (folders.length === 0 || state.running) return;
    // Always confirm the destination via the save dialog — pre-filled with
    // the last path, so it's one keypress to confirm, but rendering is heavy
    // and the OS overwrite warning prevents silently clobbering a prior render.
    const destination = await pickOutput();
    if (!destination) return;
    setIsRendering(true);
    await startRender(folders, destination, buildOverrides());
  }

  // Full reset back to the empty drop-zone state for a fresh slideshow:
  // clears folders, output destination, and all sidecar results. Settings
  // are intentionally preserved (they persist across launches and are the
  // user's standing preferences — the settings drawer has its own
  // "Reset to defaults"). No-op mid-render so we never reset under a live job.
  function resetAll() {
    if (state.running) return;
    setFolders([]);
    setOutputPath(null);
    setIsRendering(false);
    setName("");
    setNameTouched(false);
    reset();
  }

  const { discovery, estimate, complete, progress, phase, error, running } =
    state;
  const hasResults = discovery !== null || estimate !== null;
  // `complete` arrives before the process exits (which is what flips
  // `running` off). Gate on `!complete` so the card swaps to "Render
  // complete" immediately, while controls stay disabled until `exit`.
  const rendering = running && isRendering && !complete;

  function truncateMiddle(path: string, max = 80): string {
    if (path.length <= max) return path;
    const half = Math.floor((max - 1) / 2);
    // path.slice(-0) returns the whole string in JS (because -0 === 0).
    // Use path.length - half so half=0 correctly yields an empty tail.
    return `${path.slice(0, half)}…${path.slice(path.length - half)}`;
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Marquee</h1>
          <p className="text-sm text-muted-foreground">
            Pick folders of photos to see a pre-render summary.
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
            <CardTitle>Folders</CardTitle>
            <CardDescription>
              Drop folders anywhere on the window, or use the button to add them.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <Button onClick={pickFolder} variant="outline" disabled={running}>
                {folders.length === 0 ? "Choose folder" : "Add folder"}
              </Button>
              <Button
                onClick={runScan}
                variant="outline"
                disabled={folders.length === 0 || running}
              >
                {running && !isRendering
                  ? "Scanning…"
                  : hasResults
                    ? "Re-scan"
                    : "Scan"}
              </Button>
              <Button
                onClick={runRender}
                disabled={folders.length === 0 || running}
              >
                {rendering ? "Rendering…" : "Render"}
              </Button>
              {folders.length > 1 && (
                <span className="text-xs text-muted-foreground">
                  {folders.length} folders
                </span>
              )}
            </div>
            <div className="space-y-1.5">
              <label
                htmlFor="slideshow-name"
                className="text-xs font-medium text-muted-foreground"
              >
                Name your slideshow
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="slideshow-name"
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setNameTouched(true);
                    setName(e.target.value);
                  }}
                  placeholder={derivedBaseName}
                  disabled={running}
                  className="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
                />
                <span className="text-sm text-muted-foreground">.mp4</span>
              </div>
            </div>
            <div className="flex items-center gap-3 flex-wrap text-xs">
              <Button
                onClick={pickOutput}
                variant="outline"
                size="sm"
                disabled={running}
              >
                {outputPath ? "Change destination" : "Choose destination…"}
              </Button>
              {outputPath ? (
                <span
                  className="font-mono text-muted-foreground truncate"
                  title={outputPath}
                >
                  {truncateMiddle(outputPath, 64)}
                </span>
              ) : (
                <span className="text-muted-foreground">
                  Render will ask where to save.
                </span>
              )}
            </div>
            {folders.length > 0 && (
              <ul className="space-y-1">
                {folders.map((p) => (
                  <li
                    key={p}
                    className="flex items-center justify-between gap-3 text-xs font-mono bg-muted/40 rounded-md px-3 py-2"
                  >
                    <span className="truncate" title={p}>
                      {truncateMiddle(p)}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeFolder(p)}
                      disabled={running}
                      className="shrink-0 text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      aria-label={`Remove ${p}`}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
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
                  onChange={(e) => {
                    // Explicit isFinite check so a user-typed `0` (valid:
                    // no crossfade) survives instead of being treated as
                    // falsy and reset to DEFAULT.
                    const parsed = Number(e.target.value);
                    update(
                      "fadeDuration",
                      Number.isFinite(parsed) ? parsed : DEFAULT_SETTINGS.fadeDuration,
                    );
                  }}
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

              <div className="md:col-span-2 border-t pt-5 space-y-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Appearance
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <Toggle
                    label="Static (skip Ken Burns motion)"
                    checked={settings.staticMode}
                    onChange={(v) => update("staticMode", v)}
                  />
                  <Toggle
                    label="Random order"
                    checked={settings.randomOrder}
                    onChange={(v) => update("randomOrder", v)}
                  />
                  <Toggle
                    label="Hide all overlays"
                    checked={settings.noOverlays}
                    onChange={(v) => update("noOverlays", v)}
                  />
                  <Toggle
                    label="Hide date overlay"
                    checked={settings.noDate}
                    onChange={(v) => update("noDate", v)}
                    disabled={settings.noOverlays}
                  />
                  <Toggle
                    label="Hide location overlay"
                    checked={settings.noLocation}
                    onChange={(v) => update("noLocation", v)}
                    disabled={settings.noOverlays}
                  />
                </div>
              </div>

              <div className="md:col-span-2 border-t pt-5 space-y-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Background audio
                </div>
                <div className="flex items-center gap-3">
                  <Button variant="outline" onClick={pickAudio}>
                    {settings.audioTrack ? "Change track" : "Choose audio file"}
                  </Button>
                  {settings.audioTrack && (
                    <Button
                      variant="outline"
                      onClick={() => update("audioTrack", null)}
                    >
                      Remove
                    </Button>
                  )}
                  {settings.audioTrack && (
                    <span
                      className="text-xs font-mono text-muted-foreground truncate"
                      title={settings.audioTrack}
                    >
                      {settings.audioTrack.split("/").pop()}
                    </span>
                  )}
                </div>
                {settings.audioTrack && (
                  <Field label={`Volume (${settings.audioVolume.toFixed(2)}×)`}>
                    <input
                      type="range"
                      min={0}
                      max={2}
                      step={0.05}
                      list="audio-volume-ticks"
                      value={settings.audioVolume}
                      onChange={(e) =>
                        update("audioVolume", Number(e.target.value))
                      }
                      className="w-full"
                    />
                    <datalist id="audio-volume-ticks">
                      <option value="0" />
                      <option value="1" />
                      <option value="2" />
                    </datalist>
                    <div className="flex justify-between text-[10px] uppercase tracking-wide text-muted-foreground -mt-1">
                      <span>0×</span>
                      <span>1×</span>
                      <span>2×</span>
                    </div>
                  </Field>
                )}
              </div>

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

        {running && !isRendering && !hasResults && (
          <Card>
            <CardHeader>
              <CardTitle>Scanning…</CardTitle>
              <CardDescription>
                {progress
                  ? `${progress.done.toLocaleString()} / ${progress.total.toLocaleString()} files`
                  : phase
                    ? `Starting ${phase}…`
                    : "Starting up…"}
              </CardDescription>
            </CardHeader>
            {progress && progress.total > 0 && (
              <CardContent>
                <div
                  className="h-2 w-full overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={progress.total}
                  aria-valuenow={progress.done}
                >
                  <div
                    className="h-full bg-primary transition-[width] duration-150 ease-out"
                    style={{
                      width: `${Math.min(100, (progress.done / progress.total) * 100)}%`,
                    }}
                  />
                </div>
              </CardContent>
            )}
          </Card>
        )}

        {rendering && (
          <Card>
            <CardHeader>
              <CardTitle>Rendering…</CardTitle>
              <CardDescription>
                {phase ? `Phase: ${phase}` : "Starting render…"}
                {progress && progress.total > 0
                  ? ` · ${progress.done.toLocaleString()} / ${progress.total.toLocaleString()}`
                  : ""}
              </CardDescription>
            </CardHeader>
            {progress && progress.total > 0 && (
              <CardContent>
                <div
                  className="h-2 w-full overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={progress.total}
                  aria-valuenow={progress.done}
                >
                  <div
                    className="h-full bg-primary transition-[width] duration-150 ease-out"
                    style={{
                      width: `${Math.min(100, (progress.done / progress.total) * 100)}%`,
                    }}
                  />
                </div>
              </CardContent>
            )}
          </Card>
        )}

        {complete && (
          <Card className="border-primary">
            <CardHeader>
              <CardTitle>Render complete</CardTitle>
              <CardDescription>
                Finished in {formatDuration(complete.elapsed_s)}.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {complete.outputs.map((o) => (
                <div
                  key={o.path}
                  className="flex items-center justify-between gap-3 text-xs bg-muted/40 rounded-md px-3 py-2"
                >
                  <span className="font-mono truncate" title={o.path}>
                    {truncateMiddle(o.path)}
                  </span>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="font-mono text-muted-foreground">
                      {formatSize(o.size_bytes)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        revealItemInDir(o.path).catch((err) =>
                          console.error("[marquee] reveal failed:", err),
                        )
                      }
                    >
                      Reveal in Finder
                    </Button>
                  </div>
                </div>
              ))}
              <div className="flex items-center gap-3 flex-wrap pt-2">
                <Button onClick={runRender} disabled={running}>
                  Render again
                </Button>
                <Button
                  variant="outline"
                  onClick={resetAll}
                  disabled={running}
                >
                  New slideshow
                </Button>
                <span className="text-xs text-muted-foreground">
                  Render again uses the same folders &amp; settings · New
                  slideshow clears everything.
                </span>
              </div>
            </CardContent>
          </Card>
        )}

        {error && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Error</CardTitle>
              <CardDescription className="font-mono">{error}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" onClick={resetAll} disabled={running}>
                New slideshow
              </Button>
            </CardContent>
          </Card>
        )}

        {discovery && (
          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <CardDescription>
                What we found across the selected folder{folders.length === 1 ? "" : "s"}.
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
                  discovery.duplicates_detected !== undefined
                    ? discovery.duplicates_detected.toLocaleString()
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
