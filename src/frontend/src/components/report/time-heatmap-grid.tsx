import type { TimeSlotStat } from "@/lib/api/types";
import { formatScore, formatTimeSlot } from "@/lib/format";
import { weekdayLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);
const WEEKDAYS = Array.from({ length: 7 }, (_, weekday) => weekday);

/** Cell color: the higher the average score of the slot, the brighter. Empty slots stay dark. */
function cellColor(score: number | null): string {
  if (score === null) return "var(--surface-elevated)";
  const strength = Math.round(Math.min(1, Math.max(0.12, (score - 0.3) / 1.6)) * 100);
  return `color-mix(in oklch, var(--signal) ${strength}%, var(--surface-elevated))`;
}

/** Weekday × hour grid (Argentina time, 0 = Monday). The report only lists slots with posts. */
export function TimeHeatmapGrid({ heatmap, best }: { heatmap: TimeSlotStat[]; best?: TimeSlotStat }) {
  const slots = new Map(heatmap.map((slot) => [`${slot.weekday}-${slot.hour}`, slot]));
  return (
    <div>
      <div
        className="grid grid-cols-[2.25rem_repeat(24,minmax(0,1fr))] gap-[3px]"
        role="img"
        aria-label={
          best
            ? `Mapa de horarios. Mejor horario: ${formatTimeSlot(best.weekday, best.hour)}, ${formatScore(best.avg_score)}.`
            : "Mapa de horarios."
        }
      >
        <span />
        {HOURS.map((hour) => (
          <span key={hour} className="text-muted-foreground text-center text-[10px] leading-4">
            {hour % 6 === 0 ? hour : ""}
          </span>
        ))}
        {WEEKDAYS.map((weekday) => (
          <div key={weekday} className="contents">
            <span className="text-muted-foreground self-center text-xs">
              {weekdayLabel(weekday, { short: true })}
            </span>
            {HOURS.map((hour) => {
              const slot = slots.get(`${weekday}-${hour}`);
              const isBest = best && best.weekday === weekday && best.hour === hour;
              return (
                <span
                  key={hour}
                  title={
                    slot
                      ? `${formatTimeSlot(weekday, hour)}: ${formatScore(slot.avg_score)} (${slot.post_count} posts)`
                      : undefined
                  }
                  className={cn(
                    "aspect-square rounded-[3px]",
                    isBest && "ring-orbit ring-2 ring-offset-1 ring-offset-transparent",
                  )}
                  style={{ background: cellColor(slot?.avg_score ?? null) }}
                />
              );
            })}
          </div>
        ))}
      </div>
      <div className="text-muted-foreground mt-3 flex items-center justify-between gap-4 text-xs">
        <span className="flex items-center gap-2">
          Rinde menos
          <span
            aria-hidden="true"
            className="h-2 w-16 rounded-full"
            style={{ background: `linear-gradient(90deg, ${cellColor(0.3)}, ${cellColor(2)})` }}
          />
          Rinde más
        </span>
        {best && (
          <span>
            <span className="border-orbit mr-1.5 inline-block size-2.5 rounded-[2px] border-2 align-middle" />
            Mejor horario: {formatTimeSlot(best.weekday, best.hour).toLowerCase()},{" "}
            {formatScore(best.avg_score)}
          </span>
        )}
      </div>
    </div>
  );
}
