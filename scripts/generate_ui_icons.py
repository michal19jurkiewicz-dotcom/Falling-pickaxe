#!/usr/bin/env python3
"""
Generates bold "sticker" icons (FAST, BIG, resource-boost STAR, and its
sparkle particle) - thick black outlines on saturated fills, drawn at high
resolution and downsampled for crisp anti-aliased edges. This is the same
technique used for the Nuke badge icon (see generate_tnt_variants.py), which
reads far better at small HUD sizes than the earlier hand-pixelled 16x16
grids did.

Run once with: python scripts/generate_ui_icons.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = Path(__file__).parent.parent / "src" / "assets"
TRANSPARENT = (0, 0, 0, 0)
BLACK = (15, 15, 15, 255)

SUPER_SAMPLE = 8
NATIVE_SIZE = 40


def _grid_to_image(grid, palette, pixel_size=1):
    height = len(grid)
    width = len(grid[0])
    img = Image.new("RGBA", (width * pixel_size, height * pixel_size), TRANSPARENT)
    pixels = img.load()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            color = TRANSPARENT if ch == "." else palette[ch]
            for dy in range(pixel_size):
                for dx in range(pixel_size):
                    pixels[x * pixel_size + dx, y * pixel_size + dy] = color
    return img


def _new_canvas():
    return Image.new("RGBA", (NATIVE_SIZE * SUPER_SAMPLE, NATIVE_SIZE * SUPER_SAMPLE), TRANSPARENT)


def _finish(canvas, out_path):
    final = canvas.resize((NATIVE_SIZE, NATIVE_SIZE), Image.LANCZOS)
    final.save(out_path)
    print("Wrote", out_path)


def generate_fast_icon():
    """A bold cartoon lightning bolt - bright yellow fill, thick black outline."""
    canvas = _new_canvas()
    draw = ImageDraw.Draw(canvas)
    s = canvas.width

    points = [
        (0.62 * s, 0.02 * s),
        (0.22 * s, 0.58 * s),
        (0.46 * s, 0.58 * s),
        (0.36 * s, 0.98 * s),
        (0.80 * s, 0.38 * s),
        (0.54 * s, 0.38 * s),
    ]
    draw.polygon(points, fill=(255, 214, 10, 255), outline=BLACK, width=int(s * 0.045))

    out = ASSETS_DIR / "item" / "fast_icon.png"
    _finish(canvas, out)


def generate_big_icon():
    """Four bold double-headed diagonal arrows pointing outward from the
    center - a universal 'enlarge' symbol, built from thick shaft + triangular
    arrowhead polygons for crisp corners instead of hand-placed pixels."""
    canvas = _new_canvas()
    draw = ImageDraw.Draw(canvas)
    s = canvas.width
    cx, cy = s / 2, s / 2

    shaft_half_w = s * 0.05
    head_half_w = s * 0.11
    inner_r = s * 0.10
    shaft_r = s * 0.30
    tip_r = s * 0.44

    fill = (200, 130, 255, 255)

    for angle_deg in (45, 135, 225, 315):
        angle = math.radians(angle_deg)
        dx, dy = math.cos(angle), math.sin(angle)
        px, py = -dy, dx  # perpendicular

        inner = (cx + dx * inner_r, cy + dy * inner_r)
        shaft_end = (cx + dx * shaft_r, cy + dy * shaft_r)
        tip = (cx + dx * tip_r, cy + dy * tip_r)
        base_l = (shaft_end[0] + px * head_half_w, shaft_end[1] + py * head_half_w)
        base_r = (shaft_end[0] - px * head_half_w, shaft_end[1] - py * head_half_w)
        shaft_l1 = (inner[0] + px * shaft_half_w, inner[1] + py * shaft_half_w)
        shaft_r1 = (inner[0] - px * shaft_half_w, inner[1] - py * shaft_half_w)
        shaft_l2 = (shaft_end[0] + px * shaft_half_w, shaft_end[1] + py * shaft_half_w)
        shaft_r2 = (shaft_end[0] - px * shaft_half_w, shaft_end[1] - py * shaft_half_w)

        draw.polygon([shaft_l1, shaft_l2, shaft_r2, shaft_r1], fill=fill)
        draw.polygon([base_l, tip, base_r], fill=fill)

    # Single unified outline pass (per-shape outlines would double-draw at seams)
    mask = canvas.split()[3]
    outline_mask = mask.filter(ImageFilter.MaxFilter(int(s * 0.05) // 2 * 2 + 1))
    outline_layer = Image.new("RGBA", canvas.size, BLACK)
    outline_layer.putalpha(outline_mask)
    combined = Image.alpha_composite(outline_layer, canvas)

    out = ASSETS_DIR / "item" / "big_icon.png"
    _finish(combined, out)


def generate_star_icon():
    """A bold 5-pointed star for the resource-boost power-up badge."""
    canvas = _new_canvas()
    draw = ImageDraw.Draw(canvas)
    s = canvas.width
    cx, cy = s / 2, s / 2
    outer_r = s * 0.46
    inner_r = outer_r * 0.42

    points = []
    for i in range(10):
        angle = math.radians(-90 + i * 36)
        r = outer_r if i % 2 == 0 else inner_r
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    draw.polygon(points, fill=(255, 221, 70, 255), outline=BLACK, width=int(s * 0.035))

    glow_r = inner_r * 0.55
    draw.ellipse((cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r), fill=(255, 250, 220, 200))

    out = ASSETS_DIR / "item" / "star_icon.png"
    _finish(canvas, out)


def generate_sparkle_particle():
    """A small 4-point sparkle used as a particle trail during the resource boost."""
    grid = [
        "....A....",
        "....A....",
        "...ABA...",
        "A..ABA..A",
        ".A.ABA.A.",
        "AAAABAAAA",
        ".A.ABA.A.",
        "A..ABA..A",
        "...ABA...",
        "....A....",
        "....A....",
    ]
    palette = {
        "A": (255, 225, 90, 235),
        "B": (255, 250, 220, 235),
    }
    img = _grid_to_image(grid, palette, pixel_size=1)
    out = ASSETS_DIR / "particle" / "sparkle.png"
    img.save(out)
    print("Wrote", out)


if __name__ == "__main__":
    generate_fast_icon()
    generate_big_icon()
    generate_star_icon()
    generate_sparkle_particle()
    print("Done generating UI icons.")
