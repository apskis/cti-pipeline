#!/usr/bin/env python3
"""Flat illustrations for the GeneLabs employee awareness BLOG format.

Drawn with Pillow rather than imported, for three reasons that matter here:

  1. No stock image can say "a web page reached a program on your laptop". Every
     library result for that search is a hooded figure at a keyboard, which is the
     single most tired image in security communication and teaches the reader
     nothing.
  2. Licensing. A post that goes to every employee and gets screenshotted needs art
     GeneLabs owns outright.
  3. The palette has to be the house palette. Drawing it guarantees that; sourcing it
     guarantees an argument with brand.

There is no SVG converter in this environment (no cairosvg, no rsvg-convert), so
these are raster, drawn at 3x and downsampled, which is what keeps the edges clean at
document scale.

Labels use Liberation Sans, which is metrically compatible with Arial, because Arial
itself is not installed here. At label sizes the two are indistinguishable in print.

Each function returns a PIL Image at final size. Add a new scene as a function and
register it in SCENES.
"""
from PIL import Image, ImageDraw, ImageFont
import glob, os

# ---------------------------------------------------------------- house palette
ORANGE      = (255, 113,   9)
ORANGE_DEEP = (224,  95,   0)
TINT        = (255, 244, 232)
ABBEY       = ( 68,  70,  72)
GREY        = (103, 103, 101)
LIGHT       = (244, 244, 244)
RULE        = (217, 217, 217)
WHITE       = (255, 255, 255)
RED         = (198,  40,  40)

SS = 3  # supersample factor


def _font(size, bold=False):
    pat = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    hits = glob.glob(f"/usr/share/fonts/**/{pat}", recursive=True)
    if not hits:
        hits = glob.glob("/usr/share/fonts/**/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
                         recursive=True)
    return ImageFont.truetype(hits[0], size) if hits else ImageFont.load_default()


def _canvas(w, h, bg=WHITE):
    im = Image.new("RGB", (w * SS, h * SS), bg)
    return im, ImageDraw.Draw(im)


def _finish(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def _rrect(dr, box, r, fill=None, outline=None, width=1):
    dr.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def _centre(dr, text, font, cx, y, fill):
    l, t, r, b = dr.textbbox((0, 0), text, font=font)
    dr.text((cx - (r - l) / 2, y), text, font=font, fill=fill)


def _browser(dr, x, y, w, h, title_bar=TINT, body=WHITE, border=RULE):
    """A browser window: chrome bar with three dots, then a content area."""
    _rrect(dr, (x, y, x + w, y + h), 10 * SS, fill=body, outline=border, width=2 * SS)
    bar = 26 * SS
    dr.rounded_rectangle((x, y, x + w, y + bar + 10 * SS), radius=10 * SS, fill=title_bar)
    dr.rectangle((x, y + bar, x + w, y + bar + 2 * SS), fill=title_bar)
    dr.line((x, y + bar, x + w, y + bar), fill=border, width=2 * SS)
    for i in range(3):
        cx = x + 16 * SS + i * 14 * SS
        cy = y + bar / 2
        dr.ellipse((cx - 4 * SS, cy - 4 * SS, cx + 4 * SS, cy + 4 * SS), fill=GREY)


def _laptop(dr, x, y, w, border=ABBEY):
    """A laptop seen head on: screen, then a base wider than the screen."""
    h = int(w * 0.62)
    _rrect(dr, (x, y, x + w, y + h), 8 * SS, fill=WHITE, outline=border, width=3 * SS)
    base_pad = int(w * 0.10)
    dr.rounded_rectangle((x - base_pad, y + h + 4 * SS, x + w + base_pad, y + h + 16 * SS),
                         radius=6 * SS, fill=border)
    return h


def _arrow(dr, pts, colour=ORANGE, width=5, head=14):
    dr.line(pts, fill=colour, width=width * SS, joint="curve")
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    h = head * SS
    dr.polygon([(x2, y2),
                (x2 - ux * h + px * h * 0.55, y2 - uy * h + py * h * 0.55),
                (x2 - ux * h - px * h * 0.55, y2 - uy * h - py * h * 0.55)], fill=colour)


def _cross(dr, cx, cy, r, colour=RED, width=5):
    dr.line((cx - r, cy - r, cx + r, cy + r), fill=colour, width=width * SS)
    dr.line((cx - r, cy + r, cx + r, cy - r), fill=colour, width=width * SS)


def _tick(dr, cx, cy, r, colour=ORANGE_DEEP, width=6):
    dr.line((cx - r, cy, cx - r * 0.15, cy + r * 0.75), fill=colour, width=width * SS)
    dr.line((cx - r * 0.15, cy + r * 0.75, cx + r, cy - r * 0.8), fill=colour, width=width * SS)


# ------------------------------------------------------------------- the scenes
def hero_driveby(w=760, h=250):
    """A page on the left reaching across into a laptop on the right.

    The whole argument of the post in one image: nothing crosses from the user, the
    arrow travels the other way.
    """
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    _browser(dr, int(W * 0.05), int(H * 0.17), int(W * 0.33), int(H * 0.62))
    f = _font(15 * SS)
    fs = _font(13 * SS, bold=True)
    dr.text((int(W * 0.08), int(H * 0.42)), "an ordinary", font=f, fill=GREY)
    dr.text((int(W * 0.08), int(H * 0.55)), "web page", font=fs, fill=ABBEY)

    lx = int(W * 0.62)
    lw = int(W * 0.28)
    ly = int(H * 0.20)
    lh = _laptop(dr, lx, ly, lw)
    dr.rectangle((lx + 14 * SS, ly + 14 * SS, lx + lw - 14 * SS, ly + lh - 14 * SS), fill=LIGHT)
    dr.text((lx + 26 * SS, ly + 30 * SS), "a program", font=f, fill=GREY)
    dr.text((lx + 26 * SS, ly + 48 * SS), "already", font=f, fill=GREY)
    dr.text((lx + 26 * SS, ly + 66 * SS), "running here", font=fs, fill=ABBEY)

    y = int(H * 0.47)
    _arrow(dr, [(int(W * 0.395), y), (int(W * 0.47), y - 22 * SS),
                (int(W * 0.55), y - 22 * SS), (int(W * 0.605), y)], ORANGE, 6, 16)
    _centre(dr, "you do nothing", _font(14 * SS, bold=True), int(W * 0.50), int(H * 0.11), ORANGE_DEEP)
    return _finish(im, w, h)


def three_absences(w=760, h=210):
    """The three things this attack does NOT need, crossed out.

    Employees have been trained on all three. Showing them struck through is the
    fastest way to say the old rule will not save you here.
    """
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    fl = _font(14 * SS, bold=True)
    labels = ["no attachment", "no password box", "no link to click"]
    cw = W / 3
    for i, lab in enumerate(labels):
        cx = int(cw * i + cw / 2)
        cy = int(H * 0.42)
        # The glyph has to stay legible THROUGH the cross, or the image says only
        # "no" three times and the reader never learns what is being ruled out.
        # First draft had 20pt glyphs under a 34pt heavy cross and the document icon
        # was unreadable. Glyphs are now ~40% larger and the cross is lighter weight
        # in a softer red, so it reads as struck through rather than obliterated.
        dr.ellipse((cx - 52 * SS, cy - 52 * SS, cx + 52 * SS, cy + 52 * SS), fill=LIGHT)
        if i == 0:                                   # a document with no attachment
            _rrect(dr, (cx - 28 * SS, cy - 36 * SS, cx + 28 * SS, cy + 36 * SS), 5 * SS,
                   fill=WHITE, outline=GREY, width=4 * SS)
            for k in range(4):
                dr.line((cx - 16 * SS, cy - 18 * SS + k * 14 * SS,
                         cx + 16 * SS, cy - 18 * SS + k * 14 * SS), fill=RULE, width=4 * SS)
        elif i == 1:                                 # a credential field
            _rrect(dr, (cx - 38 * SS, cy - 20 * SS, cx + 38 * SS, cy + 20 * SS), 5 * SS,
                   fill=WHITE, outline=GREY, width=4 * SS)
            for k in range(5):
                dr.ellipse((cx - 26 * SS + k * 12 * SS, cy - 5 * SS,
                            cx - 16 * SS + k * 12 * SS, cy + 5 * SS), fill=GREY)
        else:                                        # a mouse cursor
            dr.polygon([(cx - 11 * SS, cy - 33 * SS), (cx - 11 * SS, cy + 25 * SS),
                        (cx + 3 * SS, cy + 11 * SS), (cx + 22 * SS, cy + 30 * SS),
                        (cx + 30 * SS, cy + 21 * SS), (cx + 12 * SS, cy + 3 * SS),
                        (cx + 27 * SS, cy - 3 * SS)], fill=GREY)
        _cross(dr, cx, cy, 44 * SS, (214, 92, 92), 5)
        _centre(dr, lab, fl, cx, int(H * 0.76), ABBEY)
    return _finish(im, w, h)


def quiet_change(w=760, h=230):
    """A tool answering normally, with one altered line the user cannot see.

    The point of the post is persistence and invisibility, not theft, so the image has
    to show something that still looks right.
    """
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    bx, by, bw, bh = int(W * 0.06), int(H * 0.16), int(W * 0.40), int(H * 0.66)
    _rrect(dr, (bx, by, bx + bw, by + bh), 10 * SS, fill=WHITE, outline=RULE, width=3 * SS)
    f = _font(14 * SS); fb = _font(14 * SS, bold=True)
    dr.text((bx + 18 * SS, by + 16 * SS), "before", font=fb, fill=GREY)
    for k in range(4):
        dr.line((bx + 18 * SS, by + 46 * SS + k * 18 * SS,
                 bx + bw - (26 if k == 3 else 18) * SS, by + 46 * SS + k * 18 * SS),
                fill=RULE, width=5 * SS)

    cx2 = int(W * 0.54)
    _rrect(dr, (cx2, by, cx2 + bw, by + bh), 10 * SS, fill=WHITE, outline=ORANGE, width=3 * SS)
    dr.text((cx2 + 18 * SS, by + 16 * SS), "after", font=fb, fill=ORANGE_DEEP)
    for k in range(4):
        col = ORANGE if k == 2 else RULE
        dr.line((cx2 + 18 * SS, by + 46 * SS + k * 18 * SS,
                 cx2 + bw - (26 if k == 3 else 18) * SS, by + 46 * SS + k * 18 * SS),
                fill=col, width=5 * SS)
    _centre(dr, "same name, same settings, one line you cannot see",
            _font(14 * SS, bold=True), int(W * 0.5), int(H * 0.87), ABBEY)
    return _finish(im, w, h)


def do_these(w=760, h=200):
    """Three actions, ticked. Deliberately the only image with ticks in it."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    f = _font(14 * SS, bold=True)
    fs = _font(12 * SS)
    items = [("update it", "let it install"), ("ask first", "approved route"), ("tell us", "if it feels off")]
    cw = W / 3
    for i, (a, b) in enumerate(items):
        cx = int(cw * i + cw / 2)
        cy = int(H * 0.38)
        dr.ellipse((cx - 40 * SS, cy - 40 * SS, cx + 40 * SS, cy + 40 * SS), fill=TINT)
        _tick(dr, cx, cy, 20 * SS)
        _centre(dr, a, f, cx, int(H * 0.66), ABBEY)
        _centre(dr, b, fs, cx, int(H * 0.82), GREY)
    return _finish(im, w, h)


def _phone(dr, cx, cy, w, colour=ABBEY, fill=WHITE):
    """A handset seen head on, screen and earpiece."""
    h = int(w * 1.75)
    _rrect(dr, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 10 * SS,
           fill=fill, outline=colour, width=3 * SS)
    dr.rounded_rectangle((cx - w * 0.18, cy - h / 2 + 8 * SS, cx + w * 0.18, cy - h / 2 + 13 * SS),
                         radius=3 * SS, fill=colour)
    return h


def _waveform(dr, x, y, w, bars, colour, peak=1.0):
    """A voice, drawn as a bar waveform. Same shape either side means the same voice."""
    import math
    step = w / (len(bars) * 1.0)
    for i, b in enumerate(bars):
        bx = x + i * step + step * 0.25
        bh = max(3, b * peak) * SS
        dr.rounded_rectangle((bx, y - bh, bx + step * 0.5, y + bh), radius=2 * SS, fill=colour)


def hero_voice_clone(w=760, h=255):
    """The mechanism: a few seconds of public audio becomes a voice you recognise.

    Deliberately NOT a picture of a criminal. The point of this attack is that nothing
    sounds wrong, so nothing in this image is allowed to look wrong either - the only
    red mark is on the word 'proves', not on the caller or the phone."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    f = _font(13 * SS, bold=True)
    fs = _font(11 * SS)
    y = int(H * 0.44)

    # left - the source material, entirely public and entirely ordinary
    lx = int(W * 0.14)
    _rrect(dr, (lx - 62 * SS, y - 34 * SS, lx + 62 * SS, y + 34 * SS), 8 * SS,
           fill=LIGHT, outline=RULE, width=2 * SS)
    WAVE = [7, 15, 26, 12, 30, 18, 9, 22, 14, 28, 11, 19]
    _waveform(dr, lx - 50 * SS, y, 100 * SS, WAVE, GREY, peak=0.9)
    _centre(dr, "a few seconds", f, lx, y + 46 * SS, ABBEY)
    _centre(dr, "of public audio", fs, lx, y + 64 * SS, GREY)

    # middle - the copy step, unremarkable on purpose
    mx = int(W * 0.44)
    _arrow(dr, [(lx + 66 * SS, y), (mx - 44 * SS, y)])
    _rrect(dr, (mx - 42 * SS, y - 26 * SS, mx + 42 * SS, y + 26 * SS), 8 * SS,
           fill=TINT, outline=ORANGE, width=3 * SS)
    _centre(dr, "copied", f, mx, y - 10 * SS, ORANGE_DEEP)
    _centre(dr, "in minutes", fs, mx, y + 8 * SS, GREY)

    # right - the call, and the SAME waveform, which is the whole argument
    rx = int(W * 0.76)
    _arrow(dr, [(mx + 46 * SS, y), (rx - 62 * SS, y)])
    ph = _phone(dr, rx, y, 58 * SS)
    _waveform(dr, rx - 22 * SS, y, 44 * SS, WAVE, ORANGE_DEEP, peak=0.42)
    _centre(dr, "a voice you know", f, rx, y + 46 * SS, ABBEY)
    _centre(dr, "asking for something", fs, rx, y + 64 * SS, GREY)

    # the one struck word in the image
    # The caption is the sentence the reader should keep, so it is NOT struck through.
    # A strike reads as "cancelled", which would invert the lesson. Strikes are for
    # negated glyphs only.
    cap = _font(12 * SS, bold=True)
    _centre(dr, "The voice is the copy. It proves nothing.", cap, W / 2, H - 30 * SS, ORANGE_DEEP)
    return _finish(im, w, h)


def verify_own_channel(w=760, h=215):
    """Before and after, drawn to the same scale: the number they gave you, and the
    number you already had. Nothing in the left panel looks wrong, because it does not."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(12 * SS, bold=True)
    f = _font(13 * SS, bold=True)
    fs = _font(11 * SS)

    mid = W // 2
    dr.line((mid, 20 * SS, mid, H - 26 * SS), fill=RULE, width=2 * SS)
    y = int(H * 0.50)

    # left - the route the caller offers
    lx = int(W * 0.25)
    _centre(dr, "THE ROUTE THEY OFFER", ft, lx, 22 * SS, GREY)
    _phone(dr, int(lx - 62 * SS), y, 46 * SS)
    _arrow(dr, [(int(lx - 32 * SS), y), (int(lx + 26 * SS), y)], colour=RED)
    _rrect(dr, (lx + 30 * SS, y - 26 * SS, lx + 138 * SS, y + 26 * SS), 8 * SS,
           fill=WHITE, outline=RED, width=3 * SS)
    _centre(dr, "a number", f, int(lx + 84 * SS), y - 12 * SS, ABBEY)
    _centre(dr, "they gave you", fs, int(lx + 84 * SS), y + 8 * SS, GREY)
    _centre(dr, "still the same caller", fs, lx, y + 52 * SS, RED)

    # right - the route you already had
    rx = int(W * 0.75)
    _centre(dr, "THE ROUTE YOU CHOOSE", ft, rx, 22 * SS, GREY)
    _rrect(dr, (rx - 148 * SS, y - 26 * SS, rx - 40 * SS, y + 26 * SS), 8 * SS,
           fill=TINT, outline=ORANGE, width=3 * SS)
    _centre(dr, "the directory", f, int(rx - 94 * SS), y - 12 * SS, ABBEY)
    _centre(dr, "you already had", fs, int(rx - 94 * SS), y + 8 * SS, GREY)
    _arrow(dr, [(int(rx - 36 * SS), y), (int(rx + 32 * SS), y)])
    _phone(dr, int(rx + 62 * SS), y, 46 * SS)
    _centre(dr, "a different person answers", fs, rx, y + 52 * SS, ORANGE_DEEP)
    return _finish(im, w, h)


def _key(dr, x, y, L, colour=ORANGE_DEEP):
    """A key drawn side on: ring, shaft, two teeth. Reads at small sizes."""
    r = int(L * 0.20)
    dr.ellipse((x, y - r, x + 2 * r, y + r), outline=colour, width=4 * SS)
    dr.line((x + 2 * r, y, x + L, y), fill=colour, width=5 * SS)
    dr.line((x + L - int(L * 0.06), y, x + L - int(L * 0.06), y + int(L * 0.16)),
            fill=colour, width=5 * SS)
    dr.line((x + L - int(L * 0.20), y, x + L - int(L * 0.20), y + int(L * 0.12)),
            fill=colour, width=5 * SS)


def _lock(dr, cx, cy, w, colour=GREY, fill=WHITE, shackle=True):
    """A padlock: shackle above, body below. Colour carries which lock matters."""
    h = int(w * 0.78)
    if shackle:
        s = int(w * 0.42)
        dr.arc((cx - s, cy - h // 2 - s, cx + s, cy - h // 2 + s),
               start=180, end=360, fill=colour, width=4 * SS)
    _rrect(dr, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5 * SS,
           fill=fill, outline=colour, width=4 * SS)
    dr.ellipse((cx - 4 * SS, cy - 6 * SS, cx + 4 * SS, cy + 2 * SS), fill=colour)
    dr.line((cx, cy + 1 * SS, cx, cy + 9 * SS), fill=colour, width=3 * SS)
    return h


def hero_one_key(w=760, h=250):
    """The mechanism of password reuse, with no attacker in it.

    There is no message in this attack - no email, no call, no page - so there is
    deliberately nothing in this image for the reader to spot. The argument is
    entirely in the geometry: ONE key, drawn once, reaching THREE locks, and the
    third one is the work lock. The leaked list on the left is drawn as an ordinary
    document because that is what it is; making it sinister would suggest the
    employee could have seen it coming, and they could not."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    f = _font(13 * SS, bold=True)
    fs = _font(11 * SS)
    y = int(H * 0.42)

    # left - a list from somewhere else entirely. Ordinary on purpose.
    lx = int(W * 0.13)
    _rrect(dr, (lx - 40 * SS, y - 40 * SS, lx + 40 * SS, y + 34 * SS), 6 * SS,
           fill=LIGHT, outline=RULE, width=3 * SS)
    for i in range(5):
        ly = y - 28 * SS + i * 13 * SS
        dr.line((lx - 28 * SS, ly, lx + 20 * SS, ly), fill=GREY, width=3 * SS)
    _centre(dr, "a list leaked", f, lx, y + 46 * SS, ABBEY)
    _centre(dr, "somewhere else", fs, lx, y + 64 * SS, GREY)

    # middle - one key. Drawn ONCE, which is the whole point.
    mx = int(W * 0.40)
    _arrow(dr, [(lx + 46 * SS, y), (mx - 52 * SS, y)])
    _key(dr, mx - 44 * SS, y, 88 * SS)
    _centre(dr, "one password", f, mx, y + 46 * SS, ORANGE_DEEP)
    _centre(dr, "reused", fs, mx, y + 64 * SS, GREY)

    # right - three locks, and only the third one is GeneLabs's
    rx = int(W * 0.76)
    labels = [("a shop", GREY, WHITE), ("a forum", GREY, WHITE), ("work", ORANGE, TINT)]
    for i, (lab, col, fill) in enumerate(labels):
        cy = int(H * 0.20) + i * int(H * 0.28)
        _arrow(dr, [(mx + 54 * SS, y), (rx - 40 * SS, cy)],
               colour=ORANGE if i == 2 else RULE, width=4, head=11)
        _lock(dr, rx, cy, 46 * SS, colour=col, fill=fill)
        dr.text((rx + 34 * SS, cy - 7 * SS), lab,
                font=f if i == 2 else fs, fill=ABBEY if i == 2 else GREY)

    cap = _font(12 * SS, bold=True)
    _centre(dr, "The same key opens every lock it was ever used on.",
            cap, W / 2, H - 26 * SS, ORANGE_DEEP)
    return _finish(im, w, h)


def silent_then_one_prompt(w=760, h=235):
    """Before and after at the same scale: the attack is invisible, except once.

    The left panel is empty because the attack really is invisible - drawing a
    warning triangle there would be a lie. The right panel is the single moment the
    employee gets, and it is the only thing in the image with any colour."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    ft = _font(12 * SS, bold=True)
    f = _font(13 * SS, bold=True)
    fs = _font(11 * SS)

    mid = W // 2
    dr.line((mid, 20 * SS, mid, H - 30 * SS), fill=RULE, width=2 * SS)
    y = int(H * 0.50)

    # left - nothing. Deliberately, and the caption says so. The captions sit BELOW
    # the laptop base: an earlier draft put the grey line at y+44, which landed on
    # the dark base bar and rendered dark-on-dark and unreadable.
    lx = int(W * 0.25)
    _centre(dr, "WHILE IT IS HAPPENING", ft, lx, 22 * SS, GREY)
    _laptop(dr, int(lx - 62 * SS), int(y - 52 * SS), 124 * SS)
    _centre(dr, "no email, no call, no page", fs, lx, y + 52 * SS, GREY)
    _centre(dr, "nothing reaches you at all", f, lx, y + 70 * SS, ABBEY)

    # right - the one prompt, the only coloured thing in the picture
    rx = int(W * 0.75)
    _centre(dr, "THE ONE MOMENT YOU SEE", ft, rx, 22 * SS, GREY)
    ph = _phone(dr, rx, y, 62 * SS, colour=ORANGE, fill=TINT)
    _centre(dr, "Approve", f, rx, y - 18 * SS, ORANGE_DEEP)
    _centre(dr, "sign-in?", f, rx, y + 2 * SS, ORANGE_DEEP)
    _centre(dr, "a prompt you did not ask for", f, rx, y + 70 * SS, ABBEY)

    cap = _font(12 * SS, bold=True)
    _centre(dr, "Dismissing it stops that attempt. Reporting it stops the rest.",
            cap, W / 2, H - 26 * SS, ORANGE_DEEP)
    return _finish(im, w, h)


def hero_stolen_session(w=760, h=250):
    """Why a stolen session defeats MFA, argued in geometry rather than words.

    The five earlier heroes all show something ARRIVING, or a key being reused. This
    attack is different again: the attacker never meets the front door at all. So the
    door is drawn intact and correct - a lock AND a second lock for MFA, both closed -
    and the copied session is drawn going PAST them, not through them. Nothing in the
    picture is broken, which is the honest depiction: every control worked and the
    account was still entered."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    f = _font(13 * SS, bold=True)
    fs = _font(11 * SS)
    y = int(H * 0.40)

    # left - the machine, with something small taken off it
    lx = int(W * 0.14)
    _laptop(dr, lx - 52 * SS, y - 34 * SS, 104 * SS)
    _rrect(dr, (lx - 16 * SS, y - 22 * SS, lx + 26 * SS, y - 2 * SS), 4 * SS,
           fill=TINT, outline=ORANGE, width=3 * SS)
    _centre(dr, "your signed-in", f, lx, y + 44 * SS, ABBEY)
    _centre(dr, "session, copied", fs, lx, y + 62 * SS, GREY)

    # middle - the front door, WORKING. Both locks closed.
    mx = int(W * 0.47)
    _rrect(dr, (mx - 52 * SS, int(H * 0.13), mx + 52 * SS, int(H * 0.80)), 8 * SS,
           fill=LIGHT, outline=RULE, width=3 * SS)
    _lock(dr, mx, int(H * 0.31), 40 * SS, colour=GREY, fill=WHITE)
    _lock(dr, mx, int(H * 0.58), 40 * SS, colour=GREY, fill=WHITE)
    _centre(dr, "password", fs, mx, int(H * 0.42), GREY)
    _centre(dr, "and MFA", fs, mx, int(H * 0.69), GREY)
    _centre(dr, "both still working", fs, mx, int(H * 0.88), GREY)

    # the copied session goes AROUND, over the top. Nothing is broken.
    _arrow(dr, [(lx + 58 * SS, y - 18 * SS),
                (mx - 10 * SS, int(H * 0.05)),
                (mx + 70 * SS, int(H * 0.05)),
                (int(W * 0.78) - 44 * SS, int(H * 0.34))],
           colour=ORANGE, width=5, head=13)

    # right - inside the account
    rx = int(W * 0.80)
    _browser(dr, rx - 44 * SS, int(H * 0.26), 96 * SS, 62 * SS,
             title_bar=TINT, body=WHITE, border=ORANGE)
    _centre(dr, "already inside", f, rx + 4 * SS, int(H * 0.66), ORANGE_DEEP)
    _centre(dr, "no sign-in needed", fs, rx + 4 * SS, int(H * 0.79), GREY)

    cap = _font(12 * SS, bold=True)
    _centre(dr, "Nothing here is broken. The attacker simply never used the door.",
            cap, W / 2, H - 16 * SS, ORANGE_DEEP)
    return _finish(im, w, h)


def new_password_not_enough(w=760, h=190):
    """The one instruction this post exists to correct.

    Changing the password is drawn as genuinely effective - a fresh key, a closed
    lock - and then the open side door is drawn beside it, still open. The reader
    should come away understanding that the usual advice is not wrong, it is just
    incomplete, which is a harder and more useful thing to convey than 'do this'."""
    im, dr = _canvas(w, h)
    W, H = w * SS, h * SS
    f = _font(12.5 * SS, bold=True)
    fs = _font(10.5 * SS)
    y = int(H * 0.42)

    lx = int(W * 0.26)
    _key(dr, lx - 44 * SS, y, 76 * SS)
    _lock(dr, lx + 60 * SS, y, 42 * SS, colour=ORANGE, fill=TINT)
    _centre(dr, "a new password", f, lx + 8 * SS, y + 52 * SS, ABBEY)
    _centre(dr, "closes this", fs, lx + 8 * SS, y + 70 * SS, GREY)

    dr.line((int(W * 0.50), int(H * 0.16), int(W * 0.50), int(H * 0.84)),
            fill=RULE, width=3 * SS)

    rx = int(W * 0.74)
    _rrect(dr, (rx - 46 * SS, y - 44 * SS, rx + 46 * SS, y + 34 * SS), 6 * SS,
           fill=WHITE, outline=ORANGE, width=4 * SS)
    dr.line((rx + 46 * SS, y - 44 * SS, rx + 74 * SS, y - 26 * SS),
            fill=ORANGE, width=4 * SS)
    dr.line((rx + 46 * SS, y + 34 * SS, rx + 74 * SS, y + 16 * SS),
            fill=ORANGE, width=4 * SS)
    _centre(dr, "the copied session", f, rx, y + 52 * SS, ORANGE_DEEP)
    _centre(dr, "stays open", fs, rx, y + 70 * SS, GREY)
    return _finish(im, w, h)


SCENES = {
    "hero_driveby":   hero_driveby,
    "three_absences": three_absences,
    "quiet_change":   quiet_change,
    "do_these":       do_these,
    "hero_voice_clone":   hero_voice_clone,
    "verify_own_channel": verify_own_channel,
    "hero_one_key":          hero_one_key,
    "silent_then_one_prompt": silent_then_one_prompt,
    "hero_stolen_session":    hero_stolen_session,
    "new_password_not_enough": new_password_not_enough,
}


def render(name, outdir):
    im = SCENES[name]()
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, f"{name}.png")
    im.save(p, "PNG")
    return p


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for n in SCENES:
        print(render(n, out))
