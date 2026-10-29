"""重点字网感（手法库第 6 批）：逐帧合成的重点字，titles 的 layout 写这些名字，cards.title_clip 转到这里渲成整屏透明 .mov。

- slam      巨字砸屏盖章（kw_slam_stamp）：红色毛笔字从几倍大一下砸下来、斜着落定，底下画面虚化压暗
- burst     速度线爆发重点字（kw_speedline_burst）：四周炸出抖动的集中线，中间一行巨字，前半实心后半空心
- knockout  后词撞飞前词（kw_crash_knockout）：新词从右边冲进来，碰到旧词那一帧把旧词撞出画面
- crack     主词裂开插入副句（kw_split_insert）：巨字从中间裂开，缝里插进一行小字
- swap      引导词换成重点词（kw_word_replace）：同一位置先出引导词，再换成更大、换色的重点词
- finish    花字质感（text_finish_fx）：横纹拖影、网点投影、霓虹空心、渐变填充、故障错位
- patch     纸片垫底字（paper_patch_text）：牛皮纸胶带标题、撕纸片、每字一块彩纸
- note      主标题旁小补充（title_aside_note）：弧形俏皮话或便利贴小标签，主标题出来后 0.3 秒弹进来
- qmark     引号括号框概念词（concept_quote_marks）：概念词外面加比字还大的括号或引号
- scribble  红色手写数字批注（handwritten_note）：红色手写数字从左往右写出来，可带白色圆角框
- icons     图标配并列词（icon_keyword_list）：并列的几个词各配一个 3D 图标，说到哪个出哪个
- recframe  录制边框（voice_fx_swap 的扩音器段自动加）：四角白色取景框、左上角闪烁的红点 REC
尺寸按 短边 1080 的像素值乘 S 换算；人脸大约在画面高 10%~47%，字默认放胸口（0.55~0.70）或整屏压暗后居中。
"""
import random
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fonts import FONTS
from kvlib import unit, hex_rgba, is_landscape, safe_zones
from motion import Writer, _torn_mask, bg_frames, ease, over, rotate_rgba, text_img, trim

BRUSH = FONTS / 'MaShanZheng-Regular.ttf'      # 毛笔
HAND = FONTS / 'ZhiMangXing-Regular.ttf'       # 行书手写
HEAVY = FONTS / 'SourceHanSansCN-Heavy.otf'    # 粗黑
ICON_CACHE = Path.home() / '.cache' / 'koubo' / 'icons'

LAYOUTS = ('slam', 'burst', 'knockout', 'crack', 'swap', 'finish', 'patch', 'note', 'qmark', 'scribble', 'icons', 'recframe')


def clip(t, W, H, FPS, st, work, aroll, out):
    {'slam': slam, 'burst': burst, 'knockout': knockout, 'crack': crack, 'swap': swap, 'finish': finish, 'patch': patch,
     'note': note, 'qmark': qmark, 'scribble': scribble, 'icons': icons, 'recframe': recframe}[t['layout']](t, W, H, FPS, st, work, aroll, out)


# ---------------------------------------------------------------- 小工具
def side_box(t, W, H, side=None, center=True):
    """横屏文字放两侧，边上留五分空白，底下留给字幕。"""
    zones = safe_zones(W, H)['text']
    explicit = side is not None
    side = side or t.get('side') or ('right' if int(t.get('t0', 0) / 4) % 2 else 'left')
    if not explicit and t.get('x') is not None and not t.get('side'):
        side = 'right' if t['x'] > 0.5 else 'left'
    l, top, r, bot = zones[-1 if side == 'right' else 0]
    pad = 12 * unit(W, H)
    l, r = max(l, 0.05) * W + pad, min(r, 0.95) * W - pad
    if center and not explicit and t.get('x') is not None:
        half_min = min((r - l) / 2, 108 * unit(W, H))
        cx = min(r - half_min, max(l + half_min, t['x'] * W))
        half = min(cx - l, r - cx)
        l, r = cx - half, cx + half
    return l, top * H + pad, r, bot * H - pad


def side_anchor(t, W, H):
    l, top, r, bot = side_box(t, W, H)
    return (l + r) / 2, min(bot - H * 0.12, max(top + H * 0.12, H * t.get('y', 0.45)))


def fit_sprite(a, maxw, maxh):
    """连描边和投影一起缩进文字区，不拉伸字形。"""
    k = min(1.0, maxw / a.shape[1], maxh / a.shape[0])
    return scale(a, k) if k < 1 else a


class SideWriter(Writer):
    """侧栏动效只在自己的留白里运动，冲入和撞飞也不经过脸。"""
    def __init__(self, out, W, H, FPS, t):
        super().__init__(out, W, H, FPS, alpha=True)
        self.box = tuple(map(int, side_box(t, W, H)))

    def put(self, c):
        l, top, r, bot = self.box
        c[:top, :, 3] = 0
        c[bot:, :, 3] = 0
        c[:, :l, 3] = 0
        c[:, r:, 3] = 0
        super().put(c)


def _clamp(p):
    return min(1.0, max(0.0, p))


def eback(p, c=1.70158):
    p = _clamp(p)
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def scale(a, k):
    k = max(0.01, k)
    return np.array(Image.fromarray(a, 'RGBA').resize((max(1, int(a.shape[1] * k)), max(1, int(a.shape[0] * k))), Image.BILINEAR))


def blur(a, r):
    return np.array(Image.fromarray(a, 'RGBA').filter(ImageFilter.GaussianBlur(r))) if r > 0.3 else a


def vblur(a, r):
    """纵向运动模糊：只沿上下方向糊开。"""
    if r < 0.5:
        return a
    k = int(r) * 2 + 1
    f = a.astype(np.float32)
    pad = np.pad(f, ((k // 2, k // 2), (0, 0), (0, 0)))
    c = np.cumsum(pad, axis=0)
    c = np.vstack([np.zeros((1,) + c.shape[1:], np.float32), c])
    return ((c[k:] - c[:-k]) / k).astype(np.uint8)


def put(canvas, a, cx, cy, opacity=1.0):
    """以中心点贴图。"""
    over(canvas, a, cx - a.shape[1] / 2, cy - a.shape[0] / 2, opacity)


def word(text, size, color, fontfile=HEAVY, stroke=0, stroke_color='#000000', spacing=0):
    return trim(text_img(text, size, color, fontfile=fontfile, stroke=stroke, stroke_color=stroke_color, pad=4 + stroke, spacing=spacing))


def fit_word(text, size, maxw, color, fontfile=HEAVY, **kw):
    a = word(text, size, color, fontfile, **kw)
    return word(text, size * maxw / a.shape[1], color, fontfile, **kw) if a.shape[1] > maxw else a


def shadow(a, r, alpha=0.55, dx=0, dy=0):
    s = np.zeros((a.shape[0] + 2 * int(r * 2) + abs(dy), a.shape[1] + 2 * int(r * 2) + abs(dx), 4), np.uint8)
    p = int(r * 2)
    s[p + max(dy, 0):p + max(dy, 0) + a.shape[0], p + max(dx, 0):p + max(dx, 0) + a.shape[1], 3] = (a[..., 3] * alpha).astype(np.uint8)
    return blur(s, r), p


def with_shadow(a, r, alpha=0.55, dy=0):
    s, p = shadow(a, r, alpha, dy=dy)
    over(s, a, p, p)
    return s


def rough(a, seed, amount=0.35):
    """毛笔、盖章的粗糙边：边缘和笔画里随机掉墨。"""
    rng = np.random.default_rng(seed)
    h, w = a.shape[:2]
    n = Image.fromarray((rng.random((max(1, h // 3), max(1, w // 3))) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    n = np.array(n.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    out = a.copy()
    out[..., 3] = (a[..., 3] * np.clip((n - amount * 0.55) / 0.25, 0, 1)).astype(np.uint8)
    return out


def dimmer(W, H, alpha):
    c = np.zeros((H, W, 4), np.uint8)
    c[..., 3] = int(255 * _clamp(alpha))
    return c


def blurred_bg(aroll, t, W, H, FPS, n, work, dim=0.15):
    """口播画面虚化压暗（bg_frames 已压到 55%，dim 再往下压），逐帧给砸屏这类整屏重包装做底。"""
    for fr in bg_frames('blur', W, H, FPS, n, work, aroll, t['t0']):
        a = np.dstack([(fr[..., :3].astype(np.float32) * (1 - dim)).astype(np.uint8), np.full(fr.shape[:2], 255, np.uint8)])
        yield a


def frames(t, FPS):
    dur = t['t1'] - t['t0']
    n = max(1, round(dur * FPS))
    return dur, n


def fade_out(tt, dur, d=0.18):
    return 1 - _clamp((tt - (dur - d)) / d)


# ---------------------------------------------------------------- slam 巨字砸屏盖章
SLAM_VARIANTS = {
    'char': '单个巨字：一两个红色毛笔字占画面高四成五，从 1.4 倍砸下来斜着落定',
    'stamp': '痛点词盖章：两到六个字的红色毛笔字加印章框，从 4 倍大砸下来，像盖了个章',
}


def slam(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'stamp')
    red = t.get('color', '#C8141E')
    text = t['text']
    if v == 'char':
        a = word(text, H * 0.40, red, BRUSH)
        a = trim(a) if a.shape[1] <= W * 0.9 else word(text, H * 0.40 * W * 0.9 / a.shape[1], red, BRUSH)
        k0, tilt = 1.4, 8
    else:
        g = fit_word(text, 210 * S, W * 0.72, red, BRUSH)
        pad = int(46 * S)
        bw, bh = g.shape[1] + 2 * pad, g.shape[0] + 2 * pad
        im = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([6 * S, 6 * S, bw - 6 * S, bh - 6 * S], radius=int(18 * S), outline=hex_rgba(red), width=int(13 * S))
        im.alpha_composite(Image.fromarray(g), (pad, pad))
        a = np.array(im)
        k0, tilt = 4.0, 12
    a = rough(a, int(t['t0'] * 100))
    a = rotate_rgba(a, tilt)   # 逆时针歪一点，像随手盖上去
    a = with_shadow(a, 10 * S, 0.45, dy=int(8 * S))
    dur, n = frames(t, FPS)
    cx, cy = W * t.get('x', 0.5), H * t.get('y', 0.5)
    if is_landscape(W, H):
        a = fit_sprite(a, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) / 1.15, H * 0.4)
    hit = t.get('slam_s', 0.16)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    bg = (np.zeros((H, W, 4), np.uint8) for _ in range(n)) if is_landscape(W, H) else blurred_bg(aroll, t, W, H, FPS, n, work, 0.15)
    for i in range(n):
        tt = i / FPS
        canvas = next(bg)
        e = fade_out(tt, dur)
        canvas[..., 3] = (canvas[..., 3] * min(1.0, tt / 0.1) * e).astype(np.uint8)
        p = _clamp(tt / hit)
        k = k0 + (1 - k0) * ease(p, 'out')
        if tt > hit:   # 落定后轻微回弹再定住
            k = 1 + 0.035 * np.sin(min(1.0, (tt - hit) / 0.2) * np.pi)
        spr = scale(a, min(k, 1.15) if is_landscape(W, H) else k)
        if i < 3:
            spr = blur(spr, 6 * S * (3 - i))
        sx = sy = 0
        if hit <= tt < hit + 0.15:   # 砸下那一下震三帧
            r = random.Random(i)
            sx, sy = r.uniform(-1, 1) * 12 * S, r.uniform(-1, 1) * 12 * S
        put(canvas, spr, cx + sx, cy + sy, min(1.0, 0.4 + p) * e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- burst 速度线爆发重点字
def _speedlines(W, H, seed, S, hole=0.36):
    r = random.Random(seed)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    R = (W ** 2 + H ** 2) ** 0.5 / 2
    for _ in range(r.randint(46, 60)):
        ang = r.uniform(0, 2 * np.pi)
        inner = R * r.uniform(hole + 0.12, hole + 0.42)
        wid = r.uniform(0.006, 0.02)
        ux, uy = np.cos(ang), np.sin(ang)
        px, py = -uy, ux
        far = R * 1.05
        d.polygon([(cx + ux * inner, cy + uy * inner),
                   (cx + ux * far + px * far * wid, cy + uy * far + py * far * wid),
                   (cx + ux * far - px * far * wid, cy + uy * far - py * far * wid)], fill=(255, 255, 255, 235))
    return np.array(im)


def burst(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    text = t['text']
    size = H * 0.23
    half = text.index('+') if '+' in text[1:] else max(1, len(text) // 2)   # 英文组合键在加号处分实心和空心
    solid = word(text[:half], size, '#FFFFFF', HEAVY)
    hollow_src = word(text[half:], size, '#FFFFFF', HEAVY, stroke=int(6 * S), stroke_color='#FFFFFF')
    inner = word(text[half:], size, '#FFFFFF', HEAVY, stroke=0)
    hollow = hollow_src.copy()   # 空心：描边版挖掉实心字
    ih, iw = inner.shape[:2]
    oy, ox = (hollow.shape[0] - ih) // 2, (hollow.shape[1] - iw) // 2
    hollow[oy:oy + ih, ox:ox + iw, 3] = np.clip(hollow[oy:oy + ih, ox:ox + iw, 3].astype(int) - inner[..., 3], 0, 255).astype(np.uint8)
    gap = int(size * 0.04)
    hh = max(solid.shape[0], hollow.shape[0])
    row = np.zeros((hh, solid.shape[1] + gap + hollow.shape[1], 4), np.uint8)
    over(row, solid, 0, (hh - solid.shape[0]) // 2)
    over(row, hollow, solid.shape[1] + gap, (hh - hollow.shape[0]) // 2)
    if row.shape[1] > W * 0.9:
        row = scale(row, W * 0.9 / row.shape[1])
    lw = int(row.shape[1] * 0.42)
    rule = np.zeros((max(2, int(4 * S)), lw, 4), np.uint8)
    rule[...] = (255, 255, 255, 255)
    dur, n = frames(t, FPS)
    life = min(dur, t.get('life', 1.4))
    cx, cy = W / 2, H * t.get('y', 0.5)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    if is_landscape(W, H):
        row = fit_sprite(row, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.9, H * 0.3)
        rule = rule[:, :int(row.shape[1] * 0.42)]
    lines = None
    for i in range(n):
        tt = i / FPS
        canvas = dimmer(W, H, (0 if is_landscape(W, H) else 0.35) * min(1, tt / 0.08) * fade_out(tt, life, 0.2))
        if tt < life:
            if i % 2 == 0 or lines is None:
                if is_landscape(W, H):
                    l, top, r, bot = map(int, side_box(t, W, H))
                    d = r - l
                    top = int(cy - d / 2)
                    lines = _speedlines(d, d, int(t['t0'] * 100) + i, S)
                    yy, xx = np.mgrid[:d, :d]
                    soft = np.clip((0.5 - np.hypot(xx / d - 0.5, yy / d - 0.5)) * 12, 0, 1)
                    lines[..., 3] = (lines[..., 3] * soft).astype(np.uint8)
                else:
                    lines = _speedlines(W, H, int(t['t0'] * 100) + i, S)
            over(canvas, lines, l if is_landscape(W, H) else 0, top if is_landscape(W, H) else 0, fade_out(tt, life, 0.2))
            p = ease(_clamp(tt / 0.12), 'out')
            spr = scale(row, 0.7 + 0.3 * p)
            e = fade_out(tt, life, 0.2)
            put(canvas, with_shadow(spr, 8 * S, 0.5), cx, cy, e)
            off = row.shape[0] * 0.62
            put(canvas, rule, cx, cy - off, e * p)
            put(canvas, rule, cx, cy + off, e * p)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- knockout 后词撞飞前词
def knockout(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    old = fit_word(t['left'], 200 * S, W * 0.86, '#FFFFFF', HEAVY, stroke=int(5 * S))
    new = fit_word(t['right'], 235 * S, W * 0.9, t.get('color', '#E0102F'), HEAVY, stroke=int(6 * S), stroke_color='#FFFFFF')
    old, new = with_shadow(old, 8 * S), with_shadow(new, 8 * S)
    dur, n = frames(t, FPS)
    tc = t.get('hit_at') or min(max(0.6, dur * 0.35), dur - 0.5)   # 接触那一帧
    cx, cy = W * 0.5, H * t.get('y', 0.64)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    if is_landscape(W, H):
        mw = (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.86
        old, new = (fit_sprite(g, mw, H * 0.3) for g in (old, new))
    for i in range(n):
        tt = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        e = fade_out(tt, dur)
        if tt < tc + 0.2:   # 旧词：先弹出，被撞时加速飞出左边并转
            k = eback(tt / 0.22) if tt < 0.22 else 1
            if tt <= tc:
                put(canvas, scale(old, max(0.05, k)), cx, cy, min(1, tt / 0.1))
            else:
                p = ease(_clamp((tt - tc) / 0.15), 'in')
                put(canvas, rotate_rgba(old, 25 * p), cx - p * W * 0.9, cy - p * H * 0.06, 1 - p * 0.3)
        a = tc - 0.25
        if tt >= a:   # 新词：0.25 秒从右边冲到落点，撞上后定住、微震
            p = ease(_clamp((tt - a) / 0.25), 'in')
            x = W + new.shape[1] / 2 - (W + new.shape[1] / 2 - cx) * p
            dx = 0
            if tc <= tt < tc + 0.12:
                dx = (8 * S) * (1 if i % 2 else -1)
            put(canvas, new, x + dx, cy, e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- crack 主词裂开插入副句
CRACK_VARIANTS = {
    'gap': '巨字横缝嵌字：巨字上下两半分开，缝里插进一行小字，中间那条字变灰',
    'shift': '三层错位：巨字切成上中下三条，左右错开，缝里插进副句',
}


def crack(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'gap')
    main = fit_word(t['text'], 300 * S, W * 0.82, '#FFFFFF', HEAVY)
    main = with_shadow(main, 8 * S, 0.5)
    sub = fit_word(t['sub'], 78 * S, W * 0.8, t.get('color', '#F2C230'), HEAVY)
    if is_landscape(W, H):
        mw = (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.72
        main, sub = (fit_sprite(g, mw, H * 0.28) for g in (main, sub))
    h = main.shape[0]
    cuts = [0, h // 2, h] if v == 'gap' else [0, h // 3, 2 * h // 3, h]
    parts = [main[a:b] for a, b in zip(cuts, cuts[1:])]
    dur, n = frames(t, FPS)
    to = t.get('open_at') or min(0.6, dur * 0.3)
    cx, cy = W / 2, H * t.get('y', 0.60)
    mid = len(parts) // 2   # 缝开在这一条的上面
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = dimmer(W, H, (0 if is_landscape(W, H) else 0.3) * min(1, tt / 0.15) * fade_out(tt, dur))
        e = fade_out(tt, dur)
        k = 1.3 - 0.3 * ease(_clamp(tt / 0.25), 'out')
        p = ease(_clamp((tt - to) / 0.25), 'out')
        gap = sub.shape[0] * 1.6 * p
        top = cy - h * k / 2 - gap / 2
        for j, part in enumerate(parts):
            ps = scale(part, k)
            y = top + cuts[j] * k + (gap if j >= mid else 0)
            dx = (-1, 1, -1)[j] * (mw * 0.12 if is_landscape(W, H) else W * 0.08) * p if v == 'shift' else 0
            op = 1 - 0.5 * p if (v == 'gap' and j == mid) else 1.0   # 横缝下面那条变灰
            over(canvas, ps, cx - ps.shape[1] / 2 + dx, y, e * min(1, tt / 0.12) * op)
        if p > 0:
            spr = sub.copy()
            flash = 1 + 0.6 * (1 - _clamp((tt - to) / 0.12))
            spr[..., :3] = np.clip(spr[..., :3].astype(np.float32) * flash, 0, 255).astype(np.uint8)
            put(canvas, spr, cx, top + cuts[mid] * k + gap / 2, e * p)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- swap 引导词换成重点词
SWAP_VARIANTS = {
    'fold': '折叠弹入：引导词上下压扁收起，重点词从一条线展开弹出',
    'ghost': '引导词放大成底纹：引导词放大到 2.5 倍淡成底纹，重点词压在上面弹出',
    'vblur': '竖向模糊换字：引导词带纵向模糊往上溜走，重点词从下面横向拉宽落定',
}


def swap(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'fold')
    lead = with_shadow(fit_word(t['lead'], 140 * S, W * 0.8, '#FFFFFF', HEAVY, stroke=int(3 * S)), 6 * S)
    key = with_shadow(fit_word(t['text'], 225 * S, W * 0.86, t.get('color', '#F5A300'), HEAVY, stroke=int(4 * S)), 8 * S)
    if is_landscape(W, H):
        mw = (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * (0.36 if v == 'ghost' else 0.78)
        lead = fit_sprite(lead, mw, H * 0.25)
        key = fit_sprite(key, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.84, H * 0.3)
    dur, n = frames(t, FPS)
    ts = t.get('swap_at') or min(max(0.5, dur * 0.35), dur - 0.4)
    cx, cy = W / 2, H * t.get('y', 0.63)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        e = fade_out(tt, dur)
        pin = ease(_clamp(tt / 0.2), 'out')
        q = _clamp((tt - ts) / 0.22)
        if v == 'fold':
            if tt < ts + 0.11:
                sy = 1 - _clamp((tt - ts) / 0.11)
                spr = np.array(Image.fromarray(lead).resize((lead.shape[1], max(1, int(lead.shape[0] * sy * pin)))))
                put(canvas, spr, cx, cy, e)
            if tt >= ts + 0.08:
                sy = eback((tt - ts - 0.08) / 0.22)
                spr = np.array(Image.fromarray(key).resize((key.shape[1], max(1, int(key.shape[0] * max(0.02, sy))))))
                put(canvas, spr, cx, cy, e)
        elif v == 'ghost':
            if tt < ts:
                put(canvas, scale(lead, 0.9 + 0.1 * pin), cx, cy, pin * e)
            else:
                put(canvas, scale(lead, 1 + 1.5 * ease(q, 'out')), cx, cy, (1 - 0.65 * q) * e)
                put(canvas, scale(key, 0.6 + 0.4 * eback(q)), cx, cy, min(1, q * 2) * e)
        else:
            if tt < ts + 0.2:
                p = ease(_clamp((tt - ts) / 0.2), 'in')
                spr = vblur(lead, 18 * S * p)
                put(canvas, spr, cx, cy - H * 0.08 * p, (1 - p) * pin * e)
            if tt >= ts:
                p = ease(q, 'out')
                spr = np.array(Image.fromarray(key).resize((max(1, int(key.shape[1] * (1.2 - 0.2 * p))), key.shape[0])))
                put(canvas, spr, cx, cy + H * 0.06 * (1 - p), p * e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- finish 花字质感
FINISH_VARIANTS = {
    'striped': '横纹拖影立体：字往右下挤出一段黑白横纹立体厚度',
    'halftone': '网点投影：黄字下面错开一层红色网点投影',
    'neon': '霓虹空心：只有发光的描边，画面压暗衬托',
    'gradient': '渐变填充：字从亮黄渐变到浅紫',
    'glitch': '故障错位：红蓝通道左右错开、隔一会儿抖一下',
}


def _mask(text, size, maxw, stroke=0):
    return fit_word(text, size, maxw, '#FFFFFF', HEAVY, stroke=stroke, stroke_color='#FFFFFF')


def _tint(m, color, alpha=1.0):
    a = np.zeros_like(m)
    a[..., :3] = hex_rgba(color)[:3]
    a[..., 3] = (m[..., 3] * alpha).astype(np.uint8)
    return a


def _finish_sprite(t, v, S, W):
    text, maxw = t['text'], W * 0.86
    size = 240 * S
    if v == 'striped':
        m = _mask(text, size, maxw)
        depth = int(32 * S)
        h, w_ = m.shape[:2]
        out = np.zeros((h + depth, w_ + depth, 4), np.uint8)
        stripe = int(4 * S) or 1
        for d in range(depth, 0, -1):
            col = '#111111' if (d // stripe) % 2 else '#FFFFFF'
            over(out, _tint(m, col), d, d)
        over(out, _tint(m, t.get('color', '#FFE24A')), 0, 0)
        return out
    if v == 'halftone':
        m = _mask(text, size, maxw)
        off = int(18 * S)
        h, w_ = m.shape[:2]
        dots = Image.new('L', (w_, h), 0)
        dd = ImageDraw.Draw(dots)
        step = max(4, int(9 * S))
        for yy in range(0, h, step):
            for xx in range((yy // step) % 2 * step // 2, w_, step):
                r = step * 0.38
                dd.ellipse([xx - r, yy - r, xx + r, yy + r], fill=255)
        sh = _tint(m, '#E2462B')
        sh[..., 3] = (sh[..., 3].astype(np.float32) * np.array(dots, np.float32) / 255).astype(np.uint8)
        out = np.zeros((h + off, w_ + off, 4), np.uint8)
        over(out, sh, off, off)
        over(out, _tint(m, '#F7B500'), 0, 0)
        return out
    if v == 'neon':
        col = t.get('color', '#E0242F')
        outline = _mask(text, size, maxw, stroke=int(9 * S))
        inner = _mask(text, size, maxw)
        ring = outline.copy()
        ih, iw = inner.shape[:2]
        oy, ox = (ring.shape[0] - ih) // 2, (ring.shape[1] - iw) // 2
        ring[oy:oy + ih, ox:ox + iw, 3] = np.clip(ring[oy:oy + ih, ox:ox + iw, 3].astype(int) - inner[..., 3], 0, 255).astype(np.uint8)
        pad = int(24 * S)
        out = np.zeros((ring.shape[0] + 2 * pad, ring.shape[1] + 2 * pad, 4), np.uint8)
        glow = np.zeros_like(out)
        over(glow, _tint(ring, col), pad, pad)
        out = blur(glow, 14 * S)
        out[..., 3] = np.clip(out[..., 3].astype(np.float32) * 2.2, 0, 255).astype(np.uint8)   # 外圈光晕加浓
        over(out, blur(glow, 4 * S), 0, 0)
        over(out, _tint(ring, col), pad, pad)
        core = _mask(text, size, maxw, stroke=int(2 * S))   # 灯管中间一条亮芯
        ch, cw_ = core.shape[:2]
        cy_, cx_ = pad + (ring.shape[0] - ch) // 2, pad + (ring.shape[1] - cw_) // 2
        thin = core.copy()
        thin[(ch - ih) // 2:(ch - ih) // 2 + ih, (cw_ - iw) // 2:(cw_ - iw) // 2 + iw, 3] = np.clip(
            thin[(ch - ih) // 2:(ch - ih) // 2 + ih, (cw_ - iw) // 2:(cw_ - iw) // 2 + iw, 3].astype(int) - inner[..., 3], 0, 255).astype(np.uint8)
        over(out, _tint(thin, '#FFFFFF', 0.9), cx_, cy_)
        return out
    if v == 'gradient':
        m = _mask(text, size, maxw)
        h, w_ = m.shape[:2]
        c1, c2 = np.array(hex_rgba('#FFE24A')[:3], np.float32), np.array(hex_rgba(t.get('color2', '#B9A6FF'))[:3], np.float32)
        u = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        out = m.copy()
        out[..., :3] = (c1 * (1 - u) + c2 * u).astype(np.uint8)
        return with_shadow(out, 6 * S, 0.5)
    m = _mask(text, size, maxw)   # glitch：白字，红蓝通道错开
    off = int(6 * S)
    h, w_ = m.shape[:2]
    out = np.zeros((h, w_ + 2 * off, 4), np.uint8)
    over(out, _tint(m, '#FF2D55', 0.85), 0, 0)
    over(out, _tint(m, '#19E0FF', 0.85), 2 * off, 0)
    over(out, _tint(m, '#FFFFFF'), off, 0)
    return out


def finish(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'striped')
    spr0 = _finish_sprite(t, v, S, W)
    if is_landscape(W, H):
        spr0 = fit_sprite(spr0, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.86, H * 0.35)
    dur, n = frames(t, FPS)
    cx, cy = W * t.get('x', 0.5), H * t.get('y', 0.62)
    dim = 0.62 if v == 'neon' and not is_landscape(W, H) else 0
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        e = fade_out(tt, dur)
        canvas = dimmer(W, H, dim * min(1, tt / 0.15) * e)
        k = 0.85 + 0.15 * eback(tt / 0.22)
        spr = scale(spr0, k)
        dx = 0
        if v == 'glitch' and (int(tt / 0.6) != int(max(0, tt - 1 / FPS) / 0.6) or (tt % 0.6) < 0.08) and tt > 0.3:
            dx = random.Random(i).uniform(-1, 1) * 14 * S
            h3 = spr.shape[0] // 3
            spr = spr.copy()
            spr[h3:2 * h3] = np.roll(spr[h3:2 * h3], int(dx * 1.5), axis=1)
        if v == 'neon' and tt > 0.25:   # 霓虹偶尔闪一下
            e *= 0.55 if random.Random(i // 3).random() < 0.06 else 1.0
        put(canvas, spr, cx + dx, cy, min(1, tt / 0.08) * e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- patch 纸片垫底字
PATCH_VARIANTS = {
    'kraft': '牛皮纸胶带标题：一条斜放的牛皮纸胶带横在头顶上方，深色字',
    'torn': '撕纸片：一块撕边灰纸片贴在人旁边，上面写红色大字',
    'chips': '每字彩纸：每个字一块彩纸随机歪着，一块块弹进来',
}
CHIP_COLORS = ['#F26B3A', '#F5D23C', '#E86FA8', '#9B7FE0', '#4CC17A', '#3D8BEA', '#E23B4E']


def _paper(w, h, color, seed, torn=False, S=1.0):
    rng = np.random.default_rng(seed)
    base = np.zeros((h, w, 4), np.uint8)
    base[..., :3] = hex_rgba(color)[:3]
    noise = rng.normal(0, 9, (h, w, 1))
    base[..., :3] = np.clip(base[..., :3].astype(np.float32) + noise, 0, 255).astype(np.uint8)
    base[..., 3] = (_torn_mask(w, h, seed, edge=int(16 * S))[..., 0] * 255).astype(np.uint8) if torn else 255
    return base


def patch(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'kraft')
    seed = int(t['t0'] * 100)
    dur, n = frames(t, FPS)
    sprites = []   # [(图, cx, cy, 出现秒)]
    if v == 'kraft':
        g = fit_word(t['text'], 112 * S, W * 0.76, '#2B2B2B', HEAVY)
        pw, ph = int(W * 0.85), int(g.shape[0] * 1.8)
        if is_landscape(W, H):
            from bigtype import _wrap
            l, top, r, bot = side_box(t, W, H)
            rows = [word(line, 64 * S, '#2B2B2B', HEAVY) for line in _wrap(t['text'], HEAVY, 64 * S, (r - l) * 0.72)]
            gap = int(12 * S)
            gh = sum(a.shape[0] for a in rows) + gap * max(0, len(rows) - 1)
            g = np.zeros((gh, max(a.shape[1] for a in rows), 4), np.uint8)
            yy = 0
            for a in rows:
                over(g, a, (g.shape[1] - a.shape[1]) / 2, yy)
                yy += a.shape[0] + gap
            pw, ph = int(g.shape[1] + 44 * S), int(g.shape[0] + 44 * S)
        p = _paper(pw, ph, '#C9A46A', seed, S=S)
        for edge in (0, pw - int(14 * S)):   # 两头锯齿撕口
            for yy in range(0, ph, int(10 * S) or 1):
                d = int(random.Random(seed + yy + edge).uniform(0, 12) * S)
                if edge == 0:
                    p[yy:yy + int(10 * S), :d, 3] = 0
                else:
                    p[yy:yy + int(10 * S), pw - d:, 3] = 0
        over(p, g, (pw - g.shape[1]) / 2, (ph - g.shape[0]) / 2)
        sprites.append((with_shadow(rotate_rgba(p, 3), 8 * S, 0.4, dy=int(5 * S)), W * 0.5, H * t.get('y', 0.09), 0.0))
    elif v == 'torn':
        g = fit_word(t['text'], 200 * S, W * 0.32, t.get('color', '#C4161C'), HEAVY)
        pw, ph = int(max(W * 0.3, g.shape[1] * 1.3)), int(max(H * 0.18, g.shape[0] * 1.4))
        p = _paper(pw, ph, '#D8D2C8', seed, torn=True, S=S)
        over(p, g, (pw - g.shape[1]) / 2, (ph - g.shape[0]) / 2)
        sprites.append((with_shadow(rotate_rgba(p, -6), 10 * S, 0.45, dy=int(6 * S)), W * t.get('x', 0.78), H * t.get('y', 0.58), 0.0))
    else:
        chars = [c for c in t['text'] if c.strip()][:8]
        cw = int(min(W * 0.16, W * 0.88 / max(1, len(chars))))
        total = cw * len(chars) * 1.06
        for j, c in enumerate(chars):
            g = word(c, cw * 0.72, '#FFFFFF' if CHIP_COLORS[(j + seed) % 7] not in ('#F5D23C',) else '#222222', HEAVY)
            p = _paper(cw, cw, CHIP_COLORS[(j + seed) % 7], seed + j, S=S)
            over(p, g, (cw - g.shape[1]) / 2, (cw - g.shape[0]) / 2)
            ang = random.Random(seed + j).uniform(-12, 12)
            sprites.append((with_shadow(rotate_rgba(p, ang), 5 * S, 0.4, dy=int(3 * S)),
                            W / 2 - total / 2 + cw * 1.06 * (j + 0.5), H * t.get('y', 0.64), (t.get('item_at') or [])[j] if j < len(t.get('item_at') or []) else j * t.get('every', 0.1)))
    if is_landscape(W, H):
        l, top, r, bot = side_box(t, W, H)
        cx, cy = side_anchor(t, W, H)
        if v == 'chips':
            rows = (len(sprites) + 1) // 2
            cell = min((r - l) / 2.5, (bot - top) / (rows + 0.5))
            sprites = [(fit_sprite(g, cell * 0.82, cell * 0.82), cx + (j % 2 - 0.5) * cell,
                        (top + bot) / 2 + (j // 2 - (rows - 1) / 2) * cell, a) for j, (g, _, _, a) in enumerate(sprites)]
        else:
            sprites = [(fit_sprite(g, (r - l) * 0.9, (bot - top) * 0.7), cx, cy, a) for g, _, _, a in sprites]
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        e = fade_out(tt, dur)
        for spr, x, y, a0 in sprites:
            if tt < a0:
                continue
            q = (tt - a0) / 0.2
            k = eback(q) if v == 'chips' else 0.92 + 0.08 * ease(_clamp(q), 'out')
            dy = 0 if v == 'chips' else -(1 - ease(_clamp(q), 'out')) * 30 * S
            put(canvas, scale(spr, max(0.05, k)), x, y + dy, min(1, q * 2) * e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- note 主标题旁小补充
NOTE_VARIANTS = {
    'arc': '弧形语气词：一行小字沿弧线斜着排在主标题右上角，黄色或薄荷绿',
    'tag': '便利贴标签：橙底黑字的小色块歪 5 度贴在主标题旁边',
}


def note(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'tag')
    size = H * t.get('size_h', 0.04)
    if v == 'tag':
        g = word(t['text'], size, '#111111', HEAVY)
        px, py = int(size * 0.45), int(size * 0.25)
        im = Image.new('RGBA', (g.shape[1] + 2 * px, g.shape[0] + 2 * py), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=int(size * 0.15), fill=hex_rgba(t.get('color', '#FF8A1A')))
        im.alpha_composite(Image.fromarray(g), (px, py))
        spr = with_shadow(rotate_rgba(np.array(im), 5), 4 * S, 0.4, dy=int(3 * S))
    else:   # 弧形：字沿一段圆弧排开，整体斜 30 度贴在主标题右上角
        col = t.get('color', '#FFD84A')
        chars = list(t['text'])
        gl = [Image.fromarray(word(c, size, col, HEAVY, stroke=int(3 * S), stroke_color='#2A2A2A')) for c in chars]
        adv = size * 1.02
        R = adv * len(chars) / np.radians(70)
        span = adv * len(chars) / R
        side = int(R * 2 + size * 3)
        im = Image.new('RGBA', (side, side), (0, 0, 0, 0))
        for j, g in enumerate(gl):
            a = -np.pi / 2 - span / 2 + adv * (j + 0.5) / R
            g = g.rotate(-np.degrees(a + np.pi / 2), resample=Image.BICUBIC, expand=True)
            x = side / 2 + R * np.cos(a) - g.width / 2
            y = side / 2 + R * np.sin(a) - g.height / 2
            im.alpha_composite(g, (int(x), int(y)))
        spr = rotate_rgba(trim(np.array(im)), -30)
    if is_landscape(W, H):
        spr = fit_sprite(spr, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.86, H * 0.3)
    dur, n = frames(t, FPS)
    cx, cy = W * t.get('x', 0.74), H * t.get('y', 0.48)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        put(canvas, scale(spr, max(0.05, eback(tt / 0.25))), cx, cy, min(1, tt / 0.1) * fade_out(tt, dur))
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- qmark 引号括号框概念词
QMARK_VARIANTS = {'bracket': '方括号「」：比字还大的白色括号把概念词框住', 'curly': '弯引号“”：一对放大的白色引号夹住概念词'}


def qmark(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'bracket')
    g = with_shadow(fit_word(t['text'], 190 * S, W * 0.64, t.get('color', '#FFE24A'), HEAVY, stroke=int(3 * S)), 7 * S)
    if is_landscape(W, H):
        g = fit_sprite(g, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.58, H * 0.23)
    lc, rc = ('「', '」') if v == 'bracket' else ('“', '”')
    ms = g.shape[0] * 1.25
    L = with_shadow(word(lc, ms, '#FFFFFF', HEAVY), 6 * S)
    R = with_shadow(word(rc, ms, '#FFFFFF', HEAVY), 6 * S)
    en = word(t['en'].upper(), 30 * S, '#FFFFFFB0', FONTS / 'Oswald-SemiBold.ttf', spacing=int(6 * S)) if t.get('en') else None
    dur, n = frames(t, FPS)
    cx, cy = W / 2, H * t.get('y', 0.62)
    gap = 14 * S
    if is_landscape(W, H):
        mw = (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.88
        f = min(1, mw / (g.shape[1] + L.shape[1] + R.shape[1] + gap * 2))
        g, L, R = (scale(a, f) for a in (g, L, R))
        gap *= f
    if is_landscape(W, H) and en is not None:
        en = fit_sprite(en, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.85, H * 0.08)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        e = fade_out(tt, dur)
        p = eback(tt / 0.2)
        put(canvas, scale(g, max(0.05, p)), cx, cy, min(1, tt / 0.08) * e)
        q = ease(_clamp((tt - 0.06) / 0.22), 'out')   # 括号从两侧合拢
        off = g.shape[1] / 2 + gap + L.shape[1] / 2 + (1 - q) * 60 * S
        ly = cy - (g.shape[0] * 0.15 if v == 'curly' else 0)
        put(canvas, L, cx - off, ly - (g.shape[0] * 0.1 if v == 'curly' else 0), q * e)
        put(canvas, R, cx + off, ly + (g.shape[0] * 0.1 if v == 'curly' else 0), q * e)
        if en is not None:
            put(canvas, en, cx, cy + g.shape[0] * 0.75, _clamp((tt - 0.25) / 0.2) * e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- scribble 红色手写数字批注
def scribble(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    g = word(str(t['value']), H * t.get('size_h', 0.16), t.get('color', '#C8202A'), HAND)
    g = rotate_rgba(g, 4)
    if is_landscape(W, H):
        g = fit_sprite(g, (side_box(t, W, H)[2] - side_box(t, W, H)[0]) * 0.78, H * 0.3)
    box = None
    if t.get('box'):
        pad = int(26 * S)
        im = Image.new('RGBA', (g.shape[1] + 2 * pad, g.shape[0] + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([3 * S, 3 * S, im.width - 3 * S, im.height - 3 * S], radius=int(24 * S),
                                             outline=(255, 255, 255, 153), width=int(6 * S))
        box = np.array(im)
    dur, n = frames(t, FPS)
    cx, cy = W * t.get('x', 0.72), H * t.get('y', 0.58)
    write = t.get('write_s', 0.4)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        e = fade_out(tt, dur)
        if box is not None:
            put(canvas, box, cx, cy, min(1, tt / 0.15) * e)
        p = ease(_clamp(tt / write), 'inout')
        spr = g.copy()
        cut = int(spr.shape[1] * p)
        soft = max(1, int(20 * S))
        ramp = np.clip((cut - np.arange(spr.shape[1])) / soft, 0, 1)   # 从左往右写出来
        spr[..., 3] = (spr[..., 3] * ramp[None, :]).astype(np.uint8)
        put(canvas, spr, cx, cy, e)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- icons 图标配并列词
ICONS_VARIANTS = {
    'unfold': '关键词展开配图标：每个词左边配一个 3D 图标，说到哪个哪个弹出来，竖着往下排',
    'row': '图标横排随读高亮：几个图标在胸前排一排，说到哪个哪个放大变亮，下面换成那个词',
    'dashbox': '虚线框逐个累加：底部一个半透明黑底白虚线框，图标和词一个个加进去',
}


def icon_png(name):
    """Fluent Emoji（微软开源，MIT）的 3D 图标，按英文名取，缓存在 ~/.cache/koubo/icons/。"""
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    stem = name.strip().lower().replace(' ', '_').replace('-', '_')
    f = ICON_CACHE / f'{stem}.png'
    if f.exists():
        return f
    folder = urllib.parse.quote(name.strip()[:1].upper() + name.strip()[1:])
    keep = name.strip().lower().replace(' ', '_')   # 有的文件名里保留连字符（globe_showing_asia-australia）
    for path in (f'{folder}/3D/{stem}_3d.png', f'{folder}/Default/3D/{stem}_3d_default.png', f'{folder}/3D/{keep}_3d.png',
                 f'{folder}/Default/3D/{keep}_3d_default.png'):
        try:
            with urllib.request.urlopen(f'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/{path}', timeout=20) as r:
                f.write_bytes(r.read())
            return f
        except Exception:
            continue
    raise SystemExit(f'图标「{name}」在 Fluent Emoji 里找不到：用它的英文名（如 Laptop、Rocket、Light bulb、Money bag），'
                     '全表见 github.com/microsoft/fluentui-emoji/tree/main/assets')


def _icon(name, d):
    im = Image.open(icon_png(name)).convert('RGBA')
    return np.array(im.resize((int(d), int(d)), Image.LANCZOS))


def icons(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return landscape_icons(t, W, H, FPS, out)
    S = unit(W, H)
    v = t.get('variant', 'unfold')
    items = t['items']
    names = t['icons']
    dur, n = frames(t, FPS)
    at = t.get('item_at') or []
    ats = [at[j] if j < len(at) and at[j] is not None else 0.15 + j * t.get('every', 0.45) for j in range(len(items))]
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'unfold':
        d = int(150 * S)
        rows = []
        for it, nm in zip(items, names):
            g = word(it, 86 * S, '#FFFFFF', HEAVY, stroke=int(3 * S))
            rows.append((_icon(nm, d), with_shadow(g, 5 * S)))
        x0, y0 = W * t.get('x', 0.56), H * t.get('y', 0.55)
        step = d * 1.15
        top = y0 - step * (len(rows) - 1) / 2
        for i in range(n):
            tt = i / FPS
            canvas = np.zeros((H, W, 4), np.uint8)
            e = fade_out(tt, dur)
            for j, (ic, g) in enumerate(rows):
                if tt < ats[j]:
                    continue
                q = (tt - ats[j]) / 0.18
                y = top + j * step
                put(canvas, scale(ic, max(0.05, eback(q))), x0, y, e)
                over(canvas, g, x0 + d * 0.62, y - g.shape[0] / 2 - (1 - ease(_clamp(q), 'out')) * 10 * S, min(1, q) * e)
            w.put(canvas)
    elif v == 'row':
        m = len(items)
        d = int(min(W * 0.24, W * 0.86 / m / 1.12))
        ics = [_icon(nm, d) for nm in names]
        labels = [with_shadow(word(it, 96 * S, '#FFE100', HEAVY, stroke=int(3 * S)), 5 * S) for it in items]
        y0 = H * t.get('y', 0.64)
        xs = [W / 2 + (j - (m - 1) / 2) * d * 1.12 for j in range(m)]
        for i in range(n):
            tt = i / FPS
            canvas = np.zeros((H, W, 4), np.uint8)
            e = fade_out(tt, dur)
            cur = max([j for j in range(m) if tt >= ats[j]], default=-1)
            for j in range(m):
                pin = ease(_clamp(tt / 0.25 - j * 0.15), 'out')
                k = 1.3 if j == cur else 1.0
                if j == cur:
                    k = 1 + 0.3 * ease(_clamp((tt - ats[j]) / 0.15), 'out')
                spr = scale(ics[j], k)
                if j != cur:
                    spr = spr.copy()
                    spr[..., :3] = (spr[..., :3] * 0.55).astype(np.uint8)
                put(canvas, spr, xs[j], y0 - (1 - pin) * 30 * S, pin * e)
            if cur >= 0:
                q = _clamp((tt - ats[cur]) / 0.15)
                put(canvas, labels[cur], W / 2, y0 + d * 0.95, q * e)
            w.put(canvas)
    else:
        bw, bh = int(W * 0.86), int(H * 0.15)
        box = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        dr = ImageDraw.Draw(box)
        dr.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=int(22 * S), fill=(0, 0, 0, 90))
        dash, gap_ = int(16 * S), int(10 * S)
        for x in range(0, bw, dash + gap_):
            dr.line([(x, 1), (min(bw, x + dash), 1)], fill=(255, 255, 255, 230), width=max(2, int(2 * S)))
            dr.line([(x, bh - 2), (min(bw, x + dash), bh - 2)], fill=(255, 255, 255, 230), width=max(2, int(2 * S)))
        for y in range(0, bh, dash + gap_):
            dr.line([(1, y), (1, min(bh, y + dash))], fill=(255, 255, 255, 230), width=max(2, int(2 * S)))
            dr.line([(bw - 2, y), (bw - 2, min(bh, y + dash))], fill=(255, 255, 255, 230), width=max(2, int(2 * S)))
        box = np.array(box)
        m = len(items)
        cell = bw / m
        d = int(min(bh * 0.52, cell * 0.55))
        parts = []
        for it, nm in zip(items, names):
            g = fit_word(it, 58 * S, cell * 0.86, '#FFFFFF', HEAVY)
            parts.append((_icon(nm, d), g))
        cx, cy = W / 2, H * t.get('y', 0.78)
        for i in range(n):
            tt = i / FPS
            canvas = np.zeros((H, W, 4), np.uint8)
            e = fade_out(tt, dur)
            put(canvas, box, cx, cy, min(1, tt / 0.15) * e)
            for j, (ic, g) in enumerate(parts):
                if tt < ats[j]:
                    continue
                q = (tt - ats[j]) / 0.18
                x = cx - bw / 2 + cell * (j + 0.5)
                put(canvas, scale(ic, max(0.05, eback(q))), x, cy - bh * 0.13, e)
                put(canvas, g, x, cy + bh * 0.3, min(1, q) * e)
            w.put(canvas)
    w.close()


def landscape_icons(t, W, H, FPS, out):
    """横屏图标和词一起进侧栏；横排高亮改成两列，虚线框随内容增高。"""
    S = unit(W, H)
    v = t.get('variant', 'unfold')
    items, names = t['items'], t['icons']
    l, top, r, bot = side_box(t, W, H)
    bw, bh = r - l, bot - top
    dur, n = frames(t, FPS)
    at = t.get('item_at') or []
    ats = [at[j] if j < len(at) and at[j] is not None else 0.15 + j * t.get('every', 0.45) for j in range(len(items))]
    grid = v == 'row'
    rows = (len(items) + 1) // 2 if grid else len(items)
    step = min(170 * S, bh / max(1, rows))
    d = int(min(100 * S, step * 0.6, bw * 0.22))
    built = [(_icon(nm, d), fit_word(it, 58 * S, bw * (0.43 if grid else 0.62), '#FFE100' if grid else '#FFFFFF', HEAVY,
                                    stroke=int(2 * S))) for it, nm in zip(items, names)]
    panel = None
    if v == 'dashbox':
        panel = Image.new('RGBA', (int(bw), int(step * rows + 30 * S)), (0, 0, 0, 95))
        dr = ImageDraw.Draw(panel)
        for x in range(0, panel.width - 2, max(1, int(24 * S))):
            for y in (1, panel.height - 2):
                dr.line((x, y, min(panel.width - 2, x + 14 * S), y), fill='white', width=max(1, int(2 * S)))
        for y in range(0, panel.height - 2, max(1, int(24 * S))):
            for x in (1, panel.width - 2):
                dr.line((x, y, x, min(panel.height - 2, y + 14 * S)), fill='white', width=max(1, int(2 * S)))
        panel = np.array(panel)
    w = SideWriter(out, W, H, FPS, t)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        e = fade_out(tt, dur)
        if panel is not None:
            put(c, panel, (l + r) / 2, (top + bot) / 2, min(1, tt / 0.15) * e)
        cur = max([j for j, a in enumerate(ats) if tt >= a], default=-1)
        for j, (ic, g) in enumerate(built):
            if tt < ats[j]:
                continue
            q = _clamp((tt - ats[j]) / 0.2)
            row = j // 2 if grid else j
            y = (top + bot) / 2 + (row - (rows - 1) / 2) * step
            if grid:
                x = l + bw * (0.25 + 0.5 * (j % 2))
                op = e * (1 if j == cur else 0.45)
                put(c, scale(ic, 1 + 0.15 * q if j == cur else 1), x, y - d * 0.22, op)
                put(c, g, x, y + d * 0.65, q * op)
            else:
                x = l + bw * 0.16
                put(c, scale(ic, max(0.05, eback(q))), x, y, e)
                over(c, g, l + bw * 0.32, y - g.shape[0] / 2, q * e)
        w.put(c)
    w.close()


# ---------------------------------------------------------------- recframe 录制边框
def recframe(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    m, L, lw = int(48 * S), int(90 * S), max(2, int(6 * S))
    mx, my, bottom = m, m, H - m
    if is_landscape(W, H):
        # 横屏边框围住上方口播区域，底部留给字幕。
        mx, my = int(W * 0.05), int(H * 0.05)
        bottom = int(H * safe_zones(W, H)['text'][0][3])
    frame = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    for (x, y, sx, sy) in ((mx, my, 1, 1), (W - mx, my, -1, 1), (mx, bottom, 1, -1), (W - mx, bottom, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=(255, 255, 255, 235), width=lw)
        d.line([(x, y), (x, y + sy * L)], fill=(255, 255, 255, 235), width=lw)
    frame = np.array(frame)
    rec = word('REC', 44 * S, '#FFFFFF', FONTS / 'Oswald-SemiBold.ttf')
    r = int(14 * S)
    dot = np.array(Image.new('RGBA', (2 * r, 2 * r), (0, 0, 0, 0)))
    im = Image.fromarray(dot)
    ImageDraw.Draw(im).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=(230, 30, 40, 255))
    dot = np.array(im)
    dur, n = frames(t, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        canvas = frame.copy()
        e = min(1, tt / 0.1) * fade_out(tt, dur, 0.1)
        if int(tt / 0.5) % 2 == 0:
            over(canvas, dot, mx + 30 * S, my + 34 * S)
        over(canvas, rec, mx + 30 * S + 2 * r + 12 * S, my + 34 * S + r - rec.shape[0] / 2)
        if e < 1:
            canvas[..., 3] = (canvas[..., 3] * e).astype(np.uint8)
        w.put(canvas)
    w.close()
