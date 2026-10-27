#!/usr/bin/env python3
"""Pixel Breakdown toolchain check: prints ✓ for what is there and how to install what is missing. Installs nothing.
The Renoise sandbox has everything preinstalled.
  python3 doctor.py            exit code 0 = ready, 1 = something is missing
  python3 doctor.py --no-asr   skip faster-whisper (only alignment needs it)"""
import importlib.util, os, shutil, subprocess, sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SYS = {"darwin": "mac", "win32": "win"}.get(sys.platform, "linux")
PIP = f'"{sys.executable}" -m pip install'
missing = 0


def need(name, why, mac, win, linux):
    global missing
    missing = 1
    print(f"  ✗ {name} ({why})\n      install: {dict(mac=mac, win=win, linux=linux)[SYS]}")


print(f"Pixel Breakdown · toolchain check ({sys.platform})")
if sys.version_info >= (3, 8):
    print(f"  ✓ Python {sys.version.split()[0]}")
else:
    need("Python 3.8+", "every script", "brew install python", "winget install Python.Python.3.12", "sudo apt install python3")

for tool in ("ffmpeg", "ffprobe"):
    if shutil.which(tool):
        print(f"  ✓ {tool}")
    else:
        need(tool, "probing, re-encoding, final encode and QA", "brew install ffmpeg", "winget install Gyan.FFmpeg", "sudo apt install ffmpeg")

mods = [("numpy", "numpy", "audio"), ("scipy", "scipy", "resampling and the mix"), ("PIL", "pillow", "contact sheets, pixelize, cover"),
        ("playwright", "playwright", "renders every frame in headless Chromium")]
if "--no-asr" not in sys.argv:
    mods.append(("faster_whisper", "faster-whisper", "transcribes and aligns the voice takes"))
for mod, pkg, why in mods:
    if importlib.util.find_spec(mod):
        print(f"  ✓ {pkg}")
    else:
        need(pkg, why, *[f'{PIP} "{pkg}"'] * 3)

if importlib.util.find_spec("playwright"):
    # Launching is the only real test: the package can be there without its browser.
    code = ("import os\nfrom playwright.sync_api import sync_playwright\nkw = {'headless': True}\n"
            "if os.environ.get('CHROME'): kw['executable_path'] = os.environ['CHROME']\n"
            "with sync_playwright() as p: p.chromium.launch(**kw).close()")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        print("  ✓ Chromium for Playwright" + (f" (CHROME={os.environ['CHROME']})" if os.environ.get("CHROME") else ""))
    else:
        last = (r.stderr.strip().splitlines() or ["?"])[-1][:160]
        need("Chromium for Playwright", f"launch failed: {last}", *[f'"{sys.executable}" -m playwright install chromium'
                                                                    + (" --with-deps" if SYS == "linux" else "")
                                                                    + "  (or set CHROME=/path/to/chrome)"] * 3)

print("\n" + ("Ready." if not missing else "Install the ✗ items above, then run doctor.py again."))
sys.exit(missing)
