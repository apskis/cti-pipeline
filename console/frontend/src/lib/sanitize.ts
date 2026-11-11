import DOMPurify from "dompurify";

// Report HTML comes from .docx files whose links and text the pipeline copied from the
// web. It is treated as hostile: only plain document markup survives, links open in a
// new tab without access to this page, and only images embedded in the file may load.
const ALLOWED_TAGS = [
  "p", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "em", "i", "u", "s", "sup", "sub",
  "br", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td", "a", "img",
  "blockquote", "pre", "code",
];
const ALLOWED_ATTR = ["href", "src", "alt", "colspan", "rowspan"];
const SAFE_LINK = /^(?:https?:|mailto:)/i;
const EMBEDDED_IMAGE = /^data:image\/(?:png|jpe?g|gif|webp);base64,/i;

function tidyElement(node: Node): void {
  if (!(node instanceof Element)) return;
  if (node.tagName === "A") {
    if (SAFE_LINK.test(node.getAttribute("href") ?? "")) {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    } else {
      node.removeAttribute("href");
    }
  }
  if (node.tagName === "IMG" && !EMBEDDED_IMAGE.test(node.getAttribute("src") ?? "")) {
    node.removeAttribute("src");
  }
}

let hooked = false;

export function sanitizeReport(html: string): string {
  if (!hooked) {
    DOMPurify.addHook("afterSanitizeAttributes", tidyElement);
    hooked = true;
  }
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ADD_ATTR: ["target", "rel"],
    ALLOW_DATA_ATTR: false,
  });
}
