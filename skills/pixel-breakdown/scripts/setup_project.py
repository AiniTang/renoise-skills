#!/usr/bin/env python3
"""Start (or refresh) a Pixel Breakdown project: folders, the engine, the pixel font.
  python3 setup_project.py <project> [--lang zh-CN] [--update]
- Makes media/enc, assets, audio, fonts, qa.
- Copies <skill>/engine/* into the project root. Files already there are kept (they may be newer than the skill's) unless
  --update is given; a differing file is reported either way.
- Downloads the Fusion Pixel font archive once into the cache (PIXEL_BREAKDOWN_CACHE, default ~/.cache/pixel-breakdown),
  checks its size and sha256, and extracts the BDF for the language plus the licence files into fonts/.
Prints the BDF path to give font.py."""
import argparse, hashlib, json, os, shutil, sys, time, urllib.request, zipfile
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SKILL = Path(__file__).resolve().parent.parent
FONTS = json.loads((SKILL / "assets/fonts.json").read_text(encoding="utf-8"))
DIRS = ["media/enc", "assets", "audio", "fonts", "qa"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch_font_archive():
    cache = Path(os.environ.get("PIXEL_BREAKDOWN_CACHE") or Path.home() / ".cache/pixel-breakdown")
    cache.mkdir(parents=True, exist_ok=True)
    dst = cache / FONTS["url"].rsplit("/", 1)[1]
    if dst.exists() and dst.stat().st_size == FONTS["bytes"] and sha256(dst) == FONTS["sha256"]:
        return dst
    for attempt in range(1, 4):
        tmp = dst.with_suffix(".part")
        try:
            print(f"downloading {FONTS['name']} ({FONTS['bytes'] / 1e6:.0f} MB), attempt {attempt}", flush=True)
            with urllib.request.urlopen(FONTS["url"], timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if tmp.stat().st_size == FONTS["bytes"] and sha256(tmp) == FONTS["sha256"]:
                tmp.replace(dst)
                return dst
            print("  checksum mismatch, retrying")
        except OSError as e:
            print(f"  download failed: {e}")
        time.sleep(2 * attempt)
    raise SystemExit("could not download the pixel font with the expected checksum; do not substitute another font")


def bdf_for(lang):
    files, key = FONTS["files"], (lang or "en").lower()
    return files.get(key) or files.get(key.split("-")[0]) or files["default"]


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument("project")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--update", action="store_true")
    a = ap.parse_args()
    project, lang = Path(a.project).expanduser().resolve(), a.lang
    for d in DIRS:
        (project / d).mkdir(parents=True, exist_ok=True)

    for src in sorted((SKILL / "engine").iterdir()):
        dst = project / src.name
        if not dst.exists() or a.update:
            shutil.copyfile(src, dst)
        elif dst.read_bytes() != src.read_bytes():
            print(f"kept the project's own {src.name} (differs from the skill's; --update replaces it)")
    print(f"engine -> {project}")

    bdf = bdf_for(lang)
    with zipfile.ZipFile(fetch_font_archive()) as z:
        for name in z.namelist():
            if name == bdf or name == "OFL.txt" or name.startswith("LICENSES/"):
                if name.endswith("/"):
                    continue
                out = project / "fonts" / name
                out.parent.mkdir(parents=True, exist_ok=True)
                if not out.exists():
                    out.write_bytes(z.read(name))
    if not (project / "fonts" / bdf).exists():
        raise SystemExit(f"{bdf} is not in the font archive")
    print(f"font  -> fonts/{bdf} (SIL OFL 1.1, licence in fonts/)")
    print(f"next: write episode.js, then  python3 font.py fonts/{bdf}")


if __name__ == "__main__":
    main()
