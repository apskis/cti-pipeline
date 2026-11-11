"""Turn one deliverable into HTML the reader pane can show.

The pipeline writes every heading as a bold Normal paragraph, so mammoth's style map has
nothing to go on. A paragraph that is nothing but a short bold run is promoted to a
heading here, which gives the reader pane real structure without touching the .docx.

The HTML is not trusted by the front end: it sanitizes it again before rendering, because
a document's hyperlinks come from web sources the pipeline read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import mammoth

# A whole paragraph of bold text up to this long reads as a heading in the bulletins.
HEADING = re.compile(r"<p><strong>([^<]{2,80}?)</strong></p>")


@dataclass(frozen=True)
class Rendered:
    html: str
    warnings: int  # mammoth messages, for the curious; never shown as an error


# Converting takes a moment per document, so results are kept per file and modification
# time, like the quality checks in deliverables.py.
_RENDERED: dict[tuple[str, int], Rendered] = {}


TABLE = re.compile(r"(<table>.*?</table>)", re.DOTALL)


def promote_headings(html: str) -> str:
    """Promote bold paragraphs outside tables; a bold table cell is a label, not a heading."""
    parts = TABLE.split(html)
    # split() with one group alternates text, table, text, ...: odd items are tables.
    return "".join(
        part if i % 2 else HEADING.sub(lambda m: f"<h3>{m[1].strip()}</h3>", part)
        for i, part in enumerate(parts)
    )


def render_docx(path: Path) -> Rendered:
    key = (str(path), path.stat().st_mtime_ns)
    if key not in _RENDERED:
        with path.open("rb") as handle:
            result = mammoth.convert_to_html(handle)
        _RENDERED[key] = Rendered(promote_headings(result.value), len(result.messages))
    return _RENDERED[key]
