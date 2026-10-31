"use client";

import { useState } from "react";
import type { AnalysisReport } from "@/lib/api/types";
import { formatDateTime, formatNumber, formatPercent, formatScore } from "@/lib/format";
import { mediaTypeLabel } from "@/lib/labels";
import { pickHighlights } from "../model";
import { scoreColor, SectionHeader } from "./shared";

const TABS = [
  { id: "top", label: "Los que más rindieron" },
  { id: "bottom", label: "Los que menos rindieron" },
] as const;

const columns = "grid grid-cols-[80px_minmax(0,1fr)_110px_110px] gap-6";

export function PostsSection({ report }: { report: AnalysisReport }) {
  const [side, setSide] = useState<"top" | "bottom">("top");
  const posts = pickHighlights(report.posts, side);

  return (
    <>
      <SectionHeader title="Tus posts." note="Originales con más de 1.000 vistas." />

      <div role="tablist" aria-label="Orden" className="mt-9 flex gap-8 border-b border-[#232738]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={side === tab.id}
            onClick={() => setSide(tab.id)}
            className={`-mb-px border-b-2 py-3 text-[15px] ${
              side === tab.id
                ? "text-foreground border-foreground font-medium"
                : "text-muted-foreground border-transparent"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        <div className={`${columns} text-muted-foreground pt-3.5 text-[13px]`}>
          <span>Nova Score</span>
          <span>Post</span>
          <span className="text-right">Vistas</span>
          <span className="text-right">Interacción</span>
        </div>
        {posts.length === 0 && (
          <p className="text-muted-foreground py-6 text-[15px]">
            Todavía no hay posts originales con más de 1.000 vistas.
          </p>
        )}
        {posts.map((p) => {
          const score = p.score ?? 0;
          return (
            <article key={p.post.id} className={`${columns} items-baseline border-b border-[#232738] py-6`}>
              <span
                className="font-mono text-[22px]"
                style={{ color: score < 0.8 ? "#9aa0b8" : scoreColor(score) }}
              >
                {formatScore(p.score)}
              </span>
              <div className="min-w-0">
                <p className="line-clamp-3 text-base leading-relaxed">{p.post.text}</p>
                <p className="text-muted-foreground mt-2 text-[13px]">
                  {mediaTypeLabel(p.features.media_type)}, {formatDateTime(p.post.created_at)}.{" "}
                  <a
                    href={p.post.url}
                    target="_blank"
                    rel="noreferrer"
                    className="underline underline-offset-4"
                  >
                    Ver en X
                  </a>
                </p>
                {p.explanation && (
                  <p className="mt-2.5 border-l border-[#a998ff] pl-3 text-sm leading-normal text-[#d9dcea]">
                    {p.explanation}
                  </p>
                )}
              </div>
              <span className="text-right font-mono text-[15px]">
                {formatNumber(p.post.metrics.impressions)}
              </span>
              <span className="text-right font-mono text-[15px]">
                {formatPercent(p.rates.engagement_rate)}
              </span>
            </article>
          );
        })}
      </div>
    </>
  );
}
