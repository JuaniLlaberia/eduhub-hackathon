import { describe, expect, it } from "vitest";
import drafts from "./fixtures/drafts_response.json";
import features from "./fixtures/feature_flags.json";
import health from "./fixtures/health.json";
import publication from "./fixtures/publish_result.json";
import report from "./fixtures/analysis_report.json";
import simulation from "./fixtures/simulation_result.json";
import trends from "./fixtures/trends_response.json";
import { createMockFetch, MOCK_FAILING_HANDLE, type MockFetch } from "./mock-fetch";

const BASE = "http://mock.test";

function get(mock: MockFetch, path: string) {
  return mock(new Request(BASE + path));
}

function post(mock: MockFetch, path: string, body: unknown) {
  return mock(
    new Request(BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

async function startJob(mock: MockFetch, handle: string) {
  const response = await post(mock, "/analyses", { handle, max_posts: 200 });
  return { response, job: await response.json() };
}

async function poll(mock: MockFetch, jobId: string) {
  return (await get(mock, `/analyses/${jobId}`)).json();
}

describe("createMockFetch", () => {
  it("serves health and feature flags from the fixtures", async () => {
    const mock = createMockFetch();
    const healthResponse = await get(mock, "/health");
    expect(healthResponse.status).toBe(200);
    expect(await healthResponse.json()).toEqual(health);
    expect(await (await get(mock, "/features")).json()).toEqual(features);
  });

  it("starts an analysis job as queued for the normalized handle", async () => {
    const { response, job } = await startJob(createMockFetch(), "@Demo_Finanzas");
    expect(response.status).toBe(202);
    expect(job.status).toBe("queued");
    expect(job.handle).toBe("demo_finanzas");
    expect(job.progress).toBe(0);
    expect(job.id).toBeTruthy();
  });

  it("advances a job one step per poll until done, then links the report", async () => {
    const mock = createMockFetch();
    const { job } = await startJob(mock, "demo_finanzas");
    const steps = [await poll(mock, job.id), await poll(mock, job.id), await poll(mock, job.id)];
    expect(steps.map((step) => step.status)).toEqual(["fetching", "analyzing", "done"]);
    for (const step of steps) expect(step.message).toBeTruthy();
    expect(steps[0].progress).toBeLessThan(steps[1].progress);
    expect(steps[2].progress).toBe(1);
    expect(steps[2].report_id).toBe(report.id);
    expect((await poll(mock, job.id)).status).toBe("done");
  });

  it("fails the job for the special failing handle, with an es-AR error", async () => {
    const mock = createMockFetch();
    const { job } = await startJob(mock, MOCK_FAILING_HANDLE);
    let current = job;
    for (let i = 0; i < 3 && current.status !== "failed"; i++) current = await poll(mock, job.id);
    expect(current.status).toBe("failed");
    expect(current.report_id).toBeNull();
    expect(current.error.message).toBeTruthy();
  });

  it("answers 404 with an ErrorResponse for unknown jobs, reports and paths", async () => {
    const mock = createMockFetch();
    for (const path of ["/analyses/nope", "/reports/nope", "/nope"]) {
      const response = await get(mock, path);
      expect(response.status).toBe(404);
      const body = await response.json();
      expect(body.error.code).toBe("not_found");
      expect(body.error.message).toBeTruthy();
    }
  });

  it("serves the report by id and as the latest report of any handle", async () => {
    const mock = createMockFetch();
    expect(await (await get(mock, `/reports/${report.id}`)).json()).toEqual(report);
    expect(await (await get(mock, "/accounts/cualquiera/report")).json()).toEqual(report);
  });

  it("serves trends, drafts, publications and simulations from the fixtures", async () => {
    const mock = createMockFetch();
    expect(await (await get(mock, "/trends")).json()).toEqual(trends);
    expect(await (await post(mock, "/drafts", { handle: "demo_finanzas" })).json()).toEqual(drafts);
    const published = await post(mock, "/publications", { handle: "demo_finanzas", text: "Hola" });
    expect(await published.json()).toEqual(publication);
    const simulated = await post(mock, "/simulations", { variants: ["Hola"] });
    expect(await simulated.json()).toEqual(simulation);
  });

  it("keeps jobs separate between mock instances", async () => {
    const { job } = await startJob(createMockFetch(), "demo_finanzas");
    expect((await get(createMockFetch(), `/analyses/${job.id}`)).status).toBe(404);
  });
});
