"""大字排版（手法库第 9 批）：逐帧合成的大字版式，titles 的 layout 写这些名字，cards.title_clip 转到这里渲成整屏 .mov。

- giant      巨字压画面（giant_word_page）：metal 金属浮雕单字、red_bleed 半透明红字出血（人站在字前，底下变灰）、collage 拼贴底毛笔字（繁体溶解成简体）
- ghostword  巨字底纹装饰（ghost_bg_word）：hollow 空心描边英文、emboss 同色系浮雕中文、edge 贴边竖排英文、grunge 两侧做旧灰字；主标题一起画
- boxed      方框单字标题（boxed_char_title）：每个字套一个白色细线方框，从上方依次落下，旁边可配黄色小字和一行白色说明
- corners    四角分字围人（corner_chars_frame）：four 四字四角、shrink 画面缩到中间四字围住、flank 两字夹头
- circletext 圆形头像配环绕字（circle_pip_text）：arc 弧形徽章字、tangent 并列词贴圆周、sandwich 大字上下夹头像
- splitswap  分屏圆头像巨字轮换（split_pip_word_swap）：上半屏素材、下半屏黑底，交界处白边圆头像，下面的巨字一词一换
- topcard    顶部整句章节标题卡（chapter_sentence_card_top，章节载体）：背景虚化、人缩小站在下方，顶部色块上整句逐字弹出
- vflank     竖排双列夹主体章节页（chapter_vertical_flank，章节载体）：主题底中间立着抠出来的主体，左右两列银色竖排字一高一低缓慢浮动
- typepanel  打字机长文面板（typewriter_panel）：accumulate 半透明面板逐行累加、满了上滚，top_card 顶部黄色条纹长文、人缩在下方
一行大小字混排（mix_size_line）走 ASS，在 typeset.py 的 mixline 版式；字幕三条在 kvlib.SUB_LOOKS 和 kvlib.phrase_subs。
铺满整屏、盖住口播的版式和变体在 kvlib.COVER_TITLES 或标 cover；读口播画面和抠像的版式不自动推近（kvlib.AROLL_TITLES）。
尺寸按 短边 1080 的像素值乘 S。
"""
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from fonts import FONTS
from keytext import side_box, side_anchor, fit_sprite, BRUSH, HEAVY, _clamp, blur, eback, fade_out, frames, put, rough, scale, shadow, with_shadow, word
from kvlib import unit, hex_rgba, is_image, probe, is_landscape, face_crop, pip_params
from motion import Writer, bg_frames, ease, over, read, resize, rotate_rgba, text_img, trim

SERIF = FONTS / 'SourceHanSerifCN-Heavy.otf'   # 粗宋
EN = FONTS / 'Anton-Regular.ttf'               # 窄体英文巨字
BEBAS = FONTS / 'BebasNeue-Regular.ttf'
TYPE = FONTS / 'SmileySans-Oblique.ttf'        # 得意黑：打字机面板

LAYOUTS = ('giant', 'ghostword', 'boxed', 'corners', 'circletext', 'splitswap', 'topcard', 'vflank', 'typepanel')


def clip(t, W, H, FPS, st, work, aroll, out):
    {'giant': giant, 'ghostword': ghostword, 'boxed': boxed, 'corners': corners, 'circletext': circletext, 'splitswap': splitswap,
     'topcard': topcard, 'vflank': vflank, 'typepanel': typepanel}[t['layout']](t, W, H, FPS, st, work, aroll, out)


# ---------------------------------------------------------------- 小工具
def _opaque(fr):
    return np.dstack([fr, np.full(fr.shape[:2], 255, np.uint8)])


def _gray(fr, amount=1.0):
    g = fr.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    return (fr * (1 - amount) + g[..., None] * amount).astype(np.uint8)


def _mask_out(c, a, k=1.0):
    """人站在字前面：把整屏透明层里人像那块挖掉（a 是 0~1 的抠像透明度）。"""
    c[..., 3] = (c[..., 3] * (1 - np.clip(a * k, 0, 1))).astype(np.uint8)
    return c


def _person(fr, a):
    """口播一帧抠成透明底的人。"""
    return np.dstack([fr, (np.clip(a, 0, 1) * 255).astype(np.uint8)])


def _soft_bg(fr, W, H, dark=0.8, r=3):
    """口播画面糊开当底（先缩小再放大，快）。"""
    im = Image.fromarray(fr).resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r)).resize((W, H), Image.BILINEAR)
    return (np.array(im, np.float32) * dark).astype(np.uint8)


def _head_square(fr, W, H):
    """头像要裁的那块正方形：(中心 x, 中心 y, 边长)，按脸检测，检测不到用画面上部中间。"""
    from effects import face_box
    b = face_box(fr)
    if not b:
        if is_landscape(W, H):
            side, x, y = face_crop(W, H)
            return x + side / 2, y + side / 2, side
        return W / 2, H * 0.33, W * 0.62
    cx, top, fw, fh = b
    side = min(fh * 2.25, W * 0.95)
    if is_landscape(W, H):
        side = min(side, face_crop(W, H)[0])
    return cx, top + fh * 0.6, side


@lru_cache(maxsize=16)
def _disc(D, ring):
    """直径 D 的圆（抗锯齿）和外面一圈宽 ring 的环，返回两张 0~1 透明度。"""
    n = D + 2 * ring
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.hypot(xx - n / 2 + 0.5, yy - n / 2 + 0.5)
    inner = np.clip(D / 2 + 0.5 - d, 0, 1)
    outer = np.clip(D / 2 + ring + 0.5 - d, 0, 1)
    return inner, np.clip(outer - inner, 0, 1)


def _avatar(fr, sq, D, ring=0, ring_col='#FFFFFF'):
    """圆形头像：从画面裁 sq 那块正方形缩成直径 D 的圆，外面一圈白环。"""
    cx, cy, side = sq
    D = int(D)
    ring = int(ring)
    n = D + 2 * ring
    k = side / D
    im = Image.fromarray(fr).transform((n, n), Image.AFFINE, (k, 0, cx - side / 2 - ring * k, 0, k, cy - side / 2 - ring * k), Image.BILINEAR)
    inner, rim = _disc(D, ring)
    rgb = np.array(im, np.float32) * inner[..., None] + np.array(hex_rgba(ring_col)[:3], np.float32) * rim[..., None]
    a = np.clip(inner + rim, 0, 1)
    return np.dstack([(rgb / np.maximum(a, 1e-3)[..., None]).clip(0, 255).astype(np.uint8), (a * 255).astype(np.uint8)])


def _circle_shrink(canvas, fr, sq, ctr, R, k, ring, ring_col):
    """全屏口播收成圆（circle_pip_text 的缩圆入场）：圆心 ctr、半径 R、画面缩放 k（1 是原大，D/边长 是头像大小）。"""
    H, W = canvas.shape[:2]
    rw = ring
    x0, y0 = max(0, int(ctr[0] - R - rw - 2)), max(0, int(ctr[1] - R - rw - 2))
    x1, y1 = min(W, int(ctr[0] + R + rw + 2)), min(H, int(ctr[1] + R + rw + 2))
    if x1 <= x0 or y1 <= y0:
        return
    src = np.array(Image.fromarray(fr).transform((x1 - x0, y1 - y0), Image.AFFINE,
                                                 (1 / k, 0, sq[0] + (x0 - ctr[0]) / k, 0, 1 / k, sq[1] + (y0 - ctr[1]) / k), Image.BILINEAR))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dist = np.hypot(xx - ctr[0], yy - ctr[1])
    m = np.clip(R + 0.5 - dist, 0, 1)[..., None]
    reg = canvas[y0:y1, x0:x1, :3].astype(np.float32)
    rgb = reg * (1 - m) + src * m
    if rw:
        rm = np.clip(np.minimum(dist - R + 0.5, R + rw + 0.5 - dist), 0, 1)[..., None]
        rgb = rgb * (1 - rm) + np.array(hex_rgba(ring_col)[:3], np.float32) * rm
    canvas[y0:y1, x0:x1, :3] = rgb.astype(np.uint8)


def _glyphs(text, fontfile, size, color, stroke=0, stroke_color='#000000'):
    """逐字排一行：每个字一张贴图，返回 [(贴图, 字中心相对笔位的 x, 字中心相对基线的 y)] 和整行宽。
    逐字弹出、打字机这类要一个字一个字出，又要字和字在同一条基线上。"""
    f = ImageFont.truetype(str(fontfile), int(size))
    out, x = [], 0.0
    for c in text:
        adv = f.getlength(c)
        if c.strip():
            l, t_, r, b = f.getbbox(c, anchor='ls', stroke_width=stroke)
            im = Image.new('RGBA', (r - l + 4, b - t_ + 4), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((2 - l, 2 - t_), c, font=f, anchor='ls', fill=hex_rgba(color), stroke_width=stroke,
                                    stroke_fill=hex_rgba(stroke_color))
            out.append((np.array(im), x + (l + r) / 2, (t_ + b) / 2))
        x += adv
    return out, x


def _wrap(text, fontfile, size, maxw):
    """按宽度折行，英文单词不拆开。"""
    f = ImageFont.truetype(str(fontfile), int(size))
    rows = []
    for para in text.replace('\\N', '\n').split('\n'):
        cur = ''
        toks = []
        for ch in para:
            if toks and ch.isascii() and ch.isalnum() and toks[-1][-1:].isascii() and toks[-1][-1:].isalnum():
                toks[-1] += ch
            else:
                toks.append(ch)
        for tk in toks:
            if cur and f.getlength(cur + tk) > maxw:
                rows.append(cur.rstrip())
                cur = tk.lstrip()
            else:
                cur += tk
        rows.append(cur)
    return [r for r in rows if r]


def _hollow(text, size, color, fontfile, stroke, spacing=0, light=False):
    """只剩描边的空心字。"""
    a = text_img(text, size, color, fontfile=fontfile, stroke=stroke, pad=6, spacing=spacing, stroke_color=color if light else '#000000')
    f = text_img(text, size, color, fontfile=fontfile, stroke=0, pad=6 + stroke, spacing=spacing)
    h, w = min(a.shape[0], f.shape[0]), min(a.shape[1], f.shape[1])
    out = a[:h, :w].copy()
    out[..., 3] = np.clip(a[:h, :w, 3].astype(np.int16) - f[:h, :w, 3], 0, 255).astype(np.uint8)
    return trim(out)


def _fit(a, maxw, maxh=None):
    k = min(1.0, maxw / a.shape[1], (maxh / a.shape[0]) if maxh else 1.0)
    return scale(a, k) if k < 1 else a


def _main_title(t, S, W, H, color='#FFFFFF'):
    """主标题（底纹字上面那一行）：白色粗黑柔投影，lead 写一行小字在上面。"""
    rows = []
    if t.get('lead'):
        rows.append(with_shadow(word(t['lead'], 46 * S, '#EDEDED', HEAVY), 6 * S, 0.5))
    rows.append(with_shadow(_fit(word(t['text'], t.get('size', 130) * S, color, HEAVY), W * 0.88), 9 * S, 0.6))
    gap = int(10 * S)
    h = sum(r.shape[0] for r in rows) + gap * (len(rows) - 1)
    wd = max(r.shape[1] for r in rows)
    b = np.zeros((h, wd, 4), np.uint8)
    y = 0
    for r in rows:
        over(b, r, (wd - r.shape[1]) / 2, y)
        y += r.shape[0] + gap
    return b


def _pop(p):
    """弹入：0.4 → 1.12 → 1。"""
    return max(0.05, 0.4 + 0.6 * eback(p))


# ---------------------------------------------------------------- giant 巨字压画面
GIANT_VARIANTS = {
    'metal': '金属浮雕单字：银灰渐变字带亮边和投影，七成不透明压在画面中上部',
    'red_bleed': '半透明红字出血：占半个画面以上的红字被画面边缘裁掉一截，人站在字前面，底下画面变灰',
    'collage': '拼贴底毛笔字：米色旧信纸报纸拼贴底，白色毛笔大字先繁体再溶解成简体，背后淡淡的空心英文',
}


def _metal(text, size, S, maxw):
    m = _fit(word(text, size, '#FFFFFF', SERIF), maxw)
    h = m.shape[0]
    g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    band = np.exp(-((g - 0.42) / 0.07) ** 2) * 0.35   # 中间一道斜面反光
    rgb = np.array([245, 245, 245], np.float32) * (1 - g) + np.array([122, 122, 122], np.float32) * g
    rgb = np.clip(rgb + 255 * band, 0, 255)
    face = m.copy()
    face[..., :3] = np.broadcast_to(rgb, face[..., :3].shape).astype(np.uint8)
    o = max(1, int(2 * S))
    e = np.zeros((h + o, m.shape[1] + o, 4), np.uint8)
    hi = m.copy()
    hi[..., :3] = 255
    over(e, hi, 0, 0)            # 左上一道亮边
    dk = m.copy()
    dk[..., :3] = 70
    over(e, dk, o, o)            # 右下一道暗边
    over(e, face, o / 2, o / 2)
    return with_shadow(e, 8 * S, 0.8, dy=int(6 * S))


def _collage_bg(W, H, seed, en, S):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    base = np.zeros((H, W, 4), np.uint8)
    base[..., :3] = (232, 220, 196)
    base[..., 3] = 255
    im = Image.fromarray(base, 'RGBA')
    papers = ['#F1E7D2', '#DCCDB0', '#E9E0CC', '#CFC0A0', '#F5EFE2', '#E2D3B5']
    for k in range(7):   # 旧信纸、报纸碎片：旋转的纸片，上面横线或灰色字条
        pw, ph = int(W * rng.uniform(0.35, 0.75)), int(H * rng.uniform(0.12, 0.3))
        pc = Image.new('RGBA', (pw, ph), hex_rgba(rng.choice(papers)))
        d = ImageDraw.Draw(pc)
        if k % 2:
            for y in range(int(ph * 0.12), ph, int(26 * S)):
                d.line([(int(pw * 0.06), y), (int(pw * 0.94), y)], fill=(150, 130, 100, 90), width=max(1, int(2 * S)))
        else:
            for y in range(int(ph * 0.1), ph - int(14 * S), int(22 * S)):
                x = int(pw * 0.05)
                while x < pw * 0.92:
                    ln = int(rng.uniform(40, 140) * S)
                    d.rectangle([x, y, min(pw - 4, x + ln), y + int(8 * S)], fill=(90, 80, 70, 70))
                    x += ln + int(rng.uniform(8, 20) * S)
        pc = pc.rotate(rng.uniform(-9, 9), expand=True, resample=Image.BICUBIC)
        sh = Image.new('RGBA', pc.size, (60, 40, 20, 0))
        sh.putalpha(pc.getchannel('A').point(lambda v: int(v * 0.25)))
        x, y = int(rng.uniform(-0.2, 0.75) * W), int(rng.uniform(-0.05, 0.9) * H)
        sh = sh.filter(ImageFilter.GaussianBlur(8 * S))
        im.paste(sh, (x + int(6 * S), y + int(8 * S)), sh)
        im.paste(pc, (x, y), pc)
    a = np.array(im)
    for _ in range(3):   # 茶渍
        st = np.zeros((H, W), np.float32)
        cx, cy, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.08, 0.2) * W
        yy, xx = np.ogrid[0:H, 0:W]
        st[((xx - cx) ** 2 + (yy - cy) ** 2) < r * r] = 1
        st = np.array(Image.fromarray((st * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r * 0.4)), np.float32) / 255 * 0.12
        a[..., :3] = (a[..., :3] * (1 - st[..., None]) + np.array([120, 80, 40]) * st[..., None]).astype(np.uint8)
    grain = nrng.normal(0, 7, (H // 2, W // 2)).astype(np.float32)
    grain = np.array(Image.fromarray(grain).resize((W, H), Image.BILINEAR))
    a[..., :3] = np.clip(a[..., :3] + grain[..., None], 0, 255).astype(np.uint8)
    if en:   # 背后淡淡的空心英文
        h = _fit(_hollow(en.upper(), 300 * S, '#7A6A4A', EN, max(2, int(3 * S)), spacing=int(14 * S)), W * 0.96, H * 0.2)
        put(a, h, W / 2, H * 0.62, 0.45)
    return a


def giant(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'metal')
    dur, n = frames(t, FPS)
    text = t['text']
    seed = int(t['t0'] * 100)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'metal':
        spr = _metal(text, H * t.get('size_h', 0.15), S, W * 0.86)
        cx, cy = W * t.get('x', 0.5), H * t.get('y', 0.6)   # 口播上放胸口，别压脸
        op = t.get('alpha', 0.72)
        if is_landscape(W, H):
            cx, cy = side_anchor(t, W, H)
            l, top, r, bot = side_box(t, W, H)
            spr = fit_sprite(spr, (r - l) * 0.9, (bot - top) * 0.8)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            p = ease(tt / 0.35, 'out')
            put(c, scale(spr, 1.08 - 0.08 * p), cx, cy, op * p * fade_out(tt, dur, 0.25))
            w.put(c)
        w.close()
        return
    if v == 'red_bleed':
        import matte
        col = t.get('color', '#B3121A')
        chars = text[:3]
        # 字从画面右边出血四分之一，压在人身后：人身上的那部分只剩一层淡红
        if len(chars) == 1:
            spr = word(chars, H * t.get('size_h', 0.5), col, HEAVY)
        else:
            spr = trim(text_img(chars, min(H * 0.4, H * 0.86 / len(chars)), col, fontfile=HEAVY, vertical=True, pad=0))
        cx = W - spr.shape[1] * (0.5 - t.get('bleed', 0.25))
        cy = H * t.get('y', 0.3 if len(chars) == 1 else 0.5)
        op = t.get('alpha', 0.78)
        if is_landscape(W, H):
            l, top, r, bot = side_box(t, W, H, t.get('side', 'right'))
            spr = fit_sprite(spr, (r - l) * 0.9, (bot - top) * 0.9)
            cx, cy = (l + r) / 2, (top + bot) / 2
        blurs = [blur(spr, 20 * S * (1 - k / 7)) for k in range(8)]   # 模糊渐显 0.25 秒
        for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
            tt = i / FPS
            q = ease(tt / 0.2)
            base = _opaque(_gray(fr, t.get('desat', 0.75) * q))
            c = np.zeros((H, W, 4), np.uint8)
            k = min(7, int(tt / 0.25 * 7))
            put(c, blurs[k], cx, cy, op * min(1.0, tt / 0.25))
            _mask_out(c, a, t.get('behind', 0.6))   # 人身上只透一层淡红，字形整个还认得出
            over(base, c, 0, 0)
            base[..., 3] = int(255 * fade_out(tt, dur, 0.15))
            w.put(base)
        w.close()
        return
    # collage：拼贴底毛笔字，trad 写繁体就先繁后简
    bg = _collage_bg(W, H, seed, t.get('en'), S)
    def brush(s):
        b = rough(word(s, H * t.get('size_h', 0.25), '#FFFFFF', BRUSH), seed, 0.18)
        b = _fit(b, W * 0.86)
        sd = b.copy()
        sd[..., :3] = (58, 38, 22)
        sh = blur(np.pad(sd, ((20, 20), (20, 20), (0, 0))), 7 * S)
        sh[..., 3] = (sh[..., 3] * 0.7).astype(np.uint8)
        over(sh, b, 20 - 3 * S, 20 - 5 * S)
        return sh
    simp = brush(text)
    trad = brush(t['trad']) if t.get('trad') and t['trad'] != text else None
    swap = t.get('swap_at', 0.7)
    for i in range(n):
        tt = i / FPS
        z = 1 + 0.04 * tt / max(dur, 0.1)   # 底图缓推
        c = resize(bg, W * z, H * z)
        oy, ox = (c.shape[0] - H) // 2, (c.shape[1] - W) // 2
        c = c[oy:oy + H, ox:ox + W].copy()
        p = ease(tt / 0.3, 'out')
        if trad is not None:
            q = _clamp((tt - swap) / 0.3)
            put(c, trad, W / 2, H * 0.42, p * (1 - q))
            put(c, simp, W / 2, H * 0.42, q)
        else:
            put(c, scale(simp, 1.06 - 0.06 * p), W / 2, H * 0.42, p)
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- ghostword 巨字底纹装饰
GHOST_VARIANTS = {
    'hollow': '空心描边英文：极大的全大写英文只剩白色细描边、字距拉开，压在人身后，主标题在前面',
    'emboss': '同色系浮雕中文：整屏红色纹理底上一个比底色只深一点的巨字像压纹，人站在前面，主标题压在上面',
    'edge': '贴边竖排英文：英文单词转 90 度竖贴在画面左边，长度顶满画面高，一半出画',
    'grunge': '两侧做旧灰字：纯黑底左右两列被裁掉一半的深灰做旧粗字，中间一行小白字加一个卡其色大字问句',
}


def _paper_noise(W, H, rgb, seed, amt=10):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, amt, (H // 3, W // 3)).astype(np.float32)
    n = np.array(Image.fromarray(n).resize((W, H), Image.BICUBIC))
    fib = rng.normal(0, amt * 0.6, (H // 12, W)).astype(np.float32)   # 横向纤维
    fib = np.array(Image.fromarray(fib).resize((W, H), Image.BILINEAR))
    a = np.zeros((H, W, 4), np.uint8)
    a[..., :3] = np.clip(np.array(rgb, np.float32) + (n + fib)[..., None], 0, 255).astype(np.uint8)
    a[..., 3] = 255
    return a


def _grunge(a, seed):
    """做旧：大块掉色加细划痕。"""
    a = rough(a, seed, 0.45)
    rng = random.Random(seed)
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    for _ in range(14):
        x, y = rng.uniform(0, a.shape[1]), rng.uniform(0, a.shape[0])
        d.line([(x, y), (x + rng.uniform(-80, 80), y + rng.uniform(-6, 6))], fill=(0, 0, 0, 0), width=rng.randint(2, 5))
    return np.array(im)


def ghostword(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    v = t.get('variant', 'hollow')
    dur, n = frames(t, FPS)
    seed = int(t['t0'] * 100)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'grunge':
        side = t.get('left') or t['text'][:2]
        side2 = t.get('right') or side
        def col(s, sd):
            c = trim(text_img(s, H * 0.22, '#5A5A5A', fontfile=HEAVY, vertical=True, pad=0))
            return _grunge(_fit(c, W * 0.22 if is_landscape(W, H) else W, H * (0.62 if is_landscape(W, H) else 0.96)), sd)
        L, R = col(side, seed), col(side2, seed + 7)
        mid = []
        if t.get('lead'):
            mid.append(word(t['lead'], 40 * S, '#FFFFFF', HEAVY))
        mid.append(_fit(word(t['text'], H * 0.07, '#C9BC8C', HEAVY), W * 0.62))
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            c[..., 3] = 255
            c[..., :3] = 10
            p = ease(tt / 0.4, 'out')
            put(c, L, W * 0.18 if is_landscape(W, H) else L.shape[1] * 0.2 - W * 0.02 * (1 - p), H * 0.45 if is_landscape(W, H) else H * 0.5, p)   # 一半出画
            put(c, R, W * 0.82 if is_landscape(W, H) else W - R.shape[1] * 0.2 + W * 0.02 * (1 - p), H * 0.45 if is_landscape(W, H) else H * 0.5, p)
            y = H * 0.44
            for j, m in enumerate(mid):
                q = ease((tt - 0.15 - 0.2 * j) / 0.3, 'out')
                put(c, m, W / 2, y + m.shape[0] / 2 + (1 - q) * 20 * S, q)
                y += m.shape[0] + 28 * S
            c[..., 3] = (c[..., 3] * min(1.0, tt / 0.1) * fade_out(tt, dur, 0.15)).astype(np.uint8)
            w.put(c)
        w.close()
        return
    main = _main_title(t, S, W, H) if t.get('text') else None
    my = H * t.get('y', 0.64)
    mx = W / 2
    if is_landscape(W, H) and main is not None:
        l, top, r, bot = side_box(t, W, H, 'right' if v == 'emboss' else None)
        main = fit_sprite(main, (r - l) * 0.92, (bot - top) * 0.7)
        mx, my = (l + r) / 2, (top + bot) / 2
    if v == 'emboss':
        bgc = hex_rgba(t.get('bg', '#B0232A'))[:3]
        page = _paper_noise(W, H, bgc, seed)
        g = word(t.get('ghost') or t['text'], H * 0.3, '#FFFFFF', HEAVY)
        g = _fit(g, W * 0.78, H * 0.5)
        ink = g.copy()
        ink[..., :3] = (np.array(bgc) * 0.8).astype(np.uint8)
        sd = g.copy()
        sd[..., :3] = (np.array(bgc) * 0.45).astype(np.uint8)
        s_, p_ = shadow(sd, 22 * S, 0.5, dy=int(H * 0.015))
        s_[..., :3] = (np.array(bgc) * 0.45).astype(np.uint8)
        over(s_, ink, p_, p_)
        ghost_y = H * t.get('ghost_y', 0.3)
        ghost_x = W / 2
        if is_landscape(W, H):
            s_ = fit_sprite(s_, W * 0.45, H * 0.58)
            ghost_x, ghost_y = W * 0.3, H * 0.43
        for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
            tt = i / FPS
            c = page.copy()
            put(c, s_, ghost_x, ghost_y, ease(tt / 0.4))
            if t.get('person'):   # 默认整页海报不放人；写 person 让人站在纸前面（巨字会被挡住大半）
                over(c, _person(fr, a), 0, 0)
            if main is not None:
                q = ease((tt - 0.25) / 0.3, 'out')
                put(c, main, mx, my + (1 - q) * 24 * S, q)
            c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    if v == 'edge':
        fr0 = next(read(aroll, t['t0'], 1 / FPS, (W, H), FPS))
        light = fr0[:, :int(W * 0.15)].mean() / 255 > 0.55   # 左边是浅色墙就用深色字，不然白字看不见
        col = t.get('color', '#202024' if light else '#FFFFFF')
        g = text_img((t.get('en') or t['text']).upper(), H * 0.3, col, fontfile=BEBAS, pad=0, spacing=int(6 * S))
        g = rotate_rgba(trim(g), 90)
        g = scale(g, H * 1.0 / g.shape[0])
        gx, gy, ga = g.shape[1] * 0.0, H / 2, t.get('ghost_alpha', 0.4 if light else 0.35)   # 中心贴左边：一半出画
    else:
        sp = int(t.get('tracking', 0.35) * 260 * S)
        g = _hollow((t.get('en') or t['text']).upper(), 260 * S, '#FFFFFF', EN, max(3, int(4 * S)), spacing=sp, light=is_landscape(W, H))
        g = _fit(g, W * 1.1, H * 0.32)
        gx, gy, ga = W / 2, H * t.get('ghost_y', 0.22), t.get('ghost_alpha', 0.85)
    if is_landscape(W, H):
        l, top, r, bot = side_box(t, W, H, 'left' if mx > W / 2 else 'right')
        g = fit_sprite(g, (r - l) * 0.9, (bot - top) * 0.9)
        gx, gy = (l + r) / 2, (top + bot) / 2
    behind = t.get('behind', True)
    src = matte.frames(aroll, t['t0'], dur, W, H, FPS) if behind else ((None, None) for _ in range(n))
    for i, (fr, a) in enumerate(src):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.4)
        gs = g if v == 'edge' else scale(g, 1 + 0.02 * tt / max(dur, 0.1))   # 停留期间缓放 2%
        put(c, gs, gx, gy, ga * p * fade_out(tt, dur, 0.2))
        if behind and a is not None:
            _mask_out(c, a)
        if main is not None:
            q = ease((tt - 0.2) / 0.3, 'out')
            put(c, main, mx, my + (1 - q) * 24 * S, q * fade_out(tt, dur, 0.2))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- boxed 方框单字标题
def boxed(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    chars = [c for c in t['text'] if c.strip()][:t.get('max_chars', 4)]
    m = len(chars)
    fs = min(W * 0.15, W * 0.9 / (m * 1.25 + (m - 1) * 0.12) / 1.0)
    if is_landscape(W, H):
        l, top, r, bot = side_box(t, W, H)
        fs = min(110 * S, (r - l) / 3.1)
    side = fs * 1.25
    gap = fs * 0.12
    bw = max(2, int(2 * S))
    tiles = []
    for ch in chars:
        tile = np.zeros((int(side) + 8, int(side) + 8, 4), np.uint8)
        im = Image.fromarray(tile)
        ImageDraw.Draw(im).rectangle([4, 4, 4 + side, 4 + side], outline=(255, 255, 255, 255), width=bw)
        tile = np.array(im)
        g = word(ch, fs, '#FFFFFF', SERIF)
        hard = g.copy()   # 立体阴影：一层偏移 3px 的硬投影加一层柔投影
        hard[..., :3] = 0
        hard[..., 3] = (hard[..., 3] * 0.5).astype(np.uint8)
        put(tile, blur(np.pad(hard, ((10, 10), (10, 10), (0, 0))), 4 * S), tile.shape[1] / 2 + 3 * S, tile.shape[0] / 2 + 3 * S)
        put(tile, g, tile.shape[1] / 2, tile.shape[0] / 2)
        tiles.append(tile)
    total = m * side + (m - 1) * gap
    x0 = W * t.get('x', 0.5) - total / 2
    y = H * t.get('y', 0.64)
    note = []
    if t.get('tag'):
        note.append(with_shadow(word(t['tag'], 54 * S, '#F5C518', HEAVY), 5 * S, 0.5))
    if t.get('sub'):
        note.append(with_shadow(_fit(word(t['sub'], 38 * S, '#FFFFFF', HEAVY), W * 0.86), 5 * S, 0.5))
    if is_landscape(W, H):
        note = [fit_sprite(g, (r - l) * 0.9, H * 0.1) for g in note]
        x0, y = (l + r) / 2 - side - gap / 2, top + side * 0.8
    behind = t.get('behind', False)
    if behind:
        import matte
        src = matte.frames(aroll, t['t0'], dur, W, H, FPS)
    else:
        src = ((None, None) for _ in range(n))
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(src):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        fo = fade_out(tt, dur, 0.2)
        for j, tile in enumerate(tiles):   # 依次从上方一成画面高处落下，0.25 秒缓出
            p = ease((tt - 0.07 * j) / 0.25, 'out')
            if p <= 0:
                continue
            put(c, tile, x0 + (j % 2 if is_landscape(W, H) else j) * (side + gap) + side / 2,
                y + (j // 2) * (side + gap) - H * 0.1 * (1 - p) if is_landscape(W, H) else y - H * 0.1 * (1 - p), min(1.0, p * 2) * fo)
        if behind and a is not None:
            _mask_out(c, a)
        ny = y + side * 0.62 + 18 * S
        if is_landscape(W, H):
            ny += ((m + 1) // 2 - 1) * (side + gap)
        for j, nt in enumerate(note):
            q = ease((tt - 0.07 * m - 0.15 - 0.12 * j) / 0.25, 'out')
            put(c, nt, (l + r) / 2 if is_landscape(W, H) else W * t.get('x', 0.5), ny + nt.shape[0] / 2, q * fo)
            ny += nt.shape[0] + 8 * S
        w.put(c)
    w.close()


# ---------------------------------------------------------------- corners 四角分字围人
CORNER_VARIANTS = {
    'four': '四字四角：一个四字词拆开，上排两字贴顶部左右、下排两字在胸口高度，两字一组先后弹出，其中一字换色',
    'shrink': '画面缩到中间：口播缩到画面中间，四个字在四角围住它',
    'flank': '两字夹头：两个字左右夹住头部，常用于结尾口号',
}


def _corner_char(ch, h, color, S):
    g = word(ch, h, color, HEAVY, stroke=int(5 * S), stroke_color='#111111')
    return with_shadow(g, 6 * S, 0.55, dy=int(4 * S))


def corners(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'four')
    dur, n = frames(t, FPS)
    chars = [c for c in t['text'] if c.strip()]
    cols = t.get('colors') or ['#FFC21A'] * len(chars)
    alt = t.get('alt', len(chars) - 1)   # 一字换色
    if 'colors' not in t and 0 <= alt < len(cols):
        cols[alt] = t.get('alt_color', '#F7C6CC')
    at = t.get('item_at')
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'flank':
        fr0 = next(read(aroll, t['t0'] + min(0.3, dur / 2), 1 / FPS, (W, H), FPS))
        from effects import face_box
        b = face_box(fr0) or (W / 2, H * 0.14, W * 0.32, H * 0.22)
        cx, top, fw, fh = b
        h = min(fh * 0.6, H * 0.11)
        sprs = [_corner_char(c, h, cols[j % len(cols)], S) for j, c in enumerate(chars[:2])]
        cy = top + fh * 0.5
        pos = [(cx - fw * 0.55 - sprs[0].shape[1] * 0.55, cy), (cx + fw * 0.55 + sprs[-1].shape[1] * 0.55, cy)]
        pos = [(min(max(x, sprs[0].shape[1] * 0.55), W - sprs[0].shape[1] * 0.55), y) for x, y in pos]
        if is_landscape(W, H):
            pos = [((b[0] + b[2]) / 2, H * 0.4) for b in (side_box(t, W, H, 'left'), side_box(t, W, H, 'right'))]
        starts = at or [0.0, 0.15]
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            for j, (spr, (x, y)) in enumerate(zip(sprs, pos)):
                p = (tt - starts[min(j, len(starts) - 1)]) / 0.25
                if p > 0:
                    put(c, scale(spr, _pop(p)), x, y, min(1.0, p * 3) * fade_out(tt, dur))
            w.put(c)
        w.close()
        return
    h = H * t.get('size_h', 0.085)
    sprs = [_corner_char(c, h, cols[j % len(cols)], S) for j, c in enumerate(chars[:4])]
    if v == 'shrink':
        pos = [(W * 0.13, H * 0.3), (W * 0.87, H * 0.3), (W * 0.13, H * 0.68), (W * 0.87, H * 0.68)]
    else:
        pos = [(W * 0.15, H * 0.08), (W * 0.85, H * 0.08), (W * 0.15, H * 0.42), (W * 0.85, H * 0.42)]
    if is_landscape(W, H):
        pos = [(W * 0.17, H * 0.26), (W * 0.83, H * 0.26), (W * 0.17, H * 0.62), (W * 0.83, H * 0.62)]
    starts = at or [0.0, 0.0, 0.3, 0.3]
    if v == 'shrink':
        src = read(aroll, t['t0'], dur, (W, H), FPS)
        sk = t.get('shrink_to', 0.5)
    for i in range(n):
        tt = i / FPS
        if v == 'shrink':   # 口播 0.25 秒缩到画面中间，黑底，细白边
            fr = next(src)
            k = 1 - (1 - sk) * ease(tt / 0.25, 'out')
            c = np.zeros((H, W, 4), np.uint8)
            c[..., 3] = 255
            c[..., :3] = 12
            sw, sh = int(W * k), int(H * k)
            f = resize(fr, sw, sh)
            bw = int(4 * S)
            x0, y0 = (W - sw) // 2, (H - sh) // 2
            c[max(0, y0 - bw):y0 + sh + bw, max(0, x0 - bw):x0 + sw + bw, :3] = 245
            c[y0:y0 + sh, x0:x0 + sw, :3] = f
        else:
            c = np.zeros((H, W, 4), np.uint8)
        for j, (spr, (x, y)) in enumerate(zip(sprs, pos)):
            d0 = starts[min(j, len(starts) - 1)] + (0.25 if v == 'shrink' else 0)
            p = (tt - d0) / 0.25
            if p > 0:
                put(c, scale(spr, _pop(p)), x, y, min(1.0, p * 3))
        if v == 'shrink':
            c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
        else:
            c[..., 3] = (c[..., 3] * fade_out(tt, dur)).astype(np.uint8)
        w.put(c)
    w.close()


# ---------------------------------------------------------------- circletext 圆形头像配环绕字
CIRCLE_VARIANTS = {
    'arc': '弧形徽章字：人缩成圆头像，上方一行字顺着圆顶弯曲，下方一行沿圆底弯曲，像印章',
    'tangent': '并列词贴圆周：三个黄色粗字依次贴着圆周出现，左下、右下沿切线倾斜，正上方水平',
    'sandwich': '大字上下夹头像：白色粗圆环把全屏人物快速缩成圆，圆上下各压一行红黄大字',
}


def _arc_chars(text, hl, R, size, top, S):
    """沿圆弧排字：top=True 在圆顶（字头朝外），否则在圆底（字头朝圆心），都从左往右读。返回 [(贴图, 角度)]。"""
    sprs = [_corner_char(c, size, '#F5C518' if c in ''.join(hl or []) else '#FFFFFF', S * 0.8) for c in text]
    step = np.degrees(size * 1.12 / R)
    m = len(sprs)
    out = []
    for j, s in enumerate(sprs):
        if top:
            th = -90 + (j - (m - 1) / 2) * step
            rot = -(th + 90)
        else:
            th = 90 + ((m - 1) / 2 - j) * step
            rot = -(th - 90)
        out.append((rotate_rgba(s, rot), th))
    return out


def circletext(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'arc')
    dur, n = frames(t, FPS)
    frs = list(read(aroll, t['t0'], dur, (W, H), FPS))
    sq = _head_square(frs[min(len(frs) - 1, int(0.3 * FPS))], W, H)
    D = W * (0.55 if v == 'sandwich' else t.get('d', 0.46))
    ctr = np.array([W / 2, H * t.get('y', 0.47 if v == 'sandwich' else 0.42)])
    if is_landscape(W, H):
        pp = pip_params({}, st)
        D = W * pp['d']
        ctr = np.array([W - H * 0.28, H * 0.25])
    ring = int((12 if v == 'sandwich' else 6) * S)
    shrink = t.get('shrink_s', 0.3)
    R0 = float(np.hypot(W, H))
    sq_c = np.array(sq[:2])
    kD = D / sq[2]
    layers = []   # (贴图, x, y, 出现时刻)
    if v == 'arc':
        r = D / 2 * 1.1 + H * 0.03
        sz = H * (0.035 if is_landscape(W, H) else 0.05)
        text_ctr = ctr
        if is_landscape(W, H):
            r, sz = H * 0.28, H * 0.065
            text_ctr = np.array([W * 0.32, H * 0.45])
        k = 0
        for txt, top in ((t.get('text'), True), (t.get('text2'), False)):
            if not txt:
                continue
            for spr, th in _arc_chars(txt, t.get('hl'), r, sz, top, S):
                layers.append((spr, text_ctr[0] + np.cos(np.radians(th)) * r, text_ctr[1] + np.sin(np.radians(th)) * r, shrink + 0.05 * k))
                k += 1
    elif v == 'tangent':
        items = (t.get('items') or [])[:3]
        ang, rot = [145, 35, -90], [-50, 50, 0]
        ats = t.get('item_at') or [shrink + 0.15 + 0.4 * j for j in range(len(items))]
        for j, it in enumerate(items):
            g = word(it, H * (0.11 if is_landscape(W, H) else 0.055), '#FFE36A', HEAVY, stroke=int(6 * S), stroke_color='#111111')
            g = rotate_rgba(with_shadow(g, 6 * S, 0.5), rot[j])
            r = D / 2 + ring + max(g.shape[:2]) * 0.42
            th = np.radians(ang[j])
            layers.append((g, ctr[0] + np.cos(th) * r, ctr[1] + np.sin(th) * r, max(shrink, ats[j] or 0)))
    else:   # sandwich
        top = _fit(word(t['text'], H * 0.085, '#E8342E', HEAVY, stroke=int(7 * S), stroke_color='#FFFFFF'), W * 0.92)
        bot = _fit(word(t.get('text2') or '', H * 0.085, '#F5C518', HEAVY, stroke=int(7 * S), stroke_color='#111111'), W * 0.92) \
            if t.get('text2') else None
        layers.append((with_shadow(top, 8 * S, 0.55), W / 2, ctr[1] - D / 2 - top.shape[0] * 0.5, shrink))
        if bot is not None:
            layers.append((with_shadow(bot, 8 * S, 0.55), W / 2, ctr[1] + D / 2 + bot.shape[0] * 0.5 - D * 0.1, shrink + 0.15))
    if is_landscape(W, H):
        if v == 'sandwich':
            layers = [(fit_sprite(g, W * 0.52, H * 0.18), W * 0.34, H * (0.35 + j * 0.23), a) for j, (g, _, _, a) in enumerate(layers)]
        elif v == 'tangent':
            layers = [(fit_sprite(g, W * 0.17, H * 0.23), W * (0.16 + j * 0.2), H * (0.45 + (j % 2) * 0.08), a)
                      for j, (g, _, _, a) in enumerate(layers)]
    bgs = bg_frames(t.get('bg', 'blur'), W, H, FPS, n, work, aroll, t['t0'])
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        bg = next(bgs)
        c[..., :3] = bg if bg is not None else 14
        p = ease(tt / shrink, 'out')
        R = R0 + (D / 2 - R0) * p
        k = 1 + (kD - 1) * ease(_clamp((R0 - R) / (R0 - D / 2) * 1.6 - 0.6))   # 先收圆、圆比头像那块小了再连画面一起缩
        cc = sq_c + (ctr - sq_c) * p
        _circle_shrink(c, frs[min(i, len(frs) - 1)], sq, cc, R, k, ring if R < R0 * 0.6 else 0, '#FFFFFF')
        for spr, x, y, d0 in layers:
            q = (tt - d0) / 0.22
            if q > 0:
                put(c, scale(spr, _pop(q)), x, y, min(1.0, q * 3))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- splitswap 分屏圆头像巨字轮换
def splitswap(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return landscape_splitswap(t, W, H, FPS, st, aroll, out)
    S = unit(W, H)
    dur, n = frames(t, FPS)
    th = int(H * t.get('top_h', 0.47))
    s_in = t.get('src_in', 0)
    avail = dur if is_image(t['src']) else min(dur, max(1 / FPS, probe(t['src'])['duration'] - s_in))
    tops = list(read(t['src'], s_in, avail, (W, th), FPS, crop=t.get('crop')))   # 录屏比这段短就放慢铺满，不停在最后一帧
    frs = list(read(aroll, t['t0'], dur, (W, H), FPS))
    sq = _head_square(frs[min(len(frs) - 1, int(0.3 * FPS))], W, H)
    D = int(W * t.get('d', 0.47))
    ring = int(6 * S)
    items = t.get('items') or []
    ats = t.get('item_at') or [0.25 + 0.8 * j for j in range(len(items))]
    ats = [a if a is not None else 0.25 + 0.8 * j for j, a in enumerate(ats)]
    words = [with_shadow(_fit(word(x, H * t.get('word_h', 0.11), '#FFFFFF', SERIF), W * 0.9), 10 * S, 0.6) for x in items]
    wy = H * t.get('word_y', 0.71)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        c[..., :3] = 8
        p = ease(tt / 0.25, 'out')
        top = tops[min(len(tops) - 1, int(i * len(tops) / n))]
        oy = int(-th * 0.15 * (1 - p))   # 上半屏素材往下落定
        c[max(0, oy):th + oy, :, :3] = top[max(0, -oy):, :]
        av = _avatar(frs[min(i, len(frs) - 1)], sq, D, ring)
        put(c, scale(av, 0.6 + 0.4 * eback(tt / 0.3)), W / 2, H * t.get('pip_y', 0.5), min(1.0, tt / 0.12))
        j = max([k for k, a in enumerate(ats) if a <= tt + 1e-6], default=None)
        if j is not None:
            q = _clamp((tt - ats[j]) / 0.15)
            put(c, scale(words[j], 1.2 - 0.2 * ease(q, 'out')), W / 2, wy, min(1.0, q * 2.5))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


def landscape_splitswap(t, W, H, FPS, st, aroll, out):
    """横屏用左素材、右关键词，小圆头像独立放右上角。"""
    S = unit(W, H)
    dur, n = frames(t, FPS)
    sw, sh = int(W * 0.58) // 2 * 2, int(H * 0.66) // 2 * 2
    s_in = t.get('src_in', 0)
    avail = dur if is_image(t['src']) else min(dur, max(1 / FPS, probe(t['src'])['duration'] - s_in))
    tops = list(read(t['src'], s_in, avail, (sw, sh), FPS, crop=t.get('crop')))
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    items = t.get('items') or []
    ats = t.get('item_at') or []
    ats = [ats[j] if j < len(ats) and ats[j] is not None else 0.25 + 0.8 * j for j in range(len(items))]
    words = [with_shadow(_fit(word(x, 120 * S, '#FFFFFF', SERIF), W * 0.25, H * 0.22), 8 * S, 0.6) for x in items]
    pp = pip_params({}, st)
    D = int(W * pp['d'])
    ring = int(6 * S)
    px = min(W * pp['x'], W * 0.95 - D / 2 - ring)
    py = max(H * pp['y'], H * 0.05 + D / 2 + ring)
    sq = None
    w = Writer(out, W, H, FPS, alpha=True)
    for i, fr in enumerate(frs):
        tt = i / FPS
        if sq is None:
            sq = _head_square(fr, W, H)
        c = np.full((H, W, 4), (8, 8, 8, 255), np.uint8)
        p = ease(tt / 0.25, 'out')
        top = tops[min(len(tops) - 1, int(i * len(tops) / n))]
        over(c, _opaque(top), W * 0.05, H * 0.1 - (1 - p) * H * 0.04, p)
        av = _avatar(fr, sq, D, ring)
        put(c, av, px, py, p)
        j = max([k for k, a in enumerate(ats) if a <= tt], default=-1)
        if j >= 0:
            q = ease((tt - ats[j]) / 0.18, 'out')
            put(c, scale(words[j], 1.1 - 0.1 * q), W * 0.8, H * 0.56, q)
        c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- topcard 顶部整句章节标题卡
def topcard(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    text = t['text']
    rows = _wrap(text, HEAVY, 80 * S, W * 0.78) if len(text) > 9 else [text]
    fs = min(86 * S, W * 0.78 / max(len(r) for r in rows) * 1.02)
    rows = _wrap(text, HEAVY, fs, W * 0.8)
    if is_landscape(W, H):
        fs = 80 * S
        rows = _wrap(text, HEAVY, fs, W * 0.46)
    ink = t.get('ink', '#1A1A1A')
    gl = [_glyphs(r, HEAVY, fs, ink) for r in rows]
    lh = fs * 1.28
    pad_x, pad_y = 44 * S, 30 * S
    bw = max(wd for _, wd in gl) + pad_x * 2
    bh = lh * len(rows) + pad_y * 2 - (lh - fs) * 0.6
    by = H * t.get('y', 0.18) - bh / 2
    bx = W / 2
    if is_landscape(W, H):
        bx = W * 0.31
        by = H * 0.4 - bh / 2
    block = Image.new('RGBA', (int(bw) + 40, int(bh) + 40), (0, 0, 0, 0))
    ImageDraw.Draw(block).rounded_rectangle([20, 20, 20 + bw, 20 + bh], radius=int(28 * S), fill=hex_rgba(t.get('color', '#FFD23F')))
    block = np.array(block)
    sd = block.copy()
    sd[..., :3] = 0
    sd = blur(sd, 12 * S)
    sd[..., 3] = (sd[..., 3] * 0.45).astype(np.uint8)
    kicker = None
    if t.get('number') is not None:
        kicker = with_shadow(word(f"PART {int(str(t['number']).lstrip('0') or 0):02d}", 34 * S, '#FFFFFF', HEAVY, spacing=int(6 * S)), 5 * S, 0.6)
    per = t.get('per_char', 0.08)
    sk = t.get('person_scale', 0.71)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        q = ease(tt / 0.35, 'out')
        c = _opaque(_soft_bg(fr, W, H, 0.85))
        if q < 1:   # 刚进来时从清楚的原画面糊开
            c[..., :3] = (fr * (1 - q) + c[..., :3] * q).astype(np.uint8)
        k = 1 - (1 - sk) * q   # 人缩小，脚底贴着画面下沿
        pp = scale(_person(fr, a), k)
        over(c, pp, (W * 0.77 if is_landscape(W, H) else W / 2) - pp.shape[1] / 2, H - pp.shape[0])
        p = ease((tt - 0.1) / 0.4)
        put(c, sd, bx, by + bh / 2 + 12 * S, p)
        put(c, block, bx, by + bh / 2, p)
        if kicker is not None:
            put(c, kicker, bx, by - kicker.shape[0] * 0.6, p)
        m = 0
        for r, (gs, wd) in enumerate(gl):
            ox = bx - wd / 2
            base = by + pad_y + fs * 0.88 + r * lh
            for spr, gx, gy in gs:   # 逐字弹出
                e = (tt - 0.25 - per * m) / 0.18
                m += 1
                if e > 0:
                    put(c, scale(spr, 1 + 0.35 * (1 - eback(e))), ox + gx, base + gy, min(1.0, e * 2))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.2))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- vflank 竖排双列夹主体章节页
def _silver_col(text, h, S):
    g = trim(text_img(text, h, '#FFFFFF', fontfile=SERIF, vertical=True, pad=0))
    yy = np.linspace(0, 1, g.shape[0], dtype=np.float32)
    per = (yy * len(text)) % 1.0   # 每个字自己一段从亮到暗的金属渐变
    rgb = 250 - 120 * per
    g[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)[:, None, None]
    glow = g.copy()
    glow[..., :3] = 255
    gl = blur(np.pad(glow, ((30, 30), (30, 30), (0, 0))), 14 * S)
    gl[..., 3] = (gl[..., 3] * 0.45).astype(np.uint8)
    over(gl, g, 30, 30)
    return gl


def _space_bg(W, H, seed):
    rng = np.random.default_rng(seed)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    c = np.array([10, 14, 38], np.float32) * (1 - yy) + np.array([34, 46, 96], np.float32) * yy
    a = np.zeros((H, W, 4), np.uint8)
    a[..., :3] = np.broadcast_to(c, (H, W, 3)).astype(np.uint8)
    a[..., 3] = 255
    for _ in range(220):
        x, y, b = rng.integers(0, W), rng.integers(0, H), rng.uniform(0.3, 1)
        r = 1 if b < 0.8 else 2
        a[max(0, y - r):y + r, max(0, x - r):x + r, :3] = int(255 * b)
    return a


def vflank(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    text = t['text'].replace(' ', '')
    cut = t.get('cut', (len(text) + 1) // 2)
    lt, rt = t.get('left') or text[:cut], t.get('right') or text[cut:]
    ch = H * t.get('char_h', 0.08)
    L, R = _silver_col(lt, ch, S), (_silver_col(rt, ch, S) if rt else None)
    if is_landscape(W, H):
        L = fit_sprite(L, W * 0.22, H * 0.5)
        R = fit_sprite(R, W * 0.22, H * 0.5) if R is not None else None
    if t.get('bg_src'):
        bg0 = _opaque(next(read(t['bg_src'], 0, 1 / FPS, (W, H), FPS)))
        bg0[..., :3] = (bg0[..., :3] * 0.7).astype(np.uint8)
    else:
        bg0 = _space_bg(W, H, int(t['t0'] * 100))
    subj = None
    if t.get('subject'):
        s = np.array(Image.open(t['subject']).convert('RGBA'))
        subj = _fit(s, W * 0.5, H * 0.5)
    top = []
    if t.get('number') is not None or t.get('en'):
        lab = ' · '.join(x for x in (f"{int(str(t.get('number')).lstrip('0') or 0):02d}" if t.get('number') is not None else '',
                                     (t.get('en') or '').upper()) if x)
        top.append(word(lab, 30 * S, '#C9CED8', HEAVY, spacing=int(8 * S)))
    src = matte.frames(aroll, t['t0'], dur, W, H, FPS) if subj is None else ((None, None) for _ in range(n))
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(src):
        tt = i / FPS
        fl = lambda ph: H * 0.01 * np.sin(2 * np.pi * tt / 4 + ph)   # 各层周期 4 秒、幅度 1% 画面高的缓慢浮动
        z = 1 + 0.04 * tt / max(dur, 0.1)
        c = resize(bg0, W * z, H * z)
        oy, ox = (c.shape[0] - H) // 2, (c.shape[1] - W) // 2
        c = c[oy:oy + H, ox:ox + W].copy()
        p = ease(tt / 0.5, 'out')
        put(c, L, W * 0.17, H * (0.17 if is_landscape(W, H) else 0.19) + L.shape[0] / 2 + fl(1.3) - (1 - p) * 40 * S, p)
        if R is not None:
            put(c, R, W * 0.83, H * (0.23 if is_landscape(W, H) else 0.32) + R.shape[0] / 2 + fl(3.9) + (1 - p) * 40 * S, p)
        if subj is not None:
            g = subj.copy()
            g[..., :3] = 255
            put(c, blur(np.pad(g, ((40, 40), (40, 40), (0, 0))), 22 * S), W / 2, H * 0.58 + fl(2.6), 0.5 * p)
            put(c, subj, W / 2, H * 0.58 + fl(2.6), p)
        else:   # 没给主体物就把人抠出来立在中间，带一圈柔光
            pk = t.get('person_scale', 0.64)
            pp = scale(_person(fr, a), pk)
            gl = pp.copy()
            gl[..., :3] = 255
            gl = blur(scale(gl, 0.25), 6 * S)
            gl[..., 3] = (gl[..., 3] * 0.55).astype(np.uint8)
            gl = scale(gl, 4.0)
            y0 = H - pp.shape[0] + fl(2.6)
            put(c, gl, W / 2, y0 + pp.shape[0] / 2, p)
            over(c, pp, W / 2 - pp.shape[1] / 2, y0, p)
        for j, m in enumerate(top):
            put(c, m, W / 2, H * 0.1, ease((tt - 0.3) / 0.4))
        c[..., 3] = int(255 * min(1.0, tt / 0.15) * fade_out(tt, dur, 0.25))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- typepanel 打字机长文面板
TYPEPANEL_VARIANTS = {
    'accumulate': '面板逐行累加：半透明蓝灰圆角面板里一行行打出原文，上一句留着，满了整体上滚，末尾白色方块光标',
    'top_card': '顶部长文卡：画面上方黄色条纹字把一段长文逐字打满，人缩在下方',
}


def _stripe(g, S, c1=(255, 216, 74), c2=(232, 168, 0)):
    """黄色条纹字：横向一深一浅的条纹填充。"""
    yy = np.arange(g.shape[0])[:, None]
    band = ((yy // max(2, int(5 * S))) % 2).astype(np.float32)[..., None]
    rgb = np.array(c1, np.float32) * (1 - band) + np.array(c2, np.float32) * band
    out = g.copy()
    inner = g[..., :3].mean(-1, keepdims=True) > 128   # 只给字芯上条纹，描边保留深色
    out[..., :3] = np.where(inner, rgb, g[..., :3]).astype(np.uint8)
    return out


def typepanel(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'accumulate')
    dur, n = frames(t, FPS)
    lines = t.get('lines') or [t['text']]
    cps = t.get('cps', 7.0)
    if v == 'top_card':
        fs = 64 * S
        maxw = W * 0.86
    else:
        fs = 56 * S
        maxw = W * 0.86 - 2 * 46 * S
    font = TYPE if v == 'accumulate' else HEAVY
    if is_landscape(W, H):
        l, top, right, bot = side_box(t, W, H)
        if v == 'top_card':
            l, right = W * 0.06, W * 0.58
        fs = (46 if v == 'accumulate' else 56) * S
        maxw = right - l - 92 * S
    rows = []   # (第几句, 这一行的字)
    for k, ln in enumerate(lines):
        for r in _wrap(ln, font, fs, maxw):
            rows.append((k, r))
    # 每个字出现的时刻：每句从 line_at（说到那句的时刻）或接着上一句开始，按 cps 一个字一个字打
    starts = t.get('line_at') or []
    times, cur = [], t.get('delay', 0.3)
    for k, ln in enumerate(lines):
        if k < len(starts) and starts[k] is not None:
            cur = max(cur, starts[k])
        for r in [r for kk, r in rows if kk == k]:
            times.append([cur + j / cps for j in range(len(r))])
            cur += len(r) / cps
        cur += 0.25
    stroke = int(5 * S) if v == 'top_card' else 0
    gl = [_glyphs(r, font, fs, '#FFFFFF' if v == 'accumulate' else '#FFFFFF', stroke, '#2A1A00') for _, r in rows]
    if v == 'top_card':
        gl = [([(_stripe(s, S), gx, gy) for s, gx, gy in gs], wd) for gs, wd in gl]
    lh = fs * 1.45
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'accumulate':
        maxl = t.get('max_lines', 6)
        if is_landscape(W, H):
            maxl = min(maxl, max(1, int((bot - top - 76 * S) / lh)))
        pw = W * 0.86
        ph = lh * min(maxl, len(rows)) + 2 * 38 * S   # 面板高按行数，满 maxl 行以后上滚
        px, py = (W - pw) / 2, H * t.get('y', 0.44)
        if is_landscape(W, H):
            pw, px, py = right - l, l, top
        panel = Image.new('RGBA', (int(pw), int(ph)), (0, 0, 0, 0))
        ImageDraw.Draw(panel).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=int(26 * S), fill=hex_rgba(t.get('panel', '#4A5D7A'))[:3] + (205,))
        panel = np.array(panel)
        inner = (int(py + 26 * S), int(py + ph - 26 * S))
        f = ImageFont.truetype(str(font), int(fs))
        end = times[-1][-1] if times and times[-1] else 0.0
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            p = ease(tt / 0.3, 'out')
            over(c, panel, px, py + (1 - p) * 30 * S, p * fade_out(tt, dur, 0.2))
            shown = [r for r, ts in enumerate(times) if ts and ts[0] <= tt]
            last = shown[-1] if shown else -1
            # 满了整体上滚：第 r 行露出来那一刻起，0.2 秒内往上挪一行
            off = 0.0
            for r in range(maxl, len(rows)):
                if times[r] and tt >= times[r][0]:
                    off += lh * ease((tt - times[r][0]) / 0.2)
            layer = np.zeros((H, W, 4), np.uint8)
            cur_xy = None
            for r in shown:
                gs, wd = gl[r]
                base = py + 38 * S + fs * 0.92 + r * lh - off
                for (spr, gx, gy), ts in zip(gs, [x for x, ch in zip(times[r], rows[r][1]) if ch.strip()]):
                    if ts <= tt:
                        put(layer, spr, px + 46 * S + gx, base + gy)
                if r == last:
                    vis = sum(1 for x in times[r] if x <= tt)
                    cur_xy = (px + 46 * S + f.getlength(rows[r][1][:vis]) + 6 * S, base)
            layer[:inner[0]] = 0
            layer[inner[1]:] = 0
            over(c, layer, 0, 0, fade_out(tt, dur, 0.2))
            if cur_xy and (tt <= end or int(tt / 0.5) % 2 == 0) and inner[0] < cur_xy[1] < inner[1] + fs:   # 白色方块光标，打完 0.5 秒一闪
                x0, y1 = int(cur_xy[0]), int(cur_xy[1])
                c[max(0, y1 - int(fs * 0.78)):y1 + int(fs * 0.08), x0:x0 + int(fs * 0.45), :3] = 255
                c[max(0, y1 - int(fs * 0.78)):y1 + int(fs * 0.08), x0:x0 + int(fs * 0.45), 3] = int(255 * fade_out(tt, dur, 0.2))
            w.put(c)
        w.close()
        return
    import matte
    sk = t.get('person_scale', 0.75)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        q = ease(tt / 0.35, 'out')
        c = _opaque(_soft_bg(fr, W, H, 0.55))
        if q < 1:
            c[..., :3] = (fr * (1 - q) + c[..., :3] * q).astype(np.uint8)
        pp = scale(_person(fr, a), 1 - (1 - sk) * q)
        over(c, pp, (W * 0.78 if is_landscape(W, H) else W / 2) - pp.shape[1] / 2, H - pp.shape[0])
        layer = np.zeros_like(c) if is_landscape(W, H) else c
        off = 0
        if is_landscape(W, H):
            maxl = max(1, int((bot - top) / lh))
            for rr in range(maxl, len(rows)):
                if times[rr] and tt >= times[rr][0]:
                    off += lh * ease((tt - times[rr][0]) / 0.2)
        for r, (gs, wd) in enumerate(gl):
            base = (top if is_landscape(W, H) else H * t.get('y', 0.09)) + fs * 0.9 + r * lh - off
            ox = l + 46 * S if is_landscape(W, H) else (W - maxw) / 2
            for (spr, gx, gy), ts in zip(gs, [x for x, ch in zip(times[r], rows[r][1]) if ch.strip()]):
                if ts <= tt:
                    put(layer, spr, ox + gx, base + gy)
        if is_landscape(W, H):
            layer[:int(top)] = 0
            layer[int(bot):] = 0
            over(c, layer, 0, 0)
        c[..., 3] = int(255 * fade_out(tt, dur, 0.2))
        w.put(c)
    w.close()
