import { describe, expect, it } from "vitest";

import { sanitizeReport } from "./sanitize";

const parse = (html: string) => {
  const box = document.createElement("div");
  box.innerHTML = sanitizeReport(html);
  return box;
};

describe("sanitizeReport", () => {
  it("keeps the document markup mammoth produces", () => {
    const html =
      "<h3>Why This Matters</h3><p><strong>Lead</strong> text<sup>[1]</sup></p>" +
      "<table><tr><td><p>CVE</p></td></tr></table>";
    expect(sanitizeReport(html)).toBe(
      "<h3>Why This Matters</h3><p><strong>Lead</strong> text<sup>[1]</sup></p>" +
        "<table><tbody><tr><td><p>CVE</p></td></tr></tbody></table>",
    );
  });

  it("removes scripts, handlers, styles and frames", () => {
    const box = parse(
      '<p onclick="steal()" style="color:red">x</p><script>steal()</script>' +
        '<iframe src="https://evil.example"></iframe><img src=x onerror="steal()">',
    );
    expect(box.innerHTML).not.toMatch(/script|onclick|onerror|style|iframe|steal/);
  });

  it("opens web links in a new tab with no opener and drops other schemes", () => {
    const box = parse(
      '<a href="https://www.cisa.gov/kev">KEV</a><a href="javascript:steal()">bad</a>' +
        '<a href="mailto:secops@genelabs.com">mail</a>',
    );
    const [web, bad, mail] = Array.from(box.querySelectorAll("a"));
    expect(web?.getAttribute("target")).toBe("_blank");
    expect(web?.getAttribute("rel")).toBe("noopener noreferrer");
    expect(bad?.hasAttribute("href")).toBe(false);
    expect(mail?.getAttribute("href")).toBe("mailto:secops@genelabs.com");
  });

  it("loads only images embedded in the document", () => {
    const box = parse(
      '<img src="data:image/png;base64,iVBORw0KGgo=" alt="logo">' +
        '<img src="https://tracker.example/pixel.gif" alt="pixel">',
    );
    const [embedded, remote] = Array.from(box.querySelectorAll("img"));
    expect(embedded?.getAttribute("src")).toMatch(/^data:image\/png/);
    expect(remote?.hasAttribute("src")).toBe(false);
  });
});
