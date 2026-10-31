import type { Insight } from "@/lib/api/types";
import { insightCategoryLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";

/** An insight in es-AR with the computed evidence that backs it. */
export function InsightCard({ insight, className }: { insight: Insight; className?: string }) {
  return (
    <article className={cn("bg-surface rounded-xl border p-5", className)}>
      <p className="text-signal text-xs font-medium">{insightCategoryLabel(insight.category)}</p>
      <h3 className="mt-2 text-lg leading-snug font-semibold">{insight.title}</h3>
      <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{insight.description}</p>
      {insight.evidence.length > 0 && (
        <dl className="mt-4 grid grid-cols-2 gap-3 border-t pt-4 sm:grid-cols-3">
          {insight.evidence.map((item) => (
            <div key={item.label}>
              <dt className="text-muted-foreground text-xs">{item.label}</dt>
              <dd className="mt-1 text-lg font-semibold tabular-nums">{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}
