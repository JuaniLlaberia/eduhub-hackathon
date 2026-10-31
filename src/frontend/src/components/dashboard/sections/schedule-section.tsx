import Link from "next/link";
import type { AnalysisReport, FeatureFlags } from "@/lib/api/types";
import { formatScore, formatTimeSlot } from "@/lib/format";
import { weekdayLabel } from "@/lib/labels";
import { isLowConfidenceSlot } from "../model";
import { primaryButton, scoreColor, SectionHeader, SubTitle } from "./shared";

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);
const DAYS = Array.from({ length: 7 }, (_, day) => day);

const LEGEND = [
  { color: "#ffffff", label: "Más del doble" },
  { color: "#70dce7", label: "Por encima de lo típico" },
  { color: "#a998ff", label: "Cerca de lo típico" },
  { color: "#3f4459", label: "Por debajo" },
  { color: "#151827", label: "Sin posts" },
];

export function ScheduleSection({ report, features }: { report: AnalysisReport; features: FeatureFlags }) {
  const slots = report.best_time_slots.slice(0, 3);
  const best = slots[0];
  const byCell = new Map(report.heatmap.map((s) => [`${s.weekday}-${s.hour}`, s]));
  const anyLow = slots.some(isLowConfidenceSlot);

  return (
    <>
      <SectionHeader title="Cuándo publicar." note="Hora argentina. Frente a tu post típico." />

      <figure className="mt-10">
        <div className="overflow-x-auto">
          <div
            role="img"
            aria-label={
              best
                ? `Rendimiento por día y hora. Tu mejor momento: ${formatTimeSlot(best.weekday, best.hour)}.`
                : "Rendimiento por día y hora."
            }
            className="flex min-w-[640px] flex-col gap-1"
          >
            <div className="flex gap-1 pl-12">
              {HOURS.map((hour) => (
                <span key={hour} className="flex-1 font-mono text-[11px] text-[#5d6380]">
                  {hour % 3 === 0 ? `${hour} h` : ""}
                </span>
              ))}
            </div>
            {DAYS.map((day) => (
              <div key={day} className="flex items-center gap-1">
                <span className="text-muted-foreground w-11 text-sm">
                  {weekdayLabel(day, { short: true })}
                </span>
                {HOURS.map((hour) => {
                  const cell = byCell.get(`${day}-${hour}`);
                  const isBest = best && best.weekday === day && best.hour === hour;
                  return (
                    <span
                      key={hour}
                      title={
                        cell
                          ? `${formatTimeSlot(day, hour)}: ${formatScore(cell.avg_score)}, ${cell.post_count} posts`
                          : `${formatTimeSlot(day, hour)}: sin posts`
                      }
                      className="h-[30px] flex-1"
                      style={{
                        background: cell && cell.avg_score !== null ? scoreColor(cell.avg_score) : "#151827",
                        outline: isBest ? "2px solid #a998ff" : undefined,
                        outlineOffset: isBest ? 2 : undefined,
                      }}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <figcaption className="text-muted-foreground mt-4 flex flex-wrap gap-x-6 gap-y-2 text-[13px]">
          {LEGEND.map((item) => (
            <span key={item.label}>
              <span aria-hidden className="mr-2 inline-block size-2.5" style={{ background: item.color }} />
              {item.label}
            </span>
          ))}
        </figcaption>
      </figure>

      <div className="mt-14 flex flex-wrap gap-x-16 gap-y-12">
        <section aria-label="Mejores horarios" className="min-w-0 flex-[3_1_420px]">
          <SubTitle>Tus mejores horarios.</SubTitle>
          <table aria-label="Tus mejores horarios" className="mt-5 w-full border-collapse text-base">
            <thead>
              <tr className="text-muted-foreground text-left text-[13px]">
                <th scope="col" className="pb-2.5 font-normal">
                  Franja
                </th>
                <th scope="col" className="pb-2.5 text-right font-normal">
                  Rendimiento
                </th>
                <th scope="col" className="pb-2.5 text-right font-normal">
                  Posts
                </th>
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => (
                <tr key={`${slot.weekday}-${slot.hour}`} className="border-t border-[#232738]">
                  <td className="py-4 font-medium">{formatTimeSlot(slot.weekday, slot.hour)}</td>
                  <td className="py-4 text-right font-mono text-[#70dce7]">{formatScore(slot.avg_score)}</td>
                  <td className="text-muted-foreground py-4 text-right font-mono">{slot.post_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {anyLow && (
            <p className="text-muted-foreground border-t border-[#232738] pt-3.5 text-sm leading-relaxed">
              Hay franjas con menos de 5 posts. Tomalo como pista y probá antes de cambiar tu rutina.
            </p>
          )}
        </section>
        {best && features.generation && (
          <section aria-label="Probalo" className="min-w-0 flex-[2_1_280px]">
            <SubTitle>Probalo esta semana.</SubTitle>
            <p className="text-muted-foreground mt-3.5 text-[15px] leading-relaxed">
              Armá un post para el {formatTimeSlot(best.weekday, best.hour).toLowerCase()} y compará cómo
              rinde contra tu post típico.
            </p>
            <Link
              href={`/cuenta/${report.profile.handle}/crear?tema=${encodeURIComponent(`Post para el ${formatTimeSlot(best.weekday, best.hour)}`)}`}
              className={`${primaryButton} mt-5`}
            >
              Crear post para ese horario
            </Link>
          </section>
        )}
      </div>
    </>
  );
}
