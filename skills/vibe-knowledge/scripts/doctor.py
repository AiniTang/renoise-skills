#!/usr/bin/env python3
"""vibe-knowledge 环境自检：✓ 已有，✗ 缺什么、怎么装。什么都不装。Renoise sandbox 里大多已预装。
  python3 doctor.py            退出码 0 = 必需项齐了，1 = 缺必需项
  python3 doctor.py --no-asr   不查 faster-whisper（只有配音对齐要它）"""
import importlib.util
import os
import subprocess
import sys

from vk import CACHE

SYS = {"darwin": "mac", "win32": "win"}.get(sys.platform, "linux")
PIP = f'"{sys.executable}" -m pip install'
missing = 0


def need(name, why, mac, win, linux, required=True):
    global missing
    missing |= required
    print(f"  {'✗' if required else '·'} {name}（{why}）\n      装法：{dict(mac=mac, win=win, linux=linux)[SYS]}")


print(f"vibe-knowledge · 环境自检（{sys.platform}）")
if sys.version_info >= (3, 8):
    print(f"  ✓ Python {sys.version.split()[0]}")
else:
    need("Python 3.8+", "所有脚本", "brew install python", "winget install Python.Python.3.12", "sudo apt install python3")

import shutil  # noqa: E402
for t in ("ffmpeg", "ffprobe"):
    if shutil.which(t):
        print(f"  ✓ {t}")
    else:
        need(t, "转码、混音、成片、质检", "brew install ffmpeg", "winget install Gyan.FFmpeg", "sudo apt install ffmpeg")

mods = [("numpy", "numpy", "音频处理"), ("scipy", "scipy", "混音、代码音效"), ("PIL", "pillow", "接触表、拆层"),
        ("playwright", "playwright", "无头 Chromium 逐帧渲染画面")]
if "--no-asr" not in sys.argv:
    mods.append(("faster_whisper", "faster-whisper", "配音逐字对齐（第一次用会下载约 480 MB 的 small 模型）"))
for mod, pkg, why in mods:
    if importlib.util.find_spec(mod):
        print(f"  ✓ {pkg}")
    else:
        need(pkg, why, *[f'{PIP} "{pkg}"'] * 3)

if importlib.util.find_spec("playwright"):
    # 能启动、能拿到 WebGL 才算数：引擎全程用 WebGL 出图
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "engine/tools"))
    code = ("import sys\nsys.path.insert(0, sys.argv[1])\nfrom browser import launch\nfrom playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as p:\n b = launch(p); pg = b.new_page()\n"
            " print(pg.evaluate(\"() => !!document.createElement('canvas').getContext('webgl2')\")); b.close()")
    r = subprocess.run([sys.executable, "-c", code, sys.path[0]], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0 and r.stdout.strip() == "True":
        print("  ✓ Chromium（WebGL2 可用）" + (f"，CINE_CHROME={os.environ['CINE_CHROME']}" if os.environ.get("CINE_CHROME") else ""))
    elif r.returncode == 0:
        need("Chromium 的 WebGL2", "启动了但拿不到 WebGL2：换一个 Chromium（CINE_CHROME=路径）", *["python -m playwright install chromium"] * 3)
    else:
        last = (r.stderr.strip().splitlines() or ["?"])[-1][:160]
        need("Chromium for Playwright", f"启动失败：{last}", *[f'"{sys.executable}" -m playwright install chromium'
                                                              + (" --with-deps" if SYS == "linux" else "") + "（或设 CINE_CHROME=浏览器路径）"] * 3)

print("可选：")
for mod, pkg, why in [("rapidocr_onnxruntime", "rapidocr_onnxruntime", "qa.py 回读屏幕文字核对事实"),
                      ("rembg", "rembg", "layers.py 生图拆层（增强档纸拼贴、视差）")]:
    if importlib.util.find_spec(mod):
        print(f"  ✓ {pkg}")
    else:
        need(pkg, why, *[f'{PIP} "{pkg}"'] * 3, required=False)
es = os.environ.get("EARSHOT_PY") or str(CACHE / "earshot/.venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
if os.path.exists(es):
    print("  ✓ earshot 代码音效")
else:
    need("earshot 代码音效", "film.js 里用 earshot: 音效时要", *[f'"{sys.executable}" scripts/earshot.py install'] * 3, required=False)
if os.environ.get("MIMO_API_KEY"):
    print("  ✓ MIMO_API_KEY（可选的 MiMo 配音）")

print("\n" + ("必需项齐了。" if not missing else "把 ✗ 的装上，再跑一次 doctor.py。"))
sys.exit(missing)
