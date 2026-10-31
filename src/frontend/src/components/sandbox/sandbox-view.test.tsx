import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import reportFixture from "@/lib/api/fixtures/analysis_report.json";
import simulationFixture from "@/lib/api/fixtures/simulation_result.json";
import { SandboxView } from "./sandbox-view";

const state = vi.hoisted(() => ({
  features: { generation: true, publishing: true, simulation: true, demo_mode: false },
  result: undefined as unknown,
  simulate: vi.fn(),
}));

vi.mock("@/lib/api/queries", () => ({
  useLatestReport: () => ({ data: reportFixture, isPending: false, error: null }),
  useFeatures: () => ({ data: state.features }),
  useSimulate: () => ({ mutate: state.simulate, data: state.result, isPending: false, error: null }),
}));

beforeEach(() => {
  state.features = { generation: true, publishing: true, simulation: true, demo_mode: false };
  state.result = undefined;
  state.simulate.mockReset();
});

describe("SandboxView · variants", () => {
  it("starts with two variants and allows up to three", async () => {
    render(<SandboxView handle="demo_finanzas" />);
    expect(screen.getByLabelText("Variante 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Variante 2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Agregar variante" }));
    expect(screen.getByLabelText("Variante 3")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar variante" })).not.toBeInTheDocument();
  });

  it("prefills the audience ages from the brief", () => {
    render(<SandboxView handle="demo_finanzas" />);
    expect(screen.getByRole("checkbox", { name: "18 a 29 años" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("checkbox", { name: "50 a 64 años" })).toHaveAttribute("aria-checked", "false");
  });

  it("needs two filled variants, then simulates them with the brief", async () => {
    render(<SandboxView handle="demo_finanzas" />);
    const run = screen.getByRole("button", { name: "Probar variantes" });
    expect(run).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Variante 1"), "Uno");
    await userEvent.type(screen.getByLabelText("Variante 2"), "Dos");
    await userEvent.click(run);
    expect(state.simulate).toHaveBeenCalledWith({
      handle: "demo_finanzas",
      variants: ["Uno", "Dos"],
      audience_size: 50,
      filters: { age_groups: ["18 a 29 años", "30 a 49 años"], genders: [], provinces: [] },
      context: reportFixture.context,
    });
  });

  it("explains when the simulation is turned off", () => {
    state.features = { ...state.features, simulation: false };
    render(<SandboxView handle="demo_finanzas" />);
    expect(screen.getByText("Probar en Nova World no está disponible ahora.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Probar variantes" })).not.toBeInTheDocument();
  });
});

describe("SandboxView · result", () => {
  beforeEach(() => {
    state.result = simulationFixture;
  });

  it("compares the variants, marks the best one and keeps the disclaimer visible", () => {
    render(<SandboxView handle="demo_finanzas" />);
    expect(screen.getByText(simulationFixture.summary)).toBeInTheDocument();
    expect(screen.getByText(simulationFixture.disclaimer)).toBeInTheDocument();
    expect(screen.getByText("82,5%")).toBeInTheDocument();
    expect(screen.getByText("60,7%")).toBeInTheDocument();
    expect(screen.getByText("Mejor variante")).toBeInTheDocument();
  });

  it("shows the comparison by age group", () => {
    render(<SandboxView handle="demo_finanzas" />);
    const table = screen.getByRole("table", { name: "Por edad" });
    expect(table).toHaveTextContent("18 a 29 años");
  });
});
