import Link from "next/link";
import { cn } from "@/lib/utils";
import { container, lead, section, sectionTitle } from "./styles";

// Real accounts the backend serves in DEMO_MODE (docs/teams/backend.md). Their reports open the dashboard.
const EXAMPLE_ACCOUNTS = [
  { handle: "bilinkis", name: "Santiago Bilinkis", note: "Cuenta real de X, 190 posts" },
  { handle: "demo_finanzas", name: "Finanzas sin vueltas", note: "Cuenta de demostración, 40 posts" },
];

// TODO: add the @handle form here (components/landing/handle-form.tsx) once its tests are approved and it
// starts real analyses. Until then, only link to what works.
export function ExploreCta() {
  return (
    <section id="explorar" aria-labelledby="explorar-title" className={section}>
      <div className={cn(container, "grid gap-12 lg:grid-cols-12 lg:gap-10")}>
        <div className="lg:col-span-7">
          <h2 id="explorar-title" className={sectionTitle}>
            Las mejores ideas merecen una prueba antes de despegar.
          </h2>
          <p className={cn(lead, "mt-6")}>
            NOVA ya analiza cuentas reales de X: qué publicaciones funcionan, por qué y qué conviene publicar
            después. Abrí uno de estos análisis para recorrerlo.
          </p>
        </div>
        <ul className="flex flex-col justify-end gap-3 lg:col-span-5">
          {EXAMPLE_ACCOUNTS.map((account) => (
            <li key={account.handle}>
              <Link
                href={`/cuenta/${account.handle}`}
                className="group hover:border-orbit hover:bg-surface flex items-center justify-between gap-4 rounded-xl border px-5 py-4 transition-colors"
              >
                <span>
                  <span className="block font-medium">{account.name}</span>
                  <span className="text-muted-foreground block text-sm">@{account.handle}</span>
                  <span className="text-muted-foreground mt-1 block text-xs">{account.note}</span>
                </span>
                <span className="text-orbit text-sm font-medium whitespace-nowrap">Ver análisis</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
