#!/usr/bin/env python3
"""剪辑环境检查：有的打 ✓，缺的才给装法。不自动安装。Renoise sandbox 里全部预装。
用法：python3 doctor.py        退出码 0 = 齐了，1 = 有缺的"""
import importlib.util, shutil, subprocess, sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SYS = {"darwin": "mac", "win32": "win"}.get(sys.platform, "linux")
missing = 0

def need(name, why, mac, win, linux):
    global missing
    missing = 1
    print(f"  ✗ {name}（{why}）\n      装法：{dict(mac=mac, win=win, linux=linux)[SYS]}")

print(f"数字人口播 · 剪辑环境检查（{sys.platform}）")
if shutil.which("ffmpeg"): print("  ✓ ffmpeg")
else: need("ffmpeg", "抽帧、拼接、响度", "brew install ffmpeg", "winget install Gyan.FFmpeg", "sudo apt install ffmpeg")
print(f"  ✓ Python {sys.version.split()[0]}")
for mod, pkg, why in [("numpy", "numpy", "声音统一、音效合成"), ("PIL", "pillow", "抠像、预览图"),
                      ("faster_whisper", "faster-whisper", "逐段回听、逐字对齐"), ("rembg", "rembg[cpu]", "景深字抠像（只有 TextBehind 用）")]:
    if importlib.util.find_spec(mod): print(f"  ✓ {pkg}")
    else: need(pkg, why, *[f'{sys.executable} -m pip install "{pkg}"'] * 3)
node = shutil.which("node")
major = int(subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip().lstrip("v").split(".")[0]) if node else 0
if major >= 18: print(f"  ✓ Node {major}")
else: need("Node 18+", "Remotion 剪辑", "brew install node", "winget install OpenJS.NodeJS.LTS", "nvm install --lts")
print("\n" + ("环境齐了。" if not missing else "装好上面 ✗ 的项，再跑一次 doctor.py 确认。"))
sys.exit(missing)
