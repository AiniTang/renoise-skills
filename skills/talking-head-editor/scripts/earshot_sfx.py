"""用 earshot 的代码音效库给画面配音效（由 kvlib.all_sfx 调用，要用装了 earshot 的 Python 跑）。

earshot（github.com/Leonxlnx/earshot，MIT）把 250 多个音效存成代码，渲染不需要模型和网络；它的 launch 预设给每种音效角色
定好了专业片子里量出来的摆法：对齐点（起音 / 最响处）、比画面提前或延后多少毫秒、比配乐高几 dB、连续出现至少隔多久。

输入（标准输入 JSON）：{"timeline", "cues": kvlib.sfx_cues 挑剩下的时刻, "sounds": kvlib.SOUNDS, "style", "bgm_gain"}
输出（标准输出 JSON）：[{"src": 音效文件, "t": 开始秒, "gain": 增益 dB, "role": 用了什么, "event": 对的画面时刻, "anchor": onset|peak}, ...]
音效渲染一次缓存在项目的 sfx/earshot/。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from earshot.forge import bank as BANK
from earshot.forge import kit as K

# 自动配的三种时刻在哪几个角色之间轮换（角色见 earshot 的 launch 预设），同类连着出现时换着用，避免听觉疲劳
ROLES = {
    'premium': {'title': ['whoosh.short', 'land', 'bell', 'tock', 'whoosh.short', 'swell'],
                'chapter': ['hit', 'whoosh.long', 'drop'],
                'broll': ['pop', 'snap', 'land.light', 'click']},
    'variety': {'title': ['pop', 'bell', 'tock', 'land', 'click.confirm'],
                'chapter': ['drop', 'hit', 'whoosh.long'],
                'broll': ['pop', 'tick.crisp', 'snap', 'click']},
    # 网感档：预设角色之外把音效库里的音色也轮进来（bank: 开头），同一种声音隔很久才再出现，听着不重复
    'web': {'title': ['pop', 'bank:pro_pop_in/round', 'whoosh.short', 'bank:mallet/glock', 'land', 'bank:ui_pop/boop',
                      'bell', 'bank:swish/zing', 'tock', 'bank:pro_notify/ding_2045', 'bank:knock/wood', 'bank:pro_pop/chirp'],
            'chapter': ['hit', 'bank:pro_logo_sting/sweep_hit', 'whoosh.long', 'bank:cut_hit/punch', 'drop', 'bank:pro_whoosh_big/tonal'],
            'broll': ['pop', 'bank:swipe/flick', 'snap', 'bank:pro_pop_in/airy', 'land.light', 'bank:shutter/quick', 'click',
                      'bank:ui_pop/soft', 'bank:swipe/glide']},
}
RUN_GAP = 0.6       # 同类素材相隔不到 0.6 秒算一串（照片一张张叠上来），一串用同一个角色、换不同变体
BANK_BED_DB = 7.0   # 音效库里按需渲染的声音（打字、故障、闪光等）比配乐高出的 dB
BANK_LEVEL_DB = -14.0
PEAK_ROLES = ('riser', 'swell')   # 蓄力类：最响处对准事件，起音在前面


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='.')
    a = ap.parse_args()
    req = json.load(sys.stdin)
    tl, cues, sounds = req['timeline'], req['cues'], req['sounds']
    style = req.get('style', 'premium')
    base = Path(a.base)
    kdir = base / 'sfx/earshot'
    (kdir / 'bank').mkdir(parents=True, exist_ok=True)
    kjson = kdir / 'kit.json'
    if not kjson.exists():
        K.init('launch', str(kjson))
    roles = K.render(str(kjson), str(kdir / 'takes'), log=lambda *x: None)['roles']

    bgms = tl.get('audio', {}).get('bgm', [])
    gains = req.get('bgm_gain', [0] * len(bgms))

    def bed(t):
        """t 时刻配乐在成片里的响度（LUFS），没有配乐返回 None。"""
        for m, g in zip(bgms, gains):
            if m['t0'] + 0.06 <= t <= m['t1']:
                src = Path(m['src']) if Path(m['src']).is_absolute() else base / m['src']
                try:
                    lv = K.bed_level(str(src), m.get('src_in', 0) + t - m['t0'])
                except Exception:
                    return None
                return None if lv is None else lv + g
        return None

    take_turn, out = {}, []

    def use_role(rname, cs):
        """cs：[{t, event, rate?}]。起音对准事件开始那一帧（earshot 预设里只有蓄力类按最响处对齐，其余是起音）；
        预设里比画面提前或延后的几十毫秒保留，超过两帧的按两帧算。"""
        role = roles[rname]
        align = 'peak' if rname in PEAK_ROLES else 'onset'
        off = max(-66.0, min(66.0, float(role.get('offset_ms') or 0.0)))
        keep_t = set(K.space_run([c['t'] for c in cs], role.get('min_gap_ms') or 0))
        for c in cs:
            if c['t'] not in keep_t:
                continue
            takes = role['takes']
            k = take_turn.get(rname, 0)
            take_turn[rname] = k + 1
            take = takes[k % len(takes)]
            rate = c.get('rate') or 1.0
            start = c['t'] + off / 1000.0 - float(take[f'{align}_s']) / rate
            out.append({'src': str((kdir / 'takes' / take['file']).resolve()), 't': round(max(0.0, start), 3),
                        'gain': K.gain_db(take, role, bed(c['t'])), 'role': rname, 'sound': c.get('sound') or rname,
                        'at': round(c['t'] + off / 1000.0, 3), 'event': c.get('event', c['t']), 'anchor': align, 'lead_ms': off, **({'rate': rate} if rate != 1.0 else {})})

    def use_bank(sid, t, dur, name):
        key = hashlib.sha1(f'{sid}|{dur}'.encode()).hexdigest()[:10]
        f = kdir / 'bank' / f"{sid.replace('/', '_')}_{key}.wav"
        if not f.exists():
            y, meta = BANK.render(sid, dur=dur)
            sf.write(str(f), y, meta['sr'])
        y, sr = sf.read(str(f))
        b = bed(t)
        gain = (b + K.over_bed(BANK_BED_DB) - K.loud_lufs(y, sr)) if b is not None else BANK_LEVEL_DB
        mono = np.abs(y if y.ndim == 1 else y.mean(axis=1))
        on = int(np.argmax(mono >= mono.max() * 0.1)) / sr if mono.size and mono.max() > 0 else 0.0   # 起音对准事件
        out.append({'src': str(f.resolve()), 't': round(max(0.0, t - on), 3), 'gain': round(min(gain, -1.0), 2), 'role': sid,
                    'sound': name, 'at': t, 'event': t, 'anchor': 'onset'})

    cfg = ROLES['web'] if style != 'variety' and req.get('tone') == 'web' else ROLES.get(style, ROLES['premium'])
    turn = {}
    i = 0
    while i < len(cues):
        c = cues[i]
        i += 1
        if c.get('sound'):                       # 对着内容的声音
            spec = sounds[c['sound']]
            if spec.get('bank'):
                use_bank(spec['bank'], c['t'], round(c['dur'], 2) if spec.get('span') and c.get('dur') else None, c['sound'])
            elif spec.get('role') in roles:
                if spec.get('span') and c.get('dur'):
                    n = max(1, int(c['dur'] / spec.get('every', 0.1)))
                    use_role(spec['role'], [{**c, 't': c['t'] + j * spec.get('every', 0.1)} for j in range(n)])
                else:
                    use_role(spec['role'], [c])
            continue
        run = [c]                                # 自动配：一串素材合成一组
        while i < len(cues) and not cues[i].get('sound') and cues[i]['kind'] == c['kind'] == 'broll' and cues[i]['t'] - run[-1]['t'] < RUN_GAP:
            run.append(cues[i])
            i += 1
        names = [r for r in cfg.get(c['kind'], []) if r in roles or r.startswith('bank:')]
        if not names:
            continue
        n = turn.get(c['kind'], 0)
        turn[c['kind']] = n + 1
        pick = names[n % len(names)]
        if pick.startswith('bank:'):
            for r in run:
                use_bank(pick[5:], r['t'], None, pick[5:].split('/')[0])
        else:
            use_role(pick, run)
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == '__main__':
    main()
