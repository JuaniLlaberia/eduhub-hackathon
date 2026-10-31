// Pure rules of the dashboard (what to show and in which order). Behavior: model.test.ts.
import type { AnalysisReport, AnalyzedPost, Insight, Recommendation, TimeSlotStat } from "@/lib/api/types";

export type CreatorContext = NonNullable<AnalysisReport["context"]>;

const LOW_CONFIDENCE = 0.5;
const MIN_SLOT_POSTS = 5;
const MIN_HIGHLIGHT_VIEWS = 1000;

/** First word of the display name, or "@handle" when it is empty. */
export function firstName(displayName: string, handle = ""): string {
  const first = displayName.trim().split(/\s+/)[0];
  return first ? first : `@${handle}`;
}

/** Priority order, with recommendations whose insights all have confidence < 0.5 moved to the end. */
export function orderRecommendations(
  recommendations: Recommendation[],
  insights: Insight[],
): Recommendation[] {
  const confidence = new Map(insights.map((insight) => [insight.id, insight.confidence]));
  const isWeak = (rec: Recommendation) => {
    const known = rec.based_on_insight_ids.filter((id) => confidence.has(id));
    return known.length > 0 && known.every((id) => (confidence.get(id) ?? 1) < LOW_CONFIDENCE);
  };
  const byPriority = [...recommendations].sort((a, b) => a.priority - b.priority);
  return [...byPriority.filter((rec) => !isWeak(rec)), ...byPriority.filter(isWeak)];
}

/** A best-time slot backed by fewer than 5 posts is only a hint. */
export function isLowConfidenceSlot(slot: TimeSlotStat): boolean {
  return slot.post_count < MIN_SLOT_POSTS;
}

/** Best or worst 3 originals with at least 1.000 views and a score. */
export function pickHighlights(posts: AnalyzedPost[], side: "top" | "bottom", count = 3): AnalyzedPost[] {
  const eligible = posts.filter(
    (p) =>
      p.score !== null &&
      p.post.kind === "original" &&
      (p.post.metrics.impressions ?? 0) >= MIN_HIGHLIGHT_VIEWS,
  );
  const sign = side === "top" ? -1 : 1;
  return eligible.sort((a, b) => sign * ((a.score ?? 0) - (b.score ?? 0))).slice(0, count);
}

/** Onboarding steps done: account (always), goal, offering/audience, voice/CTA. */
export function profileProgress(context: Partial<CreatorContext> | null): {
  done: number;
  total: number;
} {
  if (!context) return { done: 1, total: 4 };
  const audience =
    !!context.offering ||
    !!context.target_audience ||
    (context.audience_filters?.age_groups?.length ?? 0) > 0 ||
    (context.audience_filters?.provinces?.length ?? 0) > 0;
  const voice = !!context.brand_voice || !!context.preferred_cta || (context.avoid_topics?.length ?? 0) > 0;
  const done = 1 + Number(!!context.goal) + Number(audience) + Number(voice);
  return { done, total: 4 };
}
