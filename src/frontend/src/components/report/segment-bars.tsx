import type { SegmentStat } from "@/lib/api/types";
import { formatScore } from "@/lib/format";
import { segmentValueLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";

/** Average score per value of one dimension, best first, with the 1.0x "typical post" mark. */
export function SegmentBars({ segments, className }: { segments: SegmentStat[]; className?: string }) {
  const rows = segments
    .filter((segment) => segment.avg_score !== null)
    .sort((a, b) => (b.avg_score ?? 0) - (a.avg_score ?? 0));
  const max = Math.max(1.2, ...rows.map((row) => row.avg_score ?? 0));
  return (
    <ul className={cn("space-y-2.5", className)}>
      {rows.map((row) => {
        const score = row.avg_score ?? 0;
        return (
          <li key={row.value} className="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-3 text-sm">
            <span className="truncate">{segmentValueLabel(row.dimension, row.value)}</span>
            <span className="bg-surface-elevated relative h-2 rounded-full">
              <span
                className={cn(
                  "absolute inset-y-0 left-0 rounded-full",
                  score >= 1 ? "bg-signal" : "bg-muted-foreground/50",
                )}
                style={{ width: `${(score / max) * 100}%` }}
              />
              <span
                aria-hidden="true"
                className="bg-orbit absolute -inset-y-1 w-px"
                style={{ left: `${(1 / max) * 100}%` }}
              />
            </span>
            <span className="text-right tabular-nums">{formatScore(score)}</span>
          </li>
        );
      })}
    </ul>
  );
}
