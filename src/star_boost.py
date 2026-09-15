import random

import pygame

SPARKLES_PER_SECOND = 12


class _Sparkle:
    def __init__(self, x, y, texture):
        self.x = x
        self.y = y
        self.texture = pygame.transform.scale_by(texture, random.uniform(0.6, 1.3))
        self.vx = random.uniform(-40, 40)
        self.vy = random.uniform(-90, -30)
        self.life = random.uniform(0.5, 0.9)
        self.age = 0.0

    def update(self, dt_seconds):
        self.age += dt_seconds
        self.x += self.vx * dt_seconds
        self.y += self.vy * dt_seconds
        self.vy += 60 * dt_seconds  # gentle upward drift that settles into a fall

    @property
    def finished(self):
        return self.age >= self.life

    def draw(self, screen, camera):
        alpha = max(0, int(255 * (1 - self.age / self.life)))
        image = self.texture.copy()
        image.set_alpha(alpha)
        rect = image.get_rect(center=(self.x - camera.offset_x, self.y - camera.offset_y))
        screen.blit(image, rect)


class StarBoost:
    """The 'resource boost' power-up: while active, resources gained from
    mining are multiplied (see Block.update's resource_multiplier) and a
    sparkle trail follows the pickaxe to sell the effect on stream.
    """

    def __init__(self, texture_atlas, atlas_items, multiplier=2):
        self.multiplier = multiplier
        self.particles = []
        self._spawn_accumulator = 0.0

        self.sparkle_texture = None
        if "sparkle" in atlas_items.get("particle", {}):
            rect = pygame.Rect(atlas_items["particle"]["sparkle"])
            self.sparkle_texture = texture_atlas.subsurface(rect)

    def update(self, dt_ms, pickaxe_x, pickaxe_y):
        dt = dt_ms / 1000.0

        if self.sparkle_texture is not None:
            self._spawn_accumulator += dt
            spawn_interval = 1.0 / SPARKLES_PER_SECOND
            while self._spawn_accumulator >= spawn_interval:
                self._spawn_accumulator -= spawn_interval
                x = pickaxe_x + random.uniform(-70, 70)
                y = pickaxe_y + random.uniform(-70, 70)
                self.particles.append(_Sparkle(x, y, self.sparkle_texture))

        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if not p.finished]

    def draw(self, screen, camera):
        for particle in self.particles:
            particle.draw(screen, camera)
