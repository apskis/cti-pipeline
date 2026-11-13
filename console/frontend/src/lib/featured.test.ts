import { describe, expect, it } from "vitest";

import type { Deliverable } from "../api/types";
import { pickFeatured } from "./featured";

const doc = (id: string, kind: string, firstSeen: string, status: Deliverable["status"] = "ok") => ({
  id,
  kind,
  title: id,
  path: `${id}.docx`,
  first_seen: firstSeen,
  modified: `${firstSeen}T12:00:00`,
  status,
  problem: null,
  review: null,
});

describe("pickFeatured", () => {
  it("takes the newest usable document of each featured kind, in display order", () => {
    const picked = pickFeatured([
      doc("TH26-1", "hunt", "2026-11-01"),
      doc("CTI26-2", "bulletin", "2026-11-09"),
      doc("CTI26-3", "bulletin", "2026-11-10", "broken"),
      doc("CTI26-1", "bulletin", "2026-11-02"),
      doc("AWR-1", "awareness", "2026-11-10"),
      doc("WK-2026-45", "weekly", "2026-11-03", "unchecked"),
    ]);
    expect(picked.map((f) => f.item.id)).toEqual(["CTI26-2", "TH26-1", "WK-2026-45"]);
    expect(picked[0]?.label).toBe("Latest bulletin");
  });

  it("is empty when nothing is on disk", () => {
    expect(pickFeatured([])).toEqual([]);
  });
});
