"use client";

import { Pending, SectionCard } from "@/components/section-card";

// TODO (STRETCH): 1–3 text variants → POST /simulations → reactions by segment per variant.
// Hidden when features.simulation is off. Always show that it compares variants, it does not predict.
export function SandboxView({ handle }: { handle: string }) {
  return (
    <SectionCard title="Probá tus variantes" description={`@${handle} · audiencia sintética argentina`}>
      <Pending />
    </SectionCard>
  );
}
