import { Suspense } from "react";
import { OnboardingFlow } from "@/components/dashboard/onboarding/onboarding-flow";
import { Skeleton } from "@/components/ui/skeleton";

// Onboarding: connect the account and tell NOVA what you publish for. ?handle=x&paso=2 edits the brief.
export default function OnboardingPage({ searchParams }: PageProps<"/empezar">) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <OnboardingForParams searchParams={searchParams} />
    </Suspense>
  );
}

async function OnboardingForParams({ searchParams }: Pick<PageProps<"/empezar">, "searchParams">) {
  const params = await searchParams;
  const handle = typeof params.handle === "string" ? params.handle : "";
  const step = params.paso === "3" ? 3 : params.paso === "4" ? 4 : 2;
  return <OnboardingFlow initialHandle={handle} initialStep={handle ? step : 1} />;
}
