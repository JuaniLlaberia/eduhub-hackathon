import { describe, expect, it } from "vitest";
import fixture from "@/lib/api/fixtures/analysis_report.json";
import type { AnalysisReport, AnalyzedPost } from "@/lib/api/types";
import {
  firstName,
  isLowConfidenceSlot,
  orderRecommendations,
  pickHighlights,
  profileProgress,
} from "./model";

const report = fixture as unknown as AnalysisReport;

function post(id: string, score: number | null, kind: string, impressions: number): AnalyzedPost {
  const base = report.posts[0];
  return {
    ...base,
    score,
    post: {
      ...base.post,
      id,
      kind: kind as AnalyzedPost["post"]["kind"],
      metrics: { ...base.post.metrics, impressions },
    },
  };
}

describe("firstName", () => {
  it("keeps only the first word of the display name", () => {
    expect(firstName("Santiago Bilinkis ⭐⭐⭐")).toBe("Santiago");
    expect(firstName("Cami (demo) · Finanzas sin vueltas")).toBe("Cami");
  });

  it("falls back to the handle when the display name is empty", () => {
    expect(firstName("   ", "bilinkis")).toBe("@bilinkis");
  });
});

describe("orderRecommendations", () => {
  it("keeps the priority order but moves low-confidence recommendations (< 0.5) to the end", () => {
    const ordered = orderRecommendations(report.recommendations, report.insights);
    expect(ordered.map((r) => r.id)).toEqual(["rec-2", "rec-3", "rec-1", "rec-4"]);
  });

  it("treats a recommendation without known insights as confident", () => {
    const recs = [{ ...report.recommendations[0], id: "x", priority: 9, based_on_insight_ids: [] }];
    expect(orderRecommendations(recs, report.insights).map((r) => r.id)).toEqual(["x"]);
  });
});

describe("isLowConfidenceSlot", () => {
  it("flags slots backed by fewer than 5 posts", () => {
    expect(isLowConfidenceSlot({ weekday: 6, hour: 16, post_count: 2, avg_score: 5.1 })).toBe(true);
    expect(isLowConfidenceSlot({ weekday: 3, hour: 16, post_count: 5, avg_score: 0.6 })).toBe(false);
  });
});

describe("pickHighlights", () => {
  const posts = [
    post("tiny-reply", 10.9, "reply", 28),
    post("small-original", 9, "original", 999),
    post("a", 7.5, "original", 108_701),
    post("b", 5.1, "original", 11_330),
    post("c", 4, "original", 65_981),
    post("d", 0.4, "original", 4_057),
    post("e", 0.02, "original", 106_802),
    post("no-score", null, "original", 5_000),
  ];

  it("returns the best originals with at least 1.000 views, best first", () => {
    expect(pickHighlights(posts, "top").map((p) => p.post.id)).toEqual(["a", "b", "c"]);
  });

  it("returns the worst ones, worst first", () => {
    expect(pickHighlights(posts, "bottom").map((p) => p.post.id)).toEqual(["e", "d", "c"]);
  });

  it("works on the fixture report", () => {
    expect(pickHighlights(report.posts, "top")[0].post.id).toBe("1980000000000277165");
  });
});

describe("profileProgress", () => {
  it("counts the connected account as the first of 4 steps", () => {
    expect(profileProgress(null)).toEqual({ done: 1, total: 4 });
  });

  it("counts goal, offering/audience and voice/CTA as one step each", () => {
    expect(profileProgress(report.context ?? null)).toEqual({ done: 4, total: 4 });
    expect(profileProgress({ goal: "reach" } as AnalysisReport["context"])).toEqual({ done: 2, total: 4 });
  });
});
