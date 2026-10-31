"use client";

// The dashboard: sidebar + Inicio / Cuándo publicar / Qué te funciona / Tus posts. Behavior: dashboard-screen.test.tsx.
import Link from "next/link";
import { useState } from "react";
import type { AnalysisReport, FeatureFlags } from "@/lib/api/types";
import { HomeSection } from "./sections/home-section";
import { PerformanceSection } from "./sections/performance-section";
import { PostsSection } from "./sections/posts-section";
import { ScheduleSection } from "./sections/schedule-section";

export type DashboardSection = "inicio" | "horarios" | "funciona" | "posts";

const SECTIONS: { id: DashboardSection; label: string }[] = [
  { id: "inicio", label: "Inicio" },
  { id: "horarios", label: "Cuándo publicar" },
  { id: "funciona", label: "Qué te funciona" },
  { id: "posts", label: "Tus posts" },
];

const navItem = "py-2 text-left text-[15px] transition-colors hover:text-foreground";

export function DashboardScreen({
  report,
  features,
  initialSection = "inicio",
}: {
  report: AnalysisReport;
  features: FeatureFlags;
  initialSection?: DashboardSection;
}) {
  const [section, setSection] = useState<DashboardSection>(initialSection);
  const handle = report.profile.handle;

  return (
    <div className="flex min-h-[80vh] flex-wrap">
      <aside className="flex max-w-[220px] flex-[1_1_200px] flex-col gap-11 border-r border-[#232738] py-2 pr-6">
        <nav aria-label="Secciones" className="flex flex-col">
          {SECTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-current={section === item.id ? "page" : undefined}
              onClick={() => setSection(item.id)}
              className={`${navItem} ${section === item.id ? "text-foreground font-medium" : "text-muted-foreground"}`}
            >
              {item.label}
            </button>
          ))}
          {features.generation && (
            <Link href={`/cuenta/${handle}/crear`} className={`${navItem} text-muted-foreground mt-5`}>
              Crear posts
            </Link>
          )}
          {features.simulation && (
            <Link href={`/cuenta/${handle}/probar`} className={`${navItem} text-muted-foreground`}>
              Probar en Nova World
            </Link>
          )}
        </nav>
        <div className="mt-auto text-sm">
          <p className="font-medium">@{handle}</p>
          <Link
            href={`/empezar?handle=${handle}`}
            className="text-muted-foreground inline-block py-1.5 underline-offset-4 hover:underline"
          >
            Configurar perfil
          </Link>
          <Link
            href="/empezar"
            className="text-muted-foreground block py-1.5 underline-offset-4 hover:underline"
          >
            Analizar otra cuenta
          </Link>
        </div>
      </aside>

      <div className="min-w-0 flex-[999_1_560px] px-4 pb-20 sm:px-12">
        <div className="mx-auto max-w-[980px]">
          {section === "inicio" && <HomeSection report={report} features={features} />}
          {section === "horarios" && <ScheduleSection report={report} features={features} />}
          {section === "funciona" && <PerformanceSection report={report} features={features} />}
          {section === "posts" && <PostsSection report={report} />}
        </div>
      </div>
    </div>
  );
}
