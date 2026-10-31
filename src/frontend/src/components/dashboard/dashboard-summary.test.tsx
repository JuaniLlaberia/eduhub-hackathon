import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import fixture from "@/lib/api/fixtures/analysis_report.json";
import type { AnalysisReport, FeatureFlags } from "@/lib/api/types";
import { DashboardScreen } from "./dashboard-screen";

const report = fixture as unknown as AnalysisReport;
const features: FeatureFlags = { generation: true, publishing: true, simulation: true, demo_mode: false };

describe("DashboardScreen · summary and evidence", () => {
  it("shows the AI summary of the analysis on Inicio", () => {
    render(<DashboardScreen report={report} features={features} />);
    expect(screen.getByText(report.summary)).toBeInTheDocument();
  });

  it("shows the evidence of every insight in Qué te funciona", async () => {
    render(<DashboardScreen report={report} features={features} />);
    await userEvent.click(screen.getByRole("button", { name: "Qué te funciona" }));
    const insight = report.insights[0];
    const article = screen.getByRole("article", { name: insight.title });
    for (const item of insight.evidence) {
      expect(within(article).getByText(item.label)).toBeInTheDocument();
      expect(within(article).getByText(item.value)).toBeInTheDocument();
    }
  });
});
