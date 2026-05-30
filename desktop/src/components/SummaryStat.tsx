import type { LucideIcon } from "lucide-react";

export type SummaryStatTone = "muted" | "neutral" | "accent";

interface SummaryStatProps {
  label: string;
  value: string;
  icon?: LucideIcon;
  tone?: SummaryStatTone;
}

/**
 * SummaryStat — a single stat block for the pre-render Summary section.
 *
 * Visual treatment:
 * - small uppercase label with an optional leading lucide glyph
 * - large tabular-nums value
 * - `tone` colors the glyph (and softens the value when `muted`) to call
 *   out whether the number is notable (accent), neutral, or low-signal.
 */
export function SummaryStat({
  label,
  value,
  icon: Icon,
  tone = "neutral",
}: SummaryStatProps) {
  const iconClass =
    tone === "accent"
      ? "text-primary"
      : tone === "muted"
      ? "text-muted-foreground/60"
      : "text-muted-foreground";

  const valueClass =
    tone === "muted"
      ? "text-2xl font-semibold tabular-nums text-muted-foreground"
      : "text-2xl font-semibold tabular-nums";

  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
        {Icon && <Icon className={`h-3.5 w-3.5 ${iconClass}`} aria-hidden="true" />}
        {label}
      </span>
      <span className={valueClass}>{value}</span>
    </div>
  );
}
