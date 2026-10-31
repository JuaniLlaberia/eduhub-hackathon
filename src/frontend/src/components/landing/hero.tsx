import { PostSky } from "@/components/report/post-sky";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { demoHandle, scoredPosts } from "./real-data";
import { container, lead } from "./styles";

export function Hero() {
  return (
    <section id="inicio" aria-labelledby="hero-title" className="relative scroll-mt-16 overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-1/3 -z-10 mx-auto h-[36rem] max-w-5xl rounded-full bg-[radial-gradient(ellipse_at_center,color-mix(in_oklch,var(--orbit)_14%,transparent),transparent_65%)]"
      />
      <div className={cn(container, "pt-14 pb-20 lg:pt-20 lg:pb-24")}>
        <div className="grid gap-8 lg:grid-cols-12 lg:items-end lg:gap-10">
          <h1
            id="hero-title"
            className="text-[clamp(2.75rem,6.4vw,5.4rem)] leading-[0.98] font-semibold tracking-[-0.038em] text-balance lg:col-span-7"
          >
            Descubrí qué hace brillar tus posts.
          </h1>
          <div className="lg:col-span-5 lg:pb-2">
            <p className={lead}>
              NOVA analiza tu cuenta de X, te explica por qué funcionó cada publicación y te ayuda a crear y
              probar la próxima antes de publicarla.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild className="h-11 px-5 text-base">
                <a href="#explorar">Explorar NOVA</a>
              </Button>
              <Button asChild variant="outline" className="h-11 px-5 text-base">
                <a href="#como-funciona">Cómo funciona</a>
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-14 lg:mt-16">
          <PostSky
            posts={scoredPosts}
            caption={`Los ${scoredPosts.length} posts de @${demoHandle}, una cuenta de demostración. Cuanto más arriba, mejor rindió frente a su post típico; cuanto más grande, más vistas tuvo. Pasá el mouse o tocá una estrella.`}
          />
        </div>
      </div>
    </section>
  );
}
