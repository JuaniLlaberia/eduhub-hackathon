import { describe, expect, it } from "vitest";
import {
  EMPTY_VALUE,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatScore,
  formatTimeSlot,
} from "./format";

describe("formatNumber", () => {
  it("rounds and uses es-AR thousands separators", () => {
    expect(formatNumber(3572.975)).toBe("3.573");
    expect(formatNumber(1234567)).toBe("1.234.567");
    expect(formatNumber(0)).toBe("0");
  });

  it("shows a dash for missing values", () => {
    expect(formatNumber(null)).toBe(EMPTY_VALUE);
  });
});

describe("formatPercent", () => {
  it("shows a rate as a one-decimal percentage with a decimal comma", () => {
    expect(formatPercent(0.0493)).toBe("4,9%");
    expect(formatPercent(0.95069)).toBe("95,1%");
    expect(formatPercent(0)).toBe("0,0%");
  });

  it("shows a dash for missing rates", () => {
    expect(formatPercent(null)).toBe(EMPTY_VALUE);
  });
});

describe("formatScore", () => {
  it("shows the score as a multiple of the typical post", () => {
    expect(formatScore(1.8)).toBe("1,8x");
    expect(formatScore(1)).toBe("1,0x");
    expect(formatScore(0.43)).toBe("0,4x");
  });

  it("shows a dash for missing scores", () => {
    expect(formatScore(null)).toBe(EMPTY_VALUE);
  });
});

describe("formatDateTime", () => {
  it("shows UTC datetimes in Argentina time (UTC-3)", () => {
    const text = formatDateTime("2026-10-28T16:30:00Z");
    expect(text).toContain("28");
    expect(text).toContain("13:30");
  });

  it("keeps the Argentine date when UTC is already the next day", () => {
    const text = formatDateTime("2026-10-29T01:00:00Z");
    expect(text).toContain("28");
    expect(text).not.toContain("29");
    expect(text).toContain("22:00");
  });
});

describe("formatTimeSlot", () => {
  it("names the weekday (0 = Monday) and the hour", () => {
    expect(formatTimeSlot(2, 21)).toBe("Miércoles 21 h");
    expect(formatTimeSlot(0, 9)).toBe("Lunes 9 h");
  });
});
