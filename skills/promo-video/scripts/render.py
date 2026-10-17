#!/usr/bin/env python3
"""Render a promo project. Remotion draws the picture and the mix; rn (renoise-kit) finishes, checks and audits.
macOS, Linux and Windows.

Usage: python3 render.py <project-dir> <mode> [frames...] [--lufs -14]      (Windows: python or py -3)
Template mode (Promo composition, storyboard-driven):
  stills  -> out/stills/scene-N.png (one mid-frame per scene, for style/storyboard review)
  preview -> out/preview.mp4 (half resolution, fast)
  final   -> out/final.mp4 + out/cover.png (+ out/captions.srt when scenes have captions)
Cinematic mode (Film composition in src/Film.tsx):
  film-stills F1 F2 ... -> out/stills/fN.png
  film-preview          -> out/film-preview.mp4 (half resolution)
  film                  -> out/film.mp4 (+ out/film-1080p.mp4 for 4K renders)

Every MP4 that leaves this script went through `rn finish`. The raw Remotion MP4 has fixed_frame_rate_flag=0 (some players
and upload pipelines show it at half its length), full-range BT.601 colour and an uncompensated AAC delay (the sound plays
43.7 ms late). Finals take their sound from a separate WAV render of the mix, so nothing needs compensating; previews skip
that render and move the sound 43.7 ms earlier instead. Loudness: -14 LUFS, encoded true peak <= -1 dBTP (--lufs -16, or the LUFS environment variable, to change).
Audits (rn qa + rn cuts) never fail a render; findings judged intended go in qa-accept.txt (CHECK or CHECK@SECONDS per line).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK copy or emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS = Path(__file__).resolve().parent
MODES = ("stills", "preview", "final", "film-stills", "film-preview", "film")
REMOTION_AAC_LEAD = "-0.0437"  # seconds; measured on Remotion 4.0.408 at 48 kHz


def read_env(project: Path) -> dict:
    """<project>/.promo-env as written by setup_project.py (KEY=value per line)."""
    env = project / ".promo-env"
    if not env.exists():
        return {}
    pairs = (line.split("=", 1) for line in env.read_text(encoding="utf-8").splitlines() if "=" in line)
    return {k.strip(): v.strip() for k, v in pairs}


def tool(name: str) -> str:
    """Full path of a command, so .cmd shims (npx.cmd on Windows) run without a shell. Next to npx.cmd sits an extensionless
    npx shell script that some Pythons' which() returns first, so npm's shims are asked for by their .cmd name."""
    found = shutil.which(name + ".cmd" if sys.platform == "win32" and name in ("npm", "npx") else name)
    if not found:
        sys.exit(f"{name} not found on PATH")
    return found


def run(*args, capture: bool = False) -> str:
    result = subprocess.run([str(a) for a in args], check=False, text=True, encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE if capture else None)
    if result.returncode != 0:
        sys.exit(result.returncode)
    return result.stdout if capture else ""


def storyboard(*args) -> str:
    return run(sys.executable, SCRIPTS / "check_storyboard.py", "storyboard.json", *args, capture=True)


def remotion(*args) -> None:
    run(tool("npx"), "remotion", *args, "--log=error")


def audit(video: str) -> None:
    """Continuity and delivery audit (references/detail-pass.md): rn qa covers format, loudness, true peak, dead air,
    level jumps, clicks, black and frozen frames; rn cuts lists the hard cuts with both sides of each on a sheet."""
    accept = []
    qa_accept = Path("qa-accept.txt")
    if qa_accept.exists():
        for line in qa_accept.read_text(encoding="utf-8-sig").splitlines():
            line = "".join(line.split("#", 1)[0].split())
            if line:
                accept += ["--accept", line]
    subprocess.run([tool("rn"), "qa", video, "--json", "out/audit/qa.json", *accept])
    subprocess.run([tool("rn"), "cuts", video, "--sheet", "out/audit/cuts.jpg", "--json", "out/audit/cuts.json"])


def finish(raw: str, target: str, lufs: str, *options: str) -> None:
    """The delivery encode; a 4K result also gets a 1080p copy."""
    run(tool("rn"), "finish", raw, "-o", target, "--lufs", lufs, *options)
    probe = Path("out/audit/probe.json")
    run(tool("rn"), "probe", target, "--json", probe, capture=True)
    if json.loads(probe.read_text(encoding="utf-8"))["video"]["height"] >= 2160:
        run(tool("rn"), "finish", target, "-o", target[:-len(".mp4")] + "-1080p.mp4", "--height", "1080", "--lufs", "keep")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("mode", choices=MODES)
    ap.add_argument("frames", nargs="*", help="film-stills: frame numbers")
    ap.add_argument("--lufs", default=os.environ.get("LUFS", "-14"), help="delivery loudness (default -14)")
    a = ap.parse_args()
    project, mode, frames, lufs = Path(a.project).resolve(), a.mode, a.frames, a.lufs
    if not project.is_dir():
        sys.exit(f"no such project: {project}")
    os.chdir(project)
    node_bin = read_env(project).get("NODE_BIN")
    if node_bin:
        os.environ["PATH"] = node_bin + os.pathsep + os.environ.get("PATH", "")
    if not shutil.which("rn"):
        sys.exit('rn not found: install renoise-kit (SKILL.md 依赖): uv tool install "renoise-kit[all]"')

    if not mode.startswith("film"):
        run(sys.executable, SCRIPTS / "check_storyboard.py", "storyboard.json")
    Path("out/audit").mkdir(parents=True, exist_ok=True)

    if mode == "stills":
        Path("out/stills").mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(storyboard("--frames").split(), 1):
            remotion("still", "Promo", f"out/stills/scene-{i}.png", f"--frame={f}")
            print(f"out/stills/scene-{i}.png (frame {f})")
        run(tool("rn"), "sheet", "out/stills", "-o", "out/stills-sheet.jpg")
    elif mode == "preview":
        remotion("render", "Promo", "out/preview-raw.mp4", "--scale=0.5")
        finish("out/preview-raw.mp4", "out/preview.mp4", lufs, "--preset", "veryfast", "--audio-offset", REMOTION_AAC_LEAD)
        audit("out/preview.mp4")
        print("out/preview.mp4")
    elif mode == "final":
        remotion("render", "Promo", "out/final-raw.mp4", "--muted")
        remotion("render", "Promo", "out/mix.wav", "--codec=wav", "--config=remotion.audio.config.ts")
        finish("out/final-raw.mp4", "out/final.mp4", lufs, "--audio", "out/mix.wav")
        scene_frames = storyboard("--frames").split()
        remotion("still", "Promo", "out/cover.png", f"--frame={scene_frames[1] if len(scene_frames) > 1 else scene_frames[0]}")
        storyboard("--srt", "out/captions.srt")
        srt = Path("out/captions.srt")
        if srt.exists() and srt.stat().st_size == 0:
            srt.unlink()
        audit("out/final.mp4")
        print("out/final.mp4")
    elif mode == "film-stills":
        if not frames:
            sys.exit("film-stills needs frame numbers")
        Path("out/stills").mkdir(parents=True, exist_ok=True)
        if Path("stills.mjs").exists():
            # one bundle + one browser for all frames (much faster than a `remotion still` per frame)
            run(tool("node"), "stills.mjs", "Film", "out/stills", *frames)
        else:
            for f in frames:
                remotion("still", "src/index.ts", "Film", f"out/stills/f{f}.png", f"--frame={f}")
                print(f"out/stills/f{f}.png")
        run(tool("rn"), "sheet", "out/stills", "-o", "out/stills-sheet.jpg")
    elif mode == "film-preview":
        remotion("render", "src/index.ts", "Film", "out/film-preview-raw.mp4", "--scale=0.5")
        finish("out/film-preview-raw.mp4", "out/film-preview.mp4", lufs, "--preset", "veryfast", "--audio-offset", REMOTION_AAC_LEAD)
        audit("out/film-preview.mp4")
        print("out/film-preview.mp4")
    else:
        remotion("render", "src/index.ts", "Film", "out/film-raw.mp4", "--muted")
        remotion("render", "src/index.ts", "Film", "out/mix.wav", "--codec=wav", "--config=remotion.audio.config.ts")
        finish("out/film-raw.mp4", "out/film.mp4", lufs, "--audio", "out/mix.wav")
        audit("out/film.mp4")
        print("out/film.mp4")


if __name__ == "__main__":
    main()
