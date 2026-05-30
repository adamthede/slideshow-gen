interface TimelineProps {
  histogram: Array<{ month: string; count: number }>;
  earliest: string;
  latest: string;
}

/**
 * Timeline — density histogram of photo counts per month across the
 * date range of the input set. Replaces the plain `earliest → latest`
 * string in the Summary section. A 10-year archive looks visibly
 * different from a vacation folder; that's the point.
 */
export function Timeline({ histogram, earliest, latest }: TimelineProps) {
  if (histogram.length === 0) return null;

  const maxCount = Math.max(...histogram.map((b) => b.count), 1);
  const width = 100; // viewBox units; SVG scales to container width
  const height = 28;
  const barW = width / histogram.length;
  const baselineY = height;

  const yearTicks = uniqueYears(histogram);

  return (
    <div className="flex flex-col gap-2 pt-2 border-t border-border">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        Date range
      </span>
      <div className="flex flex-col gap-1.5">
        <svg
          viewBox={`0 0 ${width} ${height + 8}`}
          preserveAspectRatio="none"
          className="h-12 w-full"
          role="img"
          aria-label={`Density of items per month from ${earliest} to ${latest}`}
        >
          {histogram.map((bucket, i) => {
            const h = (bucket.count / maxCount) * height;
            return (
              <rect
                key={bucket.month}
                x={i * barW}
                y={baselineY - h}
                width={Math.max(barW - 0.1, 0.1)}
                height={h}
                className="fill-primary/80"
              />
            );
          })}
          <line
            x1="0"
            y1={baselineY + 0.5}
            x2={width}
            y2={baselineY + 0.5}
            className="stroke-border"
            strokeWidth="0.4"
            vectorEffect="non-scaling-stroke"
          />
          {yearTicks.map(({ year, x }) => (
            <line
              key={`tick-${year}`}
              x1={x}
              y1={baselineY + 0.5}
              x2={x}
              y2={baselineY + 3}
              className="stroke-muted-foreground/60"
              strokeWidth="0.4"
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>
        <div className="relative h-3 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {yearTicks.map(({ year, x }) => (
            <span
              key={`label-${year}`}
              className="absolute -translate-x-1/2 tabular-nums"
              style={{ left: `${x}%` }}
            >
              {year}
            </span>
          ))}
        </div>
        <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>{formatDate(earliest)}</span>
          <span>{formatDate(latest)}</span>
        </div>
      </div>
    </div>
  );
}

function uniqueYears(
  histogram: Array<{ month: string; count: number }>,
): Array<{ year: string; x: number }> {
  const seen = new Set<string>();
  const ticks: Array<{ year: string; x: number }> = [];
  const step = 100 / histogram.length;
  histogram.forEach((bucket, i) => {
    const year = bucket.month.slice(0, 4);
    if (!seen.has(year)) {
      seen.add(year);
      // Center the tick within the year's first month bucket.
      ticks.push({ year, x: i * step + step / 2 });
    }
  });
  return ticks;
}

function formatDate(iso: string): string {
  // Display ISO date as "YYYY · MMM D" without timezone surprises.
  const [y, m, d] = iso.split("-").map((s) => parseInt(s, 10));
  if (!y || !m || !d) return iso;
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${y} · ${months[m - 1]} ${d}`;
}
