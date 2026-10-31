// Spanish (es-AR) labels for the English enum codes of the contract. Behavior: labels.test.ts.
import type {
  Impact,
  InsightCategory,
  JobStatus,
  LengthBucket,
  MediaType,
  PostKind,
  PublishStatus,
  SegmentDimension,
} from "@/lib/api/types";

const MEDIA_TYPES: Record<NonNullable<MediaType>, string> = { photo: "Foto", video: "Video", gif: "GIF" };
const TEXT_ONLY = "Solo texto";
const LENGTH_BUCKETS: Record<LengthBucket, string> = { short: "Corto", medium: "Medio", long: "Largo" };
const POST_KINDS: Record<PostKind, string> = {
  original: "Original",
  reply: "Respuesta",
  quote: "Cita",
  repost: "Repost",
};
const SEGMENT_DIMENSIONS: Record<SegmentDimension, string> = {
  topic: "Tema",
  media_type: "Formato",
  length_bucket: "Largo",
  tone: "Tono",
  post_kind: "Tipo de post",
  hook: "Gancho",
  cta: "Llamado a la acción",
};
const INSIGHT_CATEGORIES: Record<InsightCategory, string> = {
  timing: "Horario",
  topic: "Tema",
  format: "Formato",
  length: "Largo",
  tone: "Tono",
  trend: "Tendencia",
  hook: "Gancho",
  cta: "Llamado a la acción",
  other: "Otro",
};
const IMPACTS: Record<Impact, string> = { high: "Alto", medium: "Medio", low: "Bajo" };
const JOB_STATUSES: Record<JobStatus, string> = {
  queued: "En cola",
  fetching: "Buscando tus posts",
  analyzing: "Analizando",
  done: "Listo",
  failed: "Falló",
};
const PUBLISH_STATUSES: Record<PublishStatus, string> = {
  published: "Publicado",
  scheduled: "Programado",
  intent: "Listo para publicar en X",
  failed: "No se pudo publicar",
};
const WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const WEEKDAYS_SHORT = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

const capitalize = (value: string) => value.charAt(0).toUpperCase() + value.slice(1);

/** `null` means a text-only post. */
export const mediaTypeLabel = (value: MediaType): string => (value ? MEDIA_TYPES[value] : TEXT_ONLY);
export const lengthBucketLabel = (value: LengthBucket): string => LENGTH_BUCKETS[value];
export const postKindLabel = (value: PostKind): string => POST_KINDS[value];
export const segmentDimensionLabel = (value: SegmentDimension): string => SEGMENT_DIMENSIONS[value];
export const insightCategoryLabel = (value: InsightCategory): string => INSIGHT_CATEGORIES[value];
export const impactLabel = (value: Impact): string => IMPACTS[value];
export const jobStatusLabel = (value: JobStatus): string => JOB_STATUSES[value];
export const publishStatusLabel = (value: PublishStatus): string => PUBLISH_STATUSES[value];

/** Value of a SegmentStat: enum codes are translated, free-text AI labels are capitalized. */
export function segmentValueLabel(dimension: SegmentDimension, value: string): string {
  const codes: Partial<Record<SegmentDimension, Record<string, string>>> = {
    media_type: { ...MEDIA_TYPES, text: TEXT_ONLY },
    length_bucket: LENGTH_BUCKETS,
    post_kind: POST_KINDS,
  };
  return codes[dimension]?.[value] ?? capitalize(value);
}

/** 0 = Monday … 6 = Sunday, like the contract. */
export function weekdayLabel(weekday: number, options: { short?: boolean } = {}): string {
  return (options.short ? WEEKDAYS_SHORT : WEEKDAYS)[weekday];
}
