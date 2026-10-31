import { describe, expect, it } from "vitest";
import {
  impactLabel,
  insightCategoryLabel,
  jobStatusLabel,
  lengthBucketLabel,
  mediaTypeLabel,
  postKindLabel,
  publishStatusLabel,
  segmentDimensionLabel,
  segmentValueLabel,
  weekdayLabel,
} from "./labels";

describe("enum labels", () => {
  it("translates media types, with null as text only", () => {
    expect(mediaTypeLabel("photo")).toBe("Foto");
    expect(mediaTypeLabel("video")).toBe("Video");
    expect(mediaTypeLabel("gif")).toBe("GIF");
    expect(mediaTypeLabel(null)).toBe("Solo texto");
  });

  it("translates length buckets", () => {
    expect(lengthBucketLabel("short")).toBe("Corto");
    expect(lengthBucketLabel("medium")).toBe("Medio");
    expect(lengthBucketLabel("long")).toBe("Largo");
  });

  it("translates post kinds", () => {
    expect(postKindLabel("original")).toBe("Original");
    expect(postKindLabel("reply")).toBe("Respuesta");
    expect(postKindLabel("quote")).toBe("Cita");
    expect(postKindLabel("repost")).toBe("Repost");
  });

  it("translates every segment dimension, including hook and cta (contract 1.1.0)", () => {
    expect(segmentDimensionLabel("topic")).toBe("Tema");
    expect(segmentDimensionLabel("media_type")).toBe("Formato");
    expect(segmentDimensionLabel("length_bucket")).toBe("Largo");
    expect(segmentDimensionLabel("tone")).toBe("Tono");
    expect(segmentDimensionLabel("post_kind")).toBe("Tipo de post");
    expect(segmentDimensionLabel("hook")).toBe("Gancho");
    expect(segmentDimensionLabel("cta")).toBe("Llamado a la acción");
  });

  it("translates every insight category, including hook and cta (contract 1.1.0)", () => {
    expect(insightCategoryLabel("timing")).toBe("Horario");
    expect(insightCategoryLabel("topic")).toBe("Tema");
    expect(insightCategoryLabel("format")).toBe("Formato");
    expect(insightCategoryLabel("length")).toBe("Largo");
    expect(insightCategoryLabel("tone")).toBe("Tono");
    expect(insightCategoryLabel("trend")).toBe("Tendencia");
    expect(insightCategoryLabel("hook")).toBe("Gancho");
    expect(insightCategoryLabel("cta")).toBe("Llamado a la acción");
    expect(insightCategoryLabel("other")).toBe("Otro");
  });

  it("translates impact levels", () => {
    expect(impactLabel("high")).toBe("Alto");
    expect(impactLabel("medium")).toBe("Medio");
    expect(impactLabel("low")).toBe("Bajo");
  });

  it("translates job statuses", () => {
    expect(jobStatusLabel("queued")).toBe("En cola");
    expect(jobStatusLabel("fetching")).toBe("Buscando tus posts");
    expect(jobStatusLabel("analyzing")).toBe("Analizando");
    expect(jobStatusLabel("done")).toBe("Listo");
    expect(jobStatusLabel("failed")).toBe("Falló");
  });

  it("translates publish statuses", () => {
    expect(publishStatusLabel("published")).toBe("Publicado");
    expect(publishStatusLabel("scheduled")).toBe("Programado");
    expect(publishStatusLabel("intent")).toBe("Listo para publicar en X");
    expect(publishStatusLabel("failed")).toBe("No se pudo publicar");
  });
});

describe("segmentValueLabel", () => {
  it("translates enum-coded values, including the text-only media value", () => {
    expect(segmentValueLabel("media_type", "photo")).toBe("Foto");
    expect(segmentValueLabel("media_type", "text")).toBe("Solo texto");
    expect(segmentValueLabel("length_bucket", "short")).toBe("Corto");
    expect(segmentValueLabel("post_kind", "reply")).toBe("Respuesta");
  });

  it("capitalizes free-text labels written by the AI", () => {
    expect(segmentValueLabel("topic", "presupuesto")).toBe("Presupuesto");
    expect(segmentValueLabel("tone", "informativo")).toBe("Informativo");
    expect(segmentValueLabel("hook", "pregunta")).toBe("Pregunta");
  });

  it("capitalizes unknown codes instead of failing", () => {
    expect(segmentValueLabel("media_type", "carousel")).toBe("Carousel");
  });
});

describe("weekdayLabel", () => {
  it("uses 0 = Monday … 6 = Sunday, like the contract", () => {
    expect(weekdayLabel(0)).toBe("Lunes");
    expect(weekdayLabel(2)).toBe("Miércoles");
    expect(weekdayLabel(6)).toBe("Domingo");
  });

  it("has a three-letter form for the heatmap axis", () => {
    expect(weekdayLabel(2, { short: true })).toBe("Mié");
    expect(weekdayLabel(5, { short: true })).toBe("Sáb");
  });
});
