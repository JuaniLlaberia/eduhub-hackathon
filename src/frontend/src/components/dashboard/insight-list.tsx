import { SectionCard } from "@/components/section-card";
import type { Insight } from "@/lib/api/types";

// TODO: insightCategoryLabel + impactLabel badges, evidence (label: value), confidence, related posts.
export function InsightList({ insights }: { insights: Insight[] }) {
  return (
    <SectionCard title="Por qué funcionan tus posts">
      <ul className="flex flex-col gap-4">
        {insights.map((insight) => (
          <li key={insight.id}>
            <p className="font-medium">{insight.title}</p>
            <p className="text-muted-foreground text-sm">{insight.description}</p>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}
