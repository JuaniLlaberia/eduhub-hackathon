"use client";

import { Bookmark, Eye, EyeOff, Heart, MessageCircle, Repeat2, type LucideIcon } from "lucide-react";
import { useState } from "react";
import type { ReactionType } from "@/lib/api/types";
import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import { DemoBadge } from "./demo-badge";
import { demoSimulation } from "./real-data";
import { container, featureName, lead, section, sectionTitle } from "./styles";

const REACTIONS: Record<ReactionType, { label: string; Icon: LucideIcon; color: string }> = {
  bookmark: { label: "Lo guarda", Icon: Bookmark, color: "var(--orbit)" },
  repost: { label: "Lo comparte", Icon: Repeat2, color: "var(--orbit)" },
  reply: { label: "Responde", Icon: MessageCircle, color: "var(--signal)" },
  like: { label: "Le da me gusta", Icon: Heart, color: "var(--signal)" },
  read: { label: "Lo lee", Icon: Eye, color: "var(--muted-foreground)" },
  ignore: {
    label: "Lo ignora",
    Icon: EyeOff,
    color: "color-mix(in oklch, var(--muted-foreground) 40%, var(--background))",
  },
};

const { personas, reactions, variants, segments, best_variant_index, disclaimer } = demoSimulation;
const ageStart = (group: string) => Number.parseInt(group, 10) || 0;
const ageGroups = [...new Set(personas.map((persona) => persona.age_group))].sort(
  (a, b) => ageStart(a) - ageStart(b),
);

export function WorldSection() {
  const [variantIndex, setVariantIndex] = useState(best_variant_index ?? 0);
  const variant = variants.find((item) => item.variant_index === variantIndex) ?? variants[0];
  const reactionOf = (personaId: string) =>
    reactions.find((item) => item.persona_id === personaId && item.variant_index === variantIndex)
      ?.reaction ?? "ignore";
  const ageRates = segments.filter(
    (segment) => segment.dimension === "age_group" && segment.variant_index === variantIndex,
  );

  return (
    <section id="nova-world" aria-labelledby="nova-world-title" className={section}>
      <div className={cn(container, "grid gap-12 lg:grid-cols-12 lg:gap-10")}>
        <div className="lg:col-span-5">
          <p className={cn(featureName, "text-orbit")}>Nova World</p>
          <h2 id="nova-world-title" className={cn(sectionTitle, "mt-4")}>
            Probá tu post con una audiencia argentina.
          </h2>
          <p className={cn(lead, "mt-6")}>
            Antes de publicar, mirá cómo reaccionan perfiles sintéticos armados con datos reales de la
            Encuesta Nacional de Consumos Culturales 2022-23 (OpenARG), por edad, género y provincia.
          </p>

          <fieldset className="mt-10">
            <legend className="text-sm font-medium">Elegí una versión</legend>
            <div className="mt-3 space-y-2">
              {variants.map((item) => (
                <label
                  key={item.variant_index}
                  className={cn(
                    "has-focus-visible:ring-ring/60 block cursor-pointer rounded-lg border p-4 transition-colors has-focus-visible:ring-3",
                    item.variant_index === variantIndex
                      ? "border-orbit bg-surface-elevated"
                      : "hover:bg-surface",
                  )}
                >
                  <input
                    type="radio"
                    name="nova-world-variant"
                    className="sr-only"
                    checked={item.variant_index === variantIndex}
                    onChange={() => setVariantIndex(item.variant_index)}
                  />
                  <span className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium">Variante {item.variant_index + 1}</span>
                    <span className="text-muted-foreground tabular-nums">
                      {formatPercent(item.interaction_rate)} interactúa
                      {item.variant_index === best_variant_index && (
                        <span className="text-signal ml-2">la mejor</span>
                      )}
                    </span>
                  </span>
                  <span className="mt-2 block leading-relaxed">{item.text}</span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        <div className="bg-surface/60 rounded-2xl border p-5 sm:p-7 lg:col-span-7">
          <DemoBadge />
          <ul className="mt-6 space-y-4" aria-label={`Reacciones a la variante ${variant.variant_index + 1}`}>
            {ageGroups.map((group) => {
              const rate = ageRates.find((segment) => segment.value === group)?.interaction_rate;
              return (
                <li
                  key={group}
                  className="grid grid-cols-[6.5rem_1fr] items-center gap-4 sm:grid-cols-[7.5rem_1fr_3.5rem]"
                >
                  <span className="text-muted-foreground text-sm">{group}</span>
                  <ul className="flex flex-wrap gap-2">
                    {personas
                      .filter((persona) => persona.age_group === group)
                      .map((persona) => {
                        const reaction = REACTIONS[reactionOf(persona.id)];
                        const description = `${persona.gender}, ${persona.province}. ${persona.traits.join(", ")}. ${reaction.label}.`;
                        return (
                          <li key={persona.id}>
                            <span
                              title={description}
                              className="flex size-10 items-center justify-center rounded-full border transition-[background-color,border-color] duration-500 motion-reduce:transition-none sm:size-11"
                              style={{
                                background: `color-mix(in oklch, ${reaction.color} 18%, transparent)`,
                                borderColor: reaction.color,
                                transitionDelay: `${(personas.indexOf(persona) % 12) * 40}ms`,
                              }}
                            >
                              <reaction.Icon
                                aria-hidden="true"
                                className="size-4"
                                style={{ color: reaction.color }}
                              />
                              <span className="sr-only">{description}</span>
                            </span>
                          </li>
                        );
                      })}
                  </ul>
                  <span className="text-muted-foreground hidden text-right text-sm tabular-nums sm:block">
                    {rate === undefined ? "" : formatPercent(rate)}
                  </span>
                </li>
              );
            })}
          </ul>

          <ul className="text-muted-foreground mt-6 flex flex-wrap gap-x-4 gap-y-2 border-t pt-5 text-xs">
            {(Object.keys(REACTIONS) as ReactionType[]).map((type) => {
              const { label, Icon, color } = REACTIONS[type];
              return (
                <li key={type} className="flex items-center gap-1.5">
                  <Icon aria-hidden="true" className="size-3.5" style={{ color }} />
                  {label}
                  <span className="text-foreground tabular-nums">{variant.reaction_counts[type] ?? 0}</span>
                </li>
              );
            })}
          </ul>
          <p className="text-muted-foreground mt-4 text-xs leading-relaxed">
            El porcentaje de cada fila es la parte del grupo que interactuó. {disclaimer}
          </p>
        </div>
      </div>
    </section>
  );
}
