#!/usr/bin/env python3
"""人声后期（可选）：高通 + 低频加厚 + 去闷 + 齿音前的亮度 + 压缩，让克隆音色更「贴麦」。在配音 + 变速之后跑。
用法：python3 voice_post.py <期号或期目录> [--ws 工作区]      原件留 build/narration.pre.wav，重复跑从原件算。"""
import shutil, subprocess, sys

from vk import lesson_dir

if len(sys.argv) < 2:
    sys.exit(__doc__)
b = lesson_dir(sys.argv[1]) / "build"
pre, cur = b / "narration.pre.wav", b / "narration.wav"
if not pre.exists() or cur.stat().st_mtime > pre.stat().st_mtime + 1: shutil.copy(cur, pre)
chain = "highpass=f=70,equalizer=f=140:t=o:w=1:g=3.5,equalizer=f=420:t=o:w=1:g=-2,equalizer=f=3200:t=o:w=1:g=3,acompressor=threshold=-22dB:ratio=3.5:attack=4:release=90:makeup=2"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pre), "-af", chain, "-ar", "48000", str(cur)], check=True)
shutil.copystat(pre, cur); cur.touch()
print("✓ 人声后期 →", cur)
