#!/usr/bin/env python3
"""Validate storyboard.json and report timing.

Usage:
  python3 check_storyboard.py path/to/storyboard.json            # report + warnings
  python3 check_storyboard.py path/to/storyboard.json --frames   # mid-frame of each scene
  python3 check_storyboard.py path/to/storyboard.json --srt out.srt

Timing uses the same formula as src/timing.ts (cuts snap to beats when music.bpm is set).
Exit code 1 when there are errors; warnings do not fail.
"""
import argparse
import json
import os
import re
import sys

if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK copy or emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCENE_TYPES = {"statement", "hero3d", "features", "stats", "showcase", "outro"}
ICONS = {
    "spark", "bolt", "shield", "chart", "globe", "chat", "clock", "heart", "cube", "check",
    "search", "lock", "users", "book", "factory", "wallet", "layers", "rocket",
}
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]")
READ_RATE = {"zh": 7.0, "ja": 7.0, "en": 3.3}


def net_frames(sb):
    fps = sb["format"]["fps"]
    bpm = (sb.get("music") or {}).get("bpm")
    scenes = sb["scenes"]
    if not bpm:
        return [max(1, round(s["seconds"] * fps)) for s in scenes]
    beat = fps * 60 / bpm
    out, cum, prev = [], 0, 0
    for s in scenes:
        cum += max(1, round(s["seconds"] * fps / beat))
        boundary = round(cum * beat)
        out.append(boundary - prev)
        prev = boundary
    return out


def scene_text(s):
    parts = []
    t = s["type"]
    if t == "statement":
        parts += [s.get("eyebrow", ""), s.get("text", "")]
    elif t == "hero3d":
        parts += [s.get("title", ""), s.get("subtitle", "")]
    elif t == "features":
        parts.append(s.get("title", ""))
        for it in s.get("items", []):
            parts += [it.get("title", ""), it.get("body", "")]
    elif t == "stats":
        parts.append(s.get("title", ""))
        parts += [it.get("label", "") for it in s.get("items", [])]
    elif t == "showcase":
        parts += [s.get("title", ""), s.get("body", "")]
    elif t == "outro":
        parts += [s.get("tagline", ""), s.get("cta", ""), s.get("url", "")]
    return " ".join(p for p in parts if p)


def reading_seconds(text, lang):
    cjk = len(CJK.findall(text))
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.'%-]*", text))
    rate = READ_RATE.get(lang, READ_RATE["zh"])
    return cjk / rate + words / READ_RATE["en"] + 0.5


def srt_time(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("--frames", action="store_true")
    ap.add_argument("--srt")
    a = ap.parse_args()
    sb = json.load(open(a.storyboard, encoding="utf-8-sig"))
    errors, warns = [], []

    for key in ("meta", "format", "style", "brand", "scenes"):
        if key not in sb:
            errors.append(f"missing top-level key: {key}")
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)
    if sb["style"] not in {"keynote", "kinetic", "aurora", "editorial"}:
        errors.append(f"unknown style {sb['style']}")
    if sb["format"].get("aspect", "16:9") not in {"16:9", "9:16", "1:1", "4:5"}:
        errors.append("format.aspect must be 16:9, 9:16, 1:1 or 4:5")
    lang = sb["meta"].get("language", "zh")

    for i, s in enumerate(sb["scenes"]):
        if s.get("type") not in SCENE_TYPES:
            errors.append(f"scene {i + 1}: unknown type {s.get('type')}")
            continue
        if not isinstance(s.get("seconds"), (int, float)) or s["seconds"] <= 0:
            errors.append(f"scene {i + 1}: seconds must be > 0")
            continue
        if s.get("tone") not in (None, "light", "dark"):
            errors.append(f"scene {i + 1}: tone must be light or dark")
        if s["type"] == "features":
            for it in s.get("items", []):
                if it.get("image"):
                    continue
                if it.get("icon") not in ICONS:
                    errors.append(f"scene {i + 1}: unknown icon {it.get('icon')} (use one of {sorted(ICONS)})")
        need = reading_seconds(scene_text(s), lang)
        if need > s["seconds"]:
            warns.append(f"scene {i + 1} ({s['type']}): text needs ~{need:.1f}s to read, has {s['seconds']}s")
    if not sb["brand"].get("logo") and not sb["brand"].get("disclaimer"):
        warns.append("no brand.logo: add brand.disclaimer (placeholder wordmark is being used)")
    music = sb.get("music") or {}
    if music.get("file") and not music.get("bpm"):
        warns.append("music.file without music.bpm: cuts will not land on beats")

    public = os.path.join(os.path.dirname(os.path.abspath(a.storyboard)), "public")
    brand = sb["brand"]
    fonts = brand.get("fonts") or {}
    assets = [brand.get("logo"), brand.get("wordmark"), music.get("file")]
    assets += [(fonts.get(k) or {}).get("file") for k in ("display", "body")]
    for s in sb["scenes"]:
        assets.append(s.get("image"))
        assets += [it.get("image") for it in s.get("items", []) if isinstance(it, dict)]
    for path in filter(None, assets):
        if not os.path.isfile(os.path.join(public, path)):
            errors.append(f"missing asset public/{path}")

    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)

    fps = sb["format"]["fps"]
    nets = net_frames(sb)
    starts = [sum(nets[:i]) for i in range(len(nets))]

    if a.frames:
        print(" ".join(str(st + n // 2) for st, n in zip(starts, nets)))
        return

    if a.srt:
        lines, k = [], 1
        for s, st, n in zip(sb["scenes"], starts, nets):
            text = s.get("caption")
            if not text:
                continue
            lines += [str(k), f"{srt_time(st / fps)} --> {srt_time((st + n) / fps)}", text, ""]
            k += 1
        open(a.srt, "w", encoding="utf-8").write("\n".join(lines))
        print(f"wrote {a.srt} ({k - 1} cues)")
        return

    total = sum(nets)
    print(f"{sb['meta'].get('title', '')}  style={sb['style']}  aspect={sb['format'].get('aspect', '16:9')}  fps={fps}")
    for i, (s, st, n) in enumerate(zip(sb["scenes"], starts, nets)):
        print(f"  {i + 1}. {s['type']:<9} {st / fps:6.2f}s  +{n / fps:.2f}s  camera={s.get('camera', '-')}")
    print(f"total {total / fps:.2f}s ({total} frames)")
    for w in warns:
        print("WARN " + w)


if __name__ == "__main__":
    main()
