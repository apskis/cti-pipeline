import { describe, expect, it } from "vitest";

import { formatCount, formatDay, formatMoney, formatShortDay } from "./format";

describe("format", () => {
  it("keeps a date only string on its own day in any time zone", () => {
    expect(formatShortDay("2026-11-10")).toBe("10 Nov");
    expect(formatDay("2026-11-10")).toBe("10 Nov 2026");
  });

  it("formats money and missing counts", () => {
    expect(formatMoney(49.07)).toBe("$49.07");
    expect(formatCount(null)).toBe("Not available");
    expect(formatCount(1234)).toBe("1,234");
  });
});
