"use client";

// Onboarding: 4 steps (account, goal, offering/audience, voice/CTA) → POST /analyses. Behavior: onboarding-flow.test.tsx.
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useCreateAnalysis } from "@/lib/api/queries";
import {
  AGE_GROUPS,
  briefErrors,
  briefSentence,
  buildContext,
  CTAS,
  EMPTY_ANSWERS,
  GOALS,
  LIMITS,
  PROVINCES,
  type BriefAnswers,
  type CreatorGoal,
  type PreferredCta,
} from "./brief";

type Step = 1 | 2 | 3 | 4;

const HANDLE = /^[a-z0-9_.]{1,30}$/;
const normalizeHandle = (raw: string) => raw.trim().replace(/^@/, "").toLowerCase();

const primary =
  "rounded-[4px] bg-foreground px-[22px] py-[13px] text-[15px] font-medium text-background hover:bg-white disabled:opacity-60";
const quiet = "py-2.5 text-[15px] text-muted-foreground underline underline-offset-4 hover:text-foreground";
const fieldLabel = "text-sm text-muted-foreground";
const textArea =
  "mt-2 block w-full resize-none border-0 border-b border-[#3f4459] bg-transparent pt-1 pb-2.5 text-[19px] outline-none placeholder:text-[#5d6380] focus-visible:border-foreground";

function Counter({ value, max }: { value: string; max: number }) {
  return (
    <span className={`font-mono text-xs ${value.length > max ? "text-destructive" : "text-[#5d6380]"}`}>
      {value.length}/{max}
    </span>
  );
}

function Radio({ checked, label, onSelect }: { checked: boolean; label: string; onSelect: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={checked}
      onClick={onSelect}
      className="flex min-h-11 w-full items-center gap-4 text-left text-[17px]"
    >
      <span
        aria-hidden
        className={`size-4 shrink-0 rounded-full ${checked ? "border-[5px] border-foreground" : "border-[1.5px] border-[#4a5070]"}`}
      />
      <span className={checked ? "text-foreground font-medium" : "text-muted-foreground"}>{label}</span>
    </button>
  );
}

export function OnboardingFlow({
  initialHandle = "",
  initialStep = 1,
}: {
  initialHandle?: string;
  initialStep?: Step;
}) {
  const router = useRouter();
  const analysis = useCreateAnalysis();
  const [step, setStep] = useState<Step>(initialHandle ? initialStep : 1);
  const [handleInput, setHandleInput] = useState(initialHandle);
  const [handle, setHandle] = useState(normalizeHandle(initialHandle));
  const [handleError, setHandleError] = useState("");
  const [answers, setAnswers] = useState<BriefAnswers>(EMPTY_ANSWERS);
  const [topicDraft, setTopicDraft] = useState("");
  const errors = briefErrors(answers);
  const hasErrors = Object.keys(errors).length > 0;

  const update = (patch: Partial<BriefAnswers>) => setAnswers((current) => ({ ...current, ...patch }));
  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

  function submit(finalAnswers: BriefAnswers) {
    analysis.mutate(
      { handle, max_posts: 200, context: buildContext(finalAnswers) },
      { onSuccess: (job) => router.push(`/analisis/${job.id}`) },
    );
  }

  function confirmHandle() {
    const value = normalizeHandle(handleInput);
    if (!HANDLE.test(value)) {
      setHandleError("Escribí un usuario de X válido.");
      return;
    }
    setHandleError("");
    setHandle(value);
    setStep(2);
  }

  function next() {
    if (hasErrors) return;
    if (step === 4) submit(answers);
    else setStep((step + 1) as Step);
  }

  function skip() {
    if (step === 4) submit(answers);
    else setStep((step + 1) as Step);
  }

  function addTopic() {
    const topic = topicDraft.trim();
    if (topic && !answers.avoidTopics.includes(topic))
      update({ avoidTopics: [...answers.avoidTopics, topic] });
    setTopicDraft("");
  }

  const actions = (primaryLabel: string) => (
    <div className="mt-10 flex flex-wrap items-center gap-7">
      <button type="button" className={primary} onClick={next} disabled={hasErrors || analysis.isPending}>
        {analysis.isPending && step === 4 ? "Enviando…" : primaryLabel}
      </button>
      <button type="button" className={quiet} onClick={skip} disabled={analysis.isPending}>
        Omitir por ahora
      </button>
      <button
        type="button"
        className="text-muted-foreground ml-auto py-2.5 text-[15px]"
        onClick={() => setStep((step - 1) as Step)}
      >
        Atrás
      </button>
    </div>
  );

  return (
    <div className="flex min-h-[80vh] flex-col">
      <div className="flex items-center justify-end">
        <p className="text-muted-foreground text-sm">Paso {step} de 4</p>
      </div>
      <div aria-hidden className="mt-4 h-px bg-[#232738]">
        <div className="bg-foreground h-px" style={{ width: `${step * 25}%` }} />
      </div>

      <div className="flex flex-1 flex-wrap gap-x-24 gap-y-12 pt-16">
        <section className="max-w-[560px] min-w-0 flex-[3_1_440px]">
          {step === 1 && (
            <>
              <h1 className="text-[44px] leading-[1.08] font-semibold tracking-[-0.035em]">
                Empecemos por tu cuenta de X.
              </h1>
              <p className="text-muted-foreground mt-4 text-[17px] leading-relaxed">
                Leemos tus posts públicos para ver qué te funciona. No publicamos nada sin que lo apruebes.
              </p>
              <label htmlFor="onboarding-handle" className={`${fieldLabel} mt-12 block`}>
                Tu usuario
              </label>
              <div className="border-foreground mt-2 flex items-baseline gap-1 border-b pb-2.5">
                <span className="text-[28px] text-[#5d6380]">@</span>
                <input
                  id="onboarding-handle"
                  value={handleInput}
                  onChange={(event) => setHandleInput(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && confirmHandle()}
                  autoComplete="off"
                  className="min-w-0 flex-1 bg-transparent text-[28px] font-medium outline-none"
                />
              </div>
              {handleError && (
                <p role="alert" className="text-destructive mt-3 text-[15px]">
                  {handleError}
                </p>
              )}
              <div className="mt-12">
                <button type="button" className={primary} onClick={confirmHandle}>
                  Continuar
                </button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h1 className="text-[44px] leading-[1.08] font-semibold tracking-[-0.035em]">
                ¿Para qué publicás?
              </h1>
              <p className="text-muted-foreground mt-4 text-[17px] leading-relaxed">
                Lo usamos para enfocar recomendaciones y borradores. No cambia tus números.
              </p>
              <div role="radiogroup" aria-label="Objetivo" className="mt-9 border-t border-[#232738]">
                {(Object.keys(GOALS) as CreatorGoal[]).map((goal) => (
                  <div key={goal} className="border-b border-[#232738] py-1.5">
                    <Radio
                      checked={answers.goal === goal}
                      label={GOALS[goal]}
                      onSelect={() => update({ goal })}
                    />
                  </div>
                ))}
              </div>
              {actions("Continuar")}
            </>
          )}

          {step === 3 && (
            <>
              <h1 className="text-[44px] leading-[1.08] font-semibold tracking-[-0.035em]">
                ¿Qué ofrecés y a quién le hablás?
              </h1>
              <p className="text-muted-foreground mt-4 text-[17px] leading-relaxed">
                Completá solo lo que te sirva. Podés cambiarlo después.
              </p>
              <div className="mt-10">
                <div className="flex justify-between">
                  <label htmlFor="onboarding-offering" className={fieldLabel}>
                    Qué ofrecés
                  </label>
                  <Counter value={answers.offering} max={LIMITS.offering} />
                </div>
                <textarea
                  id="onboarding-offering"
                  rows={2}
                  placeholder="Un producto, un servicio o una campaña"
                  value={answers.offering}
                  onChange={(event) => update({ offering: event.target.value })}
                  className={textArea}
                />
                {errors.offering && <p className="text-destructive mt-2 text-sm">{errors.offering}</p>}
              </div>
              <div className="mt-7">
                <div className="flex justify-between">
                  <label htmlFor="onboarding-audience" className={fieldLabel}>
                    A quién le hablás
                  </label>
                  <Counter value={answers.targetAudience} max={LIMITS.targetAudience} />
                </div>
                <textarea
                  id="onboarding-audience"
                  rows={2}
                  placeholder="Por ejemplo, gente que empieza a trabajar"
                  value={answers.targetAudience}
                  onChange={(event) => update({ targetAudience: event.target.value })}
                  className={textArea}
                />
                {errors.targetAudience && (
                  <p className="text-destructive mt-2 text-sm">{errors.targetAudience}</p>
                )}
              </div>
              <fieldset className="mt-7">
                <legend className={fieldLabel}>Edades</legend>
                <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1">
                  {AGE_GROUPS.map((age) => {
                    const checked = answers.ageGroups.includes(age);
                    return (
                      <button
                        key={age}
                        type="button"
                        role="checkbox"
                        aria-checked={checked}
                        onClick={() => update({ ageGroups: toggle(answers.ageGroups, age) })}
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
              </fieldset>
              <div className="mt-5 flex items-baseline gap-4">
                <label htmlFor="onboarding-province" className={fieldLabel}>
                  Dónde están
                </label>
                <select
                  id="onboarding-province"
                  value={answers.provinces[0] ?? ""}
                  onChange={(event) => update({ provinces: event.target.value ? [event.target.value] : [] })}
                  className="bg-background border-0 border-b border-[#3f4459] px-0.5 py-2 text-base"
                >
                  <option value="">Todo el país</option>
                  {PROVINCES.map((province) => (
                    <option key={province}>{province}</option>
                  ))}
                </select>
              </div>
              {actions("Continuar")}
            </>
          )}

          {step === 4 && (
            <>
              <h1 className="text-[44px] leading-[1.08] font-semibold tracking-[-0.035em]">
                ¿Cómo hablás y qué querés que hagan?
              </h1>
              <p className="text-muted-foreground mt-4 text-[17px] leading-relaxed">
                Así los borradores suenan a vos.
              </p>
              <div className="mt-10">
                <div className="flex justify-between">
                  <label htmlFor="onboarding-voice" className={fieldLabel}>
                    Tu voz
                  </label>
                  <Counter value={answers.brandVoice} max={LIMITS.brandVoice} />
                </div>
                <textarea
                  id="onboarding-voice"
                  rows={2}
                  placeholder="Por ejemplo, cercana, con humor y sin tecnicismos"
                  value={answers.brandVoice}
                  onChange={(event) => update({ brandVoice: event.target.value })}
                  className={textArea}
                />
                {errors.brandVoice && <p className="text-destructive mt-2 text-sm">{errors.brandVoice}</p>}
              </div>
              <div className="mt-7">
                <div className="flex justify-between">
                  <label htmlFor="onboarding-topics" className={fieldLabel}>
                    Temas a evitar
                  </label>
                  <span className="font-mono text-xs text-[#5d6380]">
                    {answers.avoidTopics.length}/{LIMITS.topics}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1.5 border-b border-[#3f4459] pb-2">
                  {answers.avoidTopics.map((topic) => (
                    <span key={topic} className="text-[17px]">
                      {topic}{" "}
                      <button
                        type="button"
                        aria-label={`Quitar ${topic}`}
                        onClick={() =>
                          update({ avoidTopics: answers.avoidTopics.filter((t) => t !== topic) })
                        }
                        className="text-muted-foreground px-1"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    id="onboarding-topics"
                    value={topicDraft}
                    onChange={(event) => setTopicDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        addTopic();
                      }
                    }}
                    onBlur={addTopic}
                    placeholder="Escribí un tema y apretá Enter"
                    className="min-w-[200px] flex-1 bg-transparent py-1.5 text-[17px] outline-none placeholder:text-[#5d6380]"
                  />
                </div>
                {errors.avoidTopics && <p className="text-destructive mt-2 text-sm">{errors.avoidTopics}</p>}
              </div>
              <fieldset className="mt-7">
                <legend className={fieldLabel}>Qué querés que haga la gente</legend>
                <div
                  role="radiogroup"
                  aria-label="Llamado a la acción"
                  className="mt-1.5 grid grid-cols-2 gap-x-6"
                >
                  {(Object.keys(CTAS) as PreferredCta[]).map((cta) => (
                    <Radio
                      key={cta}
                      checked={answers.preferredCta === cta}
                      label={CTAS[cta]}
                      onSelect={() => update({ preferredCta: cta })}
                    />
                  ))}
                </div>
              </fieldset>
              {analysis.error && (
                <p role="alert" className="text-destructive mt-6 text-[15px]">
                  No pudimos empezar el análisis. Probá de nuevo en unos segundos.
                </p>
              )}
              {actions("Analizar mi cuenta")}
            </>
          )}
        </section>

        <aside
          aria-label="Así te va a leer NOVA"
          className="max-w-[420px] min-w-0 flex-[2_1_300px] self-start border-l border-[#232738] pl-10"
        >
          <p className="text-muted-foreground text-sm">Así te va a leer NOVA</p>
          <p className="mt-4 text-[22px] leading-normal tracking-[-0.01em] text-[#d9dcea]">
            {handle ? briefSentence(handle, buildContext(answers)) : "Contanos tu usuario para empezar."}
          </p>
          {step > 1 && (
            <p className="text-muted-foreground mt-6 text-sm leading-relaxed">
              Lo que no completes lo podés sumar después desde Configurar perfil.
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
