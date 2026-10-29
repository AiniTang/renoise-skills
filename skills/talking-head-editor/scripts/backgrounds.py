"""代码画的背景：网格底、点阵底、纸页、拉丝金属、网点颗粒。不用素材，不涉及版权。

用在 layout 的 bg 模式（人物抠像或小窗放在上面）、inset / circle / split 的圆外和四周、band 素材带的底。
每种背景返回一个 spec：{'path': PNG, 'scroll': 每秒向上滚多少像素, 'period': 循环周期像素}；PNG 比画面高一个周期，
渲染时按 y = (t × scroll) mod period 往下裁一屏，就是无缝慢速滚动。

python backgrounds.py grid rainbow -o 样子.png   单独出一张看看
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from kvlib import unit, canvas_size

# kind → {变体: 说明}；第一个变体是默认
KINDS = {
    'grid': {'white': '黑底白网格（格子 0.1 宽，带一点手绘波浪）', 'rainbow': '黑底灰细网格透彩虹光晕（暗色坐标纸，高级感用这个）',
             'neon': '黑底彩虹渐变细线网格（网感）', 'plaid': '卡其底藏青粗线波浪格纹（复古杂志感）'},
    'dots': {'static': '纯黑底灰色细点阵（卡片底，静止）', 'rainbow': '小白点阵缓慢漂移，透淡彩虹光晕'},
    'paper': {'kraft': '牛皮纸', 'cream': '米白纸'},
    'metal': {'silver': '银灰拉丝金属'},
    'black': {'plain': '纯黑'},
    'popart': {'pink': '波普网点：粉紫底上深一点的粉色网点，左下大右上小', 'red': '黑底红色网点（刺眼，别超过 2 秒）'},
    'grain': {'gray': '深灰纸纹暗角底：中灰偏暗带细颗粒，四周很重的黑色暗角，中心偏上最亮（纯文字页底）'},
    'waves': {'dark': '黑底动态波浪线：纯黑底铺满极细的深灰横向波浪线，像等高线一样缓慢流动'},
    'floor': {'floor': '透视地面：下半屏白色细线网格向远处收窄，上半纯黑，像赛博地平线',
              'tunnel': '上下隧道：上下两片透视网格向中间同一条地平线收窄，中间留一条黑带',
              'corner': '斜角走廊：两片网格斜着从一角伸向对角，上下对称，更有动势',
              'color': '彩色网格纹理：青色发光方格的透视地面，带品牌色'},
}


def _aa_lines(coord, cell, lw):
    """坐标到最近网格线的距离 → 抗锯齿线条 0~1。"""
    d = np.abs((coord + cell / 2) % cell - cell / 2)
    return np.clip(lw / 2 + 0.5 - d, 0, 1)


def _rainbow(W, H, alpha=1.0):
    """左上偏紫、中间偏粉、右下偏橙绿的低频彩色光晕。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx / W + yy / H) / 2
    stops = np.array([[150, 90, 255], [255, 110, 170], [255, 170, 80], [120, 230, 150]], np.float32)
    pos = u * (len(stops) - 1)
    i = np.clip(pos.astype(int), 0, len(stops) - 2)
    f = (pos - i)[..., None]
    return (stops[i] * (1 - f) + stops[i + 1] * f) * alpha


def _grid(W, H, variant, period):
    S = unit(W, H)
    yy, xx = np.mgrid[0:H + period, 0:W].astype(np.float32)
    if variant == 'plaid':
        cell, lw, amp = 0.12 * W, 10 * S, 8 * S
        xs, ys = xx + amp * np.sin(2 * np.pi * yy / (0.5 * W)), yy + amp * np.sin(2 * np.pi * xx / (0.45 * W))
        m = np.maximum(_aa_lines(xs, cell, lw), _aa_lines(ys, cell, lw))
        thin = np.maximum(_aa_lines(xs + cell / 2, cell, 3 * S), _aa_lines(ys + cell / 2, cell, 3 * S)) * 0.45
        m = np.maximum(m, thin)[..., None]
        bg, ink = np.array([138, 128, 112], np.float32), np.array([30, 42, 68], np.float32)
        img = bg * (1 - m) + ink * m
        img += np.random.default_rng(5).normal(0, 4, img.shape[:2])[..., None]
        return img
    cell = {'white': 0.1, 'rainbow': 0.035, 'neon': 0.06}[variant] * W
    lw = (2 if variant == 'white' else 1.4) * S
    if variant == 'white':   # 一点点手绘波浪，不像尺子画的
        amp = 2.5 * S
        xx, yy = xx + amp * np.sin(2 * np.pi * yy / (0.7 * W)), yy + amp * np.sin(2 * np.pi * xx / (0.6 * W))
    m = np.maximum(_aa_lines(xx, cell, lw), _aa_lines(yy, cell, lw))[..., None]
    if variant == 'white':
        return np.full(m.shape[:2] + (3,), 255, np.float32) * m * 0.42
    rb = _rainbow(W, H + period)
    if variant == 'rainbow':
        gray = np.full_like(rb, 64)
        line = gray * 0.65 + rb * 0.35
        glow = np.array(Image.fromarray(rb.astype(np.uint8)).resize((W // 8, (H + period) // 8)).filter(ImageFilter.GaussianBlur(20))
                        .resize((W, H + period), Image.BILINEAR), np.float32)
        yy2, xx2 = np.mgrid[0:H + period, 0:W].astype(np.float32)
        vig = np.clip(1 - (((xx2 - W * 0.2) / W) ** 2 + ((yy2 - H * 0.15) / H) ** 2) * 1.6, 0, 1)[..., None] * 0.10 \
            + np.clip(1 - (((xx2 - W * 0.85) / W) ** 2 + ((yy2 - H * 0.85) / H) ** 2) * 1.6, 0, 1)[..., None] * 0.08
        return line * m + glow * vig
    return rb * m * 0.8   # neon


def _dots(W, H, variant, period):
    S = unit(W, H)
    gap = round(0.02 * W)
    yy, xx = np.mgrid[0:H + period, 0:W].astype(np.float32)
    r = 1.1 * S if variant == 'static' else 1.4 * S
    d = np.hypot((xx % gap) - gap / 2, (yy % gap) - gap / 2)
    m = np.clip(r + 0.5 - d, 0, 1)[..., None]
    if variant == 'static':
        return np.full(m.shape[:2] + (3,), 46, np.float32) * m
    rb = _rainbow(W, H + period)
    return (np.full_like(rb, 255) * 0.7 + rb * 0.3) * m * 0.32 + rb * 0.035


def _popart(W, H, variant):
    """波普网点底（halftone_texture 的 popart_bg）：14 像素一格的圆点，从左下往右上由大变小，像印刷网版。"""
    S = unit(W, H)
    g = max(6, round(14 * S))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = np.clip(1.05 - (xx / W * 0.55 + (1 - yy / H) * 0.6), 0.25, 1.0)
    d = np.hypot((xx % g) - g / 2, ((yy + (xx // g % 2) * g / 2) % g) - g / 2)
    m = np.clip(g * 0.46 * k + 0.5 - d, 0, 1)[..., None]
    bg, dot = ((142, 78, 120), (183, 108, 154)) if variant == 'pink' else ((0, 0, 0), (179, 38, 30))
    return np.array(bg, np.float32) * (1 - m) + np.array(dot, np.float32) * m


def _metal(W, H):
    rng = np.random.default_rng(11)
    n = rng.normal(0, 1, (H // 4, W)).astype(np.float32)
    streak = np.array(Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W, H)).filter(
        ImageFilter.BoxBlur(1)), np.float32) - 128   # 横向拉长的噪声 = 拉丝纹
    rowk = np.cumsum(rng.normal(0, 1, W)).astype(np.float32)
    rowk = (rowk - rowk.mean()) / (rowk.std() + 1e-6)
    yy, xx = np.ogrid[:H, :W]
    sheen = 18 * np.sin(2 * np.pi * (yy / H * 0.8 + 0.15)) + 10 * np.cos(2 * np.pi * xx / W)
    v = 150 + streak * 0.35 + rowk[None, :] * 3 + sheen
    vig = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    v = (v * vig)[..., None]
    return np.concatenate([v * 0.98, v, v * 1.03], axis=2)


def _grain(W, H):
    """#4A4A4A 底加细颗粒（σ 8），径向暗角压到边缘约 15% 亮度，最亮处在 0.4 高。"""
    rng = np.random.default_rng(9)
    base = 74 + rng.normal(0, 8, (H, W)).astype(np.float32)
    fib = np.array(Image.fromarray(rng.normal(128, 30, (H // 3, W // 3)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) - 128
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W * 0.62), (yy - H * 0.4) / (H * 0.55))
    vig = np.clip(1 - r ** 1.6 * 0.85, 0.15, 1.0)
    return np.repeat(((base + fib * 0.12) * vig)[..., None], 3, axis=2)


def _waves(W, H, period):
    """黑底上 #262626 的 1 像素正弦叠加波浪线，行距 0.012 高；第 k 条和第 k+m 条形状一样，往上滚一个周期正好接上。"""
    from PIL import ImageDraw
    S = unit(W, H)
    gap = H * 0.012
    m = max(1, round(period / gap))
    im = Image.new('RGB', (W, H + period), (0, 0, 0))
    d = ImageDraw.Draw(im)
    xs = np.linspace(0, W, 160)
    for k in range(int((H + period) / gap) + 2):
        j = k % m
        ph, ph2 = j * 2 * np.pi / m, j * 4 * np.pi / m + 1.3
        ys = k * gap + 9 * S * np.sin(xs / W * 2 * np.pi * 1.3 + ph) + 5 * S * np.sin(xs / W * 2 * np.pi * 3.1 + ph2)
        d.line(list(zip(xs, ys)), fill=(52, 52, 52), width=max(1, int(2 * S)))
    return np.array(im, np.float32)


def _floor(W, H, variant):
    """网格平面透视成往远处收窄的地面：floor 下半屏 / tunnel 上下两片 / corner 斜向楔形 / color 青色发光格。远端渐隐到黑。"""
    import cv2
    S = unit(W, H)
    tw, th = W * 3, H
    cell = int(0.09 * W)
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    col = (14, 160, 180) if variant == 'color' else (191, 191, 191)
    m = np.maximum(_aa_lines(xx, cell, 3 * S), _aa_lines(yy, cell, 3 * S))
    tex = (np.array(col, np.float32)[None, None] * m[..., None]).astype(np.uint8)
    if variant == 'color':
        tex = np.maximum(tex, cv2.GaussianBlur(tex, (0, 0), 6 * S))
    hz = 0.5 * H
    band = 0.06 * H if variant == 'tunnel' else 0.0

    def plane(dst):
        src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
        M = cv2.getPerspectiveTransform(src, np.float32(dst))
        out = cv2.warpPerspective(tex, M, (W, H)).astype(np.float32)
        return out
    if variant in ('floor', 'color'):
        img = plane([[W * 0.42, hz], [W * 0.58, hz], [W * 2.2, H], [-W * 1.2, H]])
        fade = np.clip((yy[:H, :W] - hz) / (H * 0.3), 0, 1)[..., None]
    elif variant == 'tunnel':
        lo = plane([[W * 0.42, hz + band], [W * 0.58, hz + band], [W * 2.2, H], [-W * 1.2, H]])
        img = lo + lo[::-1]
        dist = np.abs(yy[:H, :W] - hz) - band
        fade = np.clip(dist / (H * 0.25), 0, 1)[..., None]
    else:
        lo = plane([[W * 0.75, H * 0.42], [W * 0.85, H * 0.47], [W * 1.4, H * 1.3], [-W * 1.4, H * 0.95]])
        img = lo + lo[::-1, ::-1]
        dist = np.hypot(xx[:H, :W] - W * 0.8, yy[:H, :W] - H * 0.45)
        fade = np.clip(dist / (H * 0.45), 0, 1)[..., None]
    return np.clip(img * fade, 0, 255)


def make(kind, variant=None, W=1080, H=1920, out_dir='.'):
    """生成背景 PNG，返回 spec。同一种背景在同一目录只画一次。"""
    if kind not in KINDS:
        raise SystemExit(f"背景「{kind}」不存在，可选：{'、'.join(KINDS)}")
    variant = variant or next(iter(KINDS[kind]))
    if variant not in KINDS[kind]:
        raise SystemExit(f"背景 {kind} 没有变体「{variant}」，可选：{'、'.join(KINDS[kind])}")
    scroll = {('dots', 'rainbow'): 14, ('grid', 'neon'): 10, ('waves', 'dark'): 9}.get((kind, variant), 0) * unit(W, H)
    period = round(0.02 * W) if kind == 'dots' else round(0.012 * H * 24) if kind == 'waves' else \
        round({'white': 0.1, 'rainbow': 0.035, 'neon': 0.06, 'plaid': 0.12}.get(variant, 0) * W)
    period = period if scroll else 0
    out = Path(out_dir) / f'bg_{kind}_{variant}_{W}x{H}.png'
    spec = {'path': str(out), 'scroll': scroll, 'period': period, 'kind': kind, 'variant': variant, 'dark': kind not in ('paper',) and variant != 'cream'}
    if out.exists():
        return spec
    if kind == 'paper':
        from kvlib import paper_texture
        paper_texture(out, W, H, variant)
        return spec
    if kind == 'black':
        img = np.zeros((H, W, 3), np.float32)
    elif kind == 'grid':
        img = _grid(W, H, variant, period)
    elif kind == 'dots':
        img = _dots(W, H, variant, period)
    elif kind == 'popart':
        img = _popart(W, H, variant)
    elif kind == 'grain':
        img = _grain(W, H)
    elif kind == 'waves':
        img = _waves(W, H, period)
    elif kind == 'floor':
        img = _floor(W, H, variant)
    else:
        img = _metal(W, H)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out)
    return spec


def frame_at(spec, t, H, _cache={}):
    """背景在第 t 秒（相对这一段开始）的一屏，numpy uint8 H×W×3。"""
    a = _cache.get(spec['path'])
    if a is None:
        a = _cache[spec['path']] = np.array(Image.open(spec['path']).convert('RGB'))
    y = int(t * spec['scroll']) % spec['period'] if spec['scroll'] else 0
    return a[y:y + H]


def ffmpeg_chain(spec, W, H):
    """把背景 PNG 接进 ffmpeg 滤镜：滚动的背景按时间往下裁一屏。返回追加在输入后的滤镜串。"""
    if not spec['scroll']:
        return f'scale={W}:{H}'
    return f"crop={W}:{H}:0:'mod(t*{spec['scroll']:.2f},{spec['period']})'"


def halftone(W, H, out_dir='.', gap=6, alpha=0.38):
    """网点颗粒层（透明底黑点），叠在压暗的素材底上，像印刷品的网点。"""
    out = Path(out_dir) / f'halftone_{W}x{H}.png'
    if out.exists():
        return str(out)
    S = unit(W, H)
    g = max(3, round(gap * S))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx % g) - g / 2, ((yy + (xx // g % 2) * g / 2) % g) - g / 2)
    m = np.clip(g * 0.32 + 0.5 - d, 0, 1)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = (m * alpha * 255).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(out)
    return str(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=list(KINDS))
    ap.add_argument('variant', nargs='?')
    ap.add_argument('-o', '--out', default='bg.png')
    ap.add_argument('--canvas', type=canvas_size, default=(1080, 1920), help='画布 WxH')
    a = ap.parse_args()
    W, H = a.canvas
    spec = make(a.kind, a.variant, W, H, out_dir=Path(a.out).parent)
    Image.open(spec['path']).crop((0, 0, W, H)).save(a.out)
    print(a.out, spec)


if __name__ == '__main__':
    main()
