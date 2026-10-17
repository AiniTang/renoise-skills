#!/usr/bin/env python3
"""Pre-compute per-frame audio features so visuals can react to the music deterministically.

  python3 audio_features.py <project>/public/music/bgm.wav [--fps 30] [--out <project>/public/music/features.json]

Writes {fps, frames, bass[], mid[], high[], level[], onsets[], spec[][]}:
  bass/mid/high/level: 0..1 per video frame (smoothed, normalised to the track's 98th percentile)
  onsets: frame numbers of kick-like hits (bass flux peaks)
  spec:   per frame, 24 log-spaced bands 40 Hz–14 kHz, 0..1 (for spectrum bars / reactive type)
Read it in Remotion with useAudioFeatures() from src/cinematic/AudioReactive.tsx.
"""
import argparse
import json
import os
import wave

import numpy as np


def load(path):
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
    x = np.frombuffer(raw, dtype=dt).astype(np.float32)
    x = x.reshape(-1, ch).mean(axis=1) / float(np.iinfo(dt).max)
    return x, sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out")
    a = ap.parse_args()
    x, sr = load(a.wav)
    hop = sr / a.fps
    frames = int(len(x) / hop)
    win = 2048
    hann = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    bands = {"bass": (30, 160), "mid": (160, 2500), "high": (2500, 12000)}
    idx = {k: (freqs >= lo) & (freqs < hi) for k, (lo, hi) in bands.items()}
    out = {k: np.zeros(frames) for k in bands}
    edges = np.geomspace(40, 14000, 25)
    sidx = []
    for j in range(24):
        m = (freqs >= edges[j]) & (freqs < edges[j + 1])
        if not m.any():
            m = np.zeros_like(freqs, dtype=bool)
            m[np.argmin(np.abs(freqs - np.sqrt(edges[j] * edges[j + 1])))] = True
        sidx.append(m)
    spec = np.zeros((frames, 24))
    level = np.zeros(frames)
    for i in range(frames):
        c = int(i * hop + hop / 2)
        s = max(0, c - win // 2)
        seg = x[s : s + win]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        mag = np.abs(np.fft.rfft(seg * hann))
        for k in bands:
            out[k][i] = np.sqrt(np.mean(mag[idx[k]] ** 2))
        level[i] = np.sqrt(np.mean(seg**2))
        spec[i] = [np.sqrt(np.mean(mag[m] ** 2)) for m in sidx]

    def norm(v, attack=0.6, release=0.18):
        v = v / (np.percentile(v, 98) + 1e-9)
        v = np.clip(v, 0, 1.2)
        sm = np.zeros_like(v)
        for i in range(len(v)):
            p = sm[i - 1] if i else v[0]
            k = attack if v[i] > p else release
            sm[i] = p + (v[i] - p) * k
        return np.clip(sm, 0, 1)

    raw_bass = out["bass"] / (np.percentile(out["bass"], 98) + 1e-9)
    flux = np.maximum(0, np.diff(raw_bass, prepend=raw_bass[0]))
    thr = np.convolve(flux, np.ones(15) / 15, mode="same") * 1.9 + 0.06
    onsets = [int(i) for i in range(1, frames - 1) if flux[i] > thr[i] and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    min_gap = max(3, a.fps // 5)
    kept = []
    for o in onsets:
        if not kept or o - kept[-1] >= min_gap:
            kept.append(o)
    res = {"fps": a.fps, "frames": frames, "onsets": kept, "level": norm(level).round(3).tolist()}
    for k in bands:
        res[k] = norm(out[k]).round(3).tolist()
    sp = np.log1p(spec / (np.percentile(spec, 98, axis=0) + 1e-9) * 4) / np.log1p(4)
    sm = np.zeros_like(sp)
    for i in range(frames):
        p = sm[i - 1] if i else sp[0]
        sm[i] = np.where(sp[i] > p, p + (sp[i] - p) * 0.7, p + (sp[i] - p) * 0.22)
    res["spec"] = np.clip(sm, 0, 1).round(2).tolist()
    dst = a.out or os.path.join(os.path.dirname(a.wav), "features.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(res, f, separators=(",", ":"))
    print(f"wrote {dst}: {frames} frames @ {a.fps}fps, {len(kept)} onsets (first: {kept[:8]})")


if __name__ == "__main__":
    main()
