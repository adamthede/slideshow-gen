mod sidecar;

use serde::Deserialize;
use sidecar::{spawn_sidecar, SidecarState};

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
}

/// Start a scan against one or more folders. For E2 this is always
/// `render --ipc --estimate-only` — real renders are Epic 4. Each folder
/// is forwarded as a separate `--dir` argument to the sidecar CLI.
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
    // started, so this file is never written.
    let throwaway_out = std::env::temp_dir()
        .join("marquee-estimate-only.mp4")
        .to_string_lossy()
        .to_string();

    let mut args: Vec<String> = vec!["render".into(), "--ipc".into()];
    for folder in &folders {
        args.push("--dir".into());
        args.push(folder.clone());
    }
    args.push("-o".into());
    args.push(throwaway_out);
    args.push("--workers".into());
    args.push("1".into());
    args.push("--estimate-only".into());

    if let Some(s) = settings {
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
    }

    spawn_sidecar(&app, args)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(SidecarState::default())
        .invoke_handler(tauri::generate_handler![start_scan])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
