#!/usr/bin/env python3
"""Audio for the 15-style catalogue reel.

1. base.wav    — the library track extended by a bar-aligned repeat so it covers the first 13 slots.
2. ending.wav  — a couple of bars before the track's final hit + the hit's decay, so the song ends with the reel.
3. retro-*.wav — code-synthesised beds for the last three slots (HUD pulse / chiptune / synthwave), light drums only.
4. sfx/chip-*.wav — chiptune effects for the pixel sample (jump, bump, coin, fanfare).

Usage: python3 tools/build_audio.py <track.mp3> [--need 137]
Prints the timings the reel needs (base length, ending start) as JSON.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def skill_dir(project: str) -> str:
    """The promo-video skill folder: $PROMO_VIDEO_SKILL, else what setup_project.sh wrote into the project's .promo-env."""
    import shlex
    if os.environ.get("PROMO_VIDEO_SKILL"):
        return os.environ["PROMO_VIDEO_SKILL"]
    env = os.path.join(project, ".promo-env")
    if os.path.exists(env):
        for line in open(env):
            if line.startswith("PROMO_VIDEO_SKILL="):
                return shlex.split(line.split("=", 1)[1])[0]
    raise SystemExit("promo-video skill not found: run <skill>/scripts/setup_project.sh for this project, or export PROMO_VIDEO_SKILL=<skill dir>")


sys.path.insert(0, os.path.join(skill_dir(ROOT), "scripts"))
from pick_music import precise_grid  # noqa: E402

SR = 48000


def ffmpeg(args):
    subprocess.run(["npx", "remotion", "ffmpeg", "-y", "-v", "error", *args], check=True, cwd=ROOT)


def load(path):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "a.wav")
        ffmpeg(["-i", path, "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", out])
        with wave.open(out) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x.reshape(-1, 2)


def save(path, x, peak=0.89):
    x = np.asarray(x, np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    m = np.abs(x).max()
    if m > peak:
        x = x * (peak / m)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def xfade_join(a, b, ms=40):
    n = int(SR * ms / 1000)
    r = np.linspace(0, 1, n)[:, None]
    return np.concatenate([a[:-n], a[-n:] * (1 - r) + b[:n] * r, b[n:]])


# ---------------------------------------------------------------- synth helpers
def t_(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, a=0.005, d=0.2, s=0.0, r=0.05, sus=None):
    """ADSR over n samples (sus = seconds held at level s before release)."""
    na, nd = int(SR * a), int(SR * d)
    nr = int(SR * r)
    ns = max(0, n - na - nd - nr) if sus is None else int(SR * sus)
    e = np.concatenate([np.linspace(0, 1, max(1, na)), np.linspace(1, s, max(1, nd)), np.full(ns, s), np.linspace(s, 0, max(1, nr))])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def square(f, sec, duty=0.5):
    ph = (t_(sec) * f) % 1
    return np.where(ph < duty, 1.0, -1.0)


def tri(f, sec):
    ph = (t_(sec) * f) % 1
    return 4 * np.abs(ph - 0.5) - 1


def saw(f, sec, detune=0.0):
    tt = t_(sec)
    out = 2 * ((tt * f) % 1) - 1
    if detune:
        out = (out + 2 * ((tt * f * (1 + detune)) % 1) - 1 + 2 * ((tt * f * (1 - detune)) % 1) - 1) / 3
    return out


def lp_fast(x, cutoff, B=256):
    """One-pole lowpass y[n] = (1-a)x[n] + a*y[n-1], vectorised per block with the a^-k cumulative-sum trick."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    k = np.arange(B)
    ak, ainv, ak1 = a**k, a ** (-k), a ** (k + 1)
    y = np.empty(len(x))
    prev = 0.0
    for s in range(0, len(x), B):
        seg = x[s : s + B]
        m = len(seg)
        y[s : s + m] = np.cumsum(seg * ainv[:m]) * ak[:m] * (1 - a) + prev * ak1[:m]
        prev = y[s + m - 1]
    return y


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def place(buf, clip, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(clip), len(buf) - i)
    buf[i : i + n] += clip[:n]


def noise(sec, seed):
    return np.random.default_rng(seed).uniform(-1, 1, int(SR * sec))


def kick(vol=0.5):
    sec = 0.28
    tt = t_(sec)
    f = 45 + 90 * np.exp(-tt * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(tt), 0.002, 0.25, 0, 0.02) * vol


def reverb(x, decay=1.2, mix=0.25, seed=3):
    n = int(SR * decay)
    ir = noise(decay, seed) * np.exp(-np.linspace(0, 6, n))
    ir /= np.abs(ir).sum() ** 0.5 * 12
    wet = np.convolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix


# ---------------------------------------------------------------- retro beds
def bed_hud(sec=12.0):
    """Dark HUD pulse: sub pulse in 8ths, filtered saw bed, sparse data blips. No drums."""
    bpm = 110
    beat = 60 / bpm
    L = int(SR * sec)
    out = np.zeros(L)
    prog = [57, 53, 48, 55]  # Am F C G roots
    for k in range(int(sec / beat / 4) + 1):
        root = prog[k % 4] - 24
        for e in range(8):
            at = (k * 4 + e * 0.5) * beat
            n = int(SR * beat * 0.5)
            # lowpassed square: a raw 55 Hz square has edges steep enough to read as clicks
            s = lp_fast(square(hz(root), beat * 0.5, 0.5), 320) * env(n, 0.006, beat * 0.4, 0.2, 0.03)
            place(out, s * 0.26, at)
        pad = saw(hz(prog[k % 4] - 12), beat * 4, 0.004) + saw(hz(prog[k % 4] - 5), beat * 4, 0.004) * 0.7
        place(out, lp_fast(pad, 700) * env(int(SR * beat * 4), 0.3, 1.0, 0.8, 0.5) * 0.12, k * 4 * beat)
    rng = np.random.default_rng(11)
    for i in range(int(sec / beat * 2)):
        if rng.random() < 0.35:
            f = hz(rng.choice([81, 84, 88, 91, 93]))
            place(out, np.sin(2 * np.pi * f * t_(0.06)) * env(int(SR * 0.06), 0.001, 0.05, 0, 0.005) * 0.08, i * beat * 0.5)
    return reverb(out, 1.6, 0.3)


def bed_chip(sec=12.0):
    """Chiptune: 25 % square lead, triangle bass, soft noise hats. Original melody in C major."""
    bpm = 132
    beat = 60 / bpm
    L = int(SR * sec)
    out = np.zeros(L)
    mel = [72, 76, 79, 76, 81, 79, 76, 74, 72, 74, 76, 79, 77, 76, 74, 72, 67, 72, 76, 79, 84, 83, 81, 79, 77, 79, 81, 76, 74, 72, 74, 72]
    bass = [48, 48, 55, 55, 57, 57, 53, 53, 48, 48, 55, 55, 53, 55, 48, 48]
    for i in range(int(sec / (beat / 2))):
        at = i * beat / 2
        m = mel[i % len(mel)]
        n = int(SR * beat / 2)
        place(out, square(hz(m), beat / 2, 0.25) * env(n, 0.002, 0.1, 0.5, 0.02) * 0.1, at)
    for i in range(int(sec / beat)):
        at = i * beat
        n = int(SR * beat)
        place(out, tri(hz(bass[i % len(bass)] - 12), beat) * env(n, 0.002, 0.2, 0.7, 0.03) * 0.22, at)
        h = noise(0.03, i) * env(int(SR * 0.03), 0.001, 0.02, 0, 0.005)
        place(out, h * 0.05, at + beat / 2)
    return out


def bed_synth(sec=12.0):
    """Synthwave: detuned saw pad (Am F C G), 16th saw arpeggio, soft kick, gentle reverb snare on 2 & 4."""
    bpm = 96
    beat = 60 / bpm
    L = int(SR * sec)
    out = np.zeros(L)
    chords = [(57, [0, 3, 7]), (53, [0, 4, 7]), (48, [0, 4, 7]), (55, [0, 4, 7])]
    bar = beat * 4
    for k in range(int(sec / bar) + 1):
        root, iv = chords[k % 4]
        pad = sum(saw(hz(root + i), bar, 0.006) for i in iv) / 3
        place(out, lp_fast(pad, 1500) * env(int(SR * bar), 0.4, 1.2, 0.8, 0.6) * 0.22, k * bar)
        arp = [root - 12 + iv[j % 3] + (12 if j % 6 >= 3 else 0) for j in range(16)]
        for j, m in enumerate(arp):
            n = int(SR * beat / 4)
            place(out, lp_fast(saw(hz(m), beat / 4), 2200) * env(n, 0.002, 0.08, 0.2, 0.02) * 0.12, k * bar + j * beat / 4)
        for b in range(4):
            place(out, kick(0.35), k * bar + b * beat)
            if b % 2 == 1:
                sn = lp_fast(noise(0.25, k * 4 + b), 3500) * env(int(SR * 0.25), 0.002, 0.2, 0, 0.03)
                place(out, sn * 0.12, k * bar + b * beat)
    return reverb(out, 1.4, 0.28)


# ---------------------------------------------------------------- chip sfx
def chip_sfx():
    jump = square(1, 0.14)  # placeholder shape, replaced below
    tt = t_(0.14)
    f = 320 + 700 * (tt / 0.14)
    jump = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(len(tt), 0.002, 0.12, 0, 0.01) * 0.35
    bump = (square(140, 0.09, 0.5) * 0.6 + noise(0.09, 5) * 0.4) * env(int(SR * 0.09), 0.001, 0.08, 0, 0.005) * 0.4
    coin = np.concatenate([square(hz(83), 0.06, 0.5) * env(int(SR * 0.06), 0.002, 0.05, 0.9, 0.004) * 0.3, square(hz(88), 0.34, 0.5) * env(int(SR * 0.34), 0.002, 0.33, 0, 0.005) * 0.3])
    fan = np.zeros(int(SR * 1.2))
    for i, m in enumerate([72, 76, 79, 84]):
        place(fan, square(hz(m), 0.1, 0.25) * env(int(SR * 0.1), 0.002, 0.08, 0.4, 0.01) * 0.28, i * 0.1)
    place(fan, (square(hz(84), 0.7, 0.25) + square(hz(88), 0.7, 0.25) * 0.6) * env(int(SR * 0.7), 0.004, 0.6, 0.2, 0.08) * 0.22, 0.42)
    return {"chip-jump": jump, "chip-bump": bump, "chip-coin": coin, "chip-fanfare": fan}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("track")
    ap.add_argument("--need", type=float, default=137.0, help="seconds the base must cover")
    ap.add_argument("--reel", type=float, default=175.0, help="reel length in seconds")
    ap.add_argument("--ending-bars", type=int, default=2)
    ap.add_argument("--tail", type=float, default=2.35, help="seconds of the final hit's decay to keep")
    a = ap.parse_args()

    song = load(a.track)
    S = len(song) / SR
    bpm, down = precise_grid(a.track, 0.0, min(60.0, S), 117.5, ROOT)
    bar = 4 * 60 / bpm
    bars = int((S - down) / bar)
    rms = [float(np.sqrt((song[int((down + b * bar) * SR) : int((down + (b + 1) * bar) * SR)] ** 2).mean())) for b in range(bars)]
    # the song's final hit: first bar in the second half that drops far below the median level
    med = float(np.median(rms))
    hit_bar = next((b for b in range(bars // 2, bars) if 20 * np.log10(rms[b] + 1e-9) < 20 * np.log10(med + 1e-9) - 12), bars)
    hit_t = down + hit_bar * bar
    # repeat R bars (multiple of 4) so the base is still mid-song at `need`; join where energy matches best
    R = int(np.ceil((a.need - hit_t) / bar / 4)) * 4 if a.need > hit_t else 0
    best = None
    for J in range(R + 4, hit_bar - 4):
        K = J - R
        score = abs(rms[J] - rms[K]) + abs(rms[J - 1] - rms[K - 1]) + 0.2 * abs(rms[J] - med)
        if best is None or score < best[0]:
            best = (score, J, K)
    _, J, K = best if best else (0, hit_bar, hit_bar)
    jt = int((down + J * bar) * SR)
    kt = int((down + K * bar) * SR)
    base = xfade_join(song[:jt], song[kt:]) if R else song
    save(os.path.join(ROOT, "public/music/base.wav"), base, peak=1.0)
    # the ending: `ending-bars` bars of groove, the final hit, and `tail` seconds of its decay
    e0 = hit_t - a.ending_bars * bar
    ending = song[int(e0 * SR) : int((hit_t + a.tail) * SR)]
    save(os.path.join(ROOT, "public/music/ending.wav"), ending, peak=1.0)
    for name, fn in [("retro-hud", bed_hud), ("retro-chip", bed_chip), ("retro-synth", bed_synth)]:
        save(os.path.join(ROOT, f"public/music/{name}.wav"), fn(12.2), peak=0.7)
    for name, x in chip_sfx().items():
        save(os.path.join(ROOT, f"public/sfx/{name}.wav"), x, peak=0.8)
    print(json.dumps({"bpm": bpm, "downbeat": round(down, 3), "bar": round(bar, 4), "repeat_bars": R, "join_bar": J, "back_to_bar": K, "base_len": round(len(base) / SR, 3), "ending_len": round(len(ending) / SR, 3), "ending_starts_in_song": round(e0, 3), "hit_in_song": round(hit_t, 3), "hit_offset_in_ending": round(hit_t - e0, 3)}))


if __name__ == "__main__":
    main()
