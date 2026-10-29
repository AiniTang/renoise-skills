"""贴纸、动效与其他（手法库一星第 15 批）：逐帧画的版式，titles 的 layout 写这些名字，cards.title_clip 转过来渲成整屏 .mov。

- trail        头像轨迹残影（avatar_motion_trail）：圆头像沿一条路径移动，每隔一段留下一个静止复制体，路径上橙色箭头链
- spinring     主体物缓转加虚线环（subject_spin_ring）：中上部一个主体物（用户给的抠好的 PNG 或 3D 图标）缓慢自转带柔光，外圈白色虚线环反向慢转
- gesturetext  文字跟手势运动（text_follow_gesture）：字按手动给的关键帧放大缩小、横拉、挤扁，跟着手势走
- paperpanels  透视纸板立在人旁（perspective_paper_panels）：几块带透视的白纸板立在人旁边，竖排彩色关键词和小字，一块块滑入
- orbitcover   地球轨道覆盖动画（orbit_coverage）：黑底地球、细灰轨道环，卫星沿轨道走，地球表面逐块亮起覆盖区，卫星往下投光
- armwipe      手臂抹字（hand_mask_text_wipe）：人旁边一块竖排字，按给的时刻被一道斜边从上往下抹掉（reverse 反过来从手里拉出来）
- mics         话筒围采宣布（mic_cluster_announce）：一排话筒从两侧冲进来像发布会围采，金色闪光扫过留下金边花字
- framesticker 边框贴纸（frame_stickers）：polaroid 拍立得 / film 胶片 / cartoon 卡通手绘框套住人，头部出框
- painpoint    痛点词贴纸接怎么办（pain_point_opening）：黄色主题词，两个彩色痛点词歪斜弹出挂小人贴纸，故障一抖换成黄色「怎么办?」配哭脸和大问号
- jytpl        剪映综艺文字模板近似（jy_text_template_variety）：energy 前方高能 / warn 警告 / out OUT 出局 / aaa 情绪词啊啊啊，循环动画；草稿铺成片，真模板可手动替换
放大镜局部放大（magnifier_zoom）是整屏特效 magnifier 的 reach 变体（手柄从画外伸进来、镜片滑到 at 再移走）。
梗句幽默短乐句（music_humor_sting）是顶层 stings，prepare 时剪成短片段放进音效、同一段配乐让开。
尺寸按 短边 1080 的像素值乘 S。
"""
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bigtype import SERIF, _avatar, _fit, _head_square, _mask_out, _opaque, _person, _pop, _soft_bg
from infocard import BOLD, MED, OSWALD, at_list, card_of, dashed_circle, emoji, glow, latin, rrect, src_image
from keytext import HEAVY, blur, eback, fade_out, frames, put, scale, with_shadow, word
from kvlib import unit, is_landscape, safe_zones, face_crop, hex_rgba, is_image, probe
from annot import side_box, side_center, side_fit
from motion import Writer, ease, over, read, resize, rotate_rgba, text_img, trim

LAYOUTS = ('trail', 'spinring', 'gesturetext', 'paperpanels', 'orbitcover', 'armwipe', 'mics', 'framesticker', 'painpoint', 'jytpl')


def clip(t, W, H, FPS, st, work, aroll, out):
    globals()[t['layout']](t, W, H, FPS, st, work, aroll, out)


def _fin(c, tt, dur, fin=0.12, fout=0.15, keep=False):
    k = min(1.0, tt / fin) * fade_out(tt, dur, fout)
    if keep:
        c[..., 3] = (c[..., 3] * k).astype(np.uint8)
    else:
        c[..., 3] = int(255 * k)
    return c


# ---------------------------------------------------------------- trail 头像轨迹残影
def _chevron(S, col='#F28A1E'):
    im = Image.new('RGBA', (int(44 * S), int(44 * S)), (0, 0, 0, 0))
    ImageDraw.Draw(im).line([(10 * S, 6 * S), (32 * S, 22 * S), (10 * S, 38 * S)], fill=hex_rgba(col), width=int(8 * S), joint='curve')
    return np.array(im)


def trail(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    path = [(x * W, y * H) for x, y in (t.get('path') or [[0.2, 0.3], [0.75, 0.42], [0.3, 0.58], [0.72, 0.74]])]
    copies = t.get('copies', 4)
    D = int((H if is_landscape(W, H) else W) * t.get('d', 0.26))
    if is_landscape(W, H) and not t.get('path'):
        path = [(W * x, H * y) for x, y in [(0.15, 0.32), (0.38, 0.62), (0.62, 0.32), (0.85, 0.62)]]
    if is_landscape(W, H):
        D = min(D, int(H * 0.26))
        path = [(min(W * 0.95 - D / 2, max(W * 0.05 + D / 2, x)), min(H * 0.78 - D / 2, max(H * 0.05 + D / 2, y))) for x, y in path]
    move = t.get('move', min(2.0, dur * 0.6))
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]
    total = sum(seg)

    def at_len(L):
        for (a, b), s_ in zip(zip(path, path[1:]), seg):
            if L <= s_:
                k = L / max(s_, 1e-6)
                return a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, math.atan2(b[1] - a[1], b[0] - a[0])
            L -= s_
        a, b = path[-2], path[-1]
        return b[0], b[1], math.atan2(b[1] - a[1], b[0] - a[0])
    chev = _chevron(S)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    sq = None
    stamps = []
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        if sq is None:
            sq = _head_square(fr, W, H)
            if is_landscape(W, H):
                from effects import face_box
                if not face_box(fr):
                    # 检测不到脸时沿用上部居中的头像范围，只把旧的宽度倍率换成短边。
                    size = min(W, H) * 0.62
                    size, x, y = face_crop(W, H, dict(x=(W / 2 - size / 2) / W, y=(H * 0.33 - size / 2) / H, s=size / W))
                    sq = (x + size / 2, y + size / 2, size)
        c = _opaque(_soft_bg(fr, W, H, 0.55, 4))
        prog = ease(tt / move)
        L = total * prog
        for k in range(int(total / (70 * S))):
            lk = (k + 0.5) * 70 * S
            if lk < L:
                x, y, ang = at_len(lk)
                put(c, rotate_rgba(chev, -math.degrees(ang)), x, y, 0.9)
        av = _avatar(fr, sq, D, int(5 * S), '#FFFFFF')
        for j in range(1, copies):
            if prog >= j / copies and len(stamps) < j:
                stamps.append((av.copy(), *at_len(total * j / copies)[:2]))
        for g, x, y in stamps:
            put(c, g, x, y, 0.85)
        x, y, _ = at_len(L)
        put(c, av, x, y)
        w.put(_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- spinring 主体物缓转加虚线环
def spinring(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    sw = int(W * t.get('w', 0.62))
    if is_landscape(W, H):
        sw = min(sw, int(H * 0.45))
    if t.get('src'):
        sub = np.array(Image.open(t['src']).convert('RGBA'))
        sub = _fit(sub, sw, sw)
    else:
        sub = emoji(t.get('icon', 'Globe showing asia-australia'), sw)
    gl = sub.copy()
    gl[..., :3] = (255, 214, 160)
    gl = blur(np.pad(gl, ((40, 40), (40, 40), (0, 0))), 22 * S)
    gl[..., 3] = (gl[..., 3] * 0.55).astype(np.uint8)
    D = int(max(sub.shape[:2]) * 1.12)
    ring = dashed_circle(D, 3 * S, '#FFFFFF', dash_deg=5, gap_deg=5)
    cy = H * t.get('y', 0.36)
    title = with_shadow(_fit(word(t['text'], 100 * S, '#FFFFFF', HEAVY), W * 0.86), 8 * S, 0.6) if t.get('text') else None
    cx = W / 2
    if is_landscape(W, H):
        cx, cy = W * 0.3, H * t.get('y', 0.44)
        hh = max(gl.shape[0], D * 1.2) / 2
        cy = np.clip(cy, H * 0.05 + hh, H * 0.8 - hh)
        title = _fit(title, W * 0.35, H * 0.25) if title is not None else None
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = _opaque(_soft_bg(next(frs), W, H, 0.35, 5))   # 整页：口播虚化压暗做底，主体物立在中上部
        p = ease(tt / 0.4)
        put(c, gl, cx, cy, p)
        put(c, rotate_rgba(sub, -3 * tt), cx, cy, p)
        put(c, rotate_rgba(ring, 3 * tt), cx, cy, p)
        if title is not None:
            put(c, title, (W * 0.73 if is_landscape(W, H) else W / 2), (cy if is_landscape(W, H) else cy + D / 2 + 80 * S), ease((tt - 0.3) / 0.3))
        w.put(_fin(c, tt, dur, 0.12))
    w.close()


# ---------------------------------------------------------------- gesturetext 文字跟手势运动
def gesturetext(t, W, H, FPS, st, work, aroll, out):
    """keys: [[秒, 缩放, 横移（画面宽比例）, 竖移（画面高比例）, 横向挤压]]，关键帧之间缓入缓出；不写就是双手张开放大、一推横移、一压挤扁的示范。"""
    S = unit(W, H)
    dur, n = frames(t, FPS)
    keys = t.get('keys') or [[0.0, 0.6, 0, 0, 1.0], [0.6, 1.3, 0, 0, 1.0], [1.4, 1.0, 0.25, 0, 1.0], [2.2, 1.0, 0, 0.03, 0.6], [3.0, 1.0, 0, 0, 1.0]]
    g = with_shadow(word(t['text'], 170 * S, t.get('color', '#FFFFFF'), HEAVY, stroke=int(6 * S), stroke_color='#111111'), 8 * S, 0.6)
    y0 = H * t.get('y', 0.62)
    x0 = W / 2
    if is_landscape(W, H):
        x0, y0 = side_center(t, W, H)
        g = side_fit(g, t, W, H, 0.65)

    def val(tt, j):
        if tt <= keys[0][0]:
            return keys[0][j]
        for a, b in zip(keys, keys[1:]):
            if tt < b[0]:
                return a[j] + (b[j] - a[j]) * ease((tt - a[0]) / max(1e-3, b[0] - a[0]))
        return keys[-1][j]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        k, dx, dy, sx = val(tt, 1), val(tt, 2), val(tt, 3), val(tt, 4)
        im = Image.fromarray(g)
        im = im.resize((max(1, int(g.shape[1] * k * sx)), max(1, int(g.shape[0] * k))), Image.BILINEAR)
        cx, cy = x0 + dx * W, y0 + dy * H
        if is_landscape(W, H):
            im = Image.fromarray(side_fit(np.array(im), t, W, H, 0.95))
            bx, by, br, bb = side_box(t, W, H)
            cx, cy = np.clip(cx, bx + im.width / 2, br - im.width / 2), np.clip(cy, by + im.height / 2, bb - im.height / 2)
        put(c, np.array(im), cx, cy, ease(tt / 0.15))
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- paperpanels 透视纸板立在人旁
def _panel(word_, note, color, S, W, H):
    if is_landscape(W, H):
        # 侧栏里改成横向标题配说明，不能把竖纸板连同小字一起缩小。
        pw, ph = int(W * 0.21), int(H * 0.22)
        a = rrect(pw, ph, 12 * S, '#FFFFFF', '#D0D0D0', max(1, int(2 * S)))
        put(a, _fit(word(word_, 72 * S, color, HEAVY), pw * 0.82), pw / 2, ph * 0.3)
        rows = [note[i:i + 10] for i in range(0, len(note), 10)][:3] if note else []
        for j, row in enumerate(rows):
            put(a, _fit(word(row, 34 * S, '#555555', MED), pw * 0.86), pw / 2, ph * 0.55 + j * 35 * S)
        return rotate_rgba(with_shadow(a, 8 * S, 0.35, dy=int(5 * S)), -3)
    pw, ph = int(W * 0.24), int(H * 0.5)
    im = Image.new('RGBA', (pw, ph), (250, 249, 245, 255))
    a = np.array(im)
    kw = _fit(text_img(word_, H * 0.075, color, fontfile=HEAVY, vertical=True), pw * 0.7, ph * 0.62)
    put(a, kw, pw / 2, ph * 0.36)
    if note:
        f_rows = [note[i:i + 7] for i in range(0, len(note), 7)][:4]
        for j, r in enumerate(f_rows):
            put(a, word(r, 22 * S, '#555555', MED), pw / 2, ph * 0.76 + j * 32 * S)
    import cv2
    h, w = a.shape[:2]
    k = 0.32
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [0, h], [w, h], [w, 0]]), np.float32([[0, 0], [0, h], [w * 0.8, h * (1 - k / 2)], [w * 0.8, h * k / 2]]))
    a = cv2.warpPerspective(a, M, (w, h), flags=cv2.INTER_CUBIC)
    return with_shadow(trim(a), 12 * S, 0.4, dy=int(8 * S))


def paperpanels(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = [x if isinstance(x, dict) else {'text': x} for x in (t.get('items') or [])][:3]
    cols = ['#6CC24A', '#C4161C', '#2F6FD8']
    pans = [_panel(x['text'], x.get('note'), cols[k % 3], S, W, H) for k, x in enumerate(items)]
    if is_landscape(W, H):
        pans = [_fit(g, W * 0.22, H * 0.26) for g in pans]
    times = at_list(t, len(pans), 0.7, 0.2)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for k, (g, a) in enumerate(zip(pans, times)):
            p = ease((tt - a) / 0.35, 'out')
            if p <= 0:
                continue
            x = W * (0.84 - 0.13 * (len(pans) - 1 - k)) if len(pans) > 1 else W * 0.82
            y = H * 0.56
            if is_landscape(W, H):
                x, y = W * (0.175 if k % 2 == 0 else 0.825), H * (0.3 + 0.31 * (k // 2))
            put(c, scale(g, 0.78), x + (1 - p) * W * 0.4, y, p)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- orbitcover 地球轨道覆盖动画
def orbitcover(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    ED = int(W * 0.62)
    earth = emoji('Globe showing americas', ED)
    RR = W * 0.43
    cx, cy = W / 2, H * t.get('y', 0.42)
    if is_landscape(W, H):
        ED, RR = int(H * 0.54), H * 0.4
        cx, cy = W * 0.3, H * t.get('y', 0.44)
        cy = np.clip(cy, H * 0.05 + ED / 2, H * 0.8 - ED / 2)
        earth = emoji('Globe showing americas', ED)
    rng = random.Random(5)
    zones = [(rng.uniform(-60, 240), rng.uniform(25, 50)) for _ in range(t.get('zones', 6))]
    title = with_shadow(_fit(word(t['text'], 90 * S, '#FFFFFF', HEAVY), W * 0.86), 8 * S, 0.6) if t.get('text') else None
    if is_landscape(W, H) and title is not None:
        title = _fit(title, W * 0.35, H * 0.3)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        d = ImageDraw.Draw(im)
        d.ellipse([cx - RR, cy - RR * 0.35, cx + RR, cy + RR * 0.35], outline=(85, 85, 85, 255), width=max(1, int(2 * S)))
        c = np.array(im)
        put(c, earth, cx, cy)
        lit = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lit)
        prog = tt / max(0.5, dur - 0.5)
        for k, (a0, span) in enumerate(zones):
            if prog > k / len(zones):
                ld.pieslice([cx - ED / 2, cy - ED / 2, cx + ED / 2, cy + ED / 2], a0, a0 + span, fill=(245, 233, 160, 100))
        ang = 2 * math.pi * tt / 3.0
        sx, sy = cx + RR * math.cos(ang), cy + RR * 0.35 * math.sin(ang)
        ld.polygon([(sx, sy), (cx - ED * 0.12, cy), (cx + ED * 0.12, cy)], fill=(245, 233, 160, 50))
        lm = np.array(lit)
        disc = Image.new('L', (W, H), 0)
        ImageDraw.Draw(disc).ellipse([cx - ED / 2, cy - ED / 2, cx + ED / 2, cy + ED / 2], fill=255)
        lm[..., 3] = (lm[..., 3] * (np.array(disc) / 255 * 0.85 + 0.15)).astype(np.uint8)
        over(c, lm, 0, 0)
        im = Image.fromarray(c)
        ImageDraw.Draw(im).ellipse([sx - 9 * S, sy - 9 * S, sx + 9 * S, sy + 9 * S], fill=(255, 255, 230, 255))
        c = np.array(im)
        if title is not None:
            put(c, title, (W * 0.73 if is_landscape(W, H) else W / 2), (cy if is_landscape(W, H) else H * 0.8), ease((tt - 0.4) / 0.4))
        w.put(_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- armwipe 手臂抹字
def armwipe(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    g = with_shadow(text_img(t['text'], H * 0.08, t.get('color', '#FFFFFF'), fontfile=HEAVY, vertical=True, stroke=int(4 * S), stroke_color='#111111'),
                    8 * S, 0.6)
    if is_landscape(W, H):
        g = side_fit(g, t, W, H, 0.9)
    gh, gw = g.shape[:2]
    a0 = t.get('wipe_at', max(0.5, dur - 1.2))
    wd = t.get('wipe_dur', 0.7)
    rev = t.get('reverse', False)
    x = W * t.get('x', 0.82)
    cy = H * t.get('y', 0.5)
    if is_landscape(W, H):
        bx, by, br, bb = side_box(t, W, H, 'right' if t.get('x', 0.82) >= 0.5 else 'left')
        x = np.clip(x, bx + gw / 2, br - gw / 2)
        cy = np.clip(cy, by + gh / 2, bb - gh / 2)
    yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
    edge = yy + (xx - gw / 2) * 0.6   # 斜边：像手臂扫过去
    feather = gh * 0.05
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        p = ease((tt - a0) / wd)
        front = -gh * 0.4 + (gh * 1.8) * (p if not rev else 1 - p)
        m = np.clip((edge - front) / feather, 0, 1) if not rev else np.clip((front - edge) / feather, 0, 1)
        if rev and tt < a0:
            m = np.zeros_like(m)
        a = g.copy()
        a[..., 3] = (a[..., 3] * m).astype(np.uint8)
        c = np.zeros((H, W, 4), np.uint8)
        put(c, a, x, cy, ease(tt / 0.2) if not rev else 1.0)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- mics 话筒围采宣布
def mics(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    mic = emoji('Microphone', 220 * S)
    k = t.get('count', 6)
    gold = word(t['text'], 110 * S, '#FFD84A', HEAVY, stroke=int(6 * S), stroke_color='#B8860B')
    gold = glow(gold, 10 * S, '#FFE9A0', 0.5)
    y = H * t.get('y', 0.74)
    rng = random.Random(3)
    slots = [(W * (0.08 + 0.84 * j / (k - 1)), y + rng.uniform(-30, 30) * S, rng.uniform(-25, 25)) for j in range(k)]
    cx = W / 2
    if is_landscape(W, H):
        cx, _ = side_center(t, W, H)
        gold = side_fit(gold, t, W, H, 0.9)
        mic = scale(mic, 0.65)
        y = np.clip(H * t.get('y', 0.66), H * 0.4, H * 0.7)
        slots = [(W * ((0.11 + 0.065 * (j // 2)) if j % 2 == 0 else (0.76 + 0.065 * (j // 2))), y, r) for j, (_, _, r) in enumerate(slots)]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3, 'out')
        for j, (x, yy, r) in enumerate(slots):
            side = -1 if x < W / 2 else 1
            put(c, rotate_rgba(mic, r - side * 30), x + side * (1 - p) * W * 0.6, yy, p)
        q = ease((tt - 0.3) / 0.3, 'out')
        if q > 0:
            put(c, scale(gold, 0.8 + 0.2 * q), cx, y - 190 * S, q)
            sw = (tt - 0.3) / 0.35   # 金色闪光扫过
            if 0 < sw < 1:
                band = np.zeros((int(gold.shape[0] * 1.4), int(80 * S), 4), np.uint8)
                band[...] = (255, 250, 220, 160)
                band = blur(rotate_rgba(band, 20), 8 * S)
                put(c, band, cx - gold.shape[1] / 2 + gold.shape[1] * sw, y - 190 * S)
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- framesticker 边框贴纸
FRAMESTICKER_VARIANTS = {
    'polaroid': '拍立得框：白色宽底边的相片框套住人，头顶出框，底边写一行手写字',
    'film': '胶片框：黑色胶片带两侧齿孔套住人，头顶出框',
    'cartoon': '卡通手绘框：彩色粗描边手绘框加小星星，头顶出框（不适合严肃话题）',
}


def framesticker(t, W, H, FPS, st, work, aroll, out):
    import matte
    from keytext import HAND
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'polaroid')
    fw, fh = int(W * t.get('w', 0.74)), int(H * 0.5)
    fx, fy = (W - fw) / 2, H * t.get('y', 0.3)
    if is_landscape(W, H):
        fw, fh = int(min(fw, W * 0.72)), int(H * 0.44)
        fx, fy = (W - fw) / 2, np.clip(H * t.get('y', 0.18), H * 0.05 + 26 * S, H * 0.8 - fh - 130 * S)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bw = int(26 * S)
    if v == 'polaroid':
        d.rectangle([fx - bw, fy - bw, fx + fw + bw, fy + fh + bw * 5], fill=(250, 250, 248, 255))
    elif v == 'film':
        d.rectangle([fx - bw * 2.2, fy - bw, fx + fw + bw * 2.2, fy + fh + bw], fill=(16, 16, 16, 255))
        for y in range(int(fy), int(fy + fh), int(46 * S)):
            for x in (fx - bw * 1.6, fx + fw + bw * 0.6):
                d.rounded_rectangle([x, y, x + bw, y + 24 * S], radius=4 * S, fill=(235, 235, 235, 255))
    else:
        d.rounded_rectangle([fx - bw, fy - bw, fx + fw + bw, fy + fh + bw], radius=30 * S, outline=(255, 92, 140, 255), width=int(16 * S))
        d.rounded_rectangle([fx - bw * 0.3, fy - bw * 0.3, fx + fw + bw * 0.3, fy + fh + bw * 0.3], radius=24 * S, outline=(255, 214, 64, 255), width=int(6 * S))
    d.rectangle([fx, fy, fx + fw, fy + fh], fill=(0, 0, 0, 0))
    frame = np.array(im)
    hole = np.zeros((H, W), np.float32)
    hole[int(fy):int(fy + fh), int(fx):int(fx + fw)] = 1
    cap = word(t['text'], 54 * S, '#333333', HAND) if t.get('text') and v == 'polaroid' else None
    if is_landscape(W, H) and cap is not None:
        cap = _fit(cap, fw * 0.8, 70 * S)
    stars = [emoji('Glowing star', 110 * S), emoji('Sparkles', 90 * S)] if v == 'cartoon' else []
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        p = ease(tt / 0.3, 'out')
        c = np.zeros((H, W, 4), np.uint8)
        c[..., :3] = _soft_bg(fr, W, H, 0.55, 4)
        c[..., 3] = 255
        inside = fr.astype(np.float32) * hole[..., None] + c[..., :3] * (1 - hole[..., None])
        c[..., :3] = (c[..., :3] * (1 - p) + inside * p).astype(np.uint8)
        over(c, frame, 0, (1 - p) * 60 * S, p)
        head = a.copy()
        head[int(fy + fh * 0.25):] = 0   # 只有框上沿附近往上的人压在框前：头出框
        over(c, _person(fr, head * p), 0, 0)
        if cap is not None:
            put(c, cap, W / 2, fy + fh + bw * 3, p)
        for k, s in enumerate(stars):
            q = (tt - 0.3 - 0.15 * k) / 0.2
            if q > 0:
                put(c, scale(s, _pop(min(1.0, q))), fx + (fw + 20 * S if k == 0 else -20 * S), fy + (fh * 0.15 if k == 0 else fh * 0.8), min(1.0, q * 2))
        w.put(_fin(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- painpoint 痛点词贴纸接怎么办
def painpoint(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    title = with_shadow(word(t.get('text', '剪辑'), 130 * S, '#F5D300', HEAVY, stroke=int(6 * S), stroke_color='#111111'), 8 * S, 0.6)
    pains = (t.get('items') or ['没排版~', '没思路~'])[:2]
    pcols = ['#F06A8A', '#3FCF6A']
    pg = [rotate_rgba(word(x, 124 * S, pcols[k], HEAVY, stroke=int(6 * S), stroke_color='#FFFFFF'), 8 if k == 0 else -8) for k, x in enumerate(pains)]
    walker = emoji('Man walking', 120 * S)
    ask = with_shadow(word(t.get('ask', '怎么办?'), 150 * S, '#F5D300', HEAVY, stroke=int(7 * S), stroke_color='#111111'), 8 * S, 0.6)
    cry = emoji('Loudly crying face', 200 * S)
    qm = word('?', 300 * S, '#FFFFFF', HEAVY, stroke=int(8 * S), stroke_color='#111111')
    if is_landscape(W, H):
        title, ask, qm = [side_fit(g, t, W, H, 0.85) for g in (title, ask, qm)]
        pg = [side_fit(g, t, W, H, 0.8) for g in pg]
        walker, cry = scale(walker, 0.7), scale(cry, 0.8)
    sw = t.get('switch_at', min(1.6, dur * 0.55))
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = _opaque((fr.astype(np.float32) * 0.55).astype(np.uint8))
        if tt < sw:
            put(c, title, (W * 0.175 if is_landscape(W, H) else W / 2), H * 0.3, ease(tt / 0.2))
            for k, g in enumerate(pg):
                q = (tt - 0.3 - 0.25 * k) / 0.15
                if q > 0:
                    x, y = W * (0.3 if k == 0 else 0.68), H * (0.46 if k == 0 else 0.58)
                    if is_landscape(W, H):
                        x, y = W * (0.175 if k == 0 else 0.825), H * 0.58
                    put(c, scale(g, _pop(min(1.0, q))), x, y, min(1.0, q * 2))
                    put(c, walker, x + g.shape[1] * (0.2 if is_landscape(W, H) else 0.45), y - g.shape[0] * 0.6, min(1.0, q * 2))
        else:
            q = (tt - sw - 0.15) / 0.2
            if q > 0:
                put(c, qm, (W * 0.825 if is_landscape(W, H) else W * 0.78), H * (0.3 if is_landscape(W, H) else 0.38), min(1.0, q * 2))
                put(c, scale(ask, _pop(min(1.0, q))), (W * 0.825 if is_landscape(W, H) else W / 2), H * 0.55, min(1.0, q * 2))
                put(c, cry, (W * 0.175 if is_landscape(W, H) else W * 0.24), H * 0.36, min(1.0, q * 2))
        if sw <= tt < sw + 0.15:   # 故障抖一下：红青错开
            sh = int(14 * S)
            c[..., 0] = np.roll(c[..., 0], sh, axis=1)
            c[..., 2] = np.roll(c[..., 2], -sh, axis=1)
        w.put(_fin(c, tt, dur))
    w.close()


# ---------------------------------------------------------------- jytpl 剪映综艺文字模板近似
JYTPL_VARIANTS = {
    'energy': '前方高能：红黄警示条框着「前方高能」，闪烁跳动',
    'warn': '警告：黄黑斜纹三角警示牌加「警告」，左右摇摆',
    'out': 'OUT：红色描边大 OUT 盖章砸下、抖一下',
    'aaa': '情绪词：一串「啊啊啊」逐字弹跳、越来越大',
}


def jytpl(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return _landscape_template(t, W, H, FPS, out)
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'energy')
    y = H * t.get('y', 0.64)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'energy':
        tx = word(t.get('text', '前方高能'), 150 * S, '#FFFFFF', HEAVY, stroke=int(6 * S), stroke_color='#B00000')
        bw, bh = tx.shape[1] + int(80 * S), tx.shape[0] + int(50 * S)
        box = rrect(bw, bh, 12 * S, '#E8221B', '#FFD21F', int(8 * S))
        put(box, tx, bw / 2, bh / 2)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            blink = 0.65 + 0.35 * (int(tt * 8) % 2)
            put(c, scale(box, 1 + 0.05 * math.sin(tt * 18)), W / 2, y, blink * ease(tt / 0.12))
            w.put(_fin(c, tt, dur, 0.01, keep=True))
    elif v == 'warn':
        D = int(260 * S)
        im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.polygon([(D / 2, 8 * S), (D - 8 * S, D - 14 * S), (8 * S, D - 14 * S)], fill=(255, 210, 31, 255), outline=(17, 17, 17, 255), width=int(10 * S))
        dr.text((D / 2, D * 0.62), '!', font=ImageFont.truetype(str(HEAVY), int(D * 0.5)), anchor='mm', fill=(17, 17, 17, 255))
        sign = np.array(im)
        tx = word(t.get('text', '警告'), 120 * S, '#FFD21F', HEAVY, stroke=int(6 * S), stroke_color='#111111')
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            r = 10 * math.sin(tt * 9)
            put(c, rotate_rgba(sign, r), W * 0.3, y, ease(tt / 0.15))
            put(c, rotate_rgba(tx, -r * 0.5), W * 0.64, y, ease(tt / 0.15))
            w.put(_fin(c, tt, dur, 0.01, keep=True))
    elif v == 'out':
        tx = with_shadow(word(t.get('text', 'OUT'), 260 * S, '#FFFFFF', latin(t.get('text', 'OUT'), OSWALD), stroke=int(12 * S), stroke_color='#E8221B'), 10 * S, 0.6)
        tx = rotate_rgba(tx, -12)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            k = 2.2 - 1.2 * ease(tt / 0.18, 'in') if tt < 0.18 else 1.0
            jit = 8 * S * math.sin(tt * 60) * max(0.0, 1 - (tt - 0.18) / 0.3) if tt >= 0.18 else 0
            put(c, scale(tx, k), W / 2 + jit, y, min(1.0, tt / 0.1))
            w.put(_fin(c, tt, dur, 0.01, keep=True))
    else:
        text = t.get('text', '啊啊啊啊')
        cols = ['#FF4D6D', '#FFD21F', '#3FCF6A', '#3A8DE0']
        gs = [word(ch, 120 * S * (1 + 0.18 * j), cols[j % 4], HEAVY, stroke=int(6 * S), stroke_color='#111111') for j, ch in enumerate(text)]
        tot = sum(g.shape[1] for g in gs)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            x = W / 2 - tot / 2
            for j, g in enumerate(gs):
                q = (tt - 0.1 * j) / 0.15
                if q > 0:
                    put(c, scale(g, _pop(min(1.0, q))), x + g.shape[1] / 2, y + 20 * S * math.sin(tt * 12 + j), min(1.0, q * 2))
                x += g.shape[1]
            w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()


# ---------------------------------------------------------------- 放大镜从画外伸进来（effects 的 magnifier，variant reach）
def magnifier_reach(fc, cur, f, tag, add_input, W, H, FPS, work):
    """镜片沿 from（画外一点）→ at 滑进来 0.5 秒，停住，最后 0.5 秒滑出去；镜片里放大 zoom 倍，裁切位置跟着镜片走，镜框带长手柄伸到画外。"""
    from effects import _branch, _even, _png_input
    S = unit(W, H)
    t0, t1 = float(f['t0']), float(f['t1'])
    d = t1 - t0
    cx, cy = f.get('at', [0.5, 0.4])
    cx, cy = cx * W, cy * H
    fx, fy = f.get('from', [1.25, 1.1])
    fx, fy = fx * W, fy * H
    R = _even(W * f.get('r', 0.2))
    if is_landscape(W, H):
        R = max(2, _even(min(R, H * 0.19, cy - H * 0.05, H * 0.8 - cy, cx - W * 0.05, W * 0.95 - cx)))
    z = f.get('zoom', 1.5)
    sw = _even(2 * R / z)
    if is_landscape(W, H):
        sw = max(2, min(sw, _even(min(W, H))))
    mv = f.get('move', 0.5)
    def P(tv):
        return f"if(lt({tv},{mv}),1-pow(1-{tv}/{mv},3),if(gt({tv},{d - mv:.3f}),1-pow(({tv}-{d - mv:.3f})/{mv},3),1))"

    def XY(tv):
        return f"({fx:.1f}+({cx - fx:.1f})*{P(tv)})", f"({fy:.1f}+({cy - fy:.1f})*{P(tv)})"
    X, Y = XY('t')
    m, b = _branch(fc, cur, tag, t0, t1, f"crop={sw}:{sw}:'clip({X}-{sw / 2},0,iw-{sw})':'clip({Y}-{sw / 2},0,ih-{sw})',scale={2 * R}:{2 * R},format=rgba")
    mask = Path(work) / f'lens_mask_{R}.png'
    if not mask.exists():
        im = Image.new('L', (4 * R, 4 * R), 0)
        ImageDraw.Draw(im).ellipse([4, 4, 4 * R - 4, 4 * R - 4], fill=255)
        im.resize((2 * R, 2 * R), Image.LANCZOS).save(mask)
    mi = _png_input(add_input, mask, d, FPS)
    fc.append(f"[{mi}:v]format=gray,setpts=PTS-STARTPTS+{t0:.3f}/TB[{tag}k]")
    fc.append(f"{b}[{tag}k]alphamerge[{tag}l]")
    Xt, Yt = XY(f"(t-{t0:.3f})")
    fc.append(f"{m}[{tag}l]overlay=x='{Xt}-{R}':y='{Yt}-{R}':enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}x]")
    rim = Path(work) / f'lens_rim_reach_{R}.png'
    L = int(R * 3.2)
    if not rim.exists():   # 镜框加一根伸向右下画外的长手柄
        k = 2
        D = (2 * R + 2 * L) * k
        im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        c = D / 2
        ang = math.atan2(fy - cy, fx - cx)
        hx0, hy0 = c + math.cos(ang) * R * k * 1.05, c + math.sin(ang) * R * k * 1.05
        hx1, hy1 = c + math.cos(ang) * (R + L * 0.95) * k, c + math.sin(ang) * (R + L * 0.95) * k
        dr.line([(hx0, hy0), (hx1, hy1)], fill=(52, 34, 22, 255), width=int(R * 0.26 * k))
        dr.line([(hx0, hy0), (hx1, hy1)], fill=(120, 80, 48, 255), width=int(R * 0.12 * k))
        rr = R * k
        dr.ellipse([c - rr - 16 * S * k, c - rr - 16 * S * k, c + rr + 16 * S * k, c + rr + 16 * S * k], outline=(40, 40, 46, 255), width=int(18 * S * k))
        dr.ellipse([c - rr - 3 * S * k, c - rr - 3 * S * k, c + rr + 3 * S * k, c + rr + 3 * S * k], outline=(255, 255, 255, 230), width=int(4 * S * k))
        Image.fromarray(np.array(im.resize((D // k, D // k), Image.LANCZOS))).save(rim)
    rw = Image.open(rim).size[0]
    ri = _png_input(add_input, rim, d, FPS)
    fc.append(f"[{ri}:v]format=rgba,setpts=PTS-STARTPTS+{t0:.3f}/TB[{tag}rv]")
    fc.append(f"[{tag}x][{tag}rv]overlay=x='{Xt}-{rw // 2}':y='{Yt}-{rw // 2}':enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


# ---------------------------------------------------------------- 顶层字段：叠加物与梗句短乐句
def prepare_overlays(tl):
    """叠加物的横屏默认值先写进时间线，成片和草稿就能用同一套位置与尺寸。"""
    cv = tl.get('canvas', {'w': 1080, 'h': 1920})
    W, H = cv['w'], cv['h']
    if not is_landscape(W, H):
        return
    for o in tl.get('overlays', []):
        src = o['src']
        if Path(src).suffix.lower() == '.heic':
            from kvlib import to_png
            cache = Path('.cache') / 'overlay_meta'
            cache.mkdir(parents=True, exist_ok=True)
            src = to_png(src, cache)
        info = probe(src)
        x0, y0, x1, y1 = side_box(o, W, H)
        cx, cy = side_center(o, W, H)
        size = 1080 * unit(W, H)
        ow = min(size * o.get('w', 0.3), x1 - x0, (y1 - y0) * info['w'] / info['h'])
        # 向上留一个浮点精度，避免渲染器再取整时少 2 像素。
        o['w'] = math.nextafter(max(2, int(ow + 1e-6) // 2 * 2) / size, math.inf)
        o.setdefault('x', cx / W)
        o.setdefault('y', cy / H)


def prepare(tl, st, base='.'):
    """stings: [{"t", "src": 用户给的喜剧短乐句, "in": 从第几秒截, "dur": 2~4, "db": 0}] → 剪成短片段放进手写音效，这几秒配乐让开（_breaks）。"""
    cache = Path.home() / '.cache' / 'koubo' / 'stings'
    for s in tl.get('stings') or []:
        if s.get('_prep'):
            continue
        s['_prep'] = True
        src = Path(s['src']) if Path(s['src']).is_absolute() else Path(base) / s['src']
        d = float(s.get('dur', 3.0))
        cache.mkdir(parents=True, exist_ok=True)
        out = cache / f"{src.stem}_{s.get('in', 0)}_{d}.wav"
        if not out.exists():
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(s.get('in', 0)), '-t', str(d), '-i', str(src), '-af',
                            f'afade=t=in:d=0.05,afade=t=out:st={max(0.0, d - 0.15)}:d=0.15', '-ar', '48000', '-ac', '2', str(out)], check=True)
        tl.setdefault('audio', {}).setdefault('sfx', []).append({'src': str(out), 't': float(s['t']), 'db': s.get('db', -2), 'sound': 'sting'})
        tl.setdefault('_breaks', []).append((round(float(s['t']) - 0.1, 3), round(float(s['t']) + d + 0.1, 3)))


def _landscape_template(t, W, H, FPS, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'energy')
    text = t.get('text') or {'energy': '前方高能', 'warn': '警告', 'out': 'OUT', 'aaa': '啊啊啊啊'}[v]
    cx, cy = side_center(t, W, H)
    if v == 'energy':
        tx = word(text, 100 * S, '#FFFFFF', HEAVY, stroke=int(5 * S), stroke_color='#B00000')
        g = rrect(tx.shape[1] + 60 * S, tx.shape[0] + 45 * S, 12 * S, '#E8221B', '#FFD21F', int(7 * S))
        put(g, tx, g.shape[1] / 2, g.shape[0] / 2)
    elif v == 'warn':
        D = int(160 * S)
        im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.polygon([(D / 2, 4 * S), (D - 4 * S, D - 4 * S), (4 * S, D - 4 * S)], fill='#FFD21F', outline='#111111', width=max(1, int(6 * S)))
        sign = np.array(im)
        put(sign, word('!', 90 * S, '#111111', HEAVY), D / 2, D * 0.63)
        tx = word(text, 100 * S, '#FFD21F', HEAVY, stroke=int(5 * S), stroke_color='#111111')
        g = np.zeros((sign.shape[0] + tx.shape[0] + int(30 * S), max(sign.shape[1], tx.shape[1]), 4), np.uint8)
        put(g, sign, g.shape[1] / 2, sign.shape[0] / 2)
        put(g, tx, g.shape[1] / 2, g.shape[0] - tx.shape[0] / 2)
    else:
        g = word(text, 160 * S, '#FFFFFF' if v == 'out' else '#FFD21F', latin(text, OSWALD) if v == 'out' else HEAVY,
                 stroke=int(8 * S), stroke_color='#E8221B' if v == 'out' else '#111111')
    g = side_fit(with_shadow(g, 8 * S, 0.6), t, W, H, 0.78)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        k = (1.2 - 0.2 * ease(tt / 0.18)) if v == 'out' else 1 + 0.04 * math.sin(tt * 12)
        angle = 6 * math.sin(tt * 9) if v == 'warn' else (-10 if v == 'out' else 0)
        spr = side_fit(rotate_rgba(scale(g, k), angle), t, W, H, 0.95)
        x0, y0, x1, y1 = side_box(t, W, H)
        yy = np.clip(cy, y0 + spr.shape[0] / 2, y1 - spr.shape[0] / 2)
        put(c, spr, cx, yy, ease(tt / 0.12))
        w.put(_fin(c, tt, dur, 0.01, keep=True))
    w.close()
