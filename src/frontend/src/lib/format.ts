// es-AR number and date formatting. Datetimes arrive in UTC and are shown in Argentina time.
// Behavior: format.test.ts.
import { weekdayLabel } from "@/lib/labels";

/** Shown wherever a value is missing (e.g. rates when a post has no impressions). */
export const EMPTY_VALUE = "—";

export const AR_TIME_ZONE = "America/Argentina/Buenos_Aires";

const integer = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const dateTime = new Intl.DateTimeFormat("es-AR", {
  timeZone: AR_TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** Rounded integer with es-AR grouping: 3572.9 → "3.573". */
export const formatNumber = (value: number | null): string =>
  value === null ? EMPTY_VALUE : integer.format(Math.round(value));

/** Rate (0–1) as a one-decimal percentage: 0.0493 → "4,9%". */
export const formatPercent = (rate: number | null): string =>
  rate === null ? EMPTY_VALUE : `${oneDecimal.format(rate * 100)}%`;

/** Score relative to the typical post: 1.8 → "1,8x". */
export const formatScore = (score: number | null): string =>
  score === null ? EMPTY_VALUE : `${oneDecimal.format(score)}x`;

/** ISO UTC datetime in Argentina time, e.g. "mié, 28 oct, 13:30". */
export const formatDateTime = (iso: string): string => dateTime.format(new Date(iso));

/** Weekday/hour slot of the heatmap: (2, 21) → "Miércoles 21 h". */
export const formatTimeSlot = (weekday: number, hour: number): string => `${weekdayLabel(weekday)} ${hour} h`;
