"use client";

import { useMemo, useState, type CSSProperties } from "react";
import type { AnalyzedPost } from "@/lib/api/types";
import { formatDateTime, formatNumber, formatScore } from "@/lib/format";
import { cn } from "@/lib/utils";
import { scoreScale, scoreTier, TIER_FILL, type ScoreTier } from "./score-style";
import "./post-sky.css";

type ScoredPost = AnalyzedPost & { score: number };

interface Geometry {
  id: string;
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
  font: number;
}

/** Wide sky for tablets and up; a taller, narrower one for phones so stars and labels stay legible. */
const WIDE: Geometry = {
  id: "wide",
  width: 1000,
  height: 420,
  left: 56,
  right: 24,
  top: 24,
  bottom: 44,
  font: 13,
};
const NARROW: Geometry = {
  id: "narrow",
  width: 400,
  height: 330,
  left: 40,
  right: 8,
  top: 18,
  bottom: 34,
  font: 12,
};

const SCORE_MIN = 0.25;
const SCORE_MAX = 3.2;
const GUIDES = [0.5, 1, 2];
const scale = scoreScale(SCORE_MIN, SCORE_MAX);
// Ticks sit on the 1st of each month in UTC, so they are labelled in UTC too.
const month = new Intl.DateTimeFormat("es-AR", { month: "short", timeZone: "UTC" });
const round = (value: number) => Math.round(value * 10) / 10;

interface Star {
  item: ScoredPost;
  x: number;
  y: number;
  r: number;
  tier: ScoreTier;
  delay: number;
}

function layout(posts: ScoredPost[], geometry: Geometry) {
  const { width, height, left, right, top, bottom } = geometry;
  const times = posts.map((item) => new Date(item.post.created_at).getTime());
  const start = Math.min(...times);
  const end = Math.max(...times);
  const views = Math.max(...posts.map((item) => item.post.metrics.impressions ?? 0), 1);
  const xOf = (time: number) => left + ((time - start) / Math.max(1, end - start)) * (width - left - right);
  const yOf = (score: number) => top + (1 - scale(score)) * (height - top - bottom);
  const ticks: { x: number; label: string }[] = [];
  for (const day = new Date(start); day.getTime() <= end; day.setUTCDate(day.getUTCDate() + 1)) {
    if (day.getUTCDate() === 1) ticks.push({ x: xOf(day.getTime()), label: `1 ${month.format(day)}` });
  }
  const stars: Star[] = posts.map((item) => {
    const x = xOf(new Date(item.post.created_at).getTime());
    return {
      item,
      x: round(x),
      y: round(yOf(item.score)),
      r: round(2.2 + 5.5 * Math.sqrt((item.post.metrics.impressions ?? 0) / views)),
      tier: scoreTier(item.score),
      delay: 0.15 + ((x - left) / (width - left - right)) * 1.3,
    };
  });
  return { stars, ticks, yOf };
}

/** Each post is a star: higher = better than the account's typical post (1.0x), bigger = more views. */
export function PostSky({ posts, caption }: { posts: ScoredPost[]; caption: string }) {
  const wide = useMemo(() => layout(posts, WIDE), [posts]);
  const narrow = useMemo(() => layout(posts, NARROW), [posts]);
  const tabbable = useMemo(
    () => new Set([...posts.slice(0, 6), posts.at(-1)].map((item) => item?.post.id)),
    [posts],
  );
  const [selectedId, setSelectedId] = useState(posts[0]?.post.id);
  const selected = wide.stars.find((star) => star.item.post.id === selectedId) ?? wide.stars[0];
  if (!selected) return null;

  const chart = (geometry: Geometry, data: ReturnType<typeof layout>, className: string) => (
    <SkyChart
      geometry={geometry}
      data={data}
      caption={caption}
      selectedId={selected.item.post.id}
      onSelect={setSelectedId}
      tabbable={tabbable}
      className={className}
    />
  );

  return (
    <figure className="w-full">
      <div className="relative">
        {chart(WIDE, wide, "hidden sm:block")}
        {chart(NARROW, narrow, "sm:hidden")}
        <PostCard
          item={selected.item}
          className={cn(
            "pointer-events-none absolute hidden w-64 sm:block",
            selected.x > WIDE.width * 0.72
              ? "-translate-x-full"
              : selected.x < WIDE.width * 0.28
                ? ""
                : "-translate-x-1/2",
            selected.y < WIDE.height * 0.42 ? "translate-y-5" : "-translate-y-[calc(100%+1.25rem)]",
          )}
          style={{ left: `${(selected.x / WIDE.width) * 100}%`, top: `${(selected.y / WIDE.height) * 100}%` }}
        />
      </div>
      <PostCard item={selected.item} className="mt-4 sm:hidden" />
      <figcaption className="text-muted-foreground mt-4 text-sm leading-relaxed">{caption}</figcaption>
    </figure>
  );
}

function SkyChart({
  geometry,
  data,
  caption,
  selectedId,
  onSelect,
  tabbable,
  className,
}: {
  geometry: Geometry;
  data: ReturnType<typeof layout>;
  caption: string;
  selectedId: string;
  onSelect: (id: string) => void;
  tabbable: Set<string | undefined>;
  className: string;
}) {
  const { width, height, left, right, font, id } = geometry;
  const fontSize = { fontSize: font };
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={cn("w-full overflow-visible", className)}
      aria-labelledby={`post-sky-title-${id}`}
    >
      <title id={`post-sky-title-${id}`}>{caption}</title>
      <defs>
        <radialGradient id={`post-sky-glow-${id}`}>
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
          <stop offset="30%" stopColor="var(--signal)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--orbit)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {GUIDES.map((guide) => (
        <g key={guide}>
          <line
            className="ps-line"
            pathLength={1}
            x1={left}
            x2={width - right}
            y1={data.yOf(guide)}
            y2={data.yOf(guide)}
            stroke={guide === 1 ? "var(--orbit)" : "var(--border)"}
            strokeOpacity={guide === 1 ? 0.7 : 0.6}
            strokeDasharray={guide === 1 ? undefined : "3 6"}
          />
          <text
            x={left - 8}
            y={data.yOf(guide) + 4}
            textAnchor="end"
            style={fontSize}
            className={guide === 1 ? "fill-orbit" : "fill-muted-foreground"}
          >
            {formatScore(guide)}
          </text>
        </g>
      ))}
      <text x={width - right} y={data.yOf(1) - 8} textAnchor="end" style={fontSize} className="fill-orbit">
        Tu post típico
      </text>
      {data.ticks.map((tick) => (
        <text
          key={tick.label}
          x={tick.x}
          y={height - 10}
          textAnchor="middle"
          style={fontSize}
          className="fill-muted-foreground"
        >
          {tick.label}
        </text>
      ))}

      {data.stars
        .filter((star) => star.tier === "nova")
        .map((star) => (
          <circle
            key={`glow-${star.item.post.id}`}
            className="ps-glow"
            style={{ "--delay": `${(star.delay + 0.4).toFixed(2)}s` } as CSSProperties}
            cx={star.x}
            cy={star.y}
            r={star.r * 5}
            fill={`url(#post-sky-glow-${id})`}
          />
        ))}

      {data.stars.map((star) => {
        const active = star.item.post.id === selectedId;
        return (
          <g
            key={star.item.post.id}
            className="group cursor-pointer outline-none"
            onPointerEnter={() => onSelect(star.item.post.id)}
            onFocus={() => onSelect(star.item.post.id)}
            onClick={() => onSelect(star.item.post.id)}
            tabIndex={tabbable.has(star.item.post.id) ? 0 : -1}
            role="button"
            aria-label={`Post del ${formatDateTime(star.item.post.created_at)}: ${formatScore(star.item.score)}`}
            aria-pressed={active}
          >
            <circle cx={star.x} cy={star.y} r={14} fill="transparent" />
            {active && (
              <circle
                cx={star.x}
                cy={star.y}
                r={star.r + 6}
                fill="none"
                stroke="var(--foreground)"
                strokeOpacity={0.8}
              />
            )}
            <circle
              className="ps-star group-focus-visible:stroke-[var(--ring)] group-focus-visible:stroke-[3px]"
              style={{ "--delay": `${star.delay.toFixed(2)}s` } as CSSProperties}
              cx={star.x}
              cy={star.y}
              r={star.r}
              fill={TIER_FILL[star.tier]}
            />
          </g>
        );
      })}
    </svg>
  );
}

function PostCard({
  item,
  className,
  style,
}: {
  item: ScoredPost;
  className?: string;
  style?: CSSProperties;
}) {
  const { post, score } = item;
  return (
    <div
      className={cn("bg-surface-elevated/95 rounded-xl border p-4 shadow-2xl backdrop-blur-sm", className)}
      style={style}
    >
      <p className="text-muted-foreground text-xs">{formatDateTime(post.created_at)}</p>
      <p className="mt-1 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tabular-nums">{formatScore(score)}</span>
        <span className="text-muted-foreground text-xs">frente a su post típico</span>
      </p>
      <p className="mt-2 line-clamp-3 text-sm leading-relaxed">{post.text}</p>
      <p className="text-muted-foreground mt-2 text-xs tabular-nums">
        {formatNumber(post.metrics.impressions)} vistas, {formatNumber(post.metrics.likes)} me gusta,{" "}
        {formatNumber(post.metrics.bookmarks)} guardados
      </p>
    </div>
  );
}
