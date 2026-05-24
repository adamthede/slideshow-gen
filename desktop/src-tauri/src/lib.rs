mod sidecar;

use sidecar::{spawn_sidecar, SidecarState};

/// Start a scan against a folder. For E1 this is always
/// `render --ipc --estimate-only` against the chosen folder — proves
/// the full sidecar/IPC pipeline without rendering a real MP4.
///
/// Events are emitted to the frontend on `marquee://sidecar-event`.
#[tauri::command]
async fn start_scan(app: tauri::AppHandle, folder: String) -> Result<(), String> {
    // Throwaway output path. estimate-only exits before any encode is
    // started, so this file is never written.
    let throwaway_out = std::env::temp_dir()
        .join("marquee-estimate-only.mp4")
        .to_string_lossy()
        .to_string();

    let args = vec![
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
