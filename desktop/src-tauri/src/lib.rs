mod sidecar;

use std::process::Command;

use serde::Deserialize;
use sidecar::{cancel_sidecar, spawn_sidecar, SidecarState};

/// Render settings the frontend can override. Each field is optional —
/// `None` means "let the CLI use its default", so the Rust shell never
/// has to track default values itself.
#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ScanSettings {
    /// `"1080p"` or `"4k"` — passed verbatim to `--resolution`.
    resolution: Option<String>,
    slide_duration: Option<f64>,
    fade_duration: Option<f64>,
    fps: Option<u32>,
    recursive: Option<bool>,
    /// Absolute path to a background audio file (mp3/m4a/wav/...).
    audio_track: Option<String>,
    /// Volume 0.0–N for the background track. Only applied when
    /// `audio_track` is also set.
    audio_volume: Option<f64>,
    /// Render-appearance flags — each maps directly to the matching CLI
    /// switch when true.
    static_mode: Option<bool>,
    random_order: Option<bool>,
    no_overlays: Option<bool>,
    no_date: Option<bool>,
    no_location: Option<bool>,
    /// Keep the render's temp directory instead of deleting it (debugging).
    /// Maps to `--keep-temp`; also honored on cancellation.
    keep_temp: Option<bool>,
}

/// Append the `--flag value` pairs for any overridden render settings.
/// Only fields the frontend actually sent (i.e. `Some`) produce flags;
/// everything else falls through to the CLI's own defaults.
fn append_settings(args: &mut Vec<String>, settings: Option<ScanSettings>) {
    let Some(s) = settings else {
        return;
    };
    if let Some(res) = s.resolution {
        args.push("--resolution".into());
        args.push(res);
    }
    if let Some(sd) = s.slide_duration {
        args.push("--slide-duration".into());
        args.push(sd.to_string());
    }
    if let Some(fd) = s.fade_duration {
        args.push("--fade-duration".into());
        args.push(fd.to_string());
    }
    if let Some(fps) = s.fps {
        args.push("--fps".into());
        args.push(fps.to_string());
    }
    if s.recursive.unwrap_or(false) {
        args.push("--recursive".into());
    }
    if let Some(audio) = s.audio_track {
        if !audio.is_empty() {
            args.push("--audio-track".into());
            args.push(audio);
            if let Some(vol) = s.audio_volume {
                args.push("--audio-volume".into());
                args.push(vol.to_string());
            }
        }
    }
    if s.static_mode.unwrap_or(false) {
        args.push("--static".into());
    }
    if s.random_order.unwrap_or(false) {
        args.push("--random".into());
    }
    if s.no_overlays.unwrap_or(false) {
        args.push("--no-overlays".into());
    }
    if s.no_date.unwrap_or(false) {
        args.push("--no-date".into());
    }
    if s.no_location.unwrap_or(false) {
        args.push("--no-location".into());
    }
    if s.keep_temp.unwrap_or(false) {
        args.push("--keep-temp".into());
    }
}

/// Build the full sidecar argument vector for a `render` invocation.
///
/// When `estimate_only` is true (the E2 pre-render summary path) the
/// CLI is forced to `--workers 1` and `--estimate-only`, so it exits
/// right after emitting the estimate without encoding anything. A real
/// render (E4) passes `false`: no worker override (the CLI picks its
/// own default parallelism) and no early exit, so all phases run to a
/// `complete` event.
fn build_args(
    folders: &[String],
    output: &str,
    estimate_only: bool,
    settings: Option<ScanSettings>,
) -> Vec<String> {
    let mut args: Vec<String> = vec!["render".into(), "--ipc".into()];
    for folder in folders {
        args.push("--dir".into());
        args.push(folder.clone());
    }
    args.push("-o".into());
    args.push(output.to_string());
    if estimate_only {
        args.push("--workers".into());
        args.push("1".into());
        args.push("--estimate-only".into());
    }
    append_settings(&mut args, settings);
    args
}

/// Start a pre-render scan against one or more folders. Always runs
/// `render --ipc --estimate-only` — the CLI exits after the estimate
/// without producing an MP4. Real renders go through `start_render`.
///
/// Events are emitted to the frontend on `marquee://sidecar-event`.
#[tauri::command]
async fn start_scan(
    app: tauri::AppHandle,
    folders: Vec<String>,
    settings: Option<ScanSettings>,
) -> Result<(), String> {
    if folders.is_empty() {
        return Err("No folders selected.".into());
    }

    // Throwaway output path. estimate-only exits before any encode is
    // started, so this file is never written. PID keeps it collision-safe.
    let throwaway_out = std::env::temp_dir()
        .join(format!("marquee-estimate-{}.mp4", std::process::id()))
        .to_string_lossy()
        .to_string();

    let args = build_args(&folders, &throwaway_out, true, settings);
    spawn_sidecar(&app, args)
}

/// Start a real render against one or more folders, writing the final
/// MP4 to `output`. Unlike `start_scan` this runs the full three-phase
/// pipeline to completion: no `--estimate-only`, no forced `--workers 1`.
///
/// Events stream to the frontend on `marquee://sidecar-event`, ending
/// with a `complete` event whose `outputs` list the written file(s).
#[tauri::command]
async fn start_render(
    app: tauri::AppHandle,
    folders: Vec<String>,
    output: String,
    settings: Option<ScanSettings>,
) -> Result<(), String> {
    if folders.is_empty() {
        return Err("No folders selected.".into());
    }
    if output.trim().is_empty() {
        return Err("No output destination selected.".into());
    }

    let args = build_args(&folders, &output, false, settings);
    spawn_sidecar(&app, args)
}

/// Reveal a finished output file in Finder (`open -R "$path"`).
///
/// macOS-only by design (see PRD NFR6). Returns the underlying `open`
/// error verbatim so the UI can surface it without prefixing.
#[tauri::command]
fn reveal_in_finder(path: String) -> Result<(), String> {
    if path.trim().is_empty() {
        return Err("No path provided.".into());
    }
    Command::new("open")
        .args(["-R", &path])
        .status()
        .map_err(|e| format!("Failed to invoke `open`: {e}"))
        .and_then(|status| {
            if status.success() {
                Ok(())
            } else {
                Err(format!("`open -R` exited with status {status}"))
            }
        })
}

/// Open the file in QuickTime Player (`open -a "QuickTime Player" "$path"`).
///
/// macOS-only by design (see PRD NFR6). If QuickTime is missing or refuses
/// to open the file, the error from `open` is bubbled up.
#[tauri::command]
fn open_in_quicktime(path: String) -> Result<(), String> {
    if path.trim().is_empty() {
        return Err("No path provided.".into());
    }
    Command::new("open")
        .args(["-a", "QuickTime Player", &path])
        .status()
        .map_err(|e| format!("Failed to invoke `open`: {e}"))
        .and_then(|status| {
            if status.success() {
                Ok(())
            } else {
                Err(format!("`open -a QuickTime Player` exited with status {status}"))
            }
        })
}

/// Cancel the in-flight render. Sends SIGTERM to the sidecar so the engine can
/// reap its FFmpeg children and clean up its temp dir before exiting; a SIGKILL
/// escalation fires only if it doesn't exit within the grace period. The
/// frontend learns the outcome from the `cancelled` event and the `exit`
/// message (which re-enables controls), not from this call returning.
#[tauri::command]
async fn cancel_render(app: tauri::AppHandle) -> Result<(), String> {
    cancel_sidecar(&app)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(SidecarState::default())
        .invoke_handler(tauri::generate_handler![
            start_scan,
            start_render,
            cancel_render,
            reveal_in_finder,
            open_in_quicktime
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    fn folders() -> Vec<String> {
        vec!["/photos/a".into(), "/photos/b".into()]
    }

    fn has_flag(args: &[String], flag: &str) -> bool {
        args.iter().any(|a| a == flag)
    }

    /// The value immediately following the first occurrence of `flag`.
    fn value_after<'a>(args: &'a [String], flag: &str) -> Option<&'a str> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1))
            .map(|s| s.as_str())
    }

    #[test]
    fn estimate_path_forces_workers_and_estimate_only() {
        let args = build_args(&folders(), "/tmp/throwaway.mp4", true, None);
        assert!(has_flag(&args, "--estimate-only"));
        assert_eq!(value_after(&args, "--workers"), Some("1"));
    }

    #[test]
    fn render_path_omits_estimate_only_and_worker_override() {
        let args = build_args(&folders(), "/out/slideshow.mp4", false, None);
        assert!(!has_flag(&args, "--estimate-only"));
        assert!(!has_flag(&args, "--workers"));
    }

    #[test]
    fn render_path_uses_real_output_and_all_dirs() {
        let args = build_args(&folders(), "/out/slideshow.mp4", false, None);
        assert_eq!(value_after(&args, "-o"), Some("/out/slideshow.mp4"));
        // Both folders forwarded as separate --dir arguments.
        let dir_values: Vec<&String> = args
            .iter()
            .enumerate()
            .filter(|(i, _)| i.checked_sub(1).and_then(|p| args.get(p)).map(|s| s == "--dir").unwrap_or(false))
            .map(|(_, v)| v)
            .collect();
        assert_eq!(dir_values, vec!["/photos/a", "/photos/b"]);
        assert!(has_flag(&args, "--ipc"));
        assert_eq!(args.first().map(|s| s.as_str()), Some("render"));
    }

    #[test]
    fn settings_overrides_are_appended_for_renders() {
        let settings = ScanSettings {
            resolution: Some("4k".into()),
            fps: Some(60),
            static_mode: Some(true),
            no_overlays: Some(true),
            audio_track: Some("/music/track.mp3".into()),
            audio_volume: Some(0.5),
            ..Default::default()
        };
        let args = build_args(&folders(), "/out/slideshow.mp4", false, Some(settings));
        assert_eq!(value_after(&args, "--resolution"), Some("4k"));
        assert_eq!(value_after(&args, "--fps"), Some("60"));
        assert!(has_flag(&args, "--static"));
        assert!(has_flag(&args, "--no-overlays"));
        assert_eq!(value_after(&args, "--audio-track"), Some("/music/track.mp3"));
        assert_eq!(value_after(&args, "--audio-volume"), Some("0.5"));
    }

    #[test]
    fn keep_temp_flag_appended_when_set() {
        let settings = ScanSettings {
            keep_temp: Some(true),
            ..Default::default()
        };
        let args = build_args(&folders(), "/out/slideshow.mp4", false, Some(settings));
        assert!(has_flag(&args, "--keep-temp"));
    }

    #[test]
    fn keep_temp_flag_absent_by_default() {
        let args = build_args(&folders(), "/out/slideshow.mp4", false, None);
        assert!(!has_flag(&args, "--keep-temp"));
        let settings = ScanSettings {
            keep_temp: Some(false),
            ..Default::default()
        };
        let args = build_args(&folders(), "/out/slideshow.mp4", false, Some(settings));
        assert!(!has_flag(&args, "--keep-temp"));
    }

    #[test]
    fn audio_volume_dropped_when_no_track() {
        let settings = ScanSettings {
            audio_volume: Some(0.5),
            ..Default::default()
        };
        let args = build_args(&folders(), "/out/slideshow.mp4", false, Some(settings));
        // Volume without a track is meaningless — neither flag should appear.
        assert!(!has_flag(&args, "--audio-track"));
        assert!(!has_flag(&args, "--audio-volume"));
    }
}
