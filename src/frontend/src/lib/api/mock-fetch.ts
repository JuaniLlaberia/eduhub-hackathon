import drafts from "./fixtures/drafts_response.json";
import failedJob from "./fixtures/analysis_job_failed.json";
import features from "./fixtures/feature_flags.json";
import health from "./fixtures/health.json";
import notFound from "./fixtures/error_not_found.json";
import publication from "./fixtures/publish_result.json";
import report from "./fixtures/analysis_report.json";
import simulation from "./fixtures/simulation_result.json";
import trends from "./fixtures/trends_response.json";
import type { AnalysisJob } from "./types";

export type MockFetch = (input: Request) => Promise<Response>;

export interface MockFetchOptions {
  /** Artificial latency per request, so loading states are visible. */
  delayMs?: number;
}

/** Analyzing this handle in mock mode ends in a failed job, to exercise the error UI. */
export const MOCK_FAILING_HANDLE = "error";

const STEPS: Pick<AnalysisJob, "status" | "progress" | "message">[] = [
  { status: "fetching", progress: 0.3, message: "Buscando tus posts" },
  { status: "analyzing", progress: 0.6, message: "Calculando métricas y patrones" },
  { status: "done", progress: 1, message: "Listo" },
];

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const normalize = (handle: unknown) =>
  String(handle ?? "")
    .trim()
    .replace(/^@/, "")
    .toLowerCase();

/**
 * Fake backend for mock mode (NEXT_PUBLIC_API_MOCK=1): answers every contract route with the
 * shared fixtures, and keeps analysis jobs in memory (one status step per poll).
 * Behavior: mock-fetch.test.ts.
 */
export function createMockFetch(options: MockFetchOptions = {}): MockFetch {
  const jobs = new Map<string, AnalysisJob>();
  let counter = 0;

  function advance(job: AnalysisJob): AnalysisJob {
    if (job.status === "done" || job.status === "failed") return job;
    const now = new Date().toISOString();
    if (job.handle === MOCK_FAILING_HANDLE) {
      return {
        ...job,
        status: "failed",
        progress: 0.2,
        message: null,
        updated_at: now,
        error: failedJob.error as AnalysisJob["error"],
      };
    }
    const index = STEPS.findIndex((step) => step.status === job.status) + 1;
    const step = STEPS[Math.min(index, STEPS.length - 1)];
    return { ...job, ...step, updated_at: now, report_id: step.status === "done" ? report.id : null };
  }

  async function route(request: Request): Promise<Response> {
    const path = new URL(request.url).pathname;
    const method = request.method.toUpperCase();
    if (method === "GET" && path === "/health") return json(health);
    if (method === "GET" && path === "/features") return json(features);
    if (method === "GET" && path === "/trends") return json(trends);
    if (method === "POST" && path === "/analyses") {
      const body = await request.json().catch(() => ({}));
      const now = new Date().toISOString();
      const job: AnalysisJob = {
        id: `mock-job-${++counter}-${Math.random().toString(36).slice(2, 8)}`,
        handle: normalize(body.handle),
        status: "queued",
        progress: 0,
        message: "En cola",
        created_at: now,
        updated_at: now,
        report_id: null,
        error: null,
      };
      jobs.set(job.id, job);
      return json(job, 202);
    }
    const jobMatch = path.match(/^\/analyses\/([^/]+)$/);
    if (method === "GET" && jobMatch) {
      const job = jobs.get(jobMatch[1]);
      if (!job) return json(notFound, 404);
      const next = advance(job);
      jobs.set(next.id, next);
      return json(next);
    }
    const reportMatch = path.match(/^\/reports\/([^/]+)$/);
    if (method === "GET" && reportMatch) {
      return reportMatch[1] === report.id ? json(report) : json(notFound, 404);
    }
    if (method === "GET" && /^\/accounts\/[^/]+\/report$/.test(path)) return json(report);
    if (method === "POST" && path === "/drafts") return json(drafts);
    if (method === "POST" && path === "/publications") return json(publication);
    if (method === "POST" && path === "/simulations") return json(simulation);
    return json(notFound, 404);
  }

  return async (request) => {
    if (options.delayMs) await new Promise((resolve) => setTimeout(resolve, options.delayMs));
    return route(request);
  };
}
