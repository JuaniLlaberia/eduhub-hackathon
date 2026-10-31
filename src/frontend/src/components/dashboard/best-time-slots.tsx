import { Pending, SectionCard } from "@/components/section-card";
import type { TimeSlotStat } from "@/lib/api/types";

// TODO: top 3 slots with formatTimeSlot + formatScore + post_count.
export function BestTimeSlots({ slots }: { slots: TimeSlotStat[] }) {
  return (
    <SectionCard title="Tus mejores horarios" description={`${slots.length} franjas destacadas`}>
      <Pending />
    </SectionCard>
  );
}
