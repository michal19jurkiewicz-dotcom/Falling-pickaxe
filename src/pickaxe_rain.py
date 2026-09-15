import random
import weakref
import math

import pygame
import pymunk

from constants import BLOCK_SIZE, CHUNK_WIDTH

PICKAXE_NAMES = [
    "wooden_pickaxe",
    "stone_pickaxe",
    "iron_pickaxe",
    "golden_pickaxe",
    "diamond_pickaxe",
    "netherite_pickaxe",
]

PICKAXE_DAMAGE = {
    "wooden_pickaxe": 2,
    "stone_pickaxe": 4,
    "iron_pickaxe": 6,
    "golden_pickaxe": 8,
    "diamond_pickaxe": 10,
    "netherite_pickaxe": 12,
}

RAIN_PICKAXE_COLLISION_TYPE = 4
HIT_COOLDOWN_MS = 120

# Spaces that already have the rain-pickaxe/block collision handler registered
_handler_spaces = weakref.WeakSet()


def _on_rain_pickaxe_block_collision(arbiter, space, data):
    rain_pickaxe = arbiter.shapes[0].rain_pickaxe_ref
    block = arbiter.shapes[1].block_ref
    rain_pickaxe.hit_block(block)


class _DustPuff:
    """A short, one-shot dust animation played where a rain pickaxe first lands."""

    def __init__(self, pos, texture_atlas, atlas_items, frame_duration=60):
        self.pos = pygame.Vector2(pos)
        self.frames = [
            texture_atlas.subsurface(pygame.Rect(atlas_items["particle"][f"impact_dust_{i}"]))
            for i in range(4)
            if f"impact_dust_{i}" in atlas_items["particle"]
        ]
        self.frame_duration = frame_duration
        self.elapsed = 0.0
        self.current_frame = 0
        self.finished = not self.frames

    def update(self, dt_ms):
        if self.finished:
            return
        self.elapsed += dt_ms
        if self.elapsed >= self.frame_duration:
            self.elapsed -= self.frame_duration
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.finished = True

    def draw(self, screen, camera):
        if self.finished:
            return
        image = self.frames[self.current_frame]
        rect = image.get_rect(center=(self.pos.x - camera.offset_x, self.pos.y - camera.offset_y))
        screen.blit(image, rect)


class RainPickaxe:
    """A single physical pickaxe dropped by the Pickaxe Rain event. It falls
    and collides like a real object (bounces off blocks/each other/the
    player's pickaxe) and, while it's on the ground, chips away at whatever
    block it's resting against - the same way the player's pickaxe does,
    just automatically and temporarily.
    """

    def __init__(self, space, x, y, name, texture_atlas, atlas_items, sound_manager, on_landed=None):
        self.space = space
        self.sound_manager = sound_manager
        self.name = name
        self.damage = PICKAXE_DAMAGE.get(name, 2)
        self.on_landed = on_landed
        self.landed = False
        self.removed = False
        self._last_hit_time = -HIT_COOLDOWN_MS

        rect = atlas_items["pickaxe"][name]
        self.texture = texture_atlas.subsurface(rect)
        width, height = self.texture.get_size()
        self.radius = max(6, min(width, height) * 0.32)

        mass = 6
        inertia = pymunk.moment_for_circle(mass, 0, self.radius)
        self.body = pymunk.Body(mass, inertia)
        self.body.position = (x, y)
        self.body.angle = math.radians(random.uniform(0, 360))
        self.body.angular_velocity = random.uniform(-4, 4)

        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.elasticity = 0.15
        self.shape.friction = 0.9
        self.shape.collision_type = RAIN_PICKAXE_COLLISION_TYPE
        self.shape.rain_pickaxe_ref = self

        self.space.add(self.body, self.shape)

        if space not in _handler_spaces:
            space.on_collision(RAIN_PICKAXE_COLLISION_TYPE, 2, post_solve=_on_rain_pickaxe_block_collision)
            _handler_spaces.add(space)

    def hit_block(self, block):
        if not self.landed:
            self.landed = True
            if self.on_landed:
                self.on_landed(self.body.position)

        current_time = pygame.time.get_ticks()
        if current_time - self._last_hit_time < HIT_COOLDOWN_MS:
            return
        self._last_hit_time = current_time

        block.first_hit_time = current_time
        block.last_heal_time = current_time
        block.hp -= self.damage

        if block.name in ("grass_block", "dirt"):
            self.sound_manager.play_sound("grass" + str(random.randint(1, 4)))
        else:
            self.sound_manager.play_sound("stone" + str(random.randint(1, 4)))

    def update(self):
        if self.body.velocity.y > 1200:
            self.body.velocity = (self.body.velocity.x, 1200)

    def draw(self, screen, camera):
        rotated_image = pygame.transform.rotate(self.texture, -math.degrees(self.body.angle))
        rect = rotated_image.get_rect(center=(self.body.position.x - camera.offset_x, self.body.position.y - camera.offset_y))
        screen.blit(rotated_image, rect)

    def remove(self):
        if not self.removed:
            self.space.remove(self.body, self.shape)
            self.removed = True


class PickaxeRain:
    """Manages one Pickaxe Rain event: drops a pile of real, physical
    pickaxes above the player that fall, pile up, and help mine nearby
    blocks for the duration of the event.
    """

    def __init__(self, space, spawn_x, spawn_y, texture_atlas, atlas_items, sound_manager, count=14):
        self.space = space
        self.texture_atlas = texture_atlas
        self.atlas_items = atlas_items
        self.dust_puffs = []

        available = [name for name in PICKAXE_NAMES if name in atlas_items.get("pickaxe", {})]
        left = BLOCK_SIZE * 1.2
        right = BLOCK_SIZE * (CHUNK_WIDTH - 1.2)

        self.pickaxes = []
        for i in range(count):
            if not available:
                break
            name = random.choice(available)
            x = random.uniform(left, right)
            y = spawn_y - random.uniform(200, 1600) - i * 60
            self.pickaxes.append(RainPickaxe(
                space, x, y, name, texture_atlas, atlas_items, sound_manager,
                on_landed=self._spawn_dust,
            ))

    def _spawn_dust(self, pos):
        self.dust_puffs.append(_DustPuff(pos, self.texture_atlas, self.atlas_items))

    def update(self, dt_ms):
        for p in self.pickaxes:
            p.update()

        for d in self.dust_puffs:
            d.update(dt_ms)
        self.dust_puffs = [d for d in self.dust_puffs if not d.finished]

    def draw(self, screen, camera):
        for p in self.pickaxes:
            p.draw(screen, camera)
        for d in self.dust_puffs:
            d.draw(screen, camera)

    def end(self):
        """Removes all rain pickaxes from the physics space - called when the event ends."""
        for p in self.pickaxes:
            p.remove()
        self.pickaxes = []
