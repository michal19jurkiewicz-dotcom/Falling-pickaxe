#!/usr/bin/env python3
"""
Generates the ambient weather sound loops (rain, wind, storm, thunder) as
plain synthesized WAV files, so the game has weather audio without needing
any downloaded/recorded sound assets.

These are built as a soft base hiss plus individual randomized "droplet"
transients, which reads much closer to Minecraft's light pitter-patter rain
ambience than a flat wall of filtered noise does.

Run once with: python scripts/generate_weather_sounds.py
Output goes to src/assets/sounds/.
"""
import math
import random
import wave
from array import array
from pathlib import Path

SAMPLE_RATE = 44100
OUTPUT_DIR = Path(__file__).parent.parent / "src" / "assets" / "sounds"


def _low_pass(samples, alpha):
    """Simple one-pole low-pass filter: softens harsh white noise into a duller hiss."""
    out = array("d", [0.0]) * len(samples)
    prev = 0.0
    for i, s in enumerate(samples):
        prev = alpha * s + (1 - alpha) * prev
        out[i] = prev
    return out


def _white_noise(num_samples, seed=None):
    rng = random.Random(seed)
    return array("d", [rng.uniform(-1.0, 1.0) for _ in range(num_samples)])


def _crossfade_loop(samples, fade_samples):
    """Blend the tail into the head so the clip loops without an audible click."""
    n = len(samples)
    fade_samples = min(fade_samples, n // 4)
    for i in range(fade_samples):
        t = i / fade_samples
        head = samples[i]
        tail = samples[n - fade_samples + i]
        blended = tail * (1 - t) + head * t
        samples[i] = blended
        samples[n - fade_samples + i] = blended
    return samples


def _normalize(samples, peak=0.9):
    max_val = max(abs(s) for s in samples) or 1.0
    scale = peak / max_val
    return array("d", [s * scale for s in samples])


def _write_wav(path, samples, volume=1.0):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pcm = array("h", [int(max(-1.0, min(1.0, s * volume)) * 32767) for s in samples])
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())
    print(f"Wrote {path}")


def _add_droplets(base, duration_seconds, drops_per_second, seed, drop_gain=0.5, drop_len_ms=(4, 12)):
    """Overlays short percussive 'droplet' blips at randomized times - this is
    what makes it read as rain/hail patter instead of a flat hiss."""
    rng = random.Random(seed)
    n = len(base)
    out = array("d", base)
    num_drops = int(duration_seconds * drops_per_second)
    for _ in range(num_drops):
        start = rng.randrange(0, n)
        length = int(SAMPLE_RATE * rng.uniform(*drop_len_ms) / 1000.0)
        gain = drop_gain * rng.uniform(0.5, 1.0)
        for i in range(length):
            idx = start + i
            if idx >= n:
                break
            envelope = math.exp(-i / max(1, length) * 6)
            out[idx] += (rng.uniform(-1.0, 1.0)) * gain * envelope
    return out


def generate_rain(duration_seconds=6.0):
    n = int(SAMPLE_RATE * duration_seconds)
    hiss = _low_pass(_white_noise(n, seed=1), alpha=0.15)
    hiss = _normalize(hiss, peak=0.12)  # quiet base, well below the droplets
    rain = _add_droplets(hiss, duration_seconds, drops_per_second=45, seed=11, drop_gain=0.55, drop_len_ms=(3, 9))
    rain = _crossfade_loop(rain, fade_samples=int(SAMPLE_RATE * 0.3))
    rain = _normalize(rain, peak=0.55)
    _write_wav(OUTPUT_DIR / "weather_rain.wav", rain, volume=0.5)


def generate_wind(duration_seconds=6.0):
    n = int(SAMPLE_RATE * duration_seconds)
    noise = _white_noise(n, seed=2)
    wind = _low_pass(noise, alpha=0.05)  # heavy filtering -> soft breeze, no droplets
    for i in range(n):
        gust = 0.6 + 0.4 * math.sin(2 * math.pi * i / SAMPLE_RATE * 0.08)
        wind[i] *= gust
    wind = _crossfade_loop(wind, fade_samples=int(SAMPLE_RATE * 0.5))
    wind = _normalize(wind, peak=0.4)
    _write_wav(OUTPUT_DIR / "weather_wind.wav", wind, volume=0.3)


def generate_storm(duration_seconds=6.0):
    n = int(SAMPLE_RATE * duration_seconds)
    hiss = _low_pass(_white_noise(n, seed=3), alpha=0.2)
    hiss = _normalize(hiss, peak=0.15)
    storm = _add_droplets(hiss, duration_seconds, drops_per_second=90, seed=31, drop_gain=0.6, drop_len_ms=(3, 10))

    for i in range(n):
        t = i / SAMPLE_RATE
        storm[i] += 0.18 * math.sin(2 * math.pi * 45 * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.1 * t))

    storm = _crossfade_loop(storm, fade_samples=int(SAMPLE_RATE * 0.3))
    storm = _normalize(storm, peak=0.7)
    _write_wav(OUTPUT_DIR / "weather_storm.wav", storm, volume=0.5)


def generate_thunder(duration_seconds=1.6):
    n = int(SAMPLE_RATE * duration_seconds)
    noise = _white_noise(n, seed=4)
    crack = _low_pass(noise, alpha=0.55)

    out = array("d", [0.0]) * n
    for i in range(n):
        t = i / SAMPLE_RATE
        envelope = math.exp(-t * 3.0)
        rumble = 0.55 * math.sin(2 * math.pi * 50 * t) + 0.25 * math.sin(2 * math.pi * 33 * t)
        crack_env = math.exp(-t * 40) if t < 0.15 else 0.0
        out[i] = crack[i] * (crack_env * 0.9 + envelope * 0.2) + rumble * envelope

    out = _normalize(out, peak=0.95)
    _write_wav(OUTPUT_DIR / "weather_thunder.wav", out, volume=0.8)


if __name__ == "__main__":
    generate_rain()
    generate_wind()
    generate_storm()
    generate_thunder()
    print("Done generating weather sounds.")
