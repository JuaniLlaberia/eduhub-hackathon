// What the landing shows: contract fixtures (C6) with exactly the shape the backend returns, for the demo
// account @demo_finanzas. They come from the shared fakes, so the UI always labels them as a demo account.
import draftsJson from "@/lib/api/fixtures/drafts_response.json";
import reportJson from "@/lib/api/fixtures/analysis_report.json";
import simulationJson from "@/lib/api/fixtures/simulation_result.json";
import type { AnalysisReport, AnalyzedPost, DraftsResponse, SimulationResult } from "@/lib/api/types";

export const DEMO_LABEL = "Vista de demostración: resultados ilustrativos";

export const demoReport = reportJson as AnalysisReport;
export const demoDrafts = (draftsJson as DraftsResponse).drafts;
export const demoSimulation = simulationJson as SimulationResult;

export const demoHandle = demoReport.profile.handle;

/** Posts that have a score, best first. */
export const scoredPosts: (AnalyzedPost & { score: number })[] = demoReport.posts
  .filter((item): item is AnalyzedPost & { score: number } => item.score !== null)
  .sort((a, b) => b.score - a.score);

export const bestPost = scoredPosts[0];
export const worstPost = scoredPosts[scoredPosts.length - 1];
/** The post closest to 1.0x: the account's typical post. */
export const typicalPost = scoredPosts.reduce((closest, item) =>
  Math.abs(Math.log(item.score)) < Math.abs(Math.log(closest.score)) ? item : closest,
);

/** The recommendation the "Crear" demo starts from: the account's strongest topic. */
export const demoRecommendation =
  demoReport.recommendations.find((item) => item.category === "topic") ?? demoReport.recommendations[0];
