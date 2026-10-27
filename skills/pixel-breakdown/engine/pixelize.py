"""Turn an image into true pixel art on an exact grid: cover-crop to the target aspect, area-average down, a touch of contrast and
saturation, then a limited palette without dithering. Used for the host portrait (480x270) and pixel-style stills.
  python3 pixelize.py in.png assets/host.png [--w 480] [--h 270] [--colors 48] [--fy 0.5]
Also writes <out>_x4.png (nearest-neighbour preview at 4x) to look at."""
import sys
from PIL import Image, ImageEnhance


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


src, out = sys.argv[1], sys.argv[2]
W, H, K, fy = arg('--w', 480), arg('--h', 270), arg('--colors', 48), arg('--fy', .5)
im = Image.open(src).convert('RGB'); iw, ih = im.size; a = W / H
sw, sh = (ih * a, ih) if iw / ih > a else (iw, iw / a)
sx, sy = (iw - sw) / 2, min(ih - sh, max(0, ih * fy - sh / 2))
px = im.crop((round(sx), round(sy), round(sx + sw), round(sy + sh))).resize((W, H), Image.BOX)
px = ImageEnhance.Color(ImageEnhance.Contrast(px).enhance(1.1)).enhance(1.2)
px = px.quantize(colors=K, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
px.save(out)
px.resize((W * 4, H * 4), Image.NEAREST).save(out.rsplit('.', 1)[0] + '_x4.png')
print(out, W, H, K)
