#!/usr/bin/env python3
"""Behaviour diagrams for the GeneLabs CTI Detection Hand-off.

April, 2026-08-27: *"use pictures explaining the behavior seen as well for the soc handoff"*.

These illustrate WHAT THE ADVERSARY DID, not what query to run. That pairing is the whole
design of the pseudo-detection format: the picture carries the behaviour, the prose carries
the data needed and the discriminator, and the analyst writes the search themselves.

EVERY DIAGRAM IS A CONTRAST — normal on the left, the behaviour on the right, drawn to the
same scale. A detection engineer's real problem is never "what does bad look like", it is
"what does bad look like THAT GOOD DOES NOT". A picture of only the malicious case invites a
detection that fires on everything, which then gets muted, which is worse than no detection.

Raster, drawn at 3x and downsampled. No SVG converter exists in this environment. Labels use
Liberation Sans, metrically compatible with Arial.
"""
from PIL import Image, ImageDraw, ImageFont
import glob, os

ORANGE      = (255, 113,   9)
ORANGE_DEEP = (224,  95,   0)
TINT        = (255, 244, 232)
ABBEY       = ( 68,  70,  72)
GREY        = (103, 103, 101)
MUTED       = (170, 170, 168)
LIGHT       = (244, 244, 244)
RULE        = (217, 217, 217)
WHITE       = (255, 255, 255)
GREEN       = ( 46, 125,  50)
RED         = (198,  40,  40)

SS = 3


def _font(size, bold=False):
    pat = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    hits = glob.glob(f"/usr/share/fonts/**/{pat}", recursive=True)
    return ImageFont.truetype(hits[0], size) if hits else ImageFont.load_default()


def _canvas(w, h):
    im = Image.new("RGB", (w * SS, h * SS), WHITE)
    return im, ImageDraw.Draw(im)


def _centre(dr, txt, font, cx, y, fill):
    dr.text((cx - dr.textlength(txt, font=font) / 2, y), txt, font=font, fill=fill)


def _panel(dr, x, y, w, h, title, accent, font):
    """One half of a contrast. Titled, lightly ruled, so the two read as comparable."""
    dr.rounded_rectangle((x, y, x + w, y + h), radius=8 * SS, outline=RULE, width=2 * SS)
    dr.rounded_rectangle((x, y, x + w, y + 24 * SS), radius=8 * SS,
                         fill=TINT if accent == ORANGE else LIGHT)
    dr.rectangle((x, y + 16 * SS, x + w, y + 24 * SS), fill=TINT if accent == ORANGE else LIGHT)
    dr.line((x, y + 24 * SS, x + w, y + 24 * SS), fill=RULE, width=2 * SS)
    dr.text((x + 12 * SS, y + 6 * SS), title, font=font, fill=accent)


def _host(dr, cx, cy, r, label, font, fill=WHITE, outline=ABBEY):
    dr.rounded_rectangle((cx - r, cy - r * 0.72, cx + r, cy + r * 0.72), radius=6 * SS,
                         fill=fill, outline=outline, width=3 * SS)
    _centre(dr, label, font, cx, cy - font.size * 0.55, ABBEY)


def _dot(dr, cx, cy, r, fill):
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)


def path_fanout(w=740, h=210):
    """D1 — a normal client asks for a few paths repeatedly; a scanner asks for thousands once."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(int(11 * SS), bold=True)
    f = _font(int(10 * SS))
    fs = _font(int(9 * SS))
    pw = int(W * 0.47)

    for side, (x, title, accent) in enumerate((
            (0, "NORMAL  certificate client", GREY),
            (int(W * 0.53), "SCANNER  template sweep", ORANGE_DEEP))):
        _panel(dr, x, 4 * SS, pw, H - 26 * SS, title, accent, ft)
        sx = x + 52 * SS
        cy = int(H * 0.60)
        _host(dr, sx, cy, 34 * SS, "client" if side == 0 else "one IP", f)
        tx = x + pw - 52 * SS
        _host(dr, tx, cy, 34 * SS, "host", f)
        if side == 0:
            for k in range(3):
                yy = cy - 16 * SS + k * 16 * SS
                dr.line((sx + 36 * SS, yy, tx - 36 * SS, yy), fill=GREY, width=4 * SS)
            _centre(dr, "6 paths, fetched constantly", fs, x + pw / 2, H - 40 * SS, GREY)
        else:
            for k in range(13):
                yy = cy - 40 * SS + k * 6.6 * SS
                dr.line((sx + 36 * SS, cy, tx - 36 * SS, yy), fill=ORANGE, width=1 * SS)
            _centre(dr, "thousands of paths, each once", fs, x + pw / 2, H - 40 * SS, ORANGE_DEEP)
    return im.resize((w, h), Image.LANCZOS)


def oob_callback(w=740, h=210):
    """D2 — the request tells the target to call a third party the attacker owns."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(int(11 * SS), bold=True)
    f = _font(int(10 * SS))
    fs = _font(int(9 * SS))
    _panel(dr, 0, 4 * SS, W, H - 26 * SS, "OUT OF BAND CALLBACK  the target is told to phone a stranger",
           ORANGE_DEEP, ft)
    y = int(H * 0.60)
    ax, bx, cx = int(W * 0.14), int(W * 0.48), int(W * 0.83)
    _host(dr, ax, y, 40 * SS, "attacker", f)
    _host(dr, bx, y, 40 * SS, "our host", f)
    _host(dr, cx, y, 46 * SS, "collaborator", f, fill=LIGHT, outline=MUTED)
    dr.line((ax + 42 * SS, y, bx - 42 * SS, y), fill=ORANGE, width=4 * SS)
    dr.polygon([(bx - 42 * SS, y), (bx - 54 * SS, y - 7 * SS), (bx - 54 * SS, y + 7 * SS)], fill=ORANGE)
    _centre(dr, "request carrying a URL", fs, (ax + bx) / 2, y - 26 * SS, GREY)
    dr.line((bx + 42 * SS, y, cx - 48 * SS, y), fill=ORANGE, width=4 * SS)
    dr.polygon([(cx - 48 * SS, y), (cx - 60 * SS, y - 7 * SS), (cx - 60 * SS, y + 7 * SS)], fill=ORANGE)
    _centre(dr, "if it calls out, the flaw is real", fs, (bx + cx) / 2, y - 26 * SS, ORANGE_DEEP)
    _centre(dr, "The domain belongs to the tester, not to us. Seeing it in an inbound request is the signal.",
            fs, W / 2, H - 40 * SS, GREY)
    return im.resize((w, h), Image.LANCZOS)


def known_bad_allowed(w=740, h=220):
    """D3 — an enforcement gap, not a scanning one. We hold the intel and permit the traffic."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(int(11 * SS), bold=True)
    f = _font(int(10 * SS))
    fs = _font(int(9 * SS))
    _panel(dr, 0, 4 * SS, W, H - 26 * SS,
           "ENFORCEMENT GAP  we already hold the intelligence, and the traffic is still permitted",
           ORANGE_DEEP, ft)
    y = int(H * 0.56)
    ax, fx, dx = int(W * 0.13), int(W * 0.47), int(W * 0.82)
    _host(dr, ax, y, 42 * SS, "source IP", f)
    dr.rounded_rectangle((fx - 40 * SS, y - 40 * SS, fx + 40 * SS, y + 40 * SS), radius=6 * SS,
                         fill=WHITE, outline=ABBEY, width=3 * SS)
    _centre(dr, "firewall", f, fx, y - 8 * SS, ABBEY)
    _centre(dr, "ALLOW", _font(int(10 * SS), bold=True), fx, y + 8 * SS, RED)
    _host(dr, dx, y, 42 * SS, "our asset", f)
    for x0, x1 in ((ax + 44 * SS, fx - 42 * SS), (fx + 42 * SS, dx - 44 * SS)):
        dr.line((x0, y, x1, y), fill=ORANGE, width=4 * SS)
        dr.polygon([(x1, y), (x1 - 12 * SS, y - 7 * SS), (x1 - 12 * SS, y + 7 * SS)], fill=ORANGE)
    # the intel that should have stopped it, sitting to one side, unused
    ty = y - 62 * SS
    dr.rounded_rectangle((fx - 78 * SS, ty - 16 * SS, fx + 78 * SS, ty + 16 * SS), radius=5 * SS,
                         fill=LIGHT, outline=MUTED, width=2 * SS)
    _centre(dr, "already in our threat intel", fs, fx, ty - 6 * SS, GREY)
    for k in range(5):
        yy = ty + 18 * SS + k * 6 * SS
        if k % 2 == 0:
            dr.line((fx, yy, fx, yy + 4 * SS), fill=MUTED, width=2 * SS)
    _centre(dr, "The intelligence exists. It is not reaching the block list.", fs, W / 2, H - 40 * SS, ORANGE_DEEP)
    return im.resize((w, h), Image.LANCZOS)


def outcome_missing(w=740, h=215):
    """The blocked detection — we see the question and not the answer."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(int(11 * SS), bold=True)
    f = _font(int(10 * SS))
    fs = _font(int(9 * SS))
    _panel(dr, 0, 4 * SS, W, H - 26 * SS,
           "WHAT WE ARE MISSING  we record the question and not the answer", GREY, ft)
    y = int(H * 0.56)
    ax, bx = int(W * 0.16), int(W * 0.52)
    _host(dr, ax, y, 44 * SS, "scanner", f)
    _host(dr, bx, y, 44 * SS, "our host", f)
    dr.line((ax + 46 * SS, y, bx - 46 * SS, y), fill=ORANGE, width=4 * SS)
    dr.polygon([(bx - 46 * SS, y), (bx - 58 * SS, y - 7 * SS), (bx - 58 * SS, y + 7 * SS)], fill=ORANGE)
    _centre(dr, "29,700 requests — CAPTURED", fs, (ax + bx) / 2, y - 28 * SS, ORANGE_DEEP)
    rx = int(W * 0.86)
    dr.rounded_rectangle((bx + 46 * SS, y - 26 * SS, rx, y + 26 * SS), radius=6 * SS,
                         fill=WHITE, outline=MUTED, width=2 * SS)
    for k in range(6):
        x0 = bx + 52 * SS + k * 22 * SS
        dr.line((x0, y - 22 * SS, x0 + 10 * SS, y - 22 * SS), fill=MUTED, width=2 * SS)
    _centre(dr, "response codes — NOT CAPTURED", fs, (bx + rx) / 2 + 20 * SS, y - 6 * SS, GREY)
    _centre(dr, "The web server records them. This host does not forward them, while its peers do.",
            fs, W / 2, H - 40 * SS, GREY)
    return im.resize((w, h), Image.LANCZOS)


def off_estate_asset(w=740, h=235):
    """D5 - the same corporate hostname, resolving into infrastructure we run and into
    infrastructure we do not. The contrast is the ASN and what telemetry follows from it."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(int(11 * SS), bold=True)
    f = _font(int(10 * SS))
    fs = _font(int(9 * SS))
    fb = _font(int(9 * SS), bold=True)
    _panel(dr, 0, 4 * SS, W, H - 26 * SS,
           "SAME NAME, DIFFERENT ESTATE  the hostname is identical; the address space is not",
           ORANGE_DEEP, ft)

    mid = W // 2
    dr.line((mid, 34 * SS, mid, H - 34 * SS), fill=RULE, width=2 * SS)
    y = int(H * 0.52)

    for side, cx, title, asn, colour, sensors in (
            ("norm", int(W * 0.25), "NORMAL", "AWS or AS12158", GREEN,
             ["sensor present", "logs in Splunk", "in the patch pipeline"]),
            ("find", int(W * 0.75), "THE FINDING", "AS24940, rented", RED,
             ["no sensor", "no logs", "no patch pipeline"])):
        _centre(dr, title, fb, cx, 40 * SS, colour)
        _centre(dr, "name.genelabs.com", f, cx, y - 62 * SS, ABBEY)
        dr.line((cx, y - 50 * SS, cx, y - 26 * SS), fill=ORANGE, width=4 * SS)
        dr.polygon([(cx, y - 24 * SS), (cx - 7 * SS, y - 36 * SS), (cx + 7 * SS, y - 36 * SS)],
                   fill=ORANGE)
        dr.rounded_rectangle((cx - 74 * SS, y - 22 * SS, cx + 74 * SS, y + 22 * SS), radius=6 * SS,
                             fill=(TINT if side == "find" else WHITE), outline=colour, width=3 * SS)
        _centre(dr, asn, fb, cx, y - 8 * SS, colour)
        _centre(dr, "resolves here", fs, cx, y + 8 * SS, GREY)
        for k, s in enumerate(sensors):
            _centre(dr, ("+ " if side == "norm" else "- ") + s, fs, cx,
                    y + 44 * SS + k * 15 * SS, (GREY if side == "norm" else RED))

    _centre(dr, "The discriminator is the autonomous system, not the hostname.",
            fs, W / 2, H - 40 * SS, ORANGE_DEEP)
    return im.resize((w, h), Image.LANCZOS)


SCENES = {"beh_fanout": path_fanout, "beh_oob": oob_callback,
          "beh_knownbad": known_bad_allowed, "beh_outcome": outcome_missing,
          "beh_offestate": off_estate_asset}


def render(name, outdir):
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, f"{name}.png")
    SCENES[name]().save(p, "PNG")
    return p


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for n in SCENES:
        print(render(n, out))
