"""版式、背景与镜头（手法库第 12 批）：逐帧画的版式，titles 的 layout 写这些名字，cards.title_clip 转过来渲成整屏 .mov。

- splitwin     同画面拆窗看细节（detail_split_windows）：同一个口播拆成上下两个错开的窗口，上窗露脸、下窗露手
- window       素材窗口嵌入（example_window）：thin 细蓝框示例窗配黑底波浪线 / glow 发光框加分段标签 / shadow 投影卡加金属标题
- bands        并列词素材条堆叠（keyword_band_stack）：push 顶部压入下推 / drop 卡片下落堆叠 / gray 黑白转彩跟读
- matteband    抠像人站素材带（matte_band_stack）：three 三段式白描边 / tech 科技上下两段绿描边配胶囊标签
- papercollage 纸张分层拼贴（paper_layer_collage）：揉皱纸底、身后扇形素材、白描边人物、前景撕边色纸和贴纸，逐层入场
- figure       话题人物压暗剪影（topic_figure_dim_cutout）：素材照片里的人抠出来去色压暗，从下方升到下半屏
- moodword     情绪图配一个字（mood_image_word）：一张直白的意象图缓推，上面只压一个大字
- parallax     多层视差缓动（layer_parallax_drift）：ambient 各层各自缓动 / shift 换句时前景和人反向位移、人慢慢褪色
背景（backgrounds.py 的 kind）：grain 深灰纸纹暗角底、waves 黑底动态波浪线、floor 3D 透视空间底；主题视频压暗做底是 broll 的 "bg": "video"。
口播上移底部留黑（bottom_black_badge）是 timeline 顶层 badge_bar，apply 在口播全屏的时段叠底部黑条和骑线角标。
尺寸按 短边 1080 的像素值乘 S。
"""
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from bigtype import SERIF, _avatar, _fit, _gray, _head_square, _mask_out, _opaque, _person, _pop, _soft_bg
from infocard import BOLD, MED, OSWALD, card_of, emoji, glow, rrect, src_image
from keytext import HEAVY, blur, eback, fade_out, frames, put, scale, with_shadow, word
from kvlib import unit, is_landscape, safe_zones, face_crop, hex_rgba, is_image, probe
from motion import Writer, bg_frames, ease, over, read, resize, rotate_rgba, text_img, trim

LAYOUTS = ('splitwin', 'window', 'bands', 'matteband', 'papercollage', 'figure', 'moodword', 'parallax')


def clip(t, W, H, FPS, st, work, aroll, out):
    globals()[t['layout']](t, W, H, FPS, st, work, aroll, out)


def _alpha_fin(c, tt, dur, fin=0.12, fout=0.15):
    c[..., 3] = int(255 * min(1.0, tt / fin) * fade_out(tt, dur, fout))
    return c


def _crop_fill(fr, box, w, h):
    """从画面裁 box=(x, y, 宽, 高)（像素），按 w×h 铺满（保持比例居中裁）。"""
    x, y, bw, bh = box
    r = w / h
    if bw / bh > r:
        nw = bh * r
        x += (bw - nw) / 2
        bw = nw
    else:
        nh = bw / r
        y += (bh - nh) / 2
        bh = nh
    FH, FW = fr.shape[:2]
    k = min(1.0, FW / bw, FH / bh)   # 框比画面大就等比缩小，再整个挪回画面里，别裁到黑边
    x, y, bw, bh = x + bw * (1 - k) / 2, y + bh * (1 - k) / 2, bw * k, bh * k
    x, y = min(max(0.0, x), FW - bw), min(max(0.0, y), FH - bh)
    im = Image.fromarray(fr).crop((int(x), int(y), int(x + bw), int(y + bh))).resize((max(1, int(w)), max(1, int(h))), Image.BILINEAR)
    return np.array(im)


def _rwin(rgb, r, border=0, col='#FFFFFF'):
    a = np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)])
    m = Image.new('L', (a.shape[1], a.shape[0]), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, a.shape[1] - 1, a.shape[0] - 1], radius=int(r), fill=255)
    a[..., 3] = np.array(m)
    if border:
        b = rrect(a.shape[1] + 2 * border, a.shape[0] + 2 * border, r + border, col)
        over(b, a, border, border)
        return b
    return a


def _src_frames(src, t, dur, size, FPS):
    return read(src, t.get('src_in', 0), dur, size, FPS, t.get('crop'))


def _side_zone(t, W, H):
    """横屏文字放两侧，收进 5% 安全边距。"""
    z = safe_zones(W, H)['text'][0 if t.get('side') == 'left' else 1]
    return max(0.05, z[0]) * W, z[1] * H, min(0.95, z[2]) * W, z[3] * H


# ---------------------------------------------------------------- splitwin 同画面拆窗看细节
def splitwin(t, W, H, FPS, st, work, aroll, out):
    from effects import face_box
    S = unit(W, H)
    dur, n = frames(t, FPS)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    first = None
    tw, th = W * 0.86, H * 0.22
    bw, bh = W * 0.46, H * 0.15
    if is_landscape(W, H):
        tw, th = W * 0.53, H * 0.54
        bw, bh = W * 0.32, H * 0.36
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        if first is None:
            first = fr
            fb = face_box(fr)
            if fb:
                cx, top, fw, fh = fb
                face = (cx - fh * 1.25, top - fh * 0.05, fh * 2.5, fh * 1.05)
            else:
                face = (W * 0.1, H * 0.14, W * 0.8, H * 0.25)
            if is_landscape(W, H) and not fb:
                z = safe_zones(W, H)['face']
                face = (W * z[0], H * z[1], W * (z[2] - z[0]), H * 0.40)
            hb = t.get('hands')
            hands = (hb[0] * W, hb[1] * H, hb[2] * W, hb[3] * H) if hb else (W * 0.12, H * 0.66, W * 0.76, H * 0.32)
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        p = ease(tt / 0.3, 'out')
        lerp = lambda a, b: tuple(x + (y - x) * p for x, y in zip(a, b))
        sb = lerp((0, 0, W, H), face)
        dw, dh = tw + (W - tw) * (1 - p), th + (H - th) * (1 - p)
        dcx, dcy = W / 2, H * 0.2 + (H / 2 - H * 0.2) * (1 - p)
        if is_landscape(W, H):
            dcx, dcy = W * (0.315 + 0.185 * (1 - p)), H * (0.40 + 0.10 * (1 - p))
        top_win = _rwin(_crop_fill(fr, sb, dw, dh), W * 0.035 * p)
        put(c, top_win, dcx, dcy)
        q = ease((tt - 0.15) / 0.3, 'out')
        if q > 0:
            bot = _rwin(_crop_fill(fr, hands, bw, bh), W * 0.03, int(4 * S))
            put(c, scale(bot, 0.6 + 0.4 * q), W * 0.78 if is_landscape(W, H) else W / 2 + W * 0.12,
                H * 0.43 if is_landscape(W, H) else H * 0.45, q)
        w.put(_alpha_fin(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- window 素材窗口嵌入
WINDOW_VARIANTS = {
    'thin': '细蓝框示例窗：窗口宽约三分之二，2px 亮蓝描边，窗外黑底动态波浪线',
    'glow': '发光框加分段标签：黑底中间竖屏框，四周柔和白色外发光，上方粗白斜体「第1段」和红色小字',
    'shadow': '投影卡加金属标题：虚化素材做底，预览卡带深投影浮起，灰白金属质感标题一半压在卡上沿',
}


def _metal_word(text, size, S):
    a = word(text, size, '#FFFFFF', HEAVY)
    h = a.shape[0]
    g = np.linspace(0, 1, h)[:, None]
    col = np.clip(np.where(g < 0.5, 250 - 80 * g, 170 + 60 * (g - 0.5)), 0, 255)
    a[..., :3] = np.repeat(col[..., None], 3, axis=2).repeat(a.shape[1], 1).astype(np.uint8)
    return with_shadow(a, 6 * S, 0.7, dy=int(5 * S))


def window(t, W, H, FPS, st, work, aroll, out):
    import backgrounds
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'thin')
    p0 = probe(t['src'])
    sw, sh = (p0['w'] or 1080), (p0['h'] or 1920)
    if t.get('crop'):
        sw, sh = sw * t['crop'][2], sh * t['crop'][3]
    ww = W * ({'thin': 0.68, 'glow': 0.52, 'shadow': 0.66}[v] if sh >= sw else 0.86)
    wh = ww * sh / sw
    if wh > H * 0.62:
        wh = H * 0.62
        ww = wh * sw / sh
    if is_landscape(W, H) and (v == 'glow' or (v == 'shadow' and t.get('title'))):
        k = min(1.0, W * 0.56 / ww)
        ww, wh = ww * k, wh * k
    ww, wh = int(ww) // 2 * 2, int(wh) // 2 * 2
    frs = _src_frames(t['src'], t, dur, (ww, wh), FPS)
    bgs = None
    if v == 'thin':
        spec = backgrounds.make('waves', None, W, H, work)
        bgs = (backgrounds.frame_at(spec, i / FPS, H) for i in range(n))
    elif v == 'shadow':
        bgs = (_soft_bg(f, W, H, 0.5, 5) for f in _src_frames(t['src'], t, dur, (W, H), FPS))
    lab = sub = title = None
    if v == 'glow':
        lab = text_img(t.get('label', '第1段'), 70 * S, '#FFFFFF', fontfile=HEAVY, italic=0.18)
        sub = word(t['sub'], 32 * S, '#FF3B3B', BOLD) if t.get('sub') else None
    if v == 'shadow' and t.get('title'):
        title = _metal_word(t['title'], 96 * S, S)
    cy = H * t.get('y', 0.45)
    cx = W / 2
    if is_landscape(W, H):
        # 竖素材靠左，标签和标题单独放右栏，不挤在窗口上方。
        cx = W * 0.36 if (lab is not None or title is not None) else W / 2
        cy = min(H * 0.76 - wh / 2, max(H * 0.08 + wh / 2, cy))
        zx0, zy0, zx1, zy1 = _side_zone({'side': 'right'}, W, H)
        lab = _fit(lab, zx1 - zx0) if lab is not None else None
        sub = _fit(sub, zx1 - zx0) if sub is not None else None
        title = _fit(title, zx1 - zx0) if title is not None else None
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        if bgs is not None:
            c[..., :3] = next(bgs)[..., :3]
        win = next(frs)
        p = ease(tt / 0.3, 'out')
        if v == 'thin':
            g = _rwin(win, 4 * S, int(3 * S), '#1A2BFF')
        elif v == 'glow':
            g = glow(_rwin(win, 10 * S, int(3 * S)), 22 * S, '#FFFFFF', 0.9)
        else:
            g = with_shadow(_rwin(win, 16 * S), 22 * S, 0.65, dy=int(H * 0.02))
        put(c, scale(g, 0.9 + 0.1 * p), cx, cy, p)
        if lab is not None:
            put(c, lab, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2,
                H * 0.32 if is_landscape(W, H) else cy - wh / 2 - 110 * S, ease((tt - 0.15) / 0.25))
            if sub is not None:
                put(c, sub, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2,
                    H * 0.43 if is_landscape(W, H) else cy - wh / 2 - 46 * S, ease((tt - 0.25) / 0.25))
        if title is not None:
            put(c, title, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2,
                H * 0.36 if is_landscape(W, H) else cy - wh / 2, ease((tt - 0.2) / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- bands 并列词素材条堆叠
BANDS_VARIANTS = {
    'push': '顶部压入下推：人缩进右侧金边圆头像，新词的素材条从顶部压下把旧条往下推，每条左上虚线框黄字标签',
    'drop': '卡片下落堆叠：黑底网格，人裁成底部横条卡，关键词卡（素材底加超粗白字）从顶部逐张落下堆叠',
    'gray': '黑白转彩跟读：三条素材同时在场全是黑白，念到哪条哪条变回彩色，右侧竖排白字标签，人在中左圆角小窗',
}


def _dash_label(text, S):
    tx = word(text, 40 * S, '#F0D78C', HEAVY)
    w_, h_ = tx.shape[1] + int(40 * S), tx.shape[0] + int(24 * S)
    im = Image.new('RGBA', (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w_ - 1, h_ - 1], radius=int(10 * S), fill=(0, 0, 0, 128))
    x = 6 * S
    while x < w_ - 6 * S:
        d.line([(x, 2 * S), (min(x + 12 * S, w_ - 6 * S), 2 * S)], fill=(255, 255, 255, 255), width=int(3 * S))
        d.line([(x, h_ - 3 * S), (min(x + 12 * S, w_ - 6 * S), h_ - 3 * S)], fill=(255, 255, 255, 255), width=int(3 * S))
        x += 20 * S
    y = 6 * S
    while y < h_ - 6 * S:
        d.line([(2 * S, y), (2 * S, min(y + 12 * S, h_ - 6 * S))], fill=(255, 255, 255, 255), width=int(3 * S))
        d.line([(w_ - 3 * S, y), (w_ - 3 * S, min(y + 12 * S, h_ - 6 * S))], fill=(255, 255, 255, 255), width=int(3 * S))
        y += 20 * S
    a = np.array(im)
    put(a, tx, w_ / 2, h_ / 2)
    return a


def _bands_landscape(t, W, H, FPS, st, work, aroll, out):
    from infocard import at_list
    from structure import _grid_bg
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'push')
    items = (t.get('items') or [])[:3]
    times = at_list(t, len(items), 0.6, 0.15)
    bw, bh = (int(W * 0.62), int(H * 0.18)) if v == 'push' else (int(W * 0.19), int(H * 0.48))
    feeds = [read(s, 0 if is_image(s) else probe(s)['duration'] * 0.3, dur, (bw, bh), FPS)
             for s in (t.get('srcs') or [])[:len(items)]]
    labels = [_fit(_dash_label(x, S) if v == 'push' else with_shadow(word(x, 62 * S, '#FFFFFF', HEAVY), 6 * S, 0.7), bw * 0.88)
              for x in items]
    grid = _grid_bg(W, H, S, '#0E0E0E', '#2A2A2A', 0.08)
    sq = None
    w = Writer(out, W, H, FPS, alpha=True)
    for i, fr in enumerate(read(aroll, t['t0'], dur, (W, H), FPS)):
        tt = i / FPS
        c = _opaque(grid[..., :3].copy())
        if sq is None:
            cs, x, y = face_crop(W, H)
            sq = (x + cs / 2, y + cs / 2, cs)
        k = max((j for j, a in enumerate(times) if tt >= a), default=-1)
        for j, f in enumerate(feeds):
            rgb = next(f)
            p = ease((tt - times[j]) / 0.3, 'out')
            if v == 'gray':
                rgb = (_gray(rgb) * (1 - p) + rgb * p).astype(np.uint8)
            elif p <= 0:
                continue
            card = _rwin(rgb, 18 * S)
            if v == 'push':
                # 新条从上压入，旧条下移，但第三条也停在字幕上方。
                q = ease((tt - times[k]) / 0.3, 'out')
                x, y = W * 0.36, H * 0.21 + (k - j - (1 - q)) * H * 0.20
                over(card, labels[j], 20 * S, 16 * S)
            else:
                x, y = W * (0.155 + 0.215 * j), H * 0.39
                if v == 'drop':
                    y -= (1 - p) * H * 0.20
                put(card, labels[j], bw / 2, bh * 0.78)
            put(c, card, x, y, 1.0 if v == 'gray' else p)
        if v == 'push':
            pip = st['pip']
            put(c, _avatar(fr, sq, H * 0.26, 4 * S, '#D9B45A'), W * pip['x'], H * pip['y'], ease(tt / 0.3))
        else:
            person = _rwin(_crop_fill(fr, (sq[0] - sq[2] / 2, 0, sq[2], H), W * 0.23, H * 0.40), 20 * S, int(4 * S))
            put(c, person, W * 0.825, H * 0.47, ease(tt / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


def bands(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return _bands_landscape(t, W, H, FPS, st, work, aroll, out)
    from structure import _grid_bg
    from infocard import at_list
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'push')
    items = (t.get('items') or [])[:3]
    srcs = (t.get('srcs') or [])[:len(items)]
    times = at_list(t, len(items), 0.6, 0.15)
    bh = int(H * (0.26 if v != 'drop' else 0.16))
    srcf = [read(s, 0 if is_image(s) else probe(s)['duration'] * 0.3, dur, (W if v != 'drop' else int(W * 0.86), bh), FPS) for s in srcs]
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    labels = [_dash_label(x, S) for x in items] if v == 'push' else \
        [text_img(x, 46 * S, '#FFFFFF', fontfile=HEAVY, vertical=True, stroke=int(3 * S), stroke_color='#000000') for x in items] if v == 'gray' else \
        [with_shadow(word(x, 96 * S, '#FFFFFF', HEAVY), 8 * S, 0.7) for x in items]
    grid = _grid_bg(W, H, S, '#0E0E0E', '#2A2A2A', 0.08) if v == 'drop' else None
    sq = None
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        cur = [next(f) for f in srcf]
        if sq is None:
            sq = _head_square(fr, W, H)
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        if v == 'push':
            k = max((j for j, a in enumerate(times) if tt >= a), default=-1)
            pk = ease((tt - times[k]) / 0.3, 'out') if k >= 0 else 0.0
            step = bh + 6 * S
            for j in range(k, -1, -1):
                yy = H * 0.04 + (k - j - (1 - pk)) * step
                over(c, np.dstack([cur[j], np.full(cur[j].shape[:2], 255, np.uint8)]), 0, yy)
                over(c, labels[j], 30 * S, yy + 24 * S)
            av = _avatar(fr, sq, int(W * 0.4), int(4 * S), '#D9B45A')
            put(c, av, W * 0.74, H * 0.86, ease(tt / 0.3))
        elif v == 'drop':
            c[..., :3] = grid[..., :3]
            strip = _rwin(_crop_fill(fr, (sq[0] - sq[2] * 0.8, sq[1] - sq[2] * 0.42, sq[2] * 1.6, sq[2] * 0.66), W * 0.8, H * 0.2), 16 * S, int(4 * S))
            put(c, strip, W / 2, H * 0.83)
            for j, a in enumerate(times):
                p = ease((tt - a) / 0.3, 'out')
                if p <= 0:
                    continue
                card = _rwin(cur[j], 18 * S)
                put(card, labels[j], card.shape[1] / 2, card.shape[0] / 2)
                ty = H * 0.12 + j * (bh + 18 * S) + bh / 2
                put(c, card, W / 2, ty - (1 - p) * H * 0.2, p)
        else:
            k = max((j for j, a in enumerate(times) if tt >= a), default=-1)
            for j in range(len(items)):
                col = cur[j]
                g = ease((tt - times[j]) / 0.2) if j <= k else 0.0
                if j < k:
                    g = 1.0
                band = (_gray(col) * (1 - g) + col * g).astype(np.uint8)
                y = H * 0.06 + j * (bh + 8 * S)
                over(c, np.dstack([band, np.full(band.shape[:2], 255, np.uint8)]), 0, y)
                put(c, labels[j], W - 50 * S, y + bh / 2)
            pw = _rwin(_crop_fill(fr, (sq[0] - sq[2] * 0.55, sq[1] - sq[2] * 0.45, sq[2] * 1.1, sq[2] * 1.2), W * 0.38, H * 0.25), 20 * S, int(4 * S))
            put(c, with_shadow(pw, 14 * S, 0.5), W * 0.3, H * 0.5, ease(tt / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- matteband 抠像人站素材带
MATTEBAND_VARIANTS = {
    'three': '三段式：上中下 25/45/30 三段素材，中段站着白描边人物，头略溢出到上段，标题压在人像下层',
    'tech': '科技上下两段：上 65% 黑底故障线条动态底，人物绿色细描边、胸前绿色胶囊标签，下 35% 素材',
}


def _outline(a, px, color):
    k = max(3, int(px) * 2 + 1)
    if is_landscape(a.shape[1], a.shape[0]):
        # 横屏用同样的方形最大值滤波，逐帧描边不必慢慢排像素。
        import cv2
        m = cv2.dilate((np.clip(a, 0, 1) * 255).astype(np.uint8), np.ones((min(k, 31), min(k, 31)), np.uint8), borderType=cv2.BORDER_REPLICATE)
    else:
        m = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(min(k, 31)))
    o = np.zeros(a.shape + (4,), np.uint8)
    o[..., :3] = hex_rgba(color)[:3]
    o[..., 3] = np.array(m)
    return o


def _glitch_lines(W, h, tt, seed, S):
    rng = random.Random(seed + int(tt * 12))
    im = Image.new('RGB', (W, int(h)), (8, 10, 12))
    d = ImageDraw.Draw(im)
    for _ in range(26):
        y = rng.uniform(0, h)
        col = rng.choice([(40, 220, 140), (40, 180, 230), (90, 90, 100), (220, 60, 90)])
        x0 = rng.uniform(-0.2, 0.8) * W
        d.line([(x0, y), (x0 + rng.uniform(0.1, 0.6) * W, y)], fill=col, width=max(1, int(rng.choice([1, 2, 3]) * S)))
    return np.array(im)


def matteband(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return _matteband_landscape(t, W, H, FPS, st, work, aroll, out)
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'three')
    srcs = t.get('srcs') or []
    ratios = [0.25, 0.45, 0.30] if v == 'three' else [0.65, 0.35]
    hs = [int(H * r) for r in ratios]
    hs[-1] = H - sum(hs[:-1])
    if v == 'three':
        feeds = [read(srcs[k % len(srcs)], 0 if is_image(srcs[k % len(srcs)]) else probe(srcs[k % len(srcs)])['duration'] * 0.3, dur, (W, hs[k]), FPS)
                 for k in range(3)]
    else:
        feeds = [None, read(srcs[0], 0 if is_image(srcs[0]) else probe(srcs[0])['duration'] * 0.3, dur, (W, hs[1]), FPS)]
    title = with_shadow(_fit(word(t['text'], 110 * S, '#FFFFFF', HEAVY), W * 0.9), 8 * S, 0.65) if t.get('text') else None
    sub = word(t['sub'], 46 * S, '#F5D300', HEAVY) if t.get('sub') else None
    tag = None
    if v == 'tech' and t.get('tag'):
        tg = word(t['tag'], 38 * S, '#FFFFFF', HEAVY)
        tag = rrect(tg.shape[1] + 50 * S, tg.shape[0] + 22 * S, (tg.shape[0] + 22 * S) / 2, '#2E7D5B')
        put(tag, tg, tag.shape[1] / 2, tag.shape[0] / 2)
    ps = t.get('person_scale', 0.78 if v == 'three' else 0.72)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        y = 0
        for k, hh in enumerate(hs):
            if feeds[k] is None:
                c[y:y + hh, :, :3] = _glitch_lines(W, hh, tt, 3, S)
            else:
                c[y:y + hh, :, :3] = next(feeds[k])
            y += hh
        line_y = hs[0] if v == 'three' else hs[0]
        if title is not None:
            put(c, title, W / 2, H * (0.085 if v == 'three' else 0.12), ease(tt / 0.3))
        person = _person(fr, a)
        ol = _outline(a, (6 if v == 'three' else 4) * S, '#FFFFFF' if v == 'three' else '#3FAF7A')
        over(ol, person, 0, 0)
        g = scale(ol, ps)
        bottom = (hs[0] + hs[1]) if v == 'three' else H * 0.9
        over(c, g, W / 2 - g.shape[1] / 2, bottom - g.shape[0])
        if sub is not None:
            put(c, sub, W / 2, H * 0.7, ease((tt - 0.2) / 0.3))
        if tag is not None:
            put(c, tag, W / 2, bottom - g.shape[0] * 0.38, ease((tt - 0.2) / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


def _matteband_landscape(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'three')
    srcs = t.get('srcs') or []
    # 素材放两侧，人物保留中间四成；科技版把素材放右边。
    boxes = [(0.05, 0.16, 0.25, 0.28), (0.05, 0.48, 0.25, 0.28), (0.70, 0.34, 0.25, 0.42)] if v == 'three' else [(0.70, 0.34, 0.25, 0.42)]
    feeds = [read(srcs[k % len(srcs)], 0 if is_image(srcs[k % len(srcs)]) else probe(srcs[k % len(srcs)])['duration'] * 0.3,
                  dur, (int(W * bw), int(H * bh)), FPS) for k, (x, y, bw, bh) in enumerate(boxes)]
    title = _fit(with_shadow(word(t['text'], 82 * S, '#FFFFFF', HEAVY), 6 * S, 0.6), W * 0.25) if t.get('text') else None
    sub = _fit(word(t['sub'], 42 * S, '#F5D300', HEAVY), W * 0.25) if t.get('sub') else None
    tag = None
    if v == 'tech' and t.get('tag'):
        tg = _fit(word(t['tag'], 38 * S, '#FFFFFF', HEAVY), W * 0.22)
        tag = rrect(tg.shape[1] + 40 * S, tg.shape[0] + 22 * S, 30 * S, '#2E7D5B')
        put(tag, tg, tag.shape[1] / 2, tag.shape[0] / 2)
    ps = min(t.get('person_scale', 0.82), 0.88)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        bg = _glitch_lines(W, H, tt, 3, S) if v == 'tech' else np.full((H, W, 3), 18, np.uint8)
        c = _opaque(bg)
        for f, (x, y, bw, bh) in zip(feeds, boxes):
            over(c, _rwin(next(f), 14 * S), W * x, H * y)
        if title is not None:
            put(c, title, W * (0.175 if v == 'tech' else 0.825), H * 0.22, ease(tt / 0.3))
        ol = _outline(a, (6 if v == 'three' else 4) * S, '#FFFFFF' if v == 'three' else '#3FAF7A')
        over(ol, _person(fr, a), 0, 0)
        g = scale(ol, ps)
        over(c, g, (W - g.shape[1]) / 2, H * 0.81 - g.shape[0])
        if sub is not None:
            put(c, sub, W * 0.825, H * 0.78, ease((tt - 0.2) / 0.3))
        if tag is not None:
            put(c, tag, W * 0.175, H * 0.38, ease((tt - 0.2) / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- papercollage 纸张分层拼贴
def _crumpled(W, H, seed, base='#F2F2F0'):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    for cells, amp in ((5, 1.0), (11, 0.5), (23, 0.22)):   # 几层低频噪声叠起来当折痕起伏，再按横向坡度打光
        z = rng.random((cells, max(2, int(cells * W / H))))
        im = Image.fromarray((z * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(W / cells / 3))
        acc += np.array(im, np.float32) / 255 * amp
    gx = np.gradient(acc, axis=1) * unit(W, H)
    shade = np.clip(1 + gx * 40, 0.86, 1.05)
    rgb = np.array(hex_rgba(base)[:3], np.float32)[None, None] * shade[..., None]
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _torn_strip(W, h, color, seed, S):
    rng = random.Random(seed)
    im = Image.new('RGBA', (W, int(h)), (0, 0, 0, 0))
    pts = [(0, h * 0.3)]
    x = 0
    while x < W:
        x += rng.uniform(10, 26) * S
        pts.append((x, h * 0.3 + rng.uniform(-0.12, 0.12) * h))
    pts += [(W, h), (0, h)]
    d = ImageDraw.Draw(im)
    d.polygon([(px, py - 6 * S) for px, py in pts[:-2]] + [(W, h), (0, h)], fill=(250, 250, 248, 255))   # 撕边露出的白纸芯
    d.polygon(pts, fill=hex_rgba(color))
    return np.array(im)


def papercollage(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    paper = _opaque(_crumpled(W, H, 5))
    srcs = (t.get('srcs') or [])[:3]
    fan = [rotate_rgba(card_of(s, W * 0.36, S, r=10, border=int(8 * S), ratio=3 / 4), ang) for s, ang in zip(srcs, (14, 0, -14))]
    torn = _torn_strip(W, H * 0.16, t.get('torn', '#1E2A4A'), 3, S)
    stickers = [emoji(x, 140 * S) for x in (t.get('stickers') or ['Star', 'Sparkles'])[:2]]
    title = with_shadow(_fit(word(t['text'], 96 * S, '#FFFFFF', HEAVY, stroke=int(6 * S), stroke_color='#1E2A4A'), W * 0.86), 6 * S, 0.4) if t.get('text') else None
    if is_landscape(W, H):
        fan = [rotate_rgba(card_of(s, W * 0.19, S, r=10, border=int(8 * S), ratio=4 / 3), ang)
               for s, ang in zip(srcs, (8, -5, -8))]
        torn = _torn_strip(int(W * 0.27), H * 0.17, t.get('torn', '#1E2A4A'), 3, S)
        title = _fit(title, W * 0.24) if title is not None else None
        stickers = [scale(s, 0.70) for s in stickers]
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = paper.copy()
        for k, g in enumerate(fan):
            p = ease((tt - 0.1 - 0.12 * k) / 0.3, 'out')
            if p > 0:
                cx, cy = W * (0.22 + 0.28 * k), H * 0.26
                if is_landscape(W, H):
                    cx, cy = W * (0.175 if k < 2 else 0.825), H * (0.30 if k == 0 else 0.59 if k == 1 else 0.34)
                put(c, g, cx, cy + (1 - p) * 60 * S, p)
        ol = _outline(a, 8 * S, '#FFFFFF')
        over(ol, _person(fr, a), 0, 0)
        g = scale(ol, 0.78 if is_landscape(W, H) else 0.86)
        over(c, with_shadow(g, 10 * S, 0.3), W / 2 - g.shape[1] / 2 - 20 * S,
             H * 0.81 - g.shape[0] if is_landscape(W, H) else H - g.shape[0] - 20 * S)
        p = ease((tt - 0.45) / 0.3, 'out')
        if is_landscape(W, H):
            over(c, torn, W * 0.68, H * 0.78 - torn.shape[0], p)
        else:
            over(c, torn, 0, H - torn.shape[0] * p)
        for k, s in enumerate(stickers):
            q = (tt - 0.6 - 0.15 * k) / 0.2
            if q > 0:
                put(c, scale(s, _pop(min(1.0, q))), W * (0.14 if k == 0 else 0.86),
                    H * (0.75 if k == 0 else 0.54) if is_landscape(W, H) else H * (0.62 if k == 0 else 0.5), min(1.0, q * 2))
        if title is not None:
            put(c, title, W * 0.825 if is_landscape(W, H) else W / 2,
                H * 0.70 if is_landscape(W, H) else H * 0.9, ease((tt - 0.5) / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- figure 话题人物压暗剪影
def still_alpha(src, W, H):
    """一张照片里的人像透明度（0~1）：把照片铺成 2 秒视频交给 RVM 抠，取最后一帧。照片本身带透明通道就直接用。"""
    from person_matte import alphas
    im = Image.open(src)
    if im.mode in ('RGBA', 'LA') and np.array(im.convert('RGBA'))[..., 3].min() < 250:
        a = np.array(im.convert('RGBA').resize((W, H), Image.LANCZOS))[..., 3].astype(np.float32) / 255
        return np.array(im.convert('RGB').resize((W, H), Image.LANCZOS)), a
    cache = Path.home() / '.cache' / 'koubo' / 'stills'
    cache.mkdir(parents=True, exist_ok=True)
    mp4 = cache / f'{Path(src).stem}_{int(Path(src).stat().st_mtime)}_{W}x{H}.mp4'
    if not mp4.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', str(src), '-t', '2', '-vf',
                        f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30', '-pix_fmt', 'yuv420p', str(mp4)], check=True)
    rgb = next(read(str(mp4), 1.5, 1 / 30, (W, H), 30))
    a = list(alphas(str(mp4), 1.5, 1 / 30, W, H, 30))[-1]
    return rgb, a


def figure(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    pw, ph = int(W * 0.62) // 2 * 2, int(H * 0.62) // 2 * 2
    if t.get('src'):
        rgb, a = still_alpha(t['src'], pw, ph)
    else:   # 没给照片：拿口播这一帧的人示意
        import matte
        fr, a = next(matte.frames(aroll, t['t0'], 1 / FPS, pw, ph, FPS))
        rgb = fr
    g = _gray(rgb, 0.8)
    g = (g.astype(np.float32) * 0.85).astype(np.uint8)
    ol = _outline(a, 4 * S, '#000000')
    over(ol, _person(g, a), 0, 0)
    ys, xs = np.nonzero(ol[..., 3] > 10)
    if len(ys):
        ol = ol[ys.min():, max(0, xs.min() - 4):xs.max() + 4]
    fig = scale(ol, min(1.0, W * 0.6 / ol.shape[1], H * 0.48 / ol.shape[0]))
    title = with_shadow(_fit(word(t['text'], 90 * S, '#FFFFFF', HEAVY), W * 0.86), 8 * S, 0.6) if t.get('text') else None
    sub = word(t['sub'], 40 * S, '#D9D9D9', MED) if t.get('sub') else None
    if is_landscape(W, H):
        zx0, zy0, zx1, zy1 = _side_zone({'side': 'left'}, W, H)
        fig = scale(ol, min(1.0, W * 0.25 / ol.shape[1], H * 0.60 / ol.shape[0]))
        title = _fit(title, zx1 - zx0) if title is not None else None
        sub = _fit(sub, zx1 - zx0) if sub is not None else None
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = _opaque((fr.astype(np.float32) * (1 - 0.55 * ease(tt / 0.3))).astype(np.uint8))
        p = ease(tt / 0.6, 'out')
        fx, fy = W * t.get('x', 0.6), H
        if is_landscape(W, H):
            fx, fy = W * t.get('x', 0.825), H * 0.80
        over(c, fig, fx - fig.shape[1] / 2,
             fy - fig.shape[0] + (1 - p) * H * (0.02 if is_landscape(W, H) else 0.08), p)
        if title is not None:
            put(c, title, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2, H * 0.3, ease((tt - 0.2) / 0.3))
        if sub is not None:
            put(c, sub, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2,
                H * 0.3 + title.shape[0] / 2 + 50 * S if title is not None else H * 0.36, ease((tt - 0.35) / 0.3))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- moodword 情绪图配一个字
def moodword(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    frs = read(t['src'], t.get('src_in', 0), dur, (W, H), FPS, t.get('crop'))
    col = t.get('color', '#FFFFFF')
    g = word(t['text'], H * t.get('size', 0.26), col, t.get('font') and Path(t['font']) or SERIF)
    g = with_shadow(g, 16 * S, 0.6)
    if is_landscape(W, H):
        zx0, zy0, zx1, zy1 = _side_zone(t, W, H)
        g = _fit(g, zx1 - zx0, zy1 - zy0)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        z = 1 + 0.05 * tt / max(dur, 0.1)
        big = resize(fr, W * z, H * z)
        oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
        c = _opaque((big[oy:oy + H, ox:ox + W].astype(np.float32) * 0.78).astype(np.uint8))
        put(c, g, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2,
            H * t.get('y', 0.45), ease((tt - 0.05) / 0.2))
        c[..., 3] = 255
        w.put(c)
    w.close()


# ---------------------------------------------------------------- parallax 多层视差缓动
PARALLAX_VARIANTS = {
    'ambient': '多层各自缓动：底层轻微放大、人缓慢缩小、两列文字上下浮动、主体物反向飘，每层都很慢',
    'shift': '换句视差位移：换下一句时前景主体和人往不同方向移、速度差两倍，人慢慢褪色',
}


def parallax(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'ambient')
    if t.get('bg_src'):
        bg0 = next(read(t['bg_src'], 0, 1 / FPS, (W, H), FPS))
        bg0 = (bg0.astype(np.float32) * 0.6).astype(np.uint8)
    else:
        import backgrounds
        bg0 = backgrounds.frame_at(backgrounds.make('grid', 'rainbow', W, H, work), 0, H).copy()
    title = with_shadow(_fit(word(t['text'], 120 * S, '#FFFFFF', HEAVY), W * 0.86), 8 * S, 0.6) if t.get('text') else None
    cols = [text_img(x, 52 * S, '#E8E2CF', fontfile=SERIF, vertical=True) for x in (t.get('lines') or [])[:2]]
    obj = emoji(t.get('icon', 'Light bulb'), W * 0.24) if t.get('icon', 'Light bulb') else None
    if is_landscape(W, H):
        zx0, zy0, zx1, zy1 = _side_zone({'side': 'left'}, W, H)
        title = _fit(title, zx1 - zx0) if title is not None else None
        cols = [_fit(g, W * 0.08, H * 0.48) for g in cols]
        obj = _fit(obj, W * 0.15, H * 0.22) if obj is not None else None
    from infocard import at_list
    shifts = at_list(t, len(t.get('shift_at') or [1.6]), 1.5, 1.6) if v == 'shift' and not t.get('shift_at') else (t.get('shift_at') or [])
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        z = 1 + 0.04 * tt / 4
        big = resize(bg0, W * z, H * z)
        oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
        c = _opaque(big[oy:oy + H, ox:ox + W])
        sh = 0.0
        sat = 1.0
        if v == 'shift':
            for s_ in shifts:
                sh += ease((tt - s_) / 1.2, 'inout')
            sat = 1 - 0.6 * min(1.0, sh)
            if is_landscape(W, H):
                sh = min(1.0, sh)
        fl = lambda per, ph, amp: amp * np.sin(2 * np.pi * tt / per + ph)
        if title is not None:
            put(c, title, (zx0 + zx1) / 2 if is_landscape(W, H) else W / 2 - sh * W * 0.06,
                H * (0.25 if is_landscape(W, H) else 0.13) + fl(5, 0.3, H * 0.008), ease(tt / 0.4))
        for k, g in enumerate(cols):
            put(c, g, W * (0.76 + k * 0.13) if is_landscape(W, H) else W * (0.1 if k == 0 else 0.9),
                H * 0.42 + fl(4.5, 1.7 + k * 2.1, H * 0.01), ease((tt - 0.1) / 0.4))
        pk = 0.86 * (1 - 0.03 * tt / 4)
        if is_landscape(W, H):
            pk = 0.78 * (1 - 0.03 * tt / 4)
        rgb = _gray(fr, 1 - sat) if sat < 1 else fr
        pp = scale(_person(rgb, a), pk)
        over(c, pp, W / 2 - pp.shape[1] / 2 + sh * W * (0.04 if is_landscape(W, H) else 0.12),
             H * (0.81 if is_landscape(W, H) else 1) - pp.shape[0] + fl(6, 2.6, H * 0.006))
        if obj is not None:
            put(c, obj, (zx0 + zx1) / 2 - sh * W * 0.04 if is_landscape(W, H) else W * 0.8 - sh * W * 0.24,
                H * (0.57 if is_landscape(W, H) else 0.3) - fl(4, 0.9, H * 0.015), ease((tt - 0.2) / 0.4))
        w.put(_alpha_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- 顶层字段
def prepare(tl, st, base='.'):
    """口播上移底部留黑时字幕挪到人物胸前（不放进底部黑边）。"""
    if tl.get('badge_bar') and not tl.get('_badge_prep'):
        tl['_badge_prep'] = True
        for lv in ('base', 'key'):
            cv = tl.get('canvas', {'w': 1080, 'h': 1920})
            if not is_landscape(cv['w'], cv['h']):
                st['sub'][lv]['y'] = min(st['sub'][lv]['y'], tl['badge_bar'].get('sub_y', 0.70))


def _badge_png(text, W, H, S, work):
    tx = word(text, 30 * S, '#1A1A1A', HEAVY)
    bw, bh = max(int(W * 0.21), tx.shape[1] + int(40 * S)), int(H * 0.03)
    if is_landscape(W, H):
        tx = _fit(tx, W * 0.25 - 40 * S)
        bw = max(int(W * 0.21), tx.shape[1] + int(40 * S))
        bh = max(int(H * 0.06), tx.shape[0] + int(16 * S))
    b = rrect(bw, bh, bh * 0.3, '#F1EEDB', '#3A2A18', int(3 * S))
    put(b, tx, bw / 2, bh / 2)
    p = Path(work) / 'badge_bar.png'
    Image.fromarray(b).save(p)
    return p, bw, bh


def apply(fc, cur, tl, add_input, W, H, FPS, work, total):
    """口播上移底部留黑（badge_bar）：口播全屏的时段底部 18% 盖黑条，交界线正中骑一枚米白角标；B-roll 和整屏版式时段不加。"""
    bb = tl.get('badge_bar')
    if not bb:
        return cur
    from kvlib import fullscreen_windows
    S = unit(W, H)
    ys = int(H * bb.get('h', 0.82)) // 2 * 2
    wins = [tuple(x) for x in bb['ranges']] if bb.get('ranges') else [x for x in fullscreen_windows(tl) if x[1] - x[0] > 0.3]
    if not wins:
        return cur
    en = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in wins)
    fc.append(f"{cur}drawbox=x=0:y={ys}:w={W}:h={H - ys}:color=black:t=fill:enable='{en}'[bbk]")
    cur = '[bbk]'
    if bb.get('text'):
        p, bw, bh = _badge_png(bb['text'], W, H, S, work)
        idx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', str(p)])
        fc.append(f"[{idx}:v]format=rgba[bbg]")
        bx, by = (W - bw) // 2, ys - bh // 2
        if is_landscape(W, H):
            bx = int(W * 0.05)
            by = int(min(H * 0.81 - bh, max(H * 0.05, ys - bh - 12 * S)))
        fc.append(f"{cur}[bbg]overlay={bx}:{by}:enable='{en}':eof_action=pass[bbo]")
        cur = '[bbo]'
    return cur
