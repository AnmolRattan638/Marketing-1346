#!/usr/bin/env python3
"""Synthesizes a LIBRARY of placeholder sound effects (nothing to license): many different sounds per family so a reel never repeats one.

Families (file names kind_N.mp3):  whoosh swipe | pop boop ding sparkle | click tick | riser | impact
agent/sfx_plan.py picks the least-used file of the right family for each cue and never uses one file more than 3 times in a reel.
Replace any file with a real sound of the same name (check its licence); add more by dropping kind_N.mp3 into assets/sfx/.
Needs numpy + scipy + ffmpeg, only to regenerate (the mp3s are committed).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"


def t_(d):
    return np.arange(int(SR * d)) / SR


def noise(d, rng, color="white"):
    n = rng.standard_normal(int(SR * d))
    if color == "pink":
        b, a = signal.butter(1, 1800 / (SR / 2), "low")
        n = signal.lfilter(b, a, n) * 2.2 + n * 0.3
    return n


def band(x, lo, hi):
    hi = min(hi, SR / 2 - 100)
    sos = signal.butter(3, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos")
    return signal.sosfilt(sos, x)


def sweep_noise(d, f0, f1, rng, width=0.6):
    """Noise whose pass band slides from f0 to f1: a moving whoosh."""
    x = noise(d, rng, "pink")
    n = len(x)
    out = np.zeros(n)
    steps = 12
    for k in range(steps):
        a, b = int(n * k / steps), int(n * (k + 1) / steps)
        f = f0 * (f1 / f0) ** ((k + 0.5) / steps)
        seg = band(x, f * (1 - width / 2), f * (1 + width))
        w = np.zeros(n)
        w[max(0, a - n // (steps * 2)): min(n, b + n // (steps * 2))] = 1
        w = np.convolve(w, np.hanning(int(SR * 0.03)), "same") / np.hanning(int(SR * 0.03)).sum()
        out += seg * w
    return out


def env(d, attack, release, curve=1.0):
    t = t_(d)
    a = np.clip(t / max(attack, 1e-3), 0, 1)
    r = np.clip((d - t) / max(release, 1e-3), 0, 1)
    return (a ** curve) * (r ** curve)


def norm(x, peak=0.8):
    return x / (np.abs(x).max() + 1e-9) * peak


def save(name, x):
    x = np.clip(norm(x), -1, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "x.wav"
        import wave
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k", str(OUT / f"{name}.mp3")], check=True)


def main():
    rng = np.random.default_rng(7)
    # whoosh: sliding band-passed noise, different directions, lengths, widths
    for i, (d, f0, f1, wd, att) in enumerate([(0.7, 300, 5000, 0.8, 0.55), (0.6, 5000, 400, 0.7, 0.3), (0.9, 250, 3000, 1.0, 0.65), (0.5, 800, 7000, 0.6, 0.5),
                                              (0.8, 4000, 250, 0.9, 0.25), (0.65, 500, 2500, 1.2, 0.5)], 1):
        x = sweep_noise(d, f0, f1, rng, wd) * env(d, d * att, d * (1 - att), 1.6)
        save(f"whoosh_{i}", x)
    # swipe: short, airy
    for i, (d, lo, hi) in enumerate([(0.28, 1500, 9000), (0.35, 900, 6000), (0.22, 2500, 10000), (0.4, 600, 4500)], 1):
        x = band(noise(d, rng), lo, hi) * env(d, d * 0.35, d * 0.65, 1.4)
        save(f"swipe_{i}", x)
    # pop: falling-pitch blips
    for i, (f0, f1, dec, d) in enumerate([(2700, 500, 22, 0.18), (1800, 380, 30, 0.14), (3400, 700, 26, 0.16), (1400, 300, 18, 0.22), (2200, 600, 40, 0.12), (2900, 420, 16, 0.24)], 1):
        t = t_(d)
        x = np.sin(2 * np.pi * (f1 + (f0 - f1) * np.exp(-45 * t)) * t) * np.exp(-dec * t)
        save(f"pop_{i}", x)
    # boop: rising soft blips
    for i, (f0, f1, d) in enumerate([(320, 760, 0.2), (420, 980, 0.16), (260, 620, 0.26), (520, 1180, 0.14)], 1):
        t = t_(d)
        x = np.sin(2 * np.pi * (f0 + (f1 - f0) * (t / d) ** 2) * t) * env(d, 0.01, d * 0.7, 1.2)
        save(f"boop_{i}", x)
    # ding: bell-like partials
    for i, (f, dec) in enumerate([(880, 7), (1175, 8), (1568, 9), (988, 6)], 1):
        d = 0.7
        t = t_(d)
        x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-dec * m ** 0.5 * t) for m, a in ((1, 1), (2.76, 0.4), (5.4, 0.2)))
        save(f"ding_{i}", x * env(d, 0.003, 0.2))
    # sparkle: quick rising arpeggio of tiny bells
    for i, base in enumerate([2000, 2600, 3200], 1):
        d = 0.55
        t = t_(d)
        x = np.zeros_like(t)
        for k, m in enumerate((1, 1.25, 1.5, 2)):
            s = int(SR * 0.055 * k)
            tt = t[: len(t) - s]
            x[s:] += np.sin(2 * np.pi * base * m * tt) * np.exp(-14 * tt) * 0.6
        save(f"sparkle_{i}", x)
    # click: short filtered noise ticks
    for i, (lo, d) in enumerate([(2500, 0.04), (4000, 0.03), (1800, 0.05), (3200, 0.035), (5000, 0.025), (2200, 0.045)], 1):
        x = band(noise(d, rng), lo, 12000) * np.exp(-t_(d) * (110 / (d / 0.04)))
        save(f"click_{i}", x)
    # tick: tonal woody ticks
    for i, (f, dec) in enumerate([(1200, 90), (1700, 110), (900, 80), (2300, 130)], 1):
        d = 0.07
        t = t_(d)
        save(f"tick_{i}", np.sin(2 * np.pi * f * t) * np.exp(-dec * t))
    # riser: tension builders, 1.4 s
    for i, (kind, f0, f1) in enumerate([("noise", 300, 4000), ("tone", 180, 1400), ("noise", 800, 7000), ("mix", 220, 2200)], 1):
        d = 1.4
        t = t_(d)
        tone = np.sin(2 * np.pi * (f0 + (f1 - f0) * (t / d) ** 2) * t)
        nz = sweep_noise(d, f0, f1, rng, 0.9)
        x = {"noise": nz, "tone": tone, "mix": 0.6 * tone + nz}[kind] * (t / d) ** 2.2 * env(d, 0.05, 0.03)
        save(f"riser_{i}", x)
    # impact: low thuds
    for i, (f, dec, nz_amt) in enumerate([(70, 9, 0.35), (55, 7, 0.2), (95, 12, 0.5)], 1):
        d = 0.5
        t = t_(d)
        x = np.sin(2 * np.pi * (f + 90 * np.exp(-30 * t)) * t) * np.exp(-dec * t) + nz_amt * band(noise(d, rng), 80, 1500) * np.exp(-40 * t)
        save(f"impact_{i}", x)
    print(f"{len(list(OUT.glob('*.mp3')))} sound files in {OUT}")


if __name__ == "__main__":
    sys.exit(main())
