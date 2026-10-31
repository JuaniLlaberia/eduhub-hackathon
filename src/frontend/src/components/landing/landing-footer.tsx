import { NovaLogo } from "@/components/brand/nova-logo";
import { cn } from "@/lib/utils";
import { LANDING_LINKS } from "./links";
import { container } from "./styles";

// TODO: terms and privacy pages once they exist (NOVA brand brief §7.08).
export function LandingFooter() {
  return (
    <footer className="border-t py-14">
      <div className={cn(container, "flex flex-col gap-10 md:flex-row md:items-start md:justify-between")}>
        <div>
          <NovaLogo className="text-2xl" />
          <p className="text-muted-foreground mt-3">Test before it trends.</p>
        </div>
        <nav aria-label="Pie de página">
          <ul className="text-muted-foreground grid grid-cols-2 gap-x-10 gap-y-3 text-sm">
            {LANDING_LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="hover:text-foreground rounded-sm transition-colors">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <p className={cn(container, "text-muted-foreground mt-12 text-xs leading-relaxed")}>
        Prototipo desarrollado en la Hackathon EDU HUB de LABITCONF 2026. Los datos que se muestran en esta
        página son de una cuenta de demostración.
      </p>
    </footer>
  );
}
