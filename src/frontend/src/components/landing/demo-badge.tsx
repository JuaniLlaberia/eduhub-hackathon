import { cn } from "@/lib/utils";
import { DEMO_LABEL } from "./real-data";

/** Marks every illustrative result on the landing, so demo data is never mistaken for a real one. */
export function DemoBadge({ className }: { className?: string }) {
  return (
    <p
      className={cn(
        "text-muted-foreground bg-background/60 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs",
        className,
      )}
    >
      <span aria-hidden="true" className="bg-orbit size-1.5 rounded-full" />
      {DEMO_LABEL}
    </p>
  );
}
