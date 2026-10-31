"use client";

import type { AnalyzedPost } from "@/lib/api/types";
import { formatScore } from "@/lib/format";
import { scoreScale, scoreTier, TIER_FILL } from "./score-style";

type ScoredPost = AnalyzedPost & { score: number };

const W = 1000;
const H = 190;
const PAD = 40;
const R = 7;
const AXIS_Y = 150;
const TICKS = [0.3, 0.5, 1, 2, 3];

/** Every post on one log axis of Nova Score, stacked so none overlap (a beeswarm). */
export function ScoreStrip({
  posts,
  selectedId,
  onSelect,
}: {
  posts: ScoredPost[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const scale = scoreScale(0.25, 3.2);
  const xOf = (score: number) => PAD + scale(score) * (W - PAD * 2);
  const placed: { item: ScoredPost; x: number; y: number }[] = [];
  for (const item of [...posts].sort((a, b) => a.score - b.score)) {
    const x = xOf(item.score);
    let level = 0;
    while (
      placed.some(
        (other) => Math.abs(other.x - x) < R * 2 + 1 && other.y === AXIS_Y - 18 - level * (R * 2 + 1),
      )
    ) {
      level++;
    }
    placed.push({ item, x: Math.round(x * 10) / 10, y: AXIS_Y - 18 - level * (R * 2 + 1) });
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-label="Distribución del Nova Score de los posts">
      <line x1={PAD} x2={W - PAD} y1={AXIS_Y} y2={AXIS_Y} stroke="var(--border)" />
      {TICKS.map((tick) => (
        <g key={tick}>
          <line
            x1={xOf(tick)}
            x2={xOf(tick)}
            y1={tick === 1 ? 8 : AXIS_Y - 4}
            y2={AXIS_Y + 4}
            stroke={tick === 1 ? "var(--orbit)" : "var(--border)"}
            strokeDasharray={tick === 1 ? "3 4" : undefined}
          />
          <text
            x={xOf(tick)}
            y={AXIS_Y + 24}
            textAnchor="middle"
            className="fill-muted-foreground text-[14px]"
          >
            {formatScore(tick)}
          </text>
        </g>
      ))}
      <text x={xOf(1) + 8} y={20} className="fill-orbit text-[14px]">
        Tu post típico
      </text>
      {placed.map(({ item, x, y }) => {
        const active = item.post.id === selectedId;
        return (
          <g key={item.post.id} className="cursor-pointer" onClick={() => onSelect(item.post.id)}>
            <circle cx={x} cy={y} r={R + 3} fill="transparent" />
            {active && <circle cx={x} cy={y} r={R + 4} fill="none" stroke="var(--foreground)" />}
            <circle cx={x} cy={y} r={R} fill={TIER_FILL[scoreTier(item.score)]} />
          </g>
        );
      })}
    </svg>
  );
}
