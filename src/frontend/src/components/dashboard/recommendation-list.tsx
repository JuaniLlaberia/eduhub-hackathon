import Link from "next/link";
import { SectionCard } from "@/components/section-card";
import { Button } from "@/components/ui/button";
import type { Recommendation } from "@/lib/api/types";

// TODO: sort by priority (1 first), insightCategoryLabel badge, hide the button when features.generation is off.
export function RecommendationList({
  handle,
  recommendations,
}: {
  handle: string;
  recommendations: Recommendation[];
}) {
  return (
    <SectionCard title="Qué hacer ahora">
      <ul className="flex flex-col gap-4">
        {recommendations.map((recommendation) => (
          <li key={recommendation.id} className="flex items-start justify-between gap-4">
            <div>
              <p className="font-medium">{recommendation.action}</p>
              <p className="text-muted-foreground text-sm">{recommendation.rationale}</p>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href={`/cuenta/${handle}/crear?recomendacion=${recommendation.id}`}>
                Crear post con esto
              </Link>
            </Button>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}
