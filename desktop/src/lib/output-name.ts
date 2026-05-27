/**
 * Default output filename derivation for the render destination.
 *
 * The visible "Name your slideshow" field is pre-filled from this: a single
 * source folder yields its (sanitized) folder name, while multiple folders or
 * none fall back to a date-stamped default. Kept pure so it is unit-testable.
 */

/** Last path segment of a POSIX/Windows path, with trailing separators stripped. */
function basename(p: string): string {
  const trimmed = p.replace(/[/\\]+$/, "");
  return trimmed.split(/[/\\]/).pop() ?? "";
}

/**
 * Make a folder name safe to use as a filename: macOS forbids `/` and `:`
 * (the latter is the legacy HFS path separator), so map them to `-` and
 * collapse runs of whitespace.
 */
function sanitizeName(name: string): string {
  return name
    .replace(/[/:]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

/** `slideshow-YYYY-MM-DD` from local (not UTC) date components. */
function dateBaseName(now: Date): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `slideshow-${year}-${month}-${day}`;
}

/**
 * Derive a default output base name (without the `.mp4` extension) from the
 * selected source folders. One folder → its sanitized name; zero or many →
 * a date-stamped fallback. Never returns an empty string.
 */
export function deriveDefaultBaseName(
  folders: string[],
  now: Date = new Date(),
): string {
  if (folders.length === 1) {
    const base = sanitizeName(basename(folders[0]));
    if (base) return base;
  }
  return dateBaseName(now);
}
