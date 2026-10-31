"use client";

import { useState } from "react";
import { ScoreStrip } from "@/components/report/score-strip";
import { scoreTier, TIER_FILL, TIER_LABEL, type ScoreTier } from "@/components/report/score-style";
import { formatDateTime, formatScore } from "@/lib/format";
import { mediaTypeLabel, weekdayLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { bestPost, demoHandle, scoredPosts, typicalPost, worstPost } from "./real-data";
import { container, featureName, lead, section, sectionTitle } from "./styles";

const PICKS = [
  { label: "El que más rindió", item: bestPost },
  { label: "Uno típico", item: typicalPost },
  { label: "El que menos rindió", item: worstPost },
];

export function ScoreSection() {
  const [selectedId, setSelectedId] = useState(bestPost.post.id);
  const selected = scoredPosts.find((item) => item.post.id === selectedId) ?? bestPost;
  const { features } = selected;

  return (
    <section id="nova-score" aria-labelledby="nova-score-title" className={section}>
      <div className={container}>
        <p className={cn(featureName, "text-orbit")}>Nova Score</p>
        <h2 id="nova-score-title" className={cn(sectionTitle, "mt-4 max-w-3xl")}>
          Un número para saber si un post rindió.
        </h2>
        <p className={cn(lead, "mt-6")}>
          Combinamos alcance e interacción y lo comparamos con lo habitual en tu cuenta: 1,0x es tu post
          típico y {formatScore(bestPost.score)}, uno que rindió más del doble. El mismo número estima cuánto
          podría rendir un borrador antes de publicarlo.
        </p>

        <div className="bg-surface/60 mt-12 rounded-2xl border p-4 sm:p-8">
          <ScoreStrip posts={scoredPosts} selectedId={selectedId} onSelect={setSelectedId} />
          <ul className="text-muted-foreground mt-2 flex flex-wrap gap-x-5 gap-y-2 text-xs">
            {(Object.keys(TIER_LABEL) as ScoreTier[]).map((tier) => (
              <li key={tier} className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="size-2.5 rounded-full"
                  style={{ background: TIER_FILL[tier] }}
                />
                {TIER_LABEL[tier]}
              </li>
            ))}
          </ul>

          <div className="mt-8 grid gap-6 border-t pt-8 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <p className="text-sm font-medium">Mirá por qué</p>
              <div className="mt-3 flex flex-wrap gap-2 lg:flex-col">
                {PICKS.map((pick) => (
                  <button
                    key={pick.label}
                    type="button"
                    aria-pressed={pick.item.post.id === selectedId}
                    onClick={() => setSelectedId(pick.item.post.id)}
                    className={cn(
                      "focus-visible:ring-ring/60 rounded-lg border px-4 py-2.5 text-left text-sm transition-colors outline-none focus-visible:ring-3",
                      pick.item.post.id === selectedId
                        ? "border-orbit bg-surface-elevated"
                        : "hover:bg-surface",
                    )}
                  >
                    {pick.label}
                    <span className="text-muted-foreground ml-2 tabular-nums">
                      {formatScore(pick.item.score)}
                    </span>
                  </button>
                ))}
              </div>
              <p className="text-muted-foreground mt-4 text-xs">
                Posts de @{demoHandle}, una cuenta de demostración. También podés tocar cualquier punto.
              </p>
            </div>

            <article aria-live="polite" className="lg:col-span-8">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <p className="text-5xl font-semibold tracking-tight tabular-nums">
                  {formatScore(selected.score)}
                </p>
                <p className="text-muted-foreground">{TIER_LABEL[scoreTier(selected.score)].toLowerCase()}</p>
              </div>
              <p className="mt-4 text-lg leading-relaxed">{selected.post.text}</p>
              <p className="text-muted-foreground mt-2 text-sm">
                {formatDateTime(selected.post.created_at)}. {mediaTypeLabel(features.media_type)}, publicado
                un {weekdayLabel(features.weekday).toLowerCase()} a las {features.hour_local} h
                {features.topic ? `, sobre ${features.topic}` : ""}.
              </p>
              {selected.explanation && (
                <p className="border-signal mt-5 border-l-2 pl-4 leading-relaxed">{selected.explanation}</p>
              )}
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}
