import { CreateSection } from "@/components/landing/create-section";
import { ExploreCta } from "@/components/landing/explore-cta";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { LandingFooter } from "@/components/landing/landing-footer";
import { LandingNavbar } from "@/components/landing/landing-navbar";
import { ScoreSection } from "@/components/landing/score-section";
import { WorldSection } from "@/components/landing/world-section";

// Landing: the real product (analysis → Nova Score → drafts → Nova World) on the contract fixtures of the
// demo account. Product screens live under app/(app)/.
export default function LandingPage() {
  return (
    <>
      <a
        href="#contenido"
        className="bg-primary text-primary-foreground sr-only z-50 rounded-md px-4 py-2 focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Saltar al contenido
      </a>
      <LandingNavbar />
      <main id="contenido" className="flex-1">
        <Hero />
        <HowItWorks />
        <ScoreSection />
        <CreateSection />
        <WorldSection />
        <ExploreCta />
      </main>
      <LandingFooter />
    </>
  );
}
