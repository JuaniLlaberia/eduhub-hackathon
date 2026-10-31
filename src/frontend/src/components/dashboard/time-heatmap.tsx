import { Pending, SectionCard } from "@/components/section-card";
import type { TimeSlotStat } from "@/lib/api/types";

// TODO: 7 × 24 CSS grid (rows weekdayLabel short, 0 = Monday), color by avg_score.
// heatmap only has slots with posts: render the missing cells empty. avg_score may be null.
export function TimeHeatmap({ heatmap }: { heatmap: TimeSlotStat[] }) {
  return (
    <SectionCard title="Cuándo te va mejor" description={`${heatmap.length} franjas con posts`}>
      <Pending />
    </SectionCard>
  );
}
