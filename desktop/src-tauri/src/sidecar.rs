//! Sidecar bridge: spawn the frozen `slideshow-gen` CLI, parse its
//! JSON-line IPC events on stdout, and forward each as a Tauri event
//! to the frontend.
//!
//! The protocol is documented in `docs/sidecar-protocol.md` (repo root)
//! and locked by `tests/test_ipc_protocol.py`. Event types: `started`,
//! `phase_started`, `discovery_complete`, `estimate`, `progress`,
//! `phase_complete`, `info`, `warning`, `error`, `complete`.

use serde::Serialize;
use serde_json::Value;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::{
    process::{CommandEvent, CommandChild},
    ShellExt,
};
use std::sync::Mutex;

/// Event channel the frontend subscribes to.
pub const SIDECAR_EVENT: &str = "marquee://sidecar-event";

/// Envelope emitted to the frontend for every line of sidecar output.
///
/// `kind` is one of:
///   - `"event"`: stdout line parsed as a known IPC event.
///   - `"raw"`: stdout line that failed to JSON-parse (logged for diagnostics).
///   - `"stderr"`: stderr line from the sidecar (framework-level errors).
///   - `"exit"`: process exit notice.
#[derive(Clone, Serialize)]
#[serde(tag = "kind", rename_all = "lowercase")]
pub enum SidecarMessage {
    Event { payload: Value },
    Raw { line: String },
    Stderr { line: String },
    Exit { code: Option<i32>, success: bool },
}

/// In-flight sidecar process. We keep a handle so a future cancel command
/// can SIGTERM the child. Only one scan at a time in E1.
#[derive(Default)]
pub struct SidecarState {
    pub child: Mutex<Option<CommandChild>>,
}

/// Try to parse a stdout line as a sidecar IPC event.
///
/// Returns `Some(value)` if the line is valid JSON with a `type` field
/// and a known protocol version. Returns `None` if it's malformed or has
/// an unknown major version — caller should surface it as a `raw` line.
pub fn parse_sidecar_line(line: &str) -> Option<Value> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return None;
    }
    let value: Value = serde_json::from_str(trimmed).ok()?;
    let obj = value.as_object()?;

    // Required fields per protocol.
    if !obj.contains_key("type") {
        return None;
    }
    // Version check — additive changes (new event types, new optional
    // fields) won't bump v. A v=2 means a breaking change we don't know.
    let v = obj.get("v").and_then(|x| x.as_i64()).unwrap_or(0);
    if v > 1 {
        return None;
    }

    Some(value)
}

/// Spawn the sidecar with the given arguments and wire its stdout/stderr
/// to the frontend via `SIDECAR_EVENT`.
///
/// Returns immediately; the spawned reader task lives until the child exits.
pub fn spawn_sidecar(app: &AppHandle, args: Vec<String>) -> Result<(), String> {
    let state = app.state::<SidecarState>();

    // Refuse to start a second scan while one is in flight.
    {
        let guard = state.child.lock().map_err(|e| e.to_string())?;
        if guard.is_some() {
            return Err("A scan is already running".into());
        }
    }

    let sidecar = app
        .shell()
        .sidecar("slideshow-gen")
        .map_err(|e| format!("Failed to resolve sidecar: {e}"))?
        .args(args);

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

    *state.child.lock().map_err(|e| e.to_string())? = Some(child);

    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            let message = match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).to_string();
                    match parse_sidecar_line(&line) {
                        Some(payload) => SidecarMessage::Event { payload },
                        None => SidecarMessage::Raw { line },
                    }
                }
                CommandEvent::Stderr(bytes) => SidecarMessage::Stderr {
                    line: String::from_utf8_lossy(&bytes).to_string(),
                },
                CommandEvent::Terminated(payload) => SidecarMessage::Exit {
                    code: payload.code,
                    success: payload.code == Some(0),
                },
                CommandEvent::Error(err) => SidecarMessage::Stderr {
                    line: format!("sidecar runtime error: {err}"),
                },
                // Forward-compat: future CommandEvent variants are ignored.
                _ => continue,
            };

            if let Err(e) = app_handle.emit(SIDECAR_EVENT, &message) {
                eprintln!("[marquee] failed to emit sidecar event: {e}");
            }

            // On exit, clear the in-flight child handle.
            if matches!(message, SidecarMessage::Exit { .. }) {
                if let Some(state) = app_handle.try_state::<SidecarState>() {
                    if let Ok(mut guard) = state.child.lock() {
                        *guard = None;
                    }
                }
            }
        }
    });

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_well_formed_event() {
        let line = r#"{"v":1,"t":0.0,"type":"started","config":{}}"#;
        let parsed = parse_sidecar_line(line).expect("should parse");
        assert_eq!(parsed["type"], "started");
        assert_eq!(parsed["v"], 1);
    }

    #[test]
    fn rejects_malformed_json() {
        assert!(parse_sidecar_line("not json at all").is_none());
        assert!(parse_sidecar_line("{broken").is_none());
    }

    #[test]
    fn rejects_empty_lines() {
        assert!(parse_sidecar_line("").is_none());
        assert!(parse_sidecar_line("   \n").is_none());
    }

    #[test]
    fn rejects_object_without_type() {
        assert!(parse_sidecar_line(r#"{"v":1,"t":0}"#).is_none());
    }

    #[test]
    fn rejects_future_protocol_version() {
        let line = r#"{"v":2,"t":0,"type":"something_new"}"#;
        assert!(parse_sidecar_line(line).is_none());
    }

    #[test]
    fn accepts_missing_v_field_as_zero() {
        // Defensive: missing v shouldn't crash; treat as legacy/v0 which is < 1.
        let line = r#"{"t":0,"type":"info","message":"hi"}"#;
        assert!(parse_sidecar_line(line).is_some());
    }

    #[test]
    fn parses_full_event_vocabulary() {
        // From docs/sidecar-protocol.md
        let events = [
            r#"{"v":1,"t":0,"type":"started","config":{"output":"/x"}}"#,
            r#"{"v":1,"t":0.06,"type":"phase_started","phase":"images","total":4127}"#,
            r#"{"v":1,"t":0.08,"type":"discovery_complete","images":4127,"videos":23}"#,
            r#"{"v":1,"t":0.08,"type":"estimate","duration_s":14512.3,"size_bytes":36608000000,"image_duration_s":14422.5,"video_duration_s":89.8}"#,
            r#"{"v":1,"t":12.4,"type":"progress","phase":"images","done":50,"total":4127,"message":null}"#,
            r#"{"v":1,"t":215,"type":"phase_complete","phase":"images","message":"done"}"#,
            r#"{"v":1,"t":1,"type":"info","message":"hi"}"#,
            r#"{"v":1,"t":95,"type":"warning","message":"oops","file":null}"#,
            r#"{"v":1,"t":0.05,"type":"error","message":"FFmpeg not found"}"#,
            r#"{"v":1,"t":21600,"type":"complete","outputs":[{"path":"/o","size_bytes":1}],"elapsed_s":21600}"#,
        ];
        for line in events {
            assert!(parse_sidecar_line(line).is_some(), "failed: {line}");
        }
    }
}
