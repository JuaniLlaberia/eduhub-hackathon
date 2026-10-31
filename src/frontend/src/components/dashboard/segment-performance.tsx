import { Pending, SectionCard } from "@/components/section-card";
import type { SegmentStat } from "@/lib/api/types";

// TODO: one Recharts bar chart per dimension present (topic, media_type, length_bucket, tone, post_kind,
// hook, cta), bars = avg_score, labels with segmentDimensionLabel / segmentValueLabel. Skip empty dimensions.
export function SegmentPerformance({ segments }: { segments: SegmentStat[] }) {
  return (
    <SectionCard title="Qué te funciona" description="Rendimiento por tema, formato, largo y tono">
      <Pending>{segments.length} segmentos</Pending>
    </SectionCard>
  );
}
