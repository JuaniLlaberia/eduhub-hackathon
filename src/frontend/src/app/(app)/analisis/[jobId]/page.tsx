import { Suspense } from "react";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { Skeleton } from "@/components/ui/skeleton";

// Screen 2 (MUST): polls the analysis job until it is done, then goes to the dashboard.
export default function AnalysisPage({ params }: PageProps<"/analisis/[jobId]">) {
  return (
    <Suspense fallback={<Skeleton className="h-40 w-full" />}>
      <AnalysisProgressForJob params={params} />
    </Suspense>
  );
}

async function AnalysisProgressForJob({ params }: Pick<PageProps<"/analisis/[jobId]">, "params">) {
  const { jobId } = await params;
  return <AnalysisProgress jobId={jobId} />;
}
