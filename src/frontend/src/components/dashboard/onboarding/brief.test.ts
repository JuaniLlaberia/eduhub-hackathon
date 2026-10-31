import { describe, expect, it } from "vitest";
import { briefErrors, briefSentence, buildContext, ctaLabel, EMPTY_ANSWERS, goalLabel } from "./brief";

describe("labels", () => {
  it("translates every goal (contract 1.2.0)", () => {
    expect(goalLabel("sell")).toBe("Vender un producto o servicio");
    expect(goalLabel("traffic")).toBe("Llevar gente a un link");
    expect(goalLabel("reach")).toBe("Crecer en alcance");
    expect(goalLabel("community")).toBe("Armar comunidad");
    expect(goalLabel("launch")).toBe("Lanzar algo nuevo");
    expect(goalLabel("other")).toBe("Otro");
  });

  it("translates every preferred CTA", () => {
    expect(ctaLabel("link")).toBe("Que entren a un link");
    expect(ctaLabel("reply")).toBe("Que respondan");
    expect(ctaLabel("save")).toBe("Que lo guarden");
    expect(ctaLabel("share")).toBe("Que lo compartan");
    expect(ctaLabel("follow")).toBe("Que te sigan");
    expect(ctaLabel("none")).toBe("Sin llamado a la acción");
  });
});

describe("buildContext", () => {
  it("returns null when nothing was filled, so the request carries no brief", () => {
    expect(buildContext(EMPTY_ANSWERS)).toBeNull();
    expect(buildContext({ ...EMPTY_ANSWERS, offering: "   " })).toBeNull();
  });

  it("keeps only the filled fields, trimmed", () => {
    expect(
      buildContext({ ...EMPTY_ANSWERS, goal: "sell", offering: "  Un curso  ", ageGroups: ["18 a 29 años"] }),
    ).toEqual({
      goal: "sell",
      offering: "Un curso",
      audience_filters: { age_groups: ["18 a 29 años"], genders: [], provinces: [] },
    });
  });

  it("includes voice, topics to avoid and CTA", () => {
    expect(
      buildContext({
        ...EMPTY_ANSWERS,
        brandVoice: "Cercana",
        avoidTopics: ["política", " "],
        preferredCta: "reply",
      }),
    ).toEqual({ brand_voice: "Cercana", avoid_topics: ["política"], preferred_cta: "reply" });
  });
});

describe("briefErrors", () => {
  it("has no errors for valid answers", () => {
    expect(briefErrors(EMPTY_ANSWERS)).toEqual({});
  });

  it("blocks texts over the contract limits, in es-AR", () => {
    const errors = briefErrors({
      ...EMPTY_ANSWERS,
      offering: "a".repeat(501),
      targetAudience: "a".repeat(301),
      brandVoice: "a".repeat(301),
    });
    expect(errors.offering).toBe("Usá hasta 500 caracteres.");
    expect(errors.targetAudience).toBe("Usá hasta 300 caracteres.");
    expect(errors.brandVoice).toBe("Usá hasta 300 caracteres.");
  });

  it("blocks more than 10 topics or a topic over 60 characters", () => {
    expect(
      briefErrors({ ...EMPTY_ANSWERS, avoidTopics: Array.from({ length: 11 }, (_, i) => `t${i}`) })
        .avoidTopics,
    ).toBe("Elegí hasta 10 temas.");
    expect(briefErrors({ ...EMPTY_ANSWERS, avoidTopics: ["a".repeat(61)] }).avoidTopics).toBe(
      "Cada tema puede tener hasta 60 caracteres.",
    );
  });
});

describe("briefSentence", () => {
  it("describes the creator in plain es-AR from the brief", () => {
    expect(
      briefSentence("demo_finanzas", {
        goal: "sell",
        offering: "Curso online de finanzas",
        audience_filters: { age_groups: ["18 a 29 años", "30 a 49 años"], genders: [], provinces: [] },
        preferred_cta: "link",
      }),
    ).toBe(
      "Sos @demo_finanzas. Publicás para vender un producto o servicio. Ofrecés curso online de finanzas. Le hablás a gente de 18 a 29 y 30 a 49 años. Querés que entren a un link.",
    );
  });

  it("only names the account when there is no brief", () => {
    expect(briefSentence("bilinkis", null)).toBe("Sos @bilinkis.");
  });
});
