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

export const formatDay = (iso: string): string => day.format(new Date(iso));

export const formatShortDay = (iso: string): string => shortDay.format(new Date(iso));
