import { Suspense } from "react";
import { SandboxView } from "@/components/sandbox/sandbox-view";
import { Skeleton } from "@/components/ui/skeleton";

// Screen 5 (STRETCH): test 1–3 variants against the synthetic audience. Nothing may depend on it.
export default function SandboxPage({ params }: PageProps<"/cuenta/[handle]/probar">) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <SandboxForHandle params={params} />
    </Suspense>
  );
}

async function SandboxForHandle({ params }: Pick<PageProps<"/cuenta/[handle]/probar">, "params">) {
  const { handle } = await params;
  return <SandboxView handle={handle} />;
}
