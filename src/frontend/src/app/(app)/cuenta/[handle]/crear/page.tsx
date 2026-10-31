import { Suspense } from "react";
import { CreateView } from "@/components/create/create-view";
import { Skeleton } from "@/components/ui/skeleton";

// Screen 4 (WANTED): drafts from a recommendation (?recomendacion=<id>) or a topic, then publish.
export default function CreatePage({ params, searchParams }: PageProps<"/cuenta/[handle]/crear">) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <CreateForHandle params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function CreateForHandle({ params, searchParams }: PageProps<"/cuenta/[handle]/crear">) {
  const { handle } = await params;
  const { recomendacion } = await searchParams;
  const recommendationId = typeof recomendacion === "string" ? recomendacion : undefined;
  return <CreateView handle={handle} recommendationId={recommendationId} />;
}
