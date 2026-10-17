#!/usr/bin/env python3
"""Inspect the font files a project actually loads: axes, features, punctuation coverage.

Usage:
  python3 font_check.py public/fonts             # every .woff2/.woff/.ttf/.otf under a folder (recursive)
  python3 font_check.py Newsreader.woff2 Inter.woff2

Catches the silent killers (references/typography.md section 5 and 7):
  * a variable font that has an optical-size (opsz) axis in the family but not in this FILE (fontsource `wght` files):
    the font is locked to its text cut, so large type looks heavy and loose, "not elegant";
  * missing ’ “ ” – — … (a Latin subset without real punctuation quietly falls back to another font);
  * no tnum for counters, no ital file for a serif you italicise (fake italics smear).
Needs fontTools (+ brotli for woff2):  pip install fonttools brotli
"""
import os
import sys

try:
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("pip install fonttools brotli")

# families that ship an opsz axis in their variable release (the file should carry it for display sizes)
OPSZ_FAMILIES = ("newsreader", "fraunces", "source serif", "literata", "roboto serif", "inter", "bodoni moda", "dm sans", "bricolage", "big shoulders", "playfair", "recursive")
PUNCT = {"’": 0x2019, "‘": 0x2018, "“": 0x201C, "”": 0x201D, "–": 0x2013, "—": 0x2014, "…": 0x2026, "·": 0x00B7, "×": 0x00D7}


def name_of(f, ids=(16, 1)):
    for i in ids:
        for r in f["name"].names:
            if r.nameID == i:
                try:
                    return r.toUnicode()
                except Exception:  # noqa: BLE001
                    pass
    return "?"


def inspect(path):
    f = TTFont(path)
    fam = name_of(f)
    sub = name_of(f, (17, 2))
    axes = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in f["fvar"].axes} if "fvar" in f else {}
    feats = sorted({fr.FeatureTag for fr in f["GSUB"].table.FeatureList.FeatureRecord}) if "GSUB" in f else []
    cmap = f.getBestCmap() or {}
    missing = [ch for ch, cp in PUNCT.items() if cp not in cmap]
    print(f"{os.path.relpath(path)}")
    print(f"   {fam} / {sub}   axes: " + (", ".join(f"{k} {v[0]:g}–{v[2]:g}" for k, v in axes.items()) if axes else "none (static)"))
    print(f"   features: {' '.join(feats) or '-'}   glyphs: {len(f.getGlyphOrder())}")
    warns = []
    low = fam.lower()
    if axes and "wght" in axes and "opsz" not in axes and any(k in low for k in OPSZ_FAMILIES):
        warns.append(f"{fam}: this file has NO opsz axis, but the family has one. Type set large (say above 40 px) falls back to the text cut: heavy and loose. Fine for small UI text; for display sizes use the `standard`/`full` file (fontsource) or the Google Fonts variable file.")
    if missing:
        warns.append("missing glyphs " + " ".join(missing) + ": real punctuation will fall back to another font")
    for w in warns:
        print("   WARN " + w)
    return len(warns)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    files = []
    for p in sys.argv[1:]:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                files += [os.path.join(root, n) for n in sorted(names) if n.lower().endswith((".woff2", ".woff", ".ttf", ".otf"))]
        else:
            files.append(p)
    n = sum(inspect(p) for p in files)
    print(f"font_check: {len(files)} file(s), {n} warning(s)")


if __name__ == "__main__":
    main()
