"use client";

import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useFeatures, useLatestReport } from "@/lib/api/queries";
import type { FeatureFlags } from "@/lib/api/types";
import { DashboardScreen } from "./dashboard-screen";

/** Until /features answers, keep the optional tools hidden (nothing may depend on them). */
const FEATURES_OFF: FeatureFlags = {
  generation: false,
  publishing: false,
  simulation: false,
  demo_mode: false,
};

export function DashboardView({ handle }: { handle: string }) {
  const { data: report, error, isPending } = useLatestReport(handle);
  const { data: features } = useFeatures();
  if (isPending) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorState error={error} />;
  return <DashboardScreen report={report} features={features ?? FEATURES_OFF} />;
}
