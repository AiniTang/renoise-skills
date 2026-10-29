"""特效与转场（手法库一星第 14 批）。

逐帧画的版式（titles 的 layout，cards.title_clip 转过来）：
- shapecut     相似形状快切（match_shape_cut）：几张素材裁成同一个圆、同一圆心，零点几秒一下连续硬切，形状不变内容在变
- radial       径向模糊失焦感（radial_blur_feel）：画面糊成一片旋涡，中间两行极小、字距拉得极开的白字
- whitefade    底部白色渐隐（edge_white_fade）：画面底部四分之一由下往上从亮白渐隐，压在人物身后
- particles    粒子飘落层（particle_overlay）：starfield 银白星河粒子 / money 金额卡里飘钞票金币
- extend       取色画布羽化延伸（canvas_feather_extend）：口播往下挪，上方补一块取自墙面颜色的画布并大羽化融合，留白放字
- idwall       斜排 ID 水印底纹（id_watermark_bg）：整屏斜排博主 ID 小字，白、暗橙两组反向平移，压在人身后
- panels       半透明 PPT 面板比喻（ui_panel_metaphor_bg）：人身后几块半透明面板缓慢左移，配红色半透明巨字
- screenblend  灰度绿幕去饱和叠加（greenscreen_desaturate）：光效、烟雾这类素材去饱和，滤色叠在画面上
- swatch       磨砂色卡（color_swatch_card）：人旁边浮出磨砂玻璃卡，胶囊色条逐个弹出，下方黄色大字
- diagram      示意图分级发光标注（diagram_glow_callout）：示意图压暗，说到哪一级那一段覆盖色块、梯形光束连到标签
转场（kvlib.TRANSITIONS，effects.transition 转过来）：blocks 色块碎片擦屏、tunnel 隧道穿梭。
整屏特效（kvlib.FX）：tilt 画面歪头倾斜。
尺寸按 短边 1080 的像素值乘 S。
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from bigtype import _fit, _gray, _mask_out, _opaque, _person, _pop
from infocard import BOLD, MED, OSWALD, at_list, card_of, emoji, glow, latin, rrect, src_image
from keytext import HAND, HEAVY, blur, fade_out, frames, put, scale, with_shadow, word
from kvlib import unit, is_landscape, safe_zones, hex_rgba, is_image, probe
from annot import side_box, side_center, side_fit
from motion import Writer, ease, over, read, resize, rotate_rgba, text_img, trim

LAYOUTS = ('shapecut', 'radial', 'whitefade', 'particles', 'extend', 'idwall', 'panels', 'screenblend', 'swatch', 'diagram')


def clip(t, W, H, FPS, st, work, aroll, out):
    globals()[t['layout']](t, W, H, FPS, st, work, aroll, out)


def _fin(c, tt, dur, fin=0.12, fout=0.15, keep=False):
    k = min(1.0, tt / fin) * fade_out(tt, dur, fout)
    if keep:
        c[..., 3] = (c[..., 3] * k).astype(np.uint8)
    else:
        c[..., 3] = int(255 * k)
    return c


# ---------------------------------------------------------------- shapecut 相似形状快切
def shapecut(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    srcs = t['srcs']
    every = t.get('every', 0.3)
    D = int(W * t.get('d', 0.72))
    if is_landscape(W, H):
        D = min(D, int(H * 0.6))
    cy = H * t.get('y', 0.45)
    circles = t.get('circles') or [None] * len(srcs)
    discs = []
    for s, cc in zip(srcs, circles):
        im = src_image(s)
        if cc:   # 素材里那个圆的圆心和半径（相对宽高的比例）
            cx, cy, r = cc[0] * im.width, cc[1] * im.height, cc[2] * im.width
        else:
            cx, cy, r = im.width / 2, im.height / 2, min(im.size) / 2
        im = im.crop((int(cx - r), int(cy - r), int(cx + r), int(cy + r))).resize((D, D), Image.LANCZOS)
        m = Image.new('L', (D, D), 0)
        ImageDraw.Draw(m).ellipse([0, 0, D - 1, D - 1], fill=255)
        a = np.array(im.convert('RGBA'))
        a[..., 3] = np.array(m)
        discs.append(a)
    if is_landscape(W, H):
        # 上面读素材也用了 cy，画面圆心要重新取，不能跟着素材尺寸跑。
        cy = np.clip(H * t.get('y', 0.45), H * 0.05 + D / 2, H * 0.8 - D / 2)
    bg = np.zeros((H, W, 4), np.uint8)
    bg[..., :3] = hex_rgba(t.get('bg', '#111111'))[:3]
    bg[..., 3] = 255
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = bg.copy()
        k = int(tt / every) % len(discs)
        put(c, discs[k], (W * 0.3 if is_landscape(W, H) else W / 2), cy if is_landscape(W, H) else H * t.get('y', 0.45))
        if t.get('text'):
            put(c, with_shadow(_fit(word(t['text'], 90 * S, '#FFFFFF', HEAVY), W * (0.35 if is_landscape(W, H) else 0.9)), 6 * S, 0.6), (W * 0.73 if is_landscape(W, H) else W / 2), H * (0.45 if is_landscape(W, H) else 0.82))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- radial 径向模糊失焦感
def _zoom_blur(fr, k=0.12, n=8):
    H, W = fr.shape[:2]
    acc = fr.astype(np.float32).copy()
    for j in range(1, n):
        z = 1 + k * j / n
        big = np.array(Image.fromarray(fr).resize((int(W * z), int(H * z)), Image.BILINEAR))
        oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
        acc += big[oy:oy + H, ox:ox + W]
    return (acc / n).astype(np.uint8)


def _spin_blur(fr, ang=6, n=6):
    acc = fr.astype(np.float32).copy()
    im = Image.fromarray(fr)
    for j in range(1, n):
        acc += np.array(im.rotate(ang * j / n, resample=Image.BILINEAR))
    return (acc / n).astype(np.uint8)


def radial(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    lines = (t.get('lines') or [t.get('text', '')])[:2]
    gs = [text_img(x, H * 0.032, '#FFFFFF', fontfile=MED, spacing=int(H * 0.032 * 1.6)) for x in lines]
    if is_landscape(W, H):
        gs = [text_img(x, 64 * S, '#FFFFFF', fontfile=MED, spacing=int(8 * S)) for x in lines]
        gs = [side_fit(g, t, W, H, 0.9) for g in gs]
    frs = read(aroll, t['t0'], dur, (W // 2, H // 2), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        p = ease(tt / 0.35)
        b = _spin_blur(_zoom_blur(fr, 0.18 * p + 0.01), 8 * p + 0.1)
        c = _opaque(resize(b, W, H))
        c[..., :3] = (c[..., :3] * (1 - 0.25 * p)).astype(np.uint8)
        for j, g in enumerate(gs):
            put(c, g, (side_center(t, W, H)[0] if is_landscape(W, H) else W / 2), H * 0.47 + j * H * 0.06, ease((tt - 0.3) / 0.4))
        w.put(_fin(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- whitefade 底部白色渐隐
def whitefade(t, W, H, FPS, st, work, aroll, out):
    import matte
    dur, n = frames(t, FPS)
    hr = t.get('h', 0.3)
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = hex_rgba(t.get('color', '#FFFFFF'))[:3]
    yy = np.arange(H, dtype=np.float32)
    g[..., 3] = (np.clip((yy - H * (1 - hr)) / (H * hr), 0, 1) ** 1.3 * 255 * t.get('alpha', 0.8))[:, None].astype(np.uint8)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = g.copy()
        _mask_out(c, a, t.get('behind', 0.7))   # 人身上透一层淡白，像海报底部打光
        w.put(_fin(c, tt, dur, 0.4, 0.3, keep=True))
    w.close()


# ---------------------------------------------------------------- particles 粒子飘落层
PARTICLE_VARIANTS = {
    'starfield': '星河粒子：人物周围飘一层银白闪烁颗粒，结尾祝福语从颗粒里飘入',
    'money': '卡内撒钱：金额卡里飘钞票和金币，只在卡片框内显示，出框被裁掉',
}


def particles(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'starfield')
    rng = np.random.default_rng(int(t['t0'] * 100) + 7)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'starfield':
        N = 220
        x0, y0 = rng.uniform(0, W, N), rng.uniform(-H * 0.2, H, N)
        vy, sz, ph = rng.uniform(0.04, 0.12, N) * H, rng.uniform(3, 9, N) * S, rng.uniform(0, 6.28, N)
        msg = with_shadow(_fit(word(t['text'], 96 * S, '#FFFFFF', HEAVY), W * 0.86), 10 * S, 0.5) if t.get('text') else None
        if is_landscape(W, H) and msg is not None:
            msg = side_fit(msg, t, W, H, 0.9)
        for i in range(n):
            tt = i / FPS
            im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            ys = (y0 + vy * tt) % (H * 1.2) - H * 0.1
            xs = x0 + np.sin(tt * 1.3 + ph) * 12 * S
            tw = 0.55 + 0.45 * np.sin(tt * 6 + ph)
            for x, y, s, a in zip(xs, ys, sz, tw):
                d.ellipse([x - s, y - s, x + s, y + s], fill=(235, 240, 255, int(220 * a)))
            c = np.array(im.filter(ImageFilter.GaussianBlur(0.8)))
            c = np.maximum(c, np.array(im))
            if is_landscape(W, H):
                x0, y0, x1, y1 = safe_zones(W, H)['face']
                c[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W), 3] = 0
                c[int(H * 0.8):, :, 3] = 0
            if msg is not None:
                p = ease((tt - 0.4) / 0.6)
                put(c, msg, (side_center(t, W, H)[0] if is_landscape(W, H) else W / 2), H * (0.5 if is_landscape(W, H) else 0.7) + (1 - p) * 40 * S, p)
            w.put(_fin(c, tt, dur, 0.4, 0.3, keep=True))
        w.close()
        return
    cw, ch = int(W * (0.22 if is_landscape(W, H) else 0.78)), int(H * 0.26)
    card = rrect(cw, ch, 30 * S, '#14361F', '#F2C94C', int(4 * S))
    num = with_shadow(_fit(word(t.get('text', '¥10,000'), 150 * S, '#F2C94C', latin(t.get('text', '¥10,000'), OSWALD)), cw * 0.8), 8 * S, 0.6)
    sprites = [emoji('Dollar banknote', 90 * S), emoji('Coin', 70 * S), emoji('Money with wings', 90 * S)]
    N = 18
    px, py0 = rng.uniform(0, cw, N), rng.uniform(-ch, ch, N)
    vy, rot, kind = rng.uniform(0.25, 0.5, N) * ch, rng.uniform(-90, 90, N), rng.integers(0, 3, N)
    m = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=int(30 * S), fill=255)
    mask = np.array(m, np.float32) / 255
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        g = card.copy()
        layer = np.zeros_like(g)
        for x, y, s_, r, k in zip(px, py0, vy, rot, kind):
            yy = (y + s_ * tt) % (ch * 1.4) - ch * 0.2
            put(layer, rotate_rgba(sprites[k], r + tt * 60), x, yy)
        layer[..., 3] = (layer[..., 3] * mask).astype(np.uint8)
        over(g, layer, 0, 0)
        put(g, num, cw / 2, ch / 2)
        p = ease(tt / 0.3, 'out')
        put(c, scale(with_shadow(g, 14 * S, 0.5, dy=int(8 * S)), 0.85 + 0.15 * p), (side_center(t, W, H)[0] if is_landscape(W, H) else W / 2), H * t.get('y', 0.48 if is_landscape(W, H) else 0.64), p)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- extend 取色画布羽化延伸
def extend(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return _landscape_extend(t, W, H, FPS, aroll, out)
    S = unit(W, H)
    dur, n = frames(t, FPS)
    dy = int(H * t.get('shift', 0.3))
    fe = int(H * 0.15)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    col = None
    title = with_shadow(_fit(word(t['text'], 100 * S, t.get('color', '#2A2A2A'), HEAVY), W * 0.86), 4 * S, 0.15) if t.get('text') else None
    sub = word(t['sub'], 44 * S, '#555555', MED) if t.get('sub') else None
    ramp = np.clip(np.arange(fe, dtype=np.float32) / fe, 0, 1)[:, None, None]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        if col is None:   # 墙面色：画面顶部一条的中位数
            col = np.median(fr[: int(H * 0.06)].reshape(-1, 3), axis=0)
        p = ease(tt / 0.4, 'out')
        d = int(dy * p)
        c = np.empty((H, W, 3), np.float32)
        c[:] = col
        if d:
            c[d:] = fr[:H - d]
            band = c[d:d + fe]
            c[d:d + fe] = col * (1 - ramp) + band * ramp
        else:
            c[:] = fr
        c = _opaque(c.astype(np.uint8))
        if title is not None:
            put(c, title, W / 2, d * 0.5, ease((tt - 0.3) / 0.3))
            if sub is not None:
                put(c, sub, W / 2, d * 0.5 + title.shape[0] / 2 + 36 * S, ease((tt - 0.45) / 0.3))
        w.put(_fin(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- idwall 斜排 ID 水印底纹
def _id_tile(text, W, H, S, color, alpha):
    f_img = text_img(f'{text}    ', H * 0.02, color, fontfile=HAND)
    f_img = trim(f_img)
    tw = f_img.shape[1] + int(30 * S)
    lh = int(H * 0.04)
    L = int(W * 2.2)
    rows = int(H * 1.6 / lh)
    tile = np.zeros((rows * lh, L, 4), np.uint8)
    for r in range(0, rows, 2):
        off = (r // 2 % 2) * tw // 2
        for x in range(-tw + off, L, tw):
            over(tile, f_img, x, r * lh, alpha)
    return tile, tw


def idwall(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    text = t.get('text', '@口播剪辑研究所')
    a1, tw = _id_tile(text, W, H, S, '#FFFFFF', 0.4)
    a2, _ = _id_tile(text, W, H, S, '#8A4A20', 0.4)
    a2 = np.roll(a2, int(H * 0.03), axis=0)
    sp = W * 0.02
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        big = np.zeros((int(H * 1.6) // 1, int(W * 1.6), 4), np.uint8)
        ox = int(sp * tt) % tw
        over(big, a1, -tw + ox, 0)
        over(big, a2, -ox, 0)
        r = rotate_rgba(big, 10)
        c = np.zeros((H, W, 4), np.uint8)
        put(c, r, W / 2, H / 2)
        _mask_out(c, a)
        if is_landscape(W, H):
            c[int(H * 0.8):, :, 3] = 0
        w.put(_fin(c, tt, dur, 0.4, 0.3, keep=True))
    w.close()


# ---------------------------------------------------------------- panels 半透明 PPT 面板比喻
def panels(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    rng = random.Random(4)
    heads = t.get('items') or ['核心优势', '解决方案', '市场分析', '团队介绍', '发展规划', '数据亮点']
    fr0 = next(read(aroll, t['t0'], 1 / FPS, (W // 4, H // 4), FPS))
    light = fr0[: H // 8].mean() > 150   # 浅色墙前白面板看不见，换深灰
    fill, edge, ink, bar_c = ('#33333366', '#33333399', '#333333', '#33333388') if light else ('#FFFFFF66', '#FFFFFF99', '#FFFFFF', '#FFFFFF88')
    ps = []
    for k, hd in enumerate(heads[:6]):
        pw, ph = int(W * rng.uniform(0.34, 0.46)), int(H * rng.uniform(0.12, 0.2))
        if is_landscape(W, H):
            pw, ph = int(W * 0.22), int(H * 0.17)
        g = rrect(pw, ph, 10 * S, fill, edge, int(2 * S))
        over(g, word(hd, 40 * S, ink, BOLD), 22 * S, 18 * S, 0.9)
        for j in range(3):
            bar = rrect(pw * rng.uniform(0.4, 0.8), 12 * S, 6 * S, bar_c)
            over(g, bar, 22 * S, 80 * S + j * 26 * S)
        if is_landscape(W, H):
            x0, _, x1, _ = side_box(t, W, H, 'left' if k % 2 == 0 else 'right')
            ps.append((g, x1 - pw, H * (0.16 + 0.2 * (k // 2))))
            continue
        ps.append((g, W * (0.05 + 0.5 * (k % 2)) + rng.uniform(-30, 30) * S, H * (0.06 + 0.15 * k)))
    giant = word(t.get('text', '模板'), H * 0.3, '#C4161C', HEAVY)
    if is_landscape(W, H):
        giant = side_fit(giant, t, W, H, 0.85)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        dx = -W * 0.02 * tt / 3
        if is_landscape(W, H):
            x0, _, x1, _ = side_box(t, W, H)
            dx = max(dx, -(x1 - x0 - int(W * 0.22)))
        for g, x, y in ps:
            over(c, g, x + dx, y, ease((tt - 0.05) / 0.4))
        put(c, giant, (side_center(t, W, H)[0] if is_landscape(W, H) else W / 2), H * 0.42, 0.5 * ease((tt - 0.2) / 0.4))
        _mask_out(c, a)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- screenblend 灰度绿幕去饱和叠加
def screenblend(t, W, H, FPS, st, work, aroll, out):
    dur, n = frames(t, FPS)
    fx = read(t['src'], t.get('src_in', 0), dur, (W, H), FPS, t.get('crop'))
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    k = t.get('opacity', 1.0)
    als = None
    if is_landscape(W, H):
        import matte
        als = matte.cutouts(aroll, t['t0'], dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        a = next(frs).astype(np.float32) / 255
        b = _gray(next(fx)).astype(np.float32) / 255 * k * min(1.0, tt / 0.2) * fade_out(tt, dur, 0.2)
        if als is not None:
            # 横屏烟雾和源素材里的字压到人后，下方也给字幕留白。
            b *= (1 - next(als))[..., None]
            b[int(H * 0.82):] = 0
        c = 1 - (1 - a) * (1 - b)
        w.put(_opaque((c * 255).astype(np.uint8)))
    w.close()


# ---------------------------------------------------------------- swatch 磨砂色卡
def swatch(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    cols = t.get('colors') or ['#F2E9B8', '#F0A21A', '#BFE3F0']
    cw, ch = int(W * 0.44), int(H * 0.36)
    cx, cy = W * t.get('x', 0.72), H * t.get('y', 0.5)
    if is_landscape(W, H):
        cw, ch = int(W * 0.21), int(H * 0.3)
        cx, cy = side_center(t, W, H)
    big = with_shadow(word(t.get('text', '≤3 种颜色'), 76 * S, '#FFD84A', HEAVY, stroke=int(4 * S), stroke_color='#3A2A00'), 6 * S, 0.5)
    arc = word(t.get('note', '配色越少越高级'), 30 * S, '#FFFFFF', BOLD)
    if is_landscape(W, H):
        big = side_fit(big, t, W, H, 0.9)
        arc = side_fit(arc, t, W, H, 0.9)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3, 'out')
        y = cy + (1 - p) * 80 * S
        x0, y0 = int(cx - cw / 2), int(y - ch / 2)
        reg = Image.fromarray(fr).crop((x0, y0, x0 + cw, y0 + ch)).filter(ImageFilter.GaussianBlur(20 * S))
        g = np.array(reg.convert('RGBA'), np.float32)
        g[..., :3] = g[..., :3] * 0.7 + 255 * 0.3
        g = g.astype(np.uint8)
        m = Image.new('L', (cw, ch), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=int(28 * S), fill=255)
        g[..., 3] = np.array(m)
        for k, col in enumerate(cols[:4]):
            q = (tt - 0.35 - 0.1 * k) / 0.1
            if q <= 0:
                continue
            bar = rrect(cw * 0.14, ch * 0.5, cw * 0.07, col)
            put(g, scale(bar, _pop(min(1.0, q))), cw * (0.2 + 0.2 * k), ch * 0.42)
            put(g, rrect(cw * 0.1, cw * 0.1, cw * 0.05, col), cw * (0.2 + 0.2 * k), ch * 0.82, min(1.0, q))
        put(c, with_shadow(g, 14 * S, 0.35, dy=int(6 * S)), cx, y, p)
        q = ease((tt - 0.7) / 0.25, 'out')
        put(c, big, cx, y + ch / 2 + 70 * S, q)
        put(c, arc, cx, y - ch / 2 - 40 * S, q)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- diagram 示意图分级发光标注
def diagram(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    im = src_image(t['src'], t.get('crop'))
    k = min(W * (0.56 if is_landscape(W, H) else 0.9) / im.width, H * 0.6 / im.height)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    dw, dh = im.size
    ox, oy = (W - dw) / 2, H * t.get('y', 0.42) - dh / 2
    if is_landscape(W, H):
        ox, oy = W * 0.07, H * 0.44 - dh / 2
    base = np.array(im.convert('RGBA'))
    dim = base.copy()
    dim[..., :3] = (dim[..., :3] * 0.45).astype(np.uint8)
    stages = t.get('stages') or []
    cols = t.get('colors') or ['#F4A6B5', '#F2E58A']
    times = at_list(t, len(stages), 1.2, 0.4)
    layers = []
    for j, sg in enumerate(stages):
        col = hex_rgba(cols[j % len(cols)])
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        pts = [(ox + x * dw, oy + y * dh) for x, y in sg['poly']]
        d.polygon(pts, fill=col[:3] + (120,), outline=(255, 255, 255, 150))
        lab_y = H * (0.3 + 0.12 * j if is_landscape(W, H) else 0.74 + 0.07 * j)
        cx = sum(p[0] for p in pts) / len(pts)
        ys = [p[1] for p in pts]
        if is_landscape(W, H):
            d.line([(max(x for x, _ in pts), sum(ys) / len(ys)), (W * 0.68, lab_y)], fill=col[:3] + (150,), width=max(2, int(3 * S)))
        else:
            d.polygon([(cx - 30 * S, max(ys)), (cx + 30 * S, max(ys)), (W * 0.5 + W * 0.09, lab_y - 22 * S), (W * 0.5 - W * 0.09, lab_y - 22 * S)],
                  fill=col[:3] + (110,))
        L = glow(np.array(L), 8 * S, '#FFFFFF', 0.25)
        lab = rrect(W * (0.27 if is_landscape(W, H) else 0.34), H * (0.075 if is_landscape(W, H) else 0.05), 10 * S, '#1A1A1AE6')
        put(lab, _fit(word(sg.get('label', ''), 48 * S, '#%02X%02X%02X' % col[:3], HEAVY), W * (0.25 if is_landscape(W, H) else 0.3)), lab.shape[1] / 2, lab.shape[0] / 2)
        layers.append((L, lab, lab_y))
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        c[..., :3] = 12
        over(c, dim, ox, oy)
        kk = max((j for j, a in enumerate(times) if tt >= a), default=-1)
        if kk >= 0:
            L, lab, ly = layers[kk]
            q = ease((tt - times[kk]) / 0.2)
            pg = (L.shape[0] - H) // 2
            over(c, L[pg:pg + H, pg:pg + W] if pg > 0 else L, 0, 0, q)
            put(c, lab, W * 0.81 if is_landscape(W, H) else W / 2, ly, q)
        w.put(_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- 转场与整屏特效（effects.transition / effects.apply 转过来）
def blocks_mov(tr, W, H, FPS, out):
    """色块碎片擦屏：random 一堆大小不一的橙红、深色矩形 0.15 秒内铺满整屏，切点后按随机顺序散掉露出下一段；bars 黑色竖条随机升起盖满再落下。"""
    from kvlib import tr_window
    a0, d = tr_window(tr)
    t = float(tr['t'])
    v = tr.get('variant', 'random')
    rng = random.Random(int(t * 100))
    n = max(2, round(d * FPS))
    cols = [hex_rgba(x)[:3] for x in (tr.get('colors') or ['#FF4A1C', '#1E1714'])]
    if v == 'bars':
        k = 14
        bars = [(W * j / k, rng.uniform(0, 0.5)) for j in range(k)]
    else:
        rects = []
        gx, gy = 5, 9
        for yy in range(gy):
            for xx in range(gx):
                rects.append((W * xx / gx, H * yy / gy, W / gx + 2, H / gy + 2, rng.random(), rng.random(), cols[rng.randrange(len(cols))]))
    w = Writer(out, W, H, FPS, alpha=True)
    tin = max(0.05, t - a0)
    tout = max(0.05, a0 + d - t)
    for i in range(n):
        tt = a0 + i / FPS
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        if v == 'bars':
            for x, ph in bars:
                p = (tt - a0) / tin if tt < t else 1 - (tt - t) / tout
                h = H * min(1.0, max(0.0, p * 1.5 - ph))
                dr.rectangle([x, H - h, x + W / 14 + 1, H], fill=(10, 10, 10, 255))
        else:
            for x, y, w_, h_, r_in, r_out, col in rects:
                on = (tt - a0) / tin >= r_in * 0.9 if tt < t else (tt - t) / tout < r_out
                if on:
                    dr.rectangle([x, y, x + w_, y + h_], fill=col + (255,))
        w.put(np.array(im))
    w.close()
    return out


def tunnel_mov(tr, W, H, FPS, out):
    """隧道穿梭的底：青色放射光柱从中心往外冲，越往外越快越亮。"""
    from kvlib import tr_window
    a0, d = tr_window(tr)
    n = max(2, round(d * FPS))
    rng = np.random.default_rng(int(float(tr['t']) * 100))
    N = 90
    ang, sp, ph = rng.uniform(0, 2 * np.pi, N), rng.uniform(0.6, 1.4, N), rng.uniform(0, 1, N)
    col = hex_rgba(tr.get('color', '#1E6E8C'))[:3]
    R = math.hypot(W, H) / 2
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS / d
        im = Image.new('RGBA', (W, H), (4, 10, 14, 255))
        dr = ImageDraw.Draw(im)
        for a, s, p in zip(ang, sp, ph):
            r0 = ((p + tt * s * 1.6) % 1) ** 2 * R
            r1 = r0 + R * 0.12 * (0.3 + r0 / R)
            dr.line([(W / 2 + math.cos(a) * r0, H / 2 + math.sin(a) * r0), (W / 2 + math.cos(a) * r1, H / 2 + math.sin(a) * r1)],
                    fill=col + (255,), width=max(2, int(6 * r0 / R * unit(W, H) + 2)))
        a_ = np.array(im.filter(ImageFilter.GaussianBlur(2)))
        a_[..., :3] = np.maximum(a_[..., :3], np.array(im)[..., :3])
        w.put(a_)
    w.close()
    return out


def transition(fc, cur, tr, ti, add_input, W, H, FPS, work):
    from effects import _overlay_clip
    from kvlib import tr_window
    a0, d = tr_window(tr)
    t = float(tr['t'])
    tag = f'tx{ti}'
    if tr['type'] == 'blocks':
        mov = blocks_mov(tr, W, H, FPS, f'{work}/{tag}.mov')
        return _overlay_clip(fc, cur, add_input, mov, a0, a0 + d, tag)
    # tunnel：切点前后先铺隧道光柱，下一段从中心 20% 冲到满屏
    zd = max(0.1, a0 + d - t)
    zz = f"(0.2+0.8*pow(clip(t/{zd:.3f},0,1),2))"   # 截出来的这一小段时间从 0 起
    fc.append(f"{cur}split[{tag}m0][{tag}s]")   # 小窗从没叠光柱的画面里取
    mov = tunnel_mov(tr, W, H, FPS, f'{work}/{tag}.mov')
    cur = _overlay_clip(fc, f'[{tag}m0]', add_input, mov, a0, a0 + d, tag + 'u')
    fc.append(f"{cur}null[{tag}m]")
    fc.append(f"[{tag}s]trim=start={t:.3f}:duration={zd:.3f},setpts=PTS-STARTPTS,"
              f"scale=w='trunc({W}*{zz}/2)*2':h='trunc({H}*{zz}/2)*2':eval=frame,setpts=PTS+{t:.3f}/TB[{tag}z]")
    fc.append(f"[{tag}m][{tag}z]overlay=x='(W-w)/2':y='(H-h)/2':enable='between(t,{t:.3f},{t + zd:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


def tilt_fx(fc, cur, f, tag, W, H):
    """画面歪头倾斜：0.3 秒内整屏转到 angle（默认 -10 度）并放大到 1.1 倍免得露黑角，back 写了就最后 0.3 秒转回来。"""
    from effects import _branch
    t0, t1 = float(f['t0']), float(f['t1'])
    d = t1 - t0
    ang = f.get('angle', -10)
    p = f"(1-pow(1-clip(t/0.3,0,1),3))"
    if f.get('back'):
        p = f"{p}*clip(({d:.3f}-t)/0.3,0,1)"
    z = f.get('zoom', 1.1)
    if is_landscape(W, H):
        # 横屏斜转时，上下两角需要更多余量；按转角算铺满画布的最小倍率。
        ratio = max(W / H, H / W)
        a = min(math.radians(abs(ang)), math.atan(ratio))
        z = max(z, math.cos(a) + ratio * math.sin(a) + 0.01)
    m, b = _branch(fc, cur, tag, t0, t1, f"scale=iw*{z}:ih*{z},rotate='{ang}*PI/180*{p}':ow={W}:oh={H}:c=black")
    fc.append(f"{m}{b}overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


def _landscape_extend(t, W, H, FPS, aroll, out):
    """横屏把画面让到右边，墙面色补左栏，标题与画面并排。"""
    S = unit(W, H)
    dur, n = frames(t, FPS)
    title = _fit(with_shadow(word(t['text'], 90 * S, t.get('color', '#2A2A2A'), HEAVY), 4 * S, 0.15), W * 0.25) if t.get('text') else None
    sub = _fit(word(t['sub'], 36 * S, '#555555', MED), W * 0.25) if t.get('sub') else None
    w = Writer(out, W, H, FPS, alpha=True)
    for i, fr in enumerate(read(aroll, t['t0'], dur, (W, H), FPS)):
        tt = i / FPS
        p = ease(tt / 0.4, 'out')
        bg = np.median(fr[:int(H * 0.06)].reshape(-1, 3), axis=0).astype(np.uint8)
        c = np.empty((H, W, 4), np.uint8)
        c[..., :3], c[..., 3] = bg, 255
        k = 1 - 0.38 * p
        shot = _opaque(resize(fr, int(W * k), int(H * k)))
        put(c, shot, W * (0.5 + 0.14 * p), H * 0.44)
        if title is not None:
            put(c, title, W * 0.19, H * 0.4, ease((tt - 0.3) / 0.3))
        if sub is not None:
            put(c, sub, W * 0.19, H * 0.54, ease((tt - 0.45) / 0.3))
        w.put(_fin(c, tt, dur, 0.01))
    w.close()
