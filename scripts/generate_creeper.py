#!/usr/bin/env python3
"""
Derives the HUD command-panel Creeper icon from the hand-drawn Creeper block
sprite (src/assets/block/creeper.png) - keeps the badge icon visually
identical to the actual falling entity. Re-run this after updating the
hand-drawn sprite.
"""
from pathlib import Path

from PIL import Image

BLOCK_DIR = Path(__file__).parent.parent / "src" / "assets" / "block"
ITEM_DIR = Path(__file__).parent.parent / "src" / "assets" / "item"


def generate_creeper_icon():
    source = Image.open(BLOCK_DIR / "creeper.png").convert("RGBA")
    icon = source.resize((source.width * 2, source.height * 2), Image.NEAREST)
    out = ITEM_DIR / "creeper_icon.png"
    icon.save(out)
    print("Wrote", out)


if __name__ == "__main__":
    generate_creeper_icon()
