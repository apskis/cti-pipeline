---
name: "genelabs-employee-awareness-blog"
description: "Produce the GeneLabs all-employee security awareness post in the SHORT ILLUSTRATED BLOG format — 350-450 words across two pages with custom flat illustrations, a standfirst, a pull quote and an actions card, instead of the long-form bulletin layout. Same AWR-YYYY-MM-DD identity, same TLP:CLEAR sanitisation gate and same topic ledger as genelabs-employee-awareness. Use when the employee post should read like a blog rather than a document, when April asks for it \"less wordy\" or \"with pictures\", or for any awareness topic whose value is a single clear idea. For the long-form analytical-style employee post use genelabs-employee-awareness; for the security-team bulletin use genelabs-cti-bulletin."
---

# GeneLabs Employee Awareness — Blog Format

The **second** format for the `AWR-YYYY-MM-DD` series. Same reader, same identity, same
sanitisation rules as `genelabs-employee-awareness`; different shape.

> **Use this when the post has ONE clear idea.** Use the long form when the topic needs
> the reader to hold several things at once. Choosing the blog format for a genuinely
> multi-part topic produces a post that is short and inadequate, which is worse than one
> that is long and complete.

## Why this exists as a separate format

The long-form builder wraps the CTI bulletin builder, and it should — the analytical set
has to look like one family. But a bulletin layout puts a category tag, an audience line,
a severity callout, a detail table and a numbered source list in front of the reader
before a single usable sentence. In a bulletin that furniture is the point. In an
all-employee post it signals *compliance document*, and people scroll past compliance
documents.

April, 2026-08-27: *"less wordy, with pictures, more like a blog."*

Measured on the same topic the same day: long form **997 words**, blog form **363**.
Nothing was dropped that an employee needed.

## Where things live

| Item | Path |
| --- | --- |
| Builder | `CTI Deliverables\_tools\build_awareness_blog.py` |
| Illustrations | `CTI Deliverables\_tools\awareness_art.py` |
| Sanitisation gate | `CTI Deliverables\_tools\verify_awareness.py` (shared, unchanged) |
| Topic ledger | `CTI Deliverables\CTI Bulletins\2026\Employee Awareness\_awareness_topic_log.md` |
| Topic pipeline | `...\Employee Awareness\_awareness_topic_pipeline.md` |
| Rendered art, kept with the post | `...\Employee Awareness\_art\` |
| Output | `...\Employee Awareness\AWR-YYYY-MM-DD-Title_Case_Slug.docx` |

Both scripts are workspace tooling, not part of this skill directory, because a saved
skill stores only `SKILL.md`. This file specifies both completely enough to rebuild them.

**It does NOT wrap the bulletin builder.** It draws its own layout using the same
palette, typeface and footer furniture, so it is unmistakably GeneLabs while being
organised like a post.

## What does not change, and must not

- **`AWR-YYYY-MM-DD` identity and filename.** Never consume the `CTIYY-NN` series.
- **TLP:CLEAR**, enforced by the builder, which refuses to run otherwise.
- **The full sanitisation rule.** No internal hostnames, IPs, hunt or bulletin IDs, CVE
  numbers, tool names, technique IDs, or any statement about what GeneLabs monitors,
  detects, licenses or covers. The format got friendlier; the document still has no
  access control and is still trivially screenshotted.
- **The three universal instructions**: report it, reporting is never a waste of anyone's
  time, nobody is in trouble for reporting.
- **The repetition rule and the ledger.** 90 days unless the tactic fingerprint has
  materially changed. Append a ledger row after publishing.
- **`verify_awareness.py` must pass.** Same gate, same `--topic-key`, `--fingerprint`,
  `--ledger`, `--awr`, `--channel` arguments.

## Shape of the document

Two pages, in this order. Every element is optional except the headline, one image and
the actions card.

1. **Kicker** — small orange caps, e.g. `SECURITY, IN PLAIN ENGLISH`. Series furniture;
   keep it constant so the post is recognisable at a glance.
2. **Headline** — 22pt, the action or the claim. It must be useful to someone who reads
   nothing else.
3. **Standfirst** — one grey sentence that makes the reader want the next one.
4. **Hero image**, with a caption that adds something rather than restating.
5. **Short text blocks**, two or three sentences each. Never four.
6. **A pull quote** — the one line you want remembered.
7. **More images between sections**, so no page is a wall of text.
8. **The actions card** — shaded, three items, closing on reporting.
9. **Sources**, two or three, plain domains rather than full URLs.
10. **Contact line.**

### Word budget

**350–450 words of body copy.** The builder counts and warns above 500. If a draft is
over, **cut a section — do not tighten sentences.** Tightened prose in a long post is
still a long post; the format's whole value is that the reader finishes it.

### Two pages, not three

The commonest failure is a third page holding only the sources block. That page costs a
sheet and signals the document continues when it does not. Fix it by taking width off
the images (5.9in is the working default, 6.4 was too wide) rather than by cutting copy.

## Illustrations

`awareness_art.py` draws flat scenes with Pillow. **Draw, do not source**, for three
reasons:

1. No stock library can illustrate "a web page reached a program on your laptop". Every
   result for that search is a hooded figure at a keyboard, the most tired image in
   security communication, and it teaches the reader nothing.
2. Licensing. A post that goes to every employee and gets screenshotted needs art
   GeneLabs owns outright.
3. The palette must be the house palette. Drawing guarantees it.

Rendered at 3x and downsampled, which is what keeps edges clean at document scale.
Labels use Liberation Sans, metrically compatible with Arial and, unlike Arial, actually
installed in the build environment.

**Design rules learned building the first set:**

- **A negated glyph must stay legible through its cross.** The first `three_absences`
  draft put 20pt icons under a heavy 34pt cross; the document icon was unreadable and
  the image said only "no" three times. Glyphs are now ~40% larger and the cross is
  lighter weight in a softer red, so it reads as struck through rather than obliterated.
- **Show the mechanism, not the villain.** An arrow travelling from the page *into* the
  laptop carries the whole argument of a drive-by post.
- **Before/after beats a warning symbol** where the point is that something still looks
  right.
- **Ticks appear in exactly one image**, the actions one, so they mean something.

Add a scene as a function and register it in `SCENES`.

## Build

```
python build_awareness_blog.py spec.json out.docx <genelabs-cti-bulletin skill dir> [art_dir]
python verify_awareness.py out.docx --topic-key <key> --fingerprint "<tactics>" \
       --ledger "<Employee Awareness>/_awareness_topic_log.md" --awr AWR-YYYY-MM-DD \
       --channel none
```

The builder renders every scene into `art_dir` first, so a rebuild is reproducible. Copy
the rendered PNGs into `_art\` beside the post.

`--channel` declares what the post is ABOUT so channel-specific instructions are required
only where they make sense. Valid: `phone call`, `pasted command`, `none`. A blog post
that rules other channels out in prose ("no attachment, nothing to paste") will trip the
inference heuristic if the channel is not declared — that is what the flag is for.

Needs `python-docx` and `Pillow`.

## JSON spec

```json
{
  "report_id": "AWR-2026-08-27",
  "tlp": "CLEAR",
  "kicker": "Security, in plain English",
  "title": "Action-first headline",
  "standfirst": "One sentence that earns the next one.",
  "blocks": [
    {"type": "image",   "scene": "hero_driveby", "caption": "Adds something."},
    {"type": "text",    "paragraphs": ["Two or three sentences.", "Then two or three more."]},
    {"type": "heading", "text": "So what actually happens?"},
    {"type": "pull",    "text": "The line you want remembered."},
    {"type": "card",    "heading": "Three things, and the last one matters most",
                        "items": ["...", "...", "Reporting is never a waste of anyone's time, and nobody is in trouble for reporting."]}
  ],
  "sources": ["Outlet, date — domain.com"],
  "footer_contact": "secops@genelabs.com  |  ServiceNow"
}
```

Block types: `image`, `text`, `heading`, `pull`, `card`. Unknown types exit with an error
rather than rendering nothing.

## Voice

As the long form: no jargon, no acronyms needing a glossary, sentences under 45 words,
plain about there being nothing to install when that is true. Two things the shorter
format makes easier and you should exploit:

- **Say the counter-intuitive thing early.** "No attachment. No password box. Nothing to
  click." earns more attention than any amount of context.
- **Where a real victim was fooled despite knowing better, say so kindly.** In this
  format it is usually one sentence, and it is the most persuasive sentence in the post.
  Never let it read as blame — in the 27 August post the line was that the setting which
  caused the problem was chosen by the software, not by the people running it.

## Branding

Applied by the builder; do not override.

| Element | Value |
| --- | --- |
| Kicker, pull quote, card heading | GeneLabs orange `#FF7109` / `#E05F00` |
| Headline and body | Abbey `#444648` |
| Standfirst, captions, sources | Corporate grey `#676765` |
| Actions card fill | `#FFF4E8` |
| Typeface | Arial throughout |

Footer: wordmark, `TLP: CLEAR` with the **value in house black, regular weight** (orange
reads as an alert on a document meant to be calm), the label
`Employee Security Awareness`, copyright, `DOC #` and live `Page X of Y`, under an orange
rule.

**The TLP label and value are SEPARATE runs.** The gate locates the value run by its text
to assert its colour, and a combined `TLP: CLEAR` run defeats that check — it did exactly
that on the first build of this format. A new format must never be the reason a safety
check quietly stops applying.

