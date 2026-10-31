"use client";

import Link from "next/link";
import { useState } from "react";
import { briefSentence } from "@/components/dashboard/onboarding/brief";
import type { AnalysisReport, FeatureFlags } from "@/lib/api/types";
import { AR_TIME_ZONE, formatNumber, formatPercent } from "@/lib/format";
import { firstName, orderRecommendations, pickHighlights } from "../model";
import { PostSky } from "./post-sky";
import { primaryButton, SubTitle } from "./shared";

const dayMonth = new Intl.DateTimeFormat("es-AR", { timeZone: AR_TIME_ZONE, day: "numeric", month: "long" });

/** "Analizamos 40 posts, del 2 de septiembre al 28 de octubre." (period may be missing). */
function periodText(postCount: number, start: string | null, end: string | null): string {
  const period =
    start && end ? `, del ${dayMonth.format(new Date(start))} al ${dayMonth.format(new Date(end))}` : "";
  return `Analizamos ${postCount} posts${period}.`;
}

function NumberRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-[#232738] py-4">
      <dt className="text-muted-foreground text-[15px]">{label}</dt>
      <dd className="font-mono text-xl">{value}</dd>
    </div>
  );
}

export function HomeSection({ report, features }: { report: AnalysisReport; features: FeatureFlags }) {
  const [more, setMore] = useState(false);
  const { profile, kpis } = report;
  const handle = profile.handle;
  const recommendations = orderRecommendations(report.recommendations, report.insights);
  const best = pickHighlights(report.posts, "top", 1)[0];

  return (
    <>
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-[40px] leading-[1.1] font-semibold tracking-[-0.03em]">
          Hola, {firstName(profile.display_name, handle)}.
        </h1>
        <p className="text-muted-foreground text-sm">
          {periodText(kpis.post_count, kpis.period_start, kpis.period_end)}
        </p>
      </header>

      {report.context ? (
        <p className="text-muted-foreground mt-3.5 max-w-[46rem] text-[15px] leading-relaxed">
          {briefSentence(handle, report.context)}{" "}
          <Link href={`/empezar?handle=${handle}`} className="text-foreground underline underline-offset-4">
            Editar brief y volver a analizar
          </Link>
        </p>
      ) : (
        <p className="text-muted-foreground mt-3.5 text-[15px]">
          Tu perfil está incompleto: nos falta saber para qué publicás.{" "}
          <Link
            href={`/empezar?handle=${handle}&paso=2`}
            className="text-foreground underline underline-offset-4"
          >
            Completar perfil
          </Link>
        </p>
      )}

      <PostSky report={report} best={best} />

      <div className="mt-14 flex flex-wrap gap-x-16 gap-y-12">
        <section aria-label="Recomendaciones" className="min-w-0 flex-[3_1_420px]">
          <SubTitle>Qué hacer ahora.</SubTitle>
          <ol aria-label="Qué hacer ahora" className="mt-5">
            {recommendations.map((rec, index) => (
              <li
                key={rec.id}
                className="grid grid-cols-[28px_minmax(0,1fr)] gap-3 border-t border-[#232738] py-5 last:border-b"
              >
                <span className="text-muted-foreground pt-0.5 font-mono text-sm">{index + 1}</span>
                <div>
                  <p className={`${index === 0 ? "text-lg" : "text-[17px]"} leading-snug font-medium`}>
                    {rec.action}
                  </p>
                  <p className="text-muted-foreground mt-1.5 text-[15px] leading-relaxed">{rec.rationale}</p>
                  {index === 0 && features.generation && (
                    <Link
                      href={`/cuenta/${handle}/crear?recomendacion=${rec.id}`}
                      className={`${primaryButton} mt-4`}
                    >
                      Crear post con esto
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section aria-label="Tus números" className="min-w-0 flex-[2_1_280px]">
          <SubTitle>Tus números.</SubTitle>
          <dl className="mt-5">
            <NumberRow label="Vistas en un post típico" value={formatNumber(kpis.median_impressions)} />
            <NumberRow label="Interacción" value={formatPercent(kpis.rates.engagement_rate)} />
            <NumberRow label="Posts por semana" value={formatNumber(kpis.posts_per_week)} />
            {more && (
              <>
                <NumberRow label="Guardados" value={formatPercent(kpis.rates.save_rate)} />
                <NumberRow label="Compartidos" value={formatPercent(kpis.rates.share_rate)} />
                <NumberRow label="Respuestas" value={formatPercent(kpis.rates.reply_rate)} />
                <NumberRow label="Tasa pasiva" value={formatPercent(kpis.rates.passive_rate)} />
              </>
            )}
          </dl>
          <div className="border-t border-[#232738] pt-2.5">
            <button
              type="button"
              onClick={() => setMore(!more)}
              className="py-2 text-sm underline underline-offset-4"
            >
              {more ? "Ver menos" : "Ver todos tus números"}
            </button>
          </div>
          <p className="text-muted-foreground mt-3 text-[13px] leading-normal">
            Mostramos la mediana: unos pocos virales llevan el promedio a {formatNumber(kpis.avg_impressions)}{" "}
            vistas.
          </p>
        </section>
      </div>
    </>
  );
}
