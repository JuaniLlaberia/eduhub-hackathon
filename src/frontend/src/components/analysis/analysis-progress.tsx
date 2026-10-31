"use client";

// Analysis in progress: polls the job, shows the 3 steps and goes to the dashboard when it is done.
// Behavior: analysis-progress.test.tsx.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ErrorState } from "@/components/error-state";
import { useAnalysisJob } from "@/lib/api/queries";
import type { AnalysisJob } from "@/lib/api/types";

const STEPS = ["Buscar tus posts", "Analizar qué te funciona", "Armar tus recomendaciones"];

function currentStep(job: AnalysisJob | undefined): number {
  if (!job || job.status === "queued" || job.status === "fetching") return 0;
  if (job.status === "analyzing") return job.progress >= 0.85 ? 2 : 1;
  return 2;
}

export function AnalysisProgress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const { data: job, error } = useAnalysisJob(jobId);

  useEffect(() => {
    if (job?.status === "done") router.replace(`/cuenta/${job.handle}`);
  }, [job?.status, job?.handle, router]);

  if (error) return <ErrorState error={error} />;

  if (job?.status === "failed") {
    return (
      <div className="mx-auto max-w-[420px] py-16">
        <h1 className="text-[34px] leading-[1.12] font-semibold tracking-[-0.03em]">No pudimos terminar.</h1>
        <p role="alert" className="text-muted-foreground mt-3 text-base leading-relaxed">
          {job.error?.message ?? "Algo salió mal con el análisis."}
        </p>
        <Link
          href={`/empezar?handle=${job.handle}`}
          className="bg-foreground text-background mt-8 inline-block rounded-[4px] px-[18px] py-3 text-[15px] font-medium"
        >
          Probar de nuevo
        </Link>
      </div>
    );
  }

  const step = currentStep(job);
  return (
    <div className="mx-auto max-w-[420px] py-16">
      <div aria-hidden className="relative size-[72px]">
        <svg width="72" height="72" viewBox="0 0 72 72" fill="none" className="absolute inset-0">
          <circle cx="36" cy="36" r="7" fill="#f6f7fb" />
          <circle cx="36" cy="36" r="27" stroke="#2a2f45" strokeWidth="1.5" />
        </svg>
        <div className="absolute inset-0 animate-spin [animation-duration:2.4s] motion-reduce:animate-none">
          <span className="absolute top-[9px] left-1/2 -mt-[3.5px] -ml-[3.5px] size-[7px] rounded-full bg-[#a998ff]" />
        </div>
      </div>
      <h1 className="mt-8 text-[34px] leading-[1.12] font-semibold tracking-[-0.03em]">
        Estamos leyendo tus posts.
      </h1>
      <p className="text-muted-foreground mt-3 text-base leading-relaxed">
        Suele tardar menos de un minuto. Te llevamos a tu dashboard apenas termine.
      </p>
      <ol aria-label="Progreso del análisis" className="mt-9 text-[15px]">
        {STEPS.map((label, index) => (
          <li
            key={label}
            aria-current={index === step ? "step" : undefined}
            className={`flex justify-between gap-4 border-t border-[#232738] py-3.5 last:border-b ${
              index < step
                ? "text-muted-foreground"
                : index === step
                  ? "text-foreground font-medium"
                  : "text-[#5d6380]"
            }`}
          >
            <span>{label}</span>
            {index === step && <span className="font-normal text-[#a998ff]">en curso</span>}
          </li>
        ))}
      </ol>
      {job?.message && <p className="text-muted-foreground mt-4 text-sm">{job.message}</p>}
    </div>
  );
}
