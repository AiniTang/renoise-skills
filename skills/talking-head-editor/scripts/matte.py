"""抠像手法的逐帧合成（第 4 批）。人像透明度由 person_matte.py 按段抠好并缓存，这里只管怎么摆。

版式（layout 的 mode，盖住口播画面、铺满整屏的 mp4，render.py 和 cards 的版式在同一个循环里叠）：
- matte     人原地不动、背景换掉：虚化（matte_bg_blur）、换话题画面（matte_bg_swap）、原背景；都能加描边（matte_outline）
- corner    人缩到角落给内容让位（matte_corner_person）：叠录屏、观点卡、玻璃卡、倾斜图片卡
- breakout  人物出框（matte_frame_breakout）：相框出头、横条探头、压住画框角、手伸出卡片
另外给别处用：
- person_clip  人像单独渲成带透明通道的片段，「字在人后」把它盖回大字上面
- head_top     某一刻头顶在画面里的高度（头顶关键词按它摆）
- cutouts      逐帧人像透明度（白雾数字窗把人压在最上层）
"""
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

from cards import _src, _style, eback, fit_text, scale_rgba, shadow_of, ss, stack
from kvlib import unit, is_landscape, safe_zones, hex_rgba, item_times
from motion import Writer, bg_frames, ease, over, paste, read, rotate_rgba, text_img, trim
from motion import _quad_coeffs, _rmask
from person_matte import alphas



def cutouts(aroll, t0, dur, W, H, FPS):
    """逐帧人像透明度，0~1 的 H×W，和 motion.read 读到的口播画面逐像素对齐。"""
    return alphas(aroll, t0, dur, W, H, FPS)


def frames(aroll, t0, dur, W, H, FPS):
    return zip(read(aroll, t0, dur, (W, H), FPS), alphas(aroll, t0, dur, W, H, FPS))


def head_top(aroll, t, W, H, FPS):
    """t 秒时头顶的高度（占画面高的比例）。"""
    return top_of(next(alphas(aroll, t, 1 / FPS, W, H, FPS)))


def top_of(a):
    """一帧透明度里头顶的高度：画面中间一段里人像最高的那一行。"""
    H, W = a.shape
    rows = np.where((a[:, int(W * 0.3):int(W * 0.7)] > 0.5).mean(1) > 0.04)[0]
    return float(rows[0]) / H if len(rows) else 0.12


def person_clip(aroll, t0, t1, W, H, FPS, out, outline=None):
    """人像单独成片（ProRes 4444，透明底，时间从 0 开始），可带描边。"""
    w = Writer(out, W, H, FPS, alpha=True)
    S = unit(W, H)
    for fr, a in frames(aroll, t0, t1 - t0, W, H, FPS):
        o = np.zeros((H, W, 4), np.uint8)
        if outline:
            canvas = np.zeros((H, W, 3), np.float32)
            acc = np.zeros((H, W), np.float32)
            for col, la in outline_layers(a, outline, S):
                canvas = canvas * (1 - la[..., None]) + col * la[..., None]
                acc = acc + la * (1 - acc)
            canvas = canvas * (1 - a[..., None]) + fr * a[..., None]
            acc = acc + a * (1 - acc)
            o[..., :3] = np.clip(canvas / np.maximum(acc, 1e-3)[..., None], 0, 255)
            o[..., 3] = acc * 255
        else:
            o[..., :3] = fr
            o[..., 3] = a * 255
        w.put(o)
    w.close()
    return out


# ---------------------------------------------------------------- 描边
OUTLINES = {
    'solid_white': '白色实线：人像外一圈约 9 像素纯白实心描边，像贴纸，最常用',
    'color_thin': '彩色细描边：约 5 像素黄色细边（outline_color 写 green 换绿色），配干净背景',
    'dashed': '白色虚线：沿轮廓外扩一圈白色短划虚线，背景压到六成亮，像剪纸',
    'torn_edge': '撕纸毛边：约 15 像素不规则白纸边带一点投影，像从杂志上撕下来贴上去',
}
OUTLINE_COLORS = {'yellow': '#F5D020', 'green': '#3FAF7A', 'white': '#FFFFFF'}


@lru_cache(maxsize=16)
def _disk(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


@lru_cache(maxsize=4)
def _paper_noise(h, w, S):
    """撕纸边用的静态噪声：大块起伏加细碎毛刺。"""
    rng = np.random.default_rng(7)
    big = cv2.resize(rng.random((max(2, h // int(16 * S + 1)), max(2, w // int(16 * S + 1)))).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    fine = cv2.resize(rng.random((max(2, h // int(5 * S + 1)), max(2, w // int(5 * S + 1)))).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return 0.85 * big + 0.15 * fine


def outline_layers(a, look, S, color=None):
    """人像透明度 → 描边图层列表 [(RGB, H×W 0~1)]，按顺序画在人像下面。
    先把透明度柔化一下再外扩：飘起来的几根头发不会被描成一坨白。"""
    if not look:
        return []
    H, W = a.shape
    body = cv2.GaussianBlur(a, (0, 0), 2.5 * S)
    body = np.clip((body - 0.35) * 4, 0, 1)
    if look in ('solid_white', 'color_thin', 'white', 'yellow', 'green'):
        thin = look in ('color_thin', 'yellow', 'green')
        col = color or ('#FFFFFF' if not thin else OUTLINE_COLORS.get(look if look != 'color_thin' else 'yellow'))
        d = cv2.dilate(body, _disk((5 if thin else 9) * S))
        return [(np.array(hex_rgba(OUTLINE_COLORS.get(col, col))[:3], np.float32), cv2.GaussianBlur(d, (0, 0), 0.8))]
    if look == 'dashed':
        ring = cv2.dilate((body > 0.5).astype(np.uint8), _disk(15 * S))
        cs, _ = cv2.findContours(ring, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        m = np.zeros((H, W), np.uint8)
        on, period, lw = 20 * S, 32 * S, max(2, int(round(0.008 * W)))
        for c in cs:
            p = c[:, 0, :]
            if len(p) < 40:
                continue
            k = int(np.argmin(p[:, 1]))   # 从头顶那一点起量：虚线的相位每帧都对齐头顶，不会沿轮廓爬
            p = np.roll(p, -k, 0)
            s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
            edge = (p[:, 0] <= 2) | (p[:, 0] >= W - 3) | (p[:, 1] <= 2) | (p[:, 1] >= H - 3)   # 贴着画面边的那段轮廓不画
            draw = ((s % period) < on) & ~edge
            idx = np.flatnonzero(np.diff(np.concatenate([[0], draw.astype(np.int8), [0]])))
            for i0, i1 in zip(idx[::2], idx[1::2]):
                if i1 - i0 > 1:
                    cv2.polylines(m, [p[i0:i1].reshape(-1, 1, 2)], False, 255, lw, cv2.LINE_AA)
        return [(np.array([255, 255, 255], np.float32), m.astype(np.float32) / 255)]
    if look == 'torn_edge':
        b = (body > 0.5).astype(np.uint8)
        big, small = cv2.dilate(b, _disk(22 * S)), cv2.dilate(b, _disk(11 * S))
        torn = np.maximum(small, big * (_paper_noise(H, W, round(S, 2)) > 0.5)).astype(np.float32)
        torn = cv2.GaussianBlur(torn, (0, 0), 0.7)
        sh = np.roll(cv2.GaussianBlur(torn, (0, 0), 6 * S), (int(6 * S), int(4 * S)), (0, 1)) * 0.35
        return [(np.zeros(3, np.float32), sh), (np.array([250, 249, 244], np.float32), torn)]
    raise SystemExit(f'抠像描边没有「{look}」，可选：{"、".join(OUTLINES)}')


def put_person(canvas, rgb, a, look=None, S=1.0, shadow=0.0, color=None):
    """人像（rgb + 0~1 透明度，和 canvas 同尺寸）连描边、投影一起合到 canvas（float32 H×W×3）上。"""
    if shadow:
        sh = np.roll(cv2.GaussianBlur(a, (0, 0), 14 * S), (int(16 * S), int(12 * S)), (0, 1)) * shadow
        canvas *= 1 - sh[..., None]
    for col, la in outline_layers(a, look, S, color):
        canvas[:] = canvas * (1 - la[..., None]) + col * la[..., None]
    canvas[:] = canvas * (1 - a[..., None]) + rgb.astype(np.float32) * a[..., None]
    return canvas


def blur_behind(fr, a, sigma):
    """背景虚化：先把人挖掉再糊，人身边不会糊出一圈人的颜色。"""
    H, W = a.shape
    q = 4
    sm = cv2.resize(fr, (W // q, H // q), interpolation=cv2.INTER_AREA).astype(np.float32)
    keep = 1 - cv2.resize(a, (W // q, H // q), interpolation=cv2.INTER_AREA)
    num = cv2.GaussianBlur(sm * keep[..., None], (0, 0), sigma / q)
    den = cv2.GaussianBlur(keep, (0, 0), sigma / q)[..., None]
    plain = cv2.GaussianBlur(sm, (0, 0), sigma / q)
    w = np.clip(den * 4, 0, 1)
    out = num / np.maximum(den, 1e-3) * w + plain * (1 - w)
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_LINEAR)


def _bg_source(l, W, H, FPS, n, dur, work, aroll, t0):
    """版式底：src 给了素材就铺素材，否则 blur（口播虚化）/ grid:rainbow 这类代码画的底。"""
    if l.get('src') and l.get('bg') in (None, 'swap'):
        return read(_src(l['src'], work), l.get('src_in', 0), dur, (W, H), FPS)
    return bg_frames(l.get('bg') or 'blur', W, H, FPS, n, work, aroll, t0)


def layout_clip(l, tl, W, H, FPS, st, work, aroll, preview=False):
    out = f"{work}/{l['mode']}_{l['t0']:.2f}.mp4"
    {'matte': cutout, 'corner': corner, 'breakout': breakout}[l['mode']](l, tl, W, H, FPS, st, work, aroll, out, preview)
    return out


def _pop_title(text, H, W, style, color='#FFFFFF', size=0.05):
    ti = fit_text(text, H * size, W * 0.88, color, 'title', style)
    return np.maximum(shadow_of(ti, 10 * unit(W, H), 0.55), ti) if color.upper().startswith('#FFF') else ti


# ---------------------------------------------------------------- matte：人不动，换背景
BG_LOOKS = {
    'blur': '背景虚化：人始终清楚，身后整体轻度虚化，像大光圈拍的',
    'swap': '换话题背景：人原地不动，身后的实拍背景硬切成话题相关的截图、录屏或图片，压到八成亮，顶部可压一行话题标题',
    'keep': '原背景：只加描边，虚线描边时背景压到六成亮',
}


def cutout(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {bg: blur|swap|keep|grid:rainbow…, src, src_in, dim, blur, outline, outline_color, title}。"""
    S, style = unit(W, H), _style(st)
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    look = l.get('outline')
    bg = l.get('bg') or ('swap' if l.get('src') else 'blur')
    dim = l.get('dim', 0.8 if bg == 'swap' else 0.6 if look == 'dashed' else 1.0)
    src = None if bg in ('blur', 'keep') else _bg_source({**l, 'bg': None if bg == 'swap' else bg}, W, H, FPS, n, dur, work, aroll, l['t0'])
    ti = _pop_title(l['title'], H, W, style) if l.get('title') else None
    if ti is not None and is_landscape(W, H):
        z = safe_zones(W, H)['text'][0 if l.get('side') == 'left' else 1]
        ti = fit_text(l['title'], 62 * S, W * (z[2] - max(0.05, z[0])) * 0.9, '#FFFFFF', 'title', style)
        ti = np.maximum(shadow_of(ti, 8 * S, 0.55), ti)
    w = Writer(out, W, H, FPS, preview=preview)
    for i, (fr, a) in enumerate(frames(aroll, l['t0'], dur, W, H, FPS)):
        if bg == 'blur':
            base = blur_behind(fr, a, l.get('blur', 12) * S)
        elif bg == 'keep':
            base = fr.astype(np.float32)
        else:
            base = next(src).astype(np.float32)
        base *= dim
        put_person(base, fr, a, look, S, color=l.get('outline_color'))
        canvas = np.clip(base, 0, 255).astype(np.uint8)
        if ti is not None:   # 话题标题：顶部弹入
            tt = i / FPS - 0.1
            if tt > 0:
                k = 0.6 + 0.4 * eback(tt / 0.3)
                im = scale_rgba(ti, k) if abs(k - 1) > 0.01 else ti
                cx, cy = W / 2, H * l.get('title_y', 0.10)
                if is_landscape(W, H):
                    cx, cy = W * (max(0.05, z[0]) + min(0.95, z[2])) / 2, H * l.get('title_y', 0.32)
                    cy = min(H * 0.75 - im.shape[0] / 2, max(H * 0.05 + im.shape[0] / 2, cy))
                paste(canvas, im, cx - im.shape[1] / 2, cy - im.shape[0] / 2, opacity=min(1.0, tt / 0.12))
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- corner：人缩到角落
CORNER_VARIANTS = {
    'over_recording': '人叠录屏：录屏铺满（横屏录屏放在上半屏），人带白描边缩到六成放右下，整段不切',
    'point_cards': '观点卡竖排：背景虚化，人带白色虚线描边缩到左下，右上依次弹出三张深橄榄色圆角观点卡，带浅色错位投影',
    'glass_cards': '立体玻璃卡：深色网格底，人带白描边站左下，右侧三张半透明蓝玻璃卡带透视，上下错开浮着',
    'tilted_cards': '倾斜图片卡：背景虚化，以素材为底的圆角卡斜着从左滑入，沿对角线错开排，卡上超粗白字配小号英文',
}
CORNER_PRESETS = {   # 人缩到多大、站哪边、描边；人的位置按头像中心算
    'over_recording': dict(scale=0.60, side='right', outline='solid_white'),
    'point_cards': dict(scale=0.47, side='left', outline='dashed'),
    'glass_cards': dict(scale=0.50, side='left', outline='solid_white'),
    'tilted_cards': dict(scale=0.46, side='right', outline='solid_white'),
}


def _card_point(text, S, H, W, style):
    """深橄榄色观点卡，带浅色错位投影。"""
    ti = fit_text(text, H * 0.026, W * 0.34, '#F3EED8', 'title', style)
    cw, ch = int(W * 0.40), int(max(H * 0.07, ti.shape[0] + H * 0.03))
    if is_landscape(W, H):
        ti = fit_text(text, 52 * S, W * 0.44, '#F3EED8', 'title', style)
        cw, ch = int(W * 0.50), int(H * 0.15)
    off = int(8 * S)
    card = np.zeros((ch + off, cw + off, 4), np.uint8)
    r = int(14 * S)
    for (x, y), col in (((off, off), '#C8C29A'), ((0, 0), '#3B3A2C')):
        blk = np.zeros((ch, cw, 4), np.uint8)
        blk[..., :3] = hex_rgba(col)[:3]
        blk[..., 3:4] = (_rmask(cw, ch, r) * 255).astype(np.uint8)
        over(card, blk, x, y)
    over(card, ti, (cw - ti.shape[1]) / 2, (ch - ti.shape[0]) / 2)
    return card


def _card_glass(text, en, S, H, W, style, flip):
    """半透明蓝玻璃卡：白描边，往一侧转约 20° 的透视。"""
    cw, ch = int(W * 0.44), int(H * 0.095)
    if is_landscape(W, H):
        cw, ch = int(W * 0.54), int(H * 0.17)
    r = int(18 * S)

    def draw(d, k):
        d.rounded_rectangle([0, 0, cw * k - 1, ch * k - 1], radius=r * k, fill=(60, 111, 184, 158), outline=(255, 255, 255, 230), width=int(3 * S * k))
    card = ss(cw, ch, draw)
    ti = fit_text(text, H * 0.028, cw * 0.84, '#FFFFFF', 'title', style)
    if is_landscape(W, H):
        ti = fit_text(text, 52 * S, cw * 0.84, '#FFFFFF', 'title', style)
    if en:
        e = fit_text(en.upper(), H * 0.012, cw * 0.84, '#FFFFFFB0', 'en', style)
        if is_landscape(W, H):
            e = fit_text(en.upper(), 26 * S, cw * 0.84, '#FFFFFFB0', 'en', style)
        blk = stack([ti, e], int(H * 0.006), 'center')
    else:
        blk = ti
    over(card, blk, (cw - blk.shape[1]) / 2, (ch - blk.shape[0]) / 2)
    sk = 0.16   # 远的一边缩短 16%，约 20° 转角
    q = [(0, ch * sk), (cw * 0.9, 0), (cw * 0.9, ch), (0, ch * (1 - sk))] if flip else [(0, 0), (cw * 0.9, ch * sk), (cw * 0.9, ch * (1 - sk)), (0, ch)]
    im = Image.fromarray(card, 'RGBA').transform((int(cw * 0.9), ch), Image.PERSPECTIVE, _quad_coeffs(q, [(0, 0), (cw, 0), (cw, ch), (0, ch)]), Image.BICUBIC)
    a = np.array(im)
    return np.maximum(shadow_of(a, 12 * S, 0.45), a)


def _card_tilted(text, en, src, work, S, H, W, style):
    """以素材为底的圆角卡（压暗），超粗白字加小号英文，带一点斜。"""
    cw, ch = int(W * 0.58), int(H * 0.15)
    if is_landscape(W, H):
        cw, ch = int(W * 0.46), int(H * 0.16)
    if src:
        im = cv2.GaussianBlur(next(read(_src(src, work), 0, 0.04, (cw, ch), 25)), (0, 0), 3 * S).astype(np.float32) * 0.45
    else:
        im = np.zeros((ch, cw, 3), np.float32) + np.array(hex_rgba('#2B3A55')[:3], np.float32)
    card = np.zeros((ch, cw, 4), np.uint8)
    card[..., :3] = im.astype(np.uint8)
    card[..., 3:4] = (_rmask(cw, ch, int(22 * S)) * 255).astype(np.uint8)
    ti = fit_text(text, 52 * S if is_landscape(W, H) else H * 0.040, cw * 0.86, '#FFFFFF', 'title', style, italic=0.1)
    parts = [ti] + ([fit_text(en.upper(), 26 * S if is_landscape(W, H) else H * 0.013, cw * 0.86, '#FFFFFFC0', 'en', style)] if en else [])
    blk = stack(parts, int(H * 0.006))
    over(card, np.maximum(shadow_of(blk, 6 * S, 0.6), blk), cw * 0.07, (ch - blk.shape[0]) / 2)
    a = rotate_rgba(card, -5)
    return np.maximum(shadow_of(a, 14 * S, 0.5), a)


def _items(l):
    return [x if isinstance(x, dict) else {'text': x} for x in (l.get('items') or [])][:3]


def corner(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {variant, items: [文字 或 {text, en, src}], src（叠录屏的录屏）, src_in, side, scale, outline, at（每张卡出现秒数）}。
    开头 0.4 秒人从原位缩到角落，背景同时从口播换成新底。"""
    S, style = unit(W, H), _style(st)
    v = l.get('variant', 'point_cards')
    P = {**CORNER_PRESETS[v], **{k: l[k] for k in ('scale', 'side', 'outline') if k in l}}
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    s, right = P['scale'], P['side'] == 'right'
    tx = W * (0.73 if right else 0.27) - s * W / 2   # 头像中心落在左右四分之一处
    ty = H - s * H * 0.97   # 人的下沿贴画面底
    if is_landscape(W, H):
        s = min(l.get('scale', 0.72), 0.74)
        tx = W * (0.77 if right else 0.23) - s * W / 2
        ty = H * 0.80 - s * H
    move = 0.4
    items = _items(l)
    sprites = []
    rec = None
    if v == 'over_recording':
        src = _src(l['src'], work)
        from kvlib import probe, is_image
        if is_image(src):
            iw, ih = Image.open(src).size
        else:
            p = probe(src)
            iw, ih = p['w'], p['h']
        if is_landscape(W, H):
            f = min(W * 0.54 / iw, H * 0.64 / ih)
            rw, rh = max(2, int(iw * f)), max(2, int(ih * f))
            rec = (read(src, l.get('src_in', 0), dur, (rw, rh), FPS), W * (0.32 if right else 0.68) - rw / 2,
                   H * 0.44 - rh / 2, _rmask(rw, rh, int(20 * S)))
            bgs = bg_frames('blur', W, H, FPS, n, work, aroll, l['t0'])
        elif iw / ih > 0.8:   # 横屏录屏：按宽放进上半屏的圆角卡，底是口播虚化
            rw = int(W * 0.94)
            rh = int(rw * ih / iw)
            if is_landscape(W, H):
                f = min(1, W * 0.62 / rw, H * 0.56 / rh)
                rw, rh = max(2, int(rw * f)), max(2, int(rh * f))
            rec = (read(src, l.get('src_in', 0), dur, (rw, rh), FPS), (W - rw) / 2, H * 0.32 - rh / 2, _rmask(rw, rh, int(20 * S)))
            bgs = bg_frames('blur', W, H, FPS, n, work, aroll, l['t0'])
        else:
            bgs = read(src, l.get('src_in', 0), dur, (W, H), FPS)
    elif v == 'point_cards':
        bgs = None
        ats = item_times({'start': move + 0.1, **l}, len(items), 0.3)
        y = H * 0.14
        for it, a in zip(items, ats):
            c = _card_point(it['text'], S, H, W, style)
            sprites.append((c, W * 0.95 - c.shape[1], y, a, 'pop'))
            y += c.shape[0] + H * 0.03
    elif v == 'glass_cards':
        bgs = bg_frames(l.get('bg', 'grid:rainbow'), W, H, FPS, n, work)
        ats = item_times({'start': move + 0.1, **l}, len(items), 0.3)
        for j, (it, a) in enumerate(zip(items, ats)):
            c = _card_glass(it['text'], it.get('en'), S, H, W, style, flip=j % 2 == 1)
            sprites.append((c, W * (0.50 if j % 2 == 0 else 0.44), H * (0.12 + 0.15 * j), a, 'float'))
    else:
        bgs = None
        ats = item_times({'start': move, **l}, len(items), 0.3)
        for j, (it, a) in enumerate(zip(items, ats)):
            c = _card_tilted(it['text'], it.get('en'), it.get('src'), work, S, H, W, style)
            sprites.append((c, W * (0.03 + 0.08 * j), H * (0.05 + 0.185 * j), a, 'slide'))
    if is_landscape(W, H):
        # 人和卡片各占一栏，side 换边时整列一起换，不让卡片穿过脸。
        sprites = [(c, W * (0.32 if right else 0.68) - c.shape[1] / 2,
                    H * (0.14 + 0.21 * j), a, kind) for j, (c, x, y, a, kind) in enumerate(sprites)]
    w = Writer(out, W, H, FPS, preview=preview)
    for i, (fr, a) in enumerate(frames(aroll, l['t0'], dur, W, H, FPS)):
        tt = i / FPS
        p = ease(tt / move, 'out')
        if bgs is None:
            nb = blur_behind(fr, a, 22 * S) * 0.62
        else:
            nb = next(bgs).astype(np.float32)
        base = fr.astype(np.float32) * (1 - p) + nb * p if p < 1 else nb
        if rec is not None:
            gen, rx, ry, rm = rec
            rf = next(gen)
            rc = np.clip(base, 0, 255).astype(np.uint8)
            paste(rc, rf, rx, ry, rm, opacity=p)
            base = rc.astype(np.float32)
        k = 1 + (s - 1) * p
        x, y = tx * p, ty * p
        pw, ph = max(2, int(W * k)), max(2, int(H * k))
        pr = cv2.resize(fr, (pw, ph), interpolation=cv2.INTER_AREA)
        pa = cv2.resize(a, (pw, ph), interpolation=cv2.INTER_AREA)
        fa = np.zeros((H, W), np.float32)
        fr2 = np.zeros((H, W, 3), np.uint8)
        x0, y0 = int(round(x)), int(round(y))
        sx0, sy0 = max(0, -x0), max(0, -y0)
        dx0, dy0 = max(0, x0), max(0, y0)
        cw_, ch_ = min(pw - sx0, W - dx0), min(ph - sy0, H - dy0)
        fa[dy0:dy0 + ch_, dx0:dx0 + cw_] = pa[sy0:sy0 + ch_, sx0:sx0 + cw_]
        fr2[dy0:dy0 + ch_, dx0:dx0 + cw_] = pr[sy0:sy0 + ch_, sx0:sx0 + cw_]
        canvas = np.clip(base, 0, 255).astype(np.uint8)
        for c, cx, cy, a0, kind in sprites:   # 卡片在人后面：人站在前景
            if tt < a0:
                continue
            q = (tt - a0) / 0.3
            if kind == 'pop':
                kk = 0.6 + 0.4 * eback(q)
                im = scale_rgba(c, kk) if kk < 0.995 or kk > 1.005 else c
                paste(canvas, im, cx + (c.shape[1] - im.shape[1]) / 2, cy + (c.shape[0] - im.shape[0]) / 2, opacity=min(1.0, q * 3))
            elif kind == 'slide':
                e = ease(q, 'out')
                paste(canvas, c, cx - (1 - e) * W * 0.6, cy, opacity=min(1.0, q * 2))
            else:   # 玻璃卡：弹出后轻轻上下浮
                kk = 0.7 + 0.3 * eback(q)
                im = scale_rgba(c, kk) if kk < 0.995 or kk > 1.005 else c
                bob = np.sin((tt - a0) * 2.2 + cx) * 6 * S
                paste(canvas, im, cx + (c.shape[1] - im.shape[1]) / 2, cy + bob + (c.shape[0] - im.shape[0]) / 2, opacity=min(1.0, q * 3))
        cf = canvas.astype(np.float32)
        put_person(cf, fr2, fa, P['outline'] if p > 0.5 else None, S)
        w.put(np.clip(cf, 0, 255).astype(np.uint8))
    w.close()


# ---------------------------------------------------------------- breakout：人物出框
BREAKOUT_VARIANTS = {
    'head_over_frame': '相框出头：拍立得相框装着口播，人的头顶越过相框上沿探出来，相框下沿写一行手写字',
    'band_pop': '横条探头：上下两张图，中间一条口播横条，人头伸出横条压在上方大标题前面',
    'corner_over_card': '压住画框角：深色网格底上一张白色圆角画框装标题和素材，人缩小站在左下压住画框角，带投影',
    'hands_below_card': '手伸出卡片：口播装进圆角卡片、下沿裁到腰部，手越过卡片底边伸到黑底上（要手势伸出身体外的素材，近景口播做不出）',
}


def breakout(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {variant, title, src, src2, overflow（头出框多少，占画面高）, bg}。
    做法：口播缩放后放在「窗口」里照常显示，窗口外只在允许的方向（头的上方、手的下方）显示抠出来的人。"""
    S, style = unit(W, H), _style(st)
    v = l.get('variant', 'head_over_frame')
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    ht = head_top(aroll, l['t0'] + min(0.5, dur / 2), W, H, FPS)
    deco, top_deco = [], []   # (RGBA, x, y)：窗口下面的装饰（相框、画框）和人后面、窗口外的装饰（标题、卡片白边）
    edge = None
    over_ = l.get('overflow', 0.09)
    shadow = 0.0
    if v == 'head_over_frame':
        k = 0.70
        ww = int(W * k * 0.92)
        wh = int(ww * 1.02)
        wx = (W - ww) / 2
        wy = H * 0.30
        vx, vy = (W - W * k) / 2, wy - k * ht * H - over_ * H
        bd, bb = int(W * 0.035), int(W * 0.13)   # 拍立得：三边细、下边宽
        if is_landscape(W, H):
            k, ww, wh = 0.62, int(W * 0.58), int(H * 0.43)
            wx, wy = W * 0.08, H * 0.23
            vx, vy = wx + ww / 2 - W * k / 2, wy - k * ht * H - min(over_, 0.10) * H
            bd, bb = int(22 * S), int(H * 0.09)

        def frame_draw(d, kk):
            d.rounded_rectangle([0, 0, (ww + 2 * bd) * kk - 1, (wh + bd + bb) * kk - 1], radius=6 * S * kk, fill=(250, 248, 242, 255))
        fr_img = ss(ww + 2 * bd, wh + bd + bb, frame_draw)
        deco.append((np.maximum(shadow_of(fr_img, 16 * S, 0.45), fr_img), wx - bd, wy - bd))
        if l.get('title'):
            from cards import SCRIPT_FONT
            cap = trim(text_img(l['title'], H * 0.034, '#2A2A2A', fontfile=SCRIPT_FONT if l['title'].isascii() else None, style=style, role='hand'))
            cap = scale_rgba(cap, min(1.0, ww * 0.9 / cap.shape[1]))
            cap_x = wx + ww / 2 - cap.shape[1] / 2 if is_landscape(W, H) else W / 2 - cap.shape[1] / 2
            deco.append((cap, cap_x, wy + wh + (bb - cap.shape[0]) / 2))
        win = (wx, wy, wx + ww, wy + wh)
        zone = 'up'
        bgs = bg_frames(l.get('bg', 'paper:kraft'), W, H, FPS, n, work, aroll, l['t0'])
    elif v == 'band_pop':
        k = 1.0
        b0, b1 = int(H * 0.37), int(H * 0.82)
        vx, vy = 0.0, b0 - over_ * H - ht * H
        win = (0, b0, W, b1)
        zone = 'up'
        top = read(_src(l['src'], work), 0, 0.04, (W, b0), 25) if l.get('src') else None
        bot_src = l.get('src2') or l.get('src')
        bot = read(_src(bot_src, work), 0, 0.04, (W, H - b1), 25) if bot_src else None
        static = np.zeros((H, W, 3), np.uint8) + 18
        if top is not None:
            static[:b0] = (next(top).astype(np.float32) * 0.6).astype(np.uint8)
        if bot is not None:
            static[b1:] = (next(bot).astype(np.float32) * 0.6).astype(np.uint8)
        bgs = (static for _ in range(n))
        if l.get('title'):
            ti = fit_text(l['title'], H * 0.07, W * 0.9, '#FFFFFF', 'title', style, italic=0.08)
            ti = np.maximum(shadow_of(ti, 10 * S, 0.6), ti)
            top_deco.append((ti, (W - ti.shape[1]) / 2, b0 - over_ * H * 0.85 - ti.shape[0]))
        line = np.zeros((int(5 * S), W, 4), np.uint8)
        line[...] = (255, 255, 255, 235)
        deco += [(line, 0, b0 - line.shape[0] / 2), (line, 0, b1 - line.shape[0] / 2)]
        if is_landscape(W, H):
            # 横条放中间，两张素材分居左右，标题进左栏。
            k = 0.80
            vx, vy = W * 0.1, H * 0.30 - min(over_, 0.10) * H - ht * H * k
            win = (W * 0.33, H * 0.30, W * 0.67, H * 0.76)
            static = np.full((H, W, 3), 18, np.uint8)
            for src, x in ((l.get('src'), 0.05), (bot_src, 0.70)):
                if src:
                    im = next(read(_src(src, work), 0, 0.04, (int(W * 0.25), int(H * 0.42)), 25))
                    paste(static, (im * 0.6).astype(np.uint8), W * x, H * 0.34)
            bgs = (static for _ in range(n))
            deco, top_deco = [], []
            if l.get('title'):
                ti = fit_text(l['title'], 64 * S, W * 0.25, '#FFFFFF', 'title', style)
                top_deco.append((ti, W * 0.175 - ti.shape[1] / 2, H * 0.18))
            line = np.full((max(1, int(5 * S)), int(W * 0.34), 4), 255, np.uint8)
            deco = [(line, win[0], win[1]), (line, win[0], win[3])]
    elif v == 'hands_below_card':
        k = 0.88
        vx, vy = (W - W * k) / 2, H * 0.05
        win = (vx, vy, vx + W * k, vy + k * H * l.get('waist', 0.70))
        if is_landscape(W, H):
            k = 0.64
            vx, vy = (W - W * k) / 2, H * 0.10
            win = (vx, vy, vx + W * k, vy + k * H * l.get('waist', 0.70))
        zone = 'down'
        bgs = bg_frames('black', W, H, FPS, n, work)
        bw = max(2, int(4 * S))   # 卡片白边：手越过它，才看得出是伸出卡片

        def edge_draw(d, kk):
            d.rounded_rectangle([0, 0, (win[2] - win[0]) * kk - 1, (win[3] - win[1]) * kk - 1], radius=W * 0.03 * kk, outline=(255, 255, 255, 240), width=int(bw * kk))
        edge = (ss(win[2] - win[0], win[3] - win[1], edge_draw), win[0], win[1])
    else:   # corner_over_card
        k = l.get('scale', 0.48)
        vx, vy = -W * k * 0.22, H - k * H * 0.98
        win = None
        zone = 'all'
        shadow = 0.45
        bgs = bg_frames(l.get('bg', 'grid:white'), W, H, FPS, n, work)
        cw, chh = int(W * 0.84), int(H * 0.56)
        cx, cy = (W - cw) / 2, H * 0.08
        if is_landscape(W, H):
            k = min(l.get('scale', 0.68), 0.72)
            vx, vy = W * 0.23 - W * k / 2, H * 0.80 - k * H
            cw, chh = int(W * 0.54), int(H * 0.64)
            cx, cy = W * 0.41, H * 0.12

        def card_draw(d, kk):
            d.rounded_rectangle([0, 0, cw * kk - 1, chh * kk - 1], radius=W * 0.03 * kk, fill=(255, 255, 255, 255))
        card = ss(cw, chh, card_draw)
        yy = int(H * 0.035)
        if l.get('title'):
            ti = fit_text(l['title'], H * 0.042, cw * 0.86, '#1E3A5F', 'title', style)
            over(card, ti, (cw - ti.shape[1]) / 2, yy)
            yy += ti.shape[0] + int(H * 0.025)
        if l.get('src'):
            iw, ih = int(cw * 0.88), int(chh - yy - H * 0.035)
            im = np.zeros((ih, iw, 4), np.uint8)
            im[..., :3] = next(read(_src(l['src'], work), l.get('src_in', 0), 0.04, (iw, ih), 25))
            im[..., 3:4] = (_rmask(iw, ih, int(14 * S)) * 255).astype(np.uint8)
            over(card, im, (cw - iw) / 2, yy)
        deco.append((np.maximum(shadow_of(card, 20 * S, 0.5), card), cx, cy))
    if v == 'hands_below_card':   # 卡片下沿露出来的应该只有手；露出来的是整片身体，说明这段素材做不出这个效果
        a_ref = next(cutouts(aroll, l['t0'] + min(0.5, dur / 2), 1 / FPS, W, H, FPS))
        y = min(H - 1, int(H * l.get('waist', 0.70)) + int(H * 0.04))
        body = a_ref[y] > 0.5
        if is_landscape(W, H):
            z = safe_zones(W, H)['face']
            body = body[int(W * z[0]):int(W * z[2])]
        if body.mean() > 0.45:
            print(f"手伸出卡片：{l['t0']:.1f} 秒这段卡片下沿露出来的是整片身体，不是伸出来的手，效果出不来；"
                  "要人在腰部附近、手势伸到身体外面的素材，或者换 head_over_frame / band_pop")
    pw, ph = int(W * k), int(H * k)
    yy_, xx_ = np.mgrid[0:ph, 0:pw]
    gy, gx = yy_ + vy, xx_ + vx   # 缩放后口播每个像素在画面上的位置
    if win:
        inside = ((gx >= win[0]) & (gx < win[2]) & (gy >= win[1]) & (gy < win[3])).astype(np.float32)
        allow = (gy < win[1]) if zone == 'up' else (gy >= win[3])
        allow = allow.astype(np.float32)
        if v == 'hands_below_card':
            inside *= _win_mask(pw, ph, win, vx, vy, int(W * 0.03))
    else:
        inside = np.zeros((ph, pw), np.float32)
        allow = np.ones((ph, pw), np.float32)
    w = Writer(out, W, H, FPS, preview=preview)
    for i, (fr, a) in enumerate(frames(aroll, l['t0'], dur, W, H, FPS)):
        tt = i / FPS
        canvas = next(bgs).copy()
        for im, x, y in deco:
            paste(canvas, im, x, y)
        pr = cv2.resize(fr, (pw, ph), interpolation=cv2.INTER_AREA)
        pa = cv2.resize(a, (pw, ph), interpolation=cv2.INTER_AREA)
        if win:
            paste(canvas, pr, vx, vy, inside[..., None])
        for im, x, y in top_deco:
            paste(canvas, im, x, y, opacity=min(1.0, max(0.0, (tt - 0.1) / 0.25)))
        if edge is not None:
            paste(canvas, *edge)
        rgba = np.dstack([pr, (pa * allow * 255).astype(np.uint8)])
        if shadow:
            sh = shadow_of(rgba, 14 * S, shadow)
            paste(canvas, sh, vx + 14 * S, vy + 10 * S)
        paste(canvas, rgba, vx, vy)
        if tt < 0.15:   # 从口播画面 0.15 秒叠化进来，不硬跳
            canvas = (fr.astype(np.float32) * (1 - tt / 0.15) + canvas.astype(np.float32) * tt / 0.15).astype(np.uint8)
        w.put(canvas)
    w.close()


def _win_mask(pw, ph, win, vx, vy, r):
    """圆角窗口在缩放后口播坐标里的遮罩。"""
    x0, y0, x1, y1 = (int(round(win[0] - vx)), int(round(win[1] - vy)), int(round(win[2] - vx)), int(round(win[3] - vy)))
    m = np.zeros((ph, pw), np.float32)
    rm = _rmask(x1 - x0, y1 - y0, r)[..., 0]
    ys, xs = max(0, y0), max(0, x0)
    m[ys:min(ph, y1), xs:min(pw, x1)] = rm[ys - y0:min(ph, y1) - y0, xs - x0:min(pw, x1) - x0]
    return m
