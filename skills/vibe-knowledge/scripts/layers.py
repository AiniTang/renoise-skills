#!/usr/bin/env python3
"""生图拆层（增强档的纸拼贴、视差）：主体抠出来做前景层，原位置补洞做底层。抠图用 rembg（pip install rembg），跨平台。
  python3 layers.py <in.jpg> <输出前缀> [--shadow 24] [--grow 6]
输出：<前缀>_mask.png（灰度蒙版）、<前缀>_fg.png（带透明的主体层）、<前缀>_bg.png（补好洞的底层）。
- 投影不在蒙版里：补洞时把蒙版往投影方向（右下）拖 --shadow 像素求并集，再膨胀 --grow 像素。
- 补洞：装了 opencv-python 用 inpaint；否则用蒙版周围的中位色加一点噪声（纯色纸面反而更干净）。"""
import sys

import numpy as np
from PIL import Image, ImageFilter

from vk import arg

if len(sys.argv) < 3:
    sys.exit(__doc__)
src, pre = sys.argv[1], sys.argv[2]
shadow, grow = int(arg("--shadow", 24)), int(arg("--grow", 6))
try:
    from rembg import remove
except ImportError:
    sys.exit("缺 rembg：pip install rembg（第一次运行会下载约 170 MB 的分割模型）")

img = Image.open(src).convert("RGB")
mask = remove(img, only_mask=True).convert("L")
mask.save(f"{pre}_mask.png")
fg = img.copy()
fg.putalpha(mask)
fg.save(f"{pre}_fg.png")

m = np.asarray(mask) > 127
hole = m.copy()
for k in range(1, shadow + 1, 3):                     # 往右下拖，盖住投影
    hole[k:, k:] |= m[:-k, :-k]
hole_img = Image.fromarray((hole * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(grow * 2 + 1))
hole = np.asarray(hole_img) > 127
arr = np.asarray(img).copy()
try:
    import cv2
    bg = cv2.inpaint(arr[:, :, ::-1].copy(), (hole * 255).astype(np.uint8), 9, cv2.INPAINT_TELEA)[:, :, ::-1]
except ImportError:
    ring = np.asarray(hole_img.filter(ImageFilter.MaxFilter(31))) > 127
    ring &= ~hole
    med = np.median(arr[ring] if ring.any() else arr.reshape(-1, 3), axis=0)
    noise = np.random.default_rng(0).normal(0, 4, arr.shape)
    bg = arr.astype(np.float32)
    bg[hole] = (med + noise[hole])
    bg = np.clip(bg, 0, 255).astype(np.uint8)
Image.fromarray(bg).save(f"{pre}_bg.png")
print(f"→ {pre}_mask.png、{pre}_fg.png、{pre}_bg.png（主体占画面 {m.mean():.0%}）")
