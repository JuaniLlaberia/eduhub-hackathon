import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import fixture from "@/lib/api/fixtures/analysis_report.json";
import type { AnalysisReport, FeatureFlags } from "@/lib/api/types";
import { DashboardScreen } from "./dashboard-screen";

const report = fixture as unknown as AnalysisReport;
const allOn: FeatureFlags = { generation: true, publishing: true, simulation: true, demo_mode: false };
const allOff: FeatureFlags = { generation: false, publishing: false, simulation: false, demo_mode: false };

describe("DashboardScreen · Inicio", () => {
  it("greets the creator by first name", () => {
    render(<DashboardScreen report={report} features={allOn} />);
    expect(screen.getByRole("heading", { level: 1, name: "Hola, Cami." })).toBeInTheDocument();
  });

  it("lists the recommendations with low-confidence ones last, and one create button on the first", () => {
    render(<DashboardScreen report={report} features={allOn} />);
    const list = screen.getByRole("list", { name: "Qué hacer ahora" });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Publicá más sobre tu tema más fuerte esta semana");
    expect(items[3]).toHaveTextContent("Ajustá el largo de tus posts al que mejor rinde");
    const create = within(list).getAllByRole("link", { name: "Crear post con esto" });
    expect(create).toHaveLength(1);
    expect(create[0]).toHaveAttribute("href", "/cuenta/demo_finanzas/crear?recomendacion=rec-2");
  });

  it("shows the median views, not the average, as the typical post", () => {
    render(<DashboardScreen report={report} features={allOn} />);
    const numbers = screen.getByRole("region", { name: "Tus números" });
    expect(within(numbers).getByText("Vistas en un post típico")).toBeInTheDocument();
    expect(within(numbers).getByText("3.386")).toBeInTheDocument();
  });

  it("summarizes the brief and links to edit it when the report has one", () => {
    render(<DashboardScreen report={report} features={allOn} />);
    expect(screen.getByText(/Publicás para vender un producto o servicio\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Editar brief y volver a analizar" })).toHaveAttribute(
      "href",
      "/empezar?handle=demo_finanzas",
    );
  });

  it("asks to complete the profile when the report has no brief", () => {
    render(<DashboardScreen report={{ ...report, context: null }} features={allOn} />);
    expect(screen.getByRole("link", { name: "Completar perfil" })).toHaveAttribute(
      "href",
      "/empezar?handle=demo_finanzas&paso=2",
    );
  });
});

describe("DashboardScreen · features", () => {
  it("links to every enabled tool", () => {
    render(<DashboardScreen report={report} features={allOn} />);
    const nav = screen.getByRole("navigation", { name: "Secciones" });
    expect(within(nav).getByRole("link", { name: "Crear posts" })).toHaveAttribute(
      "href",
      "/cuenta/demo_finanzas/crear",
    );
    expect(within(nav).getByRole("link", { name: "Probar en Nova World" })).toHaveAttribute(
      "href",
      "/cuenta/demo_finanzas/probar",
    );
  });

  it("hides the tools that /features turns off", () => {
    render(<DashboardScreen report={report} features={allOff} />);
    expect(screen.queryByRole("link", { name: "Crear posts" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Probar en Nova World" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Crear post con esto" })).not.toBeInTheDocument();
  });
});

describe("DashboardScreen · sections", () => {
  it("switches to Cuándo publicar and warns when slots have few posts", async () => {
    render(<DashboardScreen report={report} features={allOn} />);
    await userEvent.click(screen.getByRole("button", { name: "Cuándo publicar" }));
    expect(screen.getByRole("heading", { level: 1, name: "Cuándo publicar." })).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Tus mejores horarios" });
    expect(within(table).getByText("Miércoles 21 h")).toBeInTheDocument();
    expect(within(table).getByText("1,8x")).toBeInTheDocument();
    expect(screen.getByText(/Tomalo como pista/)).toBeInTheDocument();
  });

  it("switches to Qué te funciona and changes dimension with the tabs", async () => {
    render(<DashboardScreen report={report} features={allOn} />);
    await userEvent.click(screen.getByRole("button", { name: "Qué te funciona" }));
    expect(screen.getByRole("heading", { level: 1, name: "Qué te funciona." })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Largo" }));
    expect(screen.getByRole("tab", { name: "Largo" })).toHaveAttribute("aria-selected", "true");
  });

  it("switches to Tus posts and toggles best and worst", async () => {
    render(<DashboardScreen report={report} features={allOn} />);
    await userEvent.click(screen.getByRole("button", { name: "Tus posts" }));
    expect(screen.getByRole("heading", { level: 1, name: "Tus posts." })).toBeInTheDocument();
    expect(screen.getAllByText("2,6x").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("tab", { name: "Los que menos rindieron" }));
    expect(screen.getAllByText("0,3x").length).toBeGreaterThan(0);
  });
});
