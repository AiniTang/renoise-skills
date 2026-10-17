#!/usr/bin/env python3
"""Pick a licensed track from assets/music, cut it to the film length and land its energy arrival on a chosen second.

Usage:
  python3 pick_music.py --list [--mood tech-drive] [--style 暗场科技]
  python3 pick_music.py <project>/public/music/bgm.wav --mood tech-drive --seconds 45 --hit-at 4
  python3 pick_music.py <project>/public/music/bgm.wav --track mixkit-587-discover.mp3 --seconds 30 --hit-at 6

Choosing: tracks matching --mood/--style, long enough for start + seconds, least recently used first
(usage is logged in ~/.cache/promo-video/music-usage.json so consecutive films don't reuse the same song).
--hit-at: the second in the film where the music's main section should land (logo reveal, first drop).
Writes bgm.wav (48 kHz stereo, fades applied) and credit.txt beside it, and prints the BPM for the timeline.
ffmpeg: system ffmpeg if present, else `npx remotion ffmpeg` run from the project directory.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "music")
CATALOG_FILE = os.path.join(LIB, "catalog.json")
USAGE = os.path.expanduser("~/.cache/promo-video/music-usage.json")
# The tracks themselves are not shipped (Mixkit's licence forbids redistributing them standalone): each is fetched once from
# its catalog "url" and checked against its "sha256".
CACHE = os.path.expanduser("~/.cache/promo-video/music")


def fetch(track):
    """Path to the track's audio, downloading it into the cache on first use."""
    import hashlib
    import urllib.request

    path = os.path.join(CACHE, track["file"])
    if os.path.exists(path):
        return path
    os.makedirs(CACHE, exist_ok=True)
    print(f"downloading {track['title']} from {track['url']}", file=sys.stderr)
    data = urllib.request.urlopen(track["url"], timeout=60).read()
    if hashlib.sha256(data).hexdigest() != track["sha256"]:
        raise SystemExit(f"{track['file']}: downloaded file does not match the catalog sha256; refusing it")
    with open(path + ".part", "wb") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return path


def ffmpeg(args, cwd):
    exe = shutil.which("ffmpeg")
    cmd = [exe] if exe else ["npx", "remotion", "ffmpeg"]
    subprocess.run([*cmd, "-y", "-v", "error", *args], check=True, cwd=None if exe else cwd)


def project_root(path):
    d = os.path.dirname(os.path.abspath(path))
    while d != "/":
        if os.path.exists(os.path.join(d, "package.json")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


def precise_grid(src, start, dur, bpm_hint, root, fixed=False):
    """Refine tempo to 0.05 BPM and find the first downbeat by scoring a cosine beat comb against kick-band (<250 Hz) flux.
    Full-band flux locks onto hi-hats and off-beats and drifts by ~1 BPM."""
    with tempfile.TemporaryDirectory() as tmp:
        win = os.path.join(tmp, "grid.wav")
        ffmpeg(["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src, "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", win], root)
        with wave.open(win) as w:
            m = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    hop, size = 256, 1024
    n = (len(m) - size) // hop
    frames = np.lib.stride_tricks.as_strided(m, (n, size), (m.strides[0] * hop, m.strides[0]))
    spec = np.log1p(np.abs(np.fft.rfft(frames * np.hanning(size), axis=1)))[:, :12]
    flux = np.maximum(0, np.diff(spec.sum(axis=1)))
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    t = np.arange(len(flux)) / (22050 / hop)
    best = (-1e18, bpm_hint, 0.0)
    for cand in ([bpm_hint] if fixed else np.arange(bpm_hint - 3, bpm_hint + 3.001, 0.05)):
        period = 60 / cand
        for p in np.linspace(0, period, 48, endpoint=False):
            s = float((np.cos(2 * np.pi * (t - p) / period) * flux).sum())
            if s > best[0]:
                best = (s, float(cand), float(p))
    return round(best[1], 2), best[2]


def load_usage():
    try:
        return json.load(open(USAGE))
    except (OSError, ValueError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--mood")
    ap.add_argument("--style")
    ap.add_argument("--track")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--hit-at", type=float)
    ap.add_argument("--fade-out", type=float, default=1.5)
    ap.add_argument("--bpm", type=float, help="force the tempo (e.g. a round 120 when phase stays stable); only the downbeat is searched")
    a = ap.parse_args()

    catalog = json.load(open(os.path.join(LIB, "catalog.json")))
    usage = load_usage()
    pool = [t for t in catalog if (not a.mood or t["mood"] == a.mood) and (not a.style or any(a.style in s for s in t["styles"]))]

    if a.list or not a.out:
        for t in sorted(pool, key=lambda t: (t["mood"], t["bpm"])):
            last = usage.get(t["file"])
            used = time.strftime("%m-%d", time.localtime(last)) if last else "-"
            print(f"{t['mood']:11} {t['file']:42} {t['bpm']:6}{'~' if t['bpm_approx'] else ' '} {t['energy']:4} {t['duration']:6}s  arrival {t['arrival']:5}s  used {used}  {t['note']}")
        return

    if not a.seconds:
        raise SystemExit("--seconds is required")
    if a.track:
        track = next(t for t in catalog if t["file"] == a.track)
    else:
        def start_of(t):
            return max(0.0, t["arrival"] - a.hit_at) if a.hit_at is not None else 0.0

        fits = [t for t in pool if start_of(t) + a.seconds <= t["duration"]]
        if not fits:
            raise SystemExit("no track in this mood is long enough; try another --mood or omit --hit-at")
        track = min(fits, key=lambda t: (usage.get(t["file"], 0), a.hit_at is not None and t["arrival"] < a.hit_at))

    root = project_root(a.out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    src = fetch(track)
    arrival = track["arrival"]
    if a.hit_at is not None and arrival > 0.5:
        with tempfile.TemporaryDirectory() as tmp:
            win = os.path.join(tmp, "win.wav")
            ffmpeg(["-ss", f"{arrival - 0.5:.3f}", "-t", "1.0", "-i", src, "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", win], root)
            with wave.open(win) as w:
                m = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64)
        hop, size = 256, 1024
        frames = np.array([m[i : i + size] for i in range(0, len(m) - size, hop)])
        spec = np.log1p(np.abs(np.fft.rfft(frames * np.hanning(size), axis=1)))
        flux = np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)
        arrival = arrival - 0.5 + (int(np.argmax(flux)) + 1) * hop / 22050
    start = max(0.0, arrival - a.hit_at) if a.hit_at is not None else 0.0
    bpm, phase = precise_grid(src, start, min(a.seconds, 60.0), a.bpm or track["bpm"], root, fixed=bool(a.bpm))
    if a.hit_at is None:
        start += phase
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "cut.wav")
        ffmpeg(["-ss", f"{start:.3f}", "-t", f"{a.seconds:.3f}", "-i", src, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", raw], root)
        with wave.open(raw) as w:
            sr, ch = w.getframerate(), w.getnchannels()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64).reshape(-1, ch)
    n = len(x)
    fin = int(sr * (0.05 if start == 0 else 0.4))
    fout = min(n, int(sr * a.fade_out))
    env = np.ones(n)
    env[:fin] = np.linspace(0, 1, fin)
    env[n - fout :] *= np.linspace(1, 0, fout) ** 1.5
    y = (x * env[:, None]).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())

    credit = f"{track['title']} — {track['artist']}\nSource: {track['source']}\nLicense: {track['license']}\n{track['license_url']}\n"
    open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "credit.txt"), "w").write(credit)
    usage[track["file"]] = time.time()
    os.makedirs(os.path.dirname(USAGE), exist_ok=True)
    json.dump(usage, open(USAGE, "w"), indent=1)
    hit = f", main section lands at {a.hit_at:.2f}s" if a.hit_at is not None else ""
    print(f"wrote {a.out}: {track['title']} ({track['artist']}), {n / sr:.1f}s from {start:.2f}s{hit}")
    print(f"bpm {bpm} (catalog {track['bpm']}{', may be double/half' if track['bpm_approx'] else ''})  beat = {30 * 60 / bpm:.3f} frames @30fps  — use this BPM for the timeline")
    if a.hit_at is None:
        print(f"cut starts on a beat (shifted {phase:.3f}s), so beat k of the film falls at k * beat frames")
    print(credit.strip())


if __name__ == "__main__":
    main()
