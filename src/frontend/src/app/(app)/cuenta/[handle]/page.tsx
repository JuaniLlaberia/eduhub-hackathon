import { Suspense } from "react";
import { DashboardView } from "@/components/dashboard/dashboard-view";
import { Skeleton } from "@/components/ui/skeleton";

// Screen 3 (MUST, the star of the demo): latest report of the account.
export default function DashboardPage({ params }: PageProps<"/cuenta/[handle]">) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <DashboardForHandle params={params} />
    </Suspense>
  );
}

async function DashboardForHandle({ params }: Pick<PageProps<"/cuenta/[handle]">, "params">) {
  const { handle } = await params;
  return <DashboardView handle={handle} />;
}
