"""开场与结构（手法库第 10 批）。

逐帧画的版式（titles 的 layout，cards.title_clip 转过来）：
- montage    开场快闪蒙太奇（montage_flash_open）：chaos 截图乱闪拼凑 / macro 一段段主题镜头卡点切、落在一张大标题上
- collage    卡片拼贴预告（collage_cards_title）：fan 扇形铺开 / scatter 散点快闪 / wall 曲面视频墙 / paper 纸页战绩拼贴
- textfirst  黑底文字先行开场（opening_text_first）：stack 逐行累加再露脸 / meme 逐句替换配表情包 / warning 警告式内容预告
- qframe     反问钩子画框问号（opening_question_frame）：人缩进手机比例白边框，暗色立体网格底，四周红色问号，胸前手写字
- poster     整屏海报标题页（poster_title_page）：cinema 黑底红字片名 / film 胶片齿孔做旧页 / grid 网格底抠像封面 / popart 波普网点 / magazine 杂志封面
- coverframe 首帧封面图（cover_first_frame）：抠像人带白贴纸边、倾斜彩色标题，片头只停 0.15 秒
- askpage    求赞收藏提醒页（engagement_ask_page）：flank 黑底椭圆窗两侧大字 / lines 竖排三行收藏提醒
- gesture    圆头像手势章节卡（chapter_avatar_gesture，章节载体）：虚化底上白边圆头像弹入，下方「第 N 招」
- cutnum     抠像剪纸大数字章节页（chapter_cutout_numeral，章节载体）：黑网格底、白描边抠像、剪纸彩色大数字，0.8 秒后换红网点底压章节名
- inkecho    结尾回扣开场大字（ending_echo_keyword）：开场那个大字在人身后水墨晕开，六成不透明
- actionrow  点赞转发评论条（cta_action_row）：三个词依次出现，薄荷绿短横相连，左上一张小名片
- slogan     固定口号收尾（signature_outro）：口播缩成圆角卡片露出黑网格，「学会了」故障闪入，「去」「练」两个黄字分列左右
常驻层（timeline 顶层，render 在字幕下面叠）：points 角落要点编号（point_index_marker）、hud 系列名水印或进度条小人（persistent_hud）。
展开类（prepare 在渲染前展开成 broll、layout、zoom、配乐留白）：cover 首帧封面、montage_cuts 一词一镜快剪（fast_cut_word_montage）、
section_ends 段落收尾推高收束（section_end_climax）。插入反应镜头（reaction_cutaway）在 effects.splice_inserts，多了 text 花字。
尺寸按短边 1080 的像素值乘 S。
"""
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bigtype import EN, SERIF, TYPE, _avatar, _corner_char, _fit, _glyphs, _head_square, _opaque, _paper_noise, _person, _pop, _soft_bg
from fonts import FONTS
from keytext import BRUSH, HAND, HEAVY, _clamp, blur, eback, fade_out, frames, icon_png, put, rough, scale, with_shadow, word
from kvlib import unit, is_landscape, safe_zones, face_crop, pip_params, CHAPTER_LAYOUTS, hex_rgba, is_image, probe
from motion import Writer, bg_frames, ease, over, read, resize, rotate_rgba, text_img, trim

SCRIPT = FONTS / 'GreatVibes-Regular.ttf'
BEBAS = FONTS / 'BebasNeue-Regular.ttf'

LAYOUTS = ('montage', 'collage', 'textfirst', 'qframe', 'poster', 'coverframe', 'askpage', 'gesture', 'cutnum', 'inkecho', 'actionrow', 'slogan')


def clip(t, W, H, FPS, st, work, aroll, out):
    {'montage': montage, 'collage': collage, 'textfirst': textfirst, 'qframe': qframe, 'poster': poster, 'coverframe': coverframe,
     'askpage': askpage, 'gesture': gesture, 'cutnum': cutnum, 'inkecho': inkecho, 'actionrow': actionrow,
     'slogan': slogan}[t['layout']](t, W, H, FPS, st, work, aroll, out)


# ---------------------------------------------------------------- 小工具
def _still(src, W, H, at=0.0):
    return next(read(src, at, 1 / 30, (W, H), 30))


def _shots(srcs, n, dur, W, H, FPS, seed):
    """从素材池轮着取 n 段，每段 dur 秒，视频从不同位置截。返回每段的帧列表。"""
    rng = random.Random(seed)
    out = []
    for k in range(n):
        s = srcs[k % len(srcs)]
        off = 0.0 if is_image(s) else rng.uniform(0, max(0.0, probe(s)['duration'] - dur - 0.1))
        out.append(list(read(s, off, max(dur, 1 / FPS), (W, H), FPS)))
    return out


def _card(src, w, S, radius=14, border=0, at=0.0, ratio=None, canvas=(1080, 1920)):
    """素材卡：按宽 w 缩放（ratio 给了就裁成这个宽高比），圆角、白边、投影。"""
    if not is_image(src):   # 录屏开头常是黑屏：从三成处往后取
        d = probe(src)['duration']
        at = (d * 0.3 + at) % max(0.1, d - 0.1)
    # 竖屏沿用旧的取帧分辨率，避免多一次不同的缩放影响像素。
    still_canvas = canvas if is_landscape(*canvas) else (1080, 1920)
    im = Image.fromarray(_still(src, *still_canvas, at) if not is_image(src) else np.array(Image.open(src).convert('RGB')))
    if ratio:
        cw, ch = im.width, im.height
        if cw / ch > ratio:
            nw = int(ch * ratio)
            im = im.crop(((cw - nw) // 2, 0, (cw - nw) // 2 + nw, ch))
        else:
            nh = int(cw / ratio)
            im = im.crop((0, (ch - nh) // 2, cw, (ch - nh) // 2 + nh))
    h = int(w * im.height / im.width)
    im = im.resize((int(w), h), Image.LANCZOS).convert('RGBA')
    b = int(border)
    c = Image.new('RGBA', (int(w) + 2 * b, h + 2 * b), (255, 255, 255, 255) if b else (0, 0, 0, 0))
    c.paste(im, (b, b))
    m = Image.new('L', c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, c.width - 1, c.height - 1], radius=int(radius * S), fill=255)
    c.putalpha(m)
    return with_shadow(np.array(c), 14 * S, 0.45, dy=int(8 * S))


def _rich(text, hl, size, color, hl_color, fontfile=HEAVY, stroke=0, stroke_color='#000000'):
    """一行字，hl 里的词换色；返回 RGBA（高度按字号固定，几行叠起来行距一致）。"""
    f = ImageFont.truetype(str(fontfile), int(size))
    marks = [0] * len(text)
    for w_ in hl or []:
        i = text.find(w_)
        if i >= 0:
            marks[i:i + len(w_)] = [1] * len(w_)
    pad = int(size * 0.15) + stroke
    wd = int(f.getlength(text)) + 2 * pad
    im = Image.new('RGBA', (max(1, wd), int(size * 1.3) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for ch, m in zip(text, marks):
        d.text((x, pad + size), ch, font=f, anchor='ls', fill=hex_rgba(hl_color if m else color), stroke_width=stroke, stroke_fill=hex_rgba(stroke_color))
        x += f.getlength(ch)
    return np.array(im)


def _grid_bg(W, H, S, bg='#0E0E10', line='#2A2A2E', step=0.06):
    im = Image.new('RGBA', (W, H), hex_rgba(bg))
    d = ImageDraw.Draw(im)
    g = int(W * step)
    for x in range(0, W, g):
        d.line([(x, 0), (x, H)], fill=hex_rgba(line), width=max(1, int(2 * S)))
    for y in range(0, H, g):
        d.line([(0, y), (W, y)], fill=hex_rgba(line), width=max(1, int(2 * S)))
    return np.array(im)


def _rounded_frame(fr, w, h, r, border, col='#FFFFFF'):
    """口播缩成 w×h 的圆角卡片，外圈白边。"""
    im = Image.fromarray(fr).resize((int(w), int(h)), Image.BILINEAR).convert('RGBA')
    b = int(border)
    c = Image.new('RGBA', (int(w) + 2 * b, int(h) + 2 * b), hex_rgba(col))
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=int(r), fill=255)
    c.paste(im, (b, b), m)
    m2 = Image.new('L', c.size, 0)
    ImageDraw.Draw(m2).rounded_rectangle([0, 0, c.width - 1, c.height - 1], radius=int(r + b), fill=255)
    c.putalpha(m2)
    return np.array(c)


def _outline_person(fr, a, px):
    """抠像人加一圈白色贴纸描边（透明度膨胀 px 像素填白）。"""
    k = max(1, int(px)) * 2 + 1
    small = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((a.shape[1] // 2, a.shape[0] // 2), Image.BILINEAR)
    big = np.array(small.filter(ImageFilter.MaxFilter(min(k // 2 * 2 + 1, 31))).resize((a.shape[1], a.shape[0]), Image.BILINEAR), np.float32) / 255
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., :3] = 255
    out[..., 3] = (np.clip(big * 1.4, 0, 1) * 255).astype(np.uint8)
    over(out, _person(fr, a), 0, 0)
    return out


def _glitch(spr, rng, S, amt=1.0):
    """故障闪：红青错位加几道横切片。"""
    off = int(rng.uniform(8, 16) * S * amt)
    h = spr.shape[0]
    c = np.zeros((h, spr.shape[1] + 2 * off, 4), np.uint8)
    red, cyan = spr.copy(), spr.copy()
    red[..., :3] = (255, 45, 85)
    cyan[..., :3] = (25, 224, 255)
    over(c, red, 0, 0, 0.85)
    over(c, cyan, 2 * off, 0, 0.85)
    sl = spr.copy()
    for _ in range(4):
        y0 = rng.randint(0, max(1, h - 8))
        hh = rng.randint(max(2, int(6 * S)), max(3, h // 5))
        sl[y0:y0 + hh] = np.roll(sl[y0:y0 + hh], rng.randint(-int(30 * S), int(30 * S)), axis=1)
    over(c, sl, off, 0)
    return c


def _halftone(W, H, color, dot, S, bg=None):
    im = Image.new('RGBA', (W, H), hex_rgba(bg) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    g = int(dot * 2.2)
    for j, y in enumerate(range(0, H + g, g)):
        for x in range((g // 2) * (j % 2), W + g, g):
            d.ellipse([x - dot / 2, y - dot / 2, x + dot / 2, y + dot / 2], fill=hex_rgba(color))
    return np.array(im)


def _gold_title(text, size, S, maxw):
    """金色渐变字加蓝描边。"""
    g = _fit(word(text, size, '#FFFFFF', HEAVY, stroke=int(10 * S), stroke_color='#1F4FBF'), maxw)
    yy = np.linspace(0, 1, g.shape[0], dtype=np.float32)[:, None, None]
    gold = np.array([255, 232, 130], np.float32) * (1 - yy) + np.array([242, 168, 20], np.float32) * yy
    inner = g[..., :3].mean(-1, keepdims=True) > 200
    g[..., :3] = np.where(inner, gold, g[..., :3]).astype(np.uint8)
    return with_shadow(g, 10 * S, 0.5, dy=int(6 * S))


# ---------------------------------------------------------------- montage 开场快闪蒙太奇
MONTAGE_VARIANTS = {
    'chaos': '乱闪拼凑：截图每张只停 2~4 帧，带横向拖影、红黄偏色和圆形暗角，像信号在跳，后面接干净画面做对比',
    'macro': '卡点接标题：一段段 0.5 秒的主题镜头卡点切，最后落在一张图上，正中金黄色描蓝边大标题',
}


def _side(W, H, right=False):
    x0, y0, x1, y1 = safe_zones(W, H)['text'][int(right)]
    x0, x1 = max(0.05, x0), min(0.95, x1)
    return W * (x0 + x1) / 2, H * (y0 + y1) / 2, W * (x1 - x0), H * (y1 - y0)


def montage(t, W, H, FPS, st, work, aroll, out):
    from effects import _hsmear
    S = unit(W, H)
    v = t.get('variant', 'macro')
    dur, n = frames(t, FPS)
    srcs = t['srcs']
    seed = int(t['t0'] * 100)
    rng = random.Random(seed)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'chaos':
        per = [rng.randint(2, 4) for _ in range(n)]
        cuts = np.cumsum(per)
        pics = [_still(s, W, H, rng.uniform(0, max(0.0, probe(s)['duration'] - 0.2)) if not is_image(s) else 0) for s in srcs]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        vig = np.clip(1.15 - np.hypot((xx - W / 2) / (W * 0.62), (yy - H / 2) / (H * 0.5)) ** 2 * 0.9, 0.08, 1)[..., None]
        for i in range(n):
            k = int(np.searchsorted(cuts, i, side='right'))
            fr = pics[k % len(pics)].astype(np.float32)
            z = 1.04 + 0.04 * (k % 3)
            fr = resize(fr.astype(np.uint8), W * z, H * z)[int(H * (z - 1) / 2):int(H * (z - 1) / 2) + H, int(W * (z - 1) / 2):int(W * (z - 1) / 2) + W]
            fr = _hsmear(fr, W * 0.012 * (1 + k % 2)).astype(np.float32)
            tint = np.array((200, 16, 46) if k % 2 else (245, 208, 0), np.float32)
            fr = fr * 0.7 + tint * 0.3 if rng.random() < 0.7 else fr
            c = _opaque((fr * vig).clip(0, 255).astype(np.uint8))
            c[..., 3] = int(255 * fade_out(i / FPS, dur, 0.06))
            w.put(c)
        w.close()
        return
    per = t.get('per', 0.5)
    m = max(1, int((dur - t.get('hold', 1.2)) / per))
    shots = _shots(srcs, m, per, W, H, FPS, seed)
    last = _still(srcs[-1], W, H) if is_image(srcs[-1]) else shots[-1][-1]
    title = _gold_title(t['text'], H * 0.1, S, W * 0.9) if t.get('text') else None
    t_title = m * per
    for i in range(n):
        tt = i / FPS
        if tt < t_title:
            k = min(m - 1, int(tt / per))
            f = shots[k]
            c = _opaque(f[min(len(f) - 1, int((tt - k * per) * FPS))])
        else:   # 落在最后一张图上，大标题 0.25 秒从 110% 落定
            c = _opaque((last * 0.75).astype(np.uint8))
            if title is not None:
                p = ease((tt - t_title) / 0.25, 'out')
                put(c, scale(title, 1.1 - 0.1 * p), W / 2, H * t.get('y', 0.45), min(1.0, p * 2))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- collage 卡片拼贴预告
COLLAGE_VARIANTS = {
    'fan': '扇形铺开：一组竖卡在画面中部扇形错落叠放，0.08 秒一张弹入，上下各一行大字夹住卡堆',
    'scatter': '散点快闪：四五张图 0.2 秒一张飞入，各自歪 6~15 度散在画面不同位置',
    'wall': '曲面视频墙：二十来张截图拼成向外鼓的弧形墙，0.5 秒内展平，中央压红色超大字',
    'paper': '纸页战绩拼贴：牛皮纸底上两三张倾斜的截图卡，红色手写数字直接写在卡上，右下羽化圆头像在说话',
}


def _bulge(img, k):
    """桶形外鼓（k=0 不变形）。"""
    import cv2
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)
    r2 = nx * nx + ny * ny
    f = 1 - k * 0.35 * (1 - r2.clip(0, 1))
    mx = (nx * f) * (w / 2) + w / 2
    my = (ny * f) * (h / 2) + h / 2
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def collage(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'fan')
    dur, n = frames(t, FPS)
    srcs = t['srcs']
    seed = int(t['t0'] * 100)
    rng = random.Random(seed)
    w = Writer(out, W, H, FPS, alpha=True)
    head = with_shadow(_fit(word(t['text'], H * 0.06, '#FFFFFF', HEAVY), W * 0.9), 9 * S, 0.6) if t.get('text') else None
    foot = with_shadow(_fit(word(t['text2'], H * 0.05, t.get('color2', '#FFD23F'), HEAVY), W * 0.9), 9 * S, 0.6) if t.get('text2') else None
    if v == 'wall':
        cols, rows = (6, 4) if is_landscape(W, H) else (4, 6)
        tw, th = W // cols, H // rows
        wall = np.zeros((H, W, 3), np.uint8)
        for k in range(cols * rows):
            s = srcs[k % len(srcs)]
            im = _still(s, tw, th, (k * 0.7) % max(0.1, probe(s)['duration'] - 0.2) if not is_image(s) else 0)
            x, y = (k % cols) * tw, (k // cols) * th
            wall[y + 3:y + th - 3, x + 3:x + tw - 3] = im[3:th - 3, 3:tw - 3]
        big = _fit(word(t.get('big') or t['text'], H * 0.2, '#E21B23', HEAVY, stroke=int(10 * S), stroke_color='#FFFFFF'), W * 0.9)
        for i in range(n):
            tt = i / FPS
            p = ease(tt / 0.5, 'out')
            c = _opaque((_bulge(wall, 1 - p) * (0.55 + 0.25 * p)).astype(np.uint8))
            q = ease((tt - 0.45) / 0.25, 'out')
            if q > 0:
                put(c, with_shadow(scale(big, 1.3 - 0.3 * q), 14 * S, 0.6), W / 2, H * 0.48, min(1.0, q * 2))
            c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    if v == 'paper':
        import matte
        page = _paper_noise(W, H, (190, 152, 104), seed, 9)
        cards = [_card(s, W * (0.25 if is_landscape(W, H) else 0.56), S, radius=10, border=8 * S, canvas=(W, H)) for s in srcs[:3]]
        if is_landscape(W, H):
            cards = [_fit(g, W * 0.25, H * 0.42) for g in cards]
        rots = [-7, 5, -3]
        pos = [(0.22, 0.48), (0.50, 0.45), (0.78, 0.48)] if is_landscape(W, H) else [(0.4, 0.3), (0.58, 0.52), (0.38, 0.7)]
        nums = t.get('numbers') or []
        every = t.get('every', 1.0)
        D = int(H * (0.26 if is_landscape(W, H) else 0.2))
        sq = None
        for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
            tt = i / FPS
            c = page.copy()
            for j, cd in enumerate(cards):
                p = ease((tt - j * every) / 0.3, 'out')
                if p > 0:
                    put(c, rotate_rgba(scale(cd, 1.12 - 0.12 * p), rots[j % 3]), W * pos[j][0], H * pos[j][1], min(1.0, p * 2))
                if j < len(nums):   # 红色手写数字从左往右写出来
                    q = _clamp((tt - j * every - 0.35) / 0.4)
                    if q > 0:
                        g = rough(word(str(nums[j]), H * 0.08, '#C8202A', HAND), seed + j, 0.12)
                        g = g[:, :max(1, int(g.shape[1] * q))]
                        put(c, rotate_rgba(g, rots[j % 3] + 4), W * pos[j][0] - (1 - q) * 0, H * pos[j][1] + H * 0.02)
            if sq is None:
                sq = _head_square(fr, W, H)
                if is_landscape(W, H):
                    sq = _safe_head_square(sq, W, H)
            av = _avatar(fr, sq, D, 0)
            yy, xx = np.mgrid[0:av.shape[0], 0:av.shape[1]].astype(np.float32)
            d = np.hypot(xx - av.shape[1] / 2, yy - av.shape[0] / 2) / (av.shape[0] / 2)
            av[..., 3] = (av[..., 3] * np.clip((1 - d) / 0.15, 0, 1)).astype(np.uint8)   # 羽化圆头像
            put(c, av, W * 0.95 - av.shape[1] / 2 if is_landscape(W, H) else W * 0.8, H * 0.05 + av.shape[0] / 2 if is_landscape(W, H) else H * 0.76, ease(tt / 0.3))
            if head is not None:
                put(c, head, W / 2, H * 0.1, ease(tt / 0.3))
            c[..., 3] = int(255 * min(1.0, tt / 0.12) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    if v == 'fan':
        m = min(7, max(3, len(srcs)))
        cards = [_card(srcs[j % len(srcs)], W * 0.3, S, radius=14, border=5 * S, ratio=9 / 16, at=0.6 * j, canvas=(W, H)) for j in range(m)]
        if is_landscape(W, H):
            cards = [_fit(g, W * 0.17, H * 0.36) for g in cards]
        angs = np.linspace(-22, 22, m)
        xs = np.linspace(0.2, 0.8, m)
        bgs = read(aroll, t['t0'], dur, (W, H), FPS)
        for i in range(n):
            tt = i / FPS
            c = _opaque(_soft_bg(next(bgs), W, H, 0.6))
            for j in range(m):
                p = (tt - 0.15 - 0.08 * j) / 0.15
                if p > 0:
                    yj = H * (0.5 + 0.02 * abs(angs[j]) / 22)
                    put(c, rotate_rgba(scale(cards[j], 1.15 - 0.15 * ease(p, 'out')), -angs[j]), W * xs[j], yj, min(1.0, p * 2))
            if head is not None:
                put(c, head, W / 2, H * (0.15 if is_landscape(W, H) else 0.24), ease(tt / 0.25))
            if foot is not None:
                put(c, foot, W / 2, H * 0.73, ease((tt - 0.15 - 0.08 * m) / 0.25))
            c[..., 3] = int(255 * min(1.0, tt / 0.1) * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    # scatter：叠在口播上，卡片从画外斜着飞进来
    m = min(5, len(srcs)) if len(srcs) >= 4 else len(srcs)
    m = max(m, 4)
    cards = [_card(srcs[j % len(srcs)], W * 0.4, S, radius=12, border=6 * S, at=0.5 * j, canvas=(W, H)) for j in range(m)]
    pos = [(0.27, 0.2), (0.74, 0.3), (0.3, 0.58), (0.72, 0.66), (0.5, 0.42)]
    if is_landscape(W, H):
        cards = [_fit(g, W * 0.19, H * 0.22) for g in cards]
        pos = [(0.17, 0.28), (0.83, 0.28), (0.17, 0.59), (0.83, 0.59), (0.17, 0.44)]
    rots = [rng.choice([-1, 1]) * rng.uniform(6, 15) for _ in range(m)]
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        for j in range(m):
            p = ease((tt - 0.2 * j) / 0.2, 'out')
            if p > 0:
                x0, y0 = pos[j % 5]
                fx, fy = x0 + (0.6 if x0 > 0.5 else -0.6) * (1 - p), y0 + 0.2 * (1 - p)
                put(c, rotate_rgba(cards[j], rots[j] * (1 + (1 - p))), W * fx, H * fy, min(1.0, p * 2))
        if head is not None:
            put(c, head, W / 2, H * 0.08, ease(tt / 0.25))
        c[..., 3] = (c[..., 3] * fade_out(tt, dur, 0.15)).astype(np.uint8)
        w.put(c)
    w.close()


# ---------------------------------------------------------------- textfirst 黑底文字先行开场
TEXTFIRST_VARIANTS = {
    'stack': '逐行累加再露脸：黑底上一行行出字整体上移，关键词红色，最后一行放大，随后白边圆头像从右下滑入',
    'meme': '逐句替换配表情包：上方一行粗白字每两秒换一句，下方固定一张黑白表情包',
    'warning': '警告式内容预告：上方红色「警告」带下划线，下面几行白色宋体小字介绍本期内容，信息量词标黄',
}


def textfirst(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'stack')
    dur, n = frames(t, FPS)
    lines = t['lines']
    hl = t.get('hl') or []
    every = t.get('every', 0.8 if v != 'meme' else 2.0)
    if is_landscape(W, H) and v == 'stack' and 'every' not in t:
        every = min(every, max(0.35, (dur - 1.6) / max(1, len(lines) - 1)))
    ats = t.get('line_at') or [0.15 + every * j for j in range(len(lines))]
    ats = [a if a is not None else 0.15 + every * j for j, a in enumerate(ats)]
    base = _paper_noise(W, H, (10, 10, 10), int(t['t0'] * 100), 4)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'meme':
        imgs = [_fit(with_shadow(word(x, 64 * S if is_landscape(W, H) else H * 0.05, '#FFFFFF', HEAVY), 8 * S, 0.6), W * 0.9) for x in lines]
        meme = None
        if t.get('src'):
            mm = np.array(Image.open(t['src']).convert('RGB')) if is_image(t['src']) else _still(t['src'], 640, 480)
            mm = np.array(Image.fromarray(mm).convert('L').convert('RGBA'))
            meme = _fit(mm, W * (0.38 if is_landscape(W, H) else 0.5), H * (0.55 if is_landscape(W, H) else 0.3))
        for i in range(n):
            tt = i / FPS
            c = base.copy()
            j = max([k for k, a in enumerate(ats) if a <= tt + 1e-6], default=None)
            if j is not None:
                q = ease((tt - ats[j]) / 0.2, 'out')
                g = _fit(imgs[j], W * 0.42) if is_landscape(W, H) else imgs[j]
                put(c, g, W * (0.28 if is_landscape(W, H) else 0.5), H * (0.44 if is_landscape(W, H) else 0.32) + (1 - q) * 20 * S, q)
            if meme is not None:
                put(c, meme, W * (0.73 if is_landscape(W, H) else 0.5), H * (0.44 if is_landscape(W, H) else 0.56), ease(tt / 0.3))
            c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    if v == 'warning':
        title = word(t.get('title', '警告'), 90 * S if is_landscape(W, H) else H * 0.05, '#E0141E', HEAVY)
        ul = np.zeros((max(2, int(4 * S)), int(title.shape[1] * 1.3), 4), np.uint8)
        ul[...] = (224, 20, 30, 255)
        rows = [_rich(x, hl, 48 * S if is_landscape(W, H) else H * 0.03, '#F0F0F0', '#F2B01E', SERIF) for x in lines]
        for i in range(n):
            tt = i / FPS
            c = base.copy()
            p = ease(tt / 0.3, 'out')
            put(c, title, W * (0.20 if is_landscape(W, H) else 0.5), H * (0.43 if is_landscape(W, H) else 0.26), p)
            u = ul[:, :max(1, int(ul.shape[1] * ease((tt - 0.15) / 0.3)))]
            over(c, u, W * (0.20 if is_landscape(W, H) else 0.5) - ul.shape[1] / 2, H * (0.43 if is_landscape(W, H) else 0.26) + title.shape[0] * 0.75)
            y = H * (0.28 if is_landscape(W, H) else 0.36)
            for r, a in zip(rows, ats):
                q = ease((tt - 0.3 - a) / 0.25, 'out')
                g = _fit(r, W * 0.48) if is_landscape(W, H) else r
                put(c, g, W * (0.66 if is_landscape(W, H) else 0.5), y + (1 - q) * 14 * S, q)
                y += r.shape[0] * 1.05
            c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    # stack：一行行出，整块随行数上移；末行放大 1.5 倍；说完圆头像从右下滑进来
    rows = [_rich(x, hl, (64 if j < len(lines) - 1 else 100) * S if is_landscape(W, H) else H * (0.045 if j < len(lines) - 1 else 0.068), '#FFFFFF', '#C8102E') for j, x in enumerate(lines)]
    rows = [_fit(r, W * (0.65 if is_landscape(W, H) else 0.9)) for r in rows]
    av_at = t.get('avatar_at', ats[-1] + 0.8)
    D = int(H * 0.26) if is_landscape(W, H) else int(W * 0.45)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    sq = None
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = base.copy()
        shown = [k for k, a in enumerate(ats) if a <= tt]
        # 文字块高度（已出现的行）随时间缓动，整块居中在画面 0.4 处
        def block_h(m):
            return sum(rows[k].shape[0] for k in range(m))
        prev = block_h(max(0, len(shown) - 1))
        cur = block_h(len(shown))
        q = ease((tt - (ats[shown[-1]] if shown else 0)) / 0.25) if shown else 0
        h_ = prev + (cur - prev) * q
        y = H * 0.4 - h_ / 2
        for k in shown:
            a_ = ease((tt - ats[k]) / 0.25, 'out')
            put(c, rows[k], W * (0.43 if is_landscape(W, H) else 0.5), y + rows[k].shape[0] / 2, a_)
            y += rows[k].shape[0]
        if tt >= av_at:
            if sq is None:
                sq = _head_square(fr, W, H)
                if is_landscape(W, H):
                    sq = _safe_head_square(sq, W, H)
            p = ease((tt - av_at) / 0.3, 'out')
            put(c, _avatar(fr, sq, D, int(6 * S)), W * 0.95 - (D + 12 * S) / 2 + (1 - p) * H * 0.3 if is_landscape(W, H) else W * (0.7 + 0.4 * (1 - p)), H * 0.05 + (D + 12 * S) / 2 if is_landscape(W, H) else H * (0.74 + 0.2 * (1 - p)))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- qframe 反问钩子画框问号
def _persp_grid(W, H, S):
    im = Image.new('RGBA', (W, H), (16, 16, 20, 255))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H * 0.45
    col = (58, 58, 64, 255)
    for k in range(-12, 13):   # 从消失点放射出去的线
        for ey in (0, H):
            d.line([(cx, cy), (cx + k * W * 0.18, ey)], fill=col, width=max(1, int(2 * S)))
    for j in range(1, 14):   # 越远越密的横线（地面和天花板）
        f = (j / 13) ** 2
        for sgn in (1, -1):
            y = cy + sgn * f * (H * 0.55)
            d.line([(0, y), (W, y)], fill=col, width=max(1, int(2 * S)))
    a = np.array(im)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fade = np.clip(np.hypot(xx - cx, (yy - cy) * 0.6) / (W * 0.25), 0.15, 1)[..., None]   # 消失点附近淡下去
    a[..., :3] = (16 + (a[..., :3].astype(np.float32) - 16) * fade).astype(np.uint8)
    return a


def qframe(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    seed = int(t['t0'] * 100)
    rng = random.Random(seed)
    bg = _persp_grid(W, H, S)
    marks = []
    for k in range(5):
        sz = H * rng.uniform(0.07, 0.17)
        q = word('?', sz, '#E8243C', HEAVY)
        yy = np.linspace(0, 1, q.shape[0], dtype=np.float32)[:, None, None]
        q[..., :3] = (np.array([255, 90, 110], np.float32) * (1 - yy) + np.array([180, 10, 40], np.float32) * yy).astype(np.uint8)
        q = rotate_rgba(with_shadow(q, 8 * S, 0.5, dy=int(6 * S)), rng.uniform(-25, 25))
        if sz < H * 0.1:
            q = blur(q, 5 * S)   # 小的当远处，糊一点做景深
        side = k % 2
        x = rng.uniform(0.04, 0.17) if side == 0 else rng.uniform(0.83, 0.96)
        if is_landscape(W, H):
            q = _fit(q, W * 0.10, H * 0.17)
            x = 0.13 if side == 0 else 0.87
        marks.append((q, x * W, rng.uniform(0.18, 0.68) * H if is_landscape(W, H) else rng.uniform(0.12, 0.85) * H, rng.uniform(0, 6.28)))
    sk = t.get('frame_scale', 0.6)
    text = t.get('text', '')
    gl, wd = _glyphs(text, HAND, H * 0.06, '#FFFFFF', int(5 * S), '#1A1A1A') if text else ([], 0)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = bg.copy()
        p = ease(tt / 0.3, 'out')
        for k, (q, x, y, ph) in enumerate(marks):
            put(c, q, x, y + H * 0.006 * np.sin(tt * 3 + ph), ease((tt - 0.1 - 0.06 * k) / 0.25))
        k_ = 1 - (1 - sk) * p
        if is_landscape(W, H):
            k_ = min(0.72, k_)
        fw, fh = W * k_, H * k_
        card = _rounded_frame(fr, fw, fh, 40 * S * (0.4 + 0.6 * p), 6 * S * p)
        put(c, card, W / 2, H * (0.42 if is_landscape(W, H) else 0.47))
        base = H * 0.80 if is_landscape(W, H) else H * 0.66 + H * 0.02
        for m, (spr, gx, gy) in enumerate(gl):   # 手写字逐字出现
            e = (tt - 0.35 - 0.08 * m) / 0.12
            if e > 0:
                put(c, spr, W / 2 - wd / 2 + gx, base + gy, min(1.0, e))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- poster 整屏海报标题页
POSTER_VARIANTS = {
    'cinema': '黑底红字片名：纯黑底，左边一列红色窄体大字，右边一上一下两组白字，一行极细的宽字距白色英文横穿中线',
    'film': '胶片齿孔做旧页：做旧白纸底，上下各一条黑色胶片齿孔边，中间黑色粗体标题，两侧裁切的灰色巨字，整体轻微抖动',
    'grid': '网格底抠像封面：黑底细灰网格，下方抠出来的人半身，上方两行超大白色斜体衬线字，绿色花体英文和橙色粗字',
    'popart': '波普网点：蓝色网点纹理铺满，闪电和喇叭贴纸，左上黑底色块里白字粉字每 0.5 秒叠出一行，右下圆形徽章',
    'magazine': '杂志封面：白底像一页时尚杂志，人物居中，红色巨字分压两边，竖排 MAGAZINE，底部红色拼音横穿',
}


def _condensed(text, size, color, fontfile, k=0.72, **kw):
    g = word(text, size, color, fontfile, **kw)
    return np.array(Image.fromarray(g).resize((max(1, int(g.shape[1] * k)), g.shape[0]), Image.LANCZOS))


def _film_strip(W, h, S):
    s = np.zeros((int(h), W, 4), np.uint8)
    s[..., 3] = 255
    im = Image.fromarray(s)
    d = ImageDraw.Draw(im)
    hw, hh, gap = W * 0.022, h * 0.42, W * 0.03
    x = gap / 2
    while x < W:
        d.rounded_rectangle([x, (h - hh) / 2, x + hw, (h + hh) / 2], radius=int(4 * S), fill=(245, 245, 240, 255))
        x += hw + gap
    return np.array(im)


def poster(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    v = t.get('variant', 'cinema')
    dur, n = frames(t, FPS)
    text = t['text']
    seed = int(t['t0'] * 100)
    layers = []   # (贴图, x, y, 出现时刻)
    need_person = v in ('grid', 'magazine')
    if v == 'cinema':
        page = np.zeros((H, W, 4), np.uint8)
        page[..., 3] = 255
        col = trim(text_img(text, min(H * 0.16, H * 0.62 / max(1, len(text))), t.get('color', '#C4161C'), fontfile=HEAVY, vertical=True, pad=0))
        layers.append((col, W * 0.3, H * 0.47, 0.0))
        if t.get('sub'):
            layers.append((word(t['sub'], H * 0.035, '#F2F2F2', SERIF), W * 0.7, H * 0.36, 0.15))
        if t.get('issue'):
            layers.append((word(t['issue'], H * 0.07, '#F2F2F2', SERIF), W * 0.7, H * 0.58, 0.25))
        if t.get('en'):
            layers.append((_fit(text_img(t['en'].upper(), H * 0.02, '#FFFFFF', fontfile=EN, pad=2, spacing=int(H * 0.02)), W * 0.94), W / 2, H * 0.47, 0.35))
    elif v == 'film':
        page = _paper_noise(W, H, (236, 232, 222), seed, 7)
        side = H * 0.3
        for ch, x in ((text[0], -0.08), (text[-1], 1.08)):
            g = word(ch, side, '#9E9E9E', HEAVY)
            g[..., 3] = (g[..., 3] * 0.7).astype(np.uint8)
            layers.append((g, W * x, H * 0.5, 0.0))
        layers.append((_fit(word(text, H * 0.1, '#1A1A1A', HEAVY), W * 0.84), W / 2, H * 0.46, 0.1))
        if t.get('en'):
            layers.append((word(t['en'].upper(), H * 0.022, '#1A1A1A', HEAVY, spacing=int(8 * S)), W / 2, H * 0.55, 0.2))
        if t.get('sub'):
            sb = word(t['sub'], H * 0.022, '#F2F2F2', HEAVY)
            box = np.zeros((sb.shape[0] + int(16 * S), sb.shape[1] + int(30 * S), 4), np.uint8)
            box[...] = (26, 26, 26, 255)
            put(box, sb, box.shape[1] / 2, box.shape[0] / 2)
            layers.append((box, W / 2, H * 0.6, 0.25))
        strip = _film_strip(W, H * 0.08, S)
        over(page, strip, 0, H * 0.04)
        over(page, strip, 0, H * 0.88)
    elif v == 'grid':
        page = _grid_bg(W, H, S, '#0A0A0A', '#2E2E2E', 0.035)
        rows = [text[:len(text) // 2 + len(text) % 2], text[len(text) // 2 + len(text) % 2:]] if len(text) > 3 else [text]
        y = H * 0.14
        for j, r in enumerate(x for x in rows if x):
            g = word(r, H * 0.11, '#FFFFFF', SERIF)
            yy = np.linspace(0, 1, g.shape[0], dtype=np.float32)[:, None, None]
            g[..., :3] = (np.array([255, 255, 255], np.float32) * (1 - yy) + np.array([170, 170, 178], np.float32) * yy).astype(np.uint8)
            g = np.array(Image.fromarray(g).transform(g.shape[1::-1], Image.AFFINE, (1, 0.18, -g.shape[0] * 0.09, 0, 1, 0), Image.BICUBIC))
            layers.append((_fit(g, W * 0.9), W / 2, y + g.shape[0] / 2, 0.1 + 0.12 * j))
            y += g.shape[0] * 0.95
        if t.get('en'):
            layers.append((_fit(word(t['en'], H * 0.06, '#5BD68A', SCRIPT), W * 0.8), W * 0.55, y + H * 0.01, 0.35))
        if t.get('sub'):
            layers.append((word(t['sub'], H * 0.04, '#F07A1A', HEAVY), W * 0.3, y + H * 0.06, 0.45))
    elif v == 'popart':
        page = _halftone(W, H, '#5D74B8', 9 * S, S, bg='#3A4F8C')
        rows = t.get('lines') or [text]
        boxes = []
        for j, r in enumerate(rows):
            g = _rich(r, t.get('hl') or [], H * 0.04, '#FFFFFF', '#FF4FA3')
            b = np.zeros((g.shape[0] + int(10 * S), g.shape[1] + int(30 * S), 4), np.uint8)
            b[...] = (0, 0, 0, 255)
            put(b, g, b.shape[1] / 2, b.shape[0] / 2)
            boxes.append(b)
        y = H * 0.14
        for j, b in enumerate(boxes):
            layers.append((b, W * 0.06 + b.shape[1] / 2, y + b.shape[0] / 2, 0.15 + 0.5 * j))
            y += b.shape[0] + 8 * S
        if t.get('en'):
            layers.append((word(t['en'].upper(), H * 0.03, '#FFE600', BEBAS, spacing=int(4 * S)), W * 0.8, H * 0.08, 0.1))
        for k, (nm, x, y_, sz) in enumerate((('High voltage', 0.78, 0.36, 0.2), ('Megaphone', 0.2, 0.6, 0.24))):
            try:
                ic = np.array(Image.open(icon_png(nm)).convert('RGBA'))
                layers.append((rotate_rgba(scale(ic, W * sz / ic.shape[1]), 12 if k else -10), W * x, H * y_, 0.2 + 0.15 * k))
            except Exception:
                pass
        badge = Image.new('RGBA', (int(W * 0.3), int(W * 0.3)), (0, 0, 0, 0))
        ImageDraw.Draw(badge).ellipse([0, 0, badge.width - 1, badge.height - 1], fill=hex_rgba('#FF4FA3'), outline=(255, 255, 255, 255), width=int(6 * S))
        bd = np.array(badge)
        put(bd, _fit(word(t.get('badge') or text[:4], H * 0.03, '#FFFFFF', HEAVY), W * 0.24), bd.shape[1] / 2, bd.shape[0] / 2)
        layers.append((rotate_rgba(bd, -12), W * 0.76, H * 0.8, 0.5))
    else:   # magazine
        page = _paper_noise(W, H, (246, 244, 240), seed, 4)
        layers.append((rotate_rgba(word('MAGAZINE', H * 0.05, '#1A1A1A', EN, spacing=int(6 * S)), 90), W * 0.06, H * 0.42, 0.0))
        half = max(1, len(text) // 2)
        for j, (part, x) in enumerate(((text[:half], 0.22), (text[half:], 0.78))):
            if part:
                g = trim(text_img(part, H * 0.17, '#D0021B', fontfile=SERIF, vertical=True, pad=0))
                layers.append((_fit(g, W * 0.4, H * 0.62), W * x, H * 0.42, 0.15 + 0.1 * j))
        if t.get('en'):
            bar = np.zeros((int(H * 0.08), W, 4), np.uint8)
            bar[...] = (208, 2, 27, 255)
            put(bar, _fit(word(t['en'].upper(), H * 0.05, '#FFFFFF', EN, spacing=int(10 * S)), W * 0.94), W / 2, bar.shape[0] / 2)
            layers.append((bar, W / 2, H * 0.9, 0.35))
        if t.get('sub'):
            layers.append((trim(text_img(t['sub'], H * 0.025, '#D0021B', fontfile=HEAVY, vertical=True, pad=0)), W * 0.93, H * 0.2, 0.3))
    if is_landscape(W, H):
        arranged = []
        if v in ('grid', 'magazine'):
            for j, (g, x, y, at) in enumerate(layers):
                cx, cy, sw, sh = _side(W, H, j % 2 == 1)
                g = _fit(g, sw * 0.90, H * 0.24)
                arranged.append((g, cx, H * (0.22 + 0.23 * (j // 2)), at))
        else:
            for g, x, y, at in layers:
                g = _fit(g, W * 0.82, H * 0.50)
                x = max(W * 0.05 + g.shape[1] / 2, min(W * 0.95 - g.shape[1] / 2, x))
                y = max(H * 0.06 + g.shape[0] / 2, min(H * 0.79 - g.shape[0] / 2, y))
                arranged.append((g, x, y, at))
        if v == 'magazine':
            # 刊名、主题和英文各占一块侧栏，不缩放整条横幅。
            arranged = []
            for j, part in enumerate((text[:half], text[half:])):
                cx, cy, sw, sh = _side(W, H, bool(j))
                arranged.append((_fit(word(part, 150 * S, '#D0021B', SERIF), sw, H * 0.34), cx, H * 0.40, 0.15 + j * 0.1))
            arranged.append((_fit(word('MAGAZINE', 38 * S, '#1A1A1A', EN), W * 0.23), W * 0.175, H * 0.16, 0))
            if t.get('en'):
                arranged.append((_fit(word(t['en'].upper(), 36 * S, '#D0021B', EN), W * 0.23), W * 0.825, H * 0.65, 0.35))
        layers = arranged
    src = matte.frames(aroll, t['t0'], dur, W, H, FPS) if need_person else ((None, None) for _ in range(n))
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(src):
        tt = i / FPS
        c = page.copy()
        if v == 'grid' and fr is not None:   # 人半身站在下方
            pp = scale(_person(fr, a), 0.8)
            over(c, pp, W / 2 - pp.shape[1] / 2, H - pp.shape[0] * 0.78)
        if v == 'magazine' and fr is not None:
            pp = scale(_person(fr, a), 0.9)
            over(c, pp, W / 2 - pp.shape[1] / 2, H - pp.shape[0] - H * 0.08)
        for g, x, y, d0 in layers:
            p = ease((tt - d0) / 0.3, 'out')
            if p > 0:
                put(c, scale(g, 1.04 - 0.04 * p), x, y, p)
        if v == 'cinema' and tt < 0.6:   # 入场一道光斑从左扫到右
            q = tt / 0.6
            yy, xx = np.ogrid[0:H, 0:W]
            gl = np.exp(-(((xx - W * (q * 1.4 - 0.2)) / (W * 0.18)) ** 2 + ((yy - H * 0.47) / (H * 0.08)) ** 2)) * 0.7 * (1 - q)
            c[..., :3] = np.clip(c[..., :3] + gl[..., None] * np.array([255, 180, 120]), 0, 255).astype(np.uint8)
        if v == 'film':   # 整体轻微抖动
            c = np.roll(c, int(2 * S * np.sin(tt * 30)), axis=1)
        c[..., 3] = int(255 * min(1.0, tt / 0.3) * fade_out(tt, dur, 0.2))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- coverframe 首帧封面图
def coverframe(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    at = t.get('frame_at', 0.8)
    fr, a = next(matte.frames(aroll, at, 1 / FPS, W, H, FPS))
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    c = np.zeros((H, W, 4), np.uint8)
    c[..., :3] = (np.array(hex_rgba(t.get('bg', '#FFD23F'))[:3], np.float32) * (1 - yy) +
                  np.array(hex_rgba(t.get('bg2', '#FF7A1A'))[:3], np.float32) * yy).astype(np.uint8)
    c[..., 3] = 255
    over(c, _halftone(W, H, '#FFFFFF38', 6 * S, S), 0, 0)   # 一层淡白网点
    pp = _outline_person(fr, a, 12 * S)
    pp = scale(pp, 1.05)
    over(c, pp, W / 2 - pp.shape[1] / 2, H - pp.shape[0])
    if t.get('text'):
        g = _fit(word(t['text'], H * 0.085, t.get('color', '#E8243C'), HEAVY, stroke=int(10 * S), stroke_color='#FFFFFF'), W * 0.92)
        g = rotate_rgba(with_shadow(g, 10 * S, 0.5), t.get('rot', 8))
        if is_landscape(W, H):
            cx, cy, sw, sh = _side(W, H)
            put(c, _fit(g, sw * 0.90, sh), cx, cy)
        else:
            put(c, g, W / 2, H * 0.14)
    if t.get('text2'):
        g = _fit(word(t['text2'], H * 0.06, '#FFFFFF', HEAVY, stroke=int(9 * S), stroke_color='#1A1A1A'), W * 0.9)
        g = rotate_rgba(with_shadow(g, 8 * S, 0.5), -t.get('rot', 8) * 0.8)
        if is_landscape(W, H):
            cx, cy, sw, sh = _side(W, H, True)
            put(c, _fit(g, sw * 0.90, sh), cx, cy)
        else:
            put(c, g, W / 2, H * 0.62)
    w = Writer(out, W, H, FPS, alpha=True)
    for _ in range(n):
        w.put(c)
    w.close()


# ---------------------------------------------------------------- askpage 求赞收藏提醒页
ASK_VARIANTS = {
    'flank': '暗角窗两侧大字：硬切纯黑底，人只留中间羽化椭圆窗，左右各一组大字由灰变白放大，右上弧形黄色小字，下方点赞关注评论小图标',
    'lines': '竖排收藏提醒：左侧三列竖排白色衬线大字逐列出现「视频很长 / 干货很多 / 记得收藏」，右侧博主小窗',
}


def askpage(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    v = t.get('variant', 'flank')
    dur, n = frames(t, FPS)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'lines':
        cols = t.get('lines') or ['视频很长', '干货很多', '记得收藏']
        imgs = [with_shadow(trim(text_img(x, H * 0.06, '#FFFFFF', fontfile=SERIF, vertical=True, pad=0)), 8 * S, 0.5) for x in cols]
        D = int(H * 0.26) if is_landscape(W, H) else int(W * 0.36)
        sq = None
        for i in range(n):
            tt = i / FPS
            fr = next(frs)
            c = _opaque(_soft_bg(fr, W, H, 0.4))
            for j, im in enumerate(imgs):   # 竖排从右往左读：第一列在最右
                x = W * (0.18 + 0.20 * j) if is_landscape(W, H) else W * (0.46 - 0.15 * j)
                put(c, im, x, H * 0.42, ease((tt - 0.1 - 0.3 * j) / 0.2))
            if sq is None:
                sq = _head_square(fr, W, H)
                if is_landscape(W, H):
                    sq = _safe_head_square(sq, W, H)
            put(c, _avatar(fr, sq, D, int(6 * S)), W * 0.95 - (D + 12 * S) / 2 if is_landscape(W, H) else W * 0.77, H * 0.05 + (D + 12 * S) / 2 if is_landscape(W, H) else H * 0.42, ease(tt / 0.3))
            c[..., 3] = int(255 * fade_out(tt, dur, 0.15))
            w.put(c)
        w.close()
        return
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - W / 2) / (W * 0.225), (yy - H * 0.47) / (H * 0.425))
    win = np.clip((1 - d) / 0.15, 0, 1)[..., None]   # 羽化椭圆窗
    def big(s):
        return trim(text_img(s, H * 0.13, '#FFFFFF', fontfile=SERIF, vertical=len(s) > 1, pad=0))
    sides = [(big(t['left']), t.get('left_en'), 0.15), (big(t['right']), t.get('right_en'), 0.85)]
    arc = None
    if t.get('arc'):
        from bigtype import _arc_chars
        arc = _arc_chars(t['arc'], [], W * 0.18, H * 0.035, True, S * 0.6)
    icons = []
    for nm in t.get('icons', ['Thumbs up', 'Star', 'Speech balloon']):
        try:
            ic = np.array(Image.open(icon_png(nm)).convert('RGBA'))
            icons.append(scale(ic, (H * 0.08 if is_landscape(W, H) else W * 0.1) / ic.shape[1]))
        except Exception:
            pass
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = _opaque((fr * win).astype(np.uint8))
        for j, (g, en, x) in enumerate(sides):
            p = ease((tt - 0.05 - 0.12 * j) / 0.25, 'out')
            if p <= 0:
                continue
            gg = g.copy()
            k = 0.5 + 0.5 * p   # 灰变白
            gg[..., :3] = (gg[..., :3].astype(np.float32) * k).astype(np.uint8)
            put(c, scale(gg, 0.6 + 0.4 * p), W * x, H * 0.47, min(1.0, p * 2))
            if en:
                e = text_img(en.upper(), H * 0.02, '#BDBDBD', fontfile=EN, pad=2, spacing=int(H * 0.012))
                put(c, rotate_rgba(trim(e), 90), W * x + g.shape[1] * 0.6, H * 0.47, p)
        if arc:
            cx, cy, r = (W * 0.81, H * 0.06, H * 0.16) if is_landscape(W, H) else (W * 0.78, H * 0.2, W * 0.18)
            for k_, (spr, th) in enumerate(arc):
                q = ease((tt - 0.35 - 0.04 * k_) / 0.2)
                put(c, spr, cx + np.cos(np.radians(th)) * r, cy + r + np.sin(np.radians(th)) * r, q)
        for k_, ic in enumerate(icons):
            q = (tt - 0.5 - 0.12 * k_) / 0.22
            if q > 0:
                put(c, scale(ic, _pop(q)), W * (0.38 + 0.12 * k_), H * (0.73 if is_landscape(W, H) else 0.88), min(1.0, q * 2))
        c[..., 3] = int(255 * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- gesture 圆头像手势章节卡
def gesture(t, W, H, FPS, st, work, aroll, out):
    if is_landscape(W, H):
        return _landscape_gesture(t, W, H, FPS, st, work, aroll, out)
    S = unit(W, H)
    dur, n = frames(t, FPS)
    num = str(t.get('number', '1')).lstrip('0') or '0'
    src = t.get('src') or aroll
    s_in = t.get('src_in', t['t0']) if not t.get('src') else t.get('src_in', 0)
    frs = list(read(src, s_in, dur, (W, H), FPS))
    bg = _opaque(_soft_bg(_still(aroll, W, H, max(0.0, t['t0'] - 0.1)), W, H, 0.55, r=4))
    sq = _head_square(frs[min(len(frs) - 1, int(0.2 * FPS))], W, H)
    sq = (sq[0], sq[1] + sq[2] * 0.12, sq[2] * 1.35)   # 圆里多留胸前，比手势的手要进画
    D = int(W * 0.55)
    unit_word = t.get('unit', '招')
    lab = _rich(f"第 {num} {unit_word}", [num], H * 0.06, '#FFFFFF', '#F5B400', HEAVY, stroke=int(6 * S), stroke_color='#111111')
    sub = with_shadow(word(t['text'], H * 0.032, '#FFFFFF', HEAVY), 6 * S, 0.6) if t.get('text') else None
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = bg.copy()
        p = (tt - 0.02) / 0.25
        if p > 0:
            k = 0.3 + 0.75 * eback(p) if p < 1 else 1.0
            put(c, scale(_avatar(frs[min(i, len(frs) - 1)], sq, D, int(8 * S)), max(0.05, k)), W / 2, H * 0.4 + H * 0.4 * (1 - ease(p, 'out')))
        q = (tt - 0.2) / 0.22
        if q > 0:
            put(c, scale(lab, _pop(q)), W / 2, H * 0.64, min(1.0, q * 2))
        if sub is not None:
            put(c, sub, W / 2, H * 0.7, ease((tt - 0.35) / 0.25))
        c[..., 3] = int(255 * min(1.0, tt / 0.06) * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- cutnum 抠像剪纸大数字章节页
NUM_COLORS = ['#F28BC0', '#3FA88A', '#8C5BD6', '#79B8E8']


def _paper_numeral(num, h, color, S, seed):
    g = word(num, h, color, HEAVY)
    light = word(num, h, '#FFF6E8', HEAVY)
    o = int(12 * S)
    c = np.zeros((g.shape[0] + o, g.shape[1] + o, 4), np.uint8)
    over(c, light, o, o)   # 错位浅色描边
    over(c, g, 0, 0)
    rng = np.random.default_rng(seed)
    tex = rng.normal(0, 14, (c.shape[0] // 3 + 1, c.shape[1] // 3 + 1)).astype(np.float32)
    tex = np.array(Image.fromarray(tex).resize((c.shape[1], c.shape[0]), Image.BILINEAR))
    c[..., :3] = np.clip(c[..., :3] + tex[..., None], 0, 255).astype(np.uint8)   # 纸纹
    return with_shadow(c, 10 * S, 0.5, dy=int(8 * S))


def _burst(r, S, seed):
    rng = random.Random(seed)
    D = int(r * 2.4)
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for k in range(22):
        a = 2 * np.pi * k / 22
        rr = r * (1.0 if k % 2 == 0 else 0.55) * rng.uniform(0.85, 1.15)
        pts.append((D / 2 + np.cos(a) * rr, D / 2 + np.sin(a) * rr))
    d.polygon(pts, fill=(255, 210, 40, 255), outline=(20, 20, 20, 255))
    inner = [(D / 2 + (x - D / 2) * 0.6, D / 2 + (y - D / 2) * 0.6) for x, y in pts]
    d.polygon(inner, fill=(255, 120, 30, 255))
    return np.array(im)


def cutnum(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    num = str(t.get('number', '1')).lstrip('0') or '0'
    seed = int(t['t0'] * 100)
    color = t.get('color', NUM_COLORS[(int(num) - 1) % len(NUM_COLORS)] if num.isdigit() else NUM_COLORS[0])
    numeral = _paper_numeral(num, H * 0.42, color, S, seed)
    if is_landscape(W, H):
        numeral = _fit(numeral, W * 0.22, H * 0.42)
    burst = _burst(H * 0.18 if is_landscape(W, H) else W * 0.3, S, seed)
    grid = _grid_bg(W, H, S)
    red = _halftone(W, H, '#E8343C', 10 * S, S, bg='#C81E2A')
    phase2 = t.get('phase2_at', 0.8)
    title = None
    if t.get('text'):
        g = word(t['text'], H * 0.075, '#FFFFFF', BRUSH)
        sh = _halftone(g.shape[1], g.shape[0], '#111111', 5 * S, S)
        sh[..., 3] = (sh[..., 3].astype(np.float32) * (g[..., 3] / 255)).astype(np.uint8)
        b = np.zeros((g.shape[0] + int(10 * S), g.shape[1] + int(10 * S), 4), np.uint8)
        over(b, sh, 0, int(8 * S))
        over(b, g, 0, 0)
        title = _fit(b, W * (0.25 if is_landscape(W, H) else 0.9))
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        q = ease((tt - phase2) / 0.3)
        c = grid.copy()
        if q > 0:
            over(c, red, 0, 0, q)
        p = (tt - 0.05) / 0.25
        put(c, rotate_rgba(burst, tt * 20), W * (0.82 if is_landscape(W, H) else 0.68), H * 0.38, ease(p) * (1 - 0.6 * q))
        nm = scale(numeral, (max(0.05, 0.4 + 0.6 * eback(p)) if p < 1 else 1.0) * (1 - 0.1 * q))
        put(c, blur(nm, 14 * S * q) if q > 0.05 else nm, W * (0.82 if is_landscape(W, H) else 0.68), H * 0.38, min(1.0, max(0.0, p) * 2) * (1 - 0.35 * q))
        pp = scale(_outline_person(fr, a, 10 * S), 0.9)
        over(c, pp, W * (0.45 if is_landscape(W, H) else 0.38) - pp.shape[1] / 2, H - pp.shape[0])
        if title is not None and tt > phase2:
            e = (tt - phase2 - 0.1) / 0.25
            if e > 0:
                put(c, scale(title, _pop(e)), W * (0.82 if is_landscape(W, H) else 0.5), H * 0.66, min(1.0, e * 2))
        c[..., 3] = int(255 * min(1.0, tt / 0.06) * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- inkecho 结尾回扣开场大字
def _noise(W, H, seed, cells=10):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    for k, amp in ((cells, 0.6), (cells * 3, 0.3), (cells * 9, 0.1)):
        n = rng.random((max(2, H * k // W), k)).astype(np.float32)
        acc += np.array(Image.fromarray(n).resize((W, H), Image.BICUBIC)) * amp
    acc -= acc.min()
    return acc / max(acc.max(), 1e-6)


def inkecho(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    dur, n = frames(t, FPS)
    g = _fit(word(t['text'], H * t.get('size_h', 0.12), t.get('color', '#F5D547'), HEAVY), W * 0.92)
    cx, cy = W * t.get('x', 0.5), H * t.get('y', 0.2)
    if is_landscape(W, H):
        cx, cy, sw, sh = _side(W, H, t.get('side') == 'right' if t.get('side') else bool(int(t['t0']) % 2))
        g = _fit(g, sw, sh)
        if isinstance(t.get('x'), (int, float)):
            cx = max(cx - sw / 2 + g.shape[1] / 2, min(cx + sw / 2 - g.shape[1] / 2, W * t['x']))
        if isinstance(t.get('y'), (int, float)):
            cy = max(H * 0.15 + g.shape[0] / 2, min(H * 0.75 - g.shape[0] / 2, H * t['y']))
    layer = np.zeros((H, W, 4), np.uint8)
    put(layer, g, cx, cy)
    nz = _noise(W, H, int(t['t0'] * 10))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rad = np.hypot(xx - cx, (yy - cy) * 1.4) / (W * 0.6)
    field = np.clip(0.55 * nz + 0.45 * rad, 0, 1)   # 从字中心往外、沿噪声纹理晕开
    op = t.get('alpha', 0.6)
    ink = t.get('ink_s', 1.0)
    w = Writer(out, W, H, FPS, alpha=True)
    for i, (fr, a) in enumerate(matte.frames(aroll, t['t0'], dur, W, H, FPS)):
        tt = i / FPS
        m = np.clip((tt / ink * 1.15 - field) / 0.12, 0, 1)
        c = layer.copy()
        c[..., 3] = (c[..., 3] * m * op * (1 - np.clip(a, 0, 1)) * fade_out(tt, dur, 0.2)).astype(np.uint8)
        w.put(c)
    w.close()


# ---------------------------------------------------------------- actionrow 点赞转发评论条
def actionrow(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    items = t.get('items') or ['点赞', '转发', '评论']
    words = [with_shadow(word(x, H * 0.05, '#FFFFFF', HEAVY), 7 * S, 0.6) for x in items]
    dash = np.zeros((int(8 * S), int(W * 0.06), 4), np.uint8)
    dash[...] = (43, 217, 160, 255)
    gap = W * 0.03
    total = sum(x.shape[1] for x in words) + (len(words) - 1) * (dash.shape[1] + 2 * gap)
    xs, x = [], W / 2 - total / 2
    for k, g in enumerate(words):
        xs.append(x + g.shape[1] / 2)
        x += g.shape[1] + dash.shape[1] + 2 * gap
    y = H * t.get('y', 0.72)
    if is_landscape(W, H):
        cx, cy, sw, sh = _side(W, H, t.get('side') == 'right' if t.get('side') else bool(int(t['t0']) % 2))
        words = [_fit(g, sw * 0.90) for g in words]
        xs = [cx] * len(words)
        y = H * 0.40
    card = None
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = np.zeros((H, W, 4), np.uint8)
        for k, g in enumerate(words):
            p = ease((tt - 0.1 - 0.3 * k) / 0.15, 'out')
            if p > 0:
                put(c, g, xs[k], y + (k * H * 0.15 if is_landscape(W, H) else 0) + (1 - p) * 16 * S, p)
            if k and p > 0 and not is_landscape(W, H):
                put(c, dash[:, :max(1, int(dash.shape[1] * p))], xs[k] - g.shape[1] / 2 - gap - dash.shape[1] / 2, y, p)
        if t.get('name'):
            if card is None:
                sq = _head_square(fr, W, H)
                if is_landscape(W, H):
                    sq = _safe_head_square(sq, W, H)
                av = _avatar(fr, sq, int(H * 0.05), 0)
                nm = word(t['name'], H * 0.022, '#FFFFFF', HEAVY)
                cw, ch = int(av.shape[1] + nm.shape[1] + 70 * S), int(av.shape[0] + 24 * S)
                im = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
                ImageDraw.Draw(im).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=int(ch / 2), fill=(12, 12, 12, 230))
                card = np.array(im)
                put(card, av, 12 * S + av.shape[1] / 2, ch / 2)
                put(card, nm, 24 * S + av.shape[1] + nm.shape[1] / 2, ch / 2)
                yd = int(10 * S)
                card[int(ch / 2 - nm.shape[0] / 2):int(ch / 2 - nm.shape[0] / 2) + yd, cw - int(26 * S):cw - int(26 * S) + yd] = (255, 210, 40, 255)
            if is_landscape(W, H):
                card = _fit(card, sw)
            put(c, card, cx if is_landscape(W, H) else W * 0.05 + card.shape[1] / 2, H * (0.22 if is_landscape(W, H) else 0.3), ease(tt / 0.25))
        c[..., 3] = (c[..., 3] * fade_out(tt, dur, 0.15)).astype(np.uint8)
        w.put(c)
    w.close()


# ---------------------------------------------------------------- slogan 固定口号收尾
def slogan(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    grid = _grid_bg(W, H, S)
    top = with_shadow(_fit(word(t['text'], H * 0.07, '#FFFFFF', HEAVY), W * 0.9), 8 * S, 0.6)
    pair = t.get('text2') or ''
    chars = [_corner_char(ch, H * 0.1, t.get('color', '#F5B400'), S) for ch in pair[:2]]
    at2 = t.get('at2', 0.8)
    sk = t.get('shrink_to', 0.58 if is_landscape(W, H) else 0.7)
    rng = random.Random(int(t['t0'] * 100))
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        c = grid.copy()
        p = ease(tt / 0.25, 'out')
        k = 1 - (1 - sk) * p
        card = _rounded_frame(fr, W * k, H * k, W * 0.08 * p, 0)
        put(c, card, W / 2, H * (0.43 if is_landscape(W, H) else 0.52))
        if tt >= 0.25:   # 「学会了」故障闪 0.15 秒落定
            g = _glitch(top, rng, S) if tt < 0.4 else top
            put(c, g, W / 2, H * 0.11)
        for j, ch in enumerate(chars):
            q = (tt - at2 - 0.1 * j) / 0.25
            if q > 0:
                put(c, scale(ch, _pop(q)), W * (0.15 if j == 0 else 0.85), H * 0.42, min(1.0, q * 2))
        c[..., 3] = int(255 * min(1.0, tt / 0.06) * fade_out(tt, dur, 0.15))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- 展开：首帧封面、一词一镜快剪、段落收尾推高收束
def prepare(tl, st, base='.'):
    """渲染前展开第 10 批的顶层字段（render、build_draft、rhythm_check 都调）：
    cover 首帧封面 → 片头 0.15 秒的 coverframe；montage_cuts 一词一镜快剪 → 每个短语一段铺满素材 + 头像小窗 + 一词一镜字幕；
    section_ends 段落收尾 → 快剪 + 问题句跳到 115% 一档 + 章节页处配乐停 1.2 秒；points 不写 items 时按章节页自动排编号。"""
    from kvlib import _phrases
    import infocard
    import scene
    infocard.prepare(tl, st, base)   # 第 11 批：素材打码
    scene.prepare(tl, st, base)      # 第 12 批：底部留黑挪字幕
    import props
    props.prepare(tl, st, base)      # 第 15 批：梗句幽默短乐句
    cv = tl.get('cover')
    if cv and not any(t.get('layout') == 'coverframe' for t in tl.get('titles', [])):
        tl.setdefault('titles', []).append({'t0': 0.0, 't1': cv.get('dur', 0.15), 'layout': 'coverframe', 'cover': True, 'sfx': False,
                                            **{k: v for k, v in cv.items() if k != 'dur'}})
    specs = list(tl.get('montage_cuts') or [])
    chapters = sorted((x for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS and x.get('enter') != 'cover'), key=lambda x: x['t0'])
    for se in tl.get('section_ends') or []:
        specs.append({'t0': se['t0'], 't1': se['t1'], 'srcs': se['srcs'], 'pip': se.get('pip', True), 'subs': True})
        if se.get('talk'):
            a, b = se['talk']
            tl.setdefault('zoom', []).append({'t0': a, 't1': b, 'from': 1.15, 'to': 1.15, 'ease': 0.01})
        nxt = next((c['t0'] for c in chapters if c['t0'] >= se['t1'] - 0.05), None)
        if nxt is not None:   # 章节页那一下配乐戛然而止 1.2 秒
            tl.setdefault('_breaks', []).append((round(nxt - 0.05, 3), round(nxt + se.get('silence', 1.2), 3)))
    f = Path(base) / 'lines.json'
    chars = [(c[0], c[1]) for ln in json.loads(f.read_text(encoding='utf-8')) for c in ln.get('chars', [])] if f.exists() else []
    for k, m in enumerate(specs):
        cs = [c for c in chars if m['t0'] - 0.02 <= c[1] < m['t1']]
        ps = _phrases(cs, 2, m.get('max', 6)) if cs else []
        ts = [m['t0']] + [p[1] for p in ps[1:]] + [m['t1']]
        if len(ps) < 2:   # 没有逐字时间：按 0.75 秒一镜等分
            step = m.get('shot', 0.75)
            ts = list(np.arange(m['t0'], m['t1'], step)) + [m['t1']]
        rng = random.Random(int(m['t0'] * 100))
        for j in range(len(ts) - 1):
            if ts[j + 1] - ts[j] < 0.2:
                continue
            s = m['srcs'][j % len(m['srcs'])]
            own = s if isinstance(s, dict) else {}   # 素材可以写成 {"src", "crop", ...}：同一段录屏裁不同的地方，当成不同景别的镜头
            s = own.get('src', s)
            off = 0.0 if is_image(s) else rng.uniform(0, max(0.0, probe(s)['duration'] - (ts[j + 1] - ts[j]) - 0.1))
            tl.setdefault('broll', []).append({'t0': round(ts[j], 3), 't1': round(ts[j + 1], 3), 'src': s, 'src_in': round(off, 2), 'fit': 'cover',
                                               'motion': 'static', 'sfx': False, **(m.get('broll') or {}), **{k: v for k, v in own.items() if k != 'src'}})
        if m.get('pip', True):
            canvas = tl.get('canvas') or {}
            land = is_landscape(canvas.get('w', 1080), canvas.get('h', 1920))
            pip = m['pip'] if isinstance(m.get('pip'), dict) else {'pos': m.get('pos', 'top_right' if land else 'bottom_right')}   # pip 写 {"pip": {x, y, d}} 指定小窗
            if land and not isinstance(m.get('pip'), dict) and not m.get('pos'):
                W, H = canvas['w'], canvas['h']
                params = pip_params(pip, st)
                D = params['d'] * W + 2 * params.get('border', 0) * unit(W, H)
                pip['pip'] = {**params, 'x': 0.95 - D / (2 * W), 'y': 0.05 + D / (2 * H)}
            tl.setdefault('layout', []).append({'t0': m['t0'], 't1': m['t1'], 'mode': 'pip', **pip})
        if m.get('subs', True):
            tl.setdefault('phrase_subs', []).append({'t0': m['t0'], 't1': m['t1'], 'cut': False})
    pts = tl.get('points')
    if pts and not pts.get('items'):
        items = []
        pages = sorted((x for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS), key=lambda x: x['t0'])
        for j, c in enumerate(chapters):
            end = chapters[j + 1]['t0'] if j + 1 < len(chapters) else pts.get('until', tl.get('duration', c['t1'] + 30))
            s0 = c['t1']
            for x in pages:   # 白场接力页紧接着章节页：编号等它结束再出
                if x['t0'] <= s0 + 0.05 and x['t1'] > s0:
                    s0 = x['t1']
            items.append({'t0': s0, 't1': end, 'n': str(c.get('number', j + 1)), 'text': c.get('text', '')})
        pts['items'] = items


# ---------------------------------------------------------------- 常驻层：角落要点编号、系列名水印、进度条小人
POINT_VARIANTS = {
    'glow': '顶部光扫编号：左上黄色粗斜体编号和本节名，换一点时一道黄色光团从左扫过把数字刷新',
    'film': '胶片框小窗编号：右上角胶片齿孔小卡，里面字距拉开的 POINT 和白色做旧大数字，换项处故障闪 0.15 秒',
    'brush': '斜刃编号：左上白色粗斜体编号被一刀斜切出缺口，旁边一行本节名',
}


def _point_png(item, v, W, H, S):
    num = f"{int(item['n']):02d}" if str(item['n']).isdigit() else str(item['n'])
    if v == 'film':
        cw, ch = int(W * 0.3), int(H * 0.15)
        c = np.zeros((ch, cw, 4), np.uint8)
        c[...] = (14, 14, 14, 235)
        st_ = _film_strip(cw, ch * 0.13, S)
        over(c, st_, 0, 0)
        over(c, st_, 0, ch - st_.shape[0])
        put(c, word('POINT', ch * 0.09, '#BDBDBD', EN, spacing=int(ch * 0.04)), cw / 2, ch * 0.27)
        g = rough(word(num, ch * 0.42, '#FFFFFF', EN), int(item['t0']), 0.15)
        put(c, g, cw / 2, ch * 0.54)
        if item.get('text'):
            put(c, _fit(word(item['text'], ch * 0.09, '#FFFFFF', HEAVY), cw * 0.9), cw / 2, ch * 0.78)
        return c, (W * 0.84 - cw / 2, H * 0.26 - ch / 2)
    if v == 'brush':
        g = word(num, H * 0.055, '#FFFFFF', TYPE, stroke=int(3 * S), stroke_color='#111111')
        im = Image.fromarray(g)
        d = ImageDraw.Draw(im)
        d.line([(0, g.shape[0] * 0.75), (g.shape[1], g.shape[0] * 0.35)], fill=(0, 0, 0, 0), width=max(3, int(6 * S)))   # 斜切缺口
        g = np.array(im)
        row = [g]
        if item.get('text'):
            row.append(with_shadow(word(item['text'], H * 0.026, '#FFFFFF', HEAVY), 5 * S, 0.6))
        wd = sum(x.shape[1] for x in row) + int(16 * S)
        c = np.zeros((max(x.shape[0] for x in row), wd, 4), np.uint8)
        over(c, row[0], 0, 0)
        if len(row) > 1:
            over(c, row[1], row[0].shape[1] + 16 * S, (c.shape[0] - row[1].shape[0]) / 2)
        return c, (W * 0.06, H * 0.05)
    g = word(num, H * 0.05, '#F5E400', TYPE, stroke=int(3 * S), stroke_color='#1A1A1A')
    row = [with_shadow(g, 6 * S, 0.5)]
    if item.get('text'):
        row.append(with_shadow(word(item['text'], H * 0.026, '#FFFFFF', HEAVY, stroke=int(2 * S), stroke_color='#1A1A1A'), 5 * S, 0.6))
    wd = sum(x.shape[1] for x in row) + int(14 * S)
    c = np.zeros((max(x.shape[0] for x in row), wd, 4), np.uint8)
    over(c, row[0], 0, 0)
    if len(row) > 1:
        over(c, row[1], row[0].shape[1] + 14 * S, (c.shape[0] - row[1].shape[0]) / 2)
    return c, (W * 0.06, H * 0.06)


def _point_switch(png, xy, v, W, H, FPS, S, out, seed):
    """换一点那 0.4 秒：光扫刷新 / 故障闪 / 斜切弹入。"""
    n = round(0.4 * FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    rng = random.Random(seed)
    x0, y0 = xy
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        if v == 'film':
            g = _glitch(png, rng, S, 0.6) if tt < 0.15 else png
            over(c, g, x0 - (g.shape[1] - png.shape[1]) / 2, y0, min(1.0, tt / 0.05 + 0.3))
        elif v == 'glow':
            q = tt / 0.3
            vis = png[:, :max(1, int(png.shape[1] * _clamp(q)))]
            over(c, vis, x0, y0)
            gx = x0 + png.shape[1] * q
            r = png.shape[0] * 1.2
            yy, xx = np.ogrid[0:H, 0:W]
            gl = np.exp(-(((xx - gx) / (r * 1.6)) ** 2 + ((yy - (y0 + png.shape[0] / 2)) / r) ** 2)) * (1 - _clamp((tt - 0.3) / 0.1))
            add = np.zeros((H, W, 4), np.float32)
            add[..., :3] = (255, 236, 60)
            add[..., 3] = gl * 220
            over(c, add.astype(np.uint8), 0, 0)
        else:
            p = ease(tt / 0.2, 'out')
            over(c, png, x0 - (1 - p) * 40 * S, y0, p)
        w.put(c)
    w.close()


def _hud_pngs(hud, W, H, S, work):
    v = hud.get('variant', 'watermark')
    if v == 'watermark':
        g = word(hud['text'], H * 0.026, hud.get('color', '#5A5A5A'), TYPE)
        g[..., 3] = (g[..., 3] * hud.get('alpha', 0.75)).astype(np.uint8)
        if is_landscape(W, H):
            cx, cy, sw, sh = _side(W, H, True)
            g = _fit(g, sw, H * 0.08)
        p = Path(work) / 'hud_mark.png'
        Image.fromarray(g).save(p)
        return {'mark': (p, W * 0.95 - g.shape[1] if is_landscape(W, H) else (W - g.shape[1]) / 2, H * hud.get('y', 0.06 if is_landscape(W, H) else 0.04))}
    bh = max(4, int(H * 0.008))
    track = np.zeros((bh, W, 4), np.uint8)
    track[...] = (40, 40, 40, 170)
    fill = np.zeros((bh, W, 4), np.uint8)
    fill[...] = hex_rgba(hud.get('color', '#F7D21E'))
    out = {}
    for nm, a in (('track', track), ('fill', fill)):
        p = Path(work) / f'hud_{nm}.png'
        Image.fromarray(a).save(p)
        out[nm] = p
    try:
        ic = np.array(Image.open(icon_png(hud.get('mascot', 'Person walking'))).convert('RGBA'))
        ic = scale(ic, H * 0.035 / ic.shape[0])
        p = Path(work) / 'hud_mascot.png'
        Image.fromarray(ic).save(p)
        out['mascot'] = p
    except Exception:
        pass
    out['y'] = H * hud.get('y', 0.08 if is_landscape(W, H) else 0.24)
    return out


def apply(fc, cur, tl, add_input, W, H, FPS, work, total):
    """常驻层压在字幕下面：角落要点编号（points）、系列名水印或进度条（hud）。total 是成片时长（进度条按它走完）。"""
    from effects import _overlay_clip, _overlay_png
    S = unit(W, H)
    pts = tl.get('points')
    if pts and pts.get('items'):
        v = pts.get('variant', 'glow')
        for k, it in enumerate(pts['items']):
            if it['t1'] - it['t0'] < 0.6:
                continue
            png, xy = _point_png(it, v, W, H, S)
            if is_landscape(W, H):
                cx, cy, sw, sh = _side(W, H, v == 'film')
                png = _fit(png, sw * 0.90, H * 0.22)
                xy = (cx - png.shape[1] / 2, H * 0.17)
            p = Path(work) / f'point{k}.png'
            Image.fromarray(png).save(p)
            mv = Path(work) / f'point{k}.mov'
            _point_switch(png, xy, v, W, H, FPS, S, mv, k)
            cur = _overlay_clip(fc, cur, add_input, mv, it['t0'], it['t0'] + 0.4, f'pts{k}a')
            cur = _overlay_png(fc, cur, add_input, p, it['t0'] + 0.4, it['t1'], f'pts{k}b', FPS, fout=0.15, x=int(xy[0]), y=int(xy[1]))
    import scene
    cur = scene.apply(fc, cur, tl, add_input, W, H, FPS, work, total)   # 第 12 批：口播上移底部留黑
    hud = tl.get('hud')
    if hud:
        t0, t1 = hud.get('t0', 0.0), hud.get('t1', total)
        d = _hud_pngs(hud, W, H, S, work)
        if 'mark' in d:
            p, x, y = d['mark']
            cur = _overlay_png(fc, cur, add_input, p, t0, t1, 'hudm', FPS, x=int(x), y=int(y))
        else:
            y = int(d['y'])
            cur = _overlay_png(fc, cur, add_input, d['track'], t0, t1, 'hudt', FPS, y=y)
            idx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', str(d['fill'])])
            fc.append(f"[{idx}:v]format=rgba[hudfv]")
            fc.append(f"{cur}[hudfv]overlay=x='-W+W*(t-{t0:.3f})/{max(0.1, t1 - t0):.3f}':y={y}:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[hudf]")
            cur = '[hudf]'
            if 'mascot' in d:
                idx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{total:.3f}', '-i', str(d['mascot'])])
                fc.append(f"[{idx}:v]format=rgba[hudmv]")
                fc.append(f"{cur}[hudmv]overlay=x='W*(t-{t0:.3f})/{max(0.1, t1 - t0):.3f}-w/2':y={y}-h+2:"
                          f"enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[hudmo]")
                cur = '[hudmo]'
    return cur


# 横屏手势页单独排，竖屏保留原路径。
def _landscape_gesture(t, W, H, FPS, st, work, aroll, out):
    S = unit(W, H)
    dur, n = frames(t, FPS)
    num = str(t.get('number', '1')).lstrip('0') or '0'
    src = t.get('src') or aroll
    s_in = t.get('src_in', t['t0']) if not t.get('src') else t.get('src_in', 0)
    frs = list(read(src, s_in, dur, (W, H), FPS))
    bg = _opaque(_soft_bg(_still(aroll, W, H, max(0.0, t['t0'] - 0.1)), W, H, 0.55, r=4))
    sq = _head_square(frs[min(len(frs) - 1, int(0.2 * FPS))], W, H)
    sq = (sq[0], sq[1] + sq[2] * 0.12, sq[2] * 1.35)   # 圆里多留胸前，比手势的手要进画
    if is_landscape(W, H):
        cs, x0, y0 = face_crop(W, H, {'x': (sq[0] - sq[2] / 2) / W, 'y': (sq[1] - sq[2] / 2) / W, 's': sq[2] / W})
        sq = (x0 + cs / 2, y0 + cs / 2, cs)
    D = int(H * 0.46) if is_landscape(W, H) else int(W * 0.55)
    unit_label = t.get('unit', '招')
    lab = _rich(f"第 {num} {unit_label}", [num], H * 0.06, '#FFFFFF', '#F5B400', HEAVY, stroke=int(6 * S), stroke_color='#111111')
    sub = with_shadow(word(t['text'], H * 0.032, '#FFFFFF', HEAVY), 6 * S, 0.6) if t.get('text') else None
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = bg.copy()
        p = (tt - 0.02) / 0.25
        if p > 0:
            k = 0.3 + 0.75 * eback(p) if p < 1 else 1.0
            put(c, scale(_avatar(frs[min(i, len(frs) - 1)], sq, D, int(8 * S)), max(0.05, k)), W * (0.29 if is_landscape(W, H) else 0.5), H * (0.43 if is_landscape(W, H) else 0.4) + H * 0.4 * (1 - ease(p, 'out')))
        q = (tt - 0.2) / 0.22
        if q > 0:
            put(c, scale(lab, _pop(q)), W * (0.67 if is_landscape(W, H) else 0.5), H * (0.38 if is_landscape(W, H) else 0.64), min(1.0, q * 2))
        if sub is not None:
            put(c, sub, W * (0.67 if is_landscape(W, H) else 0.5), H * (0.53 if is_landscape(W, H) else 0.7), ease((tt - 0.35) / 0.25))
        c[..., 3] = int(255 * min(1.0, tt / 0.06) * fade_out(tt, dur, 0.12))
        w.put(c)
    w.close()


def _safe_head_square(sq, W, H):
    # 圆里多留胸前时，也不能读到源画面外的黑边。
    cx, cy, size = sq
    side, x, y = face_crop(W, H, {'x': (cx - size / 2) / W, 'y': (cy - size / 2) / W, 's': size / W})
    return x + side / 2, y + side / 2, side
