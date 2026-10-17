#!/usr/bin/env python3
"""Music bed for the 12 s cut: Mixkit "Tears of Joy" from its first downbeat (film frame 0), spliced at film bar 4
(under the zoom-out whoosh) to the bar before the track's own final chord, so that chord lands on film bar 5 (the end
headline). 120 ms equal-power crossfade at the splice, 2-frame fade-in at the head. Writes public/music/bgm.wav + credit.
"""
import os, sys, json
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


SKILL = skill_dir(ROOT)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
sys.path.insert(0, os.path.join(SKILL, "templates", "remotion", "examples", "style-catalog", "tools"))
from pick_music import CATALOG_FILE, fetch, precise_grid  # noqa: E402
import build_audio as ba  # noqa: E402

ba.ROOT = ROOT
SR = 48000
SRC = fetch(next(t for t in json.load(open(CATALOG_FILE)) if t["file"] == "mixkit-839-tears-of-joy.mp3"))
FILM_S = 12.0
BPM_FILM = 124.05  # timeline.ts

song = ba.load(SRC)
bpm, down = precise_grid(SRC, 0.0, 60.0, 123.0, ROOT)
bar = 240 / bpm
m = song.mean(1)
bars = int((len(m) / SR - down) / bar)
rms = [20 * np.log10(np.sqrt((m[int((down + b * bar) * SR):int((down + (b + 1) * bar) * SR)] ** 2).mean()) + 1e-9) for b in range(bars)]
med = float(np.median(rms))
# the final chord: the last bar that is still at full level, followed by the decay
last_full = max(b for b in range(bars) if rms[b] > med - 6)
hit = down + last_full * bar
film_bar = 240 / BPM_FILM
splice_film = 4 * film_bar  # film bar 4
hit_film = 5 * film_bar  # film bar 5
head = song[int(down * SR): int((down + splice_film) * SR) + int(0.06 * SR)]
tail_start = hit - (hit_film - splice_film)
tail = song[int((tail_start - 0.06) * SR):]
n = int(0.12 * SR)
w = np.linspace(0, np.pi / 2, n)[:, None]
out = np.concatenate([head[:-n], head[-n:] * np.cos(w) + tail[:n] * np.sin(w), tail[n:]])
out = out[: int(FILM_S * SR) + SR // 10]
fade = int(SR * 2 / 30)
out[:fade] *= np.linspace(0, 1, fade)[:, None]
ba.save(os.path.join(ROOT, "public/music/bgm.wav"), out, peak=1.0)
open(os.path.join(ROOT, "public/music/credit.txt"), "w").write("Tears of Joy — Mixkit (track 839), Mixkit Stock Music Free License: web/ads OK, not broadcast.\nhttps://mixkit.co/license/#musicFree\n")
end_db = 20 * np.log10(np.sqrt((out[int((FILM_S - 0.3) * SR):int(FILM_S * SR)].mean(1) ** 2).mean()) + 1e-9)
print(json.dumps({"bpm_measured": round(bpm, 3), "downbeat": round(down, 3), "final_chord_bar": last_full, "final_chord_s": round(hit, 3), "splice_film_s": round(splice_film, 3), "hit_film_s": round(hit_film, 3), "tail_from_song_s": round(tail_start, 3), "last_300ms_db": round(float(end_db), 1)}))
