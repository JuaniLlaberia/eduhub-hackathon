import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import analyzing from "@/lib/api/fixtures/analysis_job_analyzing.json";
import done from "@/lib/api/fixtures/analysis_job_done.json";
import failed from "@/lib/api/fixtures/analysis_job_failed.json";
import queued from "@/lib/api/fixtures/analysis_job_queued.json";
import { AnalysisProgress } from "./analysis-progress";

const state = vi.hoisted(() => ({ job: undefined as unknown, error: null as unknown, replace: vi.fn() }));

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: state.replace }) }));
vi.mock("@/lib/api/queries", () => ({
  useAnalysisJob: () => ({ data: state.job, error: state.error }),
}));

beforeEach(() => {
  state.job = undefined;
  state.error = null;
  state.replace.mockReset();
});

describe("AnalysisProgress", () => {
  it("shows the three steps, with the first one current while fetching", () => {
    state.job = queued;
    render(<AnalysisProgress jobId="job-demo-1" />);
    expect(screen.getByRole("heading", { level: 1, name: "Estamos leyendo tus posts." })).toBeInTheDocument();
    const steps = within(screen.getByRole("list", { name: "Progreso del análisis" })).getAllByRole(
      "listitem",
    );
    expect(steps.map((s) => s.textContent)).toEqual([
      expect.stringContaining("Buscar tus posts"),
      expect.stringContaining("Analizar qué te funciona"),
      expect.stringContaining("Armar tus recomendaciones"),
    ]);
    expect(steps[0]).toHaveAttribute("aria-current", "step");
  });

  it("marks the analysis step and shows the backend message while analyzing", () => {
    state.job = analyzing;
    render(<AnalysisProgress jobId="job-demo-1" />);
    const steps = within(screen.getByRole("list", { name: "Progreso del análisis" })).getAllByRole(
      "listitem",
    );
    expect(steps[1]).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Calculando métricas y patrones")).toBeInTheDocument();
  });

  it("goes to the dashboard of the account when the job is done", () => {
    state.job = done;
    render(<AnalysisProgress jobId="job-demo-1" />);
    expect(state.replace).toHaveBeenCalledWith("/cuenta/demo_finanzas");
  });

  it("shows the es-AR error and a way to try again when the job fails", () => {
    state.job = failed;
    render(<AnalysisProgress jobId="job-demo-1" />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "No pudimos obtener los posts. Probá de nuevo en unos minutos.",
    );
    expect(screen.getByRole("link", { name: "Probar de nuevo" })).toHaveAttribute(
      "href",
      "/empezar?handle=demo_finanzas",
    );
    expect(state.replace).not.toHaveBeenCalled();
  });
});
