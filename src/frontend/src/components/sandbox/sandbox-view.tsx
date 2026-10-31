"use client";

// Screen 5 (STRETCH): 2–3 variants against the synthetic audience. It compares variants; it never predicts.
// Behavior: sandbox-view.test.tsx.
import Link from "next/link";
import { useState } from "react";
import { AGE_GROUPS } from "@/components/dashboard/onboarding/brief";
import { primaryButton } from "@/components/dashboard/sections/shared";
import { useFeatures, useLatestReport, useSimulate } from "@/lib/api/queries";
import type { SimulationResult } from "@/lib/api/types";
import { formatPercent } from "@/lib/format";

const MAX_VARIANTS = 3;
const AUDIENCE_SIZE = 50;

function Result({ result, variants }: { result: SimulationResult; variants: string[] }) {
  const ages = AGE_GROUPS.filter((age) =>
    result.segments.some((s) => s.dimension === "age_group" && s.value === age),
  );
  const rate = (age: string, variant: number) =>
    result.segments.find((s) => s.dimension === "age_group" && s.value === age && s.variant_index === variant)
      ?.interaction_rate ?? null;
  const max = Math.max(...result.variants.map((v) => v.interaction_rate), 0.01);

  return (
    <section aria-label="Resultado" className="mt-14">
      <h2 className="text-[22px] font-semibold tracking-[-0.015em]">Cómo reaccionó la audiencia.</h2>
      <p className="mt-3 text-[17px] leading-relaxed">{result.summary}</p>

      <div className="mt-6">
        {result.variants.map((variant) => {
          const best = variant.variant_index === result.best_variant_index;
          return (
            <div
              key={variant.variant_index}
              className="grid grid-cols-[28px_minmax(0,1fr)_90px] items-baseline gap-4 border-t border-[#232738] py-5"
            >
              <span className="text-muted-foreground font-mono text-sm">{variant.variant_index + 1}</span>
              <div className="min-w-0">
                <p className="line-clamp-2 text-[15px] leading-relaxed">
                  {variant.text || variants[variant.variant_index]}
                </p>
                <div className="mt-3 h-2 bg-[#151827]">
                  <div
                    className="h-2"
                    style={{
                      width: `${(variant.interaction_rate / max) * 100}%`,
                      background: best ? "#70dce7" : "#a998ff",
                    }}
                  />
                </div>
                {best && <p className="mt-2 text-[13px] text-[#70dce7]">Mejor variante</p>}
              </div>
              <span className="text-right font-mono text-[17px]">
                {formatPercent(variant.interaction_rate)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-muted-foreground border-t border-[#232738] pt-3 text-[13px]">
        Porcentaje de la audiencia simulada que interactuó con cada variante.
      </p>

      {ages.length > 0 && (
        <table aria-label="Por edad" className="mt-10 w-full border-collapse text-[15px]">
          <caption className="mb-3 text-left text-[17px] font-medium">Por edad</caption>
          <thead>
            <tr className="text-muted-foreground text-left text-[13px]">
              <th scope="col" className="pb-2.5 font-normal">
                Edad
              </th>
              {result.variants.map((v) => (
                <th key={v.variant_index} scope="col" className="pb-2.5 text-right font-normal">
                  Variante {v.variant_index + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ages.map((age) => (
              <tr key={age} className="border-t border-[#232738]">
                <td className="py-3">{age}</td>
                {result.variants.map((v) => (
                  <td key={v.variant_index} className="py-3 text-right font-mono">
                    {formatPercent(rate(age, v.variant_index))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="text-muted-foreground mt-8 border-l border-[#a998ff] pl-3 text-sm leading-relaxed">
        {result.disclaimer}
      </p>
    </section>
  );
}

export function SandboxView({ handle }: { handle: string }) {
  const { data: report } = useLatestReport(handle);
  const { data: features } = useFeatures();
  const simulation = useSimulate();
  const [variants, setVariants] = useState(["", ""]);
  const [ages, setAges] = useState<string[] | null>(null);
  const briefAges = report?.context?.audience_filters?.age_groups ?? [];
  const selectedAges = ages ?? briefAges;

  if (features && !features.simulation) {
    return (
      <div className="py-10">
        <p className="text-[17px]">Probar en Nova World no está disponible ahora.</p>
        <Link
          href={`/cuenta/${handle}`}
          className="text-muted-foreground mt-3 inline-block underline underline-offset-4"
        >
          Volver a tu análisis
        </Link>
      </div>
    );
  }

  const filled = variants.map((v) => v.trim()).filter(Boolean);
  const toggleAge = (age: string) =>
    setAges(selectedAges.includes(age) ? selectedAges.filter((a) => a !== age) : [...selectedAges, age]);

  function run() {
    const filters = report?.context?.audience_filters;
    simulation.mutate({
      handle,
      variants: filled,
      audience_size: AUDIENCE_SIZE,
      filters: {
        age_groups: selectedAges,
        genders: filters?.genders ?? [],
        provinces: filters?.provinces ?? [],
      },
      context: report?.context ?? null,
    });
  }

  return (
    <div className="mx-auto max-w-[760px] pb-20">
      <Link
        href={`/cuenta/${handle}`}
        className="text-muted-foreground text-sm underline-offset-4 hover:underline"
      >
        Volver a tu análisis
      </Link>
      <h1 className="mt-6 text-[40px] leading-[1.1] font-semibold tracking-[-0.03em]">
        Probar en Nova World.
      </h1>
      <p className="text-muted-foreground mt-3 text-[17px] leading-relaxed">
        Escribí 2 o 3 versiones de un post y mirá cuál prefiere una audiencia sintética argentina. Sirve para
        comparar, no para predecir.
      </p>

      <section aria-label="Variantes" className="mt-10">
        {variants.map((value, index) => (
          <div key={index} className="border-t border-[#232738] py-5">
            <label htmlFor={`variant-${index}`} className="text-muted-foreground text-sm">
              Variante {index + 1}
            </label>
            <textarea
              id={`variant-${index}`}
              rows={3}
              value={value}
              onChange={(event) =>
                setVariants(variants.map((v, i) => (i === index ? event.target.value : v)))
              }
              placeholder="El texto del post"
              className="focus-visible:border-foreground mt-2 block w-full resize-y border-0 border-b border-[#3f4459] bg-transparent pb-3 text-[17px] leading-relaxed outline-none placeholder:text-[#5d6380]"
            />
          </div>
        ))}
        {variants.length < MAX_VARIANTS && (
          <button
            type="button"
            onClick={() => setVariants([...variants, ""])}
            className="border-t border-[#232738] py-4 text-[15px] underline underline-offset-4"
          >
            Agregar variante
          </button>
        )}
      </section>

      <fieldset className="mt-8">
        <legend className="text-muted-foreground text-sm">Edades de la audiencia</legend>
        <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1">
          {AGE_GROUPS.map((age) => {
            const checked = selectedAges.includes(age);
            return (
              <button
                key={age}
                type="button"
                role="checkbox"
                aria-checked={checked}
                onClick={() => toggleAge(age)}
                className="flex min-h-11 items-center gap-2.5 text-base"
              >
                <span
                  aria-hidden
                  className={`size-4 shrink-0 rounded-[3px] ${checked ? "bg-foreground" : "border-[1.5px] border-[#4a5070]"}`}
                />
                <span className={checked ? "text-foreground" : "text-muted-foreground"}>{age}</span>
              </button>
            );
          })}
        </div>
        <p className="text-muted-foreground mt-2 text-[13px]">Sin edades elegidas, probamos con todas.</p>
      </fieldset>

      <button
        type="button"
        onClick={run}
        disabled={filled.length < 2 || simulation.isPending}
        className={`${primaryButton} mt-8 disabled:opacity-50`}
      >
        {simulation.isPending ? "Simulando…" : "Probar variantes"}
      </button>
      {simulation.error && (
        <p role="alert" className="text-destructive mt-4 text-[15px]">
          No pudimos correr la simulación. Probá de nuevo en unos segundos.
        </p>
      )}

      {simulation.data && <Result result={simulation.data} variants={filled} />}
    </div>
  );
}
