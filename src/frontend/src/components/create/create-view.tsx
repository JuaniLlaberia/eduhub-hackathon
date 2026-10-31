"use client";

// Screen 4 (WANTED): 3 drafts from a recommendation or a topic → edit → publish in X or schedule.
// Behavior: create-view.test.tsx.
import Link from "next/link";
import { useState } from "react";
import { primaryButton } from "@/components/dashboard/sections/shared";
import { useCreateDrafts, useFeatures, useLatestReport, usePublish, useTrends } from "@/lib/api/queries";
import type { Draft, PublishResult } from "@/lib/api/types";
import { formatDateTime, formatScore } from "@/lib/format";

const secondaryButton =
  "rounded-[4px] border border-[#3f4459] px-4 py-2.5 text-sm font-medium hover:border-foreground disabled:opacity-60";

function DraftCard({
  index,
  draft,
  handle,
  canPublish,
}: {
  index: number;
  draft: Draft;
  handle: string;
  canPublish: boolean;
}) {
  const publish = usePublish();
  const [text, setText] = useState(draft.text);
  const [notice, setNotice] = useState("");
  const id = `draft-${draft.id}`;

  function send(scheduledFor: string | null) {
    setNotice("");
    publish.mutate(
      { handle, text, scheduled_for: scheduledFor },
      {
        onSuccess: (result: PublishResult) => {
          if (result.status === "intent" && result.url) {
            window.open(result.url, "_blank", "noopener");
            setNotice("Abrimos X con tu post listo para publicar.");
          } else if (result.status === "scheduled" && result.scheduled_for) {
            setNotice(`Programado para ${formatDateTime(result.scheduled_for)}.`);
          } else if (result.status === "published") {
            setNotice("Publicado.");
          } else {
            setNotice(result.error ?? "No se pudo publicar. Probá de nuevo.");
          }
        },
      },
    );
  }

  return (
    <article className="grid grid-cols-[28px_minmax(0,1fr)] gap-3 border-t border-[#232738] py-6">
      <span className="text-muted-foreground pt-1 font-mono text-sm">{index + 1}</span>
      <div className="min-w-0">
        <label htmlFor={id} className="sr-only">
          Borrador {index + 1}
        </label>
        <textarea
          id={id}
          rows={3}
          value={text}
          onChange={(event) => setText(event.target.value)}
          className="focus-visible:border-foreground block w-full resize-y border-0 border-b border-[#3f4459] bg-transparent pb-3 text-[17px] leading-relaxed outline-none"
        />
        <p className="text-muted-foreground mt-3 text-sm leading-relaxed">{draft.rationale}</p>
        <dl className="text-muted-foreground mt-3 flex flex-wrap gap-x-8 gap-y-1 text-[13px]">
          {draft.estimated_score !== null && (
            <div className="flex gap-2">
              <dt>Rendimiento estimado</dt>
              <dd className="font-mono text-[#70dce7]">{formatScore(draft.estimated_score)}</dd>
            </div>
          )}
          {draft.suggested_time && (
            <div className="flex gap-2">
              <dt>Horario sugerido</dt>
              <dd className="text-foreground">{formatDateTime(draft.suggested_time)}</dd>
            </div>
          )}
          <div className="flex gap-2">
            <dt>Caracteres</dt>
            <dd className={`font-mono ${text.length > 280 ? "text-destructive" : ""}`}>{text.length}/280</dd>
          </div>
        </dl>
        {canPublish && (
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              className={secondaryButton}
              disabled={publish.isPending || !text.trim()}
              onClick={() => send(null)}
            >
              Publicar en X
            </button>
            {draft.suggested_time && (
              <button
                type="button"
                className={secondaryButton}
                disabled={publish.isPending || !text.trim()}
                onClick={() => send(draft.suggested_time)}
              >
                Programar
              </button>
            )}
          </div>
        )}
        {notice && (
          <p role="status" className="mt-3 text-sm text-[#d9dcea]">
            {notice}
          </p>
        )}
      </div>
    </article>
  );
}

export function CreateView({
  handle,
  recommendationId,
  initialTopic,
}: {
  handle: string;
  recommendationId?: string;
  initialTopic?: string;
}) {
  const { data: report } = useLatestReport(handle);
  const { data: features } = useFeatures();
  const { data: trends } = useTrends();
  const drafts = useCreateDrafts();
  const [topic, setTopic] = useState(initialTopic ?? "");
  const [instructions, setInstructions] = useState("");
  const recommendation = report?.recommendations.find((rec) => rec.id === recommendationId);

  if (features && !features.generation) {
    return (
      <div className="py-10">
        <p className="text-[17px]">Crear posts no está disponible ahora.</p>
        <Link
          href={`/cuenta/${handle}`}
          className="text-muted-foreground mt-3 inline-block underline underline-offset-4"
        >
          Volver a tu análisis
        </Link>
      </div>
    );
  }

  const canGenerate = !!recommendation || topic.trim().length > 0;

  function generate() {
    drafts.mutate({
      handle,
      recommendation_id: recommendation?.id ?? null,
      topic: recommendation ? null : topic.trim(),
      instructions: instructions.trim() || null,
      count: 3,
      context: null,
    });
  }

  return (
    <div className="mx-auto max-w-[760px] pb-20">
      <Link
        href={`/cuenta/${handle}`}
        className="text-muted-foreground text-sm underline-offset-4 hover:underline"
      >
        Volver a tu análisis
      </Link>
      <h1 className="mt-6 text-[40px] leading-[1.1] font-semibold tracking-[-0.03em]">Crear un post.</h1>
      <p className="text-muted-foreground mt-3 text-[17px] leading-relaxed">
        Te armamos 3 borradores con tu voz, a partir de lo que mejor te funciona.
      </p>

      <section aria-label="Punto de partida" className="mt-10">
        {recommendation ? (
          <div className="border-t border-b border-[#232738] py-5">
            <p className="text-muted-foreground text-sm">A partir de tu recomendación</p>
            <p className="mt-2 text-lg font-medium">{recommendation.action}</p>
            <p className="text-muted-foreground mt-1.5 text-[15px] leading-relaxed">
              {recommendation.rationale}
            </p>
          </div>
        ) : (
          <>
            <label htmlFor="create-topic" className="text-muted-foreground text-sm">
              Sobre qué querés publicar
            </label>
            <input
              id="create-topic"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="Un tema, una idea o una tendencia"
              className="border-foreground mt-2 block w-full border-0 border-b bg-transparent pb-2.5 text-[22px] outline-none placeholder:text-[#5d6380]"
            />
            {trends && trends.trends.length > 0 && (
              <div className="mt-4">
                <p className="text-muted-foreground text-[13px]">Tendencias en Argentina</p>
                <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1">
                  {trends.trends.slice(0, 6).map((trend) => (
                    <button
                      key={trend.name}
                      type="button"
                      onClick={() => setTopic(trend.name)}
                      className="hover:text-foreground text-muted-foreground min-h-9 text-[15px] underline-offset-4 hover:underline"
                    >
                      {trend.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        <label htmlFor="create-instructions" className="text-muted-foreground mt-7 block text-sm">
          Indicaciones (opcional)
        </label>
        <input
          id="create-instructions"
          value={instructions}
          maxLength={500}
          onChange={(event) => setInstructions(event.target.value)}
          placeholder="Por ejemplo, que termine con una pregunta"
          className="mt-2 block w-full border-0 border-b border-[#3f4459] bg-transparent pb-2.5 text-[17px] outline-none placeholder:text-[#5d6380]"
        />
        <button
          type="button"
          onClick={generate}
          disabled={!canGenerate || drafts.isPending}
          className={`${primaryButton} mt-8 disabled:opacity-50`}
        >
          {drafts.isPending ? "Armando borradores…" : "Generar 3 borradores"}
        </button>
        {drafts.error && (
          <p role="alert" className="text-destructive mt-4 text-[15px]">
            No pudimos armar los borradores. Probá de nuevo en unos segundos.
          </p>
        )}
      </section>

      {drafts.data && (
        <section aria-label="Borradores" className="mt-14">
          <h2 className="text-[22px] font-semibold tracking-[-0.015em]">Tus borradores.</h2>
          <div className="mt-5 border-b border-[#232738]">
            {drafts.data.drafts.map((draft, index) => (
              <DraftCard
                key={draft.id}
                index={index}
                draft={draft}
                handle={handle}
                canPublish={!!features?.publishing}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
