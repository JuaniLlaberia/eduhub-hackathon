import { Pending, SectionCard } from "@/components/section-card";
import type { AccountKPIs } from "@/lib/api/types";

// TODO: one tile per KPI with formatPercent / formatNumber:
// engagement, save, share, reply and passive rates, avg impressions, posts per week. Rates may be null.
export function KpiTiles({ kpis }: { kpis: AccountKPIs }) {
  return (
    <SectionCard title="Tus números" description={`${kpis.post_count} posts analizados`}>
      <Pending />
    </SectionCard>
  );
}
