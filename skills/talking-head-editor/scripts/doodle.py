"""手绘小元素：圈注、下划线、箭头、闪光、感叹线、打勾、打叉。用 ASS 矢量画，边画边出现，像手画上去的。

timeline 写在 doodles 里：
  {"t0": 10.6, "t1": 12.2, "type": "circle", "x": 0.3, "y": 0.6, "w": 0.4, "h": 0.12}
  x, y 是中心位置，w, h 是大小（都按画面比例）；可选 color（默认风格强调色）、width（线宽，按短边 1080）、rot（旋转角度）。
  圈大字里的词时不用估坐标，写 "target": {"text": "改坏了"}（自动找这一刻画面上含这几个字的大字，也可加 "title": 第几条），位置按排版结果自动算。
每个贴纸要对着一个具体的词或画面元素，停 1 到 2 秒；高级感每分钟最多 1 个，综艺感最多 4 个（依据头部知识口播成片）。
"""
import math
import random

from kvlib import is_landscape

TYPES = ('circle', 'multicircle', 'spiral', 'underline', 'arrow', 'sparkle', 'exclaim', 'check', 'cross')


def _wobble(pts, amp, seed):
    """给折线加一点手抖。"""
    rnd = random.Random(seed)
    return [(x + rnd.uniform(-amp, amp), y + rnd.uniform(-amp, amp)) for x, y in pts]


def _path(pts):
    return 'm ' + ' l '.join(f'{x:.0f} {y:.0f}' for x, y in pts)   # ASS 矢量坐标要写整数


def _stroke(pts, width):
    """把一条折线变成有宽度的多边形（ASS 矢量只会填充有面积的形状），两头收细像笔触。"""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[max(0, i - 1)]
        bx, by = pts[min(n - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy) or 1.0
        taper = min(1.0, 0.35 + 0.65 * min(i, n - 1 - i) / max(1, min(3, (n - 1) / 2)))
        hw = width / 2 * taper
        nx, ny = -dy / ln * hw, dx / ln * hw
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    return left + right[::-1]


def shapes(kind, w, h, seed=7):
    """返回若干条折线（相对左上角 0,0、宽 w 高 h 的框）。"""
    if kind == 'circle':      # 椭圆多画 1/8 圈，首尾不完全闭合，像手画
        n = 48
        pts = [(w / 2 + w / 2 * math.cos(-math.pi / 2 + 2.25 * math.pi * i / n), h / 2 + h / 2 * math.sin(-math.pi / 2 + 2.25 * math.pi * i / n))
               for i in range(n + 1)]
        return [_wobble(pts, min(w, h) * 0.015, seed)]
    if kind == 'multicircle':   # 多圈涂鸦圈：一笔绕两圈半，每圈错开一点，像用力圈了好几下
        n = 120
        pts = [(w / 2 + w / 2 * (0.96 + 0.05 * math.sin(i / 9)) * math.cos(-math.pi / 2 + 5 * math.pi * i / n),
                h / 2 + h / 2 * (0.94 + 0.06 * math.cos(i / 7)) * math.sin(-math.pi / 2 + 5 * math.pi * i / n)) for i in range(n + 1)]
        return [_wobble(pts, min(w, h) * 0.012, seed)]
    if kind == 'spiral':        # 螺旋圈：从外往里收两圈
        n = 90
        pts = [(w / 2 + w / 2 * (1 - 0.35 * i / n) * math.cos(-math.pi / 2 + 4 * math.pi * i / n),
                h / 2 + h / 2 * (1 - 0.35 * i / n) * math.sin(-math.pi / 2 + 4 * math.pi * i / n)) for i in range(n + 1)]
        return [_wobble(pts, min(w, h) * 0.01, seed)]
    if kind == 'underline':   # 略带起伏的一笔
        n = 16
        return [_wobble([(w * i / n, h / 2 + h * 0.18 * math.sin(i / n * math.pi * 1.5)) for i in range(n + 1)], h * 0.05, seed)]
    if kind == 'arrow':       # 从左下弯到右上，带箭头
        n = 20
        body = [(w * 0.05 + w * 0.85 * i / n, h * 0.9 - h * 0.8 * (i / n) ** 1.6) for i in range(n + 1)]
        tip = body[-1]
        return [_wobble(body, min(w, h) * 0.01, seed),
                [(tip[0] - w * 0.16, tip[1] + h * 0.02), tip, (tip[0] - w * 0.03, tip[1] + h * 0.2)]]
    if kind == 'sparkle':     # 四角星
        cx, cy = w / 2, h / 2
        return [[(cx, 0), (cx + w * 0.08, cy - h * 0.08), (w, cy), (cx + w * 0.08, cy + h * 0.08), (cx, h),
                 (cx - w * 0.08, cy + h * 0.08), (0, cy), (cx - w * 0.08, cy - h * 0.08), (cx, 0)]]
    if kind == 'exclaim':     # 三道放射短线
        return [[(w * 0.1, h * 0.55), (w * 0.35, h * 0.75)], [(w * 0.45, h * 0.1), (w * 0.55, h * 0.45)],
                [(w * 0.9, h * 0.25), (w * 0.68, h * 0.55)]]
    if kind == 'check':
        return [_wobble([(0, h * 0.55), (w * 0.35, h), (w, 0)], min(w, h) * 0.02, seed)]
    if kind == 'cross':
        return [[(0, 0), (w, h)], [(w, 0), (0, h)]]
    raise SystemExit(f'doodles 的 type「{kind}」不支持，可选：{"、".join(TYPES)}')


def resolve_target(d, tl, st, W, H):
    """贴纸写 "target": {"title": 第几条大字（从 0 数）, "text": "改坏了"} 时，按排版结果算出那几个字的位置，
    圈注、下划线就能准确落在字上，不用手估坐标。返回补好 x, y, w, h 的 d。"""
    tg = d.get('target')
    if not tg:
        return d
    from typeset import layout_title, text_w
    if 'title' in tg:
        t = tl['titles'][tg['title']]
    else:   # 不写第几条：找这个贴纸出现时正在画面上、含这几个字的大字（beats 自动展开的大字也能圈）
        hits = [x for x in tl['titles'] if x['t0'] - 0.05 <= d['t0'] <= x['t1']
                and any(tg['text'] in i.get('text', '') for i in layout_title(x, st, W, H))]
        if not hits:
            raise SystemExit(f"doodles：{d['t0']} 秒画面上没有含「{tg['text']}」的大字")
        t = hits[0]
    for it in layout_title(t, st, W, H):
        if it.get('kind') == 'dim' or tg['text'] not in it.get('text', ''):
            continue
        cond = it.get('condense', 100)
        pre = it['text'].split(tg['text'])[0]
        full_w = text_w(it['text'], it['size'], cond)
        x_left = it['x'] if it['an'] in (7, 4, 1) else (it['x'] - full_w if it['an'] in (9, 6, 3) else it['x'] - full_w / 2)
        x0 = x_left + text_w(pre, it['size'], cond)
        w = text_w(tg['text'], it['size'], cond)
        top = it['y'] if it['an'] in (7, 8, 9) else it['y'] - it['size'] / 2
        h = it['size'] * 0.8
        pad = d.get('pad', 0.25)
        kind = d.get('type')
        if kind == 'underline':
            box = (x0 + w / 2, top + h * 1.1, w * 1.05, it['size'] * 0.12)
        else:
            box = (x0 + w / 2, top + h * 0.6, w * (1 + pad), h * (1 + pad * 1.6))
        return {**d, 'x': box[0] / W, 'y': box[1] / H, 'w': box[2] / W, 'h': box[3] / H}
    raise SystemExit(f"doodles：第 {tg.get('title', '?')} 条大字里没有「{tg['text']}」")


def events(d, W, H, color_tag, ass_time, k):
    """一个贴纸的 ASS 事件：每条折线用描边画（填充透明），用逐渐展开的矩形裁剪做出「边画边出现」。"""
    x0, y0 = W * (d['x'] - d['w'] / 2), H * (d['y'] - d['h'] / 2)
    w, h = W * d['w'], H * d['h']
    lw = d.get('width', 9) * k
    if is_landscape(W, H):
        # 不挪动手写目标的含义，只收住笔画和旋转后伸出去的边缘。
        angle = math.radians(d.get('rot', 0))
        rw = abs(w * math.cos(angle)) + abs(h * math.sin(angle))
        rh = abs(w * math.sin(angle)) + abs(h * math.cos(angle))
        cx, cy = W * d['x'], H * d['y']
        # 圈词时允许笔画多伸进一点留白，不能为了边距把圈挤进字里。
        margin = 0 if d.get('target') else W * 0.05
        room = min(2 * (cx - margin) / max(1, rw + 2 * lw), 2 * (W - margin - cx) / max(1, rw + 2 * lw),
                   2 * (cy - H * 0.05) / max(1, rh + 2 * lw), 2 * (H * 0.8 - cy) / max(1, rh + 2 * lw), 1)
        if room <= 0:
            return []
        w, h, lw = w * room, h * room, lw * room
        x0, y0 = cx - w / 2, cy - h / 2
    draw_ms = int(d.get('draw', 0.35) * 1000)
    dur_ms = int((d['t1'] - d['t0']) * 1000)
    out = []
    lines = shapes(d['type'], w, h, seed=int(d['t0'] * 100))
    for i, pts in enumerate(lines):
        start = i * draw_ms // max(1, len(lines))
        end = start + draw_ms // max(1, len(lines)) + 60
        if d['type'] in ('sparkle',):
            anim = f"\\fscx30\\fscy30\\t({start},{start + 160},\\fscx110\\fscy110)\\t({start + 160},{start + 260},\\fscx100\\fscy100)"
        else:
            anim = (f"\\clip({x0 - lw:.0f},{y0 - lw:.0f},{x0 - lw + 1:.0f},{y0 + h + lw:.0f})"
                    f"\\t({start},{end},\\clip({x0 - lw:.0f},{y0 - lw:.0f},{x0 + w + lw:.0f},{y0 + h + lw:.0f}))")
        tags = (f"\\an7\\pos({x0:.0f},{y0:.0f})\\org({x0 + w / 2:.0f},{y0 + h / 2:.0f})\\frz{d.get('rot', 0)}\\bord0\\shad0"
                f"\\1c{color_tag}\\1a&H00&\\blur0.6\\fad(0,{min(200, dur_ms // 3)}){anim}\\p1")
        shape = pts if d['type'] == 'sparkle' else _stroke(pts, lw)
        out.append(f"Dialogue: 3,{ass_time(d['t0'])},{ass_time(d['t1'])},Base,,0,0,0,,{{{tags}}}{_path(shape)}{{\\p0}}")
    return out
