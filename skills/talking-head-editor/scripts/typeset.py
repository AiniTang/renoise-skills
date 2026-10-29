"""大字排版：把 timeline 里的一条 titles 展开成一组摆好位置的文字。成片渲染（render.py）和剪映草稿（build_draft.py）共用。

高级感的排版思路来自大字报式字幕教程：字放在人的一侧、左右不对称；一组字里大小差 3 倍以上，
一行小字引出一个大关键词；关键词用压窄的特粗黑体，红白两色；书法或手写字做点缀；背后可以叠一层半透明巨字。
居中的「编号 + 标题 + 细线 + 小字」是最典型的 AI 模板感，不再提供。

每个文字项（item）：
  text   文字（\\N 或换行表示换行）    role  字体角色（title / serif / body / en / en_display / en_serif / hand / note）
  size   ASS 字号（按实际画布像素）    x, y  锚点位置（像素）    an  锚点（7 左上 / 9 右上 / 8 中上 / 5 正中）
  color  颜色    hl / hl_color  变色强调的词    alpha  透明度 0~1    condense  横向压缩百分比
  spacing  字距    rot  旋转角度    hollow  只描边不填充    shadow  柔和投影    delay  比整条晚多少秒出现
  until  比整条早消失（相对整条开始的秒数）    anim  这一项自己的入场动画    glow  同色柔光
  move  出现以后的让位动作 {"at": 秒, "dur", "dx", "dy", "scale", "color", "alpha"}
特殊项：kind='dim' 整屏压暗（章节页）；kind='shape' 色块或标签底板（x, y 左上角，w, h, r 圆角，color, alpha，
wipe 从左往右刷出秒数，skew 斜切，fade_tail 右端渐隐）；kind='doodle' 手绘元素（同 doodles 的写法，坐标按画面比例）。
手法库（library.py）新加的版式：flank / yield / chunks / list / chips / concept / bignum / number，以及任何版式都能加的 block 色块衬底。
数据卡、环形图、雾面章节、章节标题页（kvlib.GRAPHIC_LAYOUTS）是逐帧合成的画面，由 cards.py 画，这里返回空。
"""
import re

from kvlib import unit, is_landscape, GRAPHIC_LAYOUTS
from keytext import side_box

CJK = re.compile(r'[⺀-鿿＀-￯]')


def text_w(s, size, condense=100):
    """估算一行字的宽度（像素）：ASS 字号是行高，中文字宽约为字号的 0.69，英文数字约 0.45。"""
    w = 0.0
    for c in s:
        w += 0.69 if CJK.match(c) else (0.25 if c == ' ' else 0.45)
    return w * size * condense / 100


def lines_of(text):
    return [x for x in text.replace('\\N', '\n').split('\n')]


def fit(size, text, maxw, condense=100):
    """字号不超过 size，并且最长一行不超过 maxw 像素宽。"""
    widest = max((text_w(l, 1, condense) for l in lines_of(text)), default=1) or 1
    return min(size, maxw / widest)


def _at(t, key, i, n, start=0.3, span=0.7):
    """第 i 个元素出现的时刻（相对这条大字开始）：优先用口播逐字时间算好的 t[key][i]，没有就在前 span 的时长里均分。"""
    ats = t.get(key) or []
    if i < len(ats) and ats[i] is not None:
        return max(0.0, ats[i])
    dur = t['t1'] - t['t0']
    return start + i * (dur * span - start) / max(1, n)


def layout_flank(t, add, W, H, k, S, cond, white, accent, soft, tc):
    """人两侧对称短语（手法库 flank_pair）：人站中间，一句话拆两段分放左右空位，先后出现。
    variant：white_red 左白右红（默认）/ stagger 错落双字（第二个字往右下错开）/ pop 双词先后弹出（综艺感）。"""
    v = t.get('variant', 'white_red')
    L, R = t['left'], t['right']
    y = H * t.get('y', 0.40)
    ra = _at(t, 'right_at', 0, 1, 0.5, 0.35)
    lc, rc = (t.get('left_color', white), t.get('right_color', accent))
    if v == 'stagger':
        size = min(fit(H * 0.15, L[:1], W * 0.16, cond), fit(H * 0.15, R[:1], W * 0.16, cond))
        for side, word, col, d0 in (('l', L, lc, 0.0), ('r', R, rc, ra)):
            cx = W * (0.15 if side == 'l' else 0.85)
            for j, ch in enumerate(word):
                add(text=ch, role=t.get('font', 'title'), size=size, x=cx + size * 0.6 * 0.69 * (j - (len(word) - 1) / 2) * 1.0,
                    y=y + size * 0.9 * j - size * 0.45 * (len(word) - 1), an=5, condense=cond, color=col, delay=d0 + j * 0.1, anim='wipe_down')
            en = t.get('left_en' if side == 'l' else 'right_en')
            if en:
                add(text=en.upper(), role='en', size=tc['tag_size'] * k * 0.8, x=cx - size * 0.25, y=y + size * 0.55, an=6, color=soft,
                    spacing=6 * k, alpha=0.8, delay=d0 + 0.2, shadow=False)
        return
    size = t.get('size', 0) * k or min(fit(H * 0.11, L, W * 0.26, cond), fit(H * 0.11, R, W * 0.26, cond))
    anim = 'pop' if v == 'pop' else None
    for side, word, col, d0 in (('l', L, lc, 0.0), ('r', R, rc, ra)):
        cx = W * (0.17 if side == 'l' else 0.83)
        add(text=word, role=t.get('font', 'title'), size=size, x=cx, y=y, an=5, condense=cond, color=col, delay=d0,
            **({'anim': anim} if anim else {}))
        en = t.get('left_en' if side == 'l' else 'right_en')
        if en:
            add(text=en.upper(), role='en', size=tc['tag_size'] * k * 0.95, x=cx, y=y + size * 0.66, an=5, color=soft, spacing=8 * k,
                alpha=0.75, delay=d0 + 0.12, shadow=False)


def layout_yield(t, add, W, H, k, cond, white, accent, tc, hl):
    """前句让位后句重点（手法库 line_yield_shift）：前半句先出，后半句出现时前半句缩小、变淡并挪开，后半句更大、换色进场。
    variant：push_up 上移让位（默认）/ diagonal 对角错位 / gray_down 后句从上落入、前句变灰下沉 / squeeze 后句从大缩入挤开前句。"""
    v = t.get('variant', 'push_up')
    l1, l2 = t['text'], t['text2']
    sw = _at(t, 'switch_at', 0, 1, 0.45 * (t['t1'] - t['t0']), 0.5)
    key = t.get('key_color', tc.get('key_color', accent))
    s1 = fit(H * 0.05, l1, W * 0.84, cond)
    s2 = fit(H * 0.075, l2, W * 0.88, cond)
    y = H * t.get('y', 0.60)
    hl2 = t.get('hl2') or hl or [l2]
    if v == 'diagonal':
        add(text=l1, role='title', size=s1, x=W * 0.08, y=y - s1, an=7, condense=cond, color=white, delay=0,
            move={'at': sw - 0.05, 'dur': 0.25, 'dx': -W * 0.03, 'dy': -H * 0.03, 'scale': 0.8})
        add(text=l2, role='title', size=s2, x=W * 0.92, y=y + s2 * 0.15, an=9, condense=cond, color=white, hl=hl2, hl_color=key,
            delay=sw, anim='zoom_in')
    elif v == 'gray_down':
        add(text=l1, role='title', size=s1, x=W / 2, y=y, an=5, condense=cond, color=white, delay=0, anim='slide_up',
            move={'at': sw - 0.05, 'dur': 0.3, 'dy': s2 * 0.55, 'scale': 0.82, 'color': '#9A9A9A'})
        add(text=l2, role='title', size=s2, x=W / 2, y=y - s2 * 0.55, an=5, condense=cond, color=white, hl=hl2, hl_color=key,
            delay=sw, anim='drop')
    elif v == 'squeeze':
        add(text=l1, role='title', size=s1, x=W / 2, y=y, an=5, condense=cond, color=white, delay=0,
            move={'at': sw - 0.05, 'dur': 0.25, 'dy': -s2 * 0.95, 'scale': 0.85})
        add(text=l2, role='title', size=s2, x=W / 2, y=y + s1 * 0.2, an=5, condense=cond, color=white, hl=hl2, hl_color=key,
            delay=sw, anim='shrink_in')
    else:   # push_up
        add(text=l1, role='title', size=s1, x=W / 2, y=y, an=5, condense=cond, color=white, delay=0,
            move={'at': sw - 0.05, 'dur': 0.25, 'dy': -s2 * 0.9, 'scale': 0.78, 'alpha': 0.75})
        add(text=l2, role='title', size=s2, x=W / 2, y=y + s1 * 0.15, an=5, condense=cond, color=white, hl=hl2, hl_color=key,
            delay=sw, anim='drop')


def layout_chunks(t, add, W, H, k, cond, white, accent, tc):
    """说一块出一块（手法库 staged_chunk_reveal）：一句话切成 3~5 块，跟着口播一块块出现在人的一侧，越重要的块越大，
    前面的不消失。chunks: [{"text": "...", "w": 1~3}]，w=3 的块换强调色。"""
    right = t.get('side', 'left') == 'right'
    x, an = (W * 0.94, 9) if right else (W * 0.06, 7)
    y = H * t.get('y', 0.50)
    key = t.get('key_color', tc.get('key_color', accent))
    sizes = {1: 0.04, 2: 0.065, 3: 0.095}
    chunks = t['chunks']
    for j, c in enumerate(chunks):
        c = c if isinstance(c, dict) else {'text': c, 'w': 2}
        w = c.get('w', 2)
        size = fit(H * sizes.get(w, 0.065), c['text'], W * 0.86, cond)
        indent = (W * 0.03 * (j % 2)) * (-1 if right else 1)
        add(text=c['text'], role='title' if w > 1 else 'body', size=size, x=x + indent, y=y, an=an, condense=cond if w > 1 else 100,
            color=key if w == 3 else white, delay=_at(t, 'chunk_at', j, len(chunks), 0.0), anim='fade_up')
        y += size * 1.08


def layout_list(t, add, W, H, k, cond, white, accent, soft, tc):
    """并列项逐条出现（手法库 list_accumulate），前面的不消失。variant：
    conclude 列举后收拢让位给结论（要 conclude 字段）/ bullets 侧边方块要点配灰色英文影子（items_en 可选）/
    grid 两列编号网格，编号出现后淡成底纹再打出名称 / one 一屏一个、连续几屏（三连击）。"""
    v = t.get('variant', 'conclude')
    rows = t['items']
    n = len(rows)
    key = t.get('key_color', tc.get('key_color', accent))
    at = [_at(t, 'item_at', j, n + (1 if t.get('conclude') else 0)) for j in range(n)]
    if v == 'bullets':
        x, y = W * t.get('x', 0.06), H * t.get('y', 0.50)
        size = min(fit(H * 0.036, '■ ' + r, W * 0.55) for r in rows)
        ens = t.get('items_en') or []
        for j, r in enumerate(rows):
            add(text='■ ' + r, role='body', size=size, x=x, y=y, an=7, color=white, delay=at[j], anim='fade_up')
            if j < len(ens) and ens[j]:
                add(text=ens[j], role='en_serif', size=size * 0.6, x=x + size * 1.1, y=y + size * 1.05, an=7, color='#BBBBBB', alpha=0.55,
                    delay=at[j] + 0.1, shadow=False)
            y += size * (1.9 if ens else 1.5)
    elif v == 'grid':
        x0, y0 = W * 0.08, H * t.get('y', 0.50)
        for j, r in enumerate(rows):
            cx, cy = x0 + (j % 2) * W * 0.46, y0 + (j // 2) * H * 0.1
            ns = H * 0.06
            add(text=f'{j + 1:02d}', role='en_display', size=ns, x=cx, y=cy, an=7, color=white, delay=at[j], anim='pop',
                move={'at': at[j] + 0.3, 'dur': 0.2, 'alpha': 0.22}, shadow=False)
            add(text=r, role='title', size=fit(H * 0.032, r, W * 0.36, cond), x=cx + ns * 0.12, y=cy + ns * 0.42, an=7, condense=cond,
                color=white, delay=at[j] + 0.35, anim='type')
    elif v == 'one':
        for j, r in enumerate(rows):
            end = at[j + 1] if j + 1 < n else None
            add(text=r, role='title', size=fit(H * 0.1, r, W * 0.86, cond), x=W / 2, y=H * t.get('y', 0.58), an=5, condense=cond,
                color=key if j == n - 1 else white, delay=at[j], until=end, anim=t.get('item_anim', 'flash'))
    else:   # conclude
        y = H * t.get('y', 0.50)
        size = min(fit(H * 0.058, r, W * 0.8, cond) for r in rows)
        ca = _at(t, 'item_at', n, n + 1)
        lift = H * 0.09 if t.get('conclude') else 0
        for j, r in enumerate(rows):
            add(text=r, role='title', size=size, x=W / 2, y=y + j * size * 1.25, an=5, condense=cond, color=white, delay=at[j], anim='slide_left',
                **({'move': {'at': ca - 0.05, 'dur': 0.3, 'dy': -lift - j * size * 1.25 * 0.38, 'scale': 0.62, 'alpha': 0.8}} if lift else {}))
        if t.get('conclude'):
            cs = fit(H * 0.075, t['conclude'], W * 0.9, cond)
            add(text=t['conclude'], role='title', size=cs, x=W / 2, y=y + n * size * 1.25 * 0.62 - lift + cs * 0.6, an=5, condense=cond,
                color=key, delay=ca, anim='slide_left')


CHIP_COLORS = {'bilingual': '#2E3B2A', 'gold': '#7A1E2A', 'red_bar': '#2A2A2A', 'stack3': '#111111'}
CAPSULES = ['#F2C230', '#6FB1F7', '#F2735B', '#64C98A', '#B48CF2', '#F29BC1']


def layout_chips(t, add, items, W, H, k, white, accent, tc):
    """标签卡逐个点出（手法库 label_chips_sequence）：口播连着说几个并列短语时，人旁边按说话节奏一张张弹出小标签卡。
    variant：bilingual 胸前一张中英标签卡（默认，颜色跟主题走）/ red_bar 深灰卡里红条擦入、沿对角线排 /
    gold 暗红小卡金字、从右往左高低错落 / capsule 人两侧彩色胶囊（开场预告要点）/ stack3 浅底竖排要点。"""
    v = t.get('variant', 'bilingual')
    rows = t.get('items') or [t['text']]
    ens = t.get('items_en') or []
    n = len(rows)
    color = t.get('chip_color', CHIP_COLORS.get(v, '#2E3B2A'))

    def chip(j, text, x, y, an, size, bg, alpha, fg, role='title', en=None, bar=None, slide=0, radius=None):
        d = _at(t, 'item_at', j, n)
        w = text_w(text, size) + size * 1.2
        if en:
            w = max(w, text_w(en, size * 0.36) * 1.3 + size * 1.2)
        h = size * (1.75 if en else 1.45)
        x0 = x - w / 2 if an == 5 else (x - w if an == 9 else x)
        items.append({'kind': 'shape', 'x': x0, 'y': y - h / 2, 'w': w, 'h': h, 'r': radius if radius is not None else h * 0.22, 'color': bg,
                      'alpha': alpha, 'delay': d, 'anim': 'pop' if not slide else 'slide', 'slide': slide})
        if bar:
            items.append({'kind': 'shape', 'x': x0 + h * 0.12, 'y': y - h / 2 + h * 0.14, 'w': w - h * 0.24, 'h': h * 0.72, 'r': h * 0.1,
                          'color': bar, 'alpha': 0.95, 'delay': d + 0.05, 'wipe': 0.25})
        ty = y - (size * 0.22 if en else 0)
        add(text=text, role=role, size=size, x=x0 + w / 2, y=ty, an=5, color=fg, delay=d + (0.18 if bar else 0.06), anim='fade', shadow=False,
            **({'slide': slide} if slide else {}))
        if en:
            add(text=en.upper(), role='en', size=size * 0.36, x=x0 + w / 2, y=y + size * 0.5, an=5, color='#CFCFCF', spacing=size * 0.08,
                delay=d + 0.12, anim='fade', shadow=False)

    if is_landscape(W, H):
        for j, r in enumerate(rows):
            side = ('left' if j % 2 == 0 else 'right') if v == 'capsule' else t.get('side', 'right' if v == 'gold' else 'left')
            l, top, rr, bot = side_box(t, W, H, side, center=False)
            count = (n + 1) // 2 if v == 'capsule' else n
            row = j // 2 if v == 'capsule' else j
            step = min(H * 0.17, (bot - top) / max(1, count))
            en = ens[j] if j < len(ens) else None
            size = min(58 * k, step / (2.3 if en else 1.9), (rr - l) / (text_w(r, 1) + 1.6))
            if en:
                size = min(size, (rr - l) / (text_w(en, 0.36) * 1.3 + 1.6))
            chip(j, r, (l + rr) / 2, (top + bot) / 2 + (row - (count - 1) / 2) * step, 5, size,
                 CAPSULES[j % len(CAPSULES)] if v == 'capsule' else color, 0.84,
                 '#1A1A1A' if v == 'capsule' else '#F2D9A0' if v == 'gold' else '#F2DE73' if v == 'stack3' else white,
                 role='serif' if v in ('gold', 'red_bar', 'stack3') else 'title', en=en,
                 bar=accent if v == 'red_bar' else None, radius=size * 0.8 if v == 'capsule' else None)
        return

    if v == 'red_bar':
        size = H * 0.03
        for j, r in enumerate(rows):
            chip(j, r, W * (0.08 + 0.13 * j), H * (0.50 + 0.07 * j), 7, size, color, 0.62, '#FFFFFF', role='serif', bar=accent)
    elif v == 'gold':
        size = H * 0.028
        x = W * 0.94
        for j, r in enumerate(rows):
            w = text_w(r, size) + size * 1.2
            chip(j, r, x, H * (0.54 + (0.03 if j % 2 else 0)), 9, size, color, 0.9, '#F2D9A0', en=ens[j] if j < len(ens) else None)
            x -= w + W * 0.02
    elif v == 'capsule':
        size = H * 0.026
        for j, r in enumerate(rows):
            left = j % 2 == 0
            chip(j, r, W * (0.05 if left else 0.95), H * (0.26 + 0.075 * (j // 2)), 7 if left else 9, size, CAPSULES[j % len(CAPSULES)], 0.95,
                 '#1A1A1A', role='body', slide=-1 if left else 1, radius=size * 0.8)
    elif v == 'stack3':
        size = H * 0.03
        for j, r in enumerate(rows):
            chip(j, r, W / 2, H * (0.50 + 0.085 * j), 5, size, color, 0.45, '#F2DE73', role='serif')
    else:   # bilingual
        size = H * 0.034
        for j, r in enumerate(rows):
            chip(j, r, W / 2, H * t.get('y', 0.64) - j * H * 0.085, 5, size, color, 0.74, '#FFFFFF', en=ens[j] if j < len(ens) else None)


def add_block(t, items, W, H, k):
    """色块衬底关键词（手法库 kw_color_block）：在关键词背后刷出一块纯色，先刷块再出字。
    block: {"color": "#0A1EFF", "style": solid 紧贴实心块（默认）/ offset 错位刷块 / skew 斜切渐隐条 / grow 方块拉长成条,
            "text": 要垫的词（默认第一个强调词）, "ink": 块上字的颜色（默认按块的明暗选黑或白）}"""
    b = t['block'] if isinstance(t['block'], dict) else {'color': t['block']}
    word = b.get('text') or (t.get('hl') or [None])[0]
    texts = [i for i in items if i.get('text') and i.get('kind') is None and (not word or word in i['text'])]
    if not texts:
        return
    it = max(texts, key=lambda i: i['size'])
    word = word or it['text']
    cond = it.get('condense', 100)
    pre = it['text'].split(word)[0]
    full = text_w(it['text'], it['size'], cond) + it.get('spacing', 0) * len(it['text'])
    x_left = it['x'] if it['an'] in (7, 4, 1) else (it['x'] - full if it['an'] in (9, 6, 3) else it['x'] - full / 2)
    x0 = x_left + text_w(pre, it['size'], cond) + it.get('spacing', 0) * len(pre)
    w = text_w(word, it['size'], cond) + it.get('spacing', 0) * len(word)
    top = it['y'] if it['an'] in (7, 8, 9) else (it['y'] - it['size'] / 2 if it['an'] in (4, 5, 6) else it['y'] - it['size'])
    style, color = b.get('style', 'solid'), b.get('color', '#0A1EFF')
    r, g, bl = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    ink = b.get('ink', '#111111' if (0.299 * r + 0.587 * g + 0.114 * bl) > 150 else '#FFFFFF')
    pad = it['size'] * 0.22
    d = it.get('delay', 0)
    shape = {'kind': 'shape', 'x': x0 - pad, 'y': top + it['size'] * 0.04, 'w': w + pad * 2, 'h': it['size'] * 0.98, 'r': 0, 'color': color,
             'alpha': 1.0, 'delay': d, 'wipe': 0.22}
    if style == 'offset':
        shape.update(y=shape['y'] + it['size'] * 0.12, rot=-2)
    elif style == 'skew':
        shape.update(skew=0.27, w=shape['w'] + W * 0.12, fade_tail=True, h=it['size'] * 0.8, y=top + it['size'] * 0.14)
    elif style == 'grow':
        shape.update(wipe=0.23, wipe_from=shape['h'])
    items.insert(items.index(it), shape)
    it['delay'] = d + 0.18
    if word == it['text']:
        it['color'] = ink
        it['hl'] = []
    else:
        it['hl'] = [word]
        it['hl_color'] = ink
    it['shadow'] = False


BEHIND_VARIANTS = {
    'brand_head': '行业色点题大字：两三个字的超粗大字铺在头部高度，头发和肩膀挡住一部分',
    'top_keyword': '头顶要点关键词：橙黄色超粗关键词压在头顶，头发盖住字的下沿，放大加模糊落定',
    'hollow_sandwich': '实心镂空夹人：两行英文巨字，实心字在人后面，只剩描边的同一行字在人前面，人像嵌在字中间',
}


def layout_behind(t, add, W, H, k, white, tc):
    """人压字（behind_text）。字画在人后面，render 再把抠出来的人盖上来；front=True 的那一项画在人前面。
    _luma（字那块背景的亮度）和 _head_top（头顶高度）由 render 量好写进来。"""
    v = t.get('variant', 'brand_head')
    ink = t['color'] if 'color' in t else (tc.get('ink_color', '#16161A') if t.get('_luma', 0) > 0.6 else white)
    x = W * t.get('x', 0.5)
    if v == 'top_keyword':   # 字高约 6% 画面高，下沿约两成被头发盖住
        n = max(len(l) for l in lines_of(t['text'])) or 1
        size = min(t.get('size', H * 0.062 / k) * k, W * 0.8 / n)
        y = t['y'] * H if 'y' in t else max(size * 0.62, t.get('_head_top', 0.12) * H - size * 0.30)
        add(text=t['text'], role=t.get('font', 'title'), size=size, x=x, y=y, an=5, color=t.get('color', '#F5D547'), shadow=True, condense=100, anim='zoom_blur')
        return
    if v == 'hollow_sandwich':   # 只适合英文和数字，中文笔画镂空看不清
        txt = (t.get('en') or t['text']).upper()
        words = txt.split()
        cut = min(range(1, len(words)), key=lambda i: abs(len(' '.join(words[:i])) - len(' '.join(words[i:]))), default=len(words))
        rows = [' '.join(words[:cut]), ' '.join(words[cut:])] if len(words) > 1 else [txt]
        size = min(t.get('size', H * 0.29 / k) * k, W * 0.88 / (max(len(r) for r in rows) * 0.24))   # Anton 很窄：大写字母宽约 0.24 个字号
        y0 = H * t.get('y', 0.22)
        for j, r in enumerate(rows):
            y = y0 + j * size * 0.56
            common = dict(text=r, role='en_display', size=size, x=x, y=y, an=5, color=ink, condense=100, delay=0.1 * j, anim='blur_still')
            add(**common, shadow=ink == white)
            add(**common, shadow=False, hollow=True, front=True)
        return
    n = max(len(l) for l in lines_of(t['text'])) or 1
    size = t.get('size', W * 0.92 / n / 0.69 / k) * k
    add(text=t['text'], role=t.get('font', 'title'), size=size, x=x, y=H * t.get('y', 0.21), an=5,
        color=ink, shadow=ink == white, condense=100)


MIXLINE_VARIANTS = {
    'static': '静态混排：关键词放大约 2.7 倍，其余小字同一条底边',
    'focus': '出现后突出：整句同样大小溶解飘下，说到关键词时它放大到 150% 变金黄，其余缩到 80%，最后整句缩小离场',
}


def _assc(c):
    from kvlib import hex_rgba
    r, g, b, a = hex_rgba(c)
    return f'&H{255 - a:02X}{b:02X}{g:02X}{r:02X}'


def _ass_esc(s):
    return s.replace('\\', '＼').replace('{', '｛').replace('}', '｝')


def layout_mixline(t, add, W, H, k, white, tc):
    """一行大小字混排（mix_size_line）：一行字里只有 key 放大，其余小字同一条底边（ASS 一行里换字号，libass 按基线对齐）。
    focus 变体整句先同样大，到 focus_at（相对秒，默认说到 key 的时刻或 0.8 秒）关键词放大变金、其余缩小。"""
    v = t.get('variant', 'static')
    text, key = t['text'], t['key']
    i = text.find(key)
    segs = [(text[:i], False), (key, True), (text[i + len(key):], False)] if i >= 0 else [(text, False)]
    segs = [(s_, b) for s_, b in segs if s_]
    gold = t.get('key_color', '#F2C230')
    if v == 'focus':
        size = H * t.get('size_h', 0.042)
        total = sum(text_w(s_, size) for s_, _ in segs)
        size *= min(1.0, W * 0.86 / max(total * 1.5, 1))
        a = int(t.get('focus_at', 0.8) * 1000)
        b = a + 280
        rich = ''.join(f"{{\\fscx100\\fscy100\\c{_assc(white)}\\t({a},{b},"
                       + (f"\\fscx150\\fscy150\\c{_assc(gold)})}}" if big else "\\fscx80\\fscy80)}")
                       + _ass_esc(s_) for s_, big in segs)
        add(text=text, rich=rich, role=t.get('font', 'title'), size=size, x=W * t.get('x', 0.5), y=H * t.get('y', 0.66), an=2,
            condense=100, anim='blur_down')
        return
    small = H * t.get('size_h', 0.034)
    big = small * t.get('ratio', 2.7)
    total = sum(text_w(s_, big if b_ else small) for s_, b_ in segs)
    f = min(1.0, W * 0.88 / max(total, 1))
    small, big = small * f, big * f
    rich = ''.join(f"{{\\fs{(big if b_ else small):.0f}\\c{_assc(gold if b_ else white)}}}" + _ass_esc(s_) for s_, b_ in segs)
    left = t.get('align', 'left') == 'left'
    add(text=text, rich=rich, role=t.get('font', 'title'), size=small, x=W * t.get('x', 0.07 if left else 0.5), y=H * t.get('y', 0.66),
        an=1 if left else 2, condense=100)


def layout_title(t, st, W, H):
    """返回 (items, 需要压暗的区域说明)。尺寸以短边 1080 为基准按比例缩放。"""
    tc = st['title']
    k = unit(W, H)
    lay = 'behind' if t.get('behind') and 'layout' not in t else t.get('layout', tc.get('layout', 'side'))
    if lay in GRAPHIC_LAYOUTS:   # 数据卡、环形图、雾面和标题页章节由 cards.py 逐帧画，不走 ASS
        return []
    S = t.get('size', tc['size']) * k
    cond = t.get('condense', tc.get('condense', 100))
    white, accent = t.get('color', tc['color']), t.get('hl_color', tc['hl_color'])
    soft = t.get('lead_color', tc.get('lead_color', white))
    hl = t.get('hl', [])
    items = []

    def add(**kw):
        kw.setdefault('color', white)
        kw.setdefault('shadow', not t.get('on_light'))
        kw.setdefault('delay', 0.07 * len([i for i in items if i.get('kind') != 'dim']))
        items.append(kw)

    if lay in ('side', 'mix'):
        right = t.get('side', 'left') == 'right'
        x = W * t.get('x', 0.95 if right else 0.05)
        an = 9 if right else 7
        y = H * t.get('y', 0.50)
        maxw = W * t.get('max_w', 0.62)
        rows = t.get('lines') if lay == 'mix' else None
        if rows is None:
            rows = []
            if t.get('lead'):
                rows.append({'text': t['lead'], 'role': 'body', 'size': tc['lead_size'], 'color': soft, 'spacing': 2})
            for ln in lines_of(t['text']):
                rows.append({'text': ln, 'role': t.get('font', 'title'), 'size': S / k, 'hl': hl})
            if t.get('en'):   # 英文副标：tracked 全大写宽字距细字（中文大字配宽字距英文，网感档默认）/ serif 斜体衬线（克制档）
                if t.get('en_look', tc.get('en_look', 'serif')) == 'tracked':
                    rows.append({'text': t['en'].upper(), 'role': 'en', 'size': tc['tag_size'] * 0.95, 'color': soft, 'spacing': 9, 'alpha': 0.78})
                else:
                    rows.append({'text': t['en'], 'role': 'en_serif', 'size': tc['en_size'], 'color': soft})
        for r in rows:
            role = r.get('role', 'title')
            c = cond if role == 'title' else 100
            size = r.get('size', S / k) * k
            if role in ('title', 'serif'):
                size = fit(size, r['text'], maxw, c)
            add(text=r['text'], role=role, size=size, x=x, y=y, an=an, condense=c, color=r.get('color', white),
                hl=r.get('hl', hl), hl_color=accent, spacing=r.get('spacing', 0) * k, **({'alpha': r['alpha']} if 'alpha' in r else {}))
            y += size * (1.12 if role in ('body', 'en_serif', 'en') else 0.98)

    elif lay == 'split':
        y = H * t.get('y', 0.27)
        maxw = W * 0.34
        size = min(fit(S, t['left'], maxw, cond), fit(S, t['right'], maxw, cond))
        for side, txt, en in (('l', t['left'], t.get('left_en')), ('r', t['right'], t.get('right_en'))):
            x, an = (W * 0.04, 7) if side == 'l' else (W * 0.96, 9)
            add(text=txt, role='title', size=size, x=x, y=y, an=an, condense=cond, hl=hl, hl_color=accent)
            if en:
                add(text=en.upper(), role='en', size=tc['tag_size'] * k, x=x + (6 * k if side == 'l' else -6 * k), y=y + size * 1.0,
                    an=an, color=accent, spacing=8 * k)

    elif lay == 'quote':
        x, y = W * t.get('x', 0.08), H * t.get('y', 0.32)
        maxw = W * 0.84
        for ln in lines_of(t['text']):
            big = any(w in ln for w in hl)
            size = fit(S * (1.4 if big else 1.0), ln, maxw)
            add(text=ln, role='serif', size=size, x=x, y=y, an=7, hl=hl, hl_color=accent)
            y += size * 1.12
        if t.get('en'):
            add(text=t['en'], role='en_serif', size=tc['en_size'] * k, x=x + 4 * k, y=y + 8 * k, an=7, color=soft)

    elif lay == 'chapter':
        x, y = W * t.get('x', 0.06), H * t.get('y', 0.30)
        if t.get('dim', True):
            items.append({'kind': 'dim', 'alpha': 0.45, 'delay': 0})
        num = str(t.get('number', '01'))
        ns = S * 2.6
        add(text=num, role='en_display', size=ns, x=x - 10 * k, y=y, an=7, hollow=True, alpha=0.75, shadow=False)
        y += ns * 0.98
        size = fit(S, t['text'], W * 0.86, cond)
        add(text=t['text'], role='title', size=size, x=x, y=y, an=7, condense=cond, hl=hl, hl_color=accent)
        y += size * 1.06
        if t.get('en'):
            add(text=t['en'].upper(), role='en', size=tc['tag_size'] * k, x=x + 6 * k, y=y, an=7, color=accent, spacing=6 * k)
            y += tc['tag_size'] * k * 1.5
        if t.get('sub'):
            add(text=t['sub'], role='body', size=tc['lead_size'] * k * 0.9, x=x + 6 * k, y=y, an=7, color=soft, spacing=2 * k)

    elif lay == 'stack':
        # 编号卡逐张累加：「三步走」「四个原因」这类并列要点，一条一条出现，前面的留着
        right = t.get('side', 'left') == 'right'
        x, an = (W * 0.95, 9) if right else (W * 0.06, 7)
        y = H * t.get('y', 0.30)
        if t.get('text'):
            hs = fit(S * 0.6, t['text'], W * 0.84, cond)
            add(text=t['text'], role='title', size=hs, x=x, y=y, an=an, condense=cond, hl=hl, hl_color=accent, delay=0)
            y += hs * 1.25
        rows = t.get('items', [])
        # 要点是这一屏的主角（常配纸页底整屏盖住口播），字要比引子大一档；每条按口播说到它的时刻出现（item_at），写了 every 按固定间隔
        ns, ts = tc['lead_size'] * k * 2.1, tc['lead_size'] * k * 1.6
        ts = min(ts, min(fit(ts, r, W * 0.84 - ns, cond) for r in rows) if rows else ts)
        for j, row in enumerate(rows):
            num = f'{j + 1:02d}'
            d = 0.3 + j * t['every'] if 'every' in t else _at(t, 'item_at', j, len(rows))
            if right:
                add(text=row, role='body', size=ts, x=x, y=y + ns * 0.2, an=9, spacing=2 * k, delay=d)
                add(text=num, role='en_display', size=ns, x=x - text_w(row, ts) - 24 * k, y=y, an=9, color=accent, delay=d)
            else:
                add(text=num, role='en_display', size=ns, x=x, y=y, an=7, color=accent, delay=d)
                add(text=row, role='body', size=ts, x=x + ns * 0.95, y=y + ns * 0.2, an=7, spacing=2 * k, delay=d)
            y += ns * 1.15

    elif lay == 'count':
        # 数字滚动大字：数字从 from 滚到 value，下面一行单位或说明
        x, y = W * t.get('x', 0.5), H * t.get('y', 0.36)
        an = {'left': 7, 'right': 9}.get(t.get('align', 'center'), 8)
        if an == 7:
            x = W * t.get('x', 0.06)
        dec = t.get('decimals', 0)
        final = f"{t.get('prefix', '')}{t['value']:,.{dec}f}{t.get('suffix', '')}"
        ns = fit(S * 1.6, final, W * 0.9)
        if t.get('lead'):
            add(text=t['lead'], role='body', size=tc['lead_size'] * k, x=x, y=y - tc['lead_size'] * k * 1.4, an=an, color=soft, spacing=2 * k,
                delay=0)
        add(text=final, role='en_display', size=ns, x=x, y=y, an=an, color=t.get('num_color', accent),
            count={'from': t.get('from', 0), 'to': t['value'], 'dur': t.get('roll', 0.9), 'decimals': dec,
                   'prefix': t.get('prefix', ''), 'suffix': t.get('suffix', '')})
        if t.get('text'):
            add(text=t['text'], role='title', size=fit(S * 0.55, t['text'], W * 0.9, cond), x=x, y=y + ns * 1.02, an=an, condense=cond,
                hl=hl, hl_color=accent)
        if t.get('log'):   # 数字下面一行绿色原始日志当证据（大数字浮现的「滚动加日志」变体）
            ls = H * 0.017
            ly = y + ns * (1.02 + (0.62 if t.get('text') else 0.1))
            lw = text_w(t['log'], ls) + ls * 1.4
            items.append({'kind': 'shape', 'x': x - lw / 2 if an == 8 else x, 'y': ly - ls * 0.3, 'w': lw, 'h': ls * 1.6, 'r': ls * 0.3,
                          'color': '#000000', 'alpha': 0.5, 'delay': t.get('roll', 0.9)})
            add(text=t['log'], role='en', size=ls, x=x if an != 8 else x, y=ly, an=an, color='#3BD16F', spacing=1 * k, delay=t.get('roll', 0.9) + 0.1,
                anim='type', shadow=False)

    elif lay == 'word':
        # 整屏单字页：一两个字撑满画面，配一行英文小字；适合强动作词、段落冲击页，配 hidden 黑底或整屏压暗
        if t.get('dim', True):
            items.append({'kind': 'dim', 'alpha': 0.55, 'delay': 0})
        size = fit(W, t['text'], W * 0.86, cond)
        y = H * t.get('y', 0.42)
        add(text=t['text'], role=t.get('font', 'title'), size=size, x=W / 2, y=y, an=5, condense=cond, hl=hl, hl_color=accent)
        if t.get('en'):
            add(text=t['en'].upper(), role='en', size=tc['tag_size'] * k * 1.2, x=W / 2, y=y + size * 0.62, an=5, color=accent,
                spacing=10 * k)

    elif lay == 'mixline':
        layout_mixline(t, add, W, H, k, white, tc)

    elif lay == 'behind':
        layout_behind(t, add, W, H, k, white, tc)

    elif lay == 'flank':
        layout_flank(t, add, W, H, k, S, cond, white, accent, soft, tc)

    elif lay == 'yield':
        layout_yield(t, add, W, H, k, cond, white, accent, tc, hl)

    elif lay == 'chunks':
        layout_chunks(t, add, W, H, k, cond, white, accent, tc)

    elif lay == 'list':
        layout_list(t, add, W, H, k, cond, white, accent, soft, tc)

    elif lay == 'chips':
        layout_chips(t, add, items, W, H, k, white, accent, tc)

    elif lay == 'concept':
        if t.get('dim', True):
            items.append({'kind': 'dim', 'alpha': 0.5, 'delay': 0})
        size = fit(H * t.get('size_h', 0.085), t['text'], W * 0.84, 100)
        sp = size * 0.45
        y = H * t.get('y', 0.36)
        add(text=t['text'], role=t.get('font', 'serif'), size=size, x=W / 2, y=y, an=5, spacing=sp, color=t.get('color', '#F4F1C0'),
            glow=True, anim='blur_still', delay=t.get('reveal_at', 0.35), hl=hl, hl_color=accent)
        if t.get('en'):
            add(text=t['en'].upper(), role='en', size=H * 0.02, x=W / 2, y=y + size * 0.85, an=5, color='#9A9A9A', spacing=H * 0.012,
                anim='blur_still', delay=t.get('reveal_at', 0.35) + 0.15, shadow=False)

    elif lay == 'bignum':
        # 巨数字点题：「这 4 个方法」时画面一侧立起一个占画面高七成的灰白数字，部分出血到画外，旁边星光闪
        right = t.get('side', 'left') == 'right'
        size = H * t.get('size_h', 0.70)
        x = W * t.get('x', 0.97 if right else 0.03)
        y = H * t.get('y', 0.56)
        add(text=str(t['number']), role='en_display', size=size, x=x, y=y, an=6 if right else 4, color=t.get('color', '#D8D8D0'),
            alpha=0.82, anim='zoom_in', shadow=False)
        w = text_w(str(t['number']), size)
        sx = (x - w * 0.95) if right else (x + w * 0.95)
        for j, (dx, dy, s) in enumerate(((0, -0.22, 0.09), (0.06, -0.12, 0.05))):
            items.append({'kind': 'doodle', 'type': 'sparkle', 'x': sx / W + (-dx if right else dx), 'y': y / H + dy, 'w': s, 'h': s * W / H,
                          'delay': 0.25 + j * 0.15, 'color': t.get('sparkle_color', '#F7F5F0')})
        if t.get('text'):
            ts = fit(S * 0.5, t['text'], W * 0.45, cond)
            add(text=t['text'], role='title', size=ts, x=W * (0.06 if right else 0.94), y=H * 0.52, an=7 if right else 9, condense=cond,
                hl=hl, hl_color=accent, delay=0.3)

    elif lay == 'number':
        # 大数字浮现：先压暗，再让窄体大数字带柔光从模糊变清楚；上面一行拉开字距的金色小标题，下面一行灰色说明
        if t.get('dim', True):
            items.append({'kind': 'dim', 'alpha': 0.6, 'delay': 0})
        y = H * t.get('y', 0.40)
        reveal = t.get('reveal_at', 0.4)
        ns = fit(H * t.get('size_h', 0.12), str(t['value']), W * 0.8)
        if t.get('lead'):
            add(text=t['lead'].upper() if t['lead'].isascii() else t['lead'], role='body', size=H * 0.022, x=W / 2, y=y - ns * 0.78, an=5,
                color='#C9A24A', spacing=H * 0.008, anim='blur_still', delay=reveal - 0.1, shadow=False)
        add(text=str(t['value']), role='en_display', size=ns, x=W / 2, y=y, an=5, color=t.get('num_color', '#F2EFB8'), glow=True,
            anim='blur_still', delay=reveal)
        if t.get('text'):
            add(text=t['text'], role='body', size=H * 0.021, x=W / 2, y=y + ns * 0.72, an=5, color='#A8A6A0', spacing=H * 0.003,
                anim='blur_still', delay=reveal + 0.15, shadow=False)

    else:   # plain：居中一行大字，可带一行说明（综艺感默认）
        x, y = W * t.get('x', 0.5), H * t.get('y', 0.32)
        an = {'left': 4, 'right': 6}.get(t.get('align', 'center'), 5)
        size = fit(S, t['text'], W * 0.92, cond)
        add(text=t['text'], role=t.get('font', 'title'), size=size, x=x, y=y, an=an, condense=cond, hl=hl, hl_color=accent,
            outline=t.get('outline', tc.get('outline', 0)) * k, outline_color=t.get('outline_color', tc.get('outline_color', '#000000')),
            box=t.get('box'))
        if t.get('sub'):
            add(text=t['sub'], role='body', size=tc['lead_size'] * k, x=x, y=y + size * 0.75, an=an, color=soft, spacing=3 * k)

    if t.get('block'):
        add_block(t, items, W, H, k)

    # 整组字不压字幕：底边超过字幕区上沿（默认画面 75% 高处）就整组往上挪
    def bottom_of(i):
        if i.get('kind') == 'shape':
            return i['y'] + i['h']
        return i['y'] + (i['size'] * 0.5 if i['an'] in (4, 5, 6) else (0 if i['an'] in (1, 2, 3) else i['size'] * 0.95))
    if lay not in ('behind', 'bignum'):
        limit = H * t.get('max_bottom', 0.75)
        bottom = max((bottom_of(i) for i in items if i.get('kind') in (None, 'shape')), default=0)
        if bottom > limit:
            for i in items:
                if i.get('kind') in (None, 'shape'):
                    i['y'] -= bottom - limit

    # 通用点缀：半透明巨字底纹、手写批注
    if t.get('ghost'):
        g = t['ghost'] if isinstance(t['ghost'], dict) else {'text': t['ghost']}
        gs = fit(g.get('size', 360) * k, g['text'], W * 0.96)
        items.insert(0, {'text': g['text'].upper(), 'role': 'en_display', 'size': gs, 'x': W / 2, 'y': H * g.get('y', 0.16), 'an': 5,
                         'color': white, 'alpha': g.get('alpha', 0.4), 'spacing': 8 * k, 'shadow': False, 'delay': 0})
    if t.get('note'):
        n = t['note'] if isinstance(t['note'], dict) else {'text': t['note']}
        items.append({'text': n['text'], 'role': 'note', 'size': n.get('size', 90) * k, 'x': W * n.get('x', 0.62), 'y': H * n.get('y', 0.62),
                      'an': 5, 'color': n.get('color', accent), 'rot': n.get('rot', -7), 'shadow': False, 'delay': 0.35})
    if is_landscape(W, H):
        _landscape_items(t, items, lay, W, H, tc.get('anim', 'blur_in'))
    return items


def _landscape_items(t, items, lay, W, H, default_anim='blur_in'):
    """保留每组字的层级和动效，横屏把整组收进人物两侧，章节改成左右两栏。"""
    ghost = items[0] if t.get('ghost') else None
    note = items[-1] if t.get('note') else None
    visible = [i for i in items if i.get('kind') in (None, 'shape') and i is not ghost and i is not note]
    if not visible:
        return

    def bounds(i):
        if i.get('kind') == 'shape':
            return i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h']
        size = max([i['size']] + [float(x) for x in re.findall(r'\\fs(\d+(?:\.\d+)?)', i.get('rich', ''))])
        rows = lines_of(i['text'])
        w = max(text_w(r, size, i.get('condense', 100)) + i.get('spacing', 0) * len(r) for r in rows)
        if i.get('rich'):
            fs, rw = i['size'], 0
            for part in re.split(r'(\{[^}]*\})', i['rich']):
                if part.startswith('{'):
                    match = re.search(r'\\fs(\d+(?:\.\d+)?)', part)
                    if match:
                        fs = float(match[1])
                else:
                    rw += text_w(part, fs, i.get('condense', 100))
            w = rw * (1.5 if '\\fscx150' in i['rich'] else 1)
        h = size * (1 + (len(rows) - 1) * 1.2)
        kind = i.get('anim', t.get('anim', default_anim))
        amp = 1.5 if kind == 'shrink_in' else 1.3 if kind in ('zoom_in', 'zoom_blur') else 1.08 if kind in ('pop', 'flash') else 1
        w, h = w * amp, h * amp
        a = i.get('an', 5)
        x = i['x'] - (0 if a in (1, 4, 7) else w if a in (3, 6, 9) else w / 2)
        y = i['y'] - (0 if a in (7, 8, 9) else h if a in (1, 2, 3) else h / 2)
        m = i.get('move') or {}
        dx, dy = m.get('dx', 0), m.get('dy', 0)
        return x + min(0, dx), y + min(0, dy), x + w + max(0, dx), y + h + max(0, dy)

    def place(group, box, enlarge=1.5):
        if not group:
            return
        bs = [bounds(i) for i in group]
        x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs)
        x1, y1 = max(b[2] for b in bs), max(b[3] for b in bs)
        l, top, r, bot = box
        # ASS 入场位移按短边像素计算，先给它留位置，不能只检查停稳后的文字。
        left = right = up = down = 0
        for i in group:
            if i.get('kind') or i.get('move'):
                continue
            kind = i.get('anim', t.get('anim', default_anim))
            if kind == 'slide_left':
                left = max(left, 90 * unit(W, H))
            elif kind == 'blur_in':
                if i.get('an') == 7:
                    left = max(left, 40 * unit(W, H))
                elif i.get('an') == 9:
                    right = max(right, 40 * unit(W, H))
                else:
                    down = max(down, 26 * unit(W, H))
            elif kind in ('drop', 'blur_down', 'fall'):
                up = max(up, H * 0.1 if kind == 'fall' else (54 if kind == 'drop' else 30) * unit(W, H))
            elif kind in ('slide_up', 'fade_up'):
                down = max(down, (60 if kind == 'slide_up' else 24) * unit(W, H))
        l, top, r, bot = l + left, top + up, r - right, bot - down
        # 给弹入、描边和柔光预留空间。
        f = min(enlarge, (r - l) * 0.88 / max(1, x1 - x0), (bot - top) * 0.84 / max(1, y1 - y0))
        cx, cy = (l + r) / 2, (top + bot) / 2
        for i in group:
            i['x'] = cx + (i['x'] - (x0 + x1) / 2) * f
            i['y'] = cy + (i['y'] - (y0 + y1) / 2) * f
            for key in ('size', 'spacing', 'w', 'h', 'r', 'outline', 'slide'):
                if key in i:
                    i[key] *= f
            if i.get('rich'):
                i['rich'] = re.sub(r'\\fs(\d+(?:\.\d+)?)', lambda m: '\\fs' + str(round(float(m[1]) * f)), i['rich'])
            if i.get('move'):
                i['move'] = dict(i['move'])
                for key in ('dx', 'dy'):
                    if key in i['move']:
                        i['move'][key] *= f
        # 手写坐标仍相对整张画布；能放下时保留，超出侧栏才收回来。
        ref = next((i for i in group if not i.get('kind')), group[0])
        bs = [bounds(i) for i in group]
        dx = W * t['x'] - ref['x'] if t.get('x') is not None and lay in ('side', 'mix', 'quote', 'count', 'behind', 'mixline', 'bignum', 'plain') else 0
        dy = H * t['y'] - ref['y'] if t.get('y') is not None else 0
        dx = min(r - max(b[2] for b in bs), max(l - min(b[0] for b in bs), dx))
        dy = min(bot - max(b[3] for b in bs), max(top - min(b[1] for b in bs), dy))
        for i in group:
            i['x'] += dx
            i['y'] += dy

    # 整页章节和单字页替代口播，背景不能只压暗后仍透出中间的人脸。
    if lay in ('chapter', 'word'):
        for i in items:
            if i.get('kind') == 'dim':
                i['alpha'] = 1.0
    if lay == 'chips':   # 卡底和字已按侧栏逐张排好
        pass
    elif lay == 'chapter':
        number = [i for i in visible if i.get('hollow')]
        rest = [i for i in visible if i not in number]
        # 默认整页章节替代口播，标题能用半幅宽；关掉背景时文字只放人物两侧。
        left_box = (W * 0.07, H * 0.2, W * 0.32, H * 0.72) if t.get('dim', True) else side_box(t, W, H, 'left', center=False)
        place(number, left_box, 1)
        box = (W * 0.38, H * 0.2, W * 0.93, H * 0.72) if t.get('dim', True) else side_box(t, W, H, 'right', center=False)
        place(rest, box, 1.5)
    elif lay == 'word':
        # 整屏字页和章节一样替代口播；明确不盖底时仍放侧栏，不能透着脸压字。
        box = (W * 0.05, H * 0.1, W * 0.95, H * 0.75) if t.get('dim', True) else side_box(t, W, H, center=False)
        place(visible, box, 1)
    elif lay in ('flank', 'split', 'bignum') or (lay == 'list' and t.get('variant') == 'grid') or (lay == 'yield' and t.get('variant') == 'diagonal'):
        for side, left in (('left', True), ('right', False)):
            group = [i for i in visible if (i['x'] < W / 2) == left]
            place(group, side_box(t, W, H, side, center=False))
    else:
        place(visible, side_box(t, W, H, center=False))
    if ghost is not None:
        main_left = sum(i['x'] for i in visible) / len(visible) < W / 2
        place([ghost], side_box(t, W, H, 'right' if main_left else 'left', center=False), 1)
    if note is not None:
        l, top, r, bot = side_box(t, W, H, center=False)
        place([note], (l, top, r, top + H * 0.13), 1)
    # 巨数字的星光跟随数字侧，不再沿画宽跑到人的脸上。
    for j, i in enumerate(i for i in items if i.get('kind') == 'doodle'):
        l, top, r, bot = side_box(t, W, H, center=False)
        i.update(x=(r - 28 * unit(W, H)) / W, y=(top + (j + 1) * (bot - top) / 4) / H,
                 w=0.025, h=0.025 * W / H)
