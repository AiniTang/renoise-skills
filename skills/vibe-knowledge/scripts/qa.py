#!/usr/bin/env python3
"""成片质检：python3 qa.py <成片.mp4> [--every 3] [--out qa/] [--ws 工作区]
1) 每 N 秒抽一帧拼接触表 qa/sheet.jpg（逐张看：字溢出、压字幕、空屏、配图里有乱码字）
2) OCR 回读屏幕上的每一行字 → qa/ocr.txt（对照 facts.md 核数字、引文、出处）。用 RapidOCR（pip install rapidocr_onnxruntime），没装就跳过这一项
3) 响度：整体 LUFS / 真峰值（目标 ≈ −14.5 LUFS、≤ −1 dBTP）
4) 冻结检测：画面连续 >3 秒几乎不变就报警（违反「最长静止 ≤3 秒」；整段几十秒不变 = 录制出事，要重录）
5) BGM：读 finish.py 写的 build/bgm.json（有没有 BGM、人声比）；没有 bgm.json 时退回做相关检测（成片开头跟原曲开头比，片长短于原曲结尾段时不准）"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vk import arg

src = Path(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
every = float(arg("--every", "3"))
out = Path(arg("--out", str(src.parent / "qa")))
ws = Path(arg("--ws")) if arg("--ws") else next((p for p in src.resolve().parents if (p / "vk.json").exists()), None)
out.mkdir(parents=True, exist_ok=True)
fr = out / "frames"
fr.mkdir(exist_ok=True)
for f in fr.glob("*.png"):
    f.unlink()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"fps=1/{every},scale=1600:-2", str(fr / "f_%04d.png")], check=True)
fs = sorted(fr.glob("f_*.png"))

# ── OCR ──
lines = []
try:
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    seen = []
    for i, f in enumerate(fs):
        t = i * every
        res, _ = engine(str(f))
        for box, text, conf in sorted(res or [], key=lambda r: min(p[1] for p in r[0])):
            text = text.strip()
            if conf > 0.5 and len(text) > 1 and text not in seen[-30:]:
                seen.append(text)
                lines.append(f"{int(t // 60)}:{t % 60:04.1f}  {text}")
    (out / "ocr.txt").write_text("\n".join(lines), encoding="utf-8")
    ocr_note = f"→ {out / 'ocr.txt'}  {len(lines)} 行"
except ImportError:
    ocr_note = "OCR：没装 rapidocr_onnxruntime，跳过（pip install rapidocr_onnxruntime）；屏幕上的字请对着接触表人工核"

# ── 接触表 ──
w = 400
ims = [Image.open(f) for f in fs]
h = int(w * ims[0].height / ims[0].width)
cols = 6
sheet = Image.new("RGB", (cols * w, ((len(ims) + cols - 1) // cols) * h), "black")
d = ImageDraw.Draw(sheet)
font_path = ws / "cine/fonts/GeistMono-VF.ttf" if ws else None
font = ImageFont.truetype(str(font_path), 20) if font_path and font_path.exists() else ImageFont.load_default()
for i, im in enumerate(ims):
    x, y = (i % cols) * w, (i // cols) * h
    sheet.paste(im.resize((w, h)), (x, y))
    t = i * every
    d.rectangle([x, y, x + 70, y + 24], fill="black")
    d.text((x + 4, y + 2), f"{int(t // 60)}:{int(t % 60):02d}", fill="yellow", font=font)
sheet.save(out / "sheet.jpg", quality=82)

# ── 响度、冻结 ──
r = subprocess.run(["ffmpeg", "-nostats", "-i", str(src), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace").stderr
I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
fz = subprocess.run(["ffmpeg", "-nostats", "-i", str(src), "-an", "-vf", "fps=10,scale=480:-2,freezedetect=n=0.002:d=3", "-f", "null", "-"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", fz)]
durs = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", fz)]
if len(durs) < len(starts):
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                                 capture_output=True, text=True).stdout)
    durs.append(total - starts[-1])
frozen = list(zip(starts, durs))
(out / "freeze.txt").write_text("\n".join(f"{int(a // 60)}:{a % 60:04.1f}  静止 {d:.1f} 秒" for a, d in frozen), encoding="utf-8")
print(f"→ {out / 'sheet.jpg'}  {len(fs)} 帧\n{ocr_note}\n响度 {I[-1] if I else '?'} LUFS  真峰值 {P[-1] if P else '?'} dBTP")
if frozen:
    print(f"⚠ 静止画面 {len(frozen)} 段（>3 秒）→ {out / 'freeze.txt'}：" + "，".join(f"{int(a // 60)}:{a % 60:04.1f} 起 {d:.1f}s" for a, d in frozen[:6]))
    if any(d > 10 for _, d in frozen):
        print("⚠⚠ 有超过 10 秒的冻结，多半是录制出事（并行录制 / 页面卡死），重录后再交付")
else:
    print("静止检测：没有超过 3 秒的静止画面")

# ── BGM ──
bj = src.parent / "bgm.json"
rep = json.loads(bj.read_text(encoding="utf-8")) if bj.exists() else {}
cfg = json.loads((ws / "vk.json").read_text(encoding="utf-8")) if ws and (ws / "vk.json").exists() else {}
extra = f"；说话时人声比 BGM 高 {rep['voice_gap_db']} dB，停顿处 {rep.get('gap_in_pauses_db')} dB" if rep.get("voice_gap_db") is not None else ""
if rep and not rep.get("forced", True):
    print("BGM：这期关掉了默认 BGM" + (f"（有 BGM{extra}）" if rep.get("has_bgm") else "（没有 BGM）"))
elif rep.get("user_bgm"):
    print(f"BGM：这期换成了 {rep['user_bgm']}{extra}")
elif rep:
    print(f"BGM：有默认 BGM{'（自动补的）' if rep.get('auto') else ''}{extra}" if rep.get("has_bgm") else
          "⚠⚠ BGM：混音里没有 BGM。默认每期都要有：确认 render.py film 跑完了 finish 这一步")
elif ws and cfg.get("force_bgm", True):
    def pcm(f, t, sr=4000):
        b = subprocess.run(["ffmpeg", "-v", "error", "-t", str(t), "-i", str(f), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
        return np.frombuffer(b, np.float32).copy()
    x = pcm(src, 12)
    ref = pcm(ws / cfg.get("bgm", "cine/music/vibe-bgm.m4a"), min(8.0, max(1.0, len(x) / 4000 - 1.0)))   # 短片取短一点的参考段
    best, lag = 0.0, 0.0
    for k in range(0, 4000 * 3, 20):
        seg = x[k:k + len(ref)]
        if len(seg) < len(ref):
            break
        c = float(np.dot(seg, ref) / (np.linalg.norm(seg) * np.linalg.norm(ref) + 1e-9))
        if c > best:
            best, lag = c, k / 4000
    if best >= 0.12:
        print(f"BGM：有默认 BGM（相关 {best:.2f}，从 {lag:.2f}s 起）{extra}")
    else:
        print(f"⚠⚠ BGM：没检测到默认 BGM（相关 {best:.2f}）。默认每期都要有：确认 render.py film 跑完了 finish 这一步")
