import pygame
from constants import BLOCK_SIZE, INTERNAL_WIDTH

def render_text_with_outline(text, font, text_color, outline_color, outline_width=2):
    # Render the text in the main color.
    text_surface = font.render(text, True, text_color)
    # Create a new surface larger than the text surface to hold the outline.
    w, h = text_surface.get_size()
    outline_surface = pygame.Surface((w + 2*outline_width, h + 2*outline_width), pygame.SRCALPHA)

    # Blit the text multiple times in the outline color, offset by outline_width in every direction.
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            # Only draw outline if offset is non-zero (avoids overdraw, though it's not a big deal)
            if dx != 0 or dy != 0:
                pos = (dx + outline_width, dy + outline_width)
                outline_surface.blit(font.render(text, True, outline_color), pos)

    # Blit the main text in the center.
    outline_surface.blit(text_surface, (outline_width, outline_width))
    return outline_surface


# Commands shown in the side panel. `icon` is (atlas_category, atlas_name) for a
# reused texture, or None to fall back to a plain color chip (no icon needed).
COMMAND_LIST = [
    ("TNT", ("block", "tnt"), (220, 70, 50)),
    ("SUPER", ("block", "super_tnt"), (255, 175, 25)),
    ("NUKE", ("item", "nuke_badge_icon"), (35, 90, 45)),
    ("RAIN", ("item", "rain_icon"), (230, 90, 60)),
    ("CREEPER", ("item", "creeper_icon"), (94, 153, 72)),
    ("FAST", ("item", "fast_icon"), (250, 210, 60)),
    ("BIG", ("item", "big_icon"), (190, 120, 255)),
    ("WOOD", ("pickaxe", "wooden_pickaxe"), (160, 120, 80)),
    ("STONE", ("pickaxe", "stone_pickaxe"), (150, 150, 150)),
    ("IRON", ("pickaxe", "iron_pickaxe"), (210, 210, 210)),
    ("GOLD", ("pickaxe", "golden_pickaxe"), (250, 210, 60)),
    ("DIAMOND", ("pickaxe", "diamond_pickaxe"), (90, 220, 220)),
    ("NETHERITE", ("pickaxe", "netherite_pickaxe"), (80, 70, 70)),
]

# Point value of each collected resource, used to compute the on-screen score.
# Roughly follows Minecraft's own rarity ordering.
RESOURCE_VALUES = {
    "coal": 1,
    "copper_ingot": 2,
    "iron_ingot": 3,
    "redstone": 4,
    "lapis_lazuli": 4,
    "gold_ingot": 5,
    "diamond": 10,
    "emerald": 15,
}


def _fit_label_surface(text, font, max_width, color=(255, 255, 255)):
    """Renders text and, if it's wider than max_width, uniformly shrinks the
    whole surface to fit - keeps long labels like "NETHERITE" legible on a
    small badge instead of overflowing it."""
    surface = font.render(text, True, color)
    if surface.get_width() <= max_width:
        return surface
    scale = max_width / surface.get_width()
    new_size = (max_width, max(1, int(surface.get_height() * scale)))
    return pygame.transform.smoothscale(surface, new_size)


def _make_circle_badge(diameter, color, icon):
    """A circular, "glossy" mobile-game-style badge: dark outer ring, a
    saturated color disc, a darker inner disc for depth, the icon centered
    on top, and a soft highlight ellipse for the glossy sheen."""
    surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    center = diameter / 2

    pygame.draw.circle(surf, (18, 18, 22, 255), (center, center), center)
    pygame.draw.circle(surf, (*color, 255), (center, center), center - 3)

    inner_r = center - 9
    dark = tuple(max(0, int(c * 0.62)) for c in color)
    pygame.draw.circle(surf, (*dark, 255), (center, center), inner_r)

    if icon is not None:
        icon_max = inner_r * 1.7
        scale = min(icon_max / icon.get_width(), icon_max / icon.get_height())
        scaled_icon = pygame.transform.smoothscale(icon, (max(1, int(icon.get_width() * scale)), max(1, int(icon.get_height() * scale))))
        icon_rect = scaled_icon.get_rect(center=(center, center))
        surf.blit(scaled_icon, icon_rect)

    gloss = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    gloss_rect = pygame.Rect(0, 0, int(diameter * 0.66), int(diameter * 0.38))
    gloss_rect.center = (int(center), int(diameter * 0.3))
    pygame.draw.ellipse(gloss, (255, 255, 255, 90), gloss_rect)
    surf.blit(gloss, (0, 0))

    pygame.draw.circle(surf, (255, 255, 255, 55), (center, center), center - 1.5, width=2)

    return surf


class Hud:
    def __init__(self, texture_atlas, atlas_items, config=None, position=(32, 32)):
        """
        :param texture_atlas: The atlas surface containing the item icons.
        :param atlas_items: A dict with keys under "item" for each ore.
        :param config: The game config, used to toggle HUD panels on/off.
        :param position: Top-left position where the HUD will be drawn.
        """
        self.texture_atlas = texture_atlas
        self.atlas_items = atlas_items
        self.config = config or {}

        # Initialize ore amounts to 0.
        self.amounts = {
            "coal": 0,
            "iron_ingot": 0,
            "copper_ingot": 0,
            "gold_ingot": 0,
            "redstone": 0,
            "lapis_lazuli": 0,
            "diamond": 0,
            "emerald": 0,
        }

        self.position = position
        self.icon_size = (64, 64)  # Size to draw each icon
        self.spacing = 15  # Space between items

        # Fonts
        self.font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 44)
        self.tiny_font = pygame.font.Font(None, 34)

        self.icon_cache = {}
        for ore in self.amounts:
            if ore in self.atlas_items["item"]:
                icon_rect = pygame.Rect(self.atlas_items["item"][ore])
                icon = self.texture_atlas.subsurface(icon_rect)
                icon = pygame.transform.scale(icon, self.icon_size)
                self.icon_cache[ore] = icon

        self.amount_text_cache = {}

        # Command panel: single-column list of circular "glossy" badges,
        # name below each one.
        self.badge_size = 52
        self.command_label_font = pygame.font.Font(None, 26)
        self.command_badge_cache = {}
        for label, source, color in COMMAND_LIST:
            icon = None
            if source is not None:
                category, name = source
                if name in self.atlas_items.get(category, {}):
                    icon_rect = pygame.Rect(self.atlas_items[category][name])
                    icon = self.texture_atlas.subsurface(icon_rect)
            self.command_badge_cache[label] = _make_circle_badge(self.badge_size, color, icon)

        # Small pickaxe icon shown to the left of the DEPTH/WYNIK block
        self.depth_pickaxe_icon = None
        if "diamond_pickaxe" in self.atlas_items.get("pickaxe", {}):
            rect = pygame.Rect(self.atlas_items["pickaxe"]["diamond_pickaxe"])
            self.depth_pickaxe_icon = pygame.transform.scale(self.texture_atlas.subsurface(rect), (56, 56))

        # Engagement banner icons (TNT / Nuke)
        self.tnt_icon = None
        self.nuke_icon = None
        if "tnt" in self.atlas_items.get("block", {}):
            rect = pygame.Rect(self.atlas_items["block"]["tnt"])
            self.tnt_icon = pygame.transform.scale(self.texture_atlas.subsurface(rect), (80, 80))
        if "nuke_badge_icon" in self.atlas_items.get("item", {}):
            rect = pygame.Rect(self.atlas_items["item"]["nuke_badge_icon"])
            self.nuke_icon = pygame.transform.smoothscale(self.texture_atlas.subsurface(rect), (80, 80))

        # Resource-boost ("star") badge icon
        self.star_icon = None
        if "star_icon" in self.atlas_items.get("item", {}):
            rect = pygame.Rect(self.atlas_items["item"]["star_icon"])
            self.star_icon = pygame.transform.scale(self.texture_atlas.subsurface(rect), (48, 48))

    def update_amounts(self, new_amounts):
        """
        Update the ore amounts.
        :param new_amounts: Dict with ore names as keys and integer amounts as values.
        """
        self.amounts.update(new_amounts)

    def get_score(self):
        """Live score computed from collected resources, each weighted by rarity."""
        return sum(self.amounts.get(name, 0) * value for name, value in RESOURCE_VALUES.items())

    def draw(self, screen, pickaxe_y, event_state=None, star_boost_state=None, subscriber_count_text=None):
        """
        Draws the HUD: ore icons/amounts, depth + live score, the next-event /
        active-event countdown, the side command list and the engagement
        banner. The last three are individually toggleable via config.
        subscriber_count_text is an optional "N subscribers" readout, shown
        only when the SUBSCRIBER_COUNT_ENABLED setting is on.
        """
        x, y = self.position

        for ore, amount in self.amounts.items():
            if ore in self.icon_cache:
                screen.blit(self.icon_cache[ore], (x, y))
            else:
                continue

            text_surface = self.amount_text_cache.get(ore)
            if text_surface is None or text_surface[0] != amount:
                text = str(amount)
                text_surface = (amount, render_text_with_outline(text, self.font, (255, 255, 255), (0, 0, 0), outline_width=2))
                self.amount_text_cache[ore] = text_surface

            text_x = x + self.icon_size[0] + self.spacing
            text_y = y + (self.icon_size[1] - text_surface[1].get_height()) // 2 + 3
            screen.blit(text_surface[1], (text_x, text_y))

            y += self.icon_size[1] + self.spacing

        y += self.spacing

        # Depth + live score (from collected resources), with a small pickaxe
        # icon to the left of the whole block for a quicker at-a-glance read.
        depth = -int(pickaxe_y // BLOCK_SIZE)
        depth_surface = render_text_with_outline(f"DEPTH  {depth}m", self.small_font, (255, 255, 255), (0, 0, 0), outline_width=2)
        score = self.get_score()
        score_surface = render_text_with_outline(f"WYNIK  {score}", self.small_font, (255, 220, 100), (0, 0, 0), outline_width=2)

        text_x = x
        if self.depth_pickaxe_icon is not None:
            block_height = depth_surface.get_height() + 6 + score_surface.get_height()
            icon_y = y + (block_height - self.depth_pickaxe_icon.get_height()) // 2
            screen.blit(self.depth_pickaxe_icon, (x, icon_y))
            text_x = x + self.depth_pickaxe_icon.get_width() + 12

        screen.blit(depth_surface, (text_x, y))
        y += depth_surface.get_height() + 6

        screen.blit(score_surface, (text_x, y))
        y += score_surface.get_height() + self.spacing

        if self.config.get("SUBSCRIBER_COUNT_ENABLED", False) and subscriber_count_text:
            subs_surface = render_text_with_outline(subscriber_count_text.upper(), self.tiny_font, (150, 220, 255), (0, 0, 0), outline_width=2)
            screen.blit(subs_surface, (text_x, y))
            y += subs_surface.get_height() + self.spacing

        if self.config.get("HUD_SHOW_NEXT_EVENT", True) and event_state is not None:
            self._draw_event_box(screen, x, y, event_state)

        if self.config.get("HUD_SHOW_ENGAGEMENT_BANNER", True):
            self._draw_engagement_banner(screen)

        if self.config.get("HUD_SHOW_COMMANDS", True):
            self._draw_command_panel(screen)

        if star_boost_state and star_boost_state.get("active"):
            self._draw_star_boost_badge(screen, star_boost_state)

    def _draw_event_box(self, screen, x, y, event_state):
        box_width, box_height = 220, 62
        box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        pygame.draw.rect(box, (10, 10, 10, 150), (0, 0, box_width, box_height), border_radius=12)

        if event_state.get("active"):
            title = str(event_state.get("name") or "Event").upper()
            remaining = max(0.0, event_state.get("time_left", 0.0))
            duration = max(0.0001, event_state.get("duration", 0.0))
            fraction = 1.0 - (remaining / duration)
            title_color = (255, 205, 90)
            bar_color = (255, 150, 60, 230)
        else:
            title = "NEXT EVENT"
            remaining = max(0.0, event_state.get("next_in", 0.0))
            interval = max(0.0001, event_state.get("interval", 0.0))
            fraction = 1.0 - (remaining / interval)
            title_color = (255, 255, 255)
            bar_color = (90, 200, 255, 230)

        title_surface = self.tiny_font.render(title, True, title_color)
        box.blit(title_surface, (12, 6))

        time_surface = self.tiny_font.render(f"{remaining:.1f}s", True, (255, 255, 255))
        box.blit(time_surface, (12, 26))

        bar_x, bar_y, bar_w, bar_h = 12, 50, box_width - 24, 6
        pygame.draw.rect(box, (255, 255, 255, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        fill_w = int(bar_w * max(0.0, min(1.0, fraction)))
        if fill_w > 0:
            pygame.draw.rect(box, bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        screen.blit(box, (x, y))

    def _draw_engagement_banner(self, screen):
        entries = []
        if self.tnt_icon is not None:
            entries.append((self.tnt_icon, "LIKE = TNT RAIN", (255, 90, 70)))
        if self.nuke_icon is not None:
            entries.append((self.nuke_icon, "SUB = NUKE", (255, 210, 60)))

        if not entries:
            return

        y = 40
        for icon, text, color in entries:
            text_surface = render_text_with_outline(text, self.font, color, (0, 0, 0), outline_width=3)
            total_width = icon.get_width() + 16 + text_surface.get_width()
            start_x = (INTERNAL_WIDTH - total_width) // 2

            screen.blit(icon, (start_x, y))
            text_y = y + (icon.get_height() - text_surface.get_height()) // 2
            screen.blit(text_surface, (start_x + icon.get_width() + 16, text_y))

            y += icon.get_height() + 18

    def _draw_command_panel(self, screen):
        """Single-column list of circular command badges with their name
        below each one, sitting on a translucent rounded backing panel so
        they stay legible over any gameplay background (stone/dirt tones
        would otherwise wash out the darker badges)."""
        row_height = self.badge_size + 34
        col_x = INTERNAL_WIDTH - self.badge_size - 40
        y = 40

        panel_pad_x = 24
        panel_pad_top = 18
        panel_pad_bottom = 20
        panel_x = col_x - panel_pad_x
        panel_y = y - panel_pad_top
        panel_width = self.badge_size + panel_pad_x * 2
        panel_height = row_height * (len(COMMAND_LIST) - 1) + self.badge_size + 14 + self.command_label_font.get_height() + panel_pad_top + panel_pad_bottom

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 14, 18, 165), (0, 0, panel_width, panel_height), border_radius=20)
        pygame.draw.rect(panel, (255, 255, 255, 35), (0, 0, panel_width, panel_height), width=2, border_radius=20)
        screen.blit(panel, (panel_x, panel_y))

        for label, _source, _color in COMMAND_LIST:
            badge = self.command_badge_cache.get(label)
            cx = col_x + self.badge_size // 2
            if badge is not None:
                screen.blit(badge, (col_x, y))

            label_surface = render_text_with_outline(label, self.command_label_font, (255, 255, 255), (0, 0, 0), outline_width=2)
            label_rect = label_surface.get_rect(center=(cx, y + self.badge_size + 14))
            screen.blit(label_surface, label_rect)

            y += row_height

    def _draw_star_boost_badge(self, screen, star_boost_state):
        """Small banner shown while the resource-boost power-up is active."""
        multiplier = star_boost_state.get("multiplier", 2)
        remaining = max(0.0, star_boost_state.get("time_left", 0.0))

        text = f"BOOST x{multiplier}  {remaining:.0f}s"
        text_surface = render_text_with_outline(text, self.small_font, (255, 240, 150), (0, 0, 0), outline_width=2)

        icon_size = self.star_icon.get_width() if self.star_icon is not None else 0
        total_width = icon_size + (10 if icon_size else 0) + text_surface.get_width()
        start_x = (INTERNAL_WIDTH - total_width) // 2
        badge_y = 12

        if self.star_icon is not None:
            screen.blit(self.star_icon, (start_x, badge_y))
        screen.blit(text_surface, (start_x + icon_size + (10 if icon_size else 0), badge_y + (icon_size - text_surface.get_height()) // 2 if icon_size else badge_y))
