"""文字与排版（手法库一星第 13 批）：逐帧画的大字版式，titles 的 layout 写这些名字，cards.title_clip 转过来渲成整屏 .mov。

- grid2x2      田字格方块字（grid_2x2_title）：四字词拆成两行两列方块大字，旁边可竖排一个红色两字词对比
- persp3d      透视立体大字（perspective_text_3d）：白色厚重立体字在人两侧沿透视伸向深处，像立在地上的招牌
- stairs       阶梯斜排字（staircase_text）：短句每个字沿斜线从左上往右下排，一个比一个大，依次弹入
- overlapframe 字跨框边混搭（text_depth_overlap_frame）：口播缩成中间窄框，几组不同字体颜色的大字一半伸出框外
- orbit        字环绕人旋转（text_orbit_3d）：关键词拆成单字绕着头转，转到身后被人挡住
- wordwall     字墙与字云（word_wall_cloud）：wall 同一个字重复成墙 / cloud 多层远近不同的字漂浮，都在人身后
- pinyin       拼音谐音注释（pinyin_note）：above 上方拼音跟读放大 / pun 下方大写拼音配谐音字 / list 点阵底头像列表注释
- credits      双语制作团队字幕（credits_bilingual）：压暗空镜上左上「制作团队 PRODUCTION TEAM」，几列职位、英文、斜线、人名
- readygo      开讲前暗角收黑（ready_go_iris_out）：人两侧错位白字和空心 READY GO→，四周暗角向内收成黑底
- darkenword   手写字变暗混合（darken_blend_text）：人身后墙上一行手写字，变暗混合只留暗色笔迹，像印在墙上
- tape         斜向警戒带英文条（hazard_tape_strips）：画面一角两条交叉的黄黑、蓝白色带印着重复英文，沿条滑入
- searchhook   模糊搜索结果钩子（search_proof_hook）：虚化的搜索结果录屏中间留一块清晰，压粗黑大字、卡其竖排关键词、灰色巨大数字底纹
双行滚动字幕（sub_rolling_two_line）是字幕样子 sub_look 的 rolling / rolling_ink，在 render.build_ass 里排。
尺寸按 短边 1080 的像素值乘 S。
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bigtype import EN, SERIF, _avatar, _fit, _head_square, _hollow, _mask_out, _opaque, _person, _pop, _soft_bg, _wrap
from fonts import FONTS
from infocard import BOLD, MED, OSWALD, glow, latin, rrect, src_image
from keytext import SideWriter, side_box, side_anchor, fit_sprite, HAND, HEAVY, blur, eback, fade_out, frames, put, scale, with_shadow, word
from kvlib import unit, hex_rgba, is_image, probe, is_landscape, safe_zones, pip_params
from motion import Writer, ease, over, read, resize, rotate_rgba, text_img, trim

KUAILE = FONTS / 'ZCOOLKuaiLe-Regular.ttf'
WENKAI = FONTS / 'LXGWWenKai-Medium.ttf'
LAYOUTS = ('grid2x2', 'persp3d', 'stairs', 'overlapframe', 'orbit', 'wordwall', 'pinyin', 'credits', 'readygo', 'darkenword', 'tape',
           'searchhook')


def clip(t, W, H, FPS, st, work, aroll, out):
    globals()[t['layout']](t, W, H, FPS, st, work, aroll, out)


def _fin(c, tt, dur, fin=0.12, fout=0.15, keep=False):
    k = min(1.0, tt / fin) * fade_out(tt, dur, fout)
    if keep:
        c[..., 3] = (c[..., 3] * k).astype(np.uint8)
    else:
        c[..., 3] = int(255 * k)
    return c


def _hard_shadow(a, dx, dy, alpha=0.85):
    s = np.zeros((a.shape[0] + abs(dy), a.shape[1] + abs(dx), 4), np.uint8)
    s[max(dy, 0):max(dy, 0) + a.shape[0], max(dx, 0):max(dx, 0) + a.shape[1], 3] = (a[..., 3] * alpha).astype(np.uint8)
    over(s, a, max(-dx, 0), max(-dy, 0))
    return s


def _clear_landscape(c, W, H):
    """装饰字也不经过脸，四周留边，底下让给字幕。"""
    l, top, r, bot = safe_zones(W, H)['face']
    c[int(top * H):int(bot * H), int(l * W):int(r * W), 3] = 0
    c[:int(H * 0.08), :, 3] = 0
    c[int(H * 0.75):, :, 3] = 0
    c[:, :int(W * 0.05), 3] = 0
    c[:, int(W * 0.95):, 3] = 0


# ---------------------------------------------------------------- grid2x2 田字格方块字
def grid2x2(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    text = t['text'].replace(' ', '')[:4]
    ch = H * t.get('size', 0.11)
    glyphs = [with_shadow(word(c, ch, '#FFFFFF', SERIF), 12 * S, 0.8, dy=int(6 * S)) for c in text]
    cell = max(g.shape[1] for g in glyphs) * 0.92
    pair = text_img(t['pair'], ch * 0.82, t.get('pair_color', '#D7261E'), fontfile=SERIF, vertical=True) if t.get('pair') else None
    cx, cy = W * (0.42 if pair is not None else 0.5), H * t.get('y', 0.66)
    if is_landscape(W, H):
        l, top, r, bot = side_box(t, W, H)
        f = min(1, (r - l) / (cell * (3.6 if pair is not None else 2.4)))
        glyphs = [scale(g, f) for g in glyphs]
        pair = scale(pair, f) if pair is not None else None
        cell *= f
        cx, cy = (l + r) / 2 - (cell * 0.5 if pair is not None else 0), (top + bot) / 2
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for k, g in enumerate(glyphs):
            p = ease((tt - 0.08 * k) / 0.22, 'out')
            if p <= 0:
                continue
            x = cx + (k % 2 - 0.5) * cell
            y = cy + (k // 2 - 0.5) * cell
            put(c, scale(g, 1.25 - 0.25 * p), x, y, p)
        if pair is not None:
            p = ease((tt - 0.4) / 0.25, 'out')
            put(c, with_shadow(pair, 10 * S, 0.7), cx + cell * 1.45, cy + (1 - p) * 30 * S, p)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- persp3d 透视立体大字
def _persp(a, lean):
    """lean>0：右边缩小（字往右侧深处退），<0 反过来。"""
    import cv2
    h, w = a.shape[:2]
    k = abs(lean)
    quad = [[0, 0], [0, h], [w, h * (1 - k / 2)], [w, h * k / 2]] if lean > 0 else [[0, h * k / 2], [0, h * (1 - k / 2)], [w, h], [w, 0]]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [0, h], [w, h], [w, 0]]), np.float32(quad))
    return cv2.warpPerspective(a, M, (w, h), flags=cv2.INTER_CUBIC)


def persp3d(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    text = t['text'].replace(' ', '')
    cut = t.get('cut', (len(text) + 1) // 2)
    lt, rt = t.get('left') or text[:cut], t.get('right') or text[cut:]
    size = H * t.get('size', 0.13)
    L = _persp(text_img(lt, size, '#FFFFFF', fontfile=HEAVY, vertical=True), 0.45)
    R = _persp(text_img(rt, size, '#FFFFFF', fontfile=HEAVY, vertical=True), -0.45) if rt else None

    def thick(a, sign):
        side = a.copy()
        side[..., :3] = (189, 189, 189)
        o = np.zeros((a.shape[0] + int(16 * S), a.shape[1] + int(16 * S), 4), np.uint8)
        for k in range(8, 0, -1):
            over(o, side, 8 * S + sign * 2 * S * k, 8 * S + 1.2 * S * k)
        over(o, a, 8 * S, 8 * S)
        return with_shadow(o, 10 * S, 0.5, dy=int(8 * S))
    L = thick(L, 1)
    R = thick(R, -1) if R is not None else None
    y = H * t.get('y', 0.55)
    if is_landscape(W, H):
        L = fit_sprite(L, W * 0.22, H * 0.52)
        R = fit_sprite(R, W * 0.22, H * 0.52) if R is not None else None
        y = H * 0.45
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.35, 'out')
        put(c, L, W * (0.17 if is_landscape(W, H) else 0.14) - (1 - p) * W * 0.2, y, p)
        if R is not None:
            q = ease((tt - 0.12) / 0.35, 'out')
            put(c, R, W * (0.83 if is_landscape(W, H) else 0.86) + (1 - q) * W * 0.2, y, q)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- stairs 阶梯斜排字
def stairs(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    text = t['text'].replace(' ', '')[:5]
    k = len(text)
    base = H * 0.09
    grow = t.get('grow', 0.25)
    glyphs = [_hard_shadow(word(c, base * (1 + grow * j), t.get('color', '#FFFFFF'), HEAVY, stroke=int(5 * S), stroke_color='#111111'),
                           int(6 * S), int(6 * S)) for j, c in enumerate(text)]
    dx, dy = W * 0.13, H * 0.065
    x0 = W / 2 - dx * (k - 1) / 2
    y0 = H * t.get('y', 0.5) - dy * (k - 1) / 2
    if is_landscape(W, H):
        l, top, r, bot = side_box(t, W, H)
        dx, dy = (r - l) * 0.7 / max(1, k - 1), H * 0.07
        glyphs = [fit_sprite(g, (r - l) * 0.28, H * 0.16) for g in glyphs]
        x0 = (l + r) / 2 - dx * (k - 1) / 2
        y0 = (top + bot) / 2 - dy * (k - 1) / 2
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for j, g in enumerate(glyphs):
            p = (tt - 0.1 * j) / 0.16
            if p > 0:
                put(c, scale(g, _pop(min(1.0, p))), x0 + dx * j, y0 + dy * j, min(1.0, p * 2))
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- overlapframe 字跨框边混搭
OVERLAP_STYLES = [('#F5C518', HEAVY, False), ('#FFFFFF', HEAVY, True), ('#E5338F', KUAILE, False), ('#FFFFFF', OSWALD, False), ('#F5C518', SERIF, True)]


def overlapframe(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = (t.get('items') or [t.get('text', '')])[:5]
    fw, fh = int(W * 0.7) // 2 * 2, int(H * 0.7) // 2 * 2
    if is_landscape(W, H):
        fw, fh = int(W * 0.44) // 2 * 2, int(H * 0.62) // 2 * 2
    fx, fy = (W - fw) / 2, (H - fh) / 2
    spots = [(fx, fy + fh * 0.18, -6), (fx + fw, fy + fh * 0.42, 5), (fx, fy + fh * 0.66, 4), (fx + fw, fy + fh * 0.86, -5), (W / 2, fy, 0)]
    if is_landscape(W, H):
        spots = [(W * 0.17, H * 0.25, -6), (W * 0.83, H * 0.3, 5),
                 (W * 0.17, H * 0.6, 4), (W * 0.83, H * 0.65, -5), (W * 0.17, H * 0.43, 0)]
    groups = []
    for k, x in enumerate(items):
        col, f, hol = OVERLAP_STYLES[k % len(OVERLAP_STYLES)]
        f = latin(x, f) if f == OSWALD else f
        g = _hollow(x, 200 * S, col, f, int(5 * S), light=is_landscape(W, H)) if hol else word(x, 200 * S, col, f, stroke=int(4 * S), stroke_color='#111111')
        groups.append(with_shadow(rotate_rgba(_fit(g, W * 0.62), spots[k][2]), 8 * S, 0.6))
    if is_landscape(W, H):
        groups = [fit_sprite(g, W * 0.22, H * 0.19) for g in groups]
    frs = read(aroll, t['t0'], dur, (fw, fh), FPS)
    times = t.get('item_at') or [0.25 + 0.3 * k for k in range(len(items))]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        p = ease(tt / 0.3, 'out')
        fr = next(frs)
        k = 1 - 0.3 * p
        big = resize(fr, W * (1 - (1 - fw / W) * p), H * (1 - (1 - fh / H) * p))
        over(c, np.dstack([big, np.full(big.shape[:2], 255, np.uint8)]), (W - big.shape[1]) / 2, (H - big.shape[0]) / 2)
        for j, g in enumerate(groups):
            a = times[j] if j < len(times) and times[j] is not None else 0.25 + 0.3 * j
            q = (tt - a) / 0.18
            if q > 0:
                x, y, _ = spots[j]
                put(c, scale(g, _pop(min(1.0, q))), x, y, min(1.0, q * 2))
        w.put(_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- orbit 字环绕人旋转
def orbit(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    chars = list(t['text'].replace(' ', ''))[:6]
    glyphs = [with_shadow(word(c, 150 * S, t.get('color', '#FFE24A'), HEAVY, stroke=int(6 * S), stroke_color='#111111'), 6 * S, 0.6) for c in chars]
    rx, ry = W * 0.4, H * 0.06
    per = t.get('period', 2.4)
    sq = None
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        if sq is None:
            sq = _head_square(fr, W, H)
        cx, cy = sq[0], sq[1] + sq[2] * 0.15
        back = np.zeros((H, W, 4), np.uint8)
        front = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3)
        for j, g in enumerate(chars and glyphs):
            th = 2 * math.pi * (tt / per + j / len(glyphs))
            x, y = cx + rx * math.cos(th), cy + ry * math.sin(th)
            depth = math.sin(th)   # >0 在前（下半圈），<0 在身后
            s = 0.75 + 0.25 * (depth + 1) / 2
            gg = scale(g, s)
            put(front if depth > 0 else back, gg, x, y, p * (0.55 + 0.45 * (depth + 1) / 2))
        if is_landscape(W, H):
            for layer in (back, front):
                _clear_landscape(layer, W, H)
        _mask_out(back, a)
        over(back, front, 0, 0)
        w.put(_fin(back, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- wordwall 字墙与字云
WORDWALL_VARIANTS = {
    'wall': '重复字墙：约 4 行 × 8 列同一个字，灰色半透明，随机几个是红色，人站在前面',
    'cloud': '多层景深字云：几层文字大小、透明度、清晰度不同，远的模糊发灰、近的清楚，各自缓慢横漂，最前面一个红色关键词',
}


def wordwall(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'wall')
    rng = random.Random(int(t['t0'] * 100) + 3)
    layers = []
    if v == 'wall':
        ch = t.get('text', '吵')[:1]
        size = H * 0.13
        gray = word(ch, size, '#8A8A8A', HEAVY)
        red = word(ch, size, '#C4161C', HEAVY)
        wall = np.zeros((H, W, 4), np.uint8)
        if is_landscape(W, H):
            for side in ('left', 'right'):
                l, top, r, bot = side_box(t, W, H, side)
                gray_ = fit_sprite(gray, (r - l) * 0.36, (bot - top) * 0.24)
                red_ = fit_sprite(red, (r - l) * 0.36, (bot - top) * 0.24)
                for row in range(3):
                    for col in range(2):
                        g = red_ if rng.random() < 0.15 else gray_
                        put(wall, g, l + (r - l) * (col + 0.5) / 2, top + (bot - top) * (row + 0.5) / 3, 0.6 if g is gray_ else 0.9)
        else:
            cols, rows = 5, 8
            for r in range(rows):
                for c_ in range(cols):
                    g = red if rng.random() < 0.15 else gray
                    put(wall, g, W * (c_ + 0.5 + 0.25 * (r % 2)) / cols, H * (r + 0.5) / rows, 0.6 if g is gray else 0.9)
        layers.append((wall, 0.0))
    else:
        words = t.get('items') or ['信息', '太多', '噪音', '焦虑', '算法', '推送', '热点', '刷屏']
        for k in range(7):
            far = k < 4
            size = H * (0.05 if far else 0.1 if k < 6 else 0.16)
            g = word(rng.choice(words), size, '#BBBBBB' if far else '#EEEEEE', HEAVY)
            if far:
                g = blur(np.pad(g, ((8, 8), (8, 8), (0, 0))), 3 * S)
            if is_landscape(W, H):
                g = fit_sprite(g, W * 0.16, H * 0.18)
            L = np.zeros((H, W, 4), np.uint8)
            for j in range(5 if far else 3):
                if is_landscape(W, H):
                    l, top, r, bot = side_box(t, W, H, 'left' if j % 2 == 0 else 'right')
                    margin = min(24 * S, (r - l - g.shape[1]) / 2)
                    x = rng.uniform(l + g.shape[1] / 2 + margin, r - g.shape[1] / 2 - margin)
                    y = rng.uniform(top + g.shape[0] / 2, bot - g.shape[0] / 2)
                else:
                    x, y = rng.uniform(0, W), rng.uniform(H * 0.05, H * 0.75)
                put(L, g, x, y, 0.4 if far else 0.75)
            speed = min(6 * S, 24 * S / max(dur, 0.1)) if is_landscape(W, H) else W * (0.01 if far else 0.025)
            layers.append((L, rng.choice([-1, 1]) * speed))
        key = with_shadow(word(t.get('text', '焦虑'), H * 0.11, '#C4161C', HEAVY), 8 * S, 0.6)
    if is_landscape(W, H) and v == 'cloud':
        key = fit_sprite(key, W * 0.22, H * 0.22)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for L, sp in layers:
            dx = sp * tt
            over(c, L, dx, 0)
            if dx:
                over(c, L, dx - W if dx > 0 else dx + W, 0)
        if is_landscape(W, H):
            _clear_landscape(c, W, H)
        _mask_out(c, a)
        if v == 'cloud':
            put(c, key, W * 0.17 if is_landscape(W, H) else W * 0.5, H * 0.5 if is_landscape(W, H) else H * 0.66, ease((tt - 0.3) / 0.3))
        w.put(_fin(c, tt, dur, 0.25, keep=True))
    w.close()


# ---------------------------------------------------------------- pinyin 拼音谐音注释
PINYIN_VARIANTS = {
    'above': '上方拼音跟读：关键词上方一行小拼音，读到哪个字那个音节放大三倍再缩回，带红色发光',
    'pun': '下方谐音梗：大字下方全大写拼音加括号谐音字，比如 SHANG(上) PAN(盘)',
    'list': '头像列表注释：黑色点阵底上几行列表，左边小头像，右边白色大字，字上方红色谐音英文',
}


def _py(text):
    from pypinyin import lazy_pinyin
    return lazy_pinyin(text)


def pinyin(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return landscape_pinyin(t, W, H, FPS, aroll, out)
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'above')
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'list':
        from structure import _grid_bg
        rows = t.get('items') or []
        bg = np.zeros((H, W, 4), np.uint8)
        bg[..., 3] = 255
        im = Image.fromarray(bg)
        d = ImageDraw.Draw(im)
        g = int(18 * S)
        for yy in range(0, H, g):
            for xx in range(0, W, g):
                d.ellipse([xx, yy, xx + 3 * S, yy + 3 * S], fill=(46, 46, 46, 255))
        bg = np.array(im)
        fr0 = next(read(aroll, t['t0'] + 0.2, 1 / FPS, (W, H), FPS))
        av = _avatar(fr0, _head_square(fr0, W, H), int(H * 0.11), int(3 * S))
        rh = H * 0.15
        y0 = H * 0.5 - rh * (len(rows) - 1) / 2
        built = [(word(r['text'], 130 * S, '#FFFFFF', HEAVY), word(r.get('pun', ''), 54 * S, '#E0263A', BOLD)) for r in rows]
        times = t.get('item_at') or [0.2 + 0.5 * k for k in range(len(rows))]
        for i in range(n):
            tt = i / FPS
            c = bg.copy()
            for k, (wd, pn) in enumerate(built):
                a = times[k] if times[k] is not None else 0.2 + 0.5 * k
                p = ease((tt - a) / 0.25, 'out')
                if p <= 0:
                    continue
                y = y0 + k * rh
                put(c, av, W * 0.16, y, p)
                over(c, wd, W * 0.3 - (1 - p) * 40 * S, y - wd.shape[0] / 2 + 20 * S, p)
                over(c, pn, W * 0.3, y - wd.shape[0] / 2 - pn.shape[0] + 14 * S, p)
            w.put(_fin(c, tt, dur))
        w.close()
        return
    text = t['text']
    sylls = t.get('pinyin') or _py(text)
    f = ImageFont.truetype(str(HEAVY), int(130 * S))
    adv = [f.getlength(c) for c in text]
    tw = sum(adv)
    main = with_shadow(word(text, 130 * S, '#FFFFFF', HEAVY, stroke=int(5 * S), stroke_color='#111111'), 8 * S, 0.6)
    cy = H * t.get('y', 0.62)
    xs, x = [], W / 2 - tw / 2
    for a_ in adv:
        xs.append(x + a_ / 2)
        x += a_
    if v == 'pun':
        line = '  '.join(f"{s.upper()}({c})" for s, c in zip(sylls, text))
        pun = _fit(word(line, 58 * S, '#F5B800', BOLD, stroke=int(3 * S), stroke_color='#111111'), W * 0.92)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            put(c, main, W / 2, cy, ease(tt / 0.2))
            put(c, pun, W / 2, cy + main.shape[0] / 2 + 40 * S, ease((tt - 0.3) / 0.25))
            w.put(_fin(c, tt, dur, 0.01, keep=True))
        w.close()
        return
    marks = [glow(word(s, 46 * S, '#FFFFFF', BOLD), 6 * S, '#D92B2B', 0.8) for s in sylls]
    times = t.get('char_at') or [0.25 + 0.22 * k for k in range(len(text))]
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        put(c, main, W / 2, cy, ease(tt / 0.2))
        for k, (g, x) in enumerate(zip(marks, xs)):
            a = times[k] if k < len(times) and times[k] is not None else 0.25 + 0.22 * k
            q = (tt - a) / 0.3
            sc = 3.0 - 2.0 * ease(q, 'out') if 0 <= q <= 1 else 1.0
            put(c, scale(g, sc * 0.7) if sc > 1.01 else g, x, cy - main.shape[0] / 2 - 26 * S, ease(tt / 0.2))
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


def landscape_pinyin(t, W, H, FPS, aroll, out):
    """拼音与字同在侧栏；整页注释列表改成横向多列。"""
    S = unit(W, H)
    v = t.get('variant', 'above')
    dur, n = frames(t, FPS)
    if v == 'list':
        rows = t.get('items') or []
        cols = min(3, max(1, len(rows)))
        nr = (len(rows) + cols - 1) // cols
        cell = W * 0.88 / cols
        fr0 = next(read(aroll, t['t0'] + 0.2, 1 / FPS, (W, H), FPS))
        av = _avatar(fr0, _head_square(fr0, W, H), int(H * 0.11), int(3 * S))
        built = [(fit_sprite(word(r['text'], 100 * S, '#FFFFFF', HEAVY), cell * 0.7, H * 0.14),
                  fit_sprite(word(r.get('pun', ''), 44 * S, '#E0263A', BOLD), cell * 0.75, H * 0.08)) for r in rows]
        at = t.get('item_at') or []
        w = Writer(out, W, H, FPS, alpha=True)
        for i in range(n):
            tt = i / FPS
            c = np.full((H, W, 4), (12, 12, 12, 255), np.uint8)
            for j, (wd, pn) in enumerate(built):
                a = at[j] if j < len(at) and at[j] is not None else 0.2 + 0.5 * j
                p = ease((tt - a) / 0.25, 'out')
                cx = W * 0.06 + cell * (j % cols + 0.5)
                cy = H * (0.35 + (j // cols) * 0.32) if nr > 1 else H * 0.45
                put(c, av, cx, cy - H * 0.15, p)
                put(c, pn, cx, cy - H * 0.035, p)
                put(c, wd, cx, cy + H * 0.08, p)
            w.put(_fin(c, tt, dur))
        w.close()
        return
    l, top, r, bot = side_box(t, W, H)
    cx, cy = side_anchor(t, W, H)
    text = t['text']
    sylls = t.get('pinyin') or _py(text)
    fs = min(130 * S, (r - l) * 0.85 / max(1, len(text)))
    main = with_shadow(word(text, fs, '#FFFFFF', HEAVY, stroke=int(4 * S)), 6 * S, 0.6)
    cell = fs
    cols = min(2, max(1, len(text)))
    rows = (len(text) + cols - 1) // cols
    cell = (r - l) * 0.9 / cols
    marks = [fit_sprite(glow(word(s, 40 * S, '#FFFFFF', BOLD), 5 * S, '#D92B2B', 0.8), cell / 1.65, H * 0.06) for s in sylls]
    glyphs = [with_shadow(word(ch, min(110 * S, cell * 0.8), '#FFFFFF', HEAVY, stroke=int(4 * S)), 5 * S, 0.6) for ch in text]
    units = [f'{s.upper()}({ch})' for s, ch in zip(sylls, text)]
    prs = [fit_sprite(word('  '.join(units[j:j + 2]), 42 * S, '#F5B800', BOLD), (r - l) * 0.9, H * 0.08)
           for j in range(0, len(units), 2)]
    at = t.get('char_at') or []
    w = SideWriter(out, W, H, FPS, t)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        if v == 'pun':
            put(c, main, cx, cy - H * 0.06, ease(tt / 0.2))
            for j, pun in enumerate(prs):
                put(c, pun, cx, cy + main.shape[0] / 2 + H * (0.04 + j * 0.065), ease((tt - 0.3) / 0.25))
        else:
            for j, g in enumerate(marks):
                a = at[j] if j < len(at) and at[j] is not None else 0.25 + 0.22 * j
                q = (tt - a) / 0.3
                sc = 1.65 - 0.65 * ease(q, 'out') if 0 <= q <= 1 else 1
                gx = cx + (j % cols - (cols - 1) / 2) * cell
                gy = cy + (j // cols - (rows - 1) / 2) * H * 0.23
                put(c, glyphs[j], gx, gy + H * 0.025, ease(tt / 0.2))
                put(c, scale(g, sc), gx, gy - H * 0.07, ease(tt / 0.2))
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- credits 双语制作团队字幕
def credits(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    roles = t.get('items') or [{'role': '出品', 'en': 'Producer', 'name': '某某'}]
    head = word('制作团队  PRODUCTION TEAM', 54 * S, '#F2F2F2', SERIF)
    cols = []
    for r in roles[:4]:
        a = word(r['role'], 62 * S, '#FFFFFF', SERIF)
        e = word(r.get('en', '').upper(), 30 * S, '#BBBBBB', SERIF)
        nm = word(r.get('name', ''), 50 * S, '#FFFFFF', SERIF)
        if is_landscape(W, H):
            cell = W * 0.88 / max(1, min(4, len(roles)))
            a, e, nm = (fit_sprite(g, cell * 0.86, H * 0.08) for g in (a, e, nm))
        cols.append((a, e, nm))
    src = t.get('src')
    frs = read(src, t.get('src_in', 0), dur, (W, H), FPS) if src else read(aroll, t['t0'], dur, (W, H), FPS)
    k = len(cols)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = _opaque((fr.astype(np.float32) * 0.62).astype(np.uint8) if src else _soft_bg(fr, W, H, 0.5, 3))
        p = ease(tt / 1.0)
        over(c, head, W * 0.07, H * (0.2 if is_landscape(W, H) else 0.62), p)
        im = Image.fromarray(c)
        d = ImageDraw.Draw(im)
        for j in range(k):
            x = W * 0.07 + W * 0.88 * j / k
            d.line([(x + 6 * S, H * (0.64 if is_landscape(W, H) else 0.79)), (x + 36 * S, H * (0.5 if is_landscape(W, H) else 0.72))], fill=(255, 255, 255, int(200 * p)), width=int(2 * S))
        c = np.array(im)
        for j, (a, e, nm) in enumerate(cols):
            x = W * 0.07 + W * 0.88 * j / k
            over(c, a, x, H * (0.38 if is_landscape(W, H) else 0.68), p)
            over(c, e, x, H * (0.38 if is_landscape(W, H) else 0.68) + a.shape[0] + 8 * S, p)
            over(c, nm, x + 40 * S, H * (0.58 if is_landscape(W, H) else 0.75), p)
        w.put(_fin(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- readygo 开讲前暗角收黑
def readygo(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    left = t.get('text', '开始')[:2]
    lg = [with_shadow(word(c, H * 0.12, '#FFFFFF', HEAVY), 8 * S, 0.6) for c in left]
    en = with_shadow(_hollow(t.get('en', 'READY GO→'), H * 0.08, '#FFFFFF', latin(t.get('en', 'READY GO→'), OSWALD), int(6 * S), light=is_landscape(W, H)), 6 * S, 0.8)
    en = rotate_rgba(en, 90)
    iris_at = t.get('iris_at', max(0.3, dur - 0.8))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W * 0.45), (yy - H * 0.47) / (H * 0.45))
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.25, 'out')
        put(c, lg[0], W * 0.13, H * 0.45 - (1 - p) * 40 * S, p)
        if len(lg) > 1:
            put(c, lg[1], W * 0.2, H * 0.45 + lg[0].shape[0] * 0.9 + (1 - p) * 40 * S, p)
        put(c, en, W * 0.86, H * 0.5, ease((tt - 0.15) / 0.25))
        q = ease((tt - iris_at) / 0.5)
        if q > 0:
            edge = 2.2 - 1.2 * q   # 暗角的边从画外收到中心 45% 的椭圆
            m = np.clip((r - edge + 0.25) / 0.25, 0, 1)
            dark = np.zeros((H, W, 4), np.uint8)
            dark[..., 3] = (m * 255 * min(1.0, q * 1.5)).astype(np.uint8)
            over(dark, c, 0, 0)
            c = dark
        w.put(_fin(c, tt, dur, 0.01, 0.05, keep=True))
    w.close()


# ---------------------------------------------------------------- darkenword 手写字变暗混合
def darkenword(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    tx = _fit(word(t['text'], H * t.get('size', 0.09), '#FFFFFF', HAND), W * 0.94)
    if is_landscape(W, H):
        l, top, r, bot = side_box(t, W, H)
        gs = [word(row, 78 * S, t.get('color', '#32302D'), HAND) for row in _wrap(t['text'], HAND, 78 * S, (r - l) * 0.88)]
        gap = int(14 * S)
        tx = np.zeros((sum(g.shape[0] for g in gs) + gap * max(0, len(gs) - 1), max(g.shape[1] for g in gs), 4), np.uint8)
        yy = 0
        for g in gs:
            over(tx, g, (tx.shape[1] - g.shape[1]) / 2, yy)
            yy += g.shape[0] + gap
    sh = tx.copy()
    sh[..., :3] = 20
    sh = blur(np.pad(sh, ((20, 20), (20, 20), (0, 0))), 4 * S)
    layer = np.full((H, W, 3), 255, np.float32)
    lay = np.zeros((H, W, 4), np.uint8)
    cx, cy = side_anchor(t, W, H) if is_landscape(W, H) else (W / 2, H * t.get('y', 0.12))
    put(lay, sh, cx + 6 * S, cy + 6 * S)
    put(lay, tx, cx, cy)
    a_ = lay[..., 3:4].astype(np.float32) / 255
    layer = layer * (1 - a_) + lay[..., :3] * a_
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        p = ease(tt / 0.6)
        mixed = np.minimum(fr.astype(np.float32), layer)
        bgc = fr * (1 - p) + mixed * p
        aa = a[..., None]
        outc = bgc * (1 - aa) + fr * aa
        w.put(_fin(_opaque(outc.astype(np.uint8)), tt, dur, 0.01, 0.2))
    w.close()


# ---------------------------------------------------------------- tape 斜向警戒带英文条
def _tape(text, W, h, bg, fg, S):
    f = ImageFont.truetype(str(latin(text, OSWALD)), int(h * 0.62))
    unit = f'{text}  ///  '
    L = int(W * 2.4)
    im = Image.new('RGBA', (L, int(h)), hex_rgba(bg))
    d = ImageDraw.Draw(im)
    x = 0
    while x < L:
        d.text((x, h / 2), unit, font=f, anchor='lm', fill=hex_rgba(fg))
        x += f.getlength(unit)
    return np.array(im)


def tape(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    h = int(H * 0.05)
    a1 = _tape(t.get('text', 'WARNING'), W, h, '#FFE100', '#111111', S)
    a2 = _tape(t.get('text2', t.get('text', 'CAUTION')), W, h, '#1D4FC4', '#FFFFFF', S)
    corner = t.get('corner', 'top')
    cy = H * (0.16 if corner == 'top' else 0.84)
    if is_landscape(W, H):
        cx, cy = side_anchor(t, W, H)
        a1 = a1[:, :int(W * 0.24)]
        a2 = a2[:, :int(W * 0.24)]
    w = SideWriter(out, W, H, FPS, t) if is_landscape(W, H) else Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for k, (a, ang, sp) in enumerate(((a1, 25, 1), (a2, -30, -1))):
            p = ease((tt - 0.12 * k) / 0.3, 'out')
            if p <= 0:
                continue
            off = 0 if is_landscape(W, H) else int((tt * 60 * S * sp) % (a.shape[1] / 3))
            strip = a[:, off:off + int(W * 1.6)]
            r = rotate_rgba(with_shadow(strip, 6 * S, 0.5), ang)
            put(c, r, (cx if is_landscape(W, H) else W / 2) + sp * (1 - p) * W * 1.2, cy)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- searchhook 模糊搜索结果钩子
def searchhook(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    frs = read(t['src'], t.get('src_in', 0), dur, (W, H), FPS, t.get('crop'))
    cb = t.get('clear', [0.06, 0.16, 0.55, 0.55] if is_landscape(W, H) else [0.1, 0.36, 0.8, 0.2])
    x0, y0, x1, y1 = int(cb[0] * W), int(cb[1] * H), int((cb[0] + cb[2]) * W), int((cb[1] + cb[3]) * H)
    big = with_shadow(_fit(word(t['text'], H * 0.1, '#111111', HEAVY, stroke=int(8 * S), stroke_color='#FFFFFF'), W * 0.92), 10 * S, 0.5)
    kws = [text_img(x, H * 0.07, '#BFB48A', fontfile=HEAVY, vertical=True, stroke=int(3 * S), stroke_color='#111111') for x in (t.get('items') or [])[:2]]
    ghost = word(t.get('number', '90%'), H * 0.42, '#9A9A9A', latin(t.get('number', '90%'), OSWALD))
    if is_landscape(W, H):
        big = fit_sprite(big, W * 0.27, H * 0.2)
        ghost = fit_sprite(ghost, W * 0.26, H * 0.26)
        kws = [fit_sprite(g, W * 0.11, H * 0.23) for g in kws]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        bl = np.array(Image.fromarray(fr).resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(2.5)).resize((W, H), Image.BILINEAR))
        bl[y0:y1, x0:x1] = fr[y0:y1, x0:x1]
        c = _opaque(bl)
        put(c, ghost, W * 0.8 if is_landscape(W, H) else W / 2, H * 0.3 if is_landscape(W, H) else H * 0.5, 0.35)
        im = Image.fromarray(c)
        ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], outline=(255, 255, 255, 255), width=int(4 * S))
        c = np.array(im)
        p = ease((tt - 0.15) / 0.25, 'out')
        put(c, scale(big, 1.2 - 0.2 * p), W * 0.8 if is_landscape(W, H) else W / 2, H * 0.61 if is_landscape(W, H) else H * 0.78, p)
        for k, g in enumerate(kws):
            q = ease((tt - 0.5 - 0.15 * k) / 0.3, 'out')
            put(c, g, W * (0.74 + 0.12 * k if is_landscape(W, H) else 0.9 - 0.11 * k) + (1 - q) * W * 0.3, H * 0.34 if is_landscape(W, H) else H * 0.28, q)
        w.put(_fin(c, tt, dur))
    w.close()
