import { cn } from "@/lib/utils";

/** The "O" of the wordmark: an eclipse ring with a bright point breaking out of it. */
export function NovaMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("inline-block", className)}>
      <circle cx="16" cy="16" r="11.5" fill="none" stroke="currentColor" strokeWidth="4.5" />
      <circle cx="24.6" cy="8.4" r="3.4" fill="var(--signal)" />
    </svg>
  );
}

/** NOVA wordmark. Scales with font-size. */
export function NovaLogo({ className }: { className?: string }) {
  return (
    <span
      role="img"
      aria-label="NOVA"
      className={cn(
        "inline-flex items-center text-xl leading-none font-semibold tracking-[0.06em]",
        className,
      )}
    >
      <span aria-hidden="true">N</span>
      <NovaMark className="mx-[0.06em] size-[0.86em]" />
      <span aria-hidden="true">VA</span>
    </span>
  );
}
