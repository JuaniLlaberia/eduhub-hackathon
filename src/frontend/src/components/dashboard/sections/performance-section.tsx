"use client";

import Link from "next/link";
import { useState } from "react";
import type { AnalysisReport, FeatureFlags, SegmentDimension } from "@/lib/api/types";
import { formatScore } from "@/lib/format";
import { insightCategoryLabel, segmentDimensionLabel, segmentValueLabel } from "@/lib/labels";
import { scoreColor, SectionHeader, SubTitle } from "./shared";

const ORDER: SegmentDimension[] = [
  "media_type",
  "length_bucket",
  "tone",
  "post_kind",
  "topic",
  "hook",
  "cta",
];

export function PerformanceSection({ report, features }: { report: AnalysisReport; features: FeatureFlags }) {
  const dimensions = ORDER.filter((d) => report.segments.filter((s) => s.dimension === d).length >= 2);
  const [dimension, setDimension] = useState<SegmentDimension | undefined>(dimensions[0]);
  const rows = report.segments
    .filter((s) => s.dimension === dimension && s.avg_score !== null)
    .sort((a, b) => (b.avg_score ?? 0) - (a.avg_score ?? 0));
  const max = Math.max(2.2, ...rows.map((r) => r.avg_score ?? 0));
  const recByInsight = new Map(
    report.recommendations.flatMap((rec) => rec.based_on_insight_ids.map((id) => [id, rec.id] as const)),
  );

  return (
    <>
      <SectionHeader title="Qué te funciona." note="Cada grupo, frente a tu post típico." />

      {dimensions.length > 0 && (
        <section aria-label="Rendimiento por grupo" className="mt-10">
          <div
            role="tablist"
            aria-label="Agrupar por"
            className="flex flex-wrap gap-8 border-b border-[#232738]"
          >
            {dimensions.map((d) => (
              <button
                key={d}
                type="button"
                role="tab"
                aria-selected={d === dimension}
                onClick={() => setDimension(d)}
                className={`-mb-px border-b-2 py-3 text-[15px] ${
                  d === dimension
                    ? "text-foreground border-foreground font-medium"
                    : "text-muted-foreground border-transparent"
                }`}
              >
                {segmentDimensionLabel(d)}
              </button>
            ))}
          </div>
          <div role="tabpanel" className="mt-2">
            {rows.map((row) => (
              <div
                key={row.value}
                className="grid grid-cols-[150px_minmax(0,1fr)_70px_80px] items-center gap-5 border-b border-[#232738] py-5"
              >
                <span className="text-[17px]">{segmentValueLabel(row.dimension, row.value)}</span>
                <div className="relative h-2">
                  <div
                    className="absolute inset-y-0 left-0"
                    style={{
                      width: `${Math.min(100, ((row.avg_score ?? 0) / max) * 100)}%`,
                      background: scoreColor(row.avg_score ?? 0),
                    }}
                  />
                  <div
                    aria-hidden
                    className="bg-foreground absolute -inset-y-2 w-px"
                    style={{ left: `${(1 / max) * 100}%` }}
                  />
                </div>
                <span className="text-right font-mono text-[17px]">{formatScore(row.avg_score)}</span>
                <span className="text-muted-foreground text-right font-mono text-[13px]">
                  {row.post_count}
                </span>
              </div>
            ))}
          </div>
          <p className="text-muted-foreground mt-3.5 text-[13px]">
            La línea vertical marca tu post típico. La última columna es la cantidad de posts.
          </p>
        </section>
      )}

      <section aria-label="Por qué" className="mt-14">
        <SubTitle>Por qué funcionan tus posts.</SubTitle>
        <div className="mt-5">
          {report.insights.map((insight) => {
            const recId = recByInsight.get(insight.id);
            return (
              <article
                key={insight.id}
                aria-labelledby={`insight-${insight.id}`}
                className="grid grid-cols-[110px_minmax(0,1fr)_auto] items-baseline gap-5 border-t border-[#232738] py-5"
              >
                <span className="text-muted-foreground text-sm">
                  {insightCategoryLabel(insight.category)}
                </span>
                <div className="min-w-0">
                  <h3 id={`insight-${insight.id}`} className="text-[17px] leading-snug font-medium">
                    {insight.title}
                  </h3>
                  <p className="text-muted-foreground mt-1.5 text-[15px] leading-relaxed">
                    {insight.description}
                  </p>
                  {insight.evidence.length > 0 && (
                    <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2">
                      {insight.evidence.map((item) => (
                        <div key={item.label} className="flex flex-col">
                          <dt className="text-muted-foreground text-xs">{item.label}</dt>
                          <dd className="font-mono text-[15px]">{item.value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>
                {features.generation && recId && (
                  <Link
                    href={`/cuenta/${report.profile.handle}/crear?recomendacion=${recId}`}
                    className="py-1.5 text-sm whitespace-nowrap underline underline-offset-4"
                  >
                    Crear con esto
                  </Link>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}
