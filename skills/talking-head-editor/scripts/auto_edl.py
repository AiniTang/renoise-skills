"""粗剪单初稿：按 transcript.json 自动挑出要留的语音岛，写成 edl.json，再由你校对文字、补标点、调顺序。

用法：python auto_edl.py transcript.json -o edl.json [--breath web_tight|premium_breath] [--speed 1.05]

自动做的判断（rough_cut_breath_trim）：
- 重录：后面 3 个岛以内有一句和它开头相同、相似度超过 0.8，只留最后一遍；
- 说了半句停下：4 个字以内、后面紧跟着同样开头的岛，删；
- 语气词：整个岛只有「嗯、啊、呃、那个」这类，删；岛开头、结尾的语气词按逐字时间剪掉；
- 疑似识别幻觉（transcribe 标了 suspect）：删。
删掉的岛写在 edl 的 dropped 里（为什么删），拿不准的翻回去改。文字是识别原文，没有标点，交给 rough_cut 前要改对。
"""
import argparse
import difflib
import re

from pathlib import Path

from kvlib import load_json, save_json, canvas_for_source, canvas_size

FILLER_CHARS = set('嗯啊呃额哦唔噢欸诶')
FILLER_WORDS = ('那个', '就是说', '然后呢', '就是')


def norm(t):
    return re.sub(r'[^\w一-鿿]', '', t).lower()


def only_filler(t):
    t = norm(t)
    for w in FILLER_WORDS:
        t = t.replace(w, '')
    return not t.strip(''.join(FILLER_CHARS))


def trim_fillers(isl):
    """岛开头、结尾的语气词按逐字时间剪掉。返回 (t0, t1, text)。"""
    ch = [c for c in isl.get('chars', []) if re.match(r'[\w一-鿿]', c[0])]
    t0, t1, text = isl['t0'], isl['t1'], isl['text']
    i, j = 0, len(ch)
    while i < j and ch[i][0] in FILLER_CHARS:
        i += 1
    while j > i and ch[j - 1][0] in FILLER_CHARS:
        j -= 1
    if ch and (i or j < len(ch)) and i < j:
        t0 = max(t0, ch[i][1] - 0.05) if i else t0
        t1 = min(t1, ch[j][1] - 0.02) if j < len(ch) else t1
        text = ''.join(c[0] for c in ch[i:j])
    return t0, t1, text


def retake_of(a, later):
    """a 是不是后面某一句的前一遍（重录或说了半句）。返回原因或 None。"""
    na = norm(a['text'])
    for b in later:
        nb = norm(b['text'])
        if not na or not nb:
            continue
        if len(na) <= 4 and nb.startswith(na[:2]):
            return f"说了半句，后面「{b['text'][:12]}」重说了"
        r = difflib.SequenceMatcher(None, na, nb[:len(na) + 2], autojunk=False).ratio()
        if r > 0.8 and na[:2] == nb[:2]:
            return f"重录，留后面那遍「{b['text'][:12]}」（相似度 {r:.2f}）"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('transcript')
    ap.add_argument('-o', '--out', default='edl.json')
    ap.add_argument('--breath', default='premium_breath', choices=['web_tight', 'premium_breath'])
    ap.add_argument('--canvas', type=canvas_size, help='画布 WxH；默认跟随源方向')
    ap.add_argument('--speed', type=float, default=1.0)
    a = ap.parse_args()
    tr = load_json(a.transcript)
    clips, dropped = [], []
    if not tr.get('files'):
        ap.error('转写里没有源素材')
    for f in tr['files']:
        f['src'] = str((Path(a.transcript).resolve().parent / f['src']).resolve())
        isl = f['islands']
        for k, x in enumerate(isl):
            why = None
            if x.get('suspect'):
                why = '疑似识别幻觉'
            elif only_filler(x['text']):
                why = '只有语气词'
            else:
                why = retake_of(x, isl[k + 1:k + 4])
            if why:
                dropped.append({'src': f['src'], 't0': x['t0'], 't1': x['t1'], 'text': x['text'], 'why': why})
                continue
            t0, t1, text = trim_fillers(x)
            clips.append({'src': f['src'], 't0': round(t0, 3), 't1': round(t1, 3), 'text': text})
    src = clips[0]['src'] if clips else tr['files'][0]['src']
    edl = {'canvas': canvas_for_source(src, a.canvas), 'speed': a.speed, 'breath': a.breath, 'clips': clips, 'dropped': dropped}
    save_json(edl, a.out)
    print(f'留 {len(clips)} 段，删 {len(dropped)} 段 → {a.out}')
    for d in dropped:
        print(f"  删 {d['t0']:6.2f}-{d['t1']:6.2f} {d['text'][:20]}：{d['why']}")
    print('文字是识别原文：改错字、加标点，段落结尾那一句写 "para": true（高级感留气口会在那里多留 1 秒）')


if __name__ == '__main__':
    main()
