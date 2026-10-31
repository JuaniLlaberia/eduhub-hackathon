import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import draftsFixture from "@/lib/api/fixtures/drafts_response.json";
import publishFixture from "@/lib/api/fixtures/publish_result.json";
import reportFixture from "@/lib/api/fixtures/analysis_report.json";
import trendsFixture from "@/lib/api/fixtures/trends_response.json";
import { formatDateTime } from "@/lib/format";
import { CreateView } from "./create-view";

const state = vi.hoisted(() => ({
  features: { generation: true, publishing: true, simulation: true, demo_mode: false },
  drafts: undefined as unknown,
  createDrafts: vi.fn(),
  publish: vi.fn(),
}));

vi.mock("@/lib/api/queries", () => ({
  useLatestReport: () => ({ data: reportFixture, isPending: false, error: null }),
  useFeatures: () => ({ data: state.features }),
  useTrends: () => ({ data: trendsFixture }),
  useCreateDrafts: () => ({ mutate: state.createDrafts, data: state.drafts, isPending: false, error: null }),
  usePublish: () => ({ mutate: state.publish, isPending: false, error: null }),
}));

const open = vi.fn();

beforeEach(() => {
  state.features = { generation: true, publishing: true, simulation: true, demo_mode: false };
  state.drafts = undefined;
  state.createDrafts.mockReset();
  state.publish.mockReset();
  open.mockReset();
  vi.stubGlobal("open", open);
});

describe("CreateView · start", () => {
  it("starts from the recommendation it came from", async () => {
    render(<CreateView handle="demo_finanzas" recommendationId="rec-2" />);
    expect(screen.getByText("Publicá más sobre tu tema más fuerte esta semana")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Generar 3 borradores" }));
    expect(state.createDrafts).toHaveBeenCalledWith({
      handle: "demo_finanzas",
      recommendation_id: "rec-2",
      topic: null,
      instructions: null,
      count: 3,
      context: null,
    });
  });

  it("starts from a topic, and a trend fills the topic", async () => {
    render(<CreateView handle="demo_finanzas" />);
    const generate = screen.getByRole("button", { name: "Generar 3 borradores" });
    expect(generate).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "#Aguinaldo" }));
    expect(screen.getByLabelText("Sobre qué querés publicar")).toHaveValue("#Aguinaldo");
    await userEvent.click(generate);
    expect(state.createDrafts).toHaveBeenCalledWith({
      handle: "demo_finanzas",
      recommendation_id: null,
      topic: "#Aguinaldo",
      instructions: null,
      count: 3,
      context: null,
    });
  });

  it("can start from a topic given in the link", () => {
    render(<CreateView handle="demo_finanzas" initialTopic="Post para el domingo" />);
    expect(screen.getByLabelText("Sobre qué querés publicar")).toHaveValue("Post para el domingo");
  });

  it("explains when generation is turned off", () => {
    state.features = { ...state.features, generation: false };
    render(<CreateView handle="demo_finanzas" />);
    expect(screen.getByText("Crear posts no está disponible ahora.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Generar 3 borradores" })).not.toBeInTheDocument();
  });
});

describe("CreateView · drafts", () => {
  beforeEach(() => {
    state.drafts = draftsFixture;
  });

  it("shows every draft as editable text with its reason, suggested time and estimated score", () => {
    render(<CreateView handle="demo_finanzas" />);
    expect(screen.getByLabelText("Borrador 1")).toHaveValue(draftsFixture.drafts[0].text);
    expect(screen.getByLabelText("Borrador 3")).toBeInTheDocument();
    expect(screen.getAllByText(draftsFixture.drafts[0].rationale).length).toBeGreaterThan(0);
    expect(screen.getAllByText(new RegExp(formatDateTime("2026-11-05T00:00:00Z"))).length).toBeGreaterThan(0);
    expect(screen.getAllByText("2,0x").length).toBeGreaterThan(0);
  });

  it("publishes the edited text by opening the X compose window", async () => {
    render(<CreateView handle="demo_finanzas" />);
    const first = screen.getByLabelText("Borrador 1");
    await userEvent.clear(first);
    await userEvent.type(first, "Hola");
    await userEvent.click(screen.getAllByRole("button", { name: "Publicar en X" })[0]);
    expect(state.publish).toHaveBeenCalledWith(
      { handle: "demo_finanzas", text: "Hola", scheduled_for: null },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    state.publish.mock.calls[0][1].onSuccess(publishFixture);
    expect(open).toHaveBeenCalledWith(publishFixture.url, "_blank", "noopener");
  });

  it("schedules at the suggested time and confirms it", async () => {
    render(<CreateView handle="demo_finanzas" />);
    await userEvent.click(screen.getAllByRole("button", { name: "Programar" })[0]);
    expect(state.publish).toHaveBeenCalledWith(
      { handle: "demo_finanzas", text: draftsFixture.drafts[0].text, scheduled_for: "2026-11-05T00:00:00Z" },
      expect.anything(),
    );
    state.publish.mock.calls[0][1].onSuccess({
      status: "scheduled",
      post_id: null,
      url: null,
      scheduled_for: "2026-11-05T00:00:00Z",
      error: null,
    });
    expect(
      await screen.findByText(`Programado para ${formatDateTime("2026-11-05T00:00:00Z")}.`),
    ).toBeInTheDocument();
  });

  it("hides publishing when /features turns it off", () => {
    state.features = { ...state.features, publishing: false };
    render(<CreateView handle="demo_finanzas" />);
    expect(screen.queryByRole("button", { name: "Publicar en X" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Programar" })).not.toBeInTheDocument();
  });
});
