"use client";

import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NovaLogo } from "@/components/brand/nova-logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LANDING_LINKS } from "./links";
import { container } from "./styles";

export function LandingNavbar() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <header className="bg-background/85 sticky top-0 z-40 border-b backdrop-blur-md">
      <div className={cn(container, "flex h-16 items-center justify-between gap-6")}>
        <a href="#inicio" className="rounded-sm" onClick={() => setOpen(false)}>
          <NovaLogo />
        </a>
        <nav aria-label="Secciones" className="hidden md:block">
          <ul className="text-muted-foreground flex gap-8 text-sm">
            {LANDING_LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="hover:text-foreground rounded-sm transition-colors">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild className="hidden h-9 px-4 md:inline-flex">
            <a href="#explorar">Explorar NOVA</a>
          </Button>
          <Button
            variant="ghost"
            size="icon-lg"
            className="size-11 md:hidden"
            aria-expanded={open}
            aria-controls="landing-menu"
            aria-label={open ? "Cerrar menú" : "Abrir menú"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
        </div>
      </div>
      <nav
        id="landing-menu"
        aria-label="Secciones"
        className={cn("border-t md:hidden", open ? "block" : "hidden")}
      >
        <ul className={cn(container, "flex flex-col py-3")}>
          {[...LANDING_LINKS, { href: "#explorar", label: "Explorar NOVA" }].map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                onClick={() => setOpen(false)}
                className="hover:bg-surface flex min-h-11 items-center rounded-md px-2 text-base"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
