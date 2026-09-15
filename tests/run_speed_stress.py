"""Isolation test: vanilla game (no chat control, no YouTube) with ONLY the
random fast/slow event active, compressed to 2-5s intervals. All other random
events disabled via huge intervals. Uncapped clock.

If this crashes with the same shapefree signature, frequent step-speed
toggling is the trigger - no threads or chat pipeline involved.
"""
import os
import sys
import time as _time
import threading
import gc
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))

import pymunk

PYNK = {"overlaps": 0}
_pynk_depth = [0]
_orig_step = pymunk.Space.step
_orig_add = pymunk.Space.add
_orig_remove = pymunk.Space.remove

def _pynk_wrap(fn):
    def wrapper(self, *args, **kwargs):
        _pynk_depth[0] += 1
        try:
            return fn(self, *args, **kwargs)
        finally:
            _pynk_depth[0] -= 1
    return wrapper

pymunk.Space.step = _pynk_wrap(_orig_step)
pymunk.Space.add = _pynk_wrap(_orig_add)
pymunk.Space.remove = _pynk_wrap(_orig_remove)

def _gc_cb(phase, info):
    if phase == "start" and _pynk_depth[0] > 0:
        PYNK["overlaps"] += 1
        print(f"[GC-RACE] collection started during pymunk call (total {PYNK['overlaps']})", flush=True)
gc.callbacks.append(_gc_cb)

import pygame

class _UncappedClock:
    def __init__(self):
        self._last = _time.perf_counter()
        self._last_dt = 16

    def tick(self, framerate=0):
        now = _time.perf_counter()
        dt_ms = max(1, int((now - self._last) * 1000))
        self._last = now
        self._last_dt = dt_ms
        return dt_ms

    def get_time(self):
        return self._last_dt

    def get_fps(self):
        return 1000.0 / max(1, self._last_dt)

pygame.time.Clock = _UncappedClock

import config as config_mod
config_mod.config["CHAT_CONTROL"] = False
if os.environ.get("REPRO_TNT") == "1":
    config_mod.config["TNT_SPAWN_INTERVAL_SECONDS_MIN"] = 2
    config_mod.config["TNT_SPAWN_INTERVAL_SECONDS_MAX"] = 5
else:
    config_mod.config["TNT_SPAWN_INTERVAL_SECONDS_MIN"] = 999999
    config_mod.config["TNT_SPAWN_INTERVAL_SECONDS_MAX"] = 999999
config_mod.config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"] = 999999
config_mod.config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"] = 999999
config_mod.config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"] = 999999
config_mod.config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"] = 999999
config_mod.config["FAST_SLOW_INTERVAL_SECONDS_MIN"] = 2
config_mod.config["FAST_SLOW_INTERVAL_SECONDS_MAX"] = 5
config_mod.config["FAST_SLOW_DURATION_SECONDS"] = 5

# Force Fast-only or Slow-only toggling (REPRO_FORCE_SPEED=fast|slow)
_FORCE = os.environ.get("REPRO_FORCE_SPEED", "").lower()
if _FORCE in ("fast", "slow"):
    import random as _random
    _orig_choice = _random.choice
    def _forced_choice(seq):
        if tuple(seq) == ("Fast", "Slow"):
            return _FORCE.capitalize()
        return _orig_choice(seq)
    _random.choice = _forced_choice

import pickaxe as pickaxe_mod

_orig_update = pickaxe_mod.Pickaxe.update
_state = {"quit_posted": False}
QUIT_Y = 265 * 120

def _patched_update(self, current_time=None):
    if not _state["quit_posted"] and self.body.position.y > QUIT_Y:
        _state["quit_posted"] = True
        print("[repro] passed crash zone without crash, posting QUIT", flush=True)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    y = -int(self.body.position.y // 120)
    if 195 <= -y <= 265 and pygame.time.get_ticks() % 500 < 17:
        print(f"[repro] Y: {y}", flush=True)
    return _orig_update(self, current_time)

pickaxe_mod.Pickaxe.update = _patched_update

import main  # noqa: F401
