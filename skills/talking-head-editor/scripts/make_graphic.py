"""用代码生成信息图动画当 B-roll（不花积分）：数字滚动、柱状图、左右对比、步骤清单、时间轴、金句卡。

用法：python make_graphic.py spec.json -o broll/g01.mov [--style premium|variety] [--w 960 --h 720]（无画布时仍为 960×720；跟随项目用 --canvas 1920x1080 或 spec.canvas）
输出带透明通道的 ProRes 4444（.mov），放进 timeline.json 的 broll，fit 用 contain 或 card。

spec.json 示例（type 决定模板，dur 是秒数）：
  {"type": "number", "dur": 3, "value": 1.5, "decimals": 1, "prefix": "", "suffix": "万亿美元", "label": "SpaceX 目标估值"}
  {"type": "number", "dur": 3, "from": 100, "value": 20, "suffix": "%", "label": "上下文余量"}   从 from 滚到 value，可以往下掉
  {"type": "bars", "dur": 4, "title": "全球火箭发射次数", "unit": "次", "items": [["美国", 180], ["中国", 92], ["俄罗斯", 17]]}
  {"type": "compare", "dur": 4, "left": {"title": "Claude Code", "points": ["规划强", "写文案强"]},
                               "right": {"title": "Codex", "points": ["写代码快", "额度多"]}}
  {"type": "steps", "dur": 5, "title": "版本管理三步走", "items": ["git init 初始化", "git commit 存档", "git revert 回退"]}
  {"type": "timeline", "dur": 5, "items": [["2015", "第一次回收成功"], ["2020", "载人飞行"], ["2026", "计划上市"]]}
  {"type": "quote", "dur": 4, "text": "不能依靠 AI 的记忆来撤回", "by": "新手第一坑"}
  {"type": "highlight", "dur": 3, "image": "broll/news.png", "boxes": [[0.05, 0.42, 0.9, 0.06]]}   截图卡片 + 荧光笔划线（boxes 相对截图）
颜色：可选 "accent" 覆盖强调色。字体跟随风格的字体角色（标题特粗黑体、正文中黑、数字 Anton、金句宋体），字体清单在 assets/fonts/。
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from kvlib import find_role_font, hex_rgba, canvas_size

THEMES = {
    'premium': dict(bg=(18, 18, 20, 225), fg=(247, 245, 240, 255), sub=(247, 245, 240, 150), accent='#D7262D', line=(255, 255, 255, 40), radius=36),
    'variety': dict(bg=(255, 255, 255, 245), fg=(25, 25, 25, 255), sub=(25, 25, 25, 160), accent='#FF4D4F', line=(0, 0, 0, 30), radius=40),
}


def ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def ease_back(p):
    p = max(0.0, min(1.0, p))
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


class Canvas:
    def __init__(self, w, h, theme, fonts):
        self.w, self.h, self.t = w, h, theme
        self.fonts = fonts          # 角色 → 字体文件：title / body / en / serif
        self._fonts = {}

    def font(self, size, role='body'):
        key = (int(size), role)
        if key not in self._fonts:
            self._fonts[key] = ImageFont.truetype(self.fonts.get(role) or self.fonts['body'], int(size))
        return self._fonts[key]

    def new(self, alpha=1.0):
        im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        if alpha > 0:
            bg = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
            d = ImageDraw.Draw(bg)
            r, g, b, a = self.t['bg']
            d.rounded_rectangle([0, 0, self.w - 1, self.h - 1], radius=self.t['radius'], fill=(r, g, b, int(a * alpha)))
            im = Image.alpha_composite(im, bg)
        return im

    def text(self, im, xy, s, size, fill, anchor='mm', alpha=1.0, role='body'):
        if role == 'en_display' and not s.isascii():   # 英文窄体没有中文字形
            role = 'title'
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        r, g, b, a = fill if isinstance(fill, tuple) else hex_rgba(fill)
        ImageDraw.Draw(layer).text(xy, s, font=self.font(size, role), fill=(r, g, b, int(a * alpha)), anchor=anchor)
        return Image.alpha_composite(im, layer)


def fmt_num(v, decimals):
    return f'{v:,.{decimals}f}' if decimals else f'{int(round(v)):,}'


def frame_number(c, s, t, dur):
    im = c.new(ease_out(t / 0.3))
    p = ease_out(t / (dur * 0.6))
    v0 = s.get('from', 0)
    v = v0 + (s['value'] - v0) * p
    big = f"{s.get('prefix', '')}{fmt_num(v, s.get('decimals', 0))}"
    suffix = s.get('suffix', '')
    if suffix.isascii():          # 「%」「x」这类短后缀跟在数字后面，中文单位另起一行
        big, suffix = big + suffix, ''
    k = 0.92 + 0.08 * ease_back(t / 0.5)
    im = c.text(im, (c.w / 2, c.h * (0.48 if suffix else 0.57)), big, c.h * 0.36 * k, s.get('accent', c.t['accent']), alpha=ease_out(t / 0.3), role='en_display')
    im = c.text(im, (c.w / 2, c.h * 0.70), suffix, c.h * 0.075, c.t['fg'], alpha=ease_out((t - 0.2) / 0.4), role='title')
    im = c.text(im, (c.w / 2, c.h * 0.2), s.get('label', ''), c.h * 0.055, c.t['sub'], alpha=ease_out((t - 0.1) / 0.4))
    return im


def frame_bars(c, s, t, dur):
    im = c.new(ease_out(t / 0.3))
    items = s['items']
    mx = max(v for _, v in items) or 1
    top, bottom = c.h * 0.24, c.h * 0.92
    gap = (bottom - top) / len(items)
    im = c.text(im, (c.w * 0.07, c.h * 0.11), s.get('title', ''), c.h * 0.065, c.t['fg'], anchor='lm', alpha=ease_out(t / 0.3), role='title')
    for i, (name, v) in enumerate(items):
        y = top + gap * (i + 0.5)
        p = ease_out((t - 0.25 - i * 0.18) / 0.8)
        x0, x1 = c.w * 0.30, c.w * 0.30 + (c.w * 0.52) * (v / mx) * p
        d = Image.new('RGBA', im.size, (0, 0, 0, 0))
        col = hex_rgba(s.get('accent', c.t['accent'])) if i == 0 else c.t['fg'][:3] + (90,)
        ImageDraw.Draw(d).rounded_rectangle([x0, y - gap * 0.22, max(x0 + 2, x1), y + gap * 0.22], radius=int(gap * 0.12), fill=col)
        im = Image.alpha_composite(im, d)
        im = c.text(im, (c.w * 0.26, y), name, gap * 0.32, c.t['fg'], anchor='rm', alpha=ease_out((t - 0.2 - i * 0.18) / 0.4))
        im = c.text(im, (x1 + c.w * 0.02, y), f"{fmt_num(v * p, s.get('decimals', 0))}{s.get('unit', '')}", gap * 0.34, c.t['sub'], anchor='lm',
                    alpha=ease_out((t - 0.4 - i * 0.18) / 0.4), role='en_display')
    return im


def frame_compare(c, s, t, dur):
    im = c.new(ease_out(t / 0.3))
    d = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(d).line([c.w / 2, c.h * 0.12, c.w / 2, c.h * 0.88], fill=c.t['line'], width=3)
    im = Image.alpha_composite(im, d)
    im = c.text(im, (c.w / 2, c.h * 0.5), 'VS', c.h * 0.09, s.get('accent', c.t['accent']), alpha=ease_out((t - 0.3) / 0.3), role='en_display')
    for side, cx in (('left', 0.25), ('right', 0.75)):
        blk = s[side]
        delay = 0 if side == 'left' else 0.25
        im = c.text(im, (c.w * cx, c.h * 0.2), blk['title'], c.h * 0.07, c.t['fg'], alpha=ease_out((t - delay) / 0.35), role='title')
        for j, pt in enumerate(blk.get('points', [])):
            im = c.text(im, (c.w * cx, c.h * (0.38 + j * 0.13)), pt, c.h * 0.062, c.t['sub'], alpha=ease_out((t - 0.4 - delay - j * 0.2) / 0.35))
    return im


def frame_steps(c, s, t, dur):
    im = c.new(ease_out(t / 0.3))
    im = c.text(im, (c.w * 0.08, c.h * 0.13), s.get('title', ''), c.h * 0.065, c.t['fg'], anchor='lm', alpha=ease_out(t / 0.3), role='title')
    items = s['items']
    per = max(0.35, (dur * 0.7) / len(items))
    gap = c.h * 0.7 / max(len(items), 1)
    for i, it in enumerate(items):
        p = ease_out((t - 0.3 - i * per) / 0.35)
        y = c.h * 0.28 + gap * i + gap * 0.3
        x = c.w * 0.08 + c.w * 0.04 * (1 - p)
        dot = Image.new('RGBA', im.size, (0, 0, 0, 0))
        r = gap * 0.17
        ImageDraw.Draw(dot).ellipse([x, y - r, x + 2 * r, y + r], fill=hex_rgba(s.get('accent', c.t['accent']))[:3] + (int(255 * p),))
        im = Image.alpha_composite(im, dot)
        im = c.text(im, (x + r, y), str(i + 1), r * 1.4, (20, 20, 20, 255), alpha=p, role='en_display')
        im = c.text(im, (x + 2 * r + c.w * 0.04, y), it, gap * 0.3, c.t['fg'], anchor='lm', alpha=p)
    return im


def frame_timeline(c, s, t, dur):
    im = c.new(ease_out(t / 0.3))
    items = s['items']
    y = c.h * 0.55
    p_line = ease_out(t / (dur * 0.5))
    d = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(d).line([c.w * 0.07, y, c.w * 0.07 + c.w * 0.86 * p_line, y], fill=c.t['fg'][:3] + (160,), width=4)
    im = Image.alpha_composite(im, d)
    for i, (year, label) in enumerate(items):
        x = c.w * (0.14 + 0.72 * i / max(len(items) - 1, 1))
        p = ease_out((t - 0.3 - i * 0.35) / 0.35)
        dot = Image.new('RGBA', im.size, (0, 0, 0, 0))
        r = c.h * 0.025 * ease_back(p) if p > 0 else 0
        if r > 0:
            ImageDraw.Draw(dot).ellipse([x - r, y - r, x + r, y + r], fill=hex_rgba(s.get('accent', c.t['accent'])))
        im = Image.alpha_composite(im, dot)
        im = c.text(im, (x, y - c.h * 0.12), year, c.h * 0.09, c.t['fg'], alpha=p, role='en_display')
        im = c.text(im, (x, y + c.h * 0.11), label, c.h * 0.045, c.t['sub'], alpha=p)
    return im


def frame_quote(c, s, t, dur):
    im = c.new(ease_out(t / 0.3))
    text = s['text']
    n = int(len(text) * ease_out(t / (dur * 0.5)))
    im = c.text(im, (c.w * 0.12, c.h * 0.25), '“', c.h * 0.25, s.get('accent', c.t['accent']), alpha=ease_out(t / 0.3), role='serif')
    size = min(c.h * 0.11, c.w * 0.82 / max(len(text), 1) * 1.25)
    im = c.text(im, (c.w / 2, c.h * 0.52), text[:n], size, c.t['fg'], role='serif')
    if s.get('by'):
        im = c.text(im, (c.w * 0.88, c.h * 0.8), '—— ' + s['by'], c.h * 0.045, c.t['sub'], anchor='rm', alpha=ease_out((t - dur * 0.5) / 0.4))
    return im


def frame_highlight(c, s, t, dur):
    """截图卡片 + 荧光笔从左往右划过指定区域。spec: {"image": 路径, "boxes": [[x,y,w,h],...]（相对截图）, "color": "#FFD23F"}"""
    if not hasattr(c, '_hl_img'):
        img = Image.open(s['image']).convert('RGBA')
        pad = int(c.w * 0.04)
        scale = min((c.w - 2 * pad) / img.width, (c.h - 2 * pad) / img.height)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        c._hl_img, c._hl_pos = img, ((c.w - img.width) // 2, (c.h - img.height) // 2)
    img, (ox, oy) = c._hl_img, c._hl_pos
    im = Image.new('RGBA', (c.w, c.h), (0, 0, 0, 0))
    card = Image.new('RGBA', img.size, (0, 0, 0, 0))
    card.paste(img, (0, 0))
    col = hex_rgba(s.get('color', c.t['accent']))
    for i, (x, y, w, h) in enumerate(s['boxes']):
        p = ease_out((t - 0.4 - i * 0.5) / 0.6)
        if p <= 0:
            continue
        mark = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(mark).rectangle([x * img.width, y * img.height, (x + w * p) * img.width, (y + h) * img.height],
                                       fill=col[:3] + (110,))
        card = Image.alpha_composite(card, mark)
    from kvlib import rounded_mask
    m = rounded_mask(img.width, img.height, c.t['radius'] // 2)
    a = ease_out(t / 0.3)
    m = m.point(lambda v: int(v * a))
    im.paste(card, (ox, oy), m)
    return im


TEMPLATES = {'number': frame_number, 'bars': frame_bars, 'compare': frame_compare, 'steps': frame_steps,
             'timeline': frame_timeline, 'quote': frame_quote, 'highlight': frame_highlight}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--style', default='premium')
    ap.add_argument('--canvas', type=canvas_size, help='画布 WxH；也可在 spec 的 canvas 写 w、h')
    ap.add_argument('--w', type=int)
    ap.add_argument('--h', type=int)
    ap.add_argument('--fps', type=int, default=30)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8')) if Path(a.spec).exists() else json.loads(a.spec)
    if bool(a.w) != bool(a.h) or a.canvas and a.w:
        ap.error('--w 和 --h 要一起给，不能和 --canvas 同时使用')
    cv = spec.get('canvas', dict(w=960, h=720))
    a.w, a.h = a.canvas or ((a.w, a.h) if a.w else (cv['w'], cv['h']))
    theme = dict(THEMES.get(a.style, THEMES['premium']))
    if spec.get('accent'):
        theme['accent'] = spec['accent']
    c = Canvas(a.w, a.h, theme, {r: find_role_font(r, a.style)[0] for r in ('title', 'body', 'en_display', 'serif')})
    fn = TEMPLATES[spec['type']]
    dur = float(spec.get('dur', 4))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{a.w}x{a.h}', '-r', str(a.fps), '-i', '-',
                            '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', a.out], stdin=subprocess.PIPE)
    for k in range(int(dur * a.fps)):
        enc.stdin.write(fn(c, spec, k / a.fps, dur).tobytes())
    enc.stdin.close()
    enc.wait()
    print('图形动画：', a.out)


if __name__ == '__main__':
    main()
