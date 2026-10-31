"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { InsightCard } from "@/components/report/insight-card";
import { SegmentBars } from "@/components/report/segment-bars";
import { TimeHeatmapGrid } from "@/components/report/time-heatmap-grid";
import type { AnalyzedPost } from "@/lib/api/types";
import { formatNumber, formatPercent } from "@/lib/format";
import { lengthBucketLabel, mediaTypeLabel, segmentValueLabel, weekdayLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { bestPost, demoRecommendation, demoReport } from "./real-data";
import { container, lead, section, sectionTitle } from "./styles";

const STEPS = [
  {
    title: "Leemos tus últimos posts.",
    body: "Hasta 200 publicaciones de tu cuenta de X, con sus vistas, me gusta, respuestas, reposts y guardados.",
    Visual: PostStack,
  },
  {
    title: "Medimos cada uno.",
    body: "Horario, largo, formato, tema y tono de cada post, y sus tasas de interacción, guardados y compartidos.",
    Visual: PostAnatomy,
  },
  {
    title: "Encontramos tus patrones.",
    body: "Comparamos cada post con tu post típico, por horario, tema y formato. Cada número es calculado, no inventado.",
    Visual: Patterns,
  },
  {
    title: "La IA te lo explica.",
    body: "Un modelo de lenguaje escribe los hallazgos usando solo esos números, y te dice qué hacer con tu próximo post.",
    Visual: Explanation,
  },
];

export function HowItWorks() {
  const [active, setActive] = useState(0);
  const steps = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(Number((entry.target as HTMLElement).dataset.step));
        }
      },
      { rootMargin: "-50% 0px -50% 0px" },
    );
    for (const step of steps.current) if (step) observer.observe(step);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="como-funciona" aria-labelledby="como-funciona-title" className={section}>
      <div className={container}>
        <h2 id="como-funciona-title" className={cn(sectionTitle, "max-w-3xl")}>
          De tus posts a tu próxima decisión.
        </h2>
        <p className={cn(lead, "mt-6")}>
          NOVA analiza tu cuenta en menos de un minuto. Así lo hizo con @{demoReport.profile.handle}, una
          cuenta de demostración.
        </p>

        <div className="mt-12 grid gap-10 lg:mt-4 lg:grid-cols-12">
          <ol className="lg:col-span-5">
            {STEPS.map(({ title, body, Visual }, index) => (
              <li
                key={title}
                ref={(element) => {
                  steps.current[index] = element;
                }}
                data-step={index}
                className={cn(
                  "flex flex-col justify-center py-8 transition-opacity duration-500 lg:min-h-[70vh] lg:py-0",
                  index !== active && "lg:opacity-35",
                )}
              >
                <span className="text-signal flex size-9 items-center justify-center rounded-full border text-sm font-medium tabular-nums">
                  {index + 1}
                </span>
                <h3 className="mt-5 text-2xl font-semibold tracking-tight">{title}</h3>
                <p className="text-muted-foreground mt-3 max-w-md leading-relaxed">{body}</p>
                <div className="mt-8 lg:hidden">
                  <Visual active />
                </div>
              </li>
            ))}
          </ol>

          <div className="hidden lg:col-span-7 lg:block">
            <div className="sticky top-24 flex h-[calc(100vh-8rem)] items-center">
              <div className="grid w-full *:col-start-1 *:row-start-1">
                {STEPS.map(({ title, Visual }, index) => (
                  <div
                    key={title}
                    aria-hidden={index !== active}
                    className={cn(
                      "self-center transition-[opacity,translate] duration-500 motion-reduce:transition-none",
                      index === active ? "opacity-100" : "pointer-events-none translate-y-4 opacity-0",
                    )}
                  >
                    <Visual active={index === active} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PostStack({ active }: { active: boolean }) {
  const recent = demoReport.posts.slice(0, 3);
  return (
    <div className="relative mx-auto w-full max-w-md space-y-3 sm:h-[23rem] sm:space-y-0">
      {recent.map((item, index) => (
        <div
          key={item.post.id}
          className="bg-surface relative rounded-xl border p-5 shadow-2xl transition-[rotate] duration-700 motion-reduce:transition-none sm:absolute sm:inset-x-0 sm:top-(--stack-top)"
          style={
            {
              "--stack-top": `${index * 7}rem`,
              rotate: active ? `${(index - 1) * 2.5}deg` : "0deg",
              zIndex: index,
            } as CSSProperties
          }
        >
          <p className="line-clamp-2 leading-relaxed">{item.post.text}</p>
          <PostMetrics item={item} />
        </div>
      ))}
    </div>
  );
}

function PostMetrics({ item }: { item: AnalyzedPost }) {
  const { metrics } = item.post;
  const values = [
    ["vistas", metrics.impressions],
    ["me gusta", metrics.likes],
    ["respuestas", metrics.replies],
    ["guardados", metrics.bookmarks],
  ] as const;
  return (
    <p className="text-muted-foreground mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
      {values.map(([label, value]) => (
        <span key={label}>
          <span className="text-foreground tabular-nums">{formatNumber(value)}</span> {label}
        </span>
      ))}
    </p>
  );
}

function PostAnatomy({ active }: { active: boolean }) {
  const { features, rates } = bestPost;
  const chips = [
    `${weekdayLabel(features.weekday)} ${features.hour_local} h`,
    mediaTypeLabel(features.media_type),
    `Largo ${lengthBucketLabel(features.length_bucket).toLowerCase()}`,
    features.topic && `Tema: ${features.topic}`,
    features.tone && `Tono: ${features.tone}`,
    `Interacción ${formatPercent(rates.engagement_rate)}`,
    `Guardados ${formatPercent(rates.save_rate)}`,
    `Compartidos ${formatPercent(rates.share_rate)}`,
    `Respuestas ${formatPercent(rates.reply_rate)}`,
  ].filter((chip): chip is string => Boolean(chip));
  return (
    <div className="mx-auto w-full max-w-lg">
      <div className="bg-surface rounded-xl border p-5">
        <p className="leading-relaxed">{bestPost.post.text}</p>
        <PostMetrics item={bestPost} />
      </div>
      <ul className="mt-5 flex flex-wrap gap-2" aria-label="Lo que medimos de este post">
        {chips.map((chip, index) => (
          <li
            key={chip}
            className={cn(
              "bg-surface-elevated rounded-full border px-3 py-1.5 text-sm transition-[opacity,translate] duration-500 motion-reduce:transition-none",
              active ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
              index >= 5 && "border-signal/40 text-signal",
            )}
            style={{ transitionDelay: active ? `${index * 70}ms` : "0ms" }}
          >
            {chip}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Patterns() {
  const topics = demoReport.segments.filter((segment) => segment.dimension === "topic");
  return (
    <div className="bg-surface/60 mx-auto w-full max-w-xl rounded-2xl border p-6">
      <h4 className="text-sm font-medium">Cuándo publicar</h4>
      <div className="mt-4">
        <TimeHeatmapGrid heatmap={demoReport.heatmap} best={demoReport.best_time_slots[0]} />
      </div>
      <h4 className="mt-8 text-sm font-medium">Qué temas rinden, frente a tu post típico</h4>
      <SegmentBars segments={topics} className="mt-4" />
      <p className="text-muted-foreground mt-4 text-xs">
        {topics.length} temas detectados en sus posts:{" "}
        {topics.map((topic) => segmentValueLabel(topic.dimension, topic.value).toLowerCase()).join(", ")}.
      </p>
    </div>
  );
}

function Explanation() {
  const insight = demoReport.insights.find((item) => item.category === "topic") ?? demoReport.insights[0];
  return (
    <div className="mx-auto w-full max-w-lg space-y-4">
      <InsightCard insight={insight} />
      <div className="border-orbit/50 bg-orbit/5 rounded-xl border p-5">
        <p className="text-orbit text-xs font-medium">Qué hacer</p>
        <p className="mt-2 text-lg font-semibold">{demoRecommendation.action}</p>
        <p className="text-muted-foreground mt-1 text-sm leading-relaxed">{demoRecommendation.rationale}</p>
      </div>
    </div>
  );
}
