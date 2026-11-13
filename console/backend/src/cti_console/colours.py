"""Turns a company's seven document colours into the console's light and dark themes.

A company picks the colours its reports use (company.json "palette"). The console
needs about twenty tokens per theme, and dark mode needs lighter versions of the
brand colours, which nobody should have to pick by hand. This works them out, and
checks contrast with the WCAG formula:

- Text must reach 4.5:1 against what it sits on (WCAG AA for body text).
- Chart bars and rules must reach 3:1 (WCAG non text contrast).

Light theme tokens follow the company's colours exactly, so a colour that fails is
reported back for the person to change. Dark theme tokens are derived, so they are
lifted until they pass.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass

RGB = tuple[float, float, float]

WHITE = "FFFFFF"
BLACK = "000000"
TEXT_RATIO = 4.5
GRAPHIC_RATIO = 3.0
# Fifty steps of 2% is enough to walk any colour all the way to white or black.
STEPS = 50

PALETTE_KEYS = ("primary", "accent", "text", "muted", "rule", "tint", "zebra")


def _rgb(hex_colour: str) -> RGB:
    return tuple(int(hex_colour[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(rgb: RGB) -> str:
    return "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def mix(a: str, b: str, amount: float) -> str:
    """`amount` of the way from a to b, in sRGB, as designers expect a tint to look."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * amount for x, y in zip(ra, rb, strict=True)))  # type: ignore[arg-type]


def luminance(hex_colour: str) -> float:
    """WCAG relative luminance."""

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def with_lightness(hex_colour: str, lightness: float) -> str:
    """The same hue and saturation at another HLS lightness, so a lifted colour stays vivid."""
    h, _, s = colorsys.rgb_to_hls(*_rgb(hex_colour))
    return _hex(colorsys.hls_to_rgb(h, max(0.0, min(1.0, lightness)), s))


def reach(colour: str, background: str, ratio: float, toward: str) -> str:
    """Lighten (toward WHITE) or darken (toward BLACK) until `ratio` on `background`."""
    _, start, _ = colorsys.rgb_to_hls(*_rgb(colour))
    end = 1.0 if toward == WHITE else 0.0
    for step in range(STEPS + 1):
        candidate = with_lightness(colour, start + (end - start) * step / STEPS)
        if contrast(candidate, background) >= ratio:
            return candidate if step else colour
    return toward


def best_on(background: str, *choices: str) -> str:
    """Whichever choice reads best on the background."""
    return max(choices, key=lambda c: contrast(c, background))


@dataclass(frozen=True)
class Check:
    """One contrast rule, as shown on the Branding tab."""

    label: str
    foreground: str
    background: str
    ratio: float
    needed: float

    @property
    def ok(self) -> bool:
        return self.ratio >= self.needed


def palette_checks(palette: dict[str, str]) -> list[Check]:
    """Rules the company's own colours must meet. They are used as given in the reports."""

    def check(label: str, fg: str, bg: str, needed: float = TEXT_RATIO) -> Check:
        return Check(label, fg, bg, round(contrast(fg, bg), 2), needed)

    p = palette
    return [
        check("Body text on white", p["text"], WHITE),
        check("Body text on the tint", p["text"], p["tint"]),
        check("Body text on the table stripe", p["text"], p["zebra"]),
        check("Secondary text on white", p["muted"], WHITE),
        check("Headings on white", p["primary"], WHITE),
        check("White text on the heading colour (table headers)", WHITE, p["primary"]),
        check("Accent on white (links)", p["accent"], WHITE),
        check("Lines on white", p["rule"], WHITE, 1.3),
    ]


def light_tokens(palette: dict[str, str]) -> dict[str, str]:
    p = palette
    page = mix(p["tint"], WHITE, 0.5)
    raised = p["tint"]
    # Grey text is a step lighter than body text, but never below AA on any card colour.
    muted = reach(mix(p["text"], WHITE, 0.25), raised, TEXT_RATIO, BLACK)
    faint = reach(mix(p["text"], WHITE, 0.35), raised, TEXT_RATIO, BLACK)
    return {
        "page": page,
        "surface": WHITE,
        "raised": raised,
        "line": mix(p["rule"], WHITE, 0.5),
        "ink": p["text"],
        "muted": muted,
        "faint": faint,
        "brand": p["primary"],
        "accent": p["accent"],
        "accent-hover": mix(p["accent"], BLACK, 0.15),
        "on-accent": best_on(p["accent"], WHITE, p["text"]),
        "accent-soft": p["tint"],
        "accent-soft-ink": p["primary"],
        "rung": p["rule"],
        "series-scan": p["accent"],
        "series-build": p["rule"],
        "series-report": p["primary"],
        "series-other": reach(mix(p["text"], WHITE, 0.5), WHITE, GRAPHIC_RATIO, BLACK),
    }


def dark_tokens(palette: dict[str, str]) -> dict[str, str]:
    p = palette
    # Cards are the heading colour pushed most of the way to black, so they keep its hue.
    surface = mix(p["primary"], "101010", 0.6)
    page = mix(surface, BLACK, 0.4)
    raised = mix(surface, WHITE, 0.06)
    soft = mix(p["accent"], surface, 0.8)
    ink = reach(p["tint"], raised, 7.0, WHITE)
    accent = reach(p["accent"], raised, TEXT_RATIO, WHITE)
    return {
        "page": page,
        "surface": surface,
        "raised": raised,
        "line": mix(surface, WHITE, 0.14),
        "ink": ink,
        "muted": reach(mix(ink, surface, 0.25), raised, TEXT_RATIO, WHITE),
        "faint": reach(mix(ink, surface, 0.4), raised, TEXT_RATIO, WHITE),
        "brand": ink,
        "accent": accent,
        "accent-hover": reach(accent, raised, contrast(accent, raised) + 1.5, WHITE),
        "on-accent": best_on(accent, page, WHITE),
        "accent-soft": soft,
        "accent-soft-ink": reach(ink, soft, TEXT_RATIO, WHITE),
        "rung": reach(mix(p["rule"], surface, 0.25), surface, GRAPHIC_RATIO, WHITE),
        # A dark mark would vanish on a dark card, so the symbol sits on a light tile.
        "symbol-tile": p["tint"],
        "series-scan": accent,
        "series-build": reach(p["rule"], surface, GRAPHIC_RATIO, WHITE),
        "series-report": reach(mix(ink, accent, 0.2), surface, GRAPHIC_RATIO, WHITE),
        "series-other": reach(mix(ink, surface, 0.5), surface, GRAPHIC_RATIO, WHITE),
    }


def console_checks(light: dict[str, str], dark: dict[str, str]) -> list[Check]:
    """The pairs the console draws text and charts with, in both themes."""
    checks: list[Check] = []
    for theme, t in (("Light", light), ("Dark", dark)):
        pairs = [
            ("text on cards", t["ink"], t["surface"], TEXT_RATIO),
            ("grey text on raised cards", t["muted"], t["raised"], TEXT_RATIO),
            ("faint text on raised cards", t["faint"], t["raised"], TEXT_RATIO),
            ("accent text on the page", t["accent"], t["page"], TEXT_RATIO),
            ("button text on the accent", t["on-accent"], t["accent"], TEXT_RATIO),
            ("chart bars on cards", t["series-scan"], t["surface"], GRAPHIC_RATIO),
        ]
        for label, fg, bg, needed in pairs:
            checks.append(Check(f"{theme}: {label}", fg, bg, round(contrast(fg, bg), 2), needed))
    return checks
