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
