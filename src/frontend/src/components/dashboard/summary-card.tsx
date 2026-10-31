import { SectionCard } from "@/components/section-card";
import type { AnalysisReport } from "@/lib/api/types";

// TODO: avatar, followers, period analyzed (formatDateTime of kpis.period_start/end), post count.
export function SummaryCard({ report }: { report: AnalysisReport }) {
  return (
    <SectionCard title={report.profile.display_name} description={`@${report.profile.handle}`}>
      <p className="text-lg leading-relaxed">{report.summary}</p>
    </SectionCard>
  );
}
