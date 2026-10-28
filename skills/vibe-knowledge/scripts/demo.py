#!/usr/bin/env python3
"""不花积分的演示期：检查引擎、渲染、混音、质检是否装好（也是 CI 跑的那一套）。
  python3 demo.py [--ws 工作区] [--take 录音.wav] [--no-optional-fonts]
建好工作区（同 new_film.py）和 lessons/demo/（两拍、约 10 秒，templates/demo/）。
配音：给了 --take（任何一段念了 templates/demo/narration.json 两句话的录音）就走 voice.py align 的真实对齐；
      没给就合成一段「占位人声」（按字数排的音节噪声，不是真的语音），时间按字数均匀排，用来检查画面和混音。
然后：python3 render.py stills demo <输出.png> 1 B02.fifty --ws …；python3 render.py film demo --title 演示 --ws …；python3 qa.py <ws>/lessons/demo/build/lessondemo.mp4"""
import shutil
import subprocess
import sys

import numpy as np

from vk import SKILL, arg, workspace
import new_film
import voice


def placeholder(L):
    d, v, lang, beats = voice.load(L)
    rng = np.random.default_rng(7)
    sr = voice.SR
    for b in beats:
        n = len(b["clean"])
        per = 0.18
        x = np.zeros(int(n * per * sr) + int(0.1 * sr), np.float32)
        rel = []
        for i, c in enumerate(b["clean"]):
            rel.append(i * per)
            if c in voice.PUNCT:
                continue
            a = int(i * per * sr); m = int(0.14 * sr)
            env = np.sin(np.linspace(0, np.pi, m)) ** 2
            tone = np.sin(2 * np.pi * (140 + 30 * rng.random()) * np.arange(m) / sr)
            x[a:a + m] += (0.12 * tone + 0.05 * rng.standard_normal(m)) * env
        b.update(x=x, rel=rel, cover=1.0, heard=None)
    voice.finish(L, beats, lang, "placeholder", 0.25, 0.3)


def main():
    ws = workspace()
    ws.mkdir(parents=True, exist_ok=True)
    new_film.setup(ws, "--no-optional-fonts" not in sys.argv)
    L = ws / "lessons" / "demo"
    if L.exists():
        shutil.rmtree(L)
    for sub in ("assets", "build", "stills"):
        (L / sub).mkdir(parents=True)
    for f in ("narration.json", "film.js"):
        shutil.copy(SKILL / "templates/demo" / f, L / f)
    take = arg("--take")
    if take:
        subprocess.run([sys.executable, str(SKILL / "scripts/voice.py"), "align", str(L), take], check=True)
    else:
        placeholder(L)
    print(f"✓ 演示期：{L}")


if __name__ == "__main__":
    main()
