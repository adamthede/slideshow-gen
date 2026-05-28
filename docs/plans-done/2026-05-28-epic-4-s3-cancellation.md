---
title: Epic 4.S3: Render cancellation
status: Done
completed: 2026-05-28
linked_pr: https://github.com/adamthede/slideshow-gen/pull/6
---

Shipped via PR #6. No backing plan file existed — created via /shipped workflow.

## Summary

Graceful render cancellation via SIGTERM signal handling. Engine calls `os.setpgrp()` to isolate its child processes into a separate process group, then `cancelRender` IPC triggers `os.killpg(own-group, SIGTERM)`. Key fixes:

- **Process group isolation verification**: Added `self._owns_process_group` flag; only True after verifying `os.getpgrp() == os.getpid()` postcondition (T1 data-integrity fix).
- **Cancel handler guards**: Gate `os.killpg()` on the isolation flag to prevent accidentally signaling Marquee's process group if `setpgrp()` fails silently (T1).
- **Benign IPC race handling**: `cancelRender()` catch block now logs the failure instead of surfacing "no render in flight" as state.error (T2 error-handling fix).
- **Card-stacking prevention**: Added `!error` to the `rendering` card gate so Error and Rendering cards don't briefly overlap mid-render (T2).

2 review cycles; 4 actioned (2 T1, 2 T2), 7 dismissed (platform-portability noise, macOS-only scope).
