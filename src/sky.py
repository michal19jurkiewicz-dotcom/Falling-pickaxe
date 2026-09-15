import math
import random

import pygame

from constants import INTERNAL_HEIGHT, INTERNAL_WIDTH

# (phase 0..1, sky RGB color, night amount 0..1) keyframes for a full day/night cycle.
# phase 0 = midnight, 0.5 = midday.
_SKY_KEYFRAMES = [
    (0.00, (10, 12, 40), 1.0),
    (0.20, (10, 12, 40), 1.0),
    (0.28, (255, 145, 90), 0.35),
    (0.35, (135, 206, 235), 0.0),
    (0.50, (135, 206, 235), 0.0),
    (0.65, (135, 206, 235), 0.0),
    (0.72, (255, 130, 80), 0.35),
    (0.80, (30, 20, 60), 0.85),
    (1.00, (10, 12, 40), 1.0),
]

WEATHER_CLEAR = "clear"
WEATHER_RAIN = "rain"
WEATHER_SNOW = "snow"
WEATHER_STORM = "storm"


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return tuple(int(_lerp(c1[i], c2[i], t)) for i in range(3))


def _sky_state_for_phase(phase):
    phase = phase % 1.0
    for i in range(len(_SKY_KEYFRAMES) - 1):
        t0, c0, n0 = _SKY_KEYFRAMES[i]
        t1, c1, n1 = _SKY_KEYFRAMES[i + 1]
        if t0 <= phase <= t1:
            local_t = 0.0 if t1 == t0 else (phase - t0) / (t1 - t0)
            return _lerp_color(c0, c1, local_t), _lerp(n0, n1, local_t)
    return _SKY_KEYFRAMES[-1][1], _SKY_KEYFRAMES[-1][2]


class Cloud:
    """A flat, blocky Minecraft-style cloud drawn from plain rectangles - no image asset needed."""

    _SHAPE = [
        (20, 15, 120, 20),
        (0, 25, 160, 15),
        (35, 0, 70, 20),
        (10, 35, 100, 15),
    ]

    def __init__(self, x, y, scale, speed):
        self.x = x
        self.y = y
        self.scale = scale
        self.speed = speed  # pixels per second, sign gives direction

    def update(self, dt_seconds):
        self.x += self.speed * dt_seconds
        width = 160 * self.scale
        if self.speed >= 0 and self.x > INTERNAL_WIDTH + width:
            self.x = -width
        elif self.speed < 0 and self.x < -width:
            self.x = INTERNAL_WIDTH + width

    def draw(self, surface, night_amount):
        shade = int(_lerp(255, 120, night_amount * 0.7))
        color = (shade, shade, shade, 235)
        width, height = int(160 * self.scale), int(50 * self.scale)
        cloud_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for rx, ry, rw, rh in self._SHAPE:
            pygame.draw.rect(
                cloud_surface, color,
                (rx * self.scale, ry * self.scale, rw * self.scale, rh * self.scale)
            )
        surface.blit(cloud_surface, (self.x, self.y))


class _Raindrop:
    __slots__ = ("x", "y", "speed", "sprite")

    def __init__(self, base_sprite):
        self.x = random.uniform(0, INTERNAL_WIDTH)
        self.y = random.uniform(-INTERNAL_HEIGHT, INTERNAL_HEIGHT)
        self.speed = random.uniform(500, 750)
        self.sprite = pygame.transform.scale_by(base_sprite, random.uniform(0.9, 1.7))
        self.sprite.set_alpha(150)  # subtle, background-layer feel rather than a foreground wall of rain

    def update(self, dt_seconds):
        self.y += self.speed * dt_seconds
        if self.y > INTERNAL_HEIGHT:
            self.y = random.uniform(-80, 0)
            self.x = random.uniform(0, INTERNAL_WIDTH)

    def draw(self, surface):
        rect = self.sprite.get_rect(center=(self.x, self.y))
        surface.blit(self.sprite, rect)


class _Snowflake:
    __slots__ = ("x", "y", "speed", "drift", "drift_phase", "sprite")

    def __init__(self, base_sprite):
        self.x = random.uniform(0, INTERNAL_WIDTH)
        self.y = random.uniform(-INTERNAL_HEIGHT, INTERNAL_HEIGHT)
        self.speed = random.uniform(80, 180)
        self.drift = random.uniform(10, 40)
        self.drift_phase = random.uniform(0, math.tau)
        self.sprite = pygame.transform.scale_by(base_sprite, random.uniform(0.7, 1.5))
        self.sprite.set_alpha(190)

    def update(self, dt_seconds):
        self.y += self.speed * dt_seconds
        self.drift_phase += dt_seconds
        if self.y > INTERNAL_HEIGHT:
            self.y = random.uniform(-80, 0)
            self.x = random.uniform(0, INTERNAL_WIDTH)

    def draw(self, surface):
        x = self.x + math.sin(self.drift_phase) * self.drift
        rect = self.sprite.get_rect(center=(int(x), int(self.y)))
        surface.blit(self.sprite, rect)


class Sky:
    """Owns the day/night cycle, background clouds, and weather (rain/snow/storm)
    including the matching ambient sounds. Clouds/sky/lightning are drawn
    procedurally; rain/snow use small generated pixel-art sprites (see
    scripts/generate_effect_sprites.py) and the ambient loops are generated
    WAV files (see scripts/generate_weather_sounds.py) - no downloaded art or
    audio needed. Every piece can be disabled independently through config.
    """

    def __init__(self, config, sound_manager, assets_dir):
        self.day_night_enabled = bool(config.get("DAY_NIGHT_CYCLE_ENABLED", True))
        self.weather_enabled = bool(config.get("WEATHER_ENABLED", True))
        self.clouds_enabled = bool(config.get("CLOUDS_ENABLED", True))

        self.cycle_seconds = max(30, config.get("DAY_NIGHT_CYCLE_SECONDS", 300))
        self.weather_min_seconds = max(10, config.get("WEATHER_CHANGE_INTERVAL_SECONDS_MIN", 60))
        self.weather_max_seconds = max(self.weather_min_seconds, config.get("WEATHER_CHANGE_INTERVAL_SECONDS_MAX", 180))

        self.sound_manager = sound_manager
        self.elapsed = 0.0

        self.clouds = [
            Cloud(
                x=random.uniform(0, INTERNAL_WIDTH),
                y=random.uniform(40, 420),
                scale=random.uniform(0.7, 1.7),
                speed=random.choice([-1, 1]) * random.uniform(12, 35),
            )
            for _ in range(11)
        ]

        self._star_positions = [
            (random.uniform(0, INTERNAL_WIDTH), random.uniform(0, INTERNAL_HEIGHT * 0.5))
            for _ in range(50)
        ]

        # Weather particle sprites are loaded directly (not through the block
        # texture atlas) so they keep their own small scale instead of being
        # blown up by BLOCK_SCALE_FACTOR like block/item/pickaxe textures.
        raindrop_sprite = pygame.image.load(assets_dir / "particle" / "rain_drop.png").convert_alpha()
        snowflake_sprite = pygame.image.load(assets_dir / "particle" / "snowflake.png").convert_alpha()

        self.weather = WEATHER_CLEAR
        self.weather_timer = random.uniform(self.weather_min_seconds, self.weather_max_seconds)
        self._raindrops = [_Raindrop(raindrop_sprite) for _ in range(60)]
        self._snowflakes = [_Snowflake(snowflake_sprite) for _ in range(60)]

        self.lightning_flash = 0.0
        self._lightning_timer = random.uniform(4, 9)

        self._current_ambient_sound = None

    def _pick_new_weather(self):
        if not self.weather_enabled:
            return
        self.weather = random.choices(
            [WEATHER_CLEAR, WEATHER_RAIN, WEATHER_SNOW, WEATHER_STORM],
            weights=[45, 25, 20, 10],
        )[0]
        print(f"[weather] Changing weather to: {self.weather}")

    def day_night_phase(self):
        if not self.day_night_enabled:
            return 0.5  # frozen at midday
        return (self.elapsed % self.cycle_seconds) / self.cycle_seconds

    def update(self, dt_ms):
        dt = dt_ms / 1000.0
        self.elapsed += dt

        if self.clouds_enabled:
            for cloud in self.clouds:
                cloud.update(dt)

        if self.weather_enabled:
            self.weather_timer -= dt
            if self.weather_timer <= 0:
                self._pick_new_weather()
                self.weather_timer = random.uniform(self.weather_min_seconds, self.weather_max_seconds)

            if self.weather in (WEATHER_RAIN, WEATHER_STORM):
                for drop in self._raindrops:
                    drop.update(dt)
            elif self.weather == WEATHER_SNOW:
                for flake in self._snowflakes:
                    flake.update(dt)

            if self.weather == WEATHER_STORM:
                self._lightning_timer -= dt
                if self._lightning_timer <= 0:
                    self.lightning_flash = 1.0
                    self._lightning_timer = random.uniform(4, 10)
                    self.sound_manager.play_sound("weather_thunder")

            if self.lightning_flash > 0:
                self.lightning_flash = max(0.0, self.lightning_flash - dt * 2.5)
        else:
            self.weather = WEATHER_CLEAR

        self._sync_ambient_sound()

    def _sync_ambient_sound(self):
        if not self.weather_enabled:
            desired = None
        elif self.weather == WEATHER_RAIN:
            desired = "weather_rain"
        elif self.weather == WEATHER_STORM:
            desired = "weather_storm"
        elif self.weather == WEATHER_SNOW:
            desired = "weather_wind"
        else:
            desired = None

        if desired != self._current_ambient_sound:
            if self._current_ambient_sound is not None:
                self.sound_manager.stop_sound(self._current_ambient_sound)
            if desired is not None:
                self.sound_manager.play_sound(desired, loop=True)
            self._current_ambient_sound = desired

    def draw_background(self, surface):
        """Sky color, stars and clouds - draw this first, before blocks/pickaxe."""
        phase = self.day_night_phase()
        color, night_amount = _sky_state_for_phase(phase)
        surface.fill(color)

        if self.day_night_enabled and night_amount > 0.05:
            star_alpha = int(255 * night_amount)
            star_surface = pygame.Surface((3, 3), pygame.SRCALPHA)
            star_surface.fill((255, 255, 255, star_alpha))
            for sx, sy in self._star_positions:
                surface.blit(star_surface, (sx, sy))

        if self.clouds_enabled:
            for cloud in self.clouds:
                cloud.draw(surface, night_amount)

        # Precipitation is drawn here, with the sky and clouds, so it reads as
        # background weather rather than a foreground overlay sitting on top
        # of the mine shaft.
        if self.weather_enabled:
            if self.weather in (WEATHER_RAIN, WEATHER_STORM):
                for drop in self._raindrops:
                    drop.draw(surface)
            elif self.weather == WEATHER_SNOW:
                for flake in self._snowflakes:
                    flake.draw(surface)

    def draw_foreground(self, surface):
        """Lightning flash only - draw this last, over gameplay."""
        if self.weather_enabled and self.lightning_flash > 0:
            flash_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, int(140 * self.lightning_flash)))
            surface.blit(flash_surface, (0, 0))
