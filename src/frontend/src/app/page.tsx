import Link from "next/link";
import { HandleForm } from "@/components/landing/handle-form";

// Screen 1 (MUST): value proposition + @handle input. See docs/teams/frontend.md.
export default function LandingPage() {
  return (
    <section className="flex flex-col items-center gap-6 py-16 text-center">
      <h1 className="max-w-2xl text-4xl font-semibold tracking-tight">Analizá tu cuenta de X</h1>
      <p className="text-muted-foreground max-w-xl text-lg">
        Entendé por qué funcionan tus posts y descubrí qué, cómo y cuándo publicar.
      </p>
      <HandleForm />
      <Link href="/cuenta/demo_finanzas" className="text-muted-foreground text-sm underline">
        Ver un análisis de ejemplo
      </Link>
    </section>
  );
}
