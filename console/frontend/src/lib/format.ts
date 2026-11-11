const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const day = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
// Chart days are UTC dates ("2026-11-10"). Formatting them in the local zone would show
// the day before for anyone west of Greenwich, so they are formatted in UTC too.
const shortDay = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

export const formatMoney = (usd: number): string => money.format(usd);

export const formatCount = (n: number | null | undefined): string =>
  n === null || n === undefined ? "Not available" : n.toLocaleString("en-US");

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;
const dayUtc = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

// A date only string ("2026-11-10", a first seen date) parses as UTC midnight, so it is
// formatted in UTC to stay on its day. A timestamp is shown in the viewer's own zone.
export const formatDay = (iso: string): string =>
  (DATE_ONLY.test(iso) ? dayUtc : day).format(new Date(iso));

export const formatShortDay = (iso: string): string => shortDay.format(new Date(iso));

/** 75 -> "1 min", 4000 -> "1 h 7 min". Runs are minutes long, so seconds are dropped. */
export function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `${minutes} min`;
  const rest = minutes % 60;
  return rest ? `${Math.floor(minutes / 60)} h ${rest} min` : `${minutes / 60} h`;
}

const time = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
});

/** A run's start, in the viewer's zone: "10 Nov 2026, 14:57". */
export const formatWhen = (iso: string): string =>
  `${formatDay(iso)}, ${time.format(new Date(iso))}`;
