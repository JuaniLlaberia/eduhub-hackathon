// Small building blocks shared by the dashboard sections (NOVA dashboard style: rules, no cards).

/** Color of a Nova Score: white = more than double, cyan = above typical, lilac = typical, grey = below. */
export function scoreColor(score: number): string {
  if (score >= 2) return "#ffffff";
  if (score >= 1.2) return "#70dce7";
  if (score >= 0.8) return "#a998ff";
  return "#3f4459";
}

export const rule = "border-[#232738]";
export const primaryButton =
  "inline-block rounded-[4px] bg-foreground px-[18px] py-3 text-[15px] font-medium text-background hover:bg-white";

export function SectionHeader({ title, note }: { title: string; note: string }) {
  return (
    <header className="flex flex-wrap items-baseline justify-between gap-3">
      <h1 className="text-[40px] leading-[1.1] font-semibold tracking-[-0.03em]">{title}</h1>
      <p className="text-muted-foreground text-sm">{note}</p>
    </header>
  );
}

export function SubTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[22px] font-semibold tracking-[-0.015em]">{children}</h2>;
}
