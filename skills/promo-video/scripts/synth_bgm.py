#!/usr/bin/env python3
"""Synthesize a royalty-free background track with a known BPM.

Usage:
  python3 synth_bgm.py out.wav --seconds 22 --bpm 120 --mood tech

Moods: tech (pulse + kick, default), upbeat (adds arpeggio and claps),
calm (pads and soft plucks, no drums), cinematic (slow swells and low hits),
eastern (pentatonic guzheng-like plucks, warm pads, taiko and woodblock).
--intro-beats sets how many beats play before the drums enter (align it to the logo hit).
Output: 48 kHz, 16-bit stereo WAV, peak-limited. Requires numpy only.
"""
import argparse
import wave

import numpy as np

SR = 48000
PROGRESSIONS = {
    "tech": [(57, "m"), (53, "M"), (48, "M"), (55, "M")],
    "upbeat": [(48, "M"), (55, "M"), (57, "m"), (53, "M")],
    "calm": [(53, "M7"), (57, "m7"), (50, "m7"), (55, "M")],
    "cinematic": [(50, "m"), (46, "M"), (41, "M"), (48, "M")],
    "eastern": [(50, "m7"), (46, "M7"), (48, "M"), (45, "m7")],
}
PENTATONIC = [0, 3, 5, 7, 10]
CHORDS = {"M": [0, 4, 7], "m": [0, 3, 7], "M7": [0, 4, 7, 11], "m7": [0, 3, 7, 10]}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def env(n, attack, release):
    e = np.ones(n)
    a = min(n, int(attack * SR))
    r = min(n - a, int(release * SR))
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[n - r:] = np.linspace(1, 0, r)
    return e


def saw_stack(freq, n, detune=0.12):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0, detune):
        f = freq * 2 ** (d / 12)
        out += 2 * ((t * f) % 1.0) - 1
    return out / 3


def pluck(freq, dur, rng, decay=0.996):
    """Karplus-Strong string, vectorised one period at a time."""
    n = int(dur * SR)
    p = max(2, int(SR / freq))
    buf = lowpass(rng.uniform(-1, 1, p), 3500)
    out = np.empty(n)
    for i in range(0, n, p):
        k = min(p, n - i)
        out[i:i + k] = buf[:k]
        buf = decay * 0.5 * (buf + np.roll(buf, -1))
    return out * env(n, 0.002, 0.08)


def add(buf, start, sig):
    end = min(len(buf), start + len(sig))
    if start < end:
        buf[start:end] += sig[: end - start]


def synth(seconds, bpm, mood, seed, intro_beats=4):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    beat = 60.0 / bpm
    bar = beat * 4
    prog = PROGRESSIONS[mood]
    L = np.zeros(n)
    R = np.zeros(n)
    drums = mood in ("tech", "upbeat")
    bars = int(np.ceil(seconds / bar))

    for b in range(bars):
        root, quality = prog[b % len(prog)]
        start = int(b * bar * SR)
        length = int(bar * SR)
        notes = [root + 12 + i for i in CHORDS[quality]]

        pad = sum(saw_stack(hz(m), length) for m in notes) / len(notes)
        pad = lowpass(pad, {"calm": 600, "eastern": 700}.get(mood, 900))
        pad *= env(length, 0.4 if mood != "cinematic" else 1.2, 0.5) * 0.22
        add(L, start, pad)
        add(R, start, np.roll(pad, 240))

        if mood in ("tech", "upbeat", "cinematic"):
            step = beat / 2 if mood != "cinematic" else beat * 2
            for k in range(int(bar / step)):
                s = int((b * bar + k * step) * SR)
                ln = int(step * SR * 0.9)
                t = np.arange(ln) / SR
                f = hz(root - 12)
                bass = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
                bass *= np.exp(-t * (6 if mood != "cinematic" else 1.5)) * 0.35
                add(L, s, bass)
                add(R, s, bass)

        if mood == "eastern":
            main = intro_beats * beat <= b * bar < seconds - 2 * bar
            rhythm = [1, 0, 1, 1, 0, 1, 0, 1] if main else [1, 0, 0, 1, 0, 0, 1, 0]
            last = 0
            for k, hit in enumerate(rhythm):
                if not hit or rng.random() < 0.15:
                    continue
                deg = int(np.clip(last + rng.integers(-2, 3), 0, 9))
                last = deg
                midi = 62 + 12 * (deg // 5) + PENTATONIC[deg % 5]
                s = int((b * bar + k * beat / 2) * SR)
                pl = pluck(hz(midi), 1.6, rng) * (0.2 if main else 0.16)
                pan = 0.5 + 0.3 * np.sin(k * 1.7 + b)
                add(L, s, pl * (1 - pan))
                add(R, s, pl * pan)
                if main and k in (0, 5):
                    add(L, s + int(beat / 4 * SR), 0.06 * pluck(hz(midi + 12), 1.0, rng))

        if mood in ("upbeat", "calm"):
            step = beat / 4 if mood == "upbeat" else beat
            pattern = notes + [notes[1] + 12]
            for k in range(int(bar / step)):
                s = int((b * bar + k * step) * SR)
                ln = int(0.35 * SR)
                t = np.arange(ln) / SR
                f = hz(pattern[k % len(pattern)] + 12)
                pl = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 9)
                pl *= 0.12 if mood == "upbeat" else 0.16
                pan = 0.5 + 0.35 * np.sin(k)
                add(L, s, pl * (1 - pan))
                add(R, s, pl * pan)

    total_beats = int(seconds / beat)
    for k in range(total_beats):
        s = int(k * beat * SR)
        in_intro = k < intro_beats
        in_outro = k >= total_beats - 4
        if drums and not in_outro:
            if not in_intro:
                ln = int(0.35 * SR)
                t = np.arange(ln) / SR
                sweep = 150 * np.exp(-t * 18) + 45
                kick = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t * 9) * 0.9
                add(L, s, kick)
                add(R, s, kick)
            hs = s + int(beat / 2 * SR)
            ln = int(0.05 * SR)
            hat = rng.standard_normal(ln)
            hat = (hat - lowpass(hat, 6000)) * np.exp(-np.arange(ln) / SR * 80) * 0.18
            add(L, hs, hat * 0.8)
            add(R, hs, hat)
            if mood == "upbeat" and k % 2 == 1 and not in_intro:
                ln = int(0.12 * SR)
                clap = rng.standard_normal(ln) * np.exp(-np.arange(ln) / SR * 30) * 0.25
                clap = clap - lowpass(clap, 1200)
                add(L, s, clap)
                add(R, s, clap)
        if mood == "eastern" and not in_outro:
            if k == intro_beats:
                ln = int(2.0 * SR)
                t = np.arange(ln) / SR
                boom = np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 8)) * t) * np.exp(-t * 1.8) * 0.9
                add(L, s, boom)
                add(R, s, boom)
            elif not in_intro:
                if k % 4 in (0, 2):
                    ln = int(0.6 * SR)
                    t = np.arange(ln) / SR
                    f = 70 * np.exp(-t * 6) + 52
                    taiko = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * (0.65 if k % 4 == 0 else 0.4)
                    taiko += lowpass(rng.standard_normal(ln), 300) * np.exp(-t * 25) * 0.25
                    add(L, s, taiko)
                    add(R, s, taiko)
                ws = s + int(beat / 2 * SR)
                ln = int(0.08 * SR)
                t = np.arange(ln) / SR
                wood = np.sin(2 * np.pi * 1250 * t) * np.exp(-t * 60) * 0.1
                add(L, ws, wood * 0.6)
                add(R, ws, wood)
        if mood == "cinematic" and k % 8 == 0:
            ln = int(1.5 * SR)
            t = np.arange(ln) / SR
            hit = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 2.5) * 0.7
            hit += lowpass(rng.standard_normal(ln), 400) * np.exp(-t * 4) * 0.4
            add(L, s, hit)
            add(R, s, hit)

    mix = np.stack([L, R], axis=1)
    fade = int(1.2 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    rms = np.sqrt(np.mean(mix ** 2)) + 1e-9
    mix *= 10 ** (-17 / 20) / rms
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    peak = np.max(np.abs(mix))
    if peak > 0.89:
        mix *= 0.89 / peak
    return mix


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--bpm", type=float, default=120)
    ap.add_argument("--mood", choices=sorted(PROGRESSIONS), default="tech")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--intro-beats", type=int, default=4)
    a = ap.parse_args()
    mix = synth(a.seconds + 1.0, a.bpm, a.mood, a.seed, a.intro_beats)
    pcm = (mix * 32767).astype("<i2")
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {a.out}: {len(mix) / SR:.2f}s, {a.bpm:g} BPM, mood={a.mood}")


if __name__ == "__main__":
    main()
