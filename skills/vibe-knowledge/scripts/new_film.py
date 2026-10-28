#!/usr/bin/env python3
"""新建一期知识短片。
  python3 new_film.py <期号> --template A --title "本福特定律" [--series "系列名"] [--ws 工作区] [--no-optional-fonts]
做的事：
1. 工作区没有引擎就建好：skill 的 engine/ → <ws>/cine/（引擎代码每次都同步到 skill 当前版本），下载字体（scripts/fonts.py），
   写 <ws>/vk.json（默认 BGM、配音引擎，已有就不动）。
2. lessons/<期号>/：narration.json（母版旁白骨架）、film.js（画面骨架）、facts.md（事实清单）、assets.json（Renoise 资产清单）、
   assets/{img,clips,audio}/、build/、stills/。"""
import argparse
import json
import shutil
import sys

from vk import SKILL, workspace
import fonts

DEFAULT_CFG = {"bgm": "cine/music/vibe-bgm.m4a", "force_bgm": True, "voice_gap_db": 10, "series": ""}


def setup(ws, optional_fonts=True):
    cine = ws / "cine"
    shutil.copytree(SKILL / "engine", cine, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    fonts.fetch(ws, optional_fonts)
    cfg = ws / "vk.json"
    if not cfg.exists():
        cfg.write_text(json.dumps(DEFAULT_CFG, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ws / "lessons").mkdir(exist_ok=True)
    print(f"✓ 工作区：{ws}（引擎 cine/、设置 vk.json）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--template", required=True, choices=list("ABCDEF"))
    ap.add_argument("--title", required=True)
    ap.add_argument("--series", default=None, help="系列名，写进尾卡和 vk.json")
    ap.add_argument("--ws", default=None)
    ap.add_argument("--no-optional-fonts", action="store_true")
    a = ap.parse_args()

    ws = workspace()
    ws.mkdir(parents=True, exist_ok=True)
    setup(ws, not a.no_optional_fonts)
    cfg = json.loads((ws / "vk.json").read_text(encoding="utf-8"))
    if a.series:
        cfg["series"] = a.series
        (ws / "vk.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    L = ws / "lessons" / a.id
    if L.exists():
        sys.exit(f"这一期已存在：{L}")
    for d in ("assets/img", "assets/clips", "assets/audio", "build", "stills"):
        (L / d).mkdir(parents=True)
    T = SKILL / "templates"
    shutil.copy(T / f"narration/{a.template}.json", L / "narration.json")
    film = (T / "film.skeleton.js").read_text(encoding="utf-8")
    film = film.replace("__TITLE__", a.title).replace("__ID__", a.id).replace("__TPL__", a.template).replace("__SERIES__", cfg.get("series") or a.title)
    (L / "film.js").write_text(film, encoding="utf-8")
    shutil.copy(T / "facts.md", L / "facts.md")
    shutil.copy(T / "assets.json", L / "assets.json")
    print(f"✓ 新一期：{L}\n  母版 {a.template} · {a.title}\n  下一步：写 facts.md → narration.json → assets.json（报价确认）→ 配音（scripts/voice.py）→ film.js")


if __name__ == "__main__":
    main()
