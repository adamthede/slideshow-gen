---
title: "Post-render output UX: reset + 'Name your slideshow'"
status: "Done"
completed: 2026-05-27
linked_pr: "https://github.com/adamthede/slideshow-gen/pull/5"
---

Shipped via PR. No backing plan file existed — created plans-done stub on merge completion. Surfaced organically during Epic 4.S2 QA.

Two post-/around-render output UX improvements sharing the render output loop:

- **Post-render reset.** `Render again` re-runs the same folders + settings (reuses `runRender`, prompts for a destination pre-filled with the last path — the planned E4.S5 shortcut, landed early). `New slideshow` does a full reset to the empty drop zone (clears folders, output destination, name field, all sidecar results; preserves settings). Both wired into the complete card and the error card; disabled while a job runs.
- **"Name your slideshow" field.** New visible/editable name field auto-filled from the source folder, backed by a new pure module `lib/output-name.ts` → `deriveDefaultBaseName(folders)` (sanitized single-folder name, date-stamped fallback for multi/none). Field tracks the folder default until edited, then pins; blank falls back to derived. `pickOutput` builds the filename from the field and reuses the last-used directory — unique names avoid the overwrite prompt while repeats still surface the OS warning.
