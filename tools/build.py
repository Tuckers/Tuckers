#!/usr/bin/env python3
"""Builds the SVGs in assets/ that the profile README is made of.

GitHub strips CSS from a README, so the designed parts are SVG images. An SVG
image cannot load a web font, so the type is outlined (tools/outline.swift),
and it cannot follow GitHub's theme by itself, so every asset is written twice,
`-light` and `-dark`, and the README picks one with <picture>.

Run from anywhere:  python3 tools/build.py
Needs macOS with Aktiv Grotesk installed (Adobe Fonts) and the Swift compiler.
"""

import base64
import json
import subprocess
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ASSETS = TOOLS.parent / "assets"
OUTLINE_SRC = TOOLS / "outline.swift"
OUTLINE_BIN = TOOLS / ".build" / "outline"

REGULAR = "AktivGrotesk-Regular"
MEDIUM = "AktivGrotesk-Medium"

# The same palette as tucker.xxx.
THEMES = {
    "light": {"ink": "#111111", "muted": "#6a6a6a"},
    "dark": {"ink": "#e1e1e1", "muted": "#909090"},
}
AMBER = "#f6ad35"
AMBER_INK = "#111111"

# The README column on a GitHub profile is 846px wide; everything is drawn at
# that size and scales down from there.
WIDTH = 846
GUTTER = 16

# The mark from the site's favicon, and the box it sits in there.
MARK = (
    "M96.4531 35.3584H69.6797V62.8418L93.4814 49.1006L99.1602 58.9375L75.3574 "
    "72.6787L99.1602 86.4209L93.4814 96.2578L69.6797 82.5156V110H58.3203V82.5156"
    "L34.5186 96.2578L28.8398 86.4209L52.6406 72.6787L28.8398 58.9375L34.5186 "
    "49.1006L58.3203 62.8418V35.3584H31.5469V24H96.4531V35.3584Z"
)
MARK_BOX = (28.84, 24.0, 70.32, 86.0)  # x, y, width, height


def compile_outline():
    if OUTLINE_BIN.exists() and OUTLINE_BIN.stat().st_mtime >= OUTLINE_SRC.stat().st_mtime:
        return
    OUTLINE_BIN.parent.mkdir(exist_ok=True)
    subprocess.run(["swiftc", "-O", str(OUTLINE_SRC), "-o", str(OUTLINE_BIN)], check=True)


_outlines = {}


def outline(text, font, size, tracking=0.0):
    """Path data and advance width for one line of text."""
    key = (text, font, size, tracking)
    if key not in _outlines:
        out = subprocess.run(
            [str(OUTLINE_BIN), font, str(size), str(tracking), text],
            check=True, capture_output=True, text=True,
        ).stdout
        _outlines[key] = json.loads(out)
    return _outlines[key]


def n(value):
    """A number as short as SVG allows."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def text(string, x, baseline, font, size, fill, tracking=0.0, anchor="start"):
    """One line of outlined text. Returns (svg, left edge, width)."""
    o = outline(string, font, size, tracking)
    left = x - o["width"] if anchor == "end" else x
    svg = f'<path transform="translate({n(left)} {n(baseline)})" fill="{fill}" d="{o["d"]}"/>'
    return svg, left, o["width"]


def photo(name, x, y, width, height):
    data = base64.b64encode((TOOLS / "img" / f"{name}.jpg").read_bytes()).decode()
    return (
        f'<image x="{n(x)}" y="{n(y)}" width="{n(width)}" height="{n(height)}" '
        f'preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{data}"/>'
    )


def arrow(x, y, size, stroke):
    """An arrow pointing up and to the right, its box's top right corner at (x, y)."""
    return (
        f'<path fill="none" stroke="{stroke}" stroke-width="1.6" stroke-linecap="square" '
        f'd="M{n(x - size)} {n(y + size)}L{n(x)} {n(y)}M{n(x - size * 0.8)} {n(y)}H{n(x)}V{n(y + size * 0.8)}"/>'
    )


def write(name, theme, width, height, body, title):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {n(width)} {n(height)}" width="{n(width)}" height="{n(height)}" '
        f'role="img" aria-label="{title}"><title>{title}</title>{"".join(body)}</svg>\n'
    )
    (ASSETS / f"{name}-{theme}.svg").write_text(svg)


def header(theme, colors):
    ink = colors["ink"]
    body = []

    scale = 38 / MARK_BOX[3]
    body.append(
        f'<path transform="translate({n(-MARK_BOX[0] * scale)} {n(4 - MARK_BOX[1] * scale)}) '
        f'scale({n(scale)})" fill="{ink}" d="{MARK}"/>'
    )

    link, left, width = text("tucker.xxx", WIDTH, 32, REGULAR, 21, ink, anchor="end")
    body.append(link)
    body.append(f'<rect x="{n(left)}" y="37" width="{n(width)}" height="1.5" fill="{ink}"/>')

    name, _, _ = text("tucker spofford", -4, 160, MEDIUM, 92, ink, tracking=-2.2)
    body.append(name)

    lead, left, width = text("design director who ", 0, 216, REGULAR, 31, ink)
    body.append(lead)
    marked_x = left + width + 7
    marked = outline("ships code", REGULAR, 31)
    # The site's hover state, held still: amber behind dark ink.
    body.append(f'<rect x="{n(marked_x - 7)}" y="186" width="{n(marked["width"] + 14)}" height="42" fill="{AMBER}"/>')
    body.append(text("ships code", marked_x, 216, REGULAR, 31, AMBER_INK)[0])

    write("header", theme, WIDTH, 236, body, "Tucker Spofford, design director who ships code")


def label(slug, string, theme, colors):
    words, _, width = text(string, 20, 19, MEDIUM, 20, colors["ink"], tracking=0.1)
    body = [f'<rect x="0" y="7" width="11" height="11" fill="{AMBER}"/>', words]
    write(f"label-{slug}", theme, round(20 + width + 2), 26, body, string)


def card(slug, title, caption, theme, colors, column, columns, image_height, sizes):
    """An image with a title and a line under it, one of `columns` in a row.

    Each card is exactly 1/columns of the row wide, and the gutter is drawn
    inside the cards, so the README can set them side by side with no space
    between and the row's edges line up with the text above and below.
    """
    slot = WIDTH / columns
    content = (WIDTH - GUTTER * (columns - 1)) / columns
    x = column * (content + GUTTER) - column * slot
    title_size, caption_size = sizes

    title_y = image_height + title_size * 1.5
    caption_y = title_y + caption_size * 1.6
    body = [
        photo(slug, x, 0, content, image_height),
        text(title, x, title_y, MEDIUM, title_size, colors["ink"], tracking=-0.2)[0],
        arrow(x + content - 1, title_y - title_size * 0.62, title_size * 0.42, colors["ink"]),
        text(caption, x, caption_y, REGULAR, caption_size, colors["muted"])[0],
    ]
    write(slug, theme, slot, caption_y + caption_size * 1.1, body, f"{title}: {caption}")


def main():
    compile_outline()
    ASSETS.mkdir(exist_ok=True)

    for theme, colors in THEMES.items():
        header(theme, colors)

        for slug, string in [
            ("building-now", "building now"),
            ("away-from-the-keyboard", "away from the keyboard"),
            ("working-with", "working with"),
            ("find-me", "find me"),
        ]:
            label(slug, string, theme, colors)

        projects = [
            ("paramecium", "paramecium", "parametric cad for people who make things"),
            ("murray", "murray", "a premium, american made camp stove"),
        ]
        for column, (slug, title, caption) in enumerate(projects):
            card(slug, title, caption, theme, colors, column, 2, 270, (27, 15.5))

        pursuits = [
            ("van", "safari sprinter", "a 4x4 campervan, built by hand"),
            ("oddhours", "oddhours", "open sometimes, almost never"),
            ("photography", "photography", "medium format, film and digital"),
        ]
        for column, (slug, title, caption) in enumerate(pursuits):
            card(slug, title, caption, theme, colors, column, 3, 184, (20, 13.5))

    for path in sorted(ASSETS.glob("*.svg")):
        print(f"{path.stat().st_size / 1024:7.1f} KB  {path.name}")


if __name__ == "__main__":
    main()
