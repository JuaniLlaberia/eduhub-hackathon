// The creator brief (contract 1.2.0): onboarding answers → CreatorContext, labels and limits. Behavior: brief.test.ts.
import type { CreatorContext } from "@/components/dashboard/model";

export type CreatorGoal = NonNullable<CreatorContext["goal"]>;
export type PreferredCta = NonNullable<CreatorContext["preferred_cta"]>;

export interface BriefAnswers {
  goal: CreatorGoal | null;
  offering: string;
  targetAudience: string;
  ageGroups: string[];
  provinces: string[];
  brandVoice: string;
  avoidTopics: string[];
  preferredCta: PreferredCta | null;
}

export const EMPTY_ANSWERS: BriefAnswers = {
  goal: null,
  offering: "",
  targetAudience: "",
  ageGroups: [],
  provinces: [],
  brandVoice: "",
  avoidTopics: [],
  preferredCta: null,
};

export type BriefErrors = Partial<Record<keyof BriefAnswers, string>>;

export const GOALS: Record<CreatorGoal, string> = {
  sell: "Vender un producto o servicio",
  traffic: "Llevar gente a un link",
  reach: "Crecer en alcance",
  community: "Armar comunidad",
  launch: "Lanzar algo nuevo",
  other: "Otro",
};

export const CTAS: Record<PreferredCta, string> = {
  link: "Que entren a un link",
  reply: "Que respondan",
  save: "Que lo guarden",
  share: "Que lo compartan",
  follow: "Que te sigan",
  none: "Sin llamado a la acción",
};

const CTA_PHRASES: Record<PreferredCta, string> = {
  link: "que entren a un link",
  reply: "que te respondan",
  save: "que lo guarden",
  share: "que lo compartan",
  follow: "que te sigan",
  none: "que solo te lean",
};

/** Values the simulator matches (ENCC personas), from the stage 11 hand-off. */
export const AGE_GROUPS = ["13 a 17 años", "18 a 29 años", "30 a 49 años", "50 a 64 años", "65 años y mas"];
export const PROVINCES = [
  "Buenos Aires",
  "Catamarca",
  "Chaco",
  "Chubut",
  "Ciudad Autónoma de Buenos Aires",
  "Corrientes",
  "Córdoba",
  "Entre Ríos",
  "Formosa",
  "Jujuy",
  "La Pampa",
  "La Rioja",
  "Mendoza",
  "Misiones",
  "Neuquén",
  "Río Negro",
  "Salta",
  "San Juan",
  "San Luis",
  "Santa Cruz",
  "Santa Fe",
  "Santiago del Estero",
  "Tierra del Fuego",
  "Tucumán",
];

export const LIMITS = { offering: 500, targetAudience: 300, brandVoice: 300, topics: 10, topic: 60 };

export const goalLabel = (goal: CreatorGoal): string => GOALS[goal];
export const ctaLabel = (cta: PreferredCta): string => CTAS[cta];

const lowerFirst = (text: string) => text.charAt(0).toLowerCase() + text.slice(1);
const stripDot = (text: string) => text.replace(/[.\s]+$/, "");

/** Only the filled fields, trimmed; null when nothing was filled. */
export function buildContext(answers: BriefAnswers): CreatorContext | null {
  const context: Partial<CreatorContext> = {};
  const offering = answers.offering.trim();
  const audience = answers.targetAudience.trim();
  const voice = answers.brandVoice.trim();
  const topics = answers.avoidTopics.map((t) => t.trim()).filter(Boolean);
  if (answers.goal) context.goal = answers.goal;
  if (offering) context.offering = offering;
  if (audience) context.target_audience = audience;
  if (answers.ageGroups.length || answers.provinces.length) {
    context.audience_filters = { age_groups: answers.ageGroups, genders: [], provinces: answers.provinces };
  }
  if (voice) context.brand_voice = voice;
  if (topics.length) context.avoid_topics = topics;
  if (answers.preferredCta) context.preferred_cta = answers.preferredCta;
  return Object.keys(context).length ? (context as CreatorContext) : null;
}

/** es-AR messages for answers over the contract limits. */
export function briefErrors(answers: BriefAnswers): BriefErrors {
  const errors: BriefErrors = {};
  const tooLong = (max: number) => `Usá hasta ${max} caracteres.`;
  if (answers.offering.length > LIMITS.offering) errors.offering = tooLong(LIMITS.offering);
  if (answers.targetAudience.length > LIMITS.targetAudience) {
    errors.targetAudience = tooLong(LIMITS.targetAudience);
  }
  if (answers.brandVoice.length > LIMITS.brandVoice) errors.brandVoice = tooLong(LIMITS.brandVoice);
  if (answers.avoidTopics.length > LIMITS.topics) {
    errors.avoidTopics = `Elegí hasta ${LIMITS.topics} temas.`;
  } else if (answers.avoidTopics.some((t) => t.length > LIMITS.topic)) {
    errors.avoidTopics = `Cada tema puede tener hasta ${LIMITS.topic} caracteres.`;
  }
  return errors;
}

/** "18 a 29 años" + "30 a 49 años" → "gente de 18 a 29 y 30 a 49 años". */
function agePhrase(groups: string[]): string {
  const bare = groups.map((g) => g.replace(/ años?( y mas)?$/, (m) => (m.includes("y mas") ? " y más" : "")));
  const joined = bare.length > 1 ? `${bare.slice(0, -1).join(", ")} y ${bare[bare.length - 1]}` : bare[0];
  return `gente de ${joined} años`;
}

/** "Sos @handle. Publicás para …" built from the brief. */
export function briefSentence(handle: string, context: Partial<CreatorContext> | null): string {
  const parts = [`Sos @${handle}.`];
  if (!context) return parts[0];
  if (context.goal) parts.push(`Publicás para ${lowerFirst(GOALS[context.goal])}.`);
  if (context.offering) parts.push(`Ofrecés ${lowerFirst(stripDot(context.offering))}.`);
  const ages = context.audience_filters?.age_groups ?? [];
  if (context.target_audience) {
    parts.push(`Le hablás a ${lowerFirst(stripDot(context.target_audience))}.`);
  } else if (ages.length) {
    parts.push(`Le hablás a ${agePhrase(ages)}.`);
  }
  if (context.brand_voice) parts.push(`Tu voz: ${lowerFirst(stripDot(context.brand_voice))}.`);
  if (context.preferred_cta) parts.push(`Querés ${CTA_PHRASES[context.preferred_cta]}.`);
  return parts.join(" ");
}
