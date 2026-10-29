"""卡片与章节的逐帧合成（手法库第 3 批）：数据卡、环形图、章节页这类大字，和盖住口播的样机、头像图文版、目录回顾、关注尾帧。

大字版式（titles 的 layout，beats 自动挑或手写）：title_clip 输出整屏透明 .mov，render.py 叠在字幕下面。
- statcard     深色描边数据卡（info_stat_card）：标题、英文副标、一两行数字，第二行跟着口播出现
- ring         占比环形图（share_ring_pie）：细圆环填充 / 三色饼图加标签 / 圆形图上扇形长出
- fog          白雾镂空大序号（chapter_fog_numeral）：底部雾面板或整屏雾，数字镂空透出后面的人
- chapter_page 章节标题页（chapter_title_page）：衬线标题加预告窗 / 毛笔手写体 / 总标题原位换分标题
版式（layout 的 mode）：layout_clip 输出铺满画面的 mp4（口播声音还在），pip 小窗可以压在上面。
- mockup   手机样机（device_mockup）           - combo    圆头像图文版（avatar_content_combo）
- overview 要点目录与回顾（points_overview）    - endcard  头像关注尾帧（follow_endcard）
尺寸都按画面比例写，短边 1080 的像素值乘 S 换算。
"""
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import backgrounds
import annot
import bigtype
import structure
import infocard
import scene
import wordart
import vfx
import props
import effects
import keytext
from fonts import FONTS
from kvlib import unit, is_landscape, safe_zones, face_crop, CHAPTER_LAYOUTS, OVERVIEW_EVERY, hex_rgba, is_image, item_times, probe, to_png
from motion import Writer, _rmask, bg_frames, ease, over, paste, read, resize, rotate_rgba, text_img, trim

SIGN_FONT = FONTS / 'MrsSaintDelafield-Regular.ttf'   # 签名体英文
SCRIPT_FONT = FONTS / 'GreatVibes-Regular.ttf'        # 手写英文
YELLOW = '#F5D300'


# ---------------------------------------------------------------- 小工具
def _style(st):
    return 'variety' if st.get('tone') == 'variety' else 'premium'


def env(t, dur, fin=0.25, fout=0.2):
    """入场淡入、出场淡出的不透明度。"""
    a = ease(t / fin, 'out') if fin else 1.0
    b = 1 - ease((t - (dur - fout)) / fout) if fout else 1.0
    return min(a, b)


def eback(p):
    """带一点回弹的缓出（弹出用）。"""
    p = min(1.0, max(0.0, p))
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def ss(w, h, draw, k=3):
    """超采样画矢量形状（圆环、扇形、圆角框）再缩回来，边缘不锯齿。draw(ImageDraw, k) 按 k 倍坐标画。"""
    im = Image.new('RGBA', (max(1, int(w * k)), max(1, int(h * k))), (0, 0, 0, 0))
    draw(ImageDraw.Draw(im), k)
    return np.array(im.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS))


def scale_rgba(a, k):
    return np.array(Image.fromarray(a, 'RGBA').resize((max(1, int(a.shape[1] * k)), max(1, int(a.shape[0] * k))), Image.BILINEAR))


def blur_rgba(a, r):
    return np.array(Image.fromarray(a, 'RGBA').filter(ImageFilter.GaussianBlur(r))) if r > 0.3 else a


def fit_text(text, size, width, color, role='title', style='premium', **kw):
    """一行字，太长就缩字号到 width 以内。"""
    a = trim(text_img(text, size, color, role, style, pad=2, **kw))
    if a.shape[1] > width:
        a = trim(text_img(text, size * width / a.shape[1], color, role, style, pad=2, **kw))
    return a


def wrap(text, size, width):
    """按宽度断行（中文一个字约一个字号宽，英文数字约半个）。"""
    lines, cur, w = [], '', 0.0
    for c in text:
        cw = size * (1.0 if ord(c) > 0x2E7F else 0.55)
        if c == '\n' or (w + cw > width and cur):
            lines.append(cur)
            cur, w = ('' if c == '\n' else c), (0.0 if c == '\n' else cw)
            continue
        cur, w = cur + c, w + cw
    return [x for x in lines + [cur] if x]


def stack(imgs, gap=0, align='left'):
    """几张 RGBA 竖着叠成一张。"""
    imgs = [x for x in imgs if x is not None]
    w = max(x.shape[1] for x in imgs)
    out = np.zeros((sum(x.shape[0] for x in imgs) + gap * (len(imgs) - 1), w, 4), np.uint8)
    y = 0
    for x in imgs:
        ox = 0 if align == 'left' else (w - x.shape[1]) // 2
        out[y:y + x.shape[0], ox:ox + x.shape[1]] = x
        y += x.shape[0] + gap
    return out


def rich_line(text, hl, size, color, hl_color, role='body', style='premium'):
    """一行字里 hl 的词换颜色。"""
    parts = re.split('(' + '|'.join(map(re.escape, hl)) + ')', text) if hl else [text]
    imgs = [text_img(p, size, hl_color if p in (hl or []) else color, role, style, pad=0) for p in parts if p]
    h = max(x.shape[0] for x in imgs)
    out = np.zeros((h, sum(x.shape[1] for x in imgs), 4), np.uint8)
    x = 0
    for a in imgs:
        out[h - a.shape[0]:, x:x + a.shape[1]] = a
        x += a.shape[1]
    return out


def number_img(value, size, style='premium', color='#EDEDED'):
    """窄体大数字，尾巴上的「+」做上标，「%」「万」这类单位缩小贴底。"""
    m = re.match(r'^([^0-9]*[0-9][0-9.,]*)(.*)$', str(value))
    head, tail = m.groups() if m else (str(value), '')
    a = trim(text_img(head, size, color, 'en_display', style, pad=2))
    tail = tail.strip().replace('⁺', '+')
    if not tail:
        return a
    sup = tail == '+'
    b = trim(text_img(tail, size * (0.5 if sup else 0.42), color, 'en_display' if tail.isascii() else 'title', style, pad=2))
    gap = int(size * 0.04)
    h = max(a.shape[0], b.shape[0])
    out = np.zeros((h, a.shape[1] + gap + b.shape[1], 4), np.uint8)
    out[h - a.shape[0]:, :a.shape[1]] = a
    by = 0 if sup else h - b.shape[0]
    out[by:by + b.shape[0], a.shape[1] + gap:] = b
    return out


def shadow_of(a, r, alpha=0.5):
    """一张 RGBA 的柔和投影（同形状的模糊黑影）。"""
    s = np.zeros_like(a)
    s[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
    return blur_rgba(s, r)


def circle_mask(d):
    im = Image.new('L', (d * 4, d * 4), 0)
    ImageDraw.Draw(im).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
    return np.array(im.resize((d, d), Image.LANCZOS), np.float32)[..., None] / 255


def _src(path, work):
    return to_png(path, work) if is_image(path) else path


def warm_blur(aroll, t0, dur, W, H, FPS, n, work, gain=(1.0, 1.0, 1.0)):
    """口播画面高斯虚化压暗做底（可偏色）。"""
    g = np.array(gain, np.float32)
    for fr in bg_frames('blur', W, H, FPS, n, work, aroll, t0):
        yield np.clip(fr.astype(np.float32) * g, 0, 255).astype(np.uint8)


def gradient(W, H, c1, c2, diagonal=True):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = ((xx / W + yy / H) / 2 if diagonal else yy / H)[..., None]
    return np.array(hex_rgba(c1)[:3], np.float32) * (1 - u) + np.array(hex_rgba(c2)[:3], np.float32) * u


# ---------------------------------------------------------------- 大字版式
def title_clip(t, W, H, FPS, st, work, aroll, preview=False):
    """一条逐帧合成的大字（layout 在 GRAPHIC_LAYOUTS 里）渲成整屏透明 .mov，返回路径。"""
    out = f"{work}/title_{t['layout']}_{t['t0']:.2f}.mov"
    if t['layout'] in keytext.LAYOUTS:   # 第 6 批重点字网感
        keytext.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in annot.LAYOUTS:     # 第 7 批贴纸标注与文字动效
        annot.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in effects.LAYOUTS:   # 第 8 批放射爆炸底、字不动底在换、文字故障换字
        effects.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in structure.LAYOUTS:   # 第 10 批开场与结构：快闪、拼贴、文字先行、画框问号、海报页、封面、求赞页、章节卡、回扣、互动条、口号
        structure.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in props.LAYOUTS:   # 第 15 批贴纸与其他（一星）
        props.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in vfx.LAYOUTS:   # 第 14 批特效（一星）
        vfx.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in wordart.LAYOUTS:   # 第 13 批文字与排版（一星）
        wordart.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in scene.LAYOUTS:   # 第 12 批版式与镜头
        scene.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in infocard.LAYOUTS:   # 第 11 批信息卡片
        infocard.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    if t['layout'] in bigtype.LAYOUTS:   # 第 9 批大字排版：巨字、底纹字、方框字、四角字、圆头像环绕字、分屏轮换、章节卡、打字机面板
        bigtype.clip(t, W, H, FPS, st, work, aroll, out)
        return out
    {'statcard': stat_card, 'ring': ring, 'fog': fog, 'chapter_page': chapter_page}[t['layout']](t, W, H, FPS, st, work, aroll, out)
    return out


STATCARD_VARIANTS = {
    'ornate': '暗金角花卡：细金描边四角花饰，金色标题配极小英文',
    'lime': '黄绿发光卡：黄绿描边带外发光，上下金色小花纹，黄色标题居中',
    'rows': '分行跟读卡：第一行先出，说到第二个数时先亮绿勾，0.25 秒后第二行出现，让观众自己算比例',
}


def _side_box(t, W, H):
    side = t.get('side') or ('left' if int(t.get('t0', 0)) % 2 else 'right')
    if t.get('side') is None and isinstance(t.get('x'), (int, float)):
        side = 'left' if t['x'] < 0.5 else 'right'
    z = safe_zones(W, H)['text'][0 if side == 'left' else 1]
    x0, y0, x1, y1 = z
    x0, x1 = max(0.05, x0), min(0.95, x1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # 手写坐标仍按整幅画面的比例算；靠近边缘时收回并给卡片留足宽高。
    if isinstance(t.get('x'), (int, float)):
        cx = max(x0 + (x1 - x0) * 0.35, min(x1 - (x1 - x0) * 0.35, t['x']))
    if isinstance(t.get('y'), (int, float)):
        cy = max(y0 + (y1 - y0) * 0.35, min(y1 - (y1 - y0) * 0.35, t['y']))
    return W * cx, H * cy, W * 2 * min(cx - x0, x1 - cx), H * 2 * min(cy - y0, y1 - cy)


def stat_card(t, W, H, FPS, st, work, aroll, out):
    """t: {title, en, rows: [{value, label, at}], variant, x, y, w}。背景压暗、整卡 0.25 秒模糊渐显，第二行在 at 秒出现。"""
    S, style = unit(W, H), _style(st)
    v = t.get('variant', 'ornate')
    dur = t['t1'] - t['t0']
    tc = '#F2E85C' if v == 'lime' else '#E9D9A6'
    bc = {'lime': '#E8F060', 'ornate': '#CDB57A'}.get(v, '#FFFFFF60')
    cw = int(W * t.get('w', 0.66))
    if is_landscape(W, H):
        cx, cy, side_w, side_h = _side_box(t, W, H)
        cw = int(min(cw, side_w - 52 * S))
    pad = int(cw * 0.08)
    inner = cw - 2 * pad
    orn = int(16 * S) if v == 'lime' else 0
    parts = []   # [图, x, y, 出现组, 居中组]：出现组 0 一开始就在，1 第二行，'check' 绿勾；居中组一起居中
    y = pad + orn
    ti = fit_text(t.get('title') or t.get('text', ''), 62 * S, inner, tc, 'title', style)
    parts.append([ti, 0, y, 0, 'title'])
    y += ti.shape[0] + int(14 * S)
    if t.get('en'):
        en = fit_text(t['en'].upper(), 22 * S, inner, '#FFFFFFA6', 'en', style, spacing=4 * S)
        parts.append([en, 0, y, 0, 'en'])
        y += en.shape[0]
    y += int(36 * S)
    rows = (t.get('rows') or [{'value': t.get('value', ''), 'label': t.get('label')}])[:2]
    for j, r in enumerate(rows):
        num = number_img(r['value'], 120 * S, style)
        if is_landscape(W, H):
            num = bigtype._fit(num, inner - (62 * S if j == 1 and v == 'rows' else 0))
        x = 0
        if j == 1 and v == 'rows':
            d = int(46 * S)
            chk = ss(d, d, lambda dr, k: (dr.ellipse([0, 0, d * k - 1, d * k - 1], fill=hex_rgba('#2ECC71')),
                                          dr.line([(d * k * 0.27, d * k * 0.52), (d * k * 0.44, d * k * 0.69), (d * k * 0.74, d * k * 0.34)],
                                                  fill=(255, 255, 255, 255), width=int(d * k * 0.11))))
            parts.append([chk, 0, y + (num.shape[0] - d) // 2, 'check', j])
            x = d + int(16 * S)
        if is_landscape(W, H):
            num = bigtype._fit(num, inner - x)
        parts.append([num, x, y, j, j])
        if r.get('label'):
            lab = fit_text(r['label'], 34 * S, max(60, inner - x - num.shape[1] - 18 * S), '#EDEDEDD0', 'body', style)
            if is_landscape(W, H):
                lab = fit_text(r['label'], 30 * S, inner, '#EDEDEDD0', 'body', style)
                parts.append([lab, 0, y + num.shape[0] + 12 * S, j, j])
                y += lab.shape[0] + int(12 * S)
            else:
                parts.append([lab, x + num.shape[1] + int(18 * S), y + num.shape[0] - lab.shape[0] - int(num.shape[0] * 0.03), j, j])
        y += num.shape[0] + int(26 * S)
    ch = y - int(26 * S) + pad + orn
    if v == 'lime':   # 居中：标题、英文各自居中，每一行数字和说明整组居中
        groups = {}
        for p in parts:
            groups.setdefault(p[4], []).append(p)
        for ps in groups.values():
            gw = max(p[1] + p[0].shape[1] for p in ps)
            for p in ps:
                p[1] += (inner - gw) // 2
    g, R = int(26 * S), int(18 * S)
    bw_ = max(1, int((3 if v == 'lime' else 1.6) * S))

    def card(dr, k):
        dr.rounded_rectangle([g * k, g * k, (g + cw) * k - 1, (g + ch) * k - 1], radius=R * k, fill=hex_rgba('#0B0B0DEB'),
                             outline=hex_rgba(bc), width=bw_ * k)
    base = ss(cw + 2 * g, ch + 2 * g, card)
    gold = hex_rgba('#D9B65C')
    if v == 'lime':
        ring_ = ss(cw + 2 * g, ch + 2 * g, lambda dr, k: dr.rounded_rectangle([g * k, g * k, (g + cw) * k - 1, (g + ch) * k - 1], radius=R * k,
                                                                             outline=hex_rgba('#E8F060'), width=int(7 * S * k)))
        base = over(blur_rgba(ring_, 11 * S), base, 0, 0)
        ow, oh = int(cw * 0.30), int(24 * S)
        o = ss(ow, oh, lambda dr, k: (dr.rectangle([0, oh * k * 0.45, ow * k, oh * k * 0.55], fill=(11, 11, 13, 255)),
                                      dr.line([(0, oh * k / 2), (ow * k, oh * k / 2)], fill=gold, width=int(2 * S * k)),
                                      dr.polygon([(ow * k / 2, 0), (ow * k / 2 + oh * k * 0.5, oh * k / 2), (ow * k / 2, oh * k),
                                                  (ow * k / 2 - oh * k * 0.5, oh * k / 2)], fill=gold),
                                      [dr.ellipse([(ow * k / 2 + s_ * oh * k * 0.95) - 3 * S * k, oh * k / 2 - 3 * S * k,
                                                   (ow * k / 2 + s_ * oh * k * 0.95) + 3 * S * k, oh * k / 2 + 3 * S * k], fill=gold) for s_ in (-1, 1)]))
        for yy in (g, g + ch):
            over(base, o, g + cw / 2 - ow / 2, yy - oh / 2)
    elif v == 'ornate':   # 四角 L 形花饰
        im = Image.fromarray(base, 'RGBA')
        dr = ImageDraw.Draw(im)
        c, L, lw = int(12 * S), int(34 * S), max(1, int(2 * S))
        for px, py, sx, sy in ((g + c, g + c, 1, 1), (g + cw - c, g + c, -1, 1), (g + c, g + ch - c, 1, -1), (g + cw - c, g + ch - c, -1, -1)):
            dr.line([(px, py), (px + sx * L, py)], fill=gold, width=lw)
            dr.line([(px, py), (px, py + sy * L)], fill=gold, width=lw)
            q = int(5 * S)
            dr.polygon([(px, py - q), (px + q, py), (px, py + q), (px - q, py)], fill=gold)
        base = np.array(im)
    static = base.copy()
    for img, x, y_, grp, _ in parts:
        if grp == 0:
            over(static, img, g + pad + x, g + y_)
    a2 = None
    if len(rows) > 1:
        a2 = rows[1].get('at')
        a2 = min(1.2, dur * 0.45) if a2 is None else a2
    cx, cy = W * t.get('x', 0.5), H * t.get('y', 0.60)
    if is_landscape(W, H):
        cx, cy, side_w, side_h = _side_box(t, W, H)
        # 连描边和外发光一起限高。
        kfit = min(1.0, side_h / static.shape[0])
    dim = 0 if t.get('_plain') else 0.45
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(max(1, round(dur * FPS))):
        tt = i / FPS
        e = env(tt, dur, 0.3, 0.2)
        canvas = np.zeros((H, W, 4), np.uint8)
        canvas[..., 3] = int(255 * dim * e)
        spr = static
        if a2 is not None and tt >= a2 - 0.3:
            spr = static.copy()
            for img, x, y_, grp, _ in parts:
                if grp == 'check' and tt >= a2 - 0.25:
                    k = eback((tt - a2 + 0.25) / 0.2)
                    sm = scale_rgba(img, max(0.05, k))
                    over(spr, sm, g + pad + x + (img.shape[1] - sm.shape[1]) / 2, g + y_ + (img.shape[0] - sm.shape[0]) / 2)
                elif grp == 1 and tt >= a2:
                    p = ease((tt - a2) / 0.25, 'out')
                    over(spr, img, g + pad + x, g + y_ + (1 - p) * 14 * S, p)
        if is_landscape(W, H) and kfit < 1:
            spr = scale_rgba(spr, kfit)
        p = ease(tt / 0.28, 'out')
        if p < 1:   # 整卡模糊渐显
            sm = blur_rgba(scale_rgba(spr, 0.96 + 0.04 * p), 8 * S * (1 - p))
            over(canvas, sm, cx - sm.shape[1] / 2, cy - sm.shape[0] / 2, p * e)
        else:
            over(canvas, spr, cx - spr.shape[1] / 2, cy - spr.shape[0] / 2, e)
        w.put(canvas)
    w.close()


RING_VARIANTS = {
    'donut': '细圆环填充：圆环从 12 点顺时针长到比例，中心百分比同步滚动',
    'pie': '饼图加标签：两三个扇区顺时针长出并略微张开，随后渐变虚线标签逐个弹出错落堆叠',
    'slice': '圆形图上扇形长出：图片（logo、地球、头像）裁成圆，一块色块从 12 点长到占比',
}
PIE_COLORS = ['#7B2FF7', '#D7263D', '#1FB5C9', '#F2A93B']


def _pie_tag(text, en, color, S, style):
    """饼图标签：渐变色块 + 白色虚线边 + 宋体中文 + 英文小字。"""
    cn = trim(text_img(text, 40 * S, '#FFFFFF', 'serif', style, pad=2))
    ens = trim(text_img(en.upper(), 17 * S, '#FFFFFFC8', 'en', style, pad=2, spacing=2 * S)) if en else None
    body = stack([cn, ens], int(6 * S))
    px, py = int(26 * S), int(16 * S)
    w, h = body.shape[1] + 2 * px, body.shape[0] + 2 * py
    c1 = np.array(hex_rgba(color)[:3], np.float32)
    grad = c1 * (1 - np.linspace(0, 1, w)[None, :, None] * 0.45) + 255 * np.linspace(0, 1, w)[None, :, None] * 0.12
    tag = np.zeros((h, w, 4), np.uint8)
    tag[..., :3] = np.clip(np.repeat(grad, h, 0), 0, 255)
    tag[..., 3:4] = (_rmask(w, h, int(10 * S)) * 255).astype(np.uint8)
    im = Image.fromarray(tag, 'RGBA')
    dr = ImageDraw.Draw(im)
    q, dl, lw = int(6 * S), int(10 * S), max(1, int(2 * S))
    for x in range(q + int(10 * S), w - q - int(10 * S), 2 * dl):
        dr.line([(x, q), (min(x + dl, w - q), q)], fill=(255, 255, 255, 230), width=lw)
        dr.line([(x, h - q), (min(x + dl, w - q), h - q)], fill=(255, 255, 255, 230), width=lw)
    for y in range(q + int(10 * S), h - q - int(10 * S), 2 * dl):
        dr.line([(q, y), (q, min(y + dl, h - q))], fill=(255, 255, 255, 230), width=lw)
        dr.line([(w - q, y), (w - q, min(y + dl, h - q))], fill=(255, 255, 255, 230), width=lw)
    tag = np.array(im)
    over(tag, body, px, py)
    return tag


def ring(t, W, H, FPS, st, work, aroll, out):
    """t: {variant, pct（donut / slice）, items: [[名字, 占比, 英文?]]（pie）, src（slice 的圆形图）, text, lead, color, at, x, y}。"""
    S, style = unit(W, H), _style(st)
    v = t.get('variant', 'donut')
    dur = t['t1'] - t['t0']
    g0, gl = t.get('at', 0.2), t.get('grow', 0.9)
    dim = 0 if t.get('_plain') else 0.5
    cx, cy = W * t.get('x', 0.5), H * t.get('y', 0.56)   # 胸口：不压脸
    label = fit_text(t['text'], 50 * S, W * 0.84, '#F7F5F0', 'title', style) if t.get('text') else None
    lead = fit_text(t['lead'], 32 * S, W * 0.84, '#EEF0F2C8', 'body', style) if t.get('lead') else None
    d = int(W * {'donut': 0.42, 'pie': 0.40, 'slice': 0.44}[v])
    if is_landscape(W, H):
        cx, cy, side_w, side_h = _side_box(t, W, H)
        d = int(min(side_w * 0.72, H * 0.30))
        cy = H * 0.36
        label = fit_text(t['text'], 38 * S, side_w, '#F7F5F0', 'title', style) if t.get('text') else None
        lead = fit_text(t['lead'], 30 * S, side_w, '#EEF0F2C8', 'body', style) if t.get('lead') else None
    pct = float(t.get('pct', 0))
    tags = []
    if v == 'donut':
        rw = d * 0.10
        col = hex_rgba(t.get('color', '#4F8BFF'))
        track = ss(d, d, lambda dr, k: dr.ellipse([0, 0, d * k - 1, d * k - 1], outline=(255, 255, 255, 46), width=int(rw * k)))
    elif v == 'pie':
        items = t['items'][:4]
        cols = t.get('colors', PIE_COLORS)
        tot = sum(float(x[1]) for x in items)
        tags = [_pie_tag(x[0], x[2] if len(x) > 2 else '', cols[j % len(cols)], S, style) for j, x in enumerate(items)]
    else:
        src = Image.open(to_png(t['src'], work)).convert('RGB')
        s_ = min(src.size)
        src = src.crop(((src.width - s_) // 2, (src.height - s_) // 2, (src.width - s_) // 2 + s_, (src.height - s_) // 2 + s_)).resize((d, d), Image.LANCZOS)
        disc = np.zeros((d, d, 4), np.uint8)
        disc[..., :3] = np.array(src)
        disc[..., 3:4] = (circle_mask(d) * 255).astype(np.uint8)
        rw_ = int(5 * S)
        disc = over(ss(d + 2 * rw_, d + 2 * rw_, lambda dr, k: dr.ellipse([0, 0, (d + 2 * rw_) * k - 1, (d + 2 * rw_) * k - 1], fill=(255, 255, 255, 255))),
                    disc, rw_, rw_)
        col = hex_rgba(t.get('color', '#A0662E'))[:3] + (225,)
    w = Writer(out, W, H, FPS, alpha=True)
    cache = {}
    for i in range(max(1, round(dur * FPS))):
        tt = i / FPS
        e = env(tt, dur, 0.3, 0.2)
        q = ease((tt - g0) / gl, 'out')
        canvas = np.zeros((H, W, 4), np.uint8)
        canvas[..., 3] = int(255 * dim * e)
        key = round(q, 3)
        if v == 'donut':
            if key not in cache:
                arc = ss(d, d, lambda dr, k: dr.arc([0, 0, d * k - 1, d * k - 1], -90, -90 + 360 * pct / 100 * q, fill=col, width=int(rw * k))) \
                    if q > 0.002 else np.zeros((d, d, 4), np.uint8)
                num = number_img(f'{round(pct * q)}%', d * 0.24, style, '#FFFFFF')
                spr = over(track.copy(), arc, 0, 0)
                cache[key] = over(spr, num, (d - num.shape[1]) / 2, (d - num.shape[0]) / 2)
            spr = cache[key]
        elif v == 'pie':
            boom = 0.03 * d * ease((tt - g0 - gl) / 0.25, 'out')
            key = (key, round(boom, 1))
            if key not in cache:
                D = int(d * 1.12)
                o = (D - d) / 2

                def pie(dr, k, q=q, boom=boom):
                    dr.ellipse([o * k, o * k, (o + d) * k, (o + d) * k], fill=(255, 255, 255, 34))
                    a0, A = -90.0, 360 * q * tot / 100
                    for j, x in enumerate(items):
                        span = 360 * float(x[1]) / 100
                        a1 = min(a0 + span, -90 + A)
                        if a1 > a0:
                            mid = np.radians(a0 + span / 2)
                            dx, dy = np.cos(mid) * boom, np.sin(mid) * boom
                            dr.pieslice([(o + dx) * k, (o + dy) * k, (o + d + dx) * k, (o + d + dy) * k], a0, a1, fill=hex_rgba(cols[j % len(cols)]))
                        a0 += span
                cache[key] = ss(D, D, pie)
            spr = cache[key]
        else:
            if key not in cache:
                D = disc.shape[0]
                rw_ = (D - d) // 2
                sec = ss(D, D, lambda dr, k: dr.pieslice([rw_ * k, rw_ * k, (rw_ + d) * k, (rw_ + d) * k], -90, -90 + 360 * pct / 100 * q, fill=col)) \
                    if q > 0.002 else np.zeros_like(disc)
                cache[key] = over(disc.copy(), sec, 0, 0)
            spr = cache[key]
        over(canvas, spr, cx - spr.shape[1] / 2, cy - spr.shape[0] / 2, e)
        top, bot = cy - spr.shape[0] / 2, cy + spr.shape[0] / 2
        if v == 'slice' and tt > g0 + gl * 0.8:   # 占比数字写在扇形中间
            num = number_img(f"{t.get('pct_text') or (str(int(pct)) + '%')}", d * 0.13, style, '#FFFFFF')
            mid = np.radians(-90 + 180 * pct / 100)
            nx, ny = cx + np.cos(mid) * d * 0.27, cy + np.sin(mid) * d * 0.27
            pe = ease((tt - g0 - gl * 0.8) / 0.25) * e
            over(canvas, shadow_of(num, 6 * S, 0.8), nx - num.shape[1] / 2, ny - num.shape[0] / 2 + 3 * S, pe)
            over(canvas, num, nx - num.shape[1] / 2, ny - num.shape[0] / 2, pe)
        if lead is not None:
            over(canvas, lead, cx - lead.shape[1] / 2, top - lead.shape[0] - 30 * S, ease(tt / 0.35) * e)
        y = bot + 34 * S
        if label is not None:
            over(canvas, label, cx - label.shape[1] / 2, y, ease((tt - 0.15) / 0.35) * e)
            y += label.shape[0] + 30 * S
        for j, tg in enumerate(tags):   # 标签逐个弹出，左右两边错落
            a = g0 + gl + 0.1 + j * 0.22
            if tt < a:
                continue
            k = max(0.05, 0.6 + 0.4 * eback((tt - a) / 0.25))
            sm = scale_rgba(tg, k)
            tx = W * (0.15 if j % 2 == 0 else 0.85)
            ty = top + spr.shape[0] * (0.18 + 0.30 * j)
            if is_landscape(W, H):
                if len(tags) > 3:
                    sm = bigtype._fit(sm, side_w * 0.46)
                    tx, ty = cx + (-1 if j % 2 == 0 else 1) * side_w * 0.25, H * (0.60 + (j // 2) * 0.10)
                else:
                    sm = bigtype._fit(sm, side_w * 0.92)
                    tx, ty = cx, H * 0.59 + j * 58 * S
            over(canvas, sm, tx - sm.shape[1] / 2, ty + (tg.shape[0] - sm.shape[0]) / 2, min(1.0, (tt - a) / 0.1) * e)
        w.put(canvas)
    w.close()


FOG_VARIANTS = {
    'panel': '底部雾面板：下方约一半高蒙七成白雾（上缘羽化），巨大斜体序号镂空，像便利贴从左下翻折进来，雾上压章节名和三个并列词',
    'window': '整屏数字窗：整屏蒙七成白雾，只有一个占画面七成高的序号是清晰窗口，人脸从数字笔画里露出来；人不挡数字时人压在雾上面',
}


def fog(t, W, H, FPS, st, work, aroll, out):
    """t: {number, text, en, items, variant, dark, person}。背景本身很亮（白墙）时自动换深色雾面，字跟着换浅色。
    window 默认人也蒙在雾里、脸从数字笔画里透出来；人压在雾上面后数字还露得出六成以上才压（person: true / false 强制）。
    白场载体接力转场（panel_carrier_transition，只对 window）：enter "cover" 开头 0.3 秒白雾从下半屏往上急速铺满（接在 panel 后面像面板放大盖屏）；
    exit "door" 最后 0.5 秒整屏白雾带着镂空数字以左边为轴像门一样透视转开；shapes ["2", "?"] 到 shape_at 秒镂空形状逆时针转 90 度换成下一个。"""
    if is_landscape(W, H):
        return _landscape_fog(t, W, H, FPS, st, work, aroll, out)
    S, style = unit(W, H), _style(st)
    v = t.get('variant', 'panel')
    dur = t['t1'] - t['t0']
    sample = next(read(aroll, t['t0'] + 0.2, 1 / FPS, (54, 96), FPS)).astype(np.float32)
    num = str(t.get('number', '1'))
    glyph = str(int(num)) if num.isdigit() else num

    def numeral(h, s):
        a = trim(text_img(s, h * 1.5, '#FFFFFF', 'en_display', style, pad=4, italic=0.16))
        return scale_rgba(a, h / a.shape[0])

    # window：默认人也蒙在雾里，脸从数字笔画里透出来。人压在雾上面要看数字还露不露得出来：
    # 试居中和靠左右几个摆法，数字笔画露出六成以上才压（person: true 强制压，false 不压）
    place, person, a_ref = None, False, None
    if v == 'window':
        place = (numeral(H * 0.70, glyph), W * 0.5, H * 0.42)
        if t.get('person', 'auto') is not False:
            import matte
            a_ref = next(matte.cutouts(aroll, t['t0'] + 0.2, 1 / FPS, W, H, FPS))

            def seen(p):
                m, cx_, cy_ = p
                mm = m[..., 3].astype(np.float32) / 255
                x0_, y0_ = int(cx_ - m.shape[1] / 2), int(cy_ - m.shape[0] / 2)
                xa, ya, xb, yb = max(0, x0_), max(0, y0_), min(W, x0_ + m.shape[1]), min(H, y0_ + m.shape[0])
                part = mm[ya - y0_:yb - y0_, xa - x0_:xb - x0_]
                return float((part * (1 - a_ref[ya:yb, xa:xb])).sum() / max(1.0, mm.sum()))
            small = numeral(H * 0.52, glyph)
            cands = [place, (small, W * 0.96 - small.shape[1] / 2, H * 0.33), (small, W * 0.04 + small.shape[1] / 2, H * 0.33)]
            best = max(cands, key=seen)
            if t.get('person') is True or seen(best) >= 0.6:
                person, place = True, best
    if person:   # 人压在雾上面时，雾只盖人身后的背景：按背景的亮度挑雾色
        keep = 1 - np.array(Image.fromarray((a_ref * 255).astype(np.uint8)).resize((54, 96), Image.BILINEAR), np.float32)[..., None] / 255
        luma = float((sample * keep).sum() / max(1.0, keep.sum() * 3)) / 255
    else:
        luma = sample.mean() / 255
    dark = t.get('dark', luma > 0.62)
    fog_rgb = (22, 22, 26) if dark else (250, 250, 247)
    ink = '#F4F2EC' if dark else '#16161A'
    fa = 0.74 if dark else 0.70

    w = Writer(out, W, H, FPS, alpha=True)
    n = max(1, round(dur * FPS))
    if v == 'panel':
        y0 = int(H * 0.52)
        ph = H - y0
        layer = np.zeros((ph, W, 4), np.uint8)
        layer[..., :3] = fog_rgb
        prof = np.full(ph, fa, np.float32)
        fe = int(H * 0.10)
        prof[:fe] = np.linspace(0, fa, fe)
        layer[..., 3] = (prof[:, None] * 255).astype(np.uint8)
        nm = numeral(H * 0.20, num)
        nx, ny = int(W * 0.05), int(H * 0.06)
        reg = layer[ny:ny + nm.shape[0], nx:nx + nm.shape[1], 3]
        reg[:] = (reg * (1 - nm[:reg.shape[0], :reg.shape[1], 3] / 255)).astype(np.uint8)   # 数字镂空
        tx = nx + nm.shape[1] + int(W * 0.04)
        tw = W - tx - int(W * 0.05)
        ty = ny + int(H * 0.012)
        ti = fit_text(t.get('text', ''), H * 0.046, tw, ink, 'title', style)
        over(layer, ti, tx, ty)
        ty += ti.shape[0] + int(H * 0.012)
        if t.get('en'):
            en = fit_text(t['en'].upper(), H * 0.0135, tw, ink + '90', 'en', style, spacing=5 * S)
            over(layer, en, tx, ty)
            ty += en.shape[0] + int(H * 0.016)
        items = [x for x in (t.get('items') or [])[:3]]
        if items:
            imgs = [trim(text_img(x, H * 0.024, ink, 'body', style, pad=2)) for x in items]
            gap = int(W * 0.035)
            k = min(1.0, tw / (sum(x.shape[1] for x in imgs) + gap * (len(imgs) - 1)))
            x = tx
            for j, im in enumerate(imgs):
                im = scale_rgba(im, k) if k < 1 else im
                over(layer, im, x, ty)
                x += im.shape[1] + gap * k
                if j < len(imgs) - 1:   # 并列词之间一道细竖线
                    bar = np.zeros((int(im.shape[0] * 0.9), max(1, int(2 * S)), 4), np.uint8)
                    bar[...] = hex_rgba(ink)[:3] + (120,)
                    over(layer, bar, x - gap * k / 2, ty + im.shape[0] * 0.05)
        pil = Image.fromarray(layer, 'RGBA')
        for i in range(n):
            tt = i / FPS
            canvas = np.zeros((H, W, 4), np.uint8)
            p = ease(tt / 0.4, 'out')
            if p < 1:   # 便利贴：绕左下角从斜着、小一圈翻进来
                k = 0.6 + 0.4 * p
                im = pil.rotate(-20 * (1 - p), resample=Image.BICUBIC, center=(0, ph)).resize((int(W * k), int(ph * k)), Image.BILINEAR)
                over(canvas, np.array(im), 0, H - im.height, min(1.0, tt / 0.12))
            else:
                canvas[y0:] = layer
            if tt > dur - 0.25 and not t.get('_relay'):   # 后面紧接放大盖屏的整屏白雾时不淡出，直接接力
                canvas[..., 3] = (canvas[..., 3] * env(tt, dur, 0, 0.25)).astype(np.uint8)
            w.put(canvas)
        w.close()
        return
    big, cx, cy = place
    ti = fit_text(t.get('text', ''), H * 0.05, W * 0.86, ink, 'title', style)
    en = fit_text(t['en'].upper(), H * 0.014, W * 0.86, ink + '90', 'en', style, spacing=5 * S) if t.get('en') else None
    if person:   # 标题压在人身上：垫一层投影才看得清
        ti = np.maximum(shadow_of(ti, 8 * S, 0.7), ti) if dark else ti
    cut = matte.cutouts(aroll, t['t0'], dur, W, H, FPS) if person else None   # 抠出来的人那块不蒙雾
    shapes = [str(x) for x in (t.get('shapes') or [])]
    big2 = scale_rgba(numeral(H * 0.70, shapes[1]), big.shape[0] / max(1, numeral(H * 0.70, shapes[1]).shape[0])) if len(shapes) > 1 else None
    sa, cover, door = t.get('shape_at', 1.0), t.get('enter') == 'cover', t.get('exit') == 'door'
    yy = np.arange(H, dtype=np.float32)[:, None]

    def hole(a, nm, k_=1.0):
        x0, y0 = int(cx - nm.shape[1] / 2), int(cy - nm.shape[0] / 2)
        sx0, sy0 = max(0, -x0), max(0, -y0)
        x1, y1 = min(W, x0 + nm.shape[1]), min(H, y0 + nm.shape[0])
        a[max(0, y0):y1, max(0, x0):x1] *= 1 - k_ * nm[sy0:sy0 + y1 - max(0, y0), sx0:sx0 + x1 - max(0, x0), 3] / 255
    for i in range(n):
        tt = i / FPS
        e = env(tt, dur, 0.02 if cover else 0.3, 0.02 if door else 0.25)
        k = 1.25 - 0.25 * ease(tt / 0.35, 'out')
        nm = scale_rgba(big, k) if k > 1.001 else big
        canvas = np.zeros((H, W, 4), np.uint8)
        canvas[..., :3] = fog_rgb
        a = np.full((H, W), fa * 255 * e, np.float32)
        if big2 is not None and tt >= sa:   # 镂空换形：逆时针转 90 度，旧形状淡出、新形状淡入
            p = ease((tt - sa) / 0.3)
            if p < 1:
                a_old = a.copy()
                hole(a_old, rotate_rgba(nm, 90 * p))
                hole(a, rotate_rgba(big2, -90 * (1 - p)))
                a = a_old * (1 - p) + a * p
            else:
                hole(a, big2)
        else:
            hole(a, nm)
        if cut is not None:
            a *= 1 - next(cut)
        if cover and tt < 0.3:   # 白雾从下半屏往上急速铺满，上缘羽化
            top = H * 0.52 - H * 0.62 * ease(tt / 0.3, 'in')
            a *= np.clip((yy - top) / (H * 0.1), 0, 1)
        canvas[..., 3] = a.astype(np.uint8)
        over(canvas, ti, W / 2 - ti.shape[1] / 2, H * 0.84, ease((tt - 0.15) / 0.3) * e)
        if en is not None:
            over(canvas, en, W / 2 - en.shape[1] / 2, H * 0.84 + ti.shape[0] + H * 0.012, ease((tt - 0.25) / 0.3) * e)
        if door and tt > dur - 0.5:   # 透视开门：以左边为轴，右边往左转过去、靠近镜头时变高
            from motion import _quad_coeffs
            p = ease((tt - (dur - 0.5)) / 0.5, 'inout')
            xr = W * np.cos(p * np.pi / 2)
            grow = H * 0.12 * np.sin(p * np.pi / 2)
            if xr > 2:
                im = Image.fromarray(canvas, 'RGBA').transform((W, H), Image.PERSPECTIVE, _quad_coeffs(
                    [(0, 0), (xr, -grow), (xr, H + grow), (0, H)], [(0, 0), (W, 0), (W, H), (0, H)]), Image.BILINEAR)
                canvas = np.array(im)
                canvas[..., :3] = (canvas[..., :3] * (1 - 0.25 * p)).astype(np.uint8)   # 转过去的门面暗一点
            else:
                canvas[...] = 0
        w.put(canvas)
    w.close()


CHAPTER_PAGE_VARIANTS = {
    'preview': '衬线标题加预告窗：口播虚化成暖橙到灰蓝的渐变底，左上大号白色衬线编号和标题，右下圆角竖屏小窗播本节要做的效果',
    'hand': '毛笔手写体章节页：口播虚化偏暖，斜放大号毛笔标题，白色小标题、拉开字距的英文、一道蓝色签名体斜穿，右边缘竖排灰色大字半露出血',
    'swap': '总标题原位换分标题：画面中间先出白色总标题，约 1 秒后同一位置换成蓝色块反白的本节名，每节重复同一套',
}


def _wipe(a, p, soft):
    """从左往右擦出：a 的透明度按 x 截到 p 的位置，边缘柔和 soft 像素。"""
    if p >= 1:
        return a
    w = a.shape[1]
    edge = p * (w + soft)
    m = np.clip((edge - np.arange(w)) / soft, 0, 1)[None, :]
    b = a.copy()
    b[..., 3] = (b[..., 3] * m).astype(np.uint8)
    return b


def chapter_page(t, W, H, FPS, st, work, aroll, out):
    """t: {variant, number, text, en, sub, preview（预告窗素材）, sign（签名体英文）, main（总标题）, swap_at}。"""
    if is_landscape(W, H):
        return _landscape_chapter(t, W, H, FPS, st, work, aroll, out)
    S, style = unit(W, H), _style(st)
    v = t.get('variant', 'hand')
    dur = t['t1'] - t['t0']
    n = max(1, round(dur * FPS))
    num = str(t.get('number', '01'))
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'swap':
        size = H * 0.065
        main = fit_text(t.get('main', ''), size, W * 0.86, '#FFFFFF', 'title', style)
        txt = fit_text(t.get('text', ''), size, W * 0.80, '#FFFFFF', 'title', style)
        px, py = int(size * 0.35), int(size * 0.22)
        blk = np.zeros((txt.shape[0] + 2 * py, txt.shape[1] + 2 * px, 4), np.uint8)
        blk[...] = hex_rgba('#0A1EFF')
        over(blk, txt, px, py)
        sa = t.get('swap_at', min(1.0, dur * 0.4))
        cx, cy = W / 2, H * t.get('y', 0.52)
        msh = shadow_of(main, 8 * S, 0.7)
        for i in range(n):
            tt = i / FPS
            canvas = np.zeros((H, W, 4), np.uint8)
            e = env(tt, dur, 0, 0.2)
            if tt < sa:
                p = ease(tt / 0.15)
                over(canvas, msh, cx - main.shape[1] / 2, cy - main.shape[0] / 2 + 4 * S, p)
                over(canvas, main, cx - main.shape[1] / 2, cy - main.shape[0] / 2, p)
            else:
                over(canvas, blk, cx - blk.shape[1] / 2, cy - blk.shape[0] / 2, e)
            w.put(canvas)
        w.close()
        return
    if v == 'preview':
        grad = gradient(W, H, '#C8552E', '#5A6478')
        bgs = (np.clip(fr * 0.55 + grad * 0.55, 0, 255).astype(np.uint8) for fr in warm_blur(aroll, t['t0'], dur, W, H, FPS, n, work))
        x0 = int(W * 0.08)
        nm = trim(text_img(num, H * 0.10, '#FFFFFF', 'serif', style, pad=2))
        ti = fit_text('· ' + t.get('text', ''), H * 0.055, W * 0.84, '#FFFFFF', 'serif', style)
        parts = [(nm, x0, H * 0.18), (ti, x0, H * 0.18 + nm.shape[0] + H * 0.02)]
        y = parts[-1][2] + ti.shape[0] + H * 0.018
        if t.get('en'):
            en = fit_text(t['en'].upper(), H * 0.016, W * 0.8, '#FFFFFF90', 'en', style, spacing=6 * S)
            parts.append((en, x0 + 4 * S, y))
            y += en.shape[0] + H * 0.014
        if t.get('sub'):
            parts.append((fit_text(t['sub'], H * 0.022, W * 0.8, '#FFFFFFCC', 'body', style), x0 + 4 * S, y))
        group = np.zeros((H, W, 4), np.uint8)
        for a, x, y_ in parts:
            over(group, shadow_of(a, 6 * S, 0.45), x, y_ + 3 * S)
            over(group, a, x, y_)
        pw = int(W * 0.40) // 2 * 2
        ph = int(pw * 16 / 9) // 2 * 2
        psrc = _src(t['preview'], work) if t.get('preview') else aroll
        prev = read(psrc, t.get('preview_in', 0) if t.get('preview') else t['t0'], dur, (pw, ph), FPS)
        pm = _rmask(pw, ph, int(W * 0.03))
        psh = shadow_of(np.dstack([np.zeros((ph, pw, 3), np.uint8), (pm[..., 0] * 255).astype(np.uint8)]), 14 * S, 0.6)
        px, py = W * 0.92 - pw, H * 0.48
        for i, (bg, pf) in enumerate(zip(bgs, prev)):
            tt = i / FPS
            canvas = np.dstack([bg, np.full((H, W), 255, np.uint8)])
            p = ease((tt - 0.2) / 0.35, 'out')
            if p > 0:
                over(canvas, psh, px, py + (1 - p) * H * 0.06 + 10 * S, p)
                rgba = np.dstack([pf, (pm[..., 0] * 255).astype(np.uint8)])
                over(canvas, rgba, px, py + (1 - p) * H * 0.06, p)
            over(canvas, _wipe(group, ease(tt / 0.5, 'inout'), 60 * S), 0, 0)
            canvas[..., 3] = int(255 * env(tt, dur, 0.2, 0.2))
            w.put(canvas)
        w.close()
        return
    # hand：毛笔手写体
    bgs = warm_blur(aroll, t['t0'], dur, W, H, FPS, n, work, (1.12, 0.97, 0.80))
    text = t.get('text', '')
    lines = [text] if len(text) <= 3 else [text[:(len(text) + 1) // 2], text[(len(text) + 1) // 2:]]
    title = stack([trim(text_img(x, H * 0.12, t.get('color', '#F0E6C0'), 'hand', style, pad=4)) for x in lines], int(H * 0.005))
    if title.shape[1] > W * 0.80:
        title = scale_rgba(title, W * 0.80 / title.shape[1])
    title = rotate_rgba(title, 12)
    edge = trim(text_img(text[:4], H * 0.17, '#CFCFCF66', 'serif', style, vertical=True, pad=2))
    sign = rotate_rgba(trim(text_img(t.get('sign') or f'Chapter {num}', H * 0.075, '#4A6BFF', fontfile=SIGN_FONT, pad=8)), 15)
    sub = fit_text(t.get('sub') or f'第 {num} 节', H * 0.030, W * 0.6, '#FFFFFF', 'title', style)
    en = fit_text((t.get('en') or '').upper(), H * 0.0135, W * 0.7, '#FFFFFFB3', 'en', style, spacing=9 * S) if t.get('en') else None
    tcx, tcy = W * 0.42, H * 0.34
    static = np.zeros((H, W, 4), np.uint8)
    over(static, edge, W - edge.shape[1] * 0.5, H * 0.10)
    late = np.zeros((H, W, 4), np.uint8)
    over(late, sub, W * 0.08, tcy + title.shape[0] / 2 + H * 0.02)
    if en is not None:
        over(late, en, W * 0.08 + 3 * S, tcy + title.shape[0] / 2 + H * 0.02 + sub.shape[0] + H * 0.014)
    over(late, sign, W * 0.66 - sign.shape[1] / 2, tcy + title.shape[0] * 0.22 - sign.shape[0] / 2)
    tl_ = np.zeros((H, W, 4), np.uint8)
    over(tl_, shadow_of(title, 8 * S, 0.5), tcx - title.shape[1] / 2, tcy - title.shape[0] / 2 + 4 * S)
    over(tl_, title, tcx - title.shape[1] / 2, tcy - title.shape[0] / 2)
    for i, bg in enumerate(bgs):
        tt = i / FPS
        canvas = np.dstack([bg, np.full((H, W), 255, np.uint8)])
        over(canvas, static, 0, 0, ease(tt / 0.3))
        over(canvas, _wipe(tl_, ease(tt / 0.5, 'inout'), 80 * S), 0, 0)
        over(canvas, late, 0, 0, ease((tt - 0.3) / 0.3))
        canvas[..., 3] = int(255 * env(tt, dur, 0.2, 0.2))
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- 版式（盖住口播的整屏画面）
LAYOUT_MODES = ('mockup', 'combo', 'overview', 'endcard')


def layout_clip(l, tl, W, H, FPS, st, work, aroll, preview=False):
    """一段 mockup / combo / overview / endcard 版式渲成铺满画面的 mp4，返回路径。"""
    out = f"{work}/{l['mode']}_{l['t0']:.2f}.mp4"
    {'mockup': mockup, 'combo': combo, 'overview': overview, 'endcard': endcard}[l['mode']](l, tl, W, H, FPS, st, work, aroll, out, preview)
    return out


def phone_sprite(pw, S):
    """代码画的手机：黑色圆角机身、细亮边、灵动岛，屏幕区透明。返回 (机身 RGBA, 屏幕 (x, y, w, h), 屏幕遮罩, 投影 RGBA, 投影外扩)。"""
    ph = int(pw * 2.08)
    r, bz = int(pw * 0.15), int(pw * 0.035)

    def body(dr, k):
        dr.rounded_rectangle([0, 0, pw * k - 1, ph * k - 1], radius=r * k, fill=(16, 16, 18, 255), outline=(88, 88, 96, 255), width=max(1, int(3 * S * k)))
        dr.rounded_rectangle([bz * k, bz * k, (pw - bz) * k - 1, (ph - bz) * k - 1], radius=(r - bz) * k, fill=(0, 0, 0, 0))
        iw, ih = pw * 0.27, pw * 0.075
        dr.rounded_rectangle([(pw - iw) / 2 * k, (bz + pw * 0.025) * k, (pw + iw) / 2 * k, (bz + pw * 0.025 + ih) * k], radius=ih / 2 * k, fill=(0, 0, 0, 255))
    m = int(pw * 0.08)
    sh = np.zeros((ph + 2 * m, pw + 2 * m, 4), np.uint8)
    sh[m:m + ph, m:m + pw, 3] = (_rmask(pw, ph, r)[..., 0] * 150).astype(np.uint8)
    return ss(pw, ph, body), (bz, bz, pw - 2 * bz, ph - 2 * bz), _rmask(pw - 2 * bz, ph - 2 * bz, r - bz), blur_rgba(sh, m / 2.2), m


def screen_frames(src, src_in, dur, sw, sh, FPS, crop=None):
    """样机屏幕里的画面：竖屏素材铺满；横版录屏铺满会被裁掉两边的字，改成按宽度放进屏幕中间、上下留黑
    （字小就写 crop 先裁出要看的那块）。"""
    if is_image(src):
        w_, h_ = Image.open(src).size
    else:
        pr = probe(src)
        w_, h_ = pr['w'], pr['h']
    if crop:
        w_, h_ = w_ * crop[2], h_ * crop[3]
    if w_ / h_ < sw / sh * 1.25:
        yield from read(src, src_in, dur, (sw, sh), FPS, crop)
        return
    ih = int(sw * h_ / w_) // 2 * 2
    for fr in read(src, src_in, dur, (sw, ih), FPS, crop):
        out = np.full((sh, sw, 3), 12, np.uint8)
        out[(sh - ih) // 2:(sh - ih) // 2 + ih] = fr
        yield out


MOCKUP_VARIANTS = {
    'steps': '样机配步骤：深色网格底，样机在右，左边黄色「方法：」下的步骤跟着口播一条条出现，顶部白色粗斜体标题',
    'screen': '渐变底样机录屏：深蓝到灰蓝渐变带细点阵，样机居中占画宽六成放录屏，顶部白色超粗英文大标题加中文副标',
    'stack': '两台叠放：示例装进样机，第二台从右侧压上来叠在前面，各带一个黄色标签',
}


def mockup(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {src, src_in, crop, variant, title, sub, steps, at（每步出现秒数）, src2, src2_in, crop2, at2, labels}。"""
    S, style = unit(W, H), _style(st)
    v = l.get('variant', 'screen')
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    src = _src(l['src'], work)
    texts = []   # (图, x, y, 出现秒)
    if v == 'steps':
        bgs = bg_frames('grid:white', W, H, FPS, n, work)
        phones = [(0.50, 0.70, 0.555, src, l.get('src_in', 0), 0.0, 0, l.get('crop'))]
        if l.get('title'):
            ti = fit_text(l['title'], H * 0.040, W * 0.90, '#FFFFFF', 'title', style, italic=0.12)
            texts.append((ti, (W - ti.shape[1]) / 2, H * 0.085, 0.0))
        steps = l.get('steps') or []
        x0, cw = W * 0.05, W * 0.37
        y = H * 0.28
        lab = trim(text_img('方法：', H * 0.030, YELLOW, 'title', style, pad=2))
        texts.append((lab, x0, y, 0.1))
        y += lab.shape[0] + H * 0.022
        for j, (s_, a) in enumerate(zip(steps, item_times(l, len(steps), max(0.4, (dur - 0.8) / max(1, len(steps)))))):
            im = stack([trim(text_img(x, H * 0.024, '#FFFFFF', 'body', style, pad=2)) for x in wrap(f'{j + 1}. {s_}', H * 0.024, cw)], int(H * 0.008))
            texts.append((im, x0, y, a))
            y += im.shape[0] + H * 0.024
    elif v == 'screen':
        g = gradient(W, H, '#0B0E22', '#6C7AA8', diagonal=False)
        gap = round(0.02 * W)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dots = np.clip(1.6 * S + 0.5 - np.hypot(xx % gap - gap / 2, yy % gap - gap / 2), 0, 1)[..., None]
        static_bg = np.clip(g + 255 * 0.12 * dots, 0, 255).astype(np.uint8)
        bgs = (static_bg for _ in range(n))
        phones = [(0.58, 0.5, 0.58, src, l.get('src_in', 0), 0.0, 0, l.get('crop'))]
        if l.get('title'):
            ti = fit_text(l['title'], H * 0.075, W * 0.9, '#FFFFFF', 'en_display', style, italic=0.12)
            texts.append((ti, (W - ti.shape[1]) / 2, H * 0.055, 0.0))
        if l.get('sub'):
            su = fit_text(l['sub'], H * 0.024, W * 0.8, '#FFFFFFD0', 'body', style)
            texts.append((su, (W - su.shape[1]) / 2, H * 0.055 + H * 0.085, 0.1))
    else:
        bgs = bg_frames('dots:static', W, H, FPS, n, work)
        src2 = _src(l.get('src2') or l['src'], work)
        a2 = l.get('at2', 0.8)
        phones = [(0.48, 0.36, 0.47, src, l.get('src_in', 0), 0.0, 0, l.get('crop')),
                  (0.48, 0.64, 0.58, src2, l.get('src2_in', 0), a2, W * 0.75, l.get('crop2', l.get('crop')))]
        labs = (l.get('labels') or [])[:2]
        for j, lb in enumerate(labs):
            tg = text_img(lb, H * 0.028, '#111111', 'title', style, pad=0)
            px, py = int(H * 0.012), int(H * 0.008)
            blk = np.zeros((tg.shape[0] + 2 * py, tg.shape[1] + 2 * px, 4), np.uint8)
            blk[..., :3] = hex_rgba(YELLOW)[:3]
            blk[..., 3:4] = (_rmask(blk.shape[1], blk.shape[0], int(8 * S)) * 255).astype(np.uint8)
            over(blk, tg, px, py)
            texts.append((blk, W * 0.10 if j == 0 else W * 0.90 - blk.shape[1], H * 0.12 if j == 0 else H * 0.885, 0.1 if j == 0 else a2 + 0.2))
    if is_landscape(W, H):
        pw = H * 0.66 / 2.08 / W
        if v == 'stack':
            phones = [(pw, 0.36, 0.42, src, l.get('src_in', 0), 0, 0, l.get('crop')),
                      (pw, 0.67, 0.42, src2, l.get('src2_in', 0), a2, 60 * S, l.get('crop2', l.get('crop')))]
            texts = [(g, W * (0.36 if j == 0 else 0.67) - g.shape[1] / 2, H * 0.78, a) for j, (g, x, y, a) in enumerate(texts)]
        else:
            phones = [(pw, 0.73, 0.42, src, l.get('src_in', 0), 0, 0, l.get('crop'))]
            texts = []
            yy = H * 0.20
            for txt, size, color in [(l.get('title'), 68, '#FFFFFF'), (l.get('sub'), 38, '#FFFFFFD0')]:
                if txt:
                    g = fit_text(txt, size * S, W * 0.45, color, 'title', style)
                    texts.append((g, W * 0.08, yy, 0))
                    yy += g.shape[0] + 24 * S
            for j, (txt, at) in enumerate(zip(l.get('steps') or [], item_times(l, len(l.get('steps') or []), 0.7))):
                g = fit_text(f'{j + 1}. {txt}', 40 * S, W * 0.45, YELLOW, 'body', style)
                texts.append((g, W * 0.08, max(yy, H * 0.40) + j * 88 * S, at))
    rigs = []
    for pwr, cxr, cyr, s_, si, a, dx, cr in phones:
        pw = int(W * pwr)
        body, (sx, sy, sw, sh_), sm, shd, m = phone_sprite(pw, S)
        rigs.append((body, sx, sy, sm, shd, m, W * cxr - pw / 2, H * cyr - body.shape[0] / 2, screen_frames(s_, si, dur, sw, sh_, FPS, cr), a, dx))
    w = Writer(out, W, H, FPS, preview=preview)
    for i in range(n):
        tt = i / FPS
        canvas = next(bgs).copy()
        for body, sx, sy, sm, shd, m, x, y, gen, a, dx in rigs:
            fr = next(gen)
            if tt < a:
                continue
            p = ease((tt - a) / 0.35, 'out') if dx else 1.0
            xx_ = x + dx * (1 - p)
            paste(canvas, shd, xx_ - m + 10 * S, y - m + 18 * S)
            paste(canvas, fr, xx_ + sx, y + sy, sm)
            paste(canvas, body, xx_, y)
        for im, x, y, a in texts:
            if tt >= a:
                p = ease((tt - a) / 0.3, 'out')
                paste(canvas, im, x - (1 - p) * 20 * S, y, opacity=p)
        w.put(canvas)
    w.close()


def avatar_frames(aroll, l, d, border, dur, FPS, W, H):
    """口播画面里人脸那块裁成圆形头像（逐帧，人在说话），带白描边。crop 同 pip。"""
    c = l.get('crop') or {'x': 0.0, 'y': 0.08, 's': 1.0}
    cs = int(c['s'] * W)
    if is_landscape(W, H):
        cs, x0, y0 = map(int, face_crop(W, H, l.get('crop')))
    m = circle_mask(d)
    D = d + 2 * border
    ring_ = ss(D, D, lambda dr, k: dr.ellipse([0, 0, D * k - 1, D * k - 1], fill=(255, 255, 255, 255)))
    for fr in read(aroll, l['t0'], dur, (W, H), FPS):
        if not is_landscape(W, H):
            y0, x0 = int(c['y'] * W), int(c['x'] * W)
        face = resize(fr[y0:y0 + cs, x0:x0 + cs], d, d)
        out = ring_.copy() if border else np.zeros((D, D, 4), np.uint8)
        over(out, np.dstack([face, (m[..., 0] * 255).astype(np.uint8)]), border, border)
        yield out


def card_sprite(src, w, max_h, S, border=0, radius=None):
    """图片做成圆角卡片（可加白描边），返回 RGBA。"""
    im = Image.open(src).convert('RGB')
    h = round(im.height * w / im.width)
    if h > max_h:
        h = int(max_h)
        w = round(im.width * h / im.height)
    r = int(radius if radius is not None else 0.03 * 1080 * S)
    img = np.array(im.resize((w, h), Image.LANCZOS))
    out = np.zeros((h + 2 * border, w + 2 * border, 4), np.uint8)
    if border:
        out[..., :3] = 255
        out[..., 3:4] = (_rmask(w + 2 * border, h + 2 * border, r + border) * 255).astype(np.uint8)
    over(out, np.dstack([img, (_rmask(w, h, max(r, 1))[..., 0] * 255).astype(np.uint8)]), border, border)
    return out


COMBO_VARIANTS = {
    'band': '头像领标题：素材铺底，左上白边圆头像，右边白色粗斜体标题和黄色副标题，下方一张横图卡片',
    'head_top': '顶部大头像配横图：牛皮纸底，顶部居中大圆头像，下方一张满宽白描边横图',
    'corner': '角落头像压叠卡：口播虚化底，两张横图卡依次上浮叠放，左下圆头像压住第二张卡的一角',
    'tutorial': '教程截图版：暗色虚化底，左上圆头像配步骤名，中间界面截图卡，下方参数截图，一行小字说明（关键词黄色）',
}
COMBO_PRESETS = {   # 头像 (cx, cy, 直径)、卡片 [(cx, cy, 宽)]、卡片最大高、标题左上角
    'band': dict(avatar=(0.20, 0.155, 0.30), cards=[(0.5, 0.67, 0.90)], max_h=0.30, title=(0.38, 0.105)),
    'head_top': dict(avatar=(0.5, 0.19, 0.44), cards=[(0.5, 0.53, 0.94)], max_h=0.30, title=None),
    'corner': dict(avatar=(0.22, 0.665, 0.34), cards=[(0.52, 0.28, 0.80), (0.56, 0.53, 0.80)], max_h=0.24, title=None),
    'tutorial': dict(avatar=(0.16, 0.11, 0.24), cards=[(0.5, 0.36, 0.90), (0.5, 0.60, 0.72)], max_h=0.22, title=(0.32, 0.075)),
}


def combo(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {variant, cards: [图片], at（每张卡出现秒数）, title, sub, note, hl, bg（band 的底，图片或视频）, crop（头像取口播哪块）}。"""
    S, style = unit(W, H), _style(st)
    v = l.get('variant', 'band')
    P = COMBO_PRESETS[v]
    if is_landscape(W, H):
        P = dict(avatar=(0.16, 0.28, H * 0.26 / W),
                 cards=[(0.55, 0.46, 0.25), (0.82, 0.46, 0.23)] if len(l.get('cards') or []) > 1 else [(0.64, 0.46, 0.51)],
                 max_h=0.52, title=(0.07, 0.49))
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    if v == 'band' and l.get('bg'):
        bgs = (np.clip(fr * 0.45, 0, 255).astype(np.uint8) for fr in read(_src(l['bg'], work), l.get('bg_in', 0), dur, (W, H), FPS))
    elif v == 'head_top':
        spec = backgrounds.make('paper', 'kraft', W, H, work)
        bgs = (backgrounds.frame_at(spec, 0, H) for _ in range(n))
    else:
        bgs = warm_blur(aroll, l['t0'], dur, W, H, FPS, n, work, (0.8, 0.8, 0.8) if v == 'tutorial' else (1, 1, 1))
    border = int(5 * S) if v != 'tutorial' else int(3 * S)
    cards = [card_sprite(_src(c, work), int(W * cw), H * P['max_h'], S, border=int(5 * S) if v in ('band', 'head_top') else 0)
             for c, (_, _, cw) in zip(l.get('cards') or [], P['cards'])]
    shadows = [shadow_of(c, 14 * S, 0.55) for c in cards]
    times = item_times(l, len(cards), 0.5)
    ax, ay, ad = P['avatar']
    d = int(W * ad) // 2 * 2
    avs = avatar_frames(aroll, l, d, border, dur, FPS, W, H)
    texts = []
    if P['title'] and l.get('title'):
        tx, ty = W * P['title'][0], H * P['title'][1]
        tw = W * (0.30 if is_landscape(W, H) else 0.95) - tx
        ti = stack([trim(text_img(x, H * 0.038, '#FFFFFF', 'title', style, pad=2, italic=0.12)) for x in wrap(l['title'], H * 0.038, tw)][:2], int(H * 0.006))
        texts.append((ti, tx, ty, 0.1))
        if l.get('sub'):
            texts.append((fit_text(l['sub'], H * 0.025, tw, YELLOW, 'body', style), tx, ty + ti.shape[0] + H * 0.014, 0.2))
    if v == 'tutorial' and l.get('note'):
        texts.append((rich_line(l['note'], l.get('hl') or [], H * 0.024, '#FFFFFF', YELLOW, 'body', style), W * (0.37 if is_landscape(W, H) else 0.08), H * 0.72, 0.3))
    w = Writer(out, W, H, FPS, preview=preview)
    for i in range(n):
        tt = i / FPS
        canvas = next(bgs).copy()
        av = next(avs)
        for c, sh, (cx, cy, _), a in zip(cards, shadows, P['cards'], times):
            if tt < a:
                continue
            p = ease((tt - a) / 0.35, 'out')
            x, y = W * cx - c.shape[1] / 2, H * cy - c.shape[0] / 2 + (1 - p) * H * 0.08
            paste(canvas, sh, x, y + 12 * S, opacity=p)
            paste(canvas, c, x, y, opacity=p)
        k = 0.7 + 0.3 * eback(tt / 0.25)
        a_ = av if k > 0.999 else scale_rgba(av, k)
        paste(canvas, a_, W * ax - a_.shape[1] / 2, H * ay - a_.shape[0] / 2, opacity=min(1.0, tt / 0.12))
        for im, x, y, a in texts:
            if tt >= a:
                paste(canvas, im, x, y, opacity=ease((tt - a) / 0.3))
        w.put(canvas)
    w.close()


OVERVIEW_VARIANTS = {
    'toc': '彩色斜标签目录：方格纸底，左边半透明红色竖排大字主题加手写英文，右边紫橙绿白四张斜标签卡依次上滑，各带描边大序号',
    'list': '两列编号目录：暖色渐变底，「01·标题」白色宋体两列逐条快速闪现',
    'grid': '2×2 编号卡回顾：口播虚化，四张圆角卡一张张弹出，每张是该章节的画面定格，上面 POINT、空心大序号和章节名',
    'tilted_collage': '倾斜作品墙：前面讲过的画面缩成 3~5 张白边卡片，斜着叠成一堆缓慢漂移，暗红色调底',
}


def chapter_items(tl, aroll, W, H, FPS):
    """从时间线自动取章节：编号、章节名、代表画面（这一章里第一张图片素材，没有就截口播）。"""
    chs = sorted((t for t in tl.get('titles', []) if t.get('layout') in CHAPTER_LAYOUTS), key=lambda t: t['t0'])
    end = max([x['t1'] for x in tl.get('subs', [])] + [c['t0'] + 6 for c in chs] or [0])
    out = []
    for i, c in enumerate(chs):
        nxt = chs[i + 1]['t0'] if i + 1 < len(chs) else end
        b = next((b for b in tl.get('broll', []) if c['t0'] - 0.1 <= b['t0'] < nxt and is_image(b.get('src', ''))), None)
        out.append({'num': str(c.get('number', f'{i + 1:02d}')), 'text': c.get('text', ''), 'src': b['src'] if b else None,
                    'at': min(c['t0'] + 2.0, (c['t0'] + nxt) / 2)})
    return out


def _frame_of(it, aroll, work, W, H, FPS):
    if it.get('src'):
        return np.array(Image.open(_src(it['src'], work)).convert('RGB'))
    return next(read(aroll, it.get('at', 0), 1 / FPS, (W // 2, H // 2), FPS))


def _cover(a, w, h):
    r = max(w / a.shape[1], h / a.shape[0])
    b = resize(a, a.shape[1] * r + 1, a.shape[0] * r + 1, fast=False)
    y0, x0 = (b.shape[0] - h) // 2, (b.shape[1] - w) // 2
    return b[y0:y0 + h, x0:x0 + w]


def overview(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {variant, items: [{num, text, src}]（不写就从时间线的章节自动取）, title, en, at / every}。"""
    if is_landscape(W, H):
        return _landscape_overview(l, tl, W, H, FPS, st, work, aroll, out, preview)
    S, style = unit(W, H), _style(st)
    v = l.get('variant', 'grid')
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    items = [dict(x, num=x.get('num', f'{j + 1:02d}')) for j, x in enumerate(l.get('items') or [])] or chapter_items(tl, aroll, W, H, FPS)
    if not items:
        raise SystemExit('overview 版式：时间线里没有章节页，也没写 items')
    cap = {'toc': 4, 'list': 12, 'grid': 4, 'tilted_collage': 5}[v]
    items = items[:cap]
    times = item_times(l, len(items), OVERVIEW_EVERY.get(v, 0.3))
    sprites = []   # (图, 中心 x, 中心 y, 出现秒, 入场方式, 漂移)
    if v == 'toc':
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cell = 0.05 * W
        lines = np.maximum(np.clip(1.6 * S - np.abs((xx + cell / 2) % cell - cell / 2), 0, 1), np.clip(1.6 * S - np.abs((yy + cell / 2) % cell - cell / 2), 0, 1))[..., None]
        bg = (np.array([243, 239, 228], np.float32) * (1 - lines * 0.45) + np.array([155, 183, 214], np.float32) * lines * 0.45).astype(np.uint8)
        bgs = (bg for _ in range(n))
        theme = trim(text_img(l.get('title', '本期要点')[:5], H * 0.10, '#D7262D8C', 'title', style, vertical=True, pad=2))
        static = [(theme, W * 0.06, H * 0.14)]
        if l.get('en'):
            static.append((rotate_rgba(trim(text_img(l['en'], H * 0.045, '#1A1A1A', fontfile=SCRIPT_FONT, pad=8)), 8), W * 0.04, H * 0.72))
        cols = ['#7A3CF0', '#FF6A1A', '#8CD94A', '#FFFFFF']
        for j, it in enumerate(items):
            cw, ch = int(W * 0.50), int(H * 0.12)
            dark = cols[j] in ('#FFFFFF', '#8CD94A')
            ink = '#1A1A1A' if dark else '#FFFFFF'
            card = np.zeros((ch, cw, 4), np.uint8)
            card[..., :3] = hex_rgba(cols[j])[:3]
            card[..., 3:4] = (_rmask(cw, ch, int(ch * 0.15)) * 255).astype(np.uint8)
            numi = trim(text_img(it['num'], ch * 0.85, '#00000000', 'en_display', style, pad=4, stroke=max(2, int(2.5 * S)), stroke_color=ink))
            over(card, numi, cw * 0.06, (ch - numi.shape[0]) / 2)
            ti = fit_text(it['text'], ch * 0.30, cw * 0.86 - numi.shape[1], ink, 'title', style)
            over(card, ti, cw * 0.10 + numi.shape[1], (ch - ti.shape[0]) / 2)
            card = over(shadow_of(card, 10 * S, 0.35), card, 0, 0)
            sprites.append((rotate_rgba(card, [-8, 4, -5, 6][j]), W * (0.66 + (0.02 if j % 2 else -0.02)), H * (0.24 + 0.155 * j), times[j], 'up', 0))
    elif v == 'list':
        g = gradient(W, H, '#2A1712', '#8A4426', diagonal=False).astype(np.uint8)
        bgs = (g for _ in range(n))
        static = []
        if l.get('title'):
            ti = fit_text(l['title'], H * 0.042, W * 0.86, '#FFFFFF', 'serif', style)
            static.append((ti, (W - ti.shape[1]) / 2, H * 0.08))
        per = (len(items) + 1) // 2
        for j, it in enumerate(items):
            col, row = divmod(j, per)
            im = fit_text(f"{it['num']}·{it['text']}", H * 0.026, W * 0.42, '#FFFFFF', 'serif', style)
            sprites.append((im, W * (0.07 if col == 0 else 0.53) + im.shape[1] / 2, H * (0.19 + 0.075 * row) + im.shape[0] / 2, times[j], 'flash', 0))
    elif v == 'grid':
        bgs = warm_blur(aroll, l['t0'], dur, W, H, FPS, n, work)
        static = []
        cw, ch = int(W * 0.44), int(H * 0.30)
        for j, it in enumerate(items):
            fr = (_cover(_frame_of(it, aroll, work, W, H, FPS), cw, ch).astype(np.float32) * 0.8).astype(np.uint8)
            shade = np.linspace(0, 0.65, ch)[:, None, None] ** 1.5
            fr = (fr * (1 - shade)).astype(np.uint8)
            card = np.dstack([fr, (_rmask(cw, ch, int(24 * S))[..., 0] * 255).astype(np.uint8)])
            pt = trim(text_img('POINT', H * 0.016, '#FFFFFFD0', 'en', style, pad=2, spacing=6 * S))
            over(card, pt, cw * 0.07, ch * 0.07)
            numi = trim(text_img(it['num'], H * 0.10, '#00000000', 'en_display', style, pad=4, stroke=max(2, int(2.5 * S)), stroke_color='#FFFFFF'))
            over(card, numi, cw * 0.07, ch * 0.07 + pt.shape[0] + H * 0.01)
            nm = fit_text(it['text'], H * 0.028, cw * 0.86, '#FFFFFF', 'title', style)
            over(card, nm, cw * 0.07, ch - nm.shape[0] - ch * 0.08)
            card = over(shadow_of(card, 12 * S, 0.5), card, 0, 0)
            sprites.append((card, W * (0.27 if j % 2 == 0 else 0.73), H * (0.27 if j < 2 else 0.60), times[j], 'pop', 0))
    else:
        bgs = warm_blur(aroll, l['t0'], dur, W, H, FPS, n, work, (0.62, 0.20, 0.20))
        static = []
        pos = [(0.32, 0.30, -9), (0.68, 0.34, 6), (0.40, 0.56, -4), (0.66, 0.62, 8), (0.50, 0.45, -6)]
        for j, it in enumerate(items):
            fr = _frame_of(it, aroll, work, W, H, FPS)
            cw = int(W * 0.40)
            chh = min(int(cw * fr.shape[0] / fr.shape[1]), int(H * 0.30))
            im = Image.fromarray(_cover(fr, cw, chh))
            tmp = f"{work}/ov_{l['t0']:.2f}_{j}.png"
            im.save(tmp)
            card = card_sprite(tmp, cw, H * 0.30, S, border=int(6 * S), radius=int(10 * S))
            card = over(shadow_of(card, 12 * S, 0.5), card, 0, 0)
            px, py, a = pos[j]
            sprites.append((rotate_rgba(card, a), W * px, H * py, times[j], 'pop', (1 if j % 2 else -1) * 0.02 * W))
    w = Writer(out, W, H, FPS, preview=preview)
    for i in range(n):
        tt = i / FPS
        canvas = next(bgs).copy()
        for im, x, y in static:
            paste(canvas, im, x, y, opacity=ease(tt / 0.3))
        for im, cx, cy, a, how, drift in sprites:
            if tt < a:
                continue
            p = ease((tt - a) / 0.3, 'out')
            dx = drift * (tt - a)
            if how == 'up':
                paste(canvas, im, cx - im.shape[1] / 2, cy - im.shape[0] / 2 + (1 - p) * H * 0.06, opacity=p)
            elif how == 'flash':
                paste(canvas, im, cx - im.shape[1] / 2 - (1 - p) * 16 * S, cy - im.shape[0] / 2, opacity=min(1.0, (tt - a) / 0.12))
            else:
                k = 1.2 - 0.2 * p
                sm = scale_rgba(im, k) if k > 1.001 else im
                paste(canvas, sm, cx + dx - sm.shape[1] / 2, cy - sm.shape[0] / 2, opacity=min(1.0, (tt - a) / 0.15))
        w.put(canvas)
    w.close()


ENDCARD_VARIANTS = {
    'follow': '加号翻勾：黑网格底中央白边圆头像弹出，下面红色加号一翻变成白底红勾，头像上方弧形黄字账号名，下面一行「感谢关注」',
    'name': '账号名放大滚入：黑底中央「@账号」带回弹地放大滚入，配一声「叮」',
}


def endcard(l, tl, W, H, FPS, st, work, aroll, out, preview=False):
    """l: {variant, avatar（头像图片，不写就用口播画面里的人脸）, crop, name（账号名）, text（下面一行字）}。"""
    if is_landscape(W, H):
        return _landscape_endcard(l, tl, W, H, FPS, st, work, aroll, out, preview)
    S, style = unit(W, H), _style(st)
    v = l.get('variant', 'follow')
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    w = Writer(out, W, H, FPS, preview=preview)
    if v == 'name':
        name = fit_text(l.get('name', '@账号'), H * 0.07, W * 0.88, '#FFFFFF', 'title', style)
        sub = fit_text(l['text'], H * 0.026, W * 0.8, '#FFFFFFB0', 'body', style) if l.get('text') else None
        for i in range(n):
            tt = i / FPS
            canvas = np.zeros((H, W, 3), np.uint8)
            k = max(0.05, 0.5 + 0.5 * eback(tt / 0.5))
            sm = scale_rgba(name, k)
            paste(canvas, sm, (W - sm.shape[1]) / 2, H * 0.45 - sm.shape[0] / 2 + (1 - ease(tt / 0.5, 'out')) * H * 0.06, opacity=min(1.0, tt / 0.15))
            if sub is not None:
                paste(canvas, sub, (W - sub.shape[1]) / 2, H * 0.53, opacity=ease((tt - 0.4) / 0.3))
            w.put(canvas)
        w.close()
        return
    bgs = (np.clip(fr * 0.6, 0, 255).astype(np.uint8) for fr in bg_frames('grid:white', W, H, FPS, n, work))
    d = int(W * 0.30) // 2 * 2
    bd = int(6 * S)
    if l.get('avatar'):
        im = Image.open(_src(l['avatar'], work)).convert('RGB')
        s_ = min(im.size)
        face = np.array(im.crop(((im.width - s_) // 2, (im.height - s_) // 2, (im.width - s_) // 2 + s_, (im.height - s_) // 2 + s_)).resize((d, d), Image.LANCZOS))
        D = d + 2 * bd
        av0 = ss(D, D, lambda dr, k: dr.ellipse([0, 0, D * k - 1, D * k - 1], fill=(255, 255, 255, 255)))
        over(av0, np.dstack([face, (circle_mask(d)[..., 0] * 255).astype(np.uint8)]), bd, bd)
        avs = (av0 for _ in range(n))
    else:
        avs = avatar_frames(aroll, l, d, bd, dur, FPS, W, H)
    bdm = int(W * 0.085)
    plus = ss(bdm, bdm, lambda dr, k: (dr.ellipse([0, 0, bdm * k - 1, bdm * k - 1], fill=hex_rgba('#FE2C55')),
                                       dr.rectangle([bdm * k * 0.27, bdm * k * 0.45, bdm * k * 0.73, bdm * k * 0.55], fill=(255, 255, 255, 255)),
                                       dr.rectangle([bdm * k * 0.45, bdm * k * 0.27, bdm * k * 0.55, bdm * k * 0.73], fill=(255, 255, 255, 255))))
    check = ss(bdm, bdm, lambda dr, k: (dr.ellipse([0, 0, bdm * k - 1, bdm * k - 1], fill=(255, 255, 255, 255)),
                                        dr.line([(bdm * k * 0.28, bdm * k * 0.52), (bdm * k * 0.44, bdm * k * 0.68), (bdm * k * 0.73, bdm * k * 0.36)],
                                                fill=hex_rgba('#FE2C55'), width=int(bdm * k * 0.11))))
    cx, cy = W * 0.5, H * 0.40
    arc = np.zeros((H, W, 4), np.uint8)   # 头像上方沿圆弧排的账号名
    name = l.get('name', '')
    if name:
        R = d / 2 + bd + W * 0.06
        size = H * 0.030
        chars = [trim(text_img(c, size, YELLOW, 'title', style, pad=2)) if c.strip() else None for c in name]
        widths = [c.shape[1] if c is not None else size * 0.35 for c in chars]
        span = sum(widths) + size * 0.08 * (len(chars) - 1)
        ang = -np.pi / 2 - span / R / 2
        for c, cw_ in zip(chars, widths):
            mid = ang + cw_ / 2 / R
            if c is not None:
                r_ = rotate_rgba(c, -np.degrees(mid + np.pi / 2))
                over(arc, r_, cx + np.cos(mid) * R - r_.shape[1] / 2, cy + np.sin(mid) * R - r_.shape[0] / 2)
            ang += (cw_ + size * 0.08) / R
    txt = fit_text(l.get('text', '感谢关注'), H * 0.032, W * 0.86, '#FFFFFF', 'body', style)
    for i in range(n):
        tt = i / FPS
        canvas = next(bgs).copy()
        av = next(avs)
        k = max(0.05, 0.6 + 0.4 * eback(tt / 0.3))
        a_ = scale_rgba(av, k) if abs(k - 1) > 0.001 else av
        paste(canvas, a_, cx - a_.shape[1] / 2, cy - a_.shape[0] / 2, opacity=min(1.0, tt / 0.1))
        by = cy + av.shape[0] / 2 - bdm * 0.45
        if tt >= 0.25:   # 加号 0.45 秒后横向翻成白底红勾，再弹一下
            if tt < 0.55:
                b, sx = plus, 1.0 if tt < 0.45 else 1 - (tt - 0.45) / 0.1
            else:
                b, sx = check, min(1.0, (tt - 0.55) / 0.1) * (1 + 0.2 * np.sin(np.pi * min(1.0, max(0.0, (tt - 0.65) / 0.15))))
            bw = max(1, int(b.shape[1] * sx))
            bh = int(b.shape[0] * (1 + 0.2 * np.sin(np.pi * min(1.0, max(0.0, (tt - 0.65) / 0.15)))) if b is check else b.shape[0])
            bb = np.array(Image.fromarray(b, 'RGBA').resize((bw, max(1, bh)), Image.BILINEAR))
            paste(canvas, bb, cx - bw / 2, by - (bb.shape[0] - b.shape[0]) / 2, opacity=min(1.0, (tt - 0.25) / 0.1))
        paste(canvas, arc, 0, 0, opacity=ease((tt - 0.2) / 0.3))
        paste(canvas, txt, cx - txt.shape[1] / 2, H * 0.60, opacity=ease((tt - 0.6) / 0.3))
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- 横屏章节与整页卡片
def _landscape_fog(t, W, H, FPS, st, work, aroll, out):
    S, style = unit(W, H), _style(st)
    dur = t['t1'] - t['t0']
    panel = t.get('variant', 'panel') == 'panel'
    # 面板移到侧边，整页数字窗则把说明放到另一半幅。
    cx, cy, sw, sh = _side_box(t, W, H) if panel else (W * 0.28, H * 0.43, W * 0.40, H * 0.66)
    num = str(t.get('number', '1'))
    shapes = [str(x) for x in t.get('shapes', [])] or [num]
    glyphs = [bigtype._fit(trim(text_img(x, (260 if panel else 620) * S, '#FFFFFF', 'en_display', style, pad=4, italic=0.16)), sw * 0.8, sh * 0.8) for x in shapes]
    sample = next(read(aroll, t['t0'] + 0.2, 1 / FPS, (96, 54), FPS))
    dark = t.get('dark', float(sample.mean()) / 255 > 0.62)
    ink, bg = ('#F4F2EC', '#16161ACC') if dark else ('#16161A', '#FAFAF7CC')
    tx, ty, tw, th = _side_box(dict(t, side='right'), W, H)
    title = fit_text(t.get('text', ''), 60 * S, sw * 0.88 if panel else tw * 0.92, ink, 'title', style)
    en = fit_text(t.get('en') or '', 26 * S, sw * 0.88, ink, 'en', style)
    labels = [fit_text(x, 34 * S, sw * 0.88, ink, 'body', style) for x in (t.get('items') or [])[:3]]
    cut = None
    if not panel and t.get('person', 'auto') is not False:
        import matte
        cut = matte.cutouts(aroll, t['t0'], dur, W, H, FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(max(1, round(dur * FPS))):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        if panel:
            pw, ph = int(sw), int(sh)
            card = np.full((ph, pw, 4), hex_rgba(bg), np.uint8)
            g = glyphs[0]
            mask = np.zeros_like(card)
            keytext.put(mask, g, pw / 2, ph * 0.25)
            card[..., 3] = (card[..., 3] * (1 - mask[..., 3] / 255)).astype(np.uint8)
            keytext.put(card, title, pw / 2, ph * 0.49)
            keytext.put(card, en, pw / 2, ph * 0.60)
            for j, label in enumerate(labels):
                keytext.put(card, label, pw / 2, ph * (0.71 + j * 0.10))
            p = ease(tt / 0.4, 'out')
            keytext.put(c, card, cx + (1 - p) * sw * 0.2, cy, p)
        else:
            c[...] = hex_rgba(bg)
            k = min(1, max(0, (tt - t.get('shape_at', 1.0)) / 0.3))
            hole = np.zeros_like(c)
            if len(glyphs) > 1 and k > 0:
                keytext.put(hole, rotate_rgba(glyphs[0], 90 * k), cx, cy, 1 - k)
                keytext.put(hole, rotate_rgba(glyphs[-1], -90 * (1 - k)), cx, cy, k)
            else:
                keytext.put(hole, glyphs[0], cx, cy)
            c[..., 3] = (c[..., 3] * (1 - hole[..., 3] / 255)).astype(np.uint8)
            if cut is not None:
                c[..., 3] = (c[..., 3] * (1 - next(cut))).astype(np.uint8)
            keytext.put(c, title, tx, H * 0.37)
            keytext.put(c, bigtype._fit(en, tw * 0.92), tx, H * 0.49)
            if t.get('enter') == 'cover':
                yy = np.arange(H)[:, None]
                top = H * (1 - ease(tt / 0.3, 'in'))
                c[..., 3] = (c[..., 3] * np.clip((yy - top) / (0.1 * H), 0, 1)).astype(np.uint8)
            if t.get('exit') == 'door' and tt > dur - 0.5:
                from motion import _quad_coeffs
                p = ease((tt - dur + 0.5) / 0.5, 'inout')
                xr, grow = W * np.cos(p * np.pi / 2), H * 0.12 * np.sin(p * np.pi / 2)
                if xr > 2:
                    c = np.array(Image.fromarray(c).transform((W, H), Image.PERSPECTIVE, _quad_coeffs(
                        [(0, 0), (xr, -grow), (xr, H + grow), (0, H)], [(0, 0), (W, 0), (W, H), (0, H)]), Image.BILINEAR))
                else:
                    c[...] = 0
        fin = 0.02 if not panel and t.get('enter') == 'cover' else 0.2
        fout = 0 if panel and t.get('_relay') else 0.02 if not panel and t.get('exit') == 'door' else 0.2
        c[..., 3] = (c[..., 3] * env(tt, dur, fin, fout)).astype(np.uint8)
        w.put(c)
    w.close()


def _landscape_chapter(t, W, H, FPS, st, work, aroll, out):
    S, style = unit(W, H), _style(st)
    v = t.get('variant', 'hand')
    dur = t['t1'] - t['t0']
    n = max(1, round(dur * FPS))
    if v == 'swap':
        cx, cy, sw, sh = _side_box(t, W, H)
        main = fit_text(t.get('main', ''), 60 * S, sw * 0.90, '#FFFFFF', 'title', style)
        txt = fit_text(t.get('text', ''), 60 * S, sw * 0.84, '#FFFFFF', 'title', style)
        block = np.full((txt.shape[0] + int(36 * S), txt.shape[1] + int(36 * S), 4), hex_rgba('#0A1EFF'), np.uint8)
        keytext.put(block, txt, block.shape[1] / 2, block.shape[0] / 2)
        w = Writer(out, W, H, FPS, alpha=True)
        for i in range(n):
            tt = i / FPS
            c = np.zeros((H, W, 4), np.uint8)
            keytext.put(c, main if tt < t.get('swap_at', min(1, dur * 0.4)) else block, cx, cy, env(tt, dur, 0.15, 0.2))
            w.put(c)
        w.close()
        return
    bgs = warm_blur(aroll, t['t0'], dur, W, H, FPS, n, work, (1.12, 0.97, 0.80))
    num = str(t.get('number', '01'))
    title = fit_text(t.get('text', ''), 150 * S if v == 'hand' else 86 * S, W * 0.45, t.get('color', '#F0E6C0'), 'hand' if v == 'hand' else 'serif', style)
    if v == 'hand':
        title = bigtype._fit(rotate_rgba(title, 8), W * 0.55, H * 0.32)
    number = fit_text(num, 120 * S, W * 0.25, '#FFFFFF', 'serif', style)
    sub = fit_text(t.get('sub') or f'第 {num} 节', 38 * S, W * 0.42, '#FFFFFF', 'body', style)
    en = fit_text(t.get('en') or '', 30 * S, W * 0.42, '#FFFFFFB3', 'en', style, spacing=4 * S)
    prev = None
    if v == 'preview':
        pw, ph = int(W * 0.40) // 2 * 2, int(H * 0.48) // 2 * 2
        prev = read(_src(t['preview'], work) if t.get('preview') else aroll, t.get('preview_in', 0) if t.get('preview') else t['t0'], dur, (pw, ph), FPS)
        pm = _rmask(pw, ph, 28 * S)
    sign = bigtype._fit(rotate_rgba(trim(text_img(t.get('sign') or f'Chapter {num}', 110 * S, '#4A6BFF', fontfile=SIGN_FONT, pad=8)), 8), W * 0.30, H * 0.30)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, bg in enumerate(bgs):
        tt = i / FPS
        c = np.dstack([bg, np.full((H, W), 255, np.uint8)])
        keytext.put(c, number, W * 0.15, H * 0.20, ease(tt / 0.3))
        keytext.put(c, title, W * (0.29 if prev is not None else 0.38), H * 0.42, ease(tt / 0.5))
        over(c, sub, W * 0.08, H * 0.62, ease((tt - 0.2) / 0.3))
        over(c, en, W * 0.08, H * 0.71, ease((tt - 0.3) / 0.3))
        if prev is not None:
            pf = next(prev)
            rgba = np.dstack([pf, (pm[..., 0] * 255).astype(np.uint8)])
            keytext.put(c, rgba, W * 0.72, H * 0.43, ease((tt - 0.2) / 0.35))
        else:
            keytext.put(c, sign, W * 0.78, H * 0.43, ease((tt - 0.3) / 0.3))
        c[..., 3] = int(255 * env(tt, dur, 0.2, 0.2))
        w.put(c)
    w.close()


def _landscape_overview(l, tl, W, H, FPS, st, work, aroll, out, preview):
    S, style = unit(W, H), _style(st)
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    v = l.get('variant', 'grid')
    items = l.get('items') or chapter_items(tl, aroll, W, H, FPS)
    items = [dict(x, num=x.get('num', f'{j + 1:02d}')) for j, x in enumerate(items)][:12 if v == 'list' else 5 if v == 'tilted_collage' else 4]
    if not items:
        raise SystemExit('overview 版式：时间线里没有章节页，也没写 items')
    times = item_times(l, len(items), OVERVIEW_EVERY.get(v, 0.3))
    title = fit_text(l.get('title') or '本期要点', 64 * S, W * 0.70, '#FFFFFF', 'serif', style)
    sprites = []
    cols = min(3, len(items)) if v == 'tilted_collage' else min(2, len(items))
    rows = (len(items) + cols - 1) // cols
    for j, it in enumerate(items):
        col, row = j % cols, j // cols
        cw = int(W * 0.84 / cols - 24 * S)
        ch = int(H * 0.54 / rows - 24 * S)
        if v in ('grid', 'tilted_collage'):
            pic = _cover(_frame_of(it, aroll, work, W, H, FPS), cw, ch)
            card = np.dstack([(pic * 0.55).astype(np.uint8), (_rmask(cw, ch, 24 * S)[..., 0] * 255).astype(np.uint8)])
        else:
            card = infocard.rrect(cw, ch, 18 * S, ['#7A3CF0', '#B94719', '#326944', '#36363E'][j % 4] if v == 'toc' else '#FFFFFF12')
        if v in ('toc', 'list'):
            number = fit_text(it['num'], min(80 * S, ch * 0.66), cw * 0.18, '#FFFFFF', 'en_display', style)
            text = fit_text(it['text'], 48 * S, cw * 0.66, '#FFFFFF', 'title', style)
            keytext.put(card, number, cw * 0.15, ch / 2)
            keytext.put(card, text, cw * 0.59, ch / 2)
        else:
            over(card, fit_text(it['num'], 110 * S if v == 'grid' else 68 * S, cw * 0.8, '#FFFFFF', 'en_display', style), cw * 0.08, ch * 0.12)
            over(card, fit_text(it['text'], 46 * S, cw * 0.84, '#FFFFFF', 'title', style), cw * 0.08, ch * 0.70)
        if v in ('toc', 'tilted_collage'):
            card = rotate_rgba(card, [-3, 3, -2, 2, 0][j % 5])
        cx = W * 0.08 + (col + 0.5) * W * 0.84 / cols
        if v == 'tilted_collage' and row == rows - 1:
            count = len(items) - row * cols
            cx = W / 2 + (col - (count - 1) / 2) * W * 0.84 / cols
        sprites.append((card, cx, H * 0.28 + (row + 0.5) * H * 0.54 / rows, times[j]))
    bgs = warm_blur(aroll, l['t0'], dur, W, H, FPS, n, work, (0.65, 0.45, 0.35))
    w = Writer(out, W, H, FPS, preview=preview)
    for i, bg in enumerate(bgs):
        tt = i / FPS
        c = bg.copy()
        paste(c, title, W * 0.08, H * 0.12)
        for j, (g, cx, cy, at) in enumerate(sprites):
            p = ease((tt - at) / 0.3, 'out')
            if v == 'tilted_collage':
                cx += np.sin(tt * 0.6 + j) * 8 * S
            paste(c, g, cx - g.shape[1] / 2, cy - g.shape[0] / 2 + (1 - p) * 20 * S, opacity=p)
        w.put(c)
    w.close()


def _landscape_endcard(l, tl, W, H, FPS, st, work, aroll, out, preview):
    S, style = unit(W, H), _style(st)
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    name = fit_text(l.get('name', '@账号'), 84 * S, W * 0.50, '#FFFFFF', 'title', style)
    sub = fit_text(l.get('text') or '感谢关注', 44 * S, W * 0.50, YELLOW, 'body', style)
    is_name = l.get('variant', 'follow') == 'name'
    avs = avatar_frames(aroll, l, int(H * 0.26), int(5 * S), dur, FPS, W, H) if not is_name and not l.get('avatar') else None
    avatar = None
    if l.get('avatar'):
        im = Image.open(_src(l['avatar'], work)).convert('RGB')
        avatar = infocard._round(Image.fromarray(_cover(np.array(im), int(H * 0.26), int(H * 0.26))), H * 0.13)
    bgs = bg_frames('black' if is_name else 'grid', W, H, FPS, n, work)
    w = Writer(out, W, H, FPS, preview=preview)
    for i, bg in enumerate(bgs):
        tt = i / FPS
        c = bg.copy()
        p = ease(tt / 0.3, 'out')
        if is_name:
            sm = scale_rgba(name, max(0.05, 0.5 + 0.5 * eback(tt / 0.5)))
            paste(c, sm, (W - sm.shape[1]) / 2, H * 0.45 - sm.shape[0] / 2 + (1 - ease(tt / 0.5, 'out')) * H * 0.06, opacity=min(1.0, tt / 0.15))
            paste(c, sub, (W - sub.shape[1]) / 2, H * 0.58, opacity=ease((tt - 0.4) / 0.3))
            w.put(c)
            continue
        av = next(avs) if avs is not None else avatar
        if l.get('variant', 'follow') == 'follow':
            av = avatar if avatar is not None else av
            paste(c, av, W * 0.26 - av.shape[1] / 2, H * 0.44 - av.shape[0] / 2, opacity=p)
            sign = infocard.pill('+' if tt < 1.1 else '✓', 50 * S, '#FFFFFF', '#FE2C55', S)
            paste(c, sign, W * 0.26 - sign.shape[1] / 2, H * 0.61, opacity=ease((tt - 0.4) / 0.2))
            x = W * 0.40
        else:
            x = (W - name.shape[1]) / 2
        paste(c, name, x, H * 0.34 + (1 - p) * 30 * S, opacity=p)
        paste(c, sub, x, H * 0.53, opacity=ease((tt - 0.2) / 0.3))
        w.put(c)
    w.close()
