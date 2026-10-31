// Inicio's hero: every post as a star (x = date, y = Nova Score on a log scale), the best original called out.
import type { AnalysisReport, AnalyzedPost } from "@/lib/api/types";
import { formatDateTime, formatScore } from "@/lib/format";
import { mediaTypeLabel } from "@/lib/labels";
import { scoreColor } from "./shared";

const MIN_SCORE = 0.1;

function starStyle(score: number): React.CSSProperties {
  const size = score >= 2 ? 3 + Math.min(5, score) : score >= 1.2 ? 4 : score >= 0.8 ? 3.5 : 3;
  const glow =
    score >= 4
      ? "0 0 10px 2px rgba(169,152,255,0.7)"
      : score >= 2
        ? "0 0 6px rgba(169,152,255,0.45)"
        : "none";
  return { width: size, height: size, background: scoreColor(score), boxShadow: glow };
}

export function PostSky({ report, best }: { report: AnalysisReport; best: AnalyzedPost | undefined }) {
  const scored = report.posts.filter((p) => p.score !== null);
  const times = scored.map((p) => new Date(p.post.created_at).getTime());
  const start = report.kpis.period_start ? new Date(report.kpis.period_start).getTime() : Math.min(...times);
  const end = report.kpis.period_end ? new Date(report.kpis.period_end).getTime() : Math.max(...times);
  const maxScore = Math.max(11, ...scored.map((p) => p.score ?? 0));
  const span = Math.log(maxScore / MIN_SCORE);
  const x = (p: AnalyzedPost) =>
    1 + (end > start ? (new Date(p.post.created_at).getTime() - start) / (end - start) : 0.5) * 98;
  const y = (score: number) =>
    (1 - Math.log(Math.min(maxScore, Math.max(MIN_SCORE, score)) / MIN_SCORE) / span) * 100;
  const typical = y(1);
  const bestX = best ? x(best) : 0;
  const bestY = best ? y(best.score ?? 1) : 0;
  const calloutLeft = bestX < 60;

  return (
    <figure className="mt-10">
      <div
        role="img"
        aria-label={`${scored.length} posts. Más arriba, más rindieron frente a tu post típico.`}
        className="relative h-[340px] border-b border-[#232738]"
      >
        <div
          className="absolute inset-x-0 border-t border-dashed border-[#343a50]"
          style={{ top: `${typical}%` }}
        />
        <span
          className="text-muted-foreground absolute left-0 -translate-y-[150%] text-xs"
          style={{ top: `${typical}%` }}
        >
          tu post típico
        </span>
        {scored.map((p) => (
          <span
            key={p.post.id}
            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{ left: `${x(p)}%`, top: `${y(p.score ?? 0)}%`, ...starStyle(p.score ?? 0) }}
          />
        ))}
        {best && (
          <a
            href={best.post.url}
            target="_blank"
            rel="noreferrer"
            className="absolute w-[260px] -translate-y-3.5 no-underline"
            style={
              calloutLeft
                ? { left: `calc(${bestX}% + 24px)`, top: `${bestY}%` }
                : { right: `calc(${100 - bestX}% + 24px)`, top: `${bestY}%` }
            }
          >
            <span className="block font-mono text-[22px] text-white">{formatScore(best.score)}</span>
            <span className="mt-1.5 line-clamp-2 block text-sm leading-snug text-[#d9dcea]">
              “{best.post.text}”
            </span>
            <span className="text-muted-foreground mt-1.5 block text-xs">
              Tu mejor post original: {mediaTypeLabel(best.features.media_type).toLowerCase()},{" "}
              {formatDateTime(best.post.created_at)}
            </span>
          </a>
        )}
      </div>
      <figcaption className="text-muted-foreground mt-2.5 text-[13px]">
        Cada punto es un post. Más arriba, más rindió frente a tu post típico.
      </figcaption>
    </figure>
  );
}
