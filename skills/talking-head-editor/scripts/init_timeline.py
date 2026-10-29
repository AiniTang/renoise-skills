"""从粗剪结果生成 timeline.json 骨架：画布、口播、自动断好的跟读字幕，其余字段留空等你填。

用法：python init_timeline.py <项目目录> [--style premium|variety] [--max-chars 12]

字幕断句规则：按标点断开；「第一，」这类太短的半句和相邻半句合成一屏；
每屏不超过 max-chars 个字宽（中文 1 个字宽，英文字母和数字约半个），超长的在词语边界均分，
不在「的、了、吗」这类字前面断；显示时把逗号换成空格、去掉句末标点。
"""
import argparse
import warnings
warnings.filterwarnings("ignore")
import math
import re
from pathlib import Path

from kvlib import load_json, save_json, probe, canvas_for_source, canvas_size

PUNCT = '，。！？；：、,.!?;:'


NO_LEAD = set('的了着过吗呢吧啊呀得地们')  # 不能出现在一屏开头的字
SHORT_W, SHORT_DUR = 4, 0.8                  # 字宽不超过 4 或不到 0.8 秒算「太短」，会和相邻半句合并


def char_w(c):
    if re.match(r'[一-鿿　-〿＀-￯]', c):
        return 1.0
    if c.isspace():
        return 0.3
    return 0.55


def width(s):
    return sum(char_w(c) for c in s)


def merge_short(pieces, max_chars):
    out = []
    for p in pieces:
        if out:
            prev = out[-1]
            pw, cw = (width(''.join(c for c, _ in x if c not in PUNCT)) for x in (prev, p))
            short = (pw <= SHORT_W or prev[-1][1] - prev[0][1] < SHORT_DUR
                     or cw <= SHORT_W or p[-1][1] - p[0][1] < SHORT_DUR)
            # 合起来不超长就合；「第二」这种只有一两个字的，超长也合，下一步会在词语边界重新均分
            if short and (pw + cw <= max_chars or min(pw, cw) <= 2):
                out[-1] = prev + p
                continue
        out.append(p)
    return out


def word_bounds(text):
    try:
        import jieba
        jieba.setLogLevel(60)
        idx, res = 0, []
        for w in jieba.lcut(text):
            idx += len(w)
            res.append(idx)
        return res
    except ImportError:
        return list(range(1, len(text) + 1))


def split_line(line, max_chars):
    chars = line['chars']
    pieces, cur = [], []
    for ch, t in chars:
        cur.append((ch, t))
        if ch in PUNCT:
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    pieces = merge_short(pieces, max_chars)
    # 太长的片段均分成几屏，切点落在词语边界上（有 jieba 用 jieba 分词，没有就按字切）
    out = []
    for p in pieces:
        text = ''.join(c for c, _ in p)
        total = width(''.join(c for c in text if c not in PUNCT))   # 标点显示时会去掉，不算宽度
        if total <= max_chars:
            out.append(p)
            continue
        n = math.ceil(total / max_chars)
        bounds = [i for i in word_bounds(text) if i < len(text) and text[i] not in NO_LEAD] or word_bounds(text)
        cuts, acc, k = [], 0, 1
        widths = [char_w(c) for c in text]
        cum = [sum(widths[:i]) for i in range(len(text) + 1)]
        for k in range(1, n):
            target = total * k / n
            best = min(bounds, key=lambda i: abs(cum[i] - target))
            if best not in cuts and 0 < best < len(text):
                cuts.append(best)
        prev = 0
        for c in sorted(cuts) + [len(p)]:
            if c > prev:
                out.append(p[prev:c])
            prev = c
    return out


def subs_from_lines(lines, dur, max_chars=12):
    """按 lines.json 的逐字时间断好跟读字幕（样本册也用）。"""
    subs = []
    for ln in lines:
        for p in split_line(ln, max_chars):
            text = ''.join(c for c, _ in p).strip()
            shown = text.rstrip(PUNCT).replace('，', ' ').replace(',', ' ').strip()
            if not shown:
                continue
            subs.append({'t0': p[0][1], 't1': p[-1][1] + 0.18, 'text': shown, 'level': 'base', 'line': ln['i']})
    # 相邻字幕首尾相接，避免闪烁；最后一条不超过视频结尾
    for x, y in zip(subs, subs[1:]):
        if y['t0'] - x['t1'] < 0.35:
            x['t1'] = y['t0']
    if subs:
        subs[-1]['t1'] = min(subs[-1]['t1'] + 0.3, dur)
    for s_ in subs:
        s_['t0'], s_['t1'] = round(s_['t0'], 3), round(s_['t1'], 3)
    return [x for x in subs if x['t1'] > 0 and x['t0'] < dur]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--style', default='premium')
    ap.add_argument('--max-chars', type=int, default=12)
    ap.add_argument('--canvas', type=canvas_size, help='画布 WxH；默认跟随粗剪画布或源方向')
    ap.add_argument('--w', type=int)
    ap.add_argument('--h', type=int)
    ap.add_argument('--fps', type=int, default=30)
    a = ap.parse_args()
    proj = Path(a.project)
    lines = load_json(proj / 'lines.json')
    dur = probe(proj / 'aroll.mp4')['duration']
    subs = subs_from_lines(lines, dur, a.max_chars)
    if bool(a.w) != bool(a.h) or a.canvas and a.w:
        ap.error('--w 和 --h 要一起给，不能和 --canvas 同时使用')
    cv = canvas_for_source(proj / 'aroll.mp4', a.canvas or ((a.w, a.h) if a.w else None), a.fps)
    if not (a.canvas or a.w) and (proj / 'canvas.json').exists():
        cv = {**load_json(proj / 'canvas.json'), 'fps': a.fps}
    tl = {
        'canvas': cv,
        'style': a.style,
        'aroll': 'aroll.mp4',
        'duration': round(dur, 3),
        'fonts': {},
        'zoom': [],
        'layout': [],
        'broll': [],
        'subs': subs,
        'titles': [],
        'overlays': [],
        'audio': {'voice': {'denoise': True}, 'bgm': [], 'sfx': []},
    }
    save_json(tl, proj / 'timeline.json')
    print(f'timeline.json 已生成：{len(subs)} 条字幕，时长 {dur:.2f} 秒')
    for s in subs:
        print(f"  {s['t0']:6.2f}-{s['t1']:6.2f}  {s['text']}")


if __name__ == '__main__':
    main()
