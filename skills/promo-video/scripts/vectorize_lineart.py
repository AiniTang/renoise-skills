"""Vectorises a client's black line art / hand-lettering so it stays sharp at 4K (first used on the HEYTEA film: the
site's crops were 675–1133 px wide and the film showed them up to 2.5× larger). 4× Lanczos upsample, light blur, threshold at the anti-aliasing midpoint, contour
trace (holes kept, even-odd fill), 0.25 px simplification. Same pixel space as the PNG, so pen_order.py masks line up.

  python3 vectorize_lineart.py public/art/drinker.png public/art/drinker-main.png --out src/film/vec.json

Merges {name: {w, h, d, color}} into --out (name = file stem). Draw with <path d fill={color} fillRule="evenodd" />."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

K = 4
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("art", nargs="+")
ap.add_argument("--out", required=True)
args = ap.parse_args()
outp = Path(args.out)
res = json.load(open(outp, encoding="utf-8")) if outp.exists() else {}
for path in args.art:
    src = Path(path)
    name = src.stem
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    a = np.array(im).astype(np.float32)
    ink = (a[..., 3] / 255.0) * np.clip(1.4 - a[..., :3].mean(-1) / 255.0 * 1.4, 0, 1)
    sel = (a[..., 3] > 200) & (a[..., :3].mean(-1) < 90)
    color = "#%02x%02x%02x" % tuple(int(v) for v in np.median(a[sel][:, :3], axis=0)) if sel.any() else "#111111"
    big = cv2.resize(ink, (w * K, h * K), interpolation=cv2.INTER_LANCZOS4)
    big = cv2.GaussianBlur(big, (0, 0), K * 0.45)
    m = (big > 0.5).astype(np.uint8)
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in cs:
        if cv2.contourArea(c) < K * K * 1.5:
            continue
        ap = cv2.approxPolyDP(c, K * 0.25, True).reshape(-1, 2) / K
        parts.append("M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in ap) + "Z")
    d = "".join(parts)
    res[name] = {"w": w, "h": h, "d": d, "color": color}
    print(f"{name}: {w}x{h} color {color} contours {len(parts)} path {len(d) // 1024} KB")
json.dump(res, open(outp, "w", encoding="utf-8"))
