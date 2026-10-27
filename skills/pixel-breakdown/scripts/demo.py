#!/usr/bin/env python3
"""An offline demo episode: checks the whole picture and sound pipeline without credits, footage or a speech model.
  python3 demo.py <project>
Sets up the project (setup_project.py), makes two synthetic 8 s vertical clips with a hard cut at 4 s (ffmpeg test sources),
encodes them with media.py, writes a 5-line English episode.js that uses compare, title, chat (user, tool, quote, progress,
result) and outro scenes, a synthetic "voice" (tone bursts, one per word, pauses between lines) and a hand-made alignment for
it. Then, inside the project:
  python3 layout.py audio/vo_demo.wav audio/vo_demo_align.json && python3 font.py fonts/<bdf>
  python3 render.py stills 0.5,3,6,9,12 && python3 render.py cues && python3 mix.py && python3 render.py cover cover.png
  python3 render.py frames --workers 4 && python3 <skill>/scripts/media.py final frames audio/mix.wav out/demo.mp4"""
import json, subprocess, sys, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT = ["Left is the viral clip, right is my AI remake.",
          "Same cuts, same timing, a brand new star.",
          "Here is exactly how it was made.",
          "I dropped the clip in and asked for a remake.",
          "Follow for the next one!"]

EPISODE = {
    "title": "Pixel Breakdown demo", "lang": "en", "brand": {"name": "Demo Channel"}, "host": None,
    "media": {"source": "media/enc/source.mp4", "remake": "media/enc/remake.mp4"},
    "script": SCRIPT,
    "anchors": {"right": [1, "right"], "star": [2, "star"], "dropped": [4, "dropped"], "remake": [4, "remake"], "follow": [5, "follow"]},
    "keywords": {"1": ["AI remake"], "2": ["brand new star"]},
    "pacing": {"3": 0.5, "4": 0.6, "5": 0.8},
    "scenes": [
        {"type": "compare", "at": 0, "crt": True, "left": {"media": "source", "label": "Original", "clock": 0},
         "right": {"media": "remake", "label": "AI remake", "labelAt": "@right-0.2", "clock": 0}, "vs": "@right+0.3",
         "items": [{"kind": "stamp", "at": "@star-0.1", "text": "New star", "x": 240, "y": 196}]},
        {"type": "title", "at": "L3-0.2", "tr": "whip", "lines": [["How it was made", "accent", 3]], "sub": "Demo"},
        {"type": "chat", "at": "L4-0.2", "tr": "pblocks",
         "app": {"name": "Agent", "model": "Demo model", "tool": "Renoise", "title": "Remake demo", "greeting": "What are we making today?",
                 "placeholder": "Describe the video"},
         "messages": [
             {"id": "m1", "role": "user", "text": "Remake this clip with my character.", "attachments": [{"thumb": "assets/thumb_source.jpg", "name": "source.mp4"}],
              "dropAt": "@dropped-0.2", "typeAt": "@dropped+0.2", "sendAt": "@remake"},
             {"id": "m2", "role": "tool", "name": "analyze_media", "detail": "source.mp4", "at": "@remake+0.3", "doneAt": "@remake+1.0"},
             {"id": "m3", "role": "quote", "title": "Quote", "rows": [["Model", "demo"], ["Length", "8 s"], ["Credits", "0"]], "costRow": 2, "at": "@remake+1.2", "step": 0.2},
             {"id": "m4", "role": "progress", "name": "Generating", "items": [{"label": "remake", "minutes": 1, "done": True}], "at": "L4e-0.6", "doneAt": "L4e-0.1"},
             {"id": "m5", "role": "result", "name": "remake.mp4", "video": "remake", "caption": "Done", "at": "L4e"}]},
        {"type": "outro", "at": "L5-0.15", "tr": "blocks", "follow": {"at": "@follow"}, "endAt": "L5e+0.3", "endText": "See you soon"}
    ],
    "cover": {"bg": "blue", "lines": [["Remake", "#fff8ec", 5], ["it", "#ffd23f", 5]], "badge": "Demo",
              "focus": {"kind": "pair", "left": {"media": "source", "t": 2, "tag": "Original"}, "right": {"media": "remake", "t": 6, "tag": "AI remake"}}}
}


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


def ffmpeg(*args):
    import shutil
    subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


def synth_voice(path, sr=48000):
    """One 0.24 s buzz per word, 0.08 s between words, 0.5 s between lines. Returns per-line word spans."""
    import numpy as np
    out, spans, t = [np.zeros(int(0.4 * sr))], [], 0.4
    for line in SCRIPT:
        words = []
        for k, word in enumerate(line.split()):
            n = int(0.24 * sr)
            ts = np.arange(n) / sr
            f0 = 140 + 30 * ((k * 7) % 5)
            tone = sum(np.sin(2 * np.pi * f0 * h * ts) / h for h in range(1, 6)) * np.sin(np.pi * ts / 0.24) * 0.25
            words.append((word, t, t + 0.24))
            out += [tone, np.zeros(int(0.08 * sr))]
            t += 0.32
        out.append(np.zeros(int(0.42 * sr)))
        t += 0.42
        spans.append(words)
    out.append(np.zeros(int(1.0 * sr)))
    x = np.concatenate(out)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return spans


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    project = Path(sys.argv[1]).expanduser().resolve()
    run(HERE / "setup_project.py", project)
    tmp = project / "media"
    for key, a, b in [("source", "testsrc2", "smptebars"), ("remake", "testsrc", "rgbtestsrc")]:
        ffmpeg("-f", "lavfi", "-i", f"{a}=size=540x960:rate=30:duration=4", "-f", "lavfi", "-i", f"{b}=size=540x960:rate=30:duration=4",
               "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", tmp / f"{key}.mp4")
        run(HERE / "media.py", "intra", tmp / f"{key}.mp4", tmp / f"enc/{key}.mp4")
        run(HERE / "media.py", "thumb", tmp / f"{key}.mp4", project / f"assets/thumb_{key}.jpg")
    (project / "episode.js").write_text("window.EP = " + json.dumps(EPISODE, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")

    sys.path.insert(0, str(project))
    from common import norm_chars
    spans = synth_voice(project / "audio/vo_demo.wav")
    lines = []
    for text, words in zip(SCRIPT, spans):
        chars = []
        for word, t0, t1 in words:
            cs = norm_chars(word)
            chars += [[c, round(t0 + (t1 - t0) * i / len(cs), 3), round(t0 + (t1 - t0) * (i + 1) / len(cs), 3)] for i, c in enumerate(cs)]
        lines.append({"text": text, "s": chars[0][1], "e": chars[-1][2], "chars": chars})
    (project / "audio/vo_demo_align.json").write_text(json.dumps({"take": "audio/vo_demo.wav", "lines": lines}), encoding="utf-8")
    print(f"demo project -> {project}\nnext (inside the project): see the commands at the top of demo.py")


if __name__ == "__main__":
    main()
