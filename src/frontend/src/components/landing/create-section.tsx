"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { formatDateTime, formatScore } from "@/lib/format";
import { cn } from "@/lib/utils";
import { demoDrafts, demoRecommendation } from "./real-data";
import { container, featureName, lead, section, sectionTitle } from "./styles";

const TYPE_MS = 1400;
const STAGGER_MS = 500;

const intentUrl = (text: string) => `https://x.com/intent/post?text=${encodeURIComponent(text)}`;

/** Elapsed ms since `start` (or Infinity with reduced motion), re-rendering each frame until `until`. */
function useElapsed(start: number | null, until: number) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (start === null) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = requestAnimationFrame(function tick(now) {
      const value = reduced ? Infinity : now - start;
      setElapsed(value);
      if (value < until) frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [start, until]);
  return start === null ? 0 : elapsed;
}

export function CreateSection() {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const elapsed = useElapsed(startedAt, TYPE_MS + STAGGER_MS * demoDrafts.length);

  return (
    <section id="crear" aria-labelledby="crear-title" className={section}>
      <div className={cn(container, "grid gap-12 lg:grid-cols-12 lg:gap-10")}>
        <div className="lg:col-span-5">
          <p className={cn(featureName, "text-signal")}>Crear</p>
          <h2 id="crear-title" className={cn(sectionTitle, "mt-4")}>
            Tu próximo post, en tu voz.
          </h2>
          <p className={cn(lead, "mt-6")}>
            Elegí una recomendación y NOVA escribe borradores con tu estilo, sugiere el mejor horario y estima
            su Nova Score. Después lo publicás en X.
          </p>

          <div className="border-orbit/50 bg-orbit/5 mt-10 rounded-xl border p-5">
            <p className="text-orbit text-xs font-medium">Recomendación del análisis</p>
            <p className="mt-2 text-lg font-semibold">{demoRecommendation.action}</p>
            <p className="text-muted-foreground mt-1 text-sm leading-relaxed">
              {demoRecommendation.rationale}
            </p>
            <Button
              className="mt-5 h-10 px-4"
              onClick={() => setStartedAt(performance.now())}
              disabled={startedAt !== null && elapsed < TYPE_MS + STAGGER_MS * demoDrafts.length}
            >
              {startedAt === null ? "Generar borradores" : "Generar de nuevo"}
            </Button>
          </div>
        </div>

        <ol className="space-y-4 lg:col-span-7" aria-live="polite">
          {demoDrafts.map((draft, index) => {
            const progress =
              startedAt === null ? 0 : Math.min(1, Math.max(0, (elapsed - index * STAGGER_MS) / TYPE_MS));
            const shown = draft.text.slice(0, Math.round(draft.text.length * progress));
            const done = progress >= 1;
            return (
              <li
                key={draft.id}
                className={cn(
                  "rounded-xl border p-5 transition-colors duration-500",
                  startedAt === null ? "border-dashed" : "bg-surface",
                )}
              >
                <div className="flex items-center justify-between gap-4">
                  <p className="text-muted-foreground text-xs">Borrador {index + 1}</p>
                  {draft.estimated_score !== null && draft.estimated_score !== undefined && (
                    <p
                      className={cn(
                        "text-signal text-sm font-medium tabular-nums transition-opacity duration-500",
                        done ? "opacity-100" : "opacity-0",
                      )}
                    >
                      {formatScore(draft.estimated_score)} estimado
                    </p>
                  )}
                </div>
                <p className="mt-2 min-h-[3.25rem] text-lg leading-relaxed">
                  {startedAt === null ? (
                    <span className="text-muted-foreground text-base">Tu borrador va a aparecer acá.</span>
                  ) : (
                    <>
                      {shown}
                      {!done && (
                        <span
                          aria-hidden="true"
                          className="bg-signal ml-0.5 inline-block h-5 w-0.5 align-middle"
                        />
                      )}
                    </>
                  )}
                </p>
                <div
                  className={cn(
                    "mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-4 text-sm transition-opacity duration-500",
                    done ? "opacity-100" : "pointer-events-none opacity-0",
                  )}
                  aria-hidden={!done}
                >
                  <span className="text-muted-foreground">
                    {draft.suggested_time
                      ? `Publicar el ${formatDateTime(draft.suggested_time)}`
                      : draft.rationale}
                  </span>
                  <a
                    href={intentUrl(draft.text)}
                    target="_blank"
                    rel="noreferrer"
                    tabIndex={done ? 0 : -1}
                    className="text-orbit rounded-sm font-medium hover:underline"
                  >
                    Abrir en X
                  </a>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
