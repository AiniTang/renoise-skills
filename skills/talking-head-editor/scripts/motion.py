"""逐帧合成：ffmpeg 表达式做不了的画面动画，用 numpy/PIL 一帧帧算好，预渲染成片段再交给 render.py 按时间叠加。

- inset   口播缩成圆角卡片并缩放（frame_card_scale）：讲重点撑满全屏、讲负面缩小露底、章节编号缩框
- circle  圆形蒙版收缩（pip_shrink_circle）：全屏口播收成一个圆，停在中间做大圆，或滑进角落变头像
- split   分屏对比（compare_split_panels）：撕纸竖条、斜线上下、圆角双窗切焦点、三屏并排
- tilt    透视斜置卡（perspective_card）：截图斜放像桌上的纸，单张左倾右倾或镜像三联
- live_card   卡片或原比例素材里平滑放大看细节（punch_zoom_detail 的平滑版）、截图划重点（screenshot_highlight）
- frame_layers / frame_card_png  素材卡的发光描边、取景器边框（clip_card_frame）
- pages   报告纸页飞入堆叠（doc_pages_fly_in）
- opening 开场第一秒入场冲击（opening_entry_hit）

每个函数输出一个文件：铺满画面的不透明 mp4，或带透明通道的 ProRes 4444（.mov）。时间都从这一段开始算。
"""
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import backgrounds
from kvlib import unit, face_crop, find_role_font, hex_rgba, is_image, is_landscape, rounded_mask, safe_zones, to_png


# ---------------------------------------------------------------- 读写帧
def read(src, t0, dur, size, FPS, crop=None):
    """逐帧读素材，按 size=(w,h) 铺满裁切，返回 RGB 数组的生成器，正好 round(dur×FPS) 帧（素材不够长就停在最后一帧）。
    crop=[x, y, 宽, 高]（相对素材的比例）先裁出这一块再铺。"""
    w, h = size
    n = max(1, round(dur * FPS))
    if is_image(src):
        im = Image.open(src).convert('RGB')
        if crop:
            im = im.crop((int(crop[0] * im.width), int(crop[1] * im.height), int((crop[0] + crop[2]) * im.width), int((crop[1] + crop[3]) * im.height)))
        r = max(w / im.width, h / im.height)
        im = im.resize((max(w, round(im.width * r)), max(h, round(im.height * r))), Image.LANCZOS)
        a = np.array(im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w, (im.height - h) // 2 + h)))
        for _ in range(n):
            yield a
        return
    vf = (f'crop=iw*{crop[2]}:ih*{crop[3]}:iw*{crop[0]}:ih*{crop[1]},' if crop else '') + \
        f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={FPS}'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-i', str(src), '-vf', vf, '-frames:v', str(n),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    last = np.zeros((h, w, 3), np.uint8)
    got = 0
    while got < n:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        last = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        got += 1
        yield last
    p.stdout.close()
    p.wait()
    if not got:   # 从素材结尾之后开始读（成片尾巴上定格的那几秒）：用最后一帧
        r = subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.3', '-i', str(src), '-vf', vf, '-frames:v', '1', '-f', 'rawvideo',
                            '-pix_fmt', 'rgb24', '-'], capture_output=True)
        if len(r.stdout) >= w * h * 3:
            last = np.frombuffer(r.stdout[:w * h * 3], np.uint8).reshape(h, w, 3)
    for _ in range(n - got):
        yield last


class Writer:
    def __init__(self, out, W, H, FPS, alpha=False, preview=False):
        enc = (['-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le'] if alpha else
               ['-c:v', 'libx264', '-preset', 'ultrafast' if preview else 'fast', '-crf', '28' if preview else '16', '-pix_fmt', 'yuv420p'])
        self.alpha = alpha
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba' if alpha else 'rgb24',
                                   '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', *enc, str(out)], stdin=subprocess.PIPE)

    def put(self, a):
        self.p.stdin.write(np.ascontiguousarray(a, np.uint8).tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait():
            raise SystemExit('逐帧合成编码失败')


# ---------------------------------------------------------------- 小工具
def clip01(x):
    return min(1.0, max(0.0, x))


def ease(p, kind='inout'):
    p = clip01(p)
    return {'out': 1 - (1 - p) ** 3, 'in': p ** 3}.get(kind, p * p * (3 - 2 * p))


def keyed(kf, t):
    """关键帧 [(秒, 值, 缓动)] 插值；缓动是到达这一帧用的曲线。"""
    if t <= kf[0][0]:
        return kf[0][1]
    for (a, va, _), (b, vb, k) in zip(kf, kf[1:]):
        if t < b:
            return va + (vb - va) * ease((t - a) / max(b - a, 1e-6), k)
    return kf[-1][1]


@lru_cache(maxsize=64)
def _rmask(w, h, r):
    return np.array(rounded_mask(w, h, r), np.float32)[..., None] / 255


def paste(dst, src, x, y, mask=None, opacity=1.0):
    """把 src（h×w×3，或 h×w×4 带透明）贴到 dst 的 (x, y)，超出画面的部分裁掉。mask 是 0~1 的 h×w×1。"""
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4].astype(np.float32) / 255 if s.shape[2] == 4 else np.ones(s.shape[:2] + (1,), np.float32)
    if mask is not None:
        a = a * mask[y0 - y:y1 - y, x0 - x:x1 - x]
    a = a * opacity
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (d * (1 - a) + s[..., :3].astype(np.float32) * a).astype(np.uint8)
    return dst


def resize(a, w, h, fast=True):
    return np.array(Image.fromarray(a).resize((max(1, int(w)), max(1, int(h))), Image.BILINEAR if fast else Image.LANCZOS))


def bg_frames(bg, W, H, FPS, n, work, aroll=None, t0=0.0):
    """圆外和四周的底：black / grid / dots / paper / metal（可写 'grid:rainbow'），blur = 口播本身虚化压暗。"""
    if bg in (None, 'none'):
        for _ in range(n):
            yield None
        return
    if bg == 'blur':
        small = (W // 8, H // 8)
        for fr in read(aroll, t0, n / FPS, small, FPS):
            im = Image.fromarray(fr).filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR)
            yield (np.array(im, np.float32) * 0.55).astype(np.uint8)
        return
    kind, _, var = bg.partition(':')
    spec = backgrounds.make(kind, var or None, W, H, work)
    for i in range(n):
        yield backgrounds.frame_at(spec, i / FPS, H).copy()


def font(role, size, style='premium'):
    return ImageFont.truetype(find_role_font(role, style)[0], int(size))


def text_img(text, size, color, role='title', style='premium', stroke=0, stroke_color='#000000', vertical=False, pad=6,
             spacing=0, italic=0.0, fontfile=None):
    """渲一段字成 RGBA 数组。vertical=True 竖排（一个字一行）；spacing 字距（像素）；italic 右倾斜度（0.2 约 11°）；
    fontfile 直接指定字体文件（签名体这类不在字体角色里的字）。"""
    f = ImageFont.truetype(str(fontfile), int(size)) if fontfile else font(role, size, style)
    if not vertical and (spacing or italic):
        asc, desc = f.getmetrics()
        adv = [f.getlength(c) for c in text]
        o = pad + stroke
        H_ = asc + desc + 2 * o
        sh = int(abs(italic) * H_) + 1
        im = Image.new('RGBA', (int(sum(adv) + spacing * max(0, len(text) - 1)) + 2 * o + sh, H_), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = o
        for c, a in zip(text, adv):
            d.text((x, o), c, font=f, fill=hex_rgba(color), stroke_width=stroke, stroke_fill=hex_rgba(stroke_color))
            x += a + spacing
        if italic:
            im = im.transform(im.size, Image.AFFINE, (1, italic, -italic * H_, 0, 1, 0), Image.BICUBIC)
        return np.array(im)
    chars = list(text) if vertical else [text]
    boxes = [f.getbbox(c) for c in chars]
    lw = max(b[2] - b[0] for b in boxes) + 2 * (pad + stroke)
    lh = [(b[3] - b[1]) if not vertical else int(size * 1.08) for b in boxes]
    W_, H_ = lw, sum(lh) + 2 * (pad + stroke)
    im = Image.new('RGBA', (int(W_), int(H_)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = pad + stroke
    for c, b, h in zip(chars, boxes, lh):
        x = (W_ - (b[2] - b[0])) / 2 - b[0]
        d.text((x, y - (b[1] if not vertical else 0)), c, font=f, fill=hex_rgba(color), stroke_width=stroke, stroke_fill=hex_rgba(stroke_color))
        y += h
    return np.array(im)


def trim(a):
    """裁掉 RGBA 四周的全透明边。"""
    ys, xs = np.nonzero(a[..., 3] > 6)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else a


def tag_img(text, size, fg, bg, role='body', style='premium', pad=(0.5, 0.25), radius=0.2):
    t = text_img(text, size, fg, role, style, pad=0)
    px, py = int(size * pad[0]), int(size * pad[1])
    im = Image.new('RGBA', (t.shape[1] + 2 * px, t.shape[0] + 2 * py), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=int(size * radius), fill=hex_rgba(bg))
    im.alpha_composite(Image.fromarray(t), (px, py))
    return np.array(im)


def rotate_rgba(a, deg):
    return np.array(Image.fromarray(a).rotate(deg, resample=Image.BICUBIC, expand=True))


# ---------------------------------------------------------------- inset：口播缩成圆角卡片并缩放
INSET_ANIMS = {
    'static': '圆角卡片静止（点阵底上的人物卡，方便随时放大缩小）',
    'expand': '卡片撑满讲重点：0.79 宽的卡片在 at 秒 0.25 秒放大到 1.06 铺满',
    'shrink': '缩小压抑讲负面：全屏在 at 秒 0.35 秒缩到 0.67 宽，四周露底，可加 gray 变黑白',
    'badge': '章节编号缩框：0.2 秒缩到 0.85 圆角框，右上弹出编号圆章',
}


def inset(aroll, l, W, H, FPS, st, work, preview=False, out=None):
    """l: {t0, t1, anim, at, to, bg, gray, badge}。返回不透明 mp4。"""
    t0, dur = l['t0'], l['t1'] - l['t0']
    anim = l.get('anim', 'static')
    at = l.get('at', min(1.0, dur * 0.4) if anim == 'expand' else 0.0)
    if anim == 'expand':
        kf = [(0, 0.79, 'out'), (at, 0.79, 'out'), (at + 0.25, l.get('to', 1.06), 'out')]
    elif anim == 'shrink':
        kf = [(0, 1.0, 'inout'), (at, 1.0, 'inout'), (at + 0.35, l.get('to', 0.67), 'inout')]
    elif anim == 'badge':
        kf = [(0, 1.0, 'out'), (at, 1.0, 'out'), (at + 0.2, l.get('to', 0.85), 'out')]
    else:
        kf = [(0, l.get('to', 0.79), 'out')]
    if is_landscape(W, H) and 'to' not in l:
        kf = [(tt, min(s, 0.72) if s < 1 else s, kind) for tt, s, kind in kf]
    gray_at = at if l.get('gray') else None
    n = max(1, round(dur * FPS))
    out = out or f"{work}/inset_{t0:.2f}.mp4"
    w = Writer(out, W, H, FPS, preview=preview)
    badge = None
    if anim == 'badge' or l.get('badge'):
        bt = str(l.get('badge') or '01')
        d = int((H if is_landscape(W, H) else W) * 0.13)
        im = Image.new('RGBA', (d, d), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse([0, 0, d - 1, d - 1], fill=hex_rgba(st['title'].get('hl_color', '#D7262D')))
        tx = text_img(bt, d * 0.46, '#FFFFFF', 'en_display', pad=0)
        im.alpha_composite(Image.fromarray(tx), ((d - tx.shape[1]) // 2, (d - tx.shape[0]) // 2))
        badge = np.array(im)
    ay = 0.38
    for i, (fr, bg) in enumerate(zip(read(aroll, t0, dur, (W, H), FPS), bg_frames(l.get('bg', 'dots'), W, H, FPS, n, work, aroll, t0))):
        t = i / FPS
        s = keyed(kf, t)
        frame = fr
        if gray_at is not None and t >= gray_at:
            g = ease((t - gray_at) / 0.3)
            lum = (fr.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
            frame = (fr * (1 - g) + lum * g).astype(np.uint8)
        if s >= 0.999:
            if s > 1.001:   # 推过全屏：以人脸高度为锚放大再裁
                big = resize(frame, W * s, H * s)
                y0 = int((big.shape[0] - H) * ay)
                x0 = (big.shape[1] - W) // 2
                frame = big[y0:y0 + H, x0:x0 + W]
            w.put(frame)
            continue
        cw, ch = int(W * s) // 2 * 2, int(H * s) // 2 * 2
        cy = H * (0.5 - 0.04 * clip01((1 - s) / 0.21))
        r = int(W * 0.04 * clip01((1 - s) / 0.05))
        if is_landscape(W, H):
            cy = H * (0.5 - 0.07 * clip01((1 - s) / 0.20))
            r = int(40 * unit(W, H) * clip01((1 - s) / 0.05))
        canvas = bg if bg is not None else np.zeros((H, W, 3), np.uint8)
        card = resize(frame, cw, ch)
        paste(canvas, card, (W - cw) / 2, cy - ch / 2, _rmask(cw, ch, max(r, 1)) if r else None)
        if badge is not None and t >= at + 0.12:
            p = ease((t - at - 0.12) / 0.25, 'out')
            sz = max(2, int(badge.shape[0] * (0.6 + 0.4 * p + 0.12 * np.sin(np.pi * p))))
            b = resize(badge, sz, sz)
            bx, by = (W + cw) / 2 - sz * 0.75, cy - ch / 2 - sz * 0.25
            if is_landscape(W, H):
                bx, by = min(W * 0.95 - sz, bx), max(H * 0.05, by)
            paste(canvas, b, bx, by, opacity=p)
        w.put(canvas)
    w.close()
    return out


# ---------------------------------------------------------------- circle：圆形蒙版收缩
CIRCLE_ANIMS = {
    'to_corner': '先缩后移进角落：圆从全屏缩到头像大小，停一下再滑到小窗位置，接着就是 pip 小窗',
    'quick': '快收圆：0.2 秒猛收成居中的圆，圆外是口播虚化',
    'center_ring': '居中大圆加环：0.5 秒收成 0.68 宽的居中大圆，白色实线环（ring 可换 pink_dash 粉色虚线）',
}
RINGS = {'gold': ('#F0D040', 3, False), 'white': ('#FFFFFF', 10, False), 'pink_dash': ('#F49AC1', 6, True), 'cream': ('#F3EED8', 3, False),
         'none': None}


def circle(aroll, l, W, H, FPS, st, work, preview=False, out=None):
    """l: {t0, t1, anim, bg, ring, crop}。bg 写 none 时输出透明底 .mov（圆外露出下面的素材）。"""
    t0, dur = l['t0'], l['t1'] - l['t0']
    anim = l.get('anim', 'to_corner')
    cs, cx, cy = face_crop(W, H, l.get('crop'))
    fc = np.array([cx + cs / 2, cy + cs / 2])   # 人脸中心在原画面里的位置
    pip = {**st['pip'], **(l.get('pip') or {})}
    if anim == 'to_corner':
        d, sh, hold, mv = pip['d'] * W, 0.6, l.get('hold', 0.7), 0.45
        tgt0, tgt1 = fc, np.array([pip['x'] * W, pip['y'] * H])
        ring = l.get('ring', 'gold')
    elif anim == 'quick':
        d, sh, hold, mv = 0.45 * 1080 * unit(W, H), 0.2, 0, 0
        tgt0 = tgt1 = np.array([W / 2, H * 0.42])
        ring = l.get('ring', 'none')
    else:
        d, sh, hold, mv = 0.68 * 1080 * unit(W, H), 0.5, 0, 0
        tgt0 = tgt1 = np.array([W / 2, H * 0.42])
        ring = l.get('ring', 'white')
    bg = l.get('bg', 'blur' if anim != 'center_ring' else 'grid:rainbow')
    alpha = bg in (None, 'none')
    n = max(1, round(dur * FPS))
    out = out or f"{work}/circle_{t0:.2f}.{'mov' if alpha else 'mp4'}"
    w = Writer(out, W, H, FPS, alpha=alpha, preview=preview)
    R0 = float(np.hypot(W, H))
    rcol, rw, dash = (RINGS.get(ring) or (None, 0, False))
    rw = rw * unit(W, H)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for i, (fr, bgf) in enumerate(zip(read(aroll, t0, dur, (W, H), FPS), bg_frames(bg, W, H, FPS, n, work, aroll, t0))):
        t = i / FPS
        p = ease(t / sh, 'out')
        R = R0 + (d / 2 - R0) * p
        k = min(1.0, 2 * R / cs)   # 先只收圆，圆比人脸那块小了才连画面一起缩，圆里永远是满的
        q = ease((t - sh - hold) / mv) if mv else 0
        ctr = fc + (tgt0 - fc) * p + (tgt1 - tgt0) * q
        canvas = np.zeros((H, W, 4), np.uint8)
        if not alpha:
            canvas[..., :3] = bgf
            canvas[..., 3] = 255
        tl = ctr - fc * k
        x0, y0 = max(0, int(ctr[0] - R - rw - 2)), max(0, int(ctr[1] - R - rw - 2))
        x1, y1 = min(W, int(ctr[0] + R + rw + 2)), min(H, int(ctr[1] + R + rw + 2))
        if x1 > x0 and y1 > y0:
            src = np.array(Image.fromarray(fr).transform((x1 - x0, y1 - y0), Image.AFFINE,
                                                         (1 / k, 0, (x0 - tl[0]) / k, 0, 1 / k, (y0 - tl[1]) / k), Image.BILINEAR))
            dist = np.hypot(xx[y0:y1, x0:x1] - ctr[0], yy[y0:y1, x0:x1] - ctr[1])
            m = np.clip(R + 0.5 - dist, 0, 1)[..., None]
            reg = canvas[y0:y1, x0:x1].astype(np.float32)
            rgb = reg[..., :3] * (1 - m) + src * m
            a = np.maximum(reg[..., 3:4] / 255, m)
            if rcol and R < R0 * 0.6:
                rm = np.clip(np.minimum(dist - R + 0.5, R + rw + 0.5 - dist), 0, 1)
                if dash:
                    ang = np.arctan2(yy[y0:y1, x0:x1] - ctr[1], xx[y0:y1, x0:x1] - ctr[0]) * R
                    rm = rm * ((ang / (rw * 3.2)) % 2 < 1.1)
                rm = rm[..., None]
                rgb = rgb * (1 - rm) + np.array(hex_rgba(rcol)[:3], np.float32) * rm
                a = np.maximum(a, rm)
            canvas[y0:y1, x0:x1, :3] = rgb.astype(np.uint8)
            canvas[y0:y1, x0:x1, 3:4] = (a * 255).astype(np.uint8)
        w.put(canvas if alpha else canvas[..., :3])
    w.close()
    return out


# ---------------------------------------------------------------- split：分屏对比
SPLIT_VARIANTS = {
    'torn': '撕纸竖条：两条竖长素材带撕纸白边，左条从左滑入、右条从右滑入，各带竖排红字',
    'diagonal': '斜线上下分割：上下两张素材用 15° 斜线分开，蓝色倾斜标签挂黄条',
    'focus': '圆角双窗切焦点：两个圆角窗并排，没在讲的一边压暗，按 focus_at 切过去',
    'triptych': '三屏并排：三个竖条等宽同步播放，下方各一个标签，中间那块白底突出',
}


def _torn_mask(w, h, seed, edge=7):
    rng = np.random.default_rng(seed)
    step = 9
    left = [(rng.uniform(0, edge), y) for y in range(0, h + step, step)]
    right = [(w - rng.uniform(0, edge), y) for y in range(h + step, -step, -step)]
    top = [(x, rng.uniform(0, edge * 0.6)) for x in range(0, w, 14)]
    bot = [(x, h - rng.uniform(0, edge * 0.6)) for x in range(w, 0, -14)]
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).polygon(top + right + bot + left, fill=255)
    return np.array(im, np.float32)[..., None] / 255


def split(l, W, H, FPS, st, work, aroll, preview=False, out=None):
    """l: {t0, t1, variant, panels: [{src, label, src_in}], focus_at, bg}。src 写 aroll 用口播画面。"""
    t0, dur = l['t0'], l['t1'] - l['t0']
    v = l.get('variant', 'torn')
    panels = l['panels']
    style = 'premium' if st.get('tone') != 'variety' else 'variety'
    n = max(1, round(dur * FPS))
    S = unit(W, H)

    def src_of(p):
        return (aroll, t0) if p.get('src', 'aroll') == 'aroll' else (to_png(p['src'], work) if is_image(p['src']) else p['src'], p.get('src_in', 0))

    if v == 'triptych':
        pw, ph, gap = int(0.30 * W), int(0.52 * H), int(0.025 * W)
        boxes = [((W - 3 * pw - 2 * gap) / 2 + j * (pw + gap), 0.42 * H - ph / 2, pw, ph) for j in range(3)]
    elif v == 'focus':
        pw, ph = int(0.46 * W), int(0.46 * W * 1.5)
        boxes = [(0.035 * W, 0.42 * H - ph / 2, pw, ph), (W - 0.035 * W - pw, 0.42 * H - ph / 2, pw, ph)]
    elif v == 'diagonal':
        ph = int(H * 0.62)
        boxes = [(0, 0, W, ph), (0, H - ph, W, ph)]
    else:
        pw, ph = int(0.44 * W), int(0.70 * H)
        boxes = [(0.26 * W - pw / 2, 0.44 * H - ph / 2, pw, ph), (0.74 * W - pw / 2, 0.44 * H - ph / 2, pw, ph)]
    boxes = boxes[:len(panels)]
    if is_landscape(W, H):
        # 横屏双窗并排，下面留出标签和字幕，不再拿宽度算窗口高度。
        count = min(len(panels), 3 if v == 'triptych' else 2)
        gap = W * 0.025
        pw, ph = int((W * 0.90 - gap * (count - 1)) / count), int(H * 0.56)
        boxes = [(W * 0.05 + j * (pw + gap), H * 0.12, pw, ph) for j in range(count)]
        if v == 'torn':
            pw = int((W * 0.90 - 16 * S - gap * (count - 1)) / count)
            boxes = [(W * 0.05 + 8 * S + j * (pw + gap), H * 0.12, pw, ph) for j in range(count)]
        if v == 'diagonal':
            boxes = [(W * 0.05, H * 0.12, int(W * 0.50), ph), (W * 0.45, H * 0.12, int(W * 0.50), ph)][:count]
    gens = []
    for p, (x, y, bw, bh) in zip(panels, boxes):
        s, si = src_of(p)
        gens.append(read(s, si, dur, (int(bw), int(bh)), FPS))
    hl = st['title'].get('hl_color', '#D7262D')
    labels = []
    for j, p in enumerate(panels[:len(boxes)]):
        lb = p.get('label')
        if not lb:
            labels.append(None)
            continue
        if v == 'torn':
            labels.append(text_img(lb, 62 * S, '#D0102A', 'serif', style, stroke=int(5 * S), stroke_color='#FFFFFF', vertical=not is_landscape(W, H)))
        elif v == 'diagonal':
            tg = tag_img(lb, 54 * S, '#FFFFFF', '#2563D9', 'title', style)
            bar = np.zeros((int(10 * S), int(tg.shape[1] * 0.7), 4), np.uint8)
            bar[...] = hex_rgba('#F5C400')
            comb = np.zeros((tg.shape[0] + bar.shape[0] + int(6 * S), tg.shape[1], 4), np.uint8)
            comb[:tg.shape[0]] = tg
            comb[-bar.shape[0]:, :bar.shape[1]] = bar
            labels.append(rotate_rgba(comb, 8))
        elif v == 'triptych':
            mid = j == 1
            labels.append(tag_img(lb, 40 * S, '#111111' if mid else '#FFFFFF', '#FFFFFF' if mid else '#E2622A', 'title', style, radius=0.1))
        else:
            labels.append(text_img(lb, 48 * S, '#FFFFFF', 'title', style))
    if is_landscape(W, H):
        for j, (lb, box) in enumerate(zip(labels, boxes)):
            if lb is not None:
                k = min(1.0, box[2] * 0.84 / lb.shape[1])
                labels[j] = resize(lb, lb.shape[1] * k, lb.shape[0] * k)
    fat = l.get('focus_at') or [0, dur / 2]
    tmasks = [_torn_mask(int(b[2]), int(b[3]), 7 + j) for j, b in enumerate(boxes)] if v == 'torn' else None
    if v == 'torn':
        border = [_torn_mask(int(b[2]) + int(12 * S), int(b[3]) + int(12 * S), 17 + j, 10) for j, b in enumerate(boxes)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    tilt = np.tan(np.radians(15))
    side = (yy - (H * 0.5 - (xx - W / 2) * tilt))   # 斜线：>0 在下半
    dmask_top = np.clip(-side / 2 + 0.5, 0, 1)[..., None]
    line = np.clip(5 * S - np.abs(side) * np.cos(np.radians(15)), 0, 1)[..., None]
    if is_landscape(W, H):
        side = xx - (W * 0.5 + (yy - H * 0.40) * tilt)
        dmask_top = np.clip(-side / 2 + 0.5, 0, 1)[..., None]
        line = (np.clip(5 * S - np.abs(side), 0, 1) * ((yy >= H * 0.12) & (yy < H * 0.68)))[..., None]
    out = out or f"{work}/split_{t0:.2f}.mp4"
    w = Writer(out, W, H, FPS, preview=preview)
    enter = [l.get('at', [0, 0.18, 0.36])[j] if isinstance(l.get('at'), list) else j * 0.18 for j in range(len(boxes))]
    for i, (frames, bg) in enumerate(zip(zip(*gens), bg_frames(l.get('bg', 'black'), W, H, FPS, n, work, aroll, t0))):
        t = i / FPS
        canvas = bg
        if v == 'diagonal':
            top, bot = frames[0], frames[1] if len(frames) > 1 else frames[0]
            full_t = np.zeros((H, W, 3), np.uint8)
            full_b = np.zeros((H, W, 3), np.uint8)
            pt, pb = ease((t - enter[0]) / 0.35, 'out'), ease((t - enter[min(1, len(enter) - 1)]) / 0.35, 'out')
            paste(full_t, top, -W * (1 - pt), 0)
            paste(full_b, bot, W * (1 - pb), H - bot.shape[0])
            if is_landscape(W, H):
                full_t, full_b = bg.copy(), bg.copy()
                paste(full_t, top, boxes[0][0] - W * (1 - pt), boxes[0][1])
                paste(full_b, bot, boxes[-1][0] + W * (1 - pb), boxes[-1][1])
            comp = full_t * dmask_top + full_b * (1 - dmask_top)
            canvas = (comp * (1 - line) + 255 * line).astype(np.uint8)
            for j, lb in enumerate(labels):
                if lb is not None:
                    py = 0.07 * H if j == 0 else 0.60 * H
                    px = 0.06 * W
                    if is_landscape(W, H):
                        px, py = boxes[j][0] + W * 0.025, H * 0.15
                    paste(canvas, lb, px, py, opacity=ease((t - enter[min(j, len(enter) - 1)] - 0.2) / 0.25))
            w.put(canvas)
            continue
        for j, (fr, (x, y, bw, bh)) in enumerate(zip(frames, boxes)):
            p = ease((t - enter[j]) / 0.35, 'out')
            if v == 'torn':
                dx = -(x + bw + 20) * (1 - p) if j == 0 else (W - x + 20) * (1 - p)
                b = border[j]
                white = np.full(b.shape[:2] + (3,), 245, np.uint8)
                paste(canvas, white, x + dx - 6 * S, y - 6 * S, b)
                paste(canvas, fr, x + dx, y, tmasks[j])
                if labels[j] is not None:
                    lb = labels[j]
                    paste(canvas, lb, (x + dx + 0.03 * W) if j == 0 else (x + dx + bw - 0.03 * W - lb.shape[1]), y + 0.03 * H)
            elif v == 'focus':
                fj = sum(1 for a in fat if t >= a) - 1
                cur = fj % 2 if fj >= 0 else 0
                tw = min((t - a) for a in fat if t >= a) if any(t >= a for a in fat) else 1
                on = ease(tw / 0.3) if cur == j else 1 - ease(tw / 0.3)
                if tw >= 0.3:
                    on = 1.0 if cur == j else 0.0
                op = 0.41 + 0.59 * on
                sc = 0.94 + 0.06 * on
                fr2 = resize(fr, bw * sc, bh * sc)
                ox, oy = x + bw * (1 - sc) / 2, y + bh * (1 - sc) / 2
                paste(canvas, fr2, ox, oy + (1 - p) * 0.06 * H, _rmask(fr2.shape[1], fr2.shape[0], int(0.04 * W)), opacity=op * p)
                if labels[j] is not None:
                    lb = labels[j]
                    paste(canvas, lb, x + (bw - lb.shape[1]) / 2, y + bh + 0.02 * H, opacity=(0.45 + 0.55 * on) * p)
            else:   # triptych
                paste(canvas, fr, x, y + (1 - p) * 0.05 * H, _rmask(int(bw), int(bh), int(0.015 * W)), opacity=p)
                if labels[j] is not None:
                    lb = labels[j]
                    paste(canvas, lb, x + (bw - lb.shape[1]) / 2, y + bh + 0.025 * H, opacity=ease((t - enter[j] - 0.15) / 0.25))
        w.put(canvas)
    w.close()
    return out


# ---------------------------------------------------------------- tilt：透视斜置卡
TILT_VARIANTS = {
    'left': '左倾：右边远、左边近，像斜放在桌上的纸',
    'right': '右倾：左边远、右边近',
    'pair': '镜像三联：左右两张向内斜摆、压暗退后，中间一张正对观众（srcs 给三张）',
}


def _quad_coeffs(dst, src):
    """PIL PERSPECTIVE 用的 8 个系数：输出坐标 dst 四点 → 源图坐标 src 四点。"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        B += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def warp_card(src_img, w, quad_fn, radius, shade=1.0, max_h=None):
    """把图片做成宽 w 的圆角卡片，再按 quad_fn(w, h) 给的四个角（左上、右上、右下、左下）扭成透视四边形，带投影。"""
    im = src_img.convert('RGB')
    h = round(im.height * w / im.width)
    if max_h and h > max_h:
        h = int(max_h)
        w = round(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    if shade != 1.0:
        im = Image.fromarray((np.array(im, np.float32) * shade).astype(np.uint8))
    card = im.convert('RGBA')
    card.putalpha(rounded_mask(w, h, radius))
    q = quad_fn(w, h)
    pad = int(w * 0.08)
    ow, oh = int(max(x for x, _ in q)) + 2 * pad, int(max(y for _, y in q)) + 2 * pad
    dst = [(x + pad, y + pad) for x, y in q]
    warped = card.transform((ow, oh), Image.PERSPECTIVE, _quad_coeffs(dst, [(0, 0), (w, 0), (w, h), (0, h)]), Image.BICUBIC)
    sh = Image.new('RGBA', (ow, oh), (0, 0, 0, 0))
    sh.putalpha(warped.getchannel('A').point(lambda a: a * 0.55))
    sh = sh.transform((ow, oh), Image.AFFINE, (1, 0, -pad * 0.15, 0, 1, -pad * 0.35)).filter(ImageFilter.GaussianBlur(pad / 2.5))
    sh.alpha_composite(warped)
    return sh.crop(sh.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox())   # 按看得见的部分居中，不按留白


def tilt(srcs, variant, W, H, st, work, name, w_ratio=0.8, max_h=0.55):
    """输出透明底 PNG（卡片在画面里的样子），返回 (路径, 宽, 高)。"""
    radius = st['card'].get('radius', 26)
    k = 0.09   # 远的那一边缩短 9%

    def left(w, h):
        return [(0, 0), (w * 0.94, h * k), (w * 0.94, h * (1 - k)), (0, h)]

    def right(w, h):
        return [(w * 0.06, h * k), (w, 0), (w, h), (w * 0.06, h * (1 - k))]

    ims = [Image.open(to_png(s, work)) for s in srcs]
    if variant == 'pair':
        side_w = int(W * 0.40)
        L = warp_card(ims[0], side_w, left, radius, 0.6, H * max_h * 0.8)
        R = warp_card(ims[-1], side_w, right, radius, 0.6, H * max_h * 0.8)
        mid = ims[1] if len(ims) > 2 else None
        canvas = Image.new('RGBA', (W, int(H * max_h * 1.25)), (0, 0, 0, 0))
        cy = canvas.height // 2
        canvas.alpha_composite(L, (int(W * 0.21 - L.width / 2), cy - L.height // 2))
        canvas.alpha_composite(R, (int(W * 0.79 - R.width / 2), cy - R.height // 2))
        if mid is not None:
            M = warp_card(mid, int(side_w * 1.2), lambda w, h: [(0, 0), (w, 0), (w, h), (0, h)], radius, 1.0, H * max_h)
            canvas.alpha_composite(M, (int(W / 2 - M.width / 2), cy - M.height // 2))
        out = f'{work}/{name}_tilt.png'
        canvas.save(out)
        return out, canvas.width, canvas.height
    card = warp_card(ims[0], int(W * w_ratio), left if variant == 'left' else right, radius, 1.0, H * max_h)
    out = f'{work}/{name}_tilt.png'
    card.save(out)
    return out, card.width, card.height


# ---------------------------------------------------------------- live_card：卡片里放大看细节、划重点
MARK_LOOKS = {'yellow': '黄色荧光笔：亮黄色块从左往右扫过，正片叠底，黑字透出来', 'inverse': '黑色反白：被划到的字变成白字黑底，比黄色更重更正式'}


def apply_marks(im, boxes, look='yellow', prog=None, color='#F2E64B'):
    """截图划重点（screenshot_highlight）：boxes 是 [x, y, w, h]（相对截图），prog 是每一道划到的进度 0~1。
    yellow 正片叠底（黑字不被吃掉），inverse 反相（白底黑字变黑底白字，彩色截图会变怪色，只给黑白文字用）。"""
    a = np.array(im.convert('RGB'), np.float32)
    H, W = a.shape[:2]
    tint = np.array(hex_rgba(color)[:3], np.float32) / 255
    for (x, y, w, h), p in zip(boxes, prog or [1.0] * len(boxes)):
        if p <= 0:
            continue
        x0, y0, x1, y1 = int(x * W), int(y * H), int((x + w * p) * W), int((y + h) * H)
        reg = a[y0:y1, x0:x1]
        a[y0:y1, x0:x1] = 255 - reg if look == 'inverse' else reg * tint
    return Image.fromarray(a.astype(np.uint8))


def live_card(src, b, W, H, FPS, st, work, name, preview=False):
    """card / contain 素材逐帧变化的部分：focus 从 t 秒起 dur 秒平滑放大到 scale 倍、对准 (cx, cy)，写了 hold 就停 hold 秒再缩回全景；
    marks 截图划重点，一道道从左往右划出（at 每道开始的秒数，wipe 划一道用的秒数）。返回 (.mov 路径, 宽, 高)。"""
    from kvlib import mark_times
    fo = b.get('focus') or {}
    mk = b.get('marks') if isinstance(b.get('marks'), dict) else None
    fit = b.get('fit', 'card')
    dur = b['t1'] - b['t0']
    img = is_image(src)
    if img:
        base = Image.open(src).convert('RGB')
        sw, sh_ = base.size
    else:
        from kvlib import probe
        pr = probe(src)
        sw, sh_ = pr['w'], pr['h']
    bw = int(W * b.get('w', 0.86)) // 2 * 2
    if is_landscape(W, H):
        bw = min(bw, int(W * 0.62) // 2 * 2)
    bh = round(sh_ * bw / sw) // 2 * 2
    mh = int(H * b.get('max_h', 0.62))
    if is_landscape(W, H):
        mh = min(mh, int(H * 0.72))
    if (fit == 'card' or is_landscape(W, H)) and bh > mh:
        bh = mh // 2 * 2
        bw = round(sw * bh / sh_) // 2 * 2
    card = st['card'] if fit == 'card' else {'radius': 0, 'shadow': 0}
    r, pad = card.get('radius', 24), card.get('shadow', 0)
    cw, ch = bw + 2 * pad, bh + 2 * pad
    shadow = np.zeros((ch, cw, 4), np.uint8)
    if pad:
        shm = Image.new('L', (cw, ch), 0)
        shm.paste(rounded_mask(bw, bh, r).point(lambda a: a * card.get('shadow_alpha', 100) / 255), (pad, pad + pad // 3))
        shadow[..., 3] = np.array(shm.filter(ImageFilter.GaussianBlur(pad / 2)))
    mask = _rmask(bw, bh, max(r, 1)) if r else None
    ft, fd, fs = fo.get('t', 0.4), fo.get('dur', 0.6), fo.get('scale', 1.0 if not fo else 2.4)
    cx, cy = fo.get('cx', 0.5), fo.get('cy', 0.5)
    hold = fo.get('hold')
    m_at = mark_times(b) if mk else []
    wipe = mk.get('wipe', 0.4) if mk else 0
    frames = read(src, b.get('src_in', 0), dur, (sw, sh_), FPS) if not img else None
    out = f'{work}/{name}_live.mov'
    w = Writer(out, cw, ch, FPS, alpha=True)
    n = max(1, round(dur * FPS))
    for i in range(n):
        t = i / FPS
        z = 1 + (fs - 1) * (ease((t - ft) / fd) - (ease((t - ft - fd - hold) / fd) if hold is not None else 0))
        fr = Image.fromarray(next(frames)) if frames else base
        if mk:
            fr = apply_marks(fr, mk['boxes'], mk.get('look', 'yellow'), [ease((t - a) / wipe, 'out') for a in m_at], mk.get('color', '#F2E64B'))
        vw, vh = sw / z, sh_ / z
        x0 = min(max(0, sw * cx - vw / 2), sw - vw)
        y0 = min(max(0, sh_ * cy - vh / 2), sh_ - vh)
        content = np.array(fr.resize((bw, bh), Image.BILINEAR if preview else Image.LANCZOS, box=(x0, y0, x0 + vw, y0 + vh)))
        rgba = shadow.copy()
        a = (mask if mask is not None else np.ones((bh, bw, 1), np.float32))
        reg = rgba[pad:pad + bh, pad:pad + bw].astype(np.float32)
        ra = reg[..., 3:4] / 255
        na = a + ra * (1 - a)
        rgb = (content * a + reg[..., :3] * ra * (1 - a)) / np.maximum(na, 1e-6)
        rgba[pad:pad + bh, pad:pad + bw, :3] = rgb.astype(np.uint8)
        rgba[pad:pad + bh, pad:pad + bw, 3:4] = (na * 255).astype(np.uint8)
        w.put(rgba)
    w.close()
    return out, cw, ch


# ---------------------------------------------------------------- card_frame：素材卡的装饰边框
CARD_FRAMES = {'glow': '发光描边：卡片边缘一圈柔和淡黄光', 'viewfinder': '取景器：四角白色直角标、右上 REC、左下 ISO 和快门、底部曝光刻度，像在回看素材'}


def frame_layers(w, h, radius, look, W, H=None):
    """素材卡（clip_card_frame）的边框图层：返回 (垫在卡片下面的 RGBA, 盖在卡片上面的 RGBA, 外扩像素)。两层都比卡片大一圈外扩。"""
    S = unit(W, H if H is not None else W)
    g = int(32 * S)
    cw, ch = w + 2 * g, h + 2 * g
    under = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    top = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    if look == 'glow':
        col = hex_rgba('#FFE68A')[:3]
        m = Image.new('L', (cw, ch), 0)
        e = int(8 * S)
        ImageDraw.Draw(m).rounded_rectangle([g - e, g - e, g + w + e, g + h + e], radius=radius + e, fill=int(255 * 0.6))
        under = Image.new('RGBA', (cw, ch), col + (0,))
        under.putalpha(m.filter(ImageFilter.GaussianBlur(12 * S)))
        ImageDraw.Draw(top).rounded_rectangle([g, g, g + w, g + h], radius=radius, outline=col + (235,), width=max(2, int(3 * S)))
    elif look == 'viewfinder':
        d = ImageDraw.Draw(top)
        lw, cl, ins = max(2, int(3 * S)), int(min(w, h) * 0.12), int(min(w, h) * 0.06)
        x0, y0, x1, y1 = g + ins, g + ins, g + w - ins, g + h - ins
        for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            d.line([(px, py), (px + sx * cl, py)], fill=(255, 255, 255, 240), width=lw)
            d.line([(px, py), (px, py + sy * cl)], fill=(255, 255, 255, 240), width=lw)
        f = font('en', 30 * S)
        r_ = int(11 * S)
        tx = x1 - cl - int(40 * S)
        d.ellipse([tx - 2 * r_ - int(10 * S), y0 + int(16 * S), tx - int(10 * S), y0 + int(16 * S) + 2 * r_], fill=(230, 40, 40, 255))
        d.text((tx, y0 + int(16 * S) + r_), 'REC', font=f, fill=(255, 255, 255, 240), anchor='lm')
        d.text((x0 + cl + int(14 * S), y1 - int(18 * S)), 'ISO 100   1/250   F2.8', font=font('en', 24 * S), fill=(255, 255, 255, 220), anchor='ls')
        mx, my = g + w / 2, y1 - int(22 * S)
        for k in range(-6, 7):
            hh = int((16 if k == 0 else 9) * S)
            d.line([(mx + k * 18 * S, my - hh), (mx + k * 18 * S, my)], fill=(255, 255, 255, 230 if k == 0 else 170), width=max(1, int(2 * S)))
    return np.array(under), np.array(top), g


def frame_card_png(card_png, out, look, pad, radius, W, H=None):
    """给已经做好的图片卡片（make_card 的输出，四周留了 pad 像素投影）加边框，返回 (路径, 宽, 高)。"""
    im = Image.open(card_png).convert('RGBA')
    w, h = im.width - 2 * pad, im.height - 2 * pad
    under, top, g = frame_layers(w, h, radius, look, W, H)
    canvas = Image.new('RGBA', (w + 2 * max(g, pad), h + 2 * max(g, pad)), (0, 0, 0, 0))
    o = max(g, pad)
    canvas.alpha_composite(Image.fromarray(under), (o - g, o - g))
    canvas.alpha_composite(im, (o - pad, o - pad))
    canvas.alpha_composite(Image.fromarray(top), (o - g, o - g))
    canvas.save(out)
    return out, canvas.width, canvas.height


# ---------------------------------------------------------------- pages：报告纸页飞入堆叠
PAGES_VARIANTS = {
    'cascade': '彩色纸页错落：白、粉、黄、蓝四张纸页从右上依次飞入，各自略倾斜上下错落',
    'scatter': '四面八方散落：十张纸页从四面八方旋转飞入，带拖影，散落堆成一桌文件',
    'stack': '一沓拖影落定：一页纸从右下斜飞进来，后面拖着三张错开 1 帧的副本，落定后叠成一摞再轻微放大',
    'curl': '卷角单页滑入：报告右下角卷起白色卷角，整页从上方滑下来定位',
}
PAPER = ['#FFFFFF', '#F6D5EA', '#F7E2B5', '#CDE9F7']


def page_sprite(src, pw, paper='#FFFFFF', curl=False, max_h=None, W=1080, H=None):
    """一张纸页：截图放在纸上（四周留白边），带投影，可加右下卷角。返回 RGBA 数组（四周留了投影的边）。"""
    S = unit(W, H if H is not None else W)
    im = Image.open(src).convert('RGB')
    m = int(pw * 0.05)
    iw = pw - 2 * m
    ih = round(im.height * iw / im.width)
    if max_h and ih + 2 * m > max_h:
        ih = int(max_h - 2 * m)
        iw = round(im.width * ih / im.height)
    page = Image.new('RGBA', (iw + 2 * m, ih + 2 * m), hex_rgba(paper))
    page.paste(im.resize((iw, ih), Image.LANCZOS), (m, m))
    pw_, ph = page.size
    if curl:
        c = int(pw_ * 0.16)
        cut = Image.new('L', page.size, 255)
        ImageDraw.Draw(cut).polygon([(pw_ - c, ph), (pw_, ph - c), (pw_, ph)], fill=0)
        page.putalpha(cut)
        flap = Image.new('RGBA', page.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(flap)
        fd.polygon([(pw_ - c + 3 * S, ph - 2 * S), (pw_ - 2 * S, ph - c + 3 * S), (pw_ - c * 1.08, ph - c * 1.08)], fill=(0, 0, 0, 90))
        flap = flap.filter(ImageFilter.GaussianBlur(4 * S))
        fd = ImageDraw.Draw(flap)   # 卷起来的那一角：纸背颜色的三角，折痕一道细灰线
        fd.polygon([(pw_ - c, ph), (pw_, ph - c), (pw_ - c, ph - c)], fill=(236, 236, 232, 255))
        fd.line([(pw_ - c, ph), (pw_, ph - c)], fill=(200, 200, 196, 255), width=max(1, int(2 * S)))
        page.alpha_composite(flap)
    sh = int(pw_ * 0.05)
    out = Image.new('RGBA', (pw_ + 2 * sh, ph + 2 * sh), (0, 0, 0, 0))
    shadow = Image.new('RGBA', out.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 120), (sh + sh // 3, sh + sh // 2, sh + sh // 3 + pw_, sh + sh // 2 + ph), page.getchannel('A'))
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(sh / 2.2)))
    out.alpha_composite(page, (sh, sh))
    return np.array(out)


def over(dst, src, x, y, opacity=1.0):
    """RGBA 叠 RGBA（dst 原地改），超出画面的部分裁掉。"""
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or opacity <= 0:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    d = dst[y0:y1, x0:x1].astype(np.float32)
    sa = s[..., 3:4] / 255 * opacity
    da = d[..., 3:4] / 255
    oa = sa + da * (1 - sa)
    dst[y0:y1, x0:x1, :3] = ((s[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)).astype(np.uint8)
    dst[y0:y1, x0:x1, 3:4] = (oa * 255).astype(np.uint8)
    return dst


def pages(b, W, H, FPS, st, work, name):
    """broll 的 fit 为 pages：srcs 给一张或几张报告截图（不够就轮着用）。输出铺满画面的透明 .mov，返回 (路径, W, H)。"""
    v = b.get('variant', 'cascade')
    if v not in PAGES_VARIANTS:
        raise SystemExit(f"pages 的 variant「{v}」不存在，可选：{'、'.join(PAGES_VARIANTS)}")
    srcs = [to_png(x, work) for x in (b.get('srcs') or [b['src']])]
    dur = b['t1'] - b['t0']
    rng = np.random.default_rng(b.get('seed', 7))
    S = unit(W, H)
    plan = []   # 每页：(图, 起点 x, y, 角度, 终点 x, y, 角度, 开始秒, 飞行秒, 不透明度)
    if v == 'cascade':
        for i in range(4):
            sp = page_sprite(srcs[i % len(srcs)], int(W * 0.40), PAPER[i], max_h=H * 0.34, W=W, H=H)
            plan.append((sp, W * 1.3, -H * 0.25, 28, W * (0.36 + 0.05 * (i % 2)), H * (0.27 + 0.12 * i), [-6, 4, -3, 7][i], 0.1 + i * 0.14, 0.55, 1.0))
    elif v == 'scatter':
        n = 10
        for i in range(n):
            th = 2 * np.pi * i / n + rng.uniform(-0.2, 0.2)
            ea = rng.uniform(-14, 14)
            sp = page_sprite(srcs[i % len(srcs)], int(W * 0.34), max_h=H * 0.30, W=W, H=H)
            plan.append((sp, W / 2 + np.cos(th) * W * 1.1, H * 0.46 + np.sin(th) * H * 0.7, ea + rng.choice([-1, 1]) * rng.uniform(30, 40),
                         W * (0.5 + rng.uniform(-0.2, 0.2)), H * (0.46 + rng.uniform(-0.14, 0.14)), ea, 0.05 + i * 0.07, 0.45, 1.0))
    elif v == 'stack':
        sp = page_sprite(srcs[0], int(W * 0.62), max_h=H * 0.55, W=W, H=H)
        for k in (3, 2, 1, 0):   # 先画落后的副本，最上面是主页
            plan.append((sp, W * 1.25, H * 1.15, 22, W * 0.5 + k * 7 * S, H * 0.45 + k * 6 * S, -3 + k * 1.2, 0.1 + k / FPS, 0.5, 1.0 if k == 0 else 0.9))
    else:
        sp = page_sprite(srcs[0], int(W * 0.62), curl=True, max_h=H * 0.55, W=W, H=H)
        plan.append((sp, W * 0.5, -H * 0.35, 0, W * 0.5, H * 0.45, -2, 0.1, 0.5, 1.0))
    if is_landscape(W, H):
        # 透明纸页叠在口播上时让开人脸，散落版分到两侧，其余在指定侧落定。
        zones = safe_zones(W, H)['text']
        arranged = []
        for j, (sp, sx, sy, sa, ex, ey, ea, t0, fl, op) in enumerate(plan):
            z = zones[j % 2 if v == 'scatter' else (0 if b.get('side') == 'left' else 1)]
            k = min(1.0, W * (z[2] - z[0]) * 0.72 / sp.shape[1], H * (0.23 if v in ('scatter', 'cascade') else 0.48) / sp.shape[0])
            sp = resize(sp, sp.shape[1] * k, sp.shape[0] * k)
            ex = W * (z[0] + z[2]) / 2
            ey = H * (0.25 + 0.115 * (j % 4)) if v in ('scatter', 'cascade') else H * 0.44 + j * 5 * S
            sx, sy = W * (-0.3 if z[0] < 0.5 else 1.3), ey
            arranged.append((sp, sx, sy, sa, ex, ey, ea, t0, fl, op))
        plan = arranged
    settle = max(p[7] + p[8] for p in plan)
    rot_cache = {}

    def rot(sp, a):
        key = (id(sp), round(a, 1))
        if key not in rot_cache:
            rot_cache[key] = rotate_rgba(sp, a)
        return rot_cache[key]

    out = f'{work}/{name}_pages.mov'
    w = Writer(out, W, H, FPS, alpha=True)
    n = max(1, round(dur * FPS))
    for i in range(n):
        t = i / FPS
        canvas = np.zeros((H, W, 4), np.uint8)
        for sp, sx, sy, sa, ex, ey, ea, t0, fl, op in plan:
            if t < t0:
                continue
            for lag, gop in ((2, 0.18), (1, 0.32), (0, 1.0)):   # 飞行中带两道拖影，近似运动模糊
                tt = t - lag / FPS
                if lag and (tt - t0 >= fl or tt < t0):
                    continue
                p = ease((tt - t0) / fl, 'out')
                x, y, a = sx + (ex - sx) * p, sy + (ey - sy) * p, sa + (ea - sa) * p
                r = rot(sp, a)
                over(canvas, r, x - r.shape[1] / 2, y - r.shape[0] / 2, op * gop)
        if t > settle:   # 落定后整摞轻轻放大
            z = 1 + 0.04 * ease((t - settle) / max(0.5, dur - settle))
            big = np.array(Image.fromarray(canvas, 'RGBA').resize((int(W * z), int(H * z)), Image.BILINEAR))
            ox, oy = (big.shape[1] - W) // 2, int((big.shape[0] - H) * 0.45)
            canvas = big[oy:oy + H, ox:ox + W]
        w.put(canvas)
    w.close()
    return out, W, H


# ---------------------------------------------------------------- opening：开场第一秒入场冲击
def opening(aroll, plan, W, H, FPS, work, preview=False):
    """按 kvlib.opening_plan 的结果渲开场头几帧。flash / zoom / iris 重画口播开头（不透明 mp4），
    boom 的速度线、spotlight 的椭圆暗角是叠在口播上的透明层。返回 (路径, 时长)。"""
    kind, dur = plan['type'], plan['dur']
    n = max(1, round(dur * FPS))
    alpha = kind in ('boom', 'spotlight')
    out = f"{work}/opening_{kind}.{'mov' if alpha else 'mp4'}"
    w = Writer(out, W, H, FPS, alpha=alpha, preview=preview)
    S = unit(W, H)
    if alpha:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        if kind == 'spotlight':
            e = np.hypot((xx - W * 0.5) / (W * 0.46), (yy - H * 0.40) / (H * 0.33))
            vig = (np.clip((e - 0.85) / 0.7, 0, 1) ** 1.3 * 0.9)[..., None]
        rng = np.random.default_rng(5)
        cx, cy = W * 0.5, H * 0.36
        for i in range(n):
            t = i / FPS
            canvas = np.zeros((H, W, 4), np.uint8)
            if kind == 'spotlight':
                k = 1 - ease((t - (dur - 0.45)) / 0.45)
                canvas[..., 3:4] = (vig * 255 * k).astype(np.uint8)
            else:
                if i % 2 == 0:
                    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                    d = ImageDraw.Draw(im)
                    for _ in range(46):
                        a = rng.uniform(0, 2 * np.pi)
                        r0 = rng.uniform(0.30, 0.42) * W
                        d.line([(cx + np.cos(a) * r0, cy + np.sin(a) * r0), (cx + np.cos(a) * W * 1.3, cy + np.sin(a) * W * 1.3)],
                               fill=(255, 255, 255, int(rng.uniform(120, 220))), width=max(2, int(rng.uniform(3, 10) * S)))
                    lines = np.array(im)
                k = 1 - ease((t - 0.35) / 0.25)
                canvas = lines.copy()
                canvas[..., 3] = (canvas[..., 3] * k).astype(np.uint8)
            w.put(canvas)
        w.close()
        return out, dur
    face = np.array([W * 0.5, H * 0.30])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for i, fr in enumerate(read(aroll, 0, dur, (W, H), FPS)):
        t = i / FPS
        if kind == 'flash':
            p = ease(t / 0.2, 'out')
            s = 1.08 - 0.08 * ease(t / dur)
            big = resize(fr, W * s, H * s)
            y0, x0 = int((big.shape[0] - H) * 0.4), (big.shape[1] - W) // 2
            f = big[y0:y0 + H, x0:x0 + W]
            r = 30 * S * (1 - p)
            if r > 1:   # 竖向动态模糊：先压扁再拉回去
                f = resize(resize(f, W, H / (1 + r / 5)), W, H)
            canvas = np.clip(f.astype(np.float32) + 255 * 0.6 * (1 - p), 0, 255).astype(np.uint8)
        elif kind == 'zoom':
            s = 0.45 + 0.55 * ease(t / 0.4, 'out')
            canvas = np.zeros((H, W, 3), np.uint8)
            if s >= 0.999:
                canvas = fr
            else:
                sm = resize(fr, W * s, H * s)
                paste(canvas, sm, (W - sm.shape[1]) / 2, (H - sm.shape[0]) / 2)
        else:   # iris
            r = keyed([(0, 0.01 * W, 'inout'), (0.5, 0.30 * W, 'inout'), (dur, float(np.hypot(W, H)), 'in')], t)
            m = np.clip(r + 0.5 - np.hypot(xx - face[0], yy - face[1]), 0, 1)[..., None]
            canvas = (fr * m).astype(np.uint8)
        w.put(canvas)
    w.close()
    return out, dur
