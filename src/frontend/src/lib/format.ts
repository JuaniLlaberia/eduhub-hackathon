// es-AR number and date formatting. Datetimes arrive in UTC and are shown in Argentina time.
// Behavior: format.test.ts.
import { notImplemented } from "@/lib/todo";

/** Shown wherever a value is missing (e.g. rates when a post has no impressions). */
export const EMPTY_VALUE = "—";

export const AR_TIME_ZONE = "America/Argentina/Buenos_Aires";

/** Rounded integer with es-AR grouping: 3572.9 → "3.573". */
export const formatNumber: (value: number | null) => string = notImplemented;

/** Rate (0–1) as a one-decimal percentage: 0.0493 → "4,9%". */
export const formatPercent: (rate: number | null) => string = notImplemented;

/** Score relative to the typical post: 1.8 → "1,8x". */
export const formatScore: (score: number | null) => string = notImplemented;

/** ISO UTC datetime in Argentina time, e.g. "mié, 28 oct, 13:30". */
export const formatDateTime: (iso: string) => string = notImplemented;

/** Weekday/hour slot of the heatmap: (2, 21) → "Miércoles 21 h". */
export const formatTimeSlot: (weekday: number, hour: number) => string = notImplemented;
