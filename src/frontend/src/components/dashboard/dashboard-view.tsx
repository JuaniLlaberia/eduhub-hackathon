"use client";

import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useLatestReport } from "@/lib/api/queries";
import { BestTimeSlots } from "./best-time-slots";
import { InsightList } from "./insight-list";
import { KpiTiles } from "./kpi-tiles";
import { PostHighlights } from "./post-highlights";
import { RecommendationList } from "./recommendation-list";
import { SegmentPerformance } from "./segment-performance";
import { SummaryCard } from "./summary-card";
import { TimeHeatmap } from "./time-heatmap";

export function DashboardView({ handle }: { handle: string }) {
  const { data: report, error, isPending } = useLatestReport(handle);
  if (isPending) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorState error={error} />;
  return (
    <div className="flex flex-col gap-6">
      <SummaryCard report={report} />
      <KpiTiles kpis={report.kpis} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TimeHeatmap heatmap={report.heatmap} />
        </div>
        <BestTimeSlots slots={report.best_time_slots} />
      </div>
      <SegmentPerformance segments={report.segments} />
      <div className="grid gap-6 lg:grid-cols-2">
        <InsightList insights={report.insights} />
        <RecommendationList handle={report.profile.handle} recommendations={report.recommendations} />
      </div>
      <PostHighlights posts={report.posts} />
    </div>
  );
}
