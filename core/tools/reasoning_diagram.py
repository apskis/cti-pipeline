#!/usr/bin/env python3
"""Chain-of-reasoning diagrams for GeneLabs CTI appendices.

April, 2026-08-27: *"We need to know your reasoning but it's a lot of words, maybe a
flow chart using pictures?"*

She is right, and the reason is specific rather than aesthetic. A reasoning appendix
written as prose forces the reader to hold the whole argument in their head to check any
one link in it. Drawn as a chain, each link can be checked on its own — which is what a
reviewer actually wants to do. They rarely read the argument end to end; they look for the
step they doubt.

WHAT THESE DIAGRAMS ENCODE THAT PROSE HIDES

Every node carries its EPISTEMIC STATUS in its colour, so a reader can see at a glance
which parts of the argument are measured and which are inferred:

    MEASURED   solid orange fill     a connector or query produced this number
    INFERRED   white, orange outline  a judgement drawn from measured facts
    RULED OUT  grey, struck through   a reading that was tested and DISPROVED
    OPEN       dashed outline         the question that would change the conclusion

The RULED OUT node is the one that matters most and the one prose loses. An argument that
shows only what it concluded reads as advocacy; one that shows what it tested and rejected
reads as analysis. On the PKIW02 advisory the falsified nodes are load bearing — RDP
looked internet reachable and was not, and a the public web classification in an earlier
advisory turned out to be scanner noise.

Nodes are laid out left to right in columns; edges connect by index. The caller supplies
the graph, so this module knows nothing about any particular finding.

Raster, drawn at 3x and downsampled, because no SVG converter exists in this environment.
Labels use Liberation Sans, metrically compatible with Arial.
"""
from PIL import Image, ImageDraw, ImageFont
import glob, os, textwrap

ORANGE      = (255, 113,   9)
ORANGE_DEEP = (224,  95,   0)
TINT        = (255, 244, 232)
ABBEY       = ( 68,  70,  72)
GREY        = (103, 103, 101)
MUTED       = (150, 150, 148)
LIGHT       = (244, 244, 244)
RULE        = (217, 217, 217)
WHITE       = (255, 255, 255)

SS = 3

STATUS = {
    "measured":  {"fill": TINT,   "outline": ORANGE, "text": ABBEY, "width": 3, "dash": False},
    "inferred":  {"fill": WHITE,  "outline": ORANGE, "text": ABBEY, "width": 2, "dash": False},
    "ruled_out": {"fill": LIGHT,  "outline": MUTED,  "text": MUTED, "width": 2, "dash": False},
    "open":      {"fill": WHITE,  "outline": GREY,   "text": ABBEY, "width": 2, "dash": True},
}


def _font(size, bold=False):
    pat = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    hits = glob.glob(f"/usr/share/fonts/**/{pat}", recursive=True)
    return ImageFont.truetype(hits[0], size) if hits else ImageFont.load_default()


def _dashed_rect(dr, box, r, outline, width, dash=14, gap=10):
    """Pillow has no dashed outline. Walk the perimeter and stroke segments."""
    x0, y0, x1, y1 = box
    pts = []
    for x in range(int(x0 + r), int(x1 - r), 1):
        pts.append((x, y0))
    for y in range(int(y0 + r), int(y1 - r), 1):
        pts.append((x1, y))
    for x in range(int(x1 - r), int(x0 + r), -1):
        pts.append((x, y1))
    for y in range(int(y1 - r), int(y0 + r), -1):
        pts.append((x0, y))
    i, n = 0, len(pts)
    while i < n:
        seg = pts[i:i + dash]
        if len(seg) > 1:
            dr.line(seg, fill=outline, width=width)
        i += dash + gap


def _node(dr, box, label, status, font, sub=None, subfont=None):
    st = STATUS[status]
    x0, y0, x1, y1 = box
    r = 9 * SS
    if st["dash"]:
        dr.rounded_rectangle(box, radius=r, fill=st["fill"])
        _dashed_rect(dr, box, r, st["outline"], st["width"] * SS)
    else:
        dr.rounded_rectangle(box, radius=r, fill=st["fill"],
                             outline=st["outline"], width=st["width"] * SS)
    inner_w = (x1 - x0) - 20 * SS
    approx = max(int(inner_w / (font.size * 0.52)), 8)
    lines = textwrap.wrap(label, approx)
    sub_lines = textwrap.wrap(sub, approx + 4) if sub else []
    lh = font.size * 1.22
    slh = (subfont.size * 1.18) if subfont else 0
    total = len(lines) * lh + (len(sub_lines) * slh + 6 * SS if sub_lines else 0)
    y = (y0 + y1) / 2 - total / 2
    for ln in lines:
        w = dr.textlength(ln, font=font)
        dr.text(((x0 + x1) / 2 - w / 2, y), ln, font=font, fill=st["text"])
        y += lh
    if sub_lines:
        y += 6 * SS
        for ln in sub_lines:
            w = dr.textlength(ln, font=subfont)
            dr.text(((x0 + x1) / 2 - w / 2, y), ln, font=subfont, fill=GREY)
            y += slh
    if status == "ruled_out":
        # Struck through, not crossed out: the node stays readable because WHAT was ruled
        # out is the informative part. A cross would hide it.
        dr.line((x0 + 12 * SS, (y0 + y1) / 2, x1 - 12 * SS, (y0 + y1) / 2),
                fill=MUTED, width=2 * SS)


def _edge(dr, a, b, label=None, font=None, colour=ORANGE):
    """Elbow connector from the right edge of a to the left edge of b."""
    ax, ay = a[2], (a[1] + a[3]) / 2
    bx, by = b[0], (b[1] + b[3]) / 2
    mid = ax + (bx - ax) / 2
    pts = [(ax, ay), (mid, ay), (mid, by), (bx, by)]
    dr.line(pts, fill=colour, width=3 * SS, joint="curve")
    h = 11 * SS
    dr.polygon([(bx, by), (bx - h, by - h * 0.5), (bx - h, by + h * 0.5)], fill=colour)
    if label and font:
        w = dr.textlength(label, font=font)
        lx, ly = mid - w / 2, min(ay, by) + abs(by - ay) / 2 - font.size * 0.7
        dr.rectangle((lx - 5 * SS, ly - 2 * SS, lx + w + 5 * SS, ly + font.size + 2 * SS),
                     fill=WHITE)
        dr.text((lx, ly), label, font=font, fill=GREY)


def chain(columns, edges, width=740, col_gap=26, node_h=76, row_gap=14, title=None):
    """Draw a left-to-right reasoning chain.

    columns : list of columns; each column is a list of node dicts
              {"label": str, "status": str, "sub": str (optional)}
    edges   : list of ((col_i, node_i), (col_j, node_j), label or None)
    """
    ncols = len(columns)
    col_w = (width - col_gap * (ncols - 1)) / ncols
    rows = max(len(c) for c in columns)
    head = 26 if title else 0
    height = int(head + rows * node_h + (rows - 1) * row_gap + 30)

    im = Image.new("RGB", (width * SS, height * SS), WHITE)
    dr = ImageDraw.Draw(im)
    f = _font(int(12.5 * SS))
    fs = _font(int(10.5 * SS))
    ft = _font(int(11 * SS), bold=True)
    fe = _font(int(10 * SS))

    if title:
        dr.text((2 * SS, 2 * SS), title.upper(), font=ft, fill=ORANGE_DEEP)

    boxes = []
    for ci, col in enumerate(columns):
        cx0 = ci * (col_w + col_gap)
        colh = len(col) * node_h + (len(col) - 1) * row_gap
        top = head + ((rows * node_h + (rows - 1) * row_gap) - colh) / 2 + 14
        cb = []
        for ni, node in enumerate(col):
            y0 = top + ni * (node_h + row_gap)
            box = (cx0 * SS, y0 * SS, (cx0 + col_w) * SS, (y0 + node_h) * SS)
            _node(dr, box, node["label"], node.get("status", "inferred"), f,
                  node.get("sub"), fs)
            cb.append(box)
        boxes.append(cb)

    for (ci, ni), (cj, nj), *rest in edges:
        lab = rest[0] if rest else None
        _edge(dr, boxes[ci][ni], boxes[cj][nj], lab, fe)

    return im.resize((width, height), Image.LANCZOS)


def legend(width=740, height=34):
    """The key. Always render it directly beneath the first diagram in a document —
    the colour coding is the whole point and is not self-evident."""
    im = Image.new("RGB", (width * SS, height * SS), WHITE)
    dr = ImageDraw.Draw(im)
    f = _font(int(10.5 * SS))
    items = [("measured", "measured — a query produced this"),
             ("inferred", "inferred from those facts"),
             ("ruled_out", "tested and ruled out"),
             ("open", "open question")]
    x = 0
    for status, text in items:
        st = STATUS[status]
        box = (x, 8 * SS, x + 26 * SS, 26 * SS)
        if st["dash"]:
            dr.rounded_rectangle(box, radius=4 * SS, fill=st["fill"])
            _dashed_rect(dr, box, 4 * SS, st["outline"], 2 * SS, dash=8, gap=6)
        else:
            dr.rounded_rectangle(box, radius=4 * SS, fill=st["fill"],
                                 outline=st["outline"], width=st["width"] * SS)
        if status == "ruled_out":
            dr.line((box[0] + 4 * SS, 17 * SS, box[2] - 4 * SS, 17 * SS), fill=MUTED, width=2 * SS)
        dr.text((x + 33 * SS, 10 * SS), text, font=f, fill=GREY)
        x += int(dr.textlength(text, font=f)) + 62 * SS
    return im.resize((width, height), Image.LANCZOS)


def render(image, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, "PNG")
    return path
