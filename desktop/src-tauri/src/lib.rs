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
}

/// Start a scan against a folder. For E2 this is always
/// `render --ipc --estimate-only` — real renders are Epic 4.
///
/// Events are emitted to the frontend on `marquee://sidecar-event`.
#[tauri::command]
async fn start_scan(
    app: tauri::AppHandle,
    folder: String,
    settings: Option<ScanSettings>,
) -> Result<(), String> {
    // Throwaway output path. estimate-only exits before any encode is
    // started, so this file is never written.
    let throwaway_out = std::env::temp_dir()
        .join("marquee-estimate-only.mp4")
        .to_string_lossy()
        .to_string();

    let mut args = vec![
        "render".into(),
        "--ipc".into(),
        "--dir".into(),
        folder,
        "-o".into(),
        throwaway_out,
        "--workers".into(),
        "1".into(),
        "--estimate-only".into(),
    ];

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
