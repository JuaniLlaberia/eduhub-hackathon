// How a Nova Score (performance vs the account's typical post, 1.0 = typical) is drawn everywhere.

export type ScoreTier = "nova" | "high" | "typical" | "low";

export function scoreTier(score: number): ScoreTier {
  if (score >= 2) return "nova";
  if (score >= 1.2) return "high";
  if (score >= 0.8) return "typical";
  return "low";
}

export const TIER_FILL: Record<ScoreTier, string> = {
  nova: "#ffffff",
  high: "var(--signal)",
  typical: "var(--orbit)",
  low: "color-mix(in oklch, var(--muted-foreground) 55%, var(--background))",
};

export const TIER_LABEL: Record<ScoreTier, string> = {
  nova: "Más del doble",
  high: "Por encima de lo típico",
  typical: "Cerca de lo típico",
  low: "Por debajo",
};

/** Log scale for scores, so 0.5x and 2x sit at the same distance from 1x. */
export function scoreScale(min: number, max: number) {
  const span = Math.log(max / min);
  return (score: number) => Math.log(Math.min(max, Math.max(min, score)) / min) / span;
}
