#!/usr/bin/env python3
"""
Generates the NUKE (MegaTNT) block texture and its HUD badge icon from the
existing tnt.png - same brick-block silhouette, recolored, with the "TNT"
lettering replaced by a radiation-trefoil logo.

SUPER_TNT's block texture, the CREEPER block texture, and the RAIN command
icon are now hand-drawn (see src/assets/Moje/ for the originals) rather than
generated - this script no longer touches those files.

Run once with: python scripts/generate_tnt_variants.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

BLOCK_DIR = Path(__file__).parent.parent / "src" / "assets" / "block"
ITEM_DIR = Path(__file__).parent.parent / "src" / "assets" / "item"

LIGHT_BG = (221, 217, 217, 255)  # a light panel shade already present in tnt.png

NUKE_MAP = {
    (145, 45, 17, 255): (35, 40, 35, 255),
    (177, 21, 39, 255): (55, 65, 50, 255),
    (219, 47, 26, 255): (255, 205, 30, 255),
    (234, 67, 24, 255): (255, 230, 90, 255),
}


def _recolor(im, color_map):
    im = im.copy()
    pixels = im.load()
    for y in range(im.height):
        for x in range(im.width):
            c = pixels[x, y]
            if c in color_map:
                pixels[x, y] = color_map[c]
    return im


def generate_nuke(source):
    im = _recolor(source, NUKE_MAP)

    # Give the logo almost the whole block (just a thin 2px brick edge top
    # and bottom) - a trefoil needs real pixel budget to read as anything
    # other than a blob, and a bigger, bolder logo also makes Nuke look
    # unmistakably different from Super TNT's slim text band.
    band_top, band_bottom = 2, 14  # rows 2..13 inclusive (12 rows tall)
    band_height = band_bottom - band_top

    scale = 16
    yellow = (255, 205, 0, 255)
    black = (10, 10, 10, 255)
    canvas = Image.new("RGBA", (16 * scale, band_height * scale), LIGHT_BG)
    draw = ImageDraw.Draw(canvas)

    cx, cy = canvas.width / 2, canvas.height / 2
    outer_r = min(canvas.width, canvas.height) / 2 - scale * 0.5

    # Real-world radiation trefoil coloring (black on yellow) reads far
    # better than black-on-gray once downsampled to a handful of pixels -
    # high contrast plus the disc outline plus the center hub are what make
    # it recognizable as THE radiation symbol rather than an abstract blob.
    draw.ellipse((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), fill=yellow, outline=black, width=int(scale * 0.6))

    for start in (-140, -20, 100):
        draw.pieslice((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), start, start + 100, fill=black)

    hub_r = outer_r * 0.22
    draw.ellipse((cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r), fill=yellow, outline=black, width=int(scale * 0.35))

    logo = canvas.resize((16, band_height), Image.LANCZOS)

    # Clear the entire original lettering band first (it spans the full 16px
    # width) so no stray "TNT" pixels survive at the edges of the new logo.
    pixels = im.load()
    for y in range(band_top, band_bottom):
        for x in range(16):
            pixels[x, y] = LIGHT_BG
    im.paste(logo, (0, band_top))

    im.save(BLOCK_DIR / "mega_tnt.png")
    print("Wrote", BLOCK_DIR / "mega_tnt.png", "(nuke logo)")


def generate_nuke_badge_icon():
    """A bold, high-contrast standalone NUKE icon for the HUD command panel -
    distinct from the in-game mega_tnt.png block texture (which must stay a
    tnt.png recolor). Rendered at high resolution with anti-aliasing then
    downsampled, so it stays crisp and punchy even at the tiny badge size the
    command list shows it at, instead of looking like a soft gray blob."""
    super_sample = 8
    size = 40 * super_sample
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    dark_green = (20, 60, 30, 255)
    bright_green = (60, 130, 60, 255)
    yellow = (255, 205, 0, 255)
    black = (12, 12, 12, 255)

    pad = size * 0.04
    draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=size * 0.22, fill=dark_green, outline=bright_green, width=int(size * 0.035))

    cx, cy = size / 2, size / 2
    outer_r = size * 0.36

    draw.ellipse((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), fill=yellow, outline=black, width=int(size * 0.03))
    for start in (-140, -20, 100):
        draw.pieslice((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), start, start + 100, fill=black)

    hub_r = outer_r * 0.22
    draw.ellipse((cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r), fill=yellow, outline=black, width=int(size * 0.018))

    final = canvas.resize((40, 40), Image.LANCZOS)
    out = ITEM_DIR / "nuke_badge_icon.png"
    final.save(out)
    print("Wrote", out)


if __name__ == "__main__":
    source = Image.open(BLOCK_DIR / "tnt.png").convert("RGBA")
    generate_nuke(source)
    generate_nuke_badge_icon()
    print("Done generating Nuke assets.")
