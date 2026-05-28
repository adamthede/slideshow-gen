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
use std::time::Duration;

/// Grace period between the graceful SIGTERM and the SIGKILL escalation. If the
/// engine hasn't reaped its process group and exited within this window, a
/// wedged FFmpeg is assumed and we hard-kill the pid.
const CANCEL_GRACE: Duration = Duration::from_secs(5);

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

    // Required: a string `type` field. A bare `"type": 42` is malformed
    // per docs/sidecar-protocol.md and would mis-handle on the TS side.
    obj.get("type").and_then(|v| v.as_str())?;

    // Version check — additive changes (new event types, new optional
    // fields) won't bump v. A v=2 means a breaking change we don't know.
    let v = obj.get("v").and_then(|x| x.as_i64()).unwrap_or(0);
    if v > 1 {
        return None;
    }

    Some(value)
}

/// Drain complete newline-terminated lines from a byte buffer.
///
/// Tauri's `CommandEvent::Stdout`/`Stderr` deliver arbitrary byte chunks
/// from the OS pipe. A single read may contain a partial line, multiple
/// lines, or end mid-multi-byte-UTF-8 character. We append to a persistent
/// buffer and only emit at `\n` boundaries — that way a line is always
/// converted from UTF-8 as a single unit, and partial reads are preserved
/// across chunks.
///
/// Trailing partial data stays in `buf` for the next chunk. Callers must
/// flush any remainder on stream close.
pub fn extract_lines(buf: &mut Vec<u8>) -> Vec<String> {
    let mut out = Vec::new();
    while let Some(nl) = buf.iter().position(|&b| b == b'\n') {
        let drained: Vec<u8> = buf.drain(..=nl).collect();
        let end = drained
            .iter()
            .rposition(|&b| b != b'\n' && b != b'\r')
            .map(|i| i + 1)
            .unwrap_or(0);
        out.push(String::from_utf8_lossy(&drained[..end]).into_owned());
    }
    out
}

fn classify_stdout_line(line: String) -> Option<SidecarMessage> {
    if line.trim().is_empty() {
        return None;
    }
    Some(match parse_sidecar_line(&line) {
        Some(payload) => SidecarMessage::Event { payload },
        None => SidecarMessage::Raw { line },
    })
}

/// Spawn the sidecar with the given arguments and wire its stdout/stderr
/// to the frontend via `SIDECAR_EVENT`.
///
/// Returns immediately; the spawned reader task lives until the child exits.
pub fn spawn_sidecar(app: &AppHandle, args: Vec<String>) -> Result<(), String> {
    let state = app.state::<SidecarState>();

    // Hold the mutex across check + spawn + set so two concurrent
    // `start_scan`/`start_render` calls can't both pass the is_some()
    // check and end up spawning multiple sidecars (TOCTOU race).
    let mut guard = state.child.lock().map_err(|e| e.to_string())?;
    if guard.is_some() {
        return Err("A scan or render is already in progress".into());
    }

    let sidecar = app
        .shell()
        .sidecar("slideshow-gen")
        .map_err(|e| format!("Failed to resolve sidecar: {e}"))?
        .args(args);

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

    *guard = Some(child);
    drop(guard);

    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        let mut stdout_buf: Vec<u8> = Vec::new();
        let mut stderr_buf: Vec<u8> = Vec::new();

        let emit = |message: &SidecarMessage| {
            if let Err(e) = app_handle.emit(SIDECAR_EVENT, message) {
                eprintln!("[marquee] failed to emit sidecar event: {e}");
            }
        };

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    stdout_buf.extend_from_slice(&bytes);
                    for line in extract_lines(&mut stdout_buf) {
                        if let Some(msg) = classify_stdout_line(line) {
                            emit(&msg);
                        }
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    stderr_buf.extend_from_slice(&bytes);
                    for line in extract_lines(&mut stderr_buf) {
                        if !line.trim().is_empty() {
                            emit(&SidecarMessage::Stderr { line });
                        }
                    }
                }
                CommandEvent::Terminated(payload) => {
                    // Flush any trailing partial lines (last line may have
                    // no terminating newline).
                    if !stdout_buf.is_empty() {
                        let line = String::from_utf8_lossy(&stdout_buf).into_owned();
                        stdout_buf.clear();
                        if let Some(msg) = classify_stdout_line(line) {
                            emit(&msg);
                        }
                    }
                    if !stderr_buf.is_empty() {
                        let line = String::from_utf8_lossy(&stderr_buf).into_owned();
                        stderr_buf.clear();
                        if !line.trim().is_empty() {
                            emit(&SidecarMessage::Stderr { line });
                        }
                    }

                    let exit_msg = SidecarMessage::Exit {
                        code: payload.code,
                        success: payload.code == Some(0),
                    };
                    emit(&exit_msg);

                    if let Some(state) = app_handle.try_state::<SidecarState>() {
                        if let Ok(mut guard) = state.child.lock() {
                            *guard = None;
                        }
                    }
                }
                CommandEvent::Error(err) => {
                    emit(&SidecarMessage::Stderr {
                        line: format!("sidecar runtime error: {err}"),
                    });
                }
                _ => continue,
            }
        }
    });

    Ok(())
}

/// Cancel the in-flight render by sending **SIGTERM** to the sidecar pid.
///
/// SIGTERM (not `CommandChild::kill()`, which is SIGKILL) is deliberate: the
/// engine catches SIGTERM, reaps its own process group (FFmpeg children
/// included), removes its temp dir, emits `cancelled`, and exits — none of
/// which a SIGKILL would allow. The PyInstaller onefile bootloader forwards
/// SIGTERM to the Python child (verified in the E4.S3 spike).
///
/// We signal by pid and leave the `CommandChild` handle in place, so the normal
/// `Terminated` path (which clears the handle and emits `exit`) still drives the
/// frontend's lifecycle. A SIGKILL escalation fires after `CANCEL_GRACE` only if
/// the process is still registered with the same pid.
pub fn cancel_sidecar(app: &AppHandle) -> Result<(), String> {
    let state = app.state::<SidecarState>();
    let pid = {
        let guard = state.child.lock().map_err(|e| e.to_string())?;
        match guard.as_ref() {
            Some(child) => child.pid() as i32,
            None => return Err("No render is running.".into()),
        }
    };

    // Graceful stop. The engine does the heavy lifting (killpg of its own group
    // + temp cleanup) on receipt.
    unsafe {
        libc::kill(pid, libc::SIGTERM);
    }

    // Escalation: hard-kill if the child is still registered with this pid after
    // the grace period (the `Terminated` handler clears the handle on a clean
    // exit, so a cleared/replaced handle means we should not signal again).
    let app = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(CANCEL_GRACE);
        if let Some(state) = app.try_state::<SidecarState>() {
            if let Ok(guard) = state.child.lock() {
                if guard.as_ref().map(|c| c.pid() as i32) == Some(pid) {
                    unsafe {
                        libc::kill(pid, libc::SIGKILL);
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
    fn rejects_non_string_type() {
        // Protocol requires `type` to be a string; a number-typed `type`
        // is malformed and must not forward as a `kind:"event"`.
        assert!(parse_sidecar_line(r#"{"v":1,"t":0,"type":42}"#).is_none());
        assert!(parse_sidecar_line(r#"{"v":1,"t":0,"type":null}"#).is_none());
        assert!(parse_sidecar_line(r#"{"v":1,"t":0,"type":{}}"#).is_none());
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
    fn extract_lines_single_complete_line() {
        let mut buf = b"hello\n".to_vec();
        let lines = extract_lines(&mut buf);
        assert_eq!(lines, vec!["hello".to_string()]);
        assert!(buf.is_empty());
    }

    #[test]
    fn extract_lines_multiple_in_one_chunk() {
        let mut buf = b"a\nb\nc\n".to_vec();
        let lines = extract_lines(&mut buf);
        assert_eq!(lines, vec!["a".to_string(), "b".to_string(), "c".to_string()]);
        assert!(buf.is_empty());
    }

    #[test]
    fn extract_lines_preserves_partial_trailing() {
        let mut buf = b"complete\npartial".to_vec();
        let lines = extract_lines(&mut buf);
        assert_eq!(lines, vec!["complete".to_string()]);
        assert_eq!(buf, b"partial");
    }

    #[test]
    fn extract_lines_joins_across_chunks() {
        let mut buf = Vec::new();
        buf.extend_from_slice(b"par");
        assert!(extract_lines(&mut buf).is_empty());
        buf.extend_from_slice(b"tial\n");
        let lines = extract_lines(&mut buf);
        assert_eq!(lines, vec!["partial".to_string()]);
        assert!(buf.is_empty());
    }

    #[test]
    fn extract_lines_handles_split_multibyte_utf8() {
        // "Müller" — ü is C3 BC. Split between the two bytes across chunks
        // would corrupt under naive from_utf8_lossy(chunk).
        let mut buf = Vec::new();
        buf.extend_from_slice(b"M\xC3");
        assert!(extract_lines(&mut buf).is_empty());
        buf.extend_from_slice(b"\xBCller\n");
        let lines = extract_lines(&mut buf);
        assert_eq!(lines, vec!["Müller".to_string()]);
    }

    #[test]
    fn extract_lines_strips_crlf() {
        let mut buf = b"line\r\n".to_vec();
        let lines = extract_lines(&mut buf);
        assert_eq!(lines, vec!["line".to_string()]);
    }

    #[test]
    fn classify_stdout_skips_empty_and_whitespace() {
        assert!(classify_stdout_line(String::new()).is_none());
        assert!(classify_stdout_line("   ".into()).is_none());
        assert!(classify_stdout_line("\t\t".into()).is_none());
    }

    #[test]
    fn classify_stdout_treats_unparseable_as_raw() {
        let msg = classify_stdout_line("not json".into()).expect("should be raw");
        assert!(matches!(msg, SidecarMessage::Raw { .. }));
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
            r#"{"v":1,"t":42.3,"type":"cancelled","message":null}"#,
        ];
        for line in events {
            assert!(parse_sidecar_line(line).is_some(), "failed: {line}");
        }
    }
}
