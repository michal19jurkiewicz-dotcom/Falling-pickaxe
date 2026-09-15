#!/usr/bin/env python3
"""
Generates small pixel-art effect sprites (rain drop, snowflake, landing dust
puff) that match the game's existing blocky Minecraft-style art, so weather
and the Pickaxe Rain event have proper sprites instead of plain vector shapes.

Run once with: python scripts/generate_effect_sprites.py
Output goes to src/assets/particle/ (picked up automatically by atlas.py).
"""
from pathlib import Path

from PIL import Image

OUTPUT_DIR = Path(__file__).parent.parent / "src" / "assets" / "particle"

# Pixel-grid colors
TRANSPARENT = (0, 0, 0, 0)


def _grid_to_image(grid, palette, pixel_size=2):
    """Turns a list of strings (one char per pixel) into an RGBA image.
    `palette` maps a character to an (r, g, b, a) tuple; '.' is always transparent.
    """
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


def generate_raindrop():
    grid = [
        "..A.",
        ".AB.",
        ".AB.",
        "AABA",
        ".AB.",
        ".AA.",
        "..A.",
        "....",
    ]
    palette = {
        "A": (120, 170, 235, 235),
        "B": (200, 225, 250, 235),
    }
    img = _grid_to_image(grid, palette, pixel_size=3)
    img.save(OUTPUT_DIR / "rain_drop.png")
    print("Wrote", OUTPUT_DIR / "rain_drop.png")


def generate_snowflake():
    grid = [
        "...A...",
        ".A.A.A.",
        "..AAA..",
        "AAABAAA",
        "..AAA..",
        ".A.A.A.",
        "...A...",
    ]
    palette = {
        "A": (235, 245, 255, 235),
        "B": (255, 255, 255, 255),
    }
    img = _grid_to_image(grid, palette, pixel_size=3)
    img.save(OUTPUT_DIR / "snowflake.png")
    print("Wrote", OUTPUT_DIR / "snowflake.png")


def generate_impact_dust():
    # 4-frame expanding, fading dust puff (for the Pickaxe Rain landing effect)
    frames = [
        [
            "........",
            "........",
            "...AA...",
            "...AA...",
            "........",
            "........",
            "........",
            "........",
        ],
        [
            "........",
            "..A..A..",
            ".A.BB.A.",
            ".A.BB.A.",
            "..A..A..",
            "........",
            "........",
            "........",
        ],
        [
            "..A..A..",
            ".A....A.",
            "A..BB..A",
            "A..BB..A",
            ".A....A.",
            "..A..A..",
            "........",
            "........",
        ],
        [
            ".A....A.",
            "A......A",
            "A..CC..A",
            "A..CC..A",
            "A......A",
            ".A....A.",
            "........",
            "........",
        ],
    ]
    alphas = [235, 200, 140, 70]
    for i, grid in enumerate(frames):
        alpha = alphas[i]
        palette = {
            "A": (200, 190, 175, alpha),
            "B": (225, 215, 200, alpha),
            "C": (210, 200, 185, max(0, alpha - 30)),
        }
        img = _grid_to_image(grid, palette, pixel_size=4)
        img.save(OUTPUT_DIR / f"impact_dust_{i}.png")
        print("Wrote", OUTPUT_DIR / f"impact_dust_{i}.png")


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_raindrop()
    generate_snowflake()
    generate_impact_dust()
    print("Done generating effect sprites.")
