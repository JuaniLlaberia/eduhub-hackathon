// TanStack Query hooks for every route the UI uses. Components fetch data only through these.
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./client";
import { unwrap } from "./errors";
import type { AnalysisRequest, DraftRequest, PublishRequest } from "./types";

export const POLL_INTERVAL_MS = 2000;

export const queryKeys = {
  features: ["features"] as const,
  trends: ["trends"] as const,
  analysis: (jobId: string) => ["analysis", jobId] as const,
  latestReport: (handle: string) => ["report", "latest", handle] as const,
};

export function useFeatures() {
  return useQuery({
    queryKey: queryKeys.features,
    queryFn: async () => unwrap(await api.GET("/features")),
    staleTime: Infinity,
  });
}

export function useTrends() {
  return useQuery({
    queryKey: queryKeys.trends,
    queryFn: async () => unwrap(await api.GET("/trends")),
  });
}

export function useCreateAnalysis() {
  return useMutation({
    mutationFn: async (body: AnalysisRequest) => unwrap(await api.POST("/analyses", { body })),
  });
}

/** Polls the job every POLL_INTERVAL_MS until it is done or failed. */
export function useAnalysisJob(jobId: string) {
  return useQuery({
    queryKey: queryKeys.analysis(jobId),
    queryFn: async () => unwrap(await api.GET("/analyses/{job_id}", { params: { path: { job_id: jobId } } })),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : POLL_INTERVAL_MS;
    },
  });
}

export function useLatestReport(handle: string) {
  return useQuery({
    queryKey: queryKeys.latestReport(handle),
    queryFn: async () => unwrap(await api.GET("/accounts/{handle}/report", { params: { path: { handle } } })),
  });
}

export function useCreateDrafts() {
  return useMutation({
    mutationFn: async (body: DraftRequest) => unwrap(await api.POST("/drafts", { body })),
  });
}

export function usePublish() {
  return useMutation({
    mutationFn: async (body: PublishRequest) => unwrap(await api.POST("/publications", { body })),
  });
}
