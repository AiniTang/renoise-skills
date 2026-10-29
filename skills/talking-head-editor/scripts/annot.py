"""贴纸标注与文字动效（手法库第 7 批）：逐帧合成的版式，titles 的 layout 写这些名字，cards.title_clip 转到这里渲成整屏透明 .mov。

按内容自动挑（library.IMPL）：
- qmarks    问号点缀（kw_question_mark）：问句旁边立起半透明大问号，或蹦出几个手绘问号
- bubble    对话气泡文字（speech_bubble_text）：头顶漫画气泡里逐字打出问句，或几个黄色小气泡散在人两侧
- meme      表情包倾斜吐槽字（meme_reaction_caption）：黑底中间一张反应图，下缘骑缝压一行歪着的立体白字
- shout     呐喊声波残影（anim_shout_wave）：大字带三四层放大残影冲出来，收成一个字
- crossin   左右滑入交错（text_cross_slide）：引导词从左、重点词从右滑进来，错成对角或交叉压在一起
- wipe      擦除显字（text_wipe_reveal）：字被刷出来——逐字从上往下、从中间往两边、被一个光点刻出来
- perchar   逐字入场（anim_per_char）：一个字一个字弹出来，或每个字从不同高度升起
- cursor    鼠标指针点击（cursor_click）：白色箭头滑到关键词右下角点一下，带一圈波纹，关键词弹一下
写坐标、字段的（library.FIELDS）：
- arrow     箭头标注（arrow_stickers）：粗箭头指向目标、3D 上升或下跌箭头、四个角的箭头指向主体
- focus     聚焦框标注（focus_box）：对焦角标收紧、黄色细框加框外压暗、发光框把一句话拎出来重写
- cardpair  双卡同步左移让位（card_slide_pair）：第一张卡居中，到时间往左让半张，第二张从右边滑进来并排
- divider   金色细分割线展开（divider_line_reveal）：肩膀高度一条细金线从中间往两边展开，两端渐隐
尺寸按短边 1080 的像素值乘 S；横屏用 safe_zones 的两侧留白，竖屏沿用原锚点。
"""
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kvlib import unit, is_landscape, safe_zones, hex_rgba, is_image, to_png
from keytext import (FONTS, HAND, HEAVY, _clamp, blur, dimmer, eback, fade_out, fit_word, frames, icon_png, put, scale, with_shadow,
                     word)
from motion import Writer, ease, over, rotate_rgba, trim

SERIF = FONTS / 'SourceHanSerifCN-Heavy.otf'
LAYOUTS = ('qmarks', 'bubble', 'meme', 'shout', 'crossin', 'wipe', 'perchar', 'cursor', 'arrow', 'focus', 'cardpair', 'divider')


def clip(t, W, H, FPS, st, work, aroll, out):
    {'qmarks': qmarks, 'bubble': bubble, 'meme': meme, 'shout': shout, 'crossin': crossin, 'wipe': wipe, 'perchar': perchar,
     'cursor': cursor, 'arrow': arrow, 'focus': focus, 'cardpair': cardpair, 'divider': divider}[t['layout']](t, W, H, FPS, st, work, aroll, out)


def _canvas(W, H):
    return np.zeros((H, W, 4), np.uint8)


def _run(t, W, H, FPS, out, draw):
    """逐帧调 draw(canvas, tt, dur, i) 画一帧，写成透明 .mov。"""
    dur, n = frames(t, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        canvas = _canvas(W, H)
        draw(canvas, i / FPS, dur, i)
        if is_landscape(W, H) and t.get('layout') in ('qmarks', 'bubble', 'shout', 'crossin', 'wipe', 'perchar', 'cursor'):
            # 入场的残影和鼠标也不能从人脸上穿过，侧栏边界外先裁掉。
            left, right = safe_zones(W, H)['text']
            canvas[:, int(left[2] * W):int(right[0] * W), 3] = 0
            canvas[:int(H * 0.05), :, 3] = 0
            canvas[int(H * 0.8):, :, 3] = 0
            canvas[:, :int(W * 0.05), 3] = canvas[:, int(W * 0.95):, 3] = 0
        w.put(canvas)
    w.close()


def _title(text, S, W, size=120, color='#FFFFFF', font=HEAVY, maxw=0.86):
    return with_shadow(fit_word(text, size * S, W * maxw, color, font, stroke=int(3 * S)), 6 * S)


def side_box(t, W, H, side=None):
    """横屏的左右留白：沿用共用安全区，再给边缘留出 5%。"""
    side = side or t.get('side') or ('left' if int(t.get('t0', 0)) % 2 == 0 else 'right')
    x0, y0, x1, y1 = safe_zones(W, H)['text'][side == 'right']
    return max(0.05, x0) * W, y0 * H, min(0.95, x1) * W, y1 * H


def side_fit(g, t, W, H, reserve=1.0):
    x0, y0, x1, y1 = side_box(t, W, H)
    return scale(g, min(1.0, (x1 - x0) * reserve / g.shape[1], (y1 - y0) * reserve / g.shape[0]))


def side_center(t, W, H):
    x0, y0, x1, y1 = side_box(t, W, H)
    return (x0 + x1) / 2, min(y1 - H * 0.1, max(y0 + H * 0.1, H * t.get('y', 0.48)))


# ---------------------------------------------------------------- qmarks 问号点缀
QMARKS_VARIANTS = {
    'stand': '半透明大问号站起：人一侧立起一个黄色大问号，从底边往上站起来',
    'hop': '手绘问号连蹦：问句右上角错开蹦出两三个手写问号',
}


def qmarks(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'stand')
    q = _title(t['text'], S, W, 130) if t.get('text') else None
    cy = H * t.get('y', 0.64)
    col = t.get('color', '#F5B800')
    cx = W / 2
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)
        q = side_fit(q, t, W, H, 0.82) if q is not None else None
        cy += H * 0.12
        if q is not None:
            cy = min(cy, H * 0.8 - q.shape[0] / 2)
    if v == 'stand':
        big = word('?', H * 0.28, col, HEAVY, stroke=int(5 * S), stroke_color='#FFFFFF')
        bx = W * (0.83 if t.get('side', 'right') == 'right' else 0.17)
    else:
        marks = [rotate_rgba(word('？', H * s_, col, HAND, stroke=int(3 * S), stroke_color='#FFFFFF'), r)
                 for s_, r in ((0.085, -14), (0.065, 10), (0.05, -4))]

    if is_landscape(W, H):
        if v == 'stand':
            big = scale(big, 0.65)
            bx = cx
        else:
            marks = [scale(m, 0.7) for m in marks]

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        if q is not None:
            put(c, scale(q, max(0.05, eback(tt / 0.22))), cx, cy, min(1, tt / 0.08) * e)
        if v == 'stand':
            p = ease(_clamp((tt - 0.1) / 0.3), 'out')
            if p > 0:
                h = max(1, int(big.shape[0] * p))
                spr = np.array(Image.fromarray(big).resize((big.shape[1], h)))
                over(c, spr, bx - spr.shape[1] / 2, cy - big.shape[0] * (1.25 if is_landscape(W, H) else 0.75) + (big.shape[0] - h), 0.7 * e)   # 底边为锚点站起来
        else:
            right = (cx - W * 0.09 if is_landscape(W, H) else W / 2) + (q.shape[1] / 2 if q is not None else 0)
            for j, m in enumerate(marks):
                a = tt - 0.15 - j * 0.15
                if a < 0:
                    continue
                x = cx + (j - 1) * 65 * S if is_landscape(W, H) else right + (10 + j * 55) * S
                y = cy - H * 0.18 - (j % 2) * 25 * S if is_landscape(W, H) else cy - (q.shape[0] * 0.6 if q is not None else 0) - (j % 2) * 40 * S
                put(c, scale(m, max(0.05, eback(a / 0.2))), min(W - m.shape[1] / 2, x), y, e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- bubble 对话气泡
BUBBLE_VARIANTS = {
    'comic': '头顶漫画气泡：白底黑边的大气泡在头顶上方，问句一个字一个字打进去',
    'tags': '黄色气泡散布：几个黄色小气泡在人两侧一个个弹出来，每个写一种情况',
}


def _bubble_img(text, size, w_max, fill, edge, tail, S, font=HEAVY):
    g = fit_word(text, size, w_max, '#111111', font)
    px, py = int(size * 0.6), int(size * 0.45)
    bw, bh = g.shape[1] + 2 * px, g.shape[0] + 2 * py
    th = int(size * 0.7)
    im = Image.new('RGBA', (bw + 8, bh + th + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(2, int(edge * S))
    tx = bw * tail
    d.polygon([(tx - size * 0.35, bh - lw), (tx + size * 0.25, bh - lw), (tx - size * 0.15, bh + th)], fill=hex_rgba(fill), outline=(17, 17, 17, 255))
    d.rounded_rectangle([4, 4, bw, bh], radius=int(bh * 0.45), fill=hex_rgba(fill), outline=(17, 17, 17, 255), width=lw)
    d.polygon([(tx - size * 0.35 + lw, bh - lw * 2), (tx + size * 0.25 - lw, bh - lw * 2), (tx - size * 0.15, bh + th - lw * 2)], fill=hex_rgba(fill))
    return np.array(im), g, (px + 4, py + 4)


def bubble(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'comic')
    if v == 'comic':
        text = t['text']
        size = (54 if is_landscape(W, H) else 84) * S
        box, g, (ox, oy) = _bubble_img(text, size, W * (0.18 if is_landscape(W, H) else 0.78), '#FFFFFF', 6, 0.42, S)
        cx, cy = side_center(t, W, H) if is_landscape(W, H) else (W * 0.5, H * t.get('y', 0.12))
        if is_landscape(W, H):
            ratio = min(1, W * 0.22 / box.shape[1])
            box, g = scale(box, ratio), scale(g, ratio)
            ox, oy = ox * ratio, oy * ratio
        per = min(0.08, max(0.03, (t['t1'] - t['t0']) * 0.5 / max(1, len(text))))

        def draw(c, tt, dur, i):
            e = fade_out(tt, dur)
            k = max(0.05, eback(tt / 0.22))
            spr = box.copy()
            n = min(len(text), int(max(0, tt - 0.2) / per) + (1 if tt > 0.2 else 0))
            if n:
                part = word(text[:n], size, '#111111', HEAVY) if n < len(text) else g
                if is_landscape(W, H):
                    part = g.copy()
                    part[:, int(g.shape[1] * n / len(text)):, 3] = 0
                over(spr, part, ox, oy + (g.shape[0] - part.shape[0]) / 2)
            put(c, scale(spr, k), cx, cy, e)
        _run(t, W, H, FPS, out, draw)
        return
    items = t['items']
    spots = [(0.2, 0.40), (0.8, 0.46), (0.22, 0.60), (0.79, 0.64)]
    if is_landscape(W, H):
        # 右上方让出人像小窗的位置，气泡上下错开。
        spots = [(0.175, 0.32), (0.825, 0.43), (0.175, 0.62), (0.825, 0.65)]
    sprites = []
    for j, it in enumerate(items[:4]):
        b, g, (ox, oy) = _bubble_img(it, 62 * S, W * 0.36, '#FFD21F', 4, 0.7 if spots[j][0] < 0.5 else 0.3, S)
        over(b, g, ox, oy)
        spr = rotate_rgba(b, random.Random(j).uniform(-6, 6))
        if is_landscape(W, H):
            spr = side_fit(spr, t, W, H, 0.88)
        sprites.append((spr, spots[j]))
    at = t.get('item_at') or []

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        for j, (spr, (x, y)) in enumerate(sprites):
            a0 = at[j] if j < len(at) and at[j] is not None else 0.1 + j * 0.3
            if tt < a0:
                continue
            put(c, scale(spr, max(0.05, eback((tt - a0) / 0.2))), W * x, H * y, e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- meme 表情包吐槽字
def meme(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    src = t.get('src')
    if src:
        im = Image.open(to_png(src, work) if is_image(src) else src).convert('RGBA')
    else:   # 没给表情图就用 3D 表情（Fluent Emoji）
        im = Image.open(icon_png(t.get('emoji', 'Face with tears of joy'))).convert('RGBA')
    iw = int(W * (0.65 if src else 0.5))
    im = np.array(im.resize((iw, int(im.height * iw / im.width)), Image.LANCZOS))
    cap = word(t['text'], H * 0.07, '#FFFFFF', HEAVY, stroke=int(4 * S), stroke_color='#111111')
    if cap.shape[1] > W * 0.88:
        cap = word(t['text'], H * 0.07 * W * 0.88 / cap.shape[1], '#FFFFFF', HEAVY, stroke=int(4 * S), stroke_color='#111111')
    depth = int(H * 0.012)
    solid = np.zeros((cap.shape[0] + depth, cap.shape[1] + depth, 4), np.uint8)
    gray = cap.copy()
    gray[..., :3] = hex_rgba('#8A8A8A')[:3]
    for d in range(depth, 0, -max(1, depth // 6)):   # 灰色多层错开叠出立体厚度
        over(solid, gray, d, d)
    over(solid, cap, 0, 0)
    capt = rotate_rgba(solid, 8)
    cy = H * t.get('y', 0.42)
    if is_landscape(W, H):
        im = scale(im, min(1, W * 0.36 / im.shape[1], H * 0.56 / im.shape[0]))
        capt = scale(capt, min(1, W * 0.38 / capt.shape[1], H * 0.24 / capt.shape[0]))
        hh = max(im.shape[0], capt.shape[0]) / 2
        cy = np.clip(H * t.get('y', 0.44), H * 0.05 + hh, H * 0.8 - hh)

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        c[..., 3] = int(255 * min(1, tt / 0.08) * e)   # 黑底
        put(c, scale(im, max(0.05, 0.85 + 0.15 * eback(tt / 0.25))), (W * 0.3 if is_landscape(W, H) else W / 2), cy, e)
        q = _clamp((tt - 0.2) / 0.18)
        if q > 0:
            put(c, scale(capt, max(0.05, eback(q))), (W * 0.72 if is_landscape(W, H) else W / 2), (cy if is_landscape(W, H) else cy + im.shape[0] / 2), e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- shout 呐喊声波残影
def shout(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    main = fit_word(t['text'], 200 * S, W * 0.82, t.get('color', '#C0182A'), SERIF, stroke=int(4 * S), stroke_color='#FFFFFF')
    main = with_shadow(main, 7 * S, 0.5)
    sub = t.get('sub')
    cy = H * t.get('y', 0.62)
    cx = W / 2
    if is_landscape(W, H):
        main = side_fit(main, t, W, H, 0.7)
        cx, cy = side_center(t, W, H)

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        p = _clamp(tt / 0.25)
        for j, (k0, a0) in enumerate(((1.4, 0.25), (1.25, 0.35), (1.12, 0.5))):   # 残影从放大处收回，越收越淡
            if p >= 1:
                break
            k = k0 + (1 - k0) * ease(p, 'out')
            put(c, scale(main, k), cx, cy, a0 * (1 - p) * e)
        put(c, scale(main, 1.06 - 0.06 * ease(p, 'out')), cx, cy, min(1, tt / 0.06) * e)
        if sub:
            q = ease(_clamp((tt - 0.2) / 0.35), 'out')
            sp = int((40 - 40 * q) * S)
            g = word(sub, 70 * S, '#FFFFFF', HEAVY, spacing=sp)
            if is_landscape(W, H):
                g = side_fit(g, t, W, H, 0.85)
            put(c, with_shadow(g, 4 * S), cx + (1 - q) * -40 * S, cy + main.shape[0] * (1.1 if is_landscape(W, H) else 0.62), q * e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- crossin 左右滑入交错
CROSSIN_VARIANTS = {
    'diagonal': '对角错位：引导词从左滑到偏左上，重点词从右滑到偏右下，错成一条对角线',
    'cross': '横穿压中：引导词变灰压在后面，更大的重点词从右边横穿过来压在它上面',
}


def crossin(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'diagonal')
    lead = _title(t['lead'], S, W, 120, '#FFFFFF' if v == 'diagonal' else '#BBBBBB', maxw=0.66)
    key = _title(t['text'], S, W, 180, t.get('color', '#E0263A'), maxw=0.82)
    cy = H * t.get('y', 0.6)
    ka = t.get('key_at') or 0.25
    if v == 'diagonal':
        L = (max(W * 0.04 + lead.shape[1] / 2, W * 0.35), cy - key.shape[0] * 0.45)   # 两行都不出画
        R = (min(W * 0.96 - key.shape[1] / 2, W * 0.62), cy + lead.shape[0] * 0.55)
    else:
        L = (W * 0.5, cy - lead.shape[0] * 0.25)
        R = (W * 0.5, cy + lead.shape[0] * 0.25)

    if is_landscape(W, H):
        lead = side_fit(lead, t, W, H, 0.85)
        key = side_fit(key, t, W, H, 0.85)
        cx, cy = side_center(t, W, H)
        L = (cx, cy - H * 0.10)
        R = (cx, cy + H * 0.10)
        if v == 'cross':
            L, R = (cx, cy - H * 0.045), (cx, cy + H * 0.045)

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur, 0.12)
        out_ = ease(_clamp((tt - (dur - 0.2)) / 0.2), 'in') * W   # 收尾整体往左出画
        p = ease(_clamp(tt / 0.25), 'out')
        start = L[0] - lead.shape[1] if is_landscape(W, H) else -lead.shape[1] / 2
        put(c, lead, start + (L[0] - start) * p - out_, L[1], e)
        q = ease(_clamp((tt - ka) / 0.25), 'out')
        if tt >= ka:
            start = R[0] + key.shape[1] if is_landscape(W, H) else W + key.shape[1] / 2
            put(c, key, start - (start - R[0]) * q - out_, R[1], e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- wipe 擦除显字
WIPE_VARIANTS = {
    'vwipe': '竖向擦除：每个字从上往下被刷出来，一个接一个，带一点模糊变清',
    'center': '中间左右展开：一条细缝从中间往两边拉开，字跟着显出来',
    'laser': '激光雕刻：一个白色光点从左往右走，走过的地方字被刻出来',
}


def wipe(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'vwipe')
    g = _title(t['text'], S, W, 180, t.get('color', '#FFFFFF'))
    if is_landscape(W, H):
        g = side_fit(g, t, W, H, 0.9)
    h, w_ = g.shape[:2]
    cx, cy = W / 2, H * t.get('y', 0.62)
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)
    n = max(1, len(t['text']))
    glow = None
    if v == 'laser':
        r = int(h * 0.3)
        im = Image.new('RGBA', (4 * r, 4 * r), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse([r, r, 3 * r, 3 * r], fill=(255, 255, 255, 255))
        glow = np.array(im.filter(ImageFilter.GaussianBlur(r * 0.6)))

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        spr = g.copy()
        a = spr[..., 3].astype(np.float32)
        if v == 'vwipe':
            cw = w_ / n
            m = np.zeros_like(a)
            for j in range(n):
                p = _clamp((tt - j * 0.1) / 0.25)
                m[:int(h * ease(p, 'out')), int(j * cw):int((j + 1) * cw) + 1] = 1
            spr[..., 3] = (a * m).astype(np.uint8)
            spr = blur(spr, 8 * S * (1 - _clamp(tt / (0.25 + n * 0.1))))
        elif v == 'center':
            p = ease(_clamp(tt / 0.45), 'out')
            half = w_ / 2 * p
            xs = np.abs(np.arange(w_) - w_ / 2)
            spr[..., 3] = (a * (xs <= half)[None, :]).astype(np.uint8)
            spr = blur(spr, 8 * S * (1 - p))
        else:
            p = _clamp(tt / 0.4)
            edge = w_ * p
            ramp = np.clip((edge - np.arange(w_)) / (6 * S), 0, 1)
            spr[..., 3] = (a * ramp[None, :]).astype(np.uint8)
        put(c, spr, cx, cy, e)
        if glow is not None and 0 < tt < 0.45:
            put(c, glow, cx - w_ / 2 + w_ * _clamp(tt / 0.4), cy, e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- perchar 逐字入场
PERCHAR_VARIANTS = {
    'zoom': '逐字缩放：一个字接一个字从小放大弹出来，最后定住',
    'rise': '随机上升：每个字随机晚一点、从下面升上来淡入，衬线字',
}


def perchar(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'zoom')
    font = SERIF if v == 'rise' else HEAVY
    hl = ''.join(t.get('hl') or [])
    chars = list(t['text'])
    size = 170 * S
    gl = [with_shadow(word(ch, size, t.get('hl_color', '#C8102E') if ch in hl else '#FFFFFF', font, stroke=int(2 * S)), 5 * S)
          if ch.strip() else None for ch in chars]
    adv = [x.shape[1] * 0.92 if x is not None else size * 0.35 for x in gl]
    total = sum(adv)
    k = min(1.0, W * 0.88 / total)
    cy = H * t.get('y', 0.62)
    cx = W / 2
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)
        x0, _, x1, _ = side_box(t, W, H)
        k = min(k, (x1 - x0) * 0.9 / total)
    rnd = random.Random(int(t['t0'] * 10))
    delays = [j * 0.07 if v == 'zoom' else rnd.uniform(0, 0.2) for j in range(len(chars))]

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        x = cx - total * k / 2
        for j, gch in enumerate(gl):
            if gch is not None and tt >= delays[j]:
                q = _clamp((tt - delays[j]) / (0.12 if v == 'zoom' else 0.3))
                spr = scale(gch, k * (max(0.05, eback(q)) if v == 'zoom' else 1))
                dy = 0 if v == 'zoom' else (1 - ease(q, 'out')) * H * 0.03
                put(c, spr, x + adv[j] * k / 2, cy + dy, (1 if v == 'zoom' else q) * e)
            x += adv[j] * k
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- cursor 鼠标指针点击
def _cursor_img(h):
    s = h / 24
    pts = [(0, 0), (0, 19), (4.5, 15), (7.5, 22), (10.5, 20.8), (7.6, 14), (13.5, 14)]
    im = Image.new('RGBA', (int(16 * s) + 8, int(25 * s) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(4 + x * s, 4 + y * s) for x, y in pts], fill=(255, 255, 255, 255), outline=(10, 10, 10, 255), width=max(2, int(s * 1.4)))
    return np.array(im)


def cursor(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    key = _title(t['text'], S, W, 170, t.get('color', '#FFBF17'), maxw=0.8)
    if is_landscape(W, H):
        key = side_fit(key, t, W, H, 0.75)
    cur = with_shadow(_cursor_img(H * 0.055), 4 * S, 0.5, dy=int(3 * S))
    cx, cy = W / 2, H * t.get('y', 0.62)
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)
    tip = (cx + key.shape[1] * 0.42, cy + key.shape[0] * 0.38)   # 点在关键词右下角，不盖住字
    click = t.get('click_at') or 0.5

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        b = 1.0
        if click <= tt < click + 0.3:   # 点下去那一刻关键词弹一下
            b = 1 + 0.12 * np.sin((tt - click) / 0.3 * np.pi)
        put(c, scale(key, b * max(0.05, eback(tt / 0.2))), cx, cy, min(1, tt / 0.08) * e)
        p = ease(_clamp((tt - 0.1) / 0.35), 'out')
        x = tip[0] + (1 - p) * W * 0.25
        y = tip[1] + (1 - p) * H * 0.08
        if tt >= click:
            q = _clamp((tt - click) / 0.25)
            if q < 1:
                r = (10 + 60 * ease(q, 'out')) * S
                ring = Image.new('RGBA', (int(2 * r) + 6, int(2 * r) + 6), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse([3, 3, 2 * r + 3, 2 * r + 3], outline=(255, 255, 255, int(255 * (1 - q))), width=max(2, int(5 * S)))
                put(c, np.array(ring), tip[0], tip[1], e)
            y += 3 * S if tt < click + 0.1 else 0
        over(c, cur, x - 4, y - 4, min(1, tt / 0.1) * e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- arrow 箭头标注
ARROW_VARIANTS = {
    'point': '粗箭头指向目标：带白边的彩色粗箭头从 from 长到 to，到了轻轻弹两下',
    'up': '3D 上升箭头：绿色立体大箭头往右上冲（down 写成红色往右下）',
    'corners': '四角视线引导：四个箭头从画面四角指向 to 那一点',
}


def _arrow_img(length, width, color, S):
    """一支朝右的粗箭头（带白边）。"""
    L, w_ = int(length), int(width)
    head = int(w_ * 2.2)
    im = Image.new('RGBA', (L + 12, head + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = (head + 12) / 2
    poly = [(6, cy - w_ / 2), (L - head * 0.9, cy - w_ / 2), (L - head * 0.9, cy - head / 2), (L + 6, cy),
            (L - head * 0.9, cy + head / 2), (L - head * 0.9, cy + w_ / 2), (6, cy + w_ / 2)]
    d.polygon(poly, fill=hex_rgba(color), outline=(255, 255, 255, 255), width=max(2, int(4 * S)))
    return np.array(im)


def arrow(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'point')
    col = t.get('color', '#F5C518')
    to = np.array([W * t['to'][0], H * t['to'][1]]) if t.get('to') else np.array([W * 0.5, H * 0.45])
    if is_landscape(W, H) and v == 'point' and not t.get('to'):
        to = np.array(side_center(t, W, H))
    if v == 'up':
        down = t.get('dir') == 'down'
        col = t.get('color', '#E23B3B' if down else '#2EB872')
        a = _arrow_img((H * 0.34 if is_landscape(W, H) else W * 0.36), 46 * S, col, S)
        depth = int(14 * S)
        solid = np.zeros((a.shape[0] + depth, a.shape[1] + depth, 4), np.uint8)
        dark = a.copy()
        dark[..., :3] = (dark[..., :3] * 0.55).astype(np.uint8)
        for d in range(depth, 0, -2):
            over(solid, dark, d, d)
        over(solid, a, 0, 0)
        spr = rotate_rgba(solid, -35 if down else 35)
        if is_landscape(W, H):
            spr = side_fit(spr, t, W, H, 0.85)
            # 手写目标还是原来的画面坐标，没写目标才自动选侧栏。
            if not t.get('to'):
                to = np.array(side_center(t, W, H))

        def draw(c, tt, dur, i):
            e = fade_out(tt, dur)
            p = ease(_clamp(tt / 0.3), 'out')
            put(c, scale(spr, max(0.05, 0.6 + 0.4 * eback(tt / 0.3))), to[0] - (1 - p) * 60 * S, to[1] + (1 - p) * (-60 if down else 60) * S,
                min(1, tt / 0.1) * e)
        _run(t, W, H, FPS, out, draw)
        return
    if v == 'corners':
        starts = [np.array([W * 0.08, H * 0.12]), np.array([W * 0.92, H * 0.12]), np.array([W * 0.08, H * 0.88]), np.array([W * 0.92, H * 0.88])]
    else:
        starts = [np.array([W * t['from'][0], H * t['from'][1]]) if t.get('from') else to + np.array([W * 0.28, H * 0.12])]
        if is_landscape(W, H) and not t.get('from'):
            starts = [to + np.array([0, H * 0.18])]
    if is_landscape(W, H) and v == 'corners':
        starts[2][1] = starts[3][1] = H * 0.72
    arrows = []
    for s0 in starts:
        vec = to - s0
        dist = np.hypot(*vec)
        L = dist * (0.45 if v == 'corners' else 0.9)
        img = _arrow_img(L, (22 if v == 'corners' else 30) * S, col, S)
        ang = -np.degrees(np.arctan2(vec[1], vec[0]))
        u = vec / max(dist, 1e-6)
        tail = s0 + u * dist * (0.12 if v == 'corners' else 0.05)
        arrows.append((img, ang, tail, u, L))

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        for img, ang, tail, u, L in arrows:
            p = ease(_clamp(tt / 0.2), 'out')
            vis = img.copy()
            vis[:, int(img.shape[1] * p):, 3] = 0   # 从尾巴长到箭头
            spr = rotate_rgba(vis, ang)
            bob = np.sin(max(0, tt - 0.2) * 2 * np.pi * 1.6) * 8 * S * (tt > 0.2)
            centre = tail + u * (L / 2 + bob)
            put(c, spr, centre[0], centre[1], e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- focus 聚焦框
FOCUS_VARIANTS = {
    'brackets': '对焦角标：四个白色角标从大一圈收紧到目标上',
    'callout': '黄色细框：黄色细圆角框圈出目标，框外压暗两成',
    'glow': '发光框重写重点句：黄绿发光框圈住目标，框里重写那句话',
}


def focus(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'brackets')
    bx, by, bw, bh = t.get('box', [0.15, 0.3, 0.7, 0.14])
    if is_landscape(W, H) and not t.get('box'):
        x0, _, x1, _ = side_box(t, W, H)
        cx, cy = side_center(t, W, H)
        bw, bh = (x1 - x0) * 0.8 / W, 0.14
        bx, by = cx / W - bw / 2, cy / H - bh / 2
    x0, y0, x1, y1 = W * bx, H * by, W * (bx + bw), H * (by + bh)
    txt = _title(t['text'], S, W, 64, '#FFFFFF', maxw=bw * 0.9) if v == 'glow' and t.get('text') else None

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        im = Image.fromarray(c)
        d = ImageDraw.Draw(im)
        if v == 'brackets':
            k = 1.2 - 0.2 * ease(_clamp(tt / 0.2), 'out')
            cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
            L, lw = (x1 - x0) * 0.15, max(3, int(8 * S))
            a = int(255 * min(1, tt / 0.1) * e)
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                px, py = cx + sx * hw, cy + sy * hh
                d.line([(px, py), (px - sx * L, py)], fill=(255, 255, 255, a), width=lw)
                d.line([(px, py), (px, py - sy * L)], fill=(255, 255, 255, a), width=lw)
        elif v == 'callout':
            p = _clamp(tt / 0.2)
            dim = Image.new('RGBA', (W, H), (0, 0, 0, int(51 * p * e)))
            ImageDraw.Draw(dim).rounded_rectangle([x0, y0, x1, y1], radius=int(6 * S), fill=(0, 0, 0, 0))
            im = dim
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([x0, y0, x1, y1], radius=int(6 * S), outline=(232, 212, 77, int(255 * p * e)), width=max(2, int(3 * S)))
        else:
            p = eback(tt / 0.25)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            hw, hh = (x1 - x0) / 2 * p, (y1 - y0) / 2 * p
            ring = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ring).rounded_rectangle([cx - hw, cy - hh, cx + hw, cy + hh], radius=int(14 * S),
                                                   fill=(10, 10, 12, int(200 * e)) if txt is not None else None,
                                                   outline=(232, 240, 96, int(255 * e)), width=max(2, int(3 * S)))
            g = ring.filter(ImageFilter.GaussianBlur(8 * S))
            im.alpha_composite(g)
            im.alpha_composite(ring)
        c[...] = np.array(im)
        if txt is not None and tt > 0.2:
            put(c, txt, (x0 + x1) / 2, (y0 + y1) / 2, _clamp((tt - 0.2) / 0.2) * e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- cardpair 双卡左移让位
def _card(src, w, work, S):
    im = Image.open(to_png(src, work) if is_image(src) else src).convert('RGBA')
    h = int(im.height * w / im.width)
    im = im.resize((int(w), h), Image.LANCZOS)
    r = int(18 * S)
    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=r, fill=255)
    im.putalpha(mask)
    return with_shadow(np.array(im), 14 * S, 0.5, dy=int(8 * S))


def cardpair(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    cw = W * t.get('w', 0.56)
    a, b = _card(t['src'], cw, work, S), _card(t['src2'], cw, work, S)
    cy = H * t.get('y', 0.46)
    at = t.get('at') or 1.2
    if is_landscape(W, H):
        # 双图是整页阅读，两列用足宽度，不能缩成两张看不清的小贴纸。
        a, b = [scale(g, min(1, W * 0.4 / g.shape[1], H * 0.62 / g.shape[0])) for g in (a, b)]
        hh = max(a.shape[0], b.shape[0]) / 2
        cy = np.clip(H * t.get('y', 0.44), H * 0.05 + hh, H * 0.8 - hh)

    def draw(c, tt, dur, i):
        e = fade_out(tt, dur)
        c[..., 3] = int(255 * e) if is_landscape(W, H) else int(255 * 0.45 * min(1, tt / 0.2) * e)
        p = ease(_clamp((tt - at) / 0.5), 'inout')
        q = ease(_clamp(tt / 0.25), 'out')
        put(c, a, W * (0.5 - 0.25 * p if is_landscape(W, H) else 0.5 - 0.28 * p), cy + (1 - q) * 40 * S, q * e)
        if tt >= at:
            put(c, b, W * (1.3 - 0.55 * p if is_landscape(W, H) else 1.3 - 0.52 * p), cy, e)
    _run(t, W, H, FPS, out, draw)


# ---------------------------------------------------------------- divider 金色细分割线
def divider(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    L = int(W * t.get('w', 0.8))
    if is_landscape(W, H):
        x0, _, x1, _ = side_box(t, W, H)
        L = int(min(L, x1 - x0))
    th = max(2, int(3 * S))
    xs = np.linspace(-1, 1, L, dtype=np.float32)
    line = np.zeros((th, L, 4), np.uint8)
    line[..., :3] = hex_rgba(t.get('color', '#C9A46A'))[:3]
    line[..., 3] = (255 * np.clip(1 - np.abs(xs) ** 2.2, 0, 1))[None, :].astype(np.uint8)
    cy = H * t.get('y', 0.42)
    cx = W / 2
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)

    def draw(c, tt, dur, i):
        p = ease(_clamp(tt / 0.6), 'out')
        half = int(L / 2 * p)
        if half < 1:
            return
        seg = line[:, L // 2 - half:L // 2 + half]
        put(c, with_shadow(seg, 3 * S, 0.45, dy=int(2 * S)), cx, cy, p * fade_out(tt, dur))   # 浅色墙上也看得见
    _run(t, W, H, FPS, out, draw)
