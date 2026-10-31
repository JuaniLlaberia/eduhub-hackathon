"use client";

import { Pending, SectionCard } from "@/components/section-card";

// TODO (TDD: write create-view.test.tsx first):
// - if recommendationId: show that recommendation (from useLatestReport(handle)); else a topic input
// - useCreateDrafts({ handle, recommendation_id, topic, instructions, count: 3 }) → editable drafts with
//   rationale, suggested_time (formatDateTime) and estimated_score (formatScore)
// - usePublish: on status "intent" open result.url (X compose window); hide when features.publishing is off
// - hide the whole screen when features.generation is off
export function CreateView({ handle, recommendationId }: { handle: string; recommendationId?: string }) {
  return (
    <div className="flex flex-col gap-6">
      <SectionCard
        title="Crear un post"
        description={recommendationId ? `@${handle} · a partir de una recomendación` : `@${handle}`}
      >
        <Pending>Elegí una recomendación o escribí un tema</Pending>
      </SectionCard>
      <SectionCard title="Borradores en tu estilo">
        <Pending />
      </SectionCard>
    </div>
  );
}
