"""信息卡片（手法库第 11 批）：逐帧画的卡片版式，titles 的 layout 写这些名字，cards.title_clip 转过来渲成整屏 .mov。

- callout    界面截图圈注卡（ui_callout_card）：人旁边滑入深色圆角截图卡，白色虚线圈住一个点，黄色手绘弧形箭头配黄底小标签
- widget     仿界面小组件（ui_widget_mock）：search 搜索框逐字打出关键词 / sfx 仿剪映音效库列表项随音效弹出
- flow       流程节点逐级点亮（flowchart_nodes）：黑底金边小卡排成流程、金色双箭头相连，说到哪张哪张变浅黄，口播压暗、右下圆头像
- axis       时间轴区间示意（timeline_axis）：two_point 两点加游标 / events 事件标点逐个点亮 / year 年份刻度尺滚动 / wave 波形切点卡
- stepwall   暗色拼格步骤墙（step_mosaic_wall）：大小不一的暗色格子里卡其色 STEP 编号和白色步骤名，整体缓推
- reslist    资源清单页（resource_list_page）：paper 整屏牛皮纸金黄斜体清单 / poster 左侧半透明规格海报、右侧大字逐个点名
- typerow    竖卡一排类型展示（type_card_row）：screenshot 白底竖版截图卡依次排开、标签上下交错 / wireframe 构图线框小卡滑入再放大一张
- photostack 并列图片卡错落（photo_card_stack）：tab 彩色折角阶梯卡 / tilted 人推到右边、左边三张倾斜白边照片卡
- comments   评论气泡堆（comment_bubbles）：behind 人身后的倾斜评论卡 / pileup 差评气泡快速堆满
- fanwin     头后三窗口扇形展开（fan_window_cards）：头顶后方一张竖窗，两张从它后面向两侧滑出，人压在卡片前
- ticker     黑底发光播报框（news_ticker_box）：发光白边黑框里反色正文缓慢上滚，标题高亮词白底黑字
- quotetype  压暗底引文逐行打出（quote_typewriter_dim）：口播压暗、头像缩到左下，引文一行一行打出
- labelcol   纸页左标签右内容卡（paper_label_column）：牛皮纸底，左列红色标签带英文，右侧大圆角卡放对应例子，换标签只换内容
- person     人物信息卡（person_info_card）：profile 仿主页博主信息条 / nameplate 金色发光名字加黄色头衔
- products   压暗叠商品卡（product_cards_dim）：口播压暗加斜条纹，白色商品卡自下而上依次弹出
- translate  外文原文配中文翻译条（doc_translation_bar）：外文截图放大、那一句反白，下方弹出黑色圆角中文意译条
截图隐私打码（privacy_mosaic）不是版式：broll 或卡片素材写 "mosaic"，prepare 时先打成马赛克副本（mosaic_file）。
尺寸按 短边 1080 的像素值乘 S。
"""
import hashlib
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bigtype import SERIF, _avatar, _fit, _head_square, _opaque, _person, _pop, _soft_bg, _wrap
from fonts import FONTS
from keytext import HAND, HEAVY, blur, eback, fade_out, frames, icon_png, put, scale, with_shadow, word
from kvlib import unit, is_landscape, safe_zones, face_crop, hex_rgba, is_image, paper_texture, probe
from motion import Writer, ease, over, read, resize, rotate_rgba, text_img, trim

MED = FONTS / 'SourceHanSansCN-Medium.otf'
BOLD = FONTS / 'SourceHanSansCN-Bold.otf'
OSWALD = FONTS / 'Oswald-Bold.ttf'
CACHE = Path.home() / '.cache' / 'koubo' / 'mosaic'

LAYOUTS = ('callout', 'widget', 'flow', 'axis', 'stepwall', 'reslist', 'typerow', 'photostack', 'comments', 'fanwin', 'ticker',
           'quotetype', 'labelcol', 'person', 'products', 'translate')


def clip(t, W, H, FPS, st, work, aroll, out):
    globals()[t['layout']](t, W, H, FPS, st, work, aroll, out)


# ---------------------------------------------------------------- 小工具
def src_image(src, crop=None, at=None):
    """素材的一张图（PIL RGB）：图片直接读，视频从三成处截一帧（录屏开头常是黑屏），按原尺寸；crop=[x, y, 宽, 高] 比例。"""
    if is_image(src):
        im = Image.open(src).convert('RGB')
    else:
        p = probe(src)
        w, h = p['w'] or 1080, p['h'] or 1920
        a = next(read(src, at if at is not None else p['duration'] * 0.3, 1 / 30, (w, h), 30))
        im = Image.fromarray(a)
    if crop:
        im = im.crop((int(crop[0] * im.width), int(crop[1] * im.height), int((crop[0] + crop[2]) * im.width), int((crop[1] + crop[3]) * im.height)))
    return im


def _round(im, r, border=0, border_col='#FFFFFF'):
    """PIL 图 → 圆角 RGBA 数组，可带一圈描边。"""
    im = im.convert('RGBA')
    b = int(border)
    c = Image.new('RGBA', (im.width + 2 * b, im.height + 2 * b), hex_rgba(border_col) if b else (0, 0, 0, 0))
    c.paste(im, (b, b))
    m = Image.new('L', c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, c.width - 1, c.height - 1], radius=int(r), fill=255)
    c.putalpha(m)
    return np.array(c)


def card_of(src, w, S, r=18, border=0, border_col='#FFFFFF', crop=None, max_h=None, shadow=True, ratio=None):
    """素材卡：宽 w（max_h 限高）、圆角、可描边、柔投影。ratio 给了先居中裁成这个宽高比。"""
    im = src_image(src, crop) if not isinstance(src, Image.Image) else src
    if ratio:
        if im.width / im.height > ratio:
            nw = int(im.height * ratio)
            im = im.crop(((im.width - nw) // 2, 0, (im.width - nw) // 2 + nw, im.height))
        else:
            nh = int(im.width / ratio)
            im = im.crop((0, (im.height - nh) // 2, im.width, (im.height - nh) // 2 + nh))
    k = w / im.width
    if max_h and im.height * k > max_h:
        k = max_h / im.height
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    a = _round(im, r * S, border, border_col)
    return with_shadow(a, 14 * S, 0.45, dy=int(8 * S)) if shadow else a


def latin(text, font):
    """英文窄体只认拉丁字母和常见符号：混了中文就换回思源黑体，不然渲成方块。"""
    return font if all(c.isascii() or c in '¥€£' for c in str(text)) else HEAVY


def rrect(w, h, r, fill, outline=None, width=0):
    im = Image.new('RGBA', (max(1, int(w)), max(1, int(h))), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([width // 2, width // 2, im.width - 1 - width // 2, im.height - 1 - width // 2], radius=int(r),
                                         fill=hex_rgba(fill) if fill else None, outline=hex_rgba(outline) if outline else None, width=int(width))
    return np.array(im)


def glow(a, r, color='#FFFFFF', k=0.8):
    """给一张 RGBA 加同形外发光（颜色 color）。"""
    g = a.copy()
    g[..., :3] = hex_rgba(color)[:3]
    p = int(r * 2)
    g = np.pad(g, ((p, p), (p, p), (0, 0)))
    g = blur(g, r)
    g[..., 3] = np.clip(g[..., 3].astype(np.float32) * k * 1.6, 0, 255).astype(np.uint8)
    over(g, a, p, p)
    return g


def line_text(text, size, color, font=HEAVY, stroke=0, stroke_color='#000000'):
    return word(text, size, color, font, stroke=stroke, stroke_color=stroke_color) if text else np.zeros((1, 1, 4), np.uint8)


def hl_text(text, hl, size, color, hl_color, font=HEAVY):
    """一行字里 hl 列出的词换色（基线对齐）。"""
    f = ImageFont.truetype(str(font), int(size))
    marks = [0] * len(text)
    for w_ in hl or []:
        i = text.find(w_)
        if i >= 0:
            marks[i:i + len(w_)] = [1] * len(w_)
    pad = int(size * 0.2)
    im = Image.new('RGBA', (int(f.getlength(text)) + 2 * pad, int(size * 1.45) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for ch, m in zip(text, marks):
        d.text((x, pad + size * 1.05), ch, font=f, anchor='ls', fill=hex_rgba(hl_color if m else color))
        x += f.getlength(ch)
    return trim(np.array(im))


def dim_frame(fr, k):
    return (fr.astype(np.float32) * k).astype(np.uint8)


def at_list(t, n, every=0.5, start=0.3):
    """每一项出现的时刻（相对这一段开头）：item_at 里写了就用（None 补均分），否则从 start 起每 every 秒一个。"""
    ia = t.get('item_at') or []
    return [ia[k] if k < len(ia) and ia[k] is not None else start + every * k for k in range(n)]


def active_idx(times, tt):
    k = -1
    for j, a in enumerate(times):
        if tt >= a:
            k = j
    return k


def dashed_circle(D, width, color, dash_deg=8, gap_deg=6, prog=1.0):
    im = Image.new('RGBA', (int(D + 2 * width), int(D + 2 * width)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    a = -90.0
    end = -90 + 360 * prog
    while a < end:
        d.arc([width, width, width + D, width + D], a, min(a + dash_deg, end), fill=hex_rgba(color), width=int(width))
        a += dash_deg + gap_deg
    return np.array(im)


def hand_arrow(w, h, color, width, prog=1.0, seed=3, flip=False):
    """手绘弧形箭头：从左下弯到右上，prog 画出来的比例（箭头最后出现）。"""
    from doodle import _stroke, shapes
    lines = shapes('arrow', w, h, seed)
    im = Image.new('RGBA', (int(w + 2 * width), int(h + 2 * width)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = lines[0]
    n = max(2, int(len(body) * min(1.0, prog / 0.8)))
    pts = [(x + width, y + width) for x, y in body[:n]]
    if len(pts) > 1:
        d.polygon(_stroke(pts, width), fill=hex_rgba(color))
    if prog >= 0.8:
        for seg in lines[1:]:
            d.line([(x + width, y + width) for x, y in seg], fill=hex_rgba(color), width=int(width * 0.8), joint='curve')
    a = np.array(im)
    return a[:, ::-1].copy() if flip else a


def pill(text, size, fg, bg, S, font=HEAVY, padx=0.55, pady=0.28, r=None):
    tx = word(text, size, fg, font)
    w, h = tx.shape[1] + int(size * padx * 2), tx.shape[0] + int(size * pady * 2)
    b = rrect(w, h, r if r is not None else h * 0.3, bg)
    put(b, tx, w / 2, h / 2)
    return b


def emoji(name, d):
    return np.array(Image.open(icon_png(name)).convert('RGBA').resize((int(d), int(d)), Image.LANCZOS))


def _aroll_frames(aroll, t, dur, W, H, FPS):
    return read(aroll, t['t0'], dur, (W, H), FPS)


def _finish(c, tt, dur, fin=0.15, fout=0.18):
    c[..., 3] = (c[..., 3] * min(1.0, tt / fin if fin else 1.0) * fade_out(tt, dur, fout)).astype(np.uint8)
    return c


# ---------------------------------------------------------------- callout 界面截图圈注卡
def _side(W, H, t):
    side = t.get('side') or ('left' if int(t.get('t0', 0)) % 2 else 'right')
    if t.get('side') is None and isinstance(t.get('x'), (int, float)):
        side = 'left' if t['x'] < 0.5 else 'right'
    x0, y0, x1, y1 = safe_zones(W, H)['text'][0 if side == 'left' else 1]
    x0, x1 = max(0.05, x0), min(0.95, x1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # 手写坐标仍按整幅画面的比例算；靠近边缘时收回并给卡片留足宽高。
    if isinstance(t.get('x'), (int, float)):
        cx = max(x0 + (x1 - x0) * 0.35, min(x1 - (x1 - x0) * 0.35, t['x']))
    if isinstance(t.get('y'), (int, float)):
        cy = max(y0 + (y1 - y0) * 0.35, min(y1 - (y1 - y0) * 0.35, t['y']))
    return W * cx, H * cy, W * 2 * min(cx - x0, x1 - cx), H * 2 * min(cy - y0, y1 - cy)


def callout(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    side = t.get('side', 'right')
    cw = W * t.get('w', 0.46)
    if is_landscape(W, H):
        cx, cy, sw, sh = _side(W, H, t)
        cw = min(cw, sw * 0.88)
    raw = card_of(t['src'], cw, S, r=26, crop=t.get('crop'), max_h=H * 0.42, shadow=False)
    inner_h, inner_w = raw.shape[:2]
    card = with_shadow(raw, 14 * S, 0.45, dy=int(8 * S))
    ch_, cw_ = card.shape[:2]
    cx = W * (0.73 if side == 'right' else 0.27)
    cy = H * t.get('y', 0.6)
    fx, fy = t.get('mark', [0.5, 0.5])
    mx, my = cx - inner_w / 2 + inner_w * fx, cy - int(8 * S) / 2 - inner_h / 2 + inner_h * fy
    D = max(W * 0.11, inner_h * 0.25) * t.get('ring', 1.0)
    if is_landscape(W, H):
        cx, cy, sw, sh = _side(W, H, t)
        cy = H * 0.34
        mx, my = cx - inner_w / 2 + inner_w * fx, cy - inner_h / 2 + inner_h * fy
        D = min(inner_w * 0.20, 90 * S) * t.get('ring', 1.0)
        mx = max(cx - sw / 2 + D / 2, min(cx + sw / 2 - D / 2, mx))
        my = max(H * 0.16 + D / 2, min(H * 0.52 - D / 2, my))
    lab = pill(t.get('label', ''), 48 * S, '#111111', t.get('label_bg', '#FFE24A'), S) if t.get('label') else None
    lx = W * (0.5 if side == 'right' else 0.5)
    ly = min(H * 0.86, cy + ch_ / 2 + 190 * S)
    if is_landscape(W, H):
        lx, ly = cx, H * 0.67
        if lab is not None:
            lab = _fit(lab, sw * 0.94)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3, 'out')
        put(c, card, cx + (1 - p) * W * 0.5 * (1 if side == 'right' else -1), cy, p)
        q = ease((tt - 0.3) / 0.35, 'out')
        if q > 0:
            put(c, dashed_circle(D + 4 * S, 8 * S, '#1A1A1A', prog=q), mx, my, 0.55)
            put(c, dashed_circle(D, 5 * S, '#FFFFFF', prog=q), mx, my)
        if lab is not None:
            r = ease((tt - 0.55) / 0.35, 'out')
            if r > 0:
                aw, ah = abs(mx - lx) + 30 * S, abs(ly - lab.shape[0] / 2 - my - D / 2) + 10 * S
                arr = hand_arrow(max(60 * S, aw), max(60 * S, ah), '#FFC72C', 12 * S, r, flip=mx < lx)
                put(c, arr, (mx + lx) / 2, (my + D / 2 + ly - lab.shape[0] / 2) / 2)
                put(c, lab, lx, ly, ease((tt - 0.5) / 0.2))
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- widget 仿界面小组件
WIDGET_VARIANTS = {
    'search': '搜索框打字：黑底白描边圆角搜索框，放大镜图标，关键词逐字打进去，上方章节大字，打完整体压暗切走',
    'sfx': '音效名卡片：仿剪映音效库列表项，深灰圆角条青色描边，音效名、作者和时长、收藏星和加号，随音效弹出、竖向错位叠放',
}


def _magnifier_icon(d, S, color='#FFFFFF'):
    im = Image.new('RGBA', (int(d), int(d)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    r = d * 0.32
    lw = max(2, int(d * 0.1))
    dr.ellipse([d * 0.12, d * 0.12, d * 0.12 + 2 * r, d * 0.12 + 2 * r], outline=hex_rgba(color), width=lw)
    dr.line([(d * 0.12 + 2 * r * 0.85, d * 0.12 + 2 * r * 0.85), (d * 0.9, d * 0.9)], fill=hex_rgba(color), width=int(lw * 1.2))
    return np.array(im)


def _sfx_chip(it, S, W):
    w, h = int(W * 0.6), int(W * 0.13)
    b = rrect(w, h, 14 * S, '#3A3A3A', '#1EC8C8', int(4 * S))
    t1 = word(it.get('name', '音效'), 48 * S, '#FFFFFF', BOLD)
    t2 = word(f"{it.get('author', '剪映音效')}  ·  {it.get('dur', '00:02')}", 30 * S, '#9A9A9A', MED)
    over(b, t1, 30 * S, h * 0.2)
    over(b, t2, 30 * S, h * 0.62)
    star = word('☆', 44 * S, '#DDDDDD', MED)
    plus = word('+', 56 * S, '#FFFFFF', BOLD)
    put(b, star, w - 120 * S, h / 2)
    put(b, plus, w - 50 * S, h / 2)
    return b


def widget(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'search')
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'sfx':
        items = t.get('items') or [{'name': t.get('text', '音效')}]
        items = [x if isinstance(x, dict) else {'name': x} for x in items]
        times = at_list(t, len(items), 0.6, 0.1)
        chips = [_sfx_chip(x, S, W) for x in items]
        if is_landscape(W, H):
            cx, cy, sw, sh = _side(W, H, t)
            chips = [_landscape_sfx(x, sw * 0.94, S) for x in items]
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            first = max(0, active_idx(times, tt) - 2) if is_landscape(W, H) else 0
            for k, (g, a) in enumerate(zip(chips, times)):
                if is_landscape(W, H) and not first <= k < first + 3:
                    continue
                if tt < a:
                    continue
                p = min(1.0, (tt - a) / 0.1)
                put(c, scale(g, 0.6 + 0.4 * p), cx if is_landscape(W, H) else W * 0.36 + 40 * S * k, H * 0.25 + (k - first) * (g.shape[0] + 24 * S) if is_landscape(W, H) else H * t.get('y', 0.64) - k * (g.shape[0] + 18 * S), p)
            w.put(_finish(c, tt, dur, 0.01))
        w.close()
        return
    kw = t.get('text') or t.get('key') or '口播剪辑'
    bw, bh = (int(W * 0.53), int(H * 0.14)) if is_landscape(W, H) else (int(W * 0.78), int(W * 0.14))
    box = rrect(bw, bh, bh * 0.3, '#0D0D0D', '#FFFFFF', int(5 * S))
    over(box, _magnifier_icon(bh * 0.52, S), bh * 0.28, bh * 0.24)
    title = with_shadow(_fit(word(t['title'], 110 * S, '#FFFFFF', HEAVY), W * 0.86), 8 * S, 0.6) if t.get('title') else None
    f = ImageFont.truetype(str(BOLD), int(bh * 0.42))
    t_in = t.get('type_at', 0.35)
    cps = t.get('cps', 6)
    t_done = t_in + len(kw) / cps
    frs = _aroll_frames(aroll, t, dur, W, H, FPS)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        k = min(len(kw), max(0, int((tt - t_in) * cps + 0.999))) if tt >= t_in else 0
        c = np.full((H, W, 4), (18, 20, 24, 255), np.uint8) if is_landscape(W, H) else _opaque(dim_frame(fr, 0.55))
        p = ease(tt / 0.25, 'out')
        b = box.copy()
        im = Image.fromarray(b)
        d = ImageDraw.Draw(im)
        tx = kw[:k]
        x0 = bh * 0.95
        d.text((x0, bh / 2), tx, font=f, anchor='lm', fill=(255, 255, 255, 255))
        if int(tt * 2.5) % 2 == 0 or tt < t_done:   # 光标闪
            cx_ = x0 + f.getlength(tx) + 6 * S
            d.rectangle([cx_, bh * 0.27, cx_ + 4 * S, bh * 0.73], fill=(255, 255, 255, 255))
        b = np.array(im)
        put(c, b, W * (0.65 if is_landscape(W, H) else 0.5), H * t.get('y', 0.45 if is_landscape(W, H) else 0.58), p)
        if title is not None:
            if is_landscape(W, H):
                put(c, _fit(title, W * 0.25), W * 0.20, H * 0.45, ease((tt - 0.05) / 0.3))
            else:
                put(c, title, W / 2, H * t.get('y', 0.58) - bh / 2 - title.shape[0] / 2 - 50 * S, ease((tt - 0.05) / 0.3))
        dimk = ease((tt - t_done - t.get('hold', 0.8)) / 0.3)
        if dimk > 0:
            c[..., :3] = (c[..., :3] * (1 - 0.6 * dimk)).astype(np.uint8)
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- flow 流程节点逐级点亮
def _node(text, w, h, S, active):
    b = rrect(w, h, 10 * S, '#F2EFA0' if active else '#111111', '#C9A646', int(3 * S))
    tx = _fit(word(text, h * 0.42, '#1A1A1A' if active else '#F3EBD2', HEAVY), w * 0.86)
    put(b, tx, w / 2, h / 2)
    return b


def _chevrons(S, color='#C9A646'):
    im = Image.new('RGBA', (int(60 * S), int(60 * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(2):
        y = 10 * S + k * 18 * S
        d.line([(12 * S, y), (30 * S, y + 16 * S), (48 * S, y)], fill=hex_rgba(color), width=int(6 * S), joint='curve')
    return np.array(im)


def flow(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = (t.get('items') or [])[:5]
    times = at_list(t, len(items), max(0.5, (dur - 0.6) / max(1, len(items))), 0.3)
    nw, nh = W * 0.66, H * 0.072
    gap = H * 0.05
    total = len(items) * nh + (len(items) - 1) * gap
    y0 = H * t.get('y', 0.42) - total / 2
    if is_landscape(W, H):
        nw, nh = W * 0.78 / max(1, len(items)) - 40 * S, H * 0.14
        y0 = H * 0.48 - nh / 2
    node = _landscape_node if is_landscape(W, H) else _node
    norm = [node(x, nw, nh, S, False) for x in items]
    act = [node(x, nw, nh, S, True) for x in items]
    chev = _chevrons(S)
    if is_landscape(W, H):
        chev = rotate_rgba(chev, 90)
    title = with_shadow(_fit(word(t['title'], 70 * S, '#F3EBD2', HEAVY), W * 0.8), 6 * S, 0.6) if t.get('title') else None
    frs = _aroll_frames(aroll, t, dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    sq = None
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = np.full((H, W, 4), (18, 20, 24, 255), np.uint8) if is_landscape(W, H) else _opaque(dim_frame(fr, 1 - 0.62 * ease(tt / 0.3)))
        if sq is None:
            sq = _head_square(fr, W, H)
            if is_landscape(W, H):
                sq = _safe_head_square(sq, W, H)
        k = active_idx(times, tt)
        for j in range(len(items)):
            p = ease((tt - 0.1 - 0.08 * j) / 0.3, 'out')
            cy = y0 + nh / 2 + (0 if is_landscape(W, H) else j * (nh + gap))
            cx = W * 0.08 + (j + 0.5) * W * 0.78 / max(1, len(items)) if is_landscape(W, H) else W / 2
            g = act[j] if j == k else norm[j]
            if j == k:
                q = min(1.0, (tt - times[j]) / 0.18)
                g = scale(g, 1.0 + 0.06 * math.sin(q * math.pi))
            put(c, g, cx, cy + (1 - p) * 30 * S, p)
            if j:
                put(c, chev, cx - W * 0.78 / len(items) / 2 if is_landscape(W, H) else W / 2, cy if is_landscape(W, H) else cy - nh / 2 - gap / 2, p)
        if title is not None:
            put(c, title, W / 2, y0 - 90 * S, ease(tt / 0.3))
        av = _avatar(fr, sq, int(H * 0.26) if is_landscape(W, H) else int(W * 0.26), int(5 * S), '#C9A646')
        put(c, av, W * 0.95 - av.shape[1] / 2 if is_landscape(W, H) else W * 0.8, H * 0.05 + av.shape[0] / 2 if is_landscape(W, H) else H * 0.84, ease((tt - 0.15) / 0.3))
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- axis 时间轴区间示意
AXIS_VARIANTS = {
    'two_point': '两点加游标：画面虚化压暗，黄色细线上两个发光菱形，白色竖线游标从左点走到右点',
    'events': '事件标点逐个点亮：米白底黑色时间轴带刻度，说到哪个事件那里变橙红圆点放大带光晕，全部点完上方出勾',
    'year': '年份刻度尺滚动：画面最上方一条细白刻度尺和年份，中间白色小三角，刻度尺缓动滚到目标年份停住',
    'wave': '波形切点卡：白色圆角卡里一段音频波形（起音前灰、起音后橙），黑色竖线标切点，下方「1 帧」刻度',
}


def _diamond(d, color, S):
    im = Image.new('RGBA', (int(d), int(d)), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(d / 2, 0), (d, d / 2), (d / 2, d), (0, d / 2)], fill=hex_rgba(color))
    return glow(np.array(im), 10 * S, color, 0.9)


def _audio(src, t0, dur, sr=8000):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0.0, t0):.3f}', '-t', f'{dur:.3f}', '-i', str(src), '-ac', '1', '-ar', str(sr),
                        '-f', 's16le', '-'], capture_output=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


def axis(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    if is_landscape(W, H) and t.get('variant', 'two_point') != 'two_point':
        return _landscape_axis(t, W, H, FPS, st, work, aroll, out)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'two_point')
    items = t.get('items') or []
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'two_point':
        a_, b_ = (items + ['起点', '终点'])[:2]
        ly = H * t.get('y', 0.46)
        x0, x1 = W * 0.16, W * 0.84
        dm = _diamond(64 * S, '#F2C94C', S)
        la, lb = word(a_, 56 * S, '#FFFFFF', HEAVY), word(b_, 56 * S, '#FFFFFF', HEAVY)
        title = with_shadow(_fit(word(t.get('title', ''), 78 * S, '#FFFFFF', HEAVY), W * 0.8), 6 * S, 0.6) if t.get('title') else None
        times = at_list(t, 2, max(0.6, dur - 1.2), 0.5)
        frs = _aroll_frames(aroll, t, dur, W, H, FPS)
        for i in range(n):
            tt = i / FPS
            fr = next(frs)
            c = _opaque(_soft_bg(fr, W, H, 0.45, 4))
            p = ease(tt / 0.4, 'out')
            im = Image.fromarray(c)
            ImageDraw.Draw(im).line([(x0, ly), (x0 + (x1 - x0) * p, ly)], fill=(212, 167, 44, 255), width=int(5 * S))
            c = np.array(im)
            put(c, dm, x0, ly, ease((tt - 0.1) / 0.2))
            put(c, la, x0, ly + 70 * S, ease((tt - 0.15) / 0.2))
            put(c, dm, x1, ly, ease((tt - 0.35) / 0.2))
            put(c, lb, x1, ly + 70 * S, ease((tt - 0.4) / 0.2))
            if title is not None:
                q = ease((tt - 0.3) / 0.3)
                im = Image.fromarray(c)
                ImageDraw.Draw(im).line([(W * 0.5, ly - 20 * S), (W * 0.5 + 60 * S * q, ly - 160 * S * q)], fill=(212, 167, 44, 255), width=int(3 * S))
                c = np.array(im)
                put(c, title, W * 0.5 + 60 * S, ly - 220 * S, q)
            m = ease((tt - times[0]) / max(0.2, times[1] - times[0]))
            if tt > times[0] - 0.1:
                cx_ = x0 + (x1 - x0) * m
                bar = np.zeros((int(140 * S), int(5 * S), 4), np.uint8)
                bar[...] = 255
                put(c, bar, cx_, ly)
            c[..., 3] = int(255 * min(1.0, tt / 0.15) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    if v == 'events':
        times = at_list(t, len(items), 0.6, 0.4)
        pw, ph = W * 0.92, H * 0.3
        panel = rrect(pw, ph, 24 * S, '#F3EEE4')
        x0, x1 = W * 0.1, W * 0.9
        ly = H * t.get('y', 0.6)
        n_tick = 10
        marks = [x0 + (x1 - x0) * (k + 0.5) / max(1, len(items)) for k in range(len(items))]
        if t.get('pos'):
            marks = [x0 + (x1 - x0) * p_ for p_ in t['pos']]
        names = [word(x, 46 * S, '#1E1714', HEAVY) for x in items]
        note = word('♪', 34 * S, '#FFFFFF', BOLD)
        check = word('✓', 90 * S, '#2BAA5A', HEAVY)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            p = ease(tt / 0.3, 'out')
            put(c, panel, W / 2, ly + 20 * S, p)
            im = Image.fromarray(c)
            d = ImageDraw.Draw(im)
            d.line([(x0, ly), (x0 + (x1 - x0) * ease((tt - 0.1) / 0.3), ly)], fill=(30, 23, 20, 255), width=int(6 * S))
            for k in range(n_tick + 1):
                x = x0 + (x1 - x0) * k / n_tick
                if x <= x0 + (x1 - x0) * ease((tt - 0.1) / 0.3):
                    d.line([(x, ly - 14 * S), (x, ly)], fill=(30, 23, 20, 255), width=int(3 * S))
                    d.text((x, ly - 22 * S), f'{k}s', font=ImageFont.truetype(str(MED), int(28 * S)), anchor='ms', fill=(110, 100, 90, 255))
            c = np.array(im)
            k_ = active_idx(times, tt)
            for j, x in enumerate(marks):
                if tt < times[j]:
                    put(c, rrect(24 * S, 24 * S, 12 * S, '#B8AFA2'), x, ly)
                    continue
                q = min(1.0, (tt - times[j]) / 0.25)
                sc = 1.3 - 0.3 * q if j == k_ else 1.0
                dot = rrect(W * 0.05 * sc, W * 0.05 * sc, W * 0.025 * sc, '#FF4A1C')
                if j == k_:
                    dot = glow(dot, 12 * S, '#FF4A1C', 0.8)
                put(c, dot, x, ly)
                put(c, note, x, ly)
                put(c, names[j], x, ly + 70 * S, q)
            if items and tt > times[-1] + 0.5:
                put(c, check, W / 2, ly - 110 * S, ease((tt - times[-1] - 0.5) / 0.2))
            w.put(_finish(c, tt, dur, 0.01))
        w.close()
        return
    if v == 'year':
        years = [str(x) for x in (items or [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])]
        target = str(t.get('target', years[-1]))
        step = W * 0.18
        band_y = H * t.get('y', 0.09)
        L = int(step * (len(years) + 6))
        ruler = Image.new('RGBA', (L, int(120 * S)), (0, 0, 0, 0))
        d = ImageDraw.Draw(ruler)
        f = ImageFont.truetype(str(latin(''.join(years), OSWALD)), int(36 * S))
        sub = step / 10
        for k in range(int(L / sub)):
            x = k * sub
            big = k % 10 == 0
            d.line([(x, 70 * S), (x, (70 - (18 if big else 9)) * S)], fill=(255, 255, 255, 230), width=int((3 if big else 1.5) * S))
        for j, y in enumerate(years):
            d.text((step * (j + 3), 44 * S), y, font=f, anchor='ms', fill=(255, 255, 255, 255))
        d.line([(0, 70 * S), (L, 70 * S)], fill=(255, 255, 255, 200), width=int(2 * S))
        ruler = np.array(ruler)
        ti = years.index(target) if target in years else len(years) - 1
        xs_end = W / 2 - step * (ti + 3)
        xs_start = xs_end + step * min(5, ti + 1)
        tri = Image.new('RGBA', (int(30 * S), int(22 * S)), (0, 0, 0, 0))
        ImageDraw.Draw(tri).polygon([(0, 22 * S), (30 * S, 22 * S), (15 * S, 0)], fill=(255, 255, 255, 255))
        tri = np.array(tri)
        sd = t.get('scroll', 1.2)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            m = ease((tt - 0.2) / sd, 'inout')
            x = xs_start + (xs_end - xs_start) * m
            over(c, ruler, x, band_y - 60 * S)
            put(c, tri, W / 2, band_y + 24 * S)
            if m >= 1:
                put(c, glow(word(target, 44 * S, '#FFD84A', latin(target, OSWALD)), 8 * S, '#FFD84A', 0.6), W / 2, band_y - 26 * S, ease((tt - 0.2 - sd) / 0.2))
            w.put(_finish(c, tt, dur, 0.2))
        w.close()
        return
    # wave 波形切点卡
    src = t.get('src') or aroll
    a0 = t.get('wave_t', t['t0'])
    wl = t.get('wave_dur', 1.2)
    sig = _audio(src, a0, wl)
    cw_, chh = int(W * 0.86), int(H * 0.2)
    card = rrect(cw_, chh, 24 * S, '#FFFFFF')
    bins = 140
    env = np.array([np.abs(seg).max() if len(seg) else 0 for seg in np.array_split(sig, bins)]) if len(sig) else np.zeros(bins)
    env = env / max(1e-4, env.max())
    thr = 0.25
    onset = next((k for k, e in enumerate(env) if e > thr), bins // 3)
    if t.get('cut_at') is not None:
        onset = int(bins * t['cut_at'] / wl)
    im = Image.fromarray(card)
    d = ImageDraw.Draw(im)
    bx0, bx1 = 40 * S, cw_ - 40 * S
    my = chh * 0.48
    for k, e in enumerate(env):
        x = bx0 + (bx1 - bx0) * k / bins
        hh = max(2 * S, e * chh * 0.36)
        d.line([(x, my - hh), (x, my + hh)], fill=(255, 122, 26, 255) if k >= onset else (138, 138, 138, 255), width=max(2, int(3 * S)))
    card = np.array(im)
    cut_x = bx0 + (bx1 - bx0) * onset / bins
    lab = word('切点', 36 * S, '#111111', HEAVY)
    fr1 = word('1 帧', 26 * S, '#555555', MED)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3, 'out')
        g = card.copy()
        q = ease((tt - 0.35) / 0.3)
        if q > 0:
            im = Image.fromarray(g)
            d = ImageDraw.Draw(im)
            d.line([(cut_x, chh * 0.12), (cut_x, chh * 0.12 + (chh * 0.72) * q)], fill=(0, 0, 0, 255), width=int(5 * S))
            if q >= 1:
                d.line([(cut_x, chh * 0.9), (cut_x + 26 * S, chh * 0.9)], fill=(0, 0, 0, 255), width=int(3 * S))
            g = np.array(im)
            if q >= 1:
                put(g, lab, cut_x, chh * 0.07 + lab.shape[0] / 2)
                over(g, fr1, cut_x + 32 * S, chh * 0.9 - fr1.shape[0] / 2)
        put(c, with_shadow(g, 14 * S, 0.4, dy=int(8 * S)), W / 2, H * t.get('y', 0.64) + (1 - p) * 60 * S, p)
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- stepwall 暗色拼格步骤墙
def _mosaic_cells(k, W, H, seed, top=0.12, bottom=0.88, gap=4):
    """k 个大小不一的格子铺满 [top, bottom] 这段画面：每行 1~2 格，宽度随机分。"""
    rng = random.Random(seed)
    rows = []
    left = k
    while left > 0:
        m = 2 if left >= 2 and (left != 3 or rng.random() < 0.6) else 1
        if left - m == 1 and m == 2 and rng.random() < 0.5:
            m = 1
        rows.append(m)
        left -= m
    hs = [rng.uniform(0.8, 1.25) * (1.15 if m == 1 else 1.0) for m in rows]
    tot = sum(hs)
    y = top * H
    cells = []
    for m, h_ in zip(rows, hs):
        hh = (bottom - top) * H * h_ / tot
        if m == 1:
            cells.append((gap, y + gap, W - 2 * gap, hh - 2 * gap))
        else:
            sp = rng.uniform(0.38, 0.62) * W
            cells.append((gap, y + gap, sp - 1.5 * gap, hh - 2 * gap))
            cells.append((sp + 0.5 * gap, y + gap, W - sp - 1.5 * gap, hh - 2 * gap))
        y += hh
    return cells


def stepwall(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = (t.get('items') or [])[:8]
    cells = _mosaic_cells(len(items), W, H, int(t['t0'] * 10) + len(items), gap=int(5 * S))
    if is_landscape(W, H):
        cols = 3 if len(items) > 4 else 2
        rows = (len(items) + cols - 1) // cols
        cw, ch = W * 0.88 / cols, H * 0.64 / max(1, rows)
        cells = [(int(W * 0.06 + j % cols * cw), int(H * 0.11 + j // cols * ch), int(cw - 10 * S), int(ch - 10 * S)) for j in range(len(items))]
    rng = random.Random(7)
    wall = np.zeros((H, W, 4), np.uint8)
    wall[..., 3] = 255
    wall[..., :3] = 10
    im = Image.fromarray(wall)
    d = ImageDraw.Draw(im)
    for (x, y, cw_, chh), j in zip(cells, range(len(items))):
        g = rng.randint(30, 42)
        d.rectangle([x, y, x + cw_, y + chh], fill=(g, g, g, 255))
    wall = np.array(im)
    nz = np.random.default_rng(3).normal(0, 5, (H, W, 1))
    wall[..., :3] = np.clip(wall[..., :3] + nz, 0, 255).astype(np.uint8)
    labels = []
    for j, ((x, y, cw_, chh), s) in enumerate(zip(cells, items)):
        num = word(f'STEP {j + 1:02d}', min(chh * 0.16, 60 * S), '#C9BC8C', OSWALD)
        nm = _fit(word(s, min(chh * 0.36, cw_ * 0.8 / max(1, len(s)) * 1.1), '#FFFFFF' if j % 3 else '#C9BC8C', HEAVY), cw_ * 0.86, chh * 0.5)
        labels.append((num, nm, x, y, cw_, chh))
    times = at_list(t, len(items), 0.12, 0.1) if not t.get('item_at') else at_list(t, len(items))
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = wall.copy()
        for (num, nm, x, y, cw_, chh), a in zip(labels, times):
            p = ease((tt - a) / 0.3, 'out')
            if p <= 0:
                continue
            over(c, num, x + 30 * S, y + 26 * S, p)
            over(c, nm, x + 30 * S - (1 - p) * 30 * S, y + chh - nm.shape[0] - 30 * S, p)
        z = 1 + (0.015 if is_landscape(W, H) else 0.06) * min(1.0, tt / max(2.0, dur))
        if z > 1.001:
            big = resize(c, W * z, H * z)
            oy, ox = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
            c = big[oy:oy + H, ox:ox + W].copy()
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- reslist 资源清单页
RESLIST_VARIANTS = {
    'paper': '整屏牛皮纸清单：米黄牛皮纸上清单居中竖排，金黄斜体粗字带深色描边，一条一条出现',
    'poster': '侧栏规格海报：左侧三分之一半透明白色说明海报（标题、分类、名单），右侧人旁边黑色大字逐个点名',
}


def reslist(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    if is_landscape(W, H):
        return _landscape_reslist(t, W, H, FPS, st, work, aroll, out)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'paper')
    items = (t.get('items') or [])[:7]
    times = at_list(t, len(items), 0.35, 0.3)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'paper':
        bgp = Path(work) / f'paper_kraft_{W}x{H}.png'
        if not bgp.exists():
            paper_texture(bgp, W, H, 'kraft')
        bg = np.array(Image.open(bgp).convert('RGBA'))
        rows = [text_img(x, 96 * S, '#F3C94D', fontfile=HEAVY, stroke=int(7 * S), stroke_color='#3A2A10', italic=0.18) for x in items]
        rows = [with_shadow(trim(r), 5 * S, 0.35, dy=int(4 * S)) for r in rows]
        title = word(t['title'], 70 * S, '#3A2A10', HEAVY) if t.get('title') else None
        gap = H * 0.085
        y0 = H * 0.46 - gap * (len(rows) - 1) / 2
        for i in range(n):
            tt = i / FPS
            c = bg.copy()
            if title is not None:
                put(c, title, W / 2, y0 - gap * 1.2, ease(tt / 0.3))
            for j, (r, a) in enumerate(zip(rows, times)):
                p = ease((tt - a) / 0.25, 'out')
                if p > 0:
                    put(c, r, W / 2 - (1 - p) * 40 * S, y0 + j * gap, p)
            c[..., 3] = int(255 * min(1.0, tt / 0.15) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    pw = int(W * 0.4)
    panel = np.zeros((H, pw, 4), np.uint8)
    panel[...] = (255, 255, 255, 195)
    head = _fit(word(t.get('title', 'FONT'), 120 * S, '#111111', latin(t.get('title', 'FONT'), OSWALD)), pw - 80 * S)
    over(panel, head, 40 * S, H * 0.14)
    cat = word(t.get('category', '可商用字体'), 50 * S, '#111111', HEAVY)
    over(panel, cat, 40 * S, H * 0.14 + head.shape[0] + 30 * S)
    for j, x in enumerate(items):
        over(panel, _fit(word(x, 46 * S, '#333333', BOLD), pw - 80 * S), 40 * S, H * 0.33 + j * 80 * S)
    if t.get('note'):
        over(panel, word(t['note'], 36 * S, '#C4161C', BOLD), 40 * S, H * 0.33 + len(items) * 80 * S + 30 * S)
    bigs = [with_shadow(_fit(word(x, 110 * S, '#111111', HEAVY, stroke=int(5 * S), stroke_color='#FFFFFF'), W * 0.56), 8 * S, 0.4) for x in items]
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3, 'out')
        over(c, panel, -pw * (1 - p), 0, p)
        k = active_idx(times, tt)
        if k >= 0:
            q = ease((tt - times[k]) / 0.2, 'out')
            put(c, bigs[k], W * 0.7, H * 0.56 + (1 - q) * 30 * S, q)
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- typerow 竖卡一排类型展示
TYPEROW_VARIANTS = {
    'screenshot': '截图竖卡排开：整屏白底，竖版截图卡依次出现，类型名和拼音上下交错标在卡旁',
    'wireframe': '构图线框卡：一排灰白线框小卡依次滑入，再放大成单张：带人形剪影的线框卡，两侧灰色巨字',
}
WIRE_KINDS = ('topbottom', 'corners', 'center', 'leftright', 'diagonal')


def _wire_card(kind, w, h, S, big=False):
    im = Image.new('RGBA', (int(w), int(h)), (248, 248, 246, 255))
    d = ImageDraw.Draw(im)
    lw = max(1, int(2 * S))
    for k in (1, 2):
        d.line([(w * k / 3, 0), (w * k / 3, h)], fill=(187, 187, 187, 255), width=lw)
        d.line([(0, h * k / 3), (w, h * k / 3)], fill=(187, 187, 187, 255), width=lw)
    g = (136, 136, 136, 255)
    def person(cx, cy, s):
        d.ellipse([cx - s * 0.18, cy - s * 0.62, cx + s * 0.18, cy - s * 0.26], fill=g)
        d.polygon([(cx - s * 0.36, cy + s * 0.4), (cx - s * 0.2, cy - s * 0.2), (cx + s * 0.2, cy - s * 0.2), (cx + s * 0.36, cy + s * 0.4)], fill=g)
    def bar(x, y, bw, bh):
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=bh / 2, fill=(60, 60, 60, 255))
    s = min(w, h) * 0.5
    if kind == 'topbottom':
        bar(w * 0.2, h * 0.1, w * 0.6, h * 0.05); person(w / 2, h * 0.62, s); bar(w * 0.25, h * 0.86, w * 0.5, h * 0.04)
    elif kind == 'corners':
        for x, y in ((0.08, 0.08), (0.62, 0.08), (0.08, 0.88), (0.62, 0.88)):
            bar(w * x, h * y, w * 0.3, h * 0.04)
        person(w / 2, h * 0.58, s)
    elif kind == 'center':
        person(w / 2, h * 0.6, s * 0.9); bar(w * 0.22, h * 0.42, w * 0.56, h * 0.06)
    elif kind == 'leftright':
        person(w * 0.66, h * 0.62, s); [bar(w * 0.06, h * (0.4 + 0.08 * k), w * 0.32, h * 0.035) for k in range(3)]
    else:
        person(w * 0.6, h * 0.64, s); bar(w * 0.06, h * 0.1, w * 0.5, h * 0.05); bar(w * 0.44, h * 0.88, w * 0.5, h * 0.04)
    d.rectangle([0, 0, w - 1, h - 1], outline=(170, 170, 170, 255), width=lw)
    return with_shadow(np.array(im), 8 * S, 0.25, dy=int(4 * S))


def typerow(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'screenshot')
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'screenshot':
        srcs = (t.get('srcs') or [])[:5]
        labels = (t.get('items') or [''] * len(srcs))[:len(srcs)]
        py = t.get('pinyin') or []
        k = len(srcs)
        cw = W * min(0.24, 0.9 / k * 0.9)
        if is_landscape(W, H):
            cw = min(cw, H * 0.44 * 9 / 16)
        cards = [card_of(s, cw, S, r=16, ratio=9 / 16) for s in srcs]
        times = at_list(t, k, 0.75, 0.2)
        gapx = W * 0.92 / k
        xs = [W * 0.04 + gapx * (j + 0.5) for j in range(k)]
        cy = H * 0.44
        for i in range(n):
            tt = i / FPS
            c = np.full((H, W, 4), 255, np.uint8)
            for j, (g, a) in enumerate(zip(cards, times)):
                p = ease((tt - a) / 0.25, 'out')
                if p <= 0:
                    continue
                put(c, g, xs[j] - (1 - p) * W * 0.3 * (j == 0), cy, p if j else 1.0 if p > 0 else 0)
                up = j % 2 == 1
                lab = word(labels[j], 60 * S, '#111111', HEAVY)
                ly = cy + (-1 if up else 1) * (g.shape[0] / 2 + 60 * S)
                if is_landscape(W, H):
                    lab = _fit(lab, gapx * 0.80)
                    ly = cy + (-1 if up else 1) * (g.shape[0] / 2 + 45 * S)
                put(c, lab, xs[j], ly, p)
                if j < len(py) and py[j]:
                    put(c, word(py[j], 28 * S, '#888888', MED), xs[j], ly + (lab.shape[0] / 2 + 22 * S) * (1 if not up else -1), p)
            c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    kinds = (t.get('kinds') or list(WIRE_KINDS))[:5]
    names = dict(zip(WIRE_KINDS, ['上下', '四角', '居中', '左右', '对角']))
    labels = t['items'][:len(kinds)] if len(t.get('items') or []) >= len(kinds) else [names.get(k, k) for k in kinds]
    sw, sh = W * 0.17, H * 0.17
    smalls = [_wire_card(kd, sw, sh, S) for kd in kinds]
    fi = t.get('focus', 0)
    bigc = _wire_card(kinds[fi], W * 0.44, H * 0.48, S, True)
    zoom_at = t.get('zoom_at', min(dur * 0.55, 0.3 + 0.2 * len(kinds) + 0.8))
    gl = t.get('giant') or labels[fi]
    giant_l = word(gl[:1], H * 0.2, '#D8D8D8', HEAVY)
    giant_r = word(gl[1:2] or gl[:1], H * 0.2, '#BFB48A', HEAVY)
    note = word(t.get('note', ''), 40 * S, '#111111', BOLD) if t.get('note') else None
    gap = W * 0.19
    xs = [W / 2 + (j - (len(kinds) - 1) / 2) * gap for j in range(len(kinds))]
    for i in range(n):
        tt = i / FPS
        c = np.full((H, W, 4), 255, np.uint8)
        z = ease((tt - zoom_at) / 0.3, 'out')
        if z < 1:
            for j, g in enumerate(smalls):
                p = ease((tt - 0.2 - 0.2 * j) / 0.25, 'out')
                if p <= 0:
                    continue
                put(c, g, xs[j] + (1 - p) * W * 0.6, H * 0.44, p * (1 - z))
                put(c, word(labels[j], 34 * S, '#333333', HEAVY), xs[j] + (1 - p) * W * 0.6, H * 0.44 + sh / 2 + 40 * S, p * (1 - z))
        if z > 0:
            put(c, giant_l, W * 0.13, H * 0.44, z)
            put(c, giant_r, W * 0.87, H * 0.44, z)
            put(c, scale(bigc, 0.4 + 0.6 * z), xs[fi] + (W / 2 - xs[fi]) * z, H * 0.44, z)
            if note is not None:
                put(c, note, W / 2, H * 0.44 + bigc.shape[0] / 2 + 50 * S, z)
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- photostack 并列图片卡错落
PHOTOSTACK_VARIANTS = {
    'tab': '彩色折角阶梯卡：背景虚化，三张圆角图片卡从上往下阶梯排列、左右交替错位，外侧带橙蓝绿三角折角，从同侧滑入',
    'tilted': '倾斜白边照片卡：人推到画面右侧，左侧三张白边照片卡带不同倾斜，自上而下错落弹入',
}
TAB_COLORS = ['#F5A000', '#3A8DE0', '#22D27A']


def photostack(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    if is_landscape(W, H):
        return _landscape_photostack(t, W, H, FPS, st, work, aroll, out)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'tab')
    srcs = (t.get('srcs') or [])[:3]
    labels = (t.get('items') or [''] * len(srcs))[:len(srcs)]
    times = at_list(t, len(srcs), 0.5, 0.25)
    frs = _aroll_frames(aroll, t, dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'tab':
        cards = []
        for j, (s, lb) in enumerate(zip(srcs, labels)):
            g = card_of(s, W * 0.64, S, r=20, ratio=0.64 / 0.16 * W / H, shadow=False)
            tab = Image.new('RGBA', (int(70 * S), int(70 * S)), (0, 0, 0, 0))
            ImageDraw.Draw(tab).polygon([(0, 0), (70 * S, 0), (0, 70 * S)], fill=hex_rgba(TAB_COLORS[j % 3]))
            tab = np.array(tab)
            if j % 2:
                tab = tab[:, ::-1].copy()
                over(g, tab, g.shape[1] - tab.shape[1], 0)
            else:
                over(g, tab, 0, 0)
            put(g, word(lb, 64 * S, '#111111', HEAVY, stroke=int(6 * S), stroke_color='#FFFFFF'), g.shape[1] / 2, g.shape[0] / 2)
            cards.append(with_shadow(g, 12 * S, 0.45, dy=int(6 * S)))
        for i in range(n):
            tt = i / FPS
            fr = next(frs)
            c = _opaque(_soft_bg(fr, W, H, 0.6, 4))
            for j, (g, a) in enumerate(zip(cards, times)):
                p = ease((tt - a) / 0.2, 'out')
                if p <= 0:
                    continue
                x = W / 2 + (-1 if j % 2 == 0 else 1) * W * 0.08
                y = H * 0.3 + j * (g.shape[0] + H * 0.02)
                put(c, g, x - (1 - p) * W, y, p)
            c[..., 3] = int(255 * min(1.0, tt / 0.15) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    tilts = [-3, 4, -6]
    cards = []
    for j, (s, lb) in enumerate(zip(srcs, labels)):
        g = card_of(s, W * 0.5, S, r=4, border=int(16 * S), ratio=4 / 3, shadow=False)
        put(g, word(lb, 58 * S, '#FFFFFF', HEAVY, stroke=int(6 * S), stroke_color='#111111'), g.shape[1] / 2, g.shape[0] * 0.82)
        cards.append(with_shadow(rotate_rgba(g, -tilts[j % 3]), 12 * S, 0.45, dy=int(6 * S)))
    shift = W * 0.2
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        p0 = ease(tt / 0.3, 'out')
        bg = _soft_bg(fr, W, H, 0.7, 4)
        c = _opaque(bg)
        dx = int(shift * p0)
        if dx:
            c[:, dx:, :3] = fr[:, :W - dx]
            c[:, :dx, :3] = bg[:, :dx]
        else:
            c[..., :3] = fr
        for j, (g, a) in enumerate(zip(cards, times)):
            p = (tt - a) / 0.2
            if p <= 0:
                continue
            put(c, scale(g, _pop(min(1.0, p))), W * 0.3 + (j % 2) * W * 0.06, H * 0.42 + j * H * 0.17, min(1.0, p * 2))
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- comments 评论气泡堆
COMMENT_VARIANTS = {
    'behind': '身后评论墙：几张倾斜白色评论卡（头像、问题、红心点赞数）错落浮在头两侧和上方，压在抠像人物身后，逐张渐显',
    'pileup': '差评气泡堆满：带小头像的白色气泡 0.1 秒一条随机位置弹出，大小不一层层叠压',
}
FACES = ['Grinning face', 'Thinking face', 'Face with rolling eyes', 'Neutral face', 'Smirking face', 'Pensive face', 'Confused face',
         'Face with open mouth']


def _comment_card(it, S, W, k):
    text = it.get('text', '')
    rows = _wrap(text, HEAVY, 42 * S, W * 0.36)[:3]
    tw = max(int(ImageFont.truetype(str(HEAVY), int(42 * S)).getlength(r)) for r in rows) if rows else 100
    cw, chh = int(tw + 160 * S), int(len(rows) * 58 * S + 96 * S)
    b = rrect(cw, chh, 20 * S, '#FFFFFF')
    av = emoji(FACES[k % len(FACES)], 60 * S)
    over(b, av, 20 * S, 18 * S)
    over(b, word(it.get('name', f'网友{k + 1:02d}'), 24 * S, '#8A8A8A', MED), 92 * S, 22 * S)
    for j, r in enumerate(rows):
        over(b, word(r, 42 * S, '#111111', HEAVY), 92 * S, 56 * S + j * 58 * S)
    lk = word(f"♥ {it.get('likes', random.Random(k).choice(['1.2w', '3896', '826', '2.4w']))}", 24 * S, '#FE2C55', BOLD)
    over(b, lk, cw - lk.shape[1] - 22 * S, chh - lk.shape[0] - 14 * S)
    return b


def _bubble(text, S, k):
    tx = word(text, 34 * S, '#222222', HEAVY)
    av = emoji(FACES[k % len(FACES)], 50 * S)
    w_, h_ = int(tx.shape[1] + av.shape[1] + 60 * S), int(max(tx.shape[0], av.shape[0]) + 26 * S)
    b = rrect(w_, h_, h_ / 2, '#FFFFFF')
    over(b, av, 14 * S, (h_ - av.shape[0]) / 2)
    over(b, tx, av.shape[1] + 28 * S, (h_ - tx.shape[0]) / 2)
    return with_shadow(b, 8 * S, 0.35, dy=int(4 * S))


def comments(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    if is_landscape(W, H):
        return _landscape_comments(t, W, H, FPS, st, work, aroll, out)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'behind')
    items = [x if isinstance(x, dict) else {'text': x} for x in (t.get('items') or [])]
    rng = random.Random(int(t['t0'] * 100) + 5)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'pileup':
        bubs = [_bubble(x['text'], S, k) for k, x in enumerate(items[:8])]
        pos = [(rng.uniform(0.28, 0.72) * W, rng.uniform(0.18, 0.78) * H, rng.uniform(0.85, 1.3)) for _ in bubs]
        times = at_list(t, len(bubs), 0.1, 0.15) if not t.get('item_at') else at_list(t, len(bubs))
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            for g, (x, y, s), a in zip(bubs, pos, times):
                p = (tt - a) / 0.15
                if p > 0:
                    put(c, scale(g, s * _pop(min(1.0, p))), x, y, min(1.0, p * 2))
            w.put(_finish(c, tt, dur, 0.01))
        w.close()
        return
    cards = [with_shadow(rotate_rgba(_comment_card(x, S, W, k), rng.uniform(6, 12) * (1 if k % 2 else -1)), 10 * S, 0.5, dy=int(10 * S))
             for k, x in enumerate(items[:5])]
    slots = [(0.25, 0.15), (0.75, 0.19), (0.22, 0.36), (0.78, 0.4), (0.5, 0.06)]
    times = at_list(t, len(cards), 0.15, 0.1) if not t.get('item_at') else at_list(t, len(cards))
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for g, (sx, sy), at_ in zip(cards, slots, times):
            p = ease((tt - at_) / 0.3)
            if p > 0:
                put(c, scale(g, 0.92), W * sx, H * sy + (1 - p) * 20 * S, p)
        from bigtype import _mask_out
        _mask_out(c, a)
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- fanwin 头后三窗口扇形展开
def fanwin(t, W, H, FPS, st, work, aroll, out):
    import matte
    from bigtype import _mask_out
    S = unit(W, H)
    dur, n = frames(t, FPS)
    srcs = (t.get('srcs') or [])[:3]
    while len(srcs) < 3 and srcs:
        srcs.append(srcs[len(srcs) % len(srcs)])
    col = t.get('stroke', '#FFFFFF')
    center = card_of(srcs[0], W * 0.27, S, r=0.06 * W * 0.27 / S, border=int(3 * S), border_col=col, ratio=9 / 16)
    sides = [card_of(s, W * 0.23, S, r=0.06 * W * 0.23 / S, border=int(3 * S), border_col=col, ratio=9 / 16) for s in srcs[1:3]]
    cy = H * t.get('y', 0.2)
    if is_landscape(W, H):
        center = _fit(center, W * 0.20, H * 0.25)
        sides = [_fit(g, W * 0.20, H * 0.25) for g in sides]
        cy = H * 0.30
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p0 = ease(tt / 0.3, 'out')
        q = ease((tt - 0.35) / 0.4, 'out')
        for k, g in enumerate(sides):
            sg = -1 if k == 0 else 1
            gg = rotate_rgba(g, -sg * 8 * q)
            put(c, gg, W * (0.17 if k == 0 else 0.83) if is_landscape(W, H) else W / 2 + sg * W * 0.22 * q, H * (0.30 if k == 0 else 0.57) if is_landscape(W, H) else cy + 20 * S * q, q * 0.98)
        put(c, scale(center, 0.7 + 0.3 * p0), W * 0.83 if is_landscape(W, H) else W / 2, cy, p0)
        _mask_out(c, a)
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- ticker 黑底发光播报框
def ticker(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    bw, bh = int(W * 0.84), int(H * 0.46)
    if is_landscape(W, H):
        cx, cy, sw, sh = _side(W, H, t)
        bw, bh = int(sw * 0.90), int(sh * 0.90)
    pad = int(30 * S)
    title = None
    if t.get('title'):
        ft = ImageFont.truetype(str(HEAVY), int(56 * S))
        rows = _wrap(t['title'], HEAVY, 56 * S, bw - 2 * pad)[:2]
        tim = Image.new('RGBA', (bw - 2 * pad, int(len(rows) * 80 * S + 10 * S)), (0, 0, 0, 0))
        d = ImageDraw.Draw(tim)
        for j, r in enumerate(rows):
            x = 0
            y = j * 80 * S + 66 * S
            for ch_ in r:
                lw = ft.getlength(ch_)
                d.text((x, y), ch_, font=ft, anchor='ls', fill=(255, 255, 255, 255))
                x += lw
            for h in t.get('hl') or []:
                i0 = r.find(h)
                if i0 >= 0:
                    x0 = ft.getlength(r[:i0])
                    x1 = x0 + ft.getlength(h)
                    d.rectangle([x0 - 4 * S, y - 60 * S, x1 + 4 * S, y + 12 * S], fill=(255, 255, 255, 255))
                    d.text((x0, y), h, font=ft, anchor='ls', fill=(0, 0, 0, 255))
        title = np.array(tim)
    body_top = pad + (title.shape[0] + 20 * S if title is not None else 0)
    body_h = int(bh - body_top - pad)
    if t.get('src'):
        im = src_image(t['src'], t.get('crop')).convert('L')
        im = Image.eval(im, lambda x: 255 - x)
        k = (bw - 2 * pad) / im.width
        im = im.resize((bw - 2 * pad, int(im.height * k)), Image.LANCZOS)
        body = np.array(im.convert('RGBA'))
    else:
        f = ImageFont.truetype(str(MED), int(38 * S))
        rows = [r for p_ in (t.get('lines') or ['']) for r in _wrap(p_, MED, 38 * S, bw - 2 * pad)]
        im = Image.new('RGBA', (bw - 2 * pad, max(body_h, int(len(rows) * 58 * S + body_h))), (0, 0, 0, 255))
        d = ImageDraw.Draw(im)
        for j, r in enumerate(rows):
            d.text((0, body_h * 0.6 + j * 58 * S), r, font=f, fill=(235, 235, 235, 255))
        body = np.array(im)
    frame = rrect(bw, bh, 18 * S, '#000000', '#FFFFFF', int(3 * S))
    frame = glow(frame, 12 * S, '#FFFFFF', 0.5)
    fp = (frame.shape[1] - bw) // 2
    speed = H * t.get('speed', 0.03)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        g = frame.copy()
        if title is not None:
            over(g, title, fp + pad, fp + pad)
        off = int(min(max(0, body.shape[0] - body_h), tt * speed))
        win = body[off:off + body_h]
        over(g, win, fp + pad, fp + body_top)
        p = ease(tt / 0.3, 'out')
        put(c, scale(g, 0.94 + 0.06 * p), cx if is_landscape(W, H) else W / 2, cy if is_landscape(W, H) else H * t.get('y', 0.42), p)
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- quotetype 压暗底引文逐行打出
def quotetype(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    lines = list(t.get('lines') or [t.get('text', '')])
    if is_landscape(W, H):
        lines = [r for line in lines for r in _wrap(line, SERIF, 60 * S, W * 0.65)]
    else:
        lines = list(t.get('lines') or _wrap(t.get('text', ''), SERIF, 66 * S, W * 0.82))
    lines = lines[:5]
    if lines:
        lines[0] = '「' + lines[0].lstrip('「')
        lines[-1] = lines[-1].rstrip('」') + '」'
    times = at_list(t, len(lines), 1.5, 0.35)
    f = ImageFont.truetype(str(SERIF), int(66 * S))
    lh = 104 * S
    y0 = H * t.get('y', 0.2)
    by = word(f"—— {t['by']}", 42 * S, '#D9D2C3', SERIF) if t.get('by') else None
    frs = _aroll_frames(aroll, t, dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    sq = None
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        if sq is None:
            sq = _head_square(fr, W, H)
            if is_landscape(W, H):
                sq = _safe_head_square(sq, W, H)
        p = ease(tt / 0.3)
        c = _opaque(_soft_bg(fr, W, H, 0.35, 8)) if is_landscape(W, H) else _opaque(dim_frame(fr, 1 - 0.6 * p))
        im = Image.fromarray(c)
        d = ImageDraw.Draw(im)
        for j, (ln, a) in enumerate(zip(lines, times)):
            if tt < a:
                break
            k = min(len(ln), int((tt - a) / max(0.05, 1.3 / max(1, len(ln))) + 1))
            d.text((W * 0.09, y0 + j * lh), ln[:k], font=f, fill=(255, 255, 255, 255))
        c = np.array(im)
        if by is not None and lines and tt > times[-1] + 1.0:
            over(c, by, W * (0.74 if is_landscape(W, H) else 0.91) - by.shape[1], y0 + len(lines) * lh + 30 * S, ease((tt - times[-1] - 1.0) / 0.3))
        D = int(H * 0.26) if is_landscape(W, H) else int(W * 0.3)
        av = _avatar(fr, sq, D, int(5 * S), '#E8D9A8')
        put(c, av, W * 0.95 - av.shape[1] / 2 if is_landscape(W, H) else W * 0.5 + (W * 0.2 - W * 0.5) * p, H * 0.05 + av.shape[0] / 2 if is_landscape(W, H) else H * 0.72 + (0.0) * p, p)
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- labelcol 纸页左标签右内容卡
def labelcol(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = [x if isinstance(x, dict) else {'label': x} for x in (t.get('items') or [])][:4]
    times = at_list(t, len(items), max(0.6, (dur - 0.4) / max(1, len(items))), 0.2)
    bgp = Path(work) / f'paper_kraft_{W}x{H}.png'
    if not bgp.exists():
        paper_texture(bgp, W, H, 'kraft')
    bg = np.array(Image.open(bgp).convert('RGBA'))
    labs = []
    for x in items:
        lb = word(x['label'], 68 * S, '#B3121A', HEAVY)
        if is_landscape(W, H):
            lb = _fit(lb, W * 0.27)
        en = word(x.get('en', ''), 28 * S, '#5A3B22', MED) if x.get('en') else None
        labs.append((lb, en))
    cards = [card_of(x['src'], W * 0.58, S, r=30, max_h=H * 0.5) if x.get('src') else None for x in items]
    ly0 = H * (0.18 if is_landscape(W, H) else 0.36)
    lgap = (H * (0.60 if is_landscape(W, H) else 0.4)) / max(1, len(items))
    cx, cy = W * 0.67, H * (0.43 if is_landscape(W, H) else 0.48)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = bg.copy()
        k = max(0, active_idx(times, tt))
        for j, (lb, en) in enumerate(labs):
            y = ly0 + j * lgap
            op = 1.0 if j == k else 0.32
            p = ease((tt - 0.1 - 0.08 * j) / 0.25)
            over(c, lb, W * 0.04, y, op * p)
            if en is not None:
                over(c, en, W * 0.04, y + lb.shape[0] + 6 * S, op * p)
        g = cards[k] if k < len(cards) else None
        if g is not None:
            q = ease((tt - times[k]) / 0.25, 'out') if k else ease(tt / 0.3, 'out')
            put(c, g, cx, cy, q)
            ly = ly0 + k * lgap + labs[k][0].shape[0] / 2
            line = np.zeros((int(3 * S), int(W * 0.08), 4), np.uint8)
            line[...] = 255
            over(c, line, W * 0.04 + labs[k][0].shape[1] + 14 * S, ly, q)
        c[..., 3] = int(255 * min(1.0, tt / 0.15) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- person 人物信息卡
PERSON_VARIANTS = {
    'profile': '博主主页信息条：白色圆角卡，左圆头像，中间名字、粉丝数、认证，右边红色「关注」，从小放大弹入画面下三分之一',
    'nameplate': '自我介绍名片：金色渐变发光的名字加几行黄色头衔，停三秒左右',
}


def _gold(text, size, S, font=HEAVY):
    a = word(text, size, '#FFFFFF', font, stroke=int(3 * S), stroke_color='#3A2400')
    h = a.shape[0]
    grad = np.linspace(0, 1, h)[:, None]
    top, mid, bot = np.array([255, 241, 180]), np.array([240, 190, 70]), np.array([170, 110, 20])
    col = np.where(grad < 0.5, top + (mid - top) * grad * 2, mid + (bot - mid) * (grad - 0.5) * 2)
    inner = a[..., 0] > 128
    a[..., :3] = np.where(inner[..., None], col[:, None, :].repeat(a.shape[1], 1), a[..., :3]).astype(np.uint8)
    ext = np.zeros_like(a)
    ext[..., :3] = (120, 70, 10)
    ext[..., 3] = a[..., 3]
    out_ = np.zeros((a.shape[0] + int(8 * S), a.shape[1] + int(8 * S), 4), np.uint8)
    over(out_, ext, int(6 * S), int(6 * S))
    over(out_, a, 0, 0)
    return glow(out_, 14 * S, '#FFD36A', 0.55)


def person(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return _landscape_person(t, W, H, FPS, st, work, aroll, out)
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'profile')
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'nameplate':
        nm = _gold(t.get('name', t.get('text', '')), 120 * S, S)
        titles = [word(x, 56 * S, '#FFE24A', HEAVY, stroke=int(3 * S), stroke_color='#2A1A00') for x in (t.get('titles') or [])[:3]]
        y = H * t.get('y', 0.68)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            p = ease(tt / 0.35, 'out')
            put(c, scale(nm, 0.85 + 0.15 * p), W / 2, y, p)
            for j, g in enumerate(titles):
                q = ease((tt - 0.3 - 0.15 * j) / 0.25, 'out')
                put(c, g, W / 2, y + nm.shape[0] / 2 + 46 * S + j * 76 * S + (1 - q) * 16 * S, q)
            w.put(_finish(c, tt, dur, 0.01))
        w.close()
        return
    cw, chh = int(W * 0.8), int(H * 0.088)
    b = rrect(cw, chh, 12 * S, '#FFFFFF')
    D = int(chh * 0.74)
    if t.get('avatar'):
        im = src_image(t['avatar']).convert('RGB')
        s_ = min(im.size)
        im = im.crop(((im.width - s_) // 2, (im.height - s_) // 2, (im.width + s_) // 2, (im.height + s_) // 2)).resize((D, D), Image.LANCZOS)
        av = _round(im, D / 2)
    else:
        fr = next(read(aroll, t['t0'] + 0.2, 1 / FPS, (W, H), FPS))
        av = _avatar(fr, _head_square(fr, W, H), D)
    over(b, av, chh * 0.13, (chh - D) / 2)
    nm = word(t.get('name', '某某博主'), 46 * S, '#111111', HEAVY)
    x0 = chh * 0.13 + D + 24 * S
    over(b, nm, x0, chh * 0.16)
    if t.get('verified', True):
        put(b, rrect(30 * S, 30 * S, 15 * S, '#25A4F5'), x0 + nm.shape[1] + 26 * S, chh * 0.16 + nm.shape[0] / 2)
        put(b, word('✓', 20 * S, '#FFFFFF', BOLD), x0 + nm.shape[1] + 26 * S, chh * 0.16 + nm.shape[0] / 2)
    over(b, word(t.get('fans', '粉丝 128.6w'), 26 * S, '#7A7A7A', MED), x0, chh * 0.6)
    btn = pill(t.get('button', '关注'), 32 * S, '#FFFFFF', '#FE2C55', S, BOLD, 0.9, 0.35, r=8 * S)
    put(b, btn, cw - btn.shape[1] / 2 - 26 * S, chh / 2)
    b = with_shadow(b, 12 * S, 0.4, dy=int(6 * S))
    y = H * t.get('y', 0.7)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        p = ease(tt / 0.3, 'out')
        put(c, scale(b, 0.6 + 0.4 * eback(min(1.0, tt / 0.3))), W / 2, y, p)
        w.put(_finish(c, tt, dur, 0.01))
    w.close()


# ---------------------------------------------------------------- products 压暗叠商品卡
def _stripes(W, H, S):
    yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx + yy) // int(18 * S)) % 2 == 0
    a = np.zeros((H, W, 4), np.uint8)
    a[..., 3] = (m * 76).astype(np.uint8)
    return a


def products(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = [x if isinstance(x, dict) else {'name': x} for x in (t.get('items') or [])][:3]
    times = at_list(t, len(items), 0.5, 0.3)
    stripes = _stripes(W, H, S)
    cw, chh = (int(W * 0.27), int(H * 0.20)) if is_landscape(W, H) else (int(W * 0.85), int(H * 0.12))
    cards = []
    for x in items:
        b = rrect(cw, chh, cw * 0.04, '#F5F5F5')
        if x.get('src'):
            pic = card_of(x['src'], chh * 0.82, S, r=12, ratio=1.0, shadow=False)
            over(b, pic, chh * 0.09, chh * 0.09)
        else:
            over(b, emoji(x.get('icon', 'Package'), chh * 0.8), chh * 0.1, chh * 0.1)
        over(b, _fit(word(x.get('name', ''), 44 * S, '#111111', HEAVY), cw * 0.42), chh * 1.0, chh * 0.18)
        over(b, word(x.get('price', ''), 60 * S, '#E8341C', HEAVY), chh * 1.0, chh * 0.5)
        btn = pill(x.get('button', '购买'), 38 * S, '#FFFFFF', '#2F8BFF', S, BOLD, 0.9, 0.35, r=10 * S)
        put(b, btn, cw - btn.shape[1] / 2 - 30 * S, chh / 2)
        if is_landscape(W, H):
            b = rrect(cw, chh, 18 * S, '#F5F5F5')
            over(b, _fit(word(x.get('name', ''), 40 * S, '#111111', HEAVY), cw * 0.88), 24 * S, 28 * S)
            over(b, word(x.get('price', ''), 64 * S, '#E8341C', HEAVY), 24 * S, chh * 0.52)
            put(b, pill(x.get('button', '购买'), 28 * S, '#FFFFFF', '#2F8BFF', S), cw * 0.81, chh * 0.72)
        cards.append(with_shadow(b, 12 * S, 0.45, dy=int(6 * S)))
    ys = [0.75, 0.55, 0.35]
    frs = _aroll_frames(aroll, t, dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        p = ease(tt / 0.3)
        c = np.full((H, W, 4), (22, 24, 28, 255), np.uint8) if is_landscape(W, H) else _opaque(dim_frame(fr, 1 - 0.55 * p))
        over(c, stripes, 0, 0, p)
        for j, (g, a) in enumerate(zip(cards, times)):
            q = (tt - a) / 0.25
            if q <= 0:
                continue
            put(c, g, W * (0.20 + j * 0.30) if is_landscape(W, H) else W / 2, H * 0.46 + (1 - eback(min(1.0, q))) * H * 0.08 if is_landscape(W, H) else H * ys[j] + (1 - eback(min(1.0, q))) * H * 0.08, min(1.0, q * 2))
        c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- translate 外文原文配中文翻译条
def translate(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    im = src_image(t['src'], t.get('crop'))
    k = W * 0.94 / im.width
    if im.height * k > H * 0.62:
        k = H * 0.62 / im.height
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    doc = np.array(im.convert('RGBA'))
    bx, by_, bw, bh = t.get('line', [0.05, 0.45, 0.9, 0.06])
    x0, y0, x1, y1 = int(bx * doc.shape[1]), int(by_ * doc.shape[0]), int((bx + bw) * doc.shape[1]), int((by_ + bh) * doc.shape[0])
    inv = doc.copy()
    inv[y0:y1, x0:x1, :3] = 255 - inv[y0:y1, x0:x1, :3]
    vig = np.zeros((H, W, 4), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W * 0.62), (yy - H / 2) / (H * 0.55))
    vig[..., :3] = 60
    vig[..., 3] = (np.clip((r - 0.55) / 0.6, 0, 1) * 200).astype(np.uint8)
    text = t.get('text', '')
    rows = _wrap(text, HEAVY, 0.03 * H, W * 0.76)[:2]
    bar_w, bar_h = int(W * 0.88), int(H * 0.05 * max(1, len(rows)) + 14 * S)
    bar = rrect(bar_w, bar_h, min(bar_h * 0.4, 40 * S), '#111111E6')
    for j, r_ in enumerate(rows):
        put(bar, hl_text(r_, t.get('hl'), 0.028 * H, '#FFFFFF', '#F7D33C'), bar_w / 2, bar_h * (j + 0.5) / len(rows))
    t_hl = t.get('hl_at', 0.3)
    t_bar = t.get('bar_at', t_hl + 1.0)
    cy = H * t.get('y', 0.4)
    dy = cy - doc.shape[0] / 2
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.full((H, W, 4), (232, 232, 230, 255), np.uint8)
        p = ease(tt / 0.3, 'out')
        g = inv if tt >= t_hl else doc
        put(c, scale(g, 1.0 + 0.04 * p), W / 2, cy)
        over(c, vig, 0, 0)
        q = (tt - t_bar) / 0.2
        if q > 0:
            put(c, scale(bar, 0.92 + 0.08 * min(1.0, q)), W / 2, min(H * 0.76, max(cy + doc.shape[0] * 0.52 + bar_h / 2 + 20 * S, H * 0.68)) if is_landscape(W, H) else dy + y1 * (1.04) + bar_h / 2 + 30 * S, min(1.0, q * 2))
        c[..., 3] = int(255 * min(1.0, tt / 0.15) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- privacy_mosaic 截图隐私打码
def mosaic_image(im, boxes, block):
    """PIL 图上每个框 [x, y, 宽, 高]（比例）缩到 1/block 再按最近邻放大回去，认不出字。"""
    im = im.copy()
    for b in boxes:
        x0, y0 = int(b[0] * im.width), int(b[1] * im.height)
        x1, y1 = int((b[0] + b[2]) * im.width), int((b[1] + b[3]) * im.height)
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        reg = im.crop((x0, y0, x1, y1))
        sm = reg.resize((max(1, (x1 - x0) // block), max(1, (y1 - y0) // block)), Image.BILINEAR)
        im.paste(sm.resize(reg.size, Image.NEAREST), (x0, y0))
    return im


def mosaic_file(src, boxes, block_1080=24):
    """素材打码后的副本路径（缓存）：图片按素材宽 1080 时每格 block_1080 像素；视频每个框用 ffmpeg 缩放出马赛克。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    # 这里是原始素材坐标的颗粒换算，不是画布字号；保留旧口径，避免竖屏里的横图变样。
    key = hashlib.md5(f'{Path(src).resolve()}|{Path(src).stat().st_mtime}|{boxes}|{block_1080}'.encode()).hexdigest()[:12]
    if is_image(src):
        out = CACHE / f'{Path(src).stem}_{key}.png'
        if not out.exists():
            im = Image.open(src).convert('RGB')
            mosaic_image(im, boxes, max(4, int(block_1080 * im.width / 1080))).save(out)
        return str(out)
    out = CACHE / f'{Path(src).stem}_{key}.mp4'
    if not out.exists():
        p = probe(src)
        w, h = p['w'], p['h']
        blk = max(4, int(block_1080 * w / 1080))
        chain, cur = [], '[0:v]'
        for k, b in enumerate(boxes):
            bw_, bh_ = max(blk, int(b[2] * w) // 2 * 2), max(blk, int(b[3] * h) // 2 * 2)
            bx_, by2 = int(b[0] * w), int(b[1] * h)
            chain.append(f"{cur}split[m{k}][s{k}]")
            chain.append(f"[s{k}]crop={bw_}:{bh_}:{bx_}:{by2},scale={max(1, bw_ // blk)}:{max(1, bh_ // blk)},scale={bw_}:{bh_}:flags=neighbor[p{k}]")
            chain.append(f"[m{k}][p{k}]overlay={bx_}:{by2}[o{k}]")
            cur = f'[o{k}]'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-filter_complex', ';'.join(chain), '-map', cur, '-map', '0:a?',
                        '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-c:a', 'copy', str(out)], check=True)
    return str(out)


def prepare(tl, st, base='.'):
    """broll、大字素材里写了 mosaic 的换成打码副本。mosaic: [[x, y, 宽, 高], ...]（相对素材画面的比例）。"""
    def fix(d, key):
        if d.get('mosaic') and d.get(key) and not d.get('_mosaic'):
            src = d[key] if Path(d[key]).is_absolute() else str(Path(base) / d[key])
            d[key] = mosaic_file(src, d['mosaic'], d.get('mosaic_block', 24))
            d['_mosaic'] = True
    for b in tl.get('broll', []):
        fix(b, 'src')
    for t in tl.get('titles', []):
        fix(t, 'src')


# ---------------------------------------------------------------- 横屏侧栏与横向清单
def _landscape_sfx(it, width, S):
    b = rrect(width, 140 * S, 14 * S, '#3A3A3A', '#1EC8C8', int(3 * S))
    over(b, _fit(word(it.get('name', '音效'), 40 * S, '#FFFFFF', BOLD), width - 48 * S), 24 * S, 22 * S)
    over(b, _fit(word(f"{it.get('author', '剪映音效')} · {it.get('dur', '00:02')}", 26 * S, '#AAAAAA', MED), width - 48 * S), 24 * S, 86 * S)
    return b


def _landscape_axis(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    v = t.get('variant', 'events')
    cx, cy, sw, sh = _side(W, H, t)
    items = [str(x) for x in t.get('items') or []]
    times = at_list(t, len(items), 0.6, 0.4)
    w = Writer(out, W, H, FPS, alpha=True)
    sig = _audio(t.get('src') or aroll, t.get('wave_t', t['t0']), t.get('wave_dur', 1.2)) if v == 'wave' else []
    bins = 65
    envelope = np.array([np.abs(x).max() if len(x) else 0 for x in np.array_split(sig, bins)]) if len(sig) else np.zeros(bins)
    envelope /= max(1e-4, envelope.max())
    onset = int(bins * t['cut_at'] / t.get('wave_dur', 1.2)) if t.get('cut_at') is not None else next((j for j, e in enumerate(envelope) if e > 0.25), bins // 3)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        panel = rrect(sw * 0.94, sh * 0.90, 24 * S, '#F3EEE4' if v != 'year' else '#111111DD')
        ph, pw = panel.shape[:2]
        im = Image.fromarray(panel)
        d = ImageDraw.Draw(im)
        if v == 'events':
            y0, y1 = ph * 0.12, ph * 0.88
            d.line([(pw * 0.17, y0), (pw * 0.17, y1)], fill='#1E1714', width=max(1, int(4 * S)))
            for j, x in enumerate(items):
                yy = y0 + (y1 - y0) * (j + 0.5) / max(1, len(items))
                active = tt >= times[j]
                r = (12 if active else 6) * S
                d.ellipse([pw * 0.17 - r, yy - r, pw * 0.17 + r, yy + r], fill='#FF4A1C' if active else '#B8AFA2')
                d.text((pw * 0.27, yy), x, font=ImageFont.truetype(str(HEAVY), int(40 * S)), anchor='lm', fill='#1E1714' if active else '#AAA399')
        elif v == 'year':
            target = str(t.get('target', items[-1] if items else '2025'))
            ti = items.index(target) if target in items else max(0, len(items) - 1)
            pos = ti - min(4, ti) * (1 - ease((tt - 0.2) / t.get('scroll', 1.2), 'inout'))
            for j, x in enumerate(items):
                yy = ph * 0.50 + (j - pos) * ph * 0.20
                if ph * 0.12 < yy < ph * 0.90:
                    d.line([(pw * 0.12, yy), (pw * 0.25, yy)], fill='#DDDDDD', width=max(1, int(3 * S)))
                    d.text((pw * 0.42, yy), x, font=ImageFont.truetype(str(OSWALD), int(48 * S)), anchor='lm', fill='#FFD84A' if j == ti else '#FFFFFF')
            d.polygon([(pw * 0.30, ph * 0.50), (pw * 0.25, ph * 0.47), (pw * 0.25, ph * 0.53)], fill='#FFD84A')
        else:
            for j, e in enumerate(envelope):
                x = pw * (0.08 + 0.84 * j / bins)
                hh = max(2 * S, e * ph * 0.22)
                d.line([(x, ph * 0.45 - hh), (x, ph * 0.45 + hh)], fill='#FF7A1A' if j >= onset else '#8A8A8A', width=max(1, int(3 * S)))
            x = pw * (0.08 + 0.84 * min(bins - 1, max(0, onset)) / bins)
            if tt > 0.35:
                d.line([(x, ph * 0.16), (x, ph * 0.74)], fill='#111111', width=max(1, int(4 * S)))
                d.text((pw / 2, ph * 0.84), '切点 · 1 帧', font=ImageFont.truetype(str(HEAVY), int(34 * S)), anchor='mm', fill='#111111')
        put(c, np.array(im), cx, cy, ease(tt / 0.3, 'out'))
        w.put(_finish(c, tt, dur))
    w.close()


def _landscape_reslist(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    paper = t.get('variant', 'paper') == 'paper'
    items = (t.get('items') or [])[:7]
    times = at_list(t, len(items), 0.35, 0.3)
    title = word(t.get('title') or '资源清单', 64 * S, '#3A2A10' if paper else '#111111', HEAVY)
    if paper:
        bgp = Path(work) / f'paper_kraft_{W}x{H}.png'
        if not bgp.exists():
            paper_texture(bgp, W, H, 'kraft')
        bg = np.array(Image.open(bgp).convert('RGBA'))
        title = _fit(title, W * 0.82)
    else:
        cx, cy, sw, sh = _side(W, H, dict(t, side='left'))
        title = _fit(title, sw * 0.84)
    rows = [word(x, (62 if paper else 36) * S, '#F3C94D' if paper else '#333333', HEAVY, stroke=int(3 * S) if paper else 0, stroke_color='#3A2A10') for x in items]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = bg.copy() if paper else np.zeros((H, W, 4), np.uint8)
        if paper:
            put(c, title, W / 2, H * 0.17)
            per = (len(rows) + 1) // 2
            for j, (g, at) in enumerate(zip(rows, times)):
                col, row = divmod(j, max(1, per))
                put(c, _fit(g, W * 0.38), W * (0.28 + col * 0.44), H * 0.33 + row * H * 0.12, ease((tt - at) / 0.25))
        else:
            panel = rrect(sw, sh, 20 * S, '#FFFFFFD9')
            put(panel, title, sw / 2, sh * 0.10)
            cat = _fit(word(t.get('category') or '资源', 30 * S, '#777777', MED), sw * 0.84)
            put(panel, cat, sw / 2, sh * 0.22)
            for j, g in enumerate(rows):
                put(panel, _fit(g, sw * 0.84), sw / 2, sh * (0.34 + j * 0.075))
            if t.get('note'):
                put(panel, _fit(word(t['note'], 26 * S, '#C4161C', BOLD), sw * 0.84), sw / 2, sh * 0.94)
            put(c, panel, cx, cy, ease(tt / 0.3))
            k = active_idx(times, tt)
            if k >= 0:
                rx, ry, rw, rh = _side(W, H, dict(t, side='right'))
                g = _fit(word(items[k], 86 * S, '#111111', HEAVY, stroke=int(4 * S), stroke_color='#FFFFFF'), rw * 0.95)
                put(c, g, rx, ry, ease((tt - times[k]) / 0.2))
        w.put(_finish(c, tt, dur))
    w.close()


def _landscape_photostack(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    srcs = (t.get('srcs') or [])[:3]
    labels = (list(t.get('items') or []) + [''] * len(srcs))[:len(srcs)]
    times = at_list(t, len(srcs), 0.5, 0.25)
    cards = []
    for j, src in enumerate(srcs):
        g = card_of(src, W * 0.25, S, r=14, border=int(7 * S), ratio=4 / 3, shadow=False)
        if t.get('variant') == 'tab':
            tab = rrect(g.shape[1], 60 * S, 0, TAB_COLORS[j])
            put(tab, _fit(word(labels[j], 38 * S, '#111111', HEAVY), g.shape[1] * 0.90), g.shape[1] / 2, 30 * S)
            over(g, tab, 0, g.shape[0] - tab.shape[0])
        else:
            put(g, _fit(word(labels[j], 38 * S, '#FFFFFF', HEAVY, stroke=int(3 * S), stroke_color='#111111'), g.shape[1] * 0.90), g.shape[1] / 2, g.shape[0] * 0.82)
            g = rotate_rgba(g, [-3, 4, -4][j])
        cards.append(g)
    frs = _aroll_frames(aroll, t, dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, fr in enumerate(frs):
        tt = i / FPS
        c = _opaque(_soft_bg(fr, W, H, 0.55, 8))
        for j, (g, at) in enumerate(zip(cards, times)):
            p = ease((tt - at) / 0.25, 'out')
            put(c, g, W * (0.20 + j * 0.30), H * (0.43 + 0.04 * (j % 2)) + (1 - p) * 30 * S, p)
        w.put(_finish(c, tt, dur))
    w.close()


def _landscape_comments(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = (t.get('items') or [])[:8]
    times = at_list(t, len(items), 0.10 if t.get('variant') == 'pileup' else 0.15, 0.1)
    cards = []
    sw = _side(W, H, t)[2]
    for j, item in enumerate(items):
        it = item if isinstance(item, dict) else {'text': item}
        rows = _wrap(it.get('text', ''), BOLD, 34 * S, sw * 0.76)
        behind = t.get('variant', 'behind') == 'behind'
        h = (100 + 46 * len(rows) + (30 if it.get('likes') else 0)) * S
        g = rrect(sw * 0.90, h, 20 * S, '#FFFFFF')
        over(g, emoji(FACES[j % len(FACES)], 40 * S), 22 * S, 16 * S)
        if behind:
            over(g, word(it.get('name', f'网友{j + 1:02d}'), 24 * S, '#8A8A8A', MED), 76 * S, 24 * S)
        for k, row in enumerate(rows):
            over(g, word(row, 34 * S, '#222222', BOLD), 24 * S, (66 + k * 46) * S)
        if it.get('likes'):
            over(g, word('♥ ' + str(it['likes']), 24 * S, '#E8343C', MED), 24 * S, h - 40 * S)
        cards.append(_fit(rotate_rgba(g, (-1 if j % 2 else 1) * (3 if t.get('variant') == 'behind' else 6)), sw * 0.94, H * 0.17))
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for j, (g, at) in enumerate(zip(cards, times)):
            cx, cy, sw, sh = _side(W, H, {'side': 'left' if j % 2 == 0 else 'right'})
            yy = H * (0.23 + (j // 2) * 0.15)
            put(c, g, cx, yy, ease((tt - at) / 0.2, 'out'))
        w.put(_finish(c, tt, dur))
    w.close()


def _landscape_person(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    cx, cy, sw, sh = _side(W, H, t)
    name = t.get('name') or t.get('text') or '某某博主'
    nameplate = t.get('variant') == 'nameplate'
    rows = _wrap(name, HEAVY, 56 * S, sw * 0.86)
    nm = [_fit(_gold(x, 72 * S, S) if nameplate else word(x, 56 * S, '#111111', HEAVY), sw * 0.86) for x in rows]
    w = Writer(out, W, H, FPS, alpha=True)
    av = None
    if not nameplate:
        D = int(H * 0.13)
        if t.get('avatar'):
            im = src_image(t['avatar'])
            side = min(im.size)
            im = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width + side) // 2, (im.height + side) // 2)).resize((D, D), Image.LANCZOS)
            av = _round(im, D / 2)
        else:
            fr = next(read(aroll, t['t0'] + 0.2, 1 / FPS, (W, H), FPS))
            size, x, y = face_crop(W, H)
            av = _avatar(fr, (x + size / 2, y + size / 2, size), D)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        if nameplate:
            y = H * 0.28
            for g in nm:
                put(c, g, cx, y, ease(tt / 0.3))
                y += g.shape[0] + 16 * S
            for j, title in enumerate((t.get('titles') or [])[:3]):
                g = _fit(word(title, 38 * S, '#FFE24A', HEAVY, stroke=int(2 * S), stroke_color='#2A1A00'), sw * 0.90)
                put(c, g, cx, y + j * 68 * S, ease((tt - 0.3 - 0.15 * j) / 0.25))
        else:
            card = rrect(sw * 0.94, sh * 0.84, 22 * S, '#FFFFFF')
            h, width = card.shape[:2]
            put(card, av, width / 2, h * 0.20)
            if t.get('verified', True):
                bx, by = width / 2 + av.shape[1] * 0.34, h * 0.20 + av.shape[0] * 0.34
                put(card, rrect(28 * S, 28 * S, 14 * S, '#25A4F5'), bx, by)
                put(card, word('✓', 20 * S, '#FFFFFF', BOLD), bx, by)
            for j, g in enumerate(nm):
                put(card, g, width / 2, h * 0.43 + j * 64 * S)
            put(card, _fit(word(t.get('fans') or '粉丝 128.6w', 30 * S, '#777777', MED), width * 0.86), width / 2, h * 0.73)
            put(card, pill(t.get('button') or '关注', 32 * S, '#FFFFFF', '#FE2C55', S), width / 2, h * 0.88)
            put(c, card, cx, cy, ease(tt / 0.3, 'out'))
        w.put(_finish(c, tt, dur))
    w.close()


def _landscape_node(text, w, h, S, active):
    b = rrect(w, h, 10 * S, '#F2EFA0' if active else '#111111', '#C9A646', int(3 * S))
    size = 52 * S
    rows = _wrap(text, HEAVY, size, w * 0.84)
    while len(rows) * size * 1.18 > h * 0.80 and size > 28 * S:
        size -= 2 * S
        rows = _wrap(text, HEAVY, size, w * 0.84)
    lh = size * 1.18
    for j, row in enumerate(rows):
        g = _fit(word(row, size, '#1A1A1A' if active else '#F3EBD2', HEAVY), w * 0.84)
        put(b, g, w / 2, h / 2 + (j - (len(rows) - 1) / 2) * lh)
    return b


def _safe_head_square(sq, W, H):
    # 圆里多留胸前时，也不能读到源画面外的黑边。
    cx, cy, size = sq
    side, x, y = face_crop(W, H, {'x': (cx - size / 2) / W, 'y': (cy - size / 2) / W, 's': size / W})
    return x + side / 2, y + side / 2, side
