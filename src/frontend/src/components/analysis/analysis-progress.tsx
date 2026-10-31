"use client";

import { ErrorState } from "@/components/error-state";
import { Pending, SectionCard } from "@/components/section-card";
import { Progress } from "@/components/ui/progress";
import { useAnalysisJob } from "@/lib/api/queries";

// TODO (TDD: write analysis-progress.test.tsx first):
// - steps list (queued → fetching → analyzing → done) with jobStatusLabel and job.message
// - on "done": router.replace(`/cuenta/${job.handle}`)
// - on "failed": show job.error.message and a "Probar de nuevo" link to "/"
export function AnalysisProgress({ jobId }: { jobId: string }) {
  const { data: job, error } = useAnalysisJob(jobId);
  if (error) return <ErrorState error={error} />;
  return (
    <SectionCard title="Analizando tu cuenta" description={job ? `@${job.handle}` : undefined}>
      <div className="flex flex-col gap-4">
        <Progress value={(job?.progress ?? 0) * 100} />
        <Pending>{job?.message ?? "Preparando el análisis…"}</Pending>
      </div>
    </SectionCard>
  );
}
