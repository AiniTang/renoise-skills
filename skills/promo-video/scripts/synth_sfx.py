#!/usr/bin/env python3
"""Synthesize the noise-based effects of the SFX kit.

Usage: python3 synth_sfx.py <out-dir>
Writes 48 kHz 16-bit stereo WAVs:
  whoosh.wav    fast camera move / transition
  impact.wav    hit for a big reveal or final card
  riser.wav     1.2 s tension build before a reveal
Only noise-based sounds are synthesized; keys, clicks and UI sounds are real
recordings in assets/sfx (synthesized ones sound fake).
Requires numpy only.
"""
import os
import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(3)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def swept(noise, start_hz, end_hz, filt):
    block = 1200
    out = [filt(noise[i : i + block], start_hz + (end_hz - start_hz) * i / len(noise)) for i in range(0, len(noise), block)]
    return np.concatenate(out)[: len(noise)]


def write(path, mono):
    peak = np.max(np.abs(mono)) or 1
    mono = mono * (0.9 / peak)
    pcm = (np.stack([mono, mono], axis=1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def whoosh():
    tt = t(0.55)
    env = np.sin(np.pi * tt / 0.55) ** 2
    return swept(rng.standard_normal(len(tt)), 400, 5400, lowpass) * env


def impact():
    tt = t(1.4)
    boom = np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-tt * 12)) / SR) * np.exp(-tt * 3.2)
    return boom + lowpass(rng.standard_normal(len(tt)), 3000) * np.exp(-tt * 18) * 0.5


def riser():
    tt = t(1.2)
    rise = swept(rng.standard_normal(len(tt)), 200, 6200, highpass) * 0.5
    tone = np.sin(2 * np.pi * np.cumsum(200 + 600 * (tt / 1.2) ** 2) / SR) * 0.25
    return (rise + tone) * (tt / 1.2) ** 2


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx"
    os.makedirs(out, exist_ok=True)
    for name, fn in (("whoosh", whoosh), ("impact", impact), ("riser", riser)):
        write(os.path.join(out, f"{name}.wav"), fn())
    print(f"wrote SFX kit to {out}")


if __name__ == "__main__":
    main()
