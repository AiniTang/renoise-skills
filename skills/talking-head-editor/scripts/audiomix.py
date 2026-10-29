"""声音的整片规划（手法库第 5 批）：人声降噪统一响度、按段落排配乐、声音先入。render.py 和 build_draft.py 共用。

- clean_voice：原声一条链处理（高通 → 按实测底噪降噪 → 齿音 → 轻压缩 → 两遍法响度标准化），结果按素材缓存。
- music_plan：配乐按段落（timeline 的 sections，没写就按章节页）排：开头 13 秒高一档正文压低、段落换曲、
  换曲接缝（交叉淡化、嗖一声盖住、硬切、留白）、开场提气曲、重音收住再硬切。只给一首曲子时在同一首里跳段。
- auto_jcut：铺满画面的素材、章节页结束的地方，下一句人声先响 0.35 秒，画面再切回口播。
"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np

from kvlib import CHAPTER_LAYOUTS, expand_bgm, music_breaks, probe

HERE = Path(__file__).resolve().parent
VOICE_VERSION = 3


# ---------------------------------------------------------------- 人声（voice_cleanup_loudness）
def noise_floor(src):
    """素材底噪（dBFS）：50 毫秒一格的音量里最安静的 2%。粗剪后的口播停顿很少，取一成会量到轻声说话；
    无线麦收音一般在 -60 dB 上下，高于 -50 就是底噪明显。"""
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(src), '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    if x.size < 1600:
        return -60.0
    n = x.size // 800
    rms = np.sqrt((x[:n * 800].reshape(n, 800) ** 2).mean(axis=1) + 1e-12)
    return round(float(20 * np.log10(np.percentile(rms, 2))), 1)


def voice_chain(vo, nf):
    """原声处理链：高通去嗡声 → 降噪（强度按底噪）→ 去齿音 → 轻压缩让大小声更平。每一项都能在 audio.voice 里关掉。"""
    ch = [f"highpass=f={vo.get('highpass', 80)}"]
    if vo.get('denoise', True):
        nr = vo.get('nr', 14 if nf > -50 else 10 if nf > -60 else 6)
        ch.append(f'afftdn=nr={nr}:nf={max(-80, min(-25, round(nf)))}:tn=1')
    if vo.get('deess', True):
        ch.append('deesser=i=0.4:m=0.5:f=0.5:s=o')
    if vo.get('compress', True):
        ch.append('acompressor=threshold=0.063:ratio=3:attack=5:release=120:makeup=1.4')
    return ','.join(ch)


def clean_voice(src, lufs=-16, vo=None, cache='.cache'):
    """人声处理后的 wav（48k 双声道）和报告 {noise_floor, lufs, tp}。响度用两遍法：先量再按量到的值线性拉，不会忽大忽小。"""
    vo = vo or {}
    s = os.stat(src)
    key = hashlib.sha1(f'{Path(src).resolve()}|{s.st_size}|{int(s.st_mtime)}|{lufs}|{json.dumps(vo, sort_keys=True)}|v{VOICE_VERSION}'
                       .encode()).hexdigest()[:16]
    out, rep = Path(cache) / f'voice_{key}.wav', Path(cache) / f'voice_{key}.json'
    if out.exists() and rep.exists():
        return out, json.loads(rep.read_text(encoding='utf-8'))
    out.parent.mkdir(parents=True, exist_ok=True)
    nf = noise_floor(src)
    ch = voice_chain(vo, nf)
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(src), '-vn', '-af',
                          f'{ch},loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    m = json.loads(err[err.rindex('{'):err.rindex('}') + 1])
    ln = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vn', '-af', f'{ch},{ln},aresample=48000',
                    '-ac', '2', '-c:a', 'pcm_s16le', str(out)], check=True)
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(out), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
    tp = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', err)
    r = {'noise_floor': nf, 'lufs': float(i[-1]) if i else None, 'tp': float(tp[-1]) if tp else None, 'chain': ch}
    rep.write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
    return out, r


# ---------------------------------------------------------------- 段落（script_segment_plan）
MOODS = ('calm', 'dense', 'happy', 'hype')   # 舒缓、信息密快剪、欢快、提气


def sections_of(tl):
    """段落表 [{t0, t1, name, mood, seam}]：timeline 的 sections；没写就按章节页切（开场一段、每个章节页起一段）。"""
    end = (tl.get('duration') or 0) + tl.get('tail', 0)
    if tl.get('sections'):
        ss = sorted((dict(s) for s in tl['sections']), key=lambda s: s['t0'])
    else:
        ch = sorted(x['t0'] for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS)
        ss = [{'t0': 0.0, 'name': '开场'}] + [{'t0': t, 'name': f'第 {i + 1} 段', 'chapter': True} for i, t in enumerate(ch) if t > 1]
    for a, b in zip(ss, ss[1:] + [{'t0': end}]):
        a['t1'] = a.get('t1', b['t0'])
        a.setdefault('mood', density_mood(tl, a['t0'], a['t1']))
    return ss


def density_mood(tl, t0, t1):
    """没写情绪的段落按画面密度判：每 10 秒 3.5 个以上画面事件（素材、版式、大字出现）算信息密的快剪段。"""
    n = sum(1 for k in ('broll', 'layout', 'titles') for x in tl.get(k, []) if t0 <= x['t0'] < t1)
    return 'dense' if n * 10 / max(t1 - t0, 1) >= 3.5 else 'calm'


# ---------------------------------------------------------------- 配乐
def beats_of(src):
    from beat_sync import beats_for
    return beats_for(src)


def track_mood(tr):
    if tr.get('mood'):
        return tr['mood']
    return 'dense' if beats_of(tr['src']).get('bpm', 100) >= 108 else 'calm'


def voice_fx(src, fx, cache='.cache'):
    """人声变声段（voice_fx_swap）：timeline 的 voice_fx [{t0, t1, type}]，在处理好的人声上改这几秒。
    - megaphone 扩音器：只留 500~3000 Hz 再轻微失真，像念别人原话（画面自动叠 REC 录制边框）
    - bleep 哔声消音：原声静音，换成 1000 Hz 的哔（画面自动贴「消音」标签，写 label 可换字）
    结果按内容缓存。"""
    if not fx:
        return src
    key = hashlib.sha1((str(Path(src).resolve()) + json.dumps(fx, sort_keys=True)).encode()).hexdigest()[:10]
    out = Path(cache) / f'voice_fx_{key}.wav'
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    chain, beeps = [], []
    for x in fx:
        on = f"enable='between(t,{x['t0']:.3f},{x['t1']:.3f})'"
        if x['type'] == 'megaphone':
            chain += [f'highpass=f=500:{on}', f'lowpass=f=3000:{on}', f'acrusher=bits=10:mix=0.35:{on}', f'volume=1.5:{on}']
        elif x['type'] == 'bleep':
            chain.append(f'volume=0:{on}')
            beeps.append(x)
        else:
            raise SystemExit(f"voice_fx 的 type「{x['type']}」不认识，可选 megaphone、bleep")
    fc = f"[0:a]{','.join(chain) or 'anull'}[v]"
    ins = ['-i', str(src)]
    mixes = ['[v]']
    for j, x in enumerate(beeps):
        d = x['t1'] - x['t0']
        ins += ['-f', 'lavfi', '-i', f'sine=f=1000:d={d:.3f}:sample_rate=48000']
        fc += f";[{j + 1}:a]volume=0.25,afade=t=in:d=0.01,afade=t=out:st={max(0, d - 0.01):.3f}:d=0.01,adelay={int(x['t0'] * 1000)}:all=1[b{j}]"
        mixes.append(f'[b{j}]')
    if beeps:
        fc += f";{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0:duration=first[out]"
    else:
        fc = fc.replace('[v]', '[out]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', fc, '-map', '[out]', '-ar', '48000', str(out)], check=True)
    return out


def first_strong_downbeat(bt, after=0.0):
    """曲子里第一个有劲的重拍（能量到最响的一半），鼓点进来之前那段太空。"""
    energy = dict((round(t, 3), e) for t, e in bt.get('energy', []))
    downs = [d for d in bt.get('downbeats', []) if d >= after]
    return next((d for d in downs if energy.get(round(d, 3), 0) >= 0.5), downs[0] if downs else after)


def snap_down(bt, pos):
    """pos 之后最近的重拍。"""
    return next((d for d in bt.get('downbeats', []) if d >= pos - 0.05), pos)


SEAMS = ('xfade', 'whoosh', 'cut', 'gap', 'dip')
LEAD = 0.3     # 交叉淡化时后一首比画面切点早进来 0.3 秒（声音先入）


def music_plan(tl, st, base='.'):
    """返回 {'bgm': [配乐段], 'env': 音量包络, 'dips': [(开始, 结束, dB)], 'cues': 换曲处的音效, 'sections': 段落表}。
    配乐段 = {src, t0, t1, src_in, fade_in, fade_out, db, duck}，render 和 build_draft 按它铺。

    曲子从哪来：
    - audio.tracks：几首曲子 [{src, mood}]，按段落情绪分配（music_section_switch）；mood 不写按速度判（108 BPM 以上算快）
    - audio.bgm 只有一首：在同一首里按段落跳到能量高的另一段（原 expand_bgm）
    - audio.bgm 手写了几段：照写的铺，只加开头高一档、重音收住
    接缝（段落写 "seam" 指定，不写按情绪变化自动选）：
    - xfade 交叉淡化 0.4 秒，后一首比画面早 0.3 秒进来；whoosh 嗖一声盖住，前一首在嗖起来时 0.2 秒淡出，后一首在嗖最响处起播；
      cut 情绪突变直接换（段落写 "shout": true 再叠一声吆喝）；gap 前一首先停，留白 gap 秒（默认 0.8）再进；
      dip 同一首跳段时的老做法：章节前压低一下再跳
    开头高一档（music_bed_levels）：audio.bed {"open": 13, "lift": 5, "fade": 0.9}，写 false 关掉
    开场提气（open_boost）：audio.open_boost {"src": 提气曲, "len": 7}，开头 7 秒放提气曲，0.34 秒淡出接主曲
    重音收住（music_hit_stop_gap）：audio.stops [{"t": 数字放大那一帧, "gap": 1.0}]：一声重音鼓，鼓尾配乐收掉，空 gap 秒后硬切进下一段"""
    au = tl.get('audio', {})
    end = (tl.get('duration') or probe(tl['aroll'])['duration']) + tl.get('tail', 0)
    secs = sections_of({**tl, 'duration': end - tl.get('tail', 0)})
    cues, dips, env = [], [], []
    bed = au.get('bed', {}) if au.get('bed', True) is not False else None
    stops = sorted(au.get('stops', []), key=lambda s: s['t'])
    tracks = [dict(x) for x in au.get('tracks', [])]
    bgms = au.get('bgm', [])
    if not tracks and len(bgms) != 1:          # 手写的几段：照写的铺
        segs = [dict(m) for m in bgms]
        for s in stops:
            dips.append((s['t'] + 0.2, s['t'] + s.get('gap', 1.0), -60))
            cues.append({'t': s['t'], 'type': s.get('sound', 'hit')})
        return _finish(tl, st, segs, secs, cues, dips, env, bed, end, base)
    single = not tracks
    if single:
        m = bgms[0]
        tracks = [{'src': m['src'], 'mood': None, **{k: m[k] for k in ('db', 'lufs', 'duck') if k in m}}]
        legacy = expand_bgm(tl, base) if not stops and not au.get('open_boost') and not tl.get('sections') else None
        if legacy is not None:   # 只有一首、没写段落：沿用已验收的章节跳段（含章节前压低）
            segs = [dict(x) for x in legacy]
            dips += [(a, b, -16) for a, b in music_breaks(tl, st)]
            return _finish(tl, st, segs, secs, cues, dips, env, bed, end, base)
        t_start, t_end = m.get('t0', 0.0), min(m.get('t1', end), end)
    else:
        t_start, t_end = 0.0, end
    for tr in tracks:
        tr['bt'] = beats_of(tr['src'])
        tr['mood_'] = track_mood(tr) if not single else None

    # 切点：段落起点、重音收住后重新进来的点、开场提气结束
    bounds = []
    for s in secs[1:]:
        if t_start + 1 < s['t0'] < t_end - 1:
            bounds.append({'t': s['t0'], 'sec': s, 'seam': s.get('seam')})
    for s in stops:
        bounds = [b for b in bounds if not s['t'] - 0.5 < b['t'] < s['t'] + s.get('gap', 1.0) + 0.5]
        bounds.append({'t': s['t'] + s.get('gap', 1.0), 'sec': _sec_at(secs, s['t'] + s.get('gap', 1.0)), 'seam': 'stop', 'stop': s})
    ob = au.get('open_boost')
    if ob:
        ob = {} if ob is True else dict(ob)
        L = ob.get('len', 7.0)
        bounds = [b for b in bounds if b['t'] > L + 1]
        bounds.append({'t': L, 'sec': _sec_at(secs, L), 'seam': 'boost'})
    bounds.sort(key=lambda b: b['t'])

    used_at = {}     # 每首曲子上次放到哪
    segs, prev, prev_mood = [], None, None
    spans = [{'t': t_start, 'sec': _sec_at(secs, t_start), 'seam': None}] + bounds
    used_downs = []
    for k, b in enumerate(spans):
        t1 = spans[k + 1]['t'] if k + 1 < len(spans) else t_end
        restart = False
        if ob and k == 0:   # 开场提气曲
            tr = {'src': ob['src'], 'bt': beats_of(ob['src'])} if ob.get('src') else tracks[0]
            mood = 'hype'
        else:
            mood = b['sec'].get('mood', 'calm')
            # 换一首的时机：段落写了 seam；3 分钟以上的片子同一首连续放满 MAX_RUN 秒（防听感疲劳）；这一首放到这段结束就放完了
            run = b['t'] - prev['t0'] if prev else 0
            tired = end >= 180 and run >= MAX_RUN
            short = prev is not None and not single and prev['src_in'] + (t1 - prev['t0']) > _dur(tracks, prev['src']) - 1
            alt = [t for t in tracks if prev and t['src'] != prev['src'] and t['mood_'] == mood]
            restart = short and not alt and not b['seam'] and not tired   # 情绪对得上的只有这一首：从头一个有劲的重拍再起，不换到情绪不对的曲子
            tr = next(t for t in tracks if t['src'] == prev['src']) if restart else \
                _pick(tracks, mood, prev, single, force=bool(b['seam']) or tired or short)
        bt = tr['bt']
        same = prev is not None and prev['src'] == tr['src'] and not single and b['seam'] not in ('stop', 'boost') and not restart
        if same:   # 同一首接着放，不切
            prev['t1'] = t1
            used_at[prev['src']] = prev['src_in'] + (t1 - prev['t0'])
            continue
        if single and any(x['src'] == tr['src'] for x in segs):   # 同一首里跳到能量高、没用过的一段
            src_in = _jump(bt, used_downs, t1 - b['t'])
        elif single and not (ob and k == 0):
            src_in = bgms[0].get('src_in', first_strong_downbeat(bt))
        elif restart:   # 同一首从头再起
            src_in = first_strong_downbeat(bt)
        elif tr['src'] in used_at:   # 再放到用过的曲子从上次停的地方接着；剩下的不够这一段用就从头一个有劲的重拍起
            src_in = snap_down(bt, used_at[tr['src']])
            if src_in + (t1 - b['t']) > bt['duration'] - 1:
                src_in = first_strong_downbeat(bt)
        elif ob and k == 0:
            src_in = max((d for d in bt.get('downbeats', []) if d + (t1 - b['t']) <= bt['duration']),
                         key=lambda d: _energy(bt, d), default=0.0) if not ob.get('src') else first_strong_downbeat(bt)
        else:
            src_in = first_strong_downbeat(bt)
        used_downs.append(src_in)
        seam = b['seam'] or (_auto_seam(prev_mood, mood) if prev else None)
        seg = {'src': tr['src'], 't0': b['t'], 't1': t1, 'src_in': round(src_in, 3),
               'fade_in': (bgms[0].get('fade_in', 0.5) if single else 0.5) if not prev else 0.02,
               'fade_out': 1.0, **{k_: tr[k_] for k_ in ('db', 'lufs', 'duck') if k_ in tr}}
        if ob and k == 0:
            seg['db'] = ob.get('db', seg.get('db', 0))
        if prev:
            _seam(seam, prev, seg, b, cues, dips)
        segs.append(seg)
        used_at[tr['src']] = src_in + (t1 - b['t'])
        prev, prev_mood = seg, mood
    # 写明要停的几处（定格暂停、段落收尾章节页那一下、梗句短乐句）分段换曲时也要停：配乐静音（前后 0.08 秒淡变）
    dips += [(fz['t0'], fz['t1'], -60) for fz in tl.get('freezes', [])] + [(a, b, -60) for a, b in tl.get('_breaks', [])]
    return _finish(tl, st, segs, secs, cues, dips, env, bed, end, base)


def _energy(bt, d):
    return dict((round(t, 3), e) for t, e in bt.get('energy', [])).get(round(d, 3), 0)


def _jump(bt, used, need):
    cands = [d for d in bt.get('downbeats', []) if d + min(need, 20) <= bt['duration'] and all(abs(d - u) > 8 for u in used)]
    return max(cands, key=lambda d: (_energy(bt, d), -d)) if cands else (used[-1] if used else 0.0)


def _sec_at(secs, t):
    return next((s for s in reversed(secs) if s['t0'] <= t + 1e-6), secs[0])


MAX_RUN = 75   # 长片子里同一首最多连着放多久（秒），到了下一个段落就换一首


def _dur(tracks, src):
    return next((t['bt']['duration'] for t in tracks if t['src'] == src and t.get('bt')), 1e9)


def _pick(tracks, mood, prev, single, force=False):
    """按情绪挑曲子：情绪对上的优先，和上一段同一首就接着放；force 时换一首（同样对得上时不重复上一首）。"""
    if single:
        return tracks[0]
    ok = [t for t in tracks if t['mood_'] == mood] or [t for t in tracks if {t['mood_'], mood} <= {'dense', 'hype'}] or tracks
    if prev and force:
        ok = [t for t in ok if t['src'] != prev['src']] or [t for t in tracks if t['src'] != prev['src']] or ok
    return ok[0]


def _auto_seam(a, b):
    if a == b:
        return 'xfade'
    if b in ('dense', 'hype', 'happy'):
        return 'whoosh'
    return 'gap'


def _seam(seam, a, b, bd, cues, dips):
    """在 a、b 两段配乐的接缝处按接缝方式改起止和淡入淡出，需要的音效放进 cues。"""
    t = bd['t']
    if seam == 'boost':                # 开场提气曲 0.34 秒淡出，主曲 0.33 秒淡入
        a['t1'], a['fade_out'] = t, 0.34
        b['t0'], b['fade_in'] = t - 0.34, 0.33
    elif seam == 'xfade':              # 交叉淡化，后一首早 0.3 秒进来（声音先入）
        b['t0'], b['fade_in'] = t - LEAD, 0.4
        a['t1'], a['fade_out'] = t - LEAD + 0.4, 0.4
    elif seam == 'whoosh':             # 嗖一声盖住接缝：嗖起来时前一首 0.2 秒淡出，后一首在嗖最响处起播
        cues.append({'t': round(t - 0.2, 3), 'type': 'whoosh', 'prio': 0})
        a['t1'], a['fade_out'] = t, 0.2
        b['fade_in'] = 0.02
    elif seam == 'cut':                # 情绪突变：画面切的那一帧直接换
        a['t1'], a['fade_out'] = t, 0.03
        b['fade_in'] = 0.02
        if bd['sec'].get('shout'):
            cues.append({'t': t, 'type': 'cheer_shout', 'prio': 0})
    elif seam == 'gap':                # 留白：前一首先停，空一会儿再进
        g = bd['sec'].get('gap', 0.8)
        a['t1'], a['fade_out'] = t - g + 0.2, 0.2
        b['fade_in'] = 0.02
    elif seam == 'stop':               # 重音收住：鼓一响配乐跟着收，空一秒硬切
        s = bd['stop']
        cues.append({'t': s['t'], 'type': s.get('sound', 'hit'), 'prio': 0})
        a['t1'], a['fade_out'] = s['t'] + 0.4, 0.2
        b['fade_in'] = 0.02
    else:                              # dip：同一首跳段的老做法
        a['t1'], a['fade_out'] = t, 0.12
        b['fade_in'] = 0.05
        dips.append((t - 0.7, t, -16))


def _bar(bt):
    d = bt.get('downbeats') or []
    return float(np.median(np.diff(d))) if len(d) > 2 else 240.0 / max(60.0, bt.get('bpm', 120))


def _window_energy(bt, d0, d1):
    e = [x for t, x in bt.get('energy', []) if d0 <= t < d1]
    return (float(np.mean(e)), float(np.std(e))) if e else (0.0, 1.0)


def climax_splice(segs, secs, end):
    """截高潮段接尾音（music_climax_splice）：段落写了 "climax": true（或秒数），这一段最后几小节换成同一首里最有劲的 4 小节，
    切点落在重拍上（同一首同速，听不出接缝），推到段落结束，后面的留白、换曲照常。"""
    out = list(segs)
    for k, sec in enumerate(secs):
        want = sec.get('climax')
        if not want:
            continue
        s_end = secs[k + 1]['t0'] if k + 1 < len(secs) else end
        seg = next((x for x in out if x['t0'] < s_end - 1 <= x['t1']), None)
        if seg is None:
            continue
        bt = beats_of(seg['src'])
        bar = _bar(bt)
        L = float(want) if not isinstance(want, bool) else min(10.0, max(6.0, 4 * bar))
        downs = [d for d in bt.get('downbeats', []) if d + L <= bt['duration'] - 0.5]
        if not downs:
            continue
        hot = max(downs, key=lambda d: _window_energy(bt, d, d + L)[0])
        film_downs = [seg['t0'] + d - seg['src_in'] for d in bt.get('downbeats', [])]   # 这一段里重拍落在成片的哪些时刻
        cut = min((t for t in film_downs if seg['t0'] + 2 < t < s_end - 2), key=lambda t: abs(t - (s_end - L)), default=None)
        if cut is None:
            continue
        hi = {**seg, 't0': round(cut, 3), 't1': round(min(s_end, seg['t1']), 3), 'src_in': round(hot, 3), 'fade_in': 0.01, 'climax': True}
        rest = None
        if seg['t1'] > s_end + 0.5:   # 同一首在下一段接着放：高潮推完回到原来的位置接着放
            rest = {**seg, 't0': round(s_end, 3), 'src_in': round(seg['src_in'] + (s_end - seg['t0']), 3), 'fade_in': 0.3}
            hi['fade_out'] = 0.3
        seg['t1'], seg['fade_out'] = round(cut, 3), 0.01
        i = out.index(seg)
        out[i + 1:i + 1] = [hi] + ([rest] if rest else [])
    return out


def beat_loop(segs, tracks):
    """节奏段无缝循环（music_beat_loop）：audio.tracks 里写了 "loop": true（或 {"bars": 4}）的曲子，挑一段能量平稳的整数小节，
    首尾按重拍对齐反复接，铺满它负责的时段；接缝 10 毫秒交叉淡化。用在大段画中画讲解，免得一首曲子放完要换。"""
    loops = {t['src']: (t['loop'] if isinstance(t['loop'], dict) else {}) for t in tracks if t.get('loop')}
    if not loops:
        return segs
    out = []
    for seg in segs:
        if seg['src'] not in loops:
            out.append(seg)
            continue
        bt = beats_of(seg['src'])
        bar = _bar(bt)
        n = loops[seg['src']].get('bars', 4 if bar * 4 >= 8 else 8)
        L = n * bar
        downs = [d for d in bt.get('downbeats', []) if d + L <= bt['duration'] - 0.5 and d >= seg['src_in']] or \
            [d for d in bt.get('downbeats', []) if d + L <= bt['duration'] - 0.5]
        if not downs:
            out.append(seg)
            continue
        mid = np.median([x for _, x in bt.get('energy', [])] or [0])
        d0 = min(downs[:12], key=lambda d: (lambda m, sd: abs(m - mid) + sd)(*_window_energy(bt, d, d + L)))
        t, first = seg['t0'], True
        while t < seg['t1'] - 0.05:
            piece = min(L, seg['t1'] - t)
            out.append({**seg, 't0': round(t, 3), 't1': round(t + piece, 3), 'src_in': round(d0, 3),
                        'fade_in': seg['fade_in'] if first else 0.01, 'fade_out': seg['fade_out'] if t + piece >= seg['t1'] - 0.05 else 0.01})
            t += piece
            first = False
    return out


def _finish(tl, st, segs, secs, cues, dips, env, bed, end, base):
    segs = beat_loop(segs, tl.get('audio', {}).get('tracks', []))
    segs = climax_splice(segs, secs, end)
    if bed is not None and segs:      # 开头高一档、正文压低，0.9 秒过渡（music_bed_levels）
        o, lift, f = bed.get('open', 13.0), bed.get('lift', 5.0), bed.get('fade', 0.9)
        o = min(o, max(3.0, end - 3))
        env = [(0.0, o, lift, lift), (o, o + f, lift, 0.0)]
    segs = [s for s in segs if s['t1'] - s['t0'] > 0.05]
    return {'bgm': segs, 'env': env, 'dips': dips, 'cues': cues, 'sections': secs}


def env_expr(m, plan, heavy=()):
    """这一段配乐的音量表达式（这段自己的时间轴）：开头高一档、留白和重音前压低。heavy 是重音音效的时刻，配乐在它前 0.2 秒压低 6 dB。"""
    T = f"(t+{m['t0']:.3f})"
    terms = []
    for a, b, g0, g1 in plan['env']:
        if b <= m['t0'] or a >= m['t1']:
            continue
        g = f"({g0}+({g1 - g0})*clip(({T}-{a:.3f})/{max(b - a, 1e-3):.3f},0,1))" if g0 != g1 else f"{g0}"
        terms.append(f"if(between({T},{a:.3f},{b:.3f}),pow(10,{g}/20),1)")
    dips = list(plan['dips']) + [(h - 0.2, h + 0.45, -6) for h in heavy]
    for a, b, db in dips:
        if b <= m['t0'] or a >= m['t1']:
            continue
        k = 1 - 10 ** (db / 20)
        terms.append(f"(1-{k:.4f}*clip(min(({T}-{a:.3f})/0.08,({b:.3f}-{T})/0.08),0,1))")
    return f",volume='{'*'.join(terms)}':eval=frame" if terms else ''


# ---------------------------------------------------------------- 声音先入（jcut_audio_lead）
def voice_starts(tl, base='.'):
    """口播里每句开口的时刻（前面停了 0.15 秒以上才算）：按 lines.json 的逐字时间；没有就对口播做静音检测。"""
    f = Path(base) / 'lines.json'
    if f.exists():
        ls = json.loads(f.read_text(encoding='utf-8'))
        out, last = [], -9.0
        for ln in ls:
            t0 = ln['chars'][0][1] if ln.get('chars') else ln['t0']
            if t0 - last >= 0.15:
                out.append(t0)
            last = ln['t1']   # 这一句说完的时刻（转写语音岛的结尾）
        return out
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(Path(base) / tl['aroll']), '-vn', '-af',
                          'silencedetect=noise=-35dB:d=0.2', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]


def auto_jcut(tl, base='.'):
    """铺满画面的素材、遮住人的版式、章节页在下一句开口前后 0.8 秒内结束时，把它延长到开口后 lead 秒（默认 0.35）：
    观众先听到下一句，画面再切回口播，段落衔接更顺。画面盖住了嘴，所以不会对不上口型。
    timeline 写 "jcut": false 关掉，写数字改提前量（0.3~1，超过 1 秒观众会困惑）。直接改内存里的 timeline。"""
    lead = tl.get('jcut', 0.35)
    if lead is False:
        return []
    fps = tl.get('canvas', {}).get('fps', 30)
    starts = voice_starts(tl, base)
    covers = [b for b in tl.get('broll', []) if b.get('fit', 'cover') == 'cover'] + \
        [l for l in tl.get('layout', []) if l.get('mode') == 'hidden'] + \
        [t for t in tl.get('titles', []) if t.get('layout') in CHAPTER_LAYOUTS]
    starts_all = sorted(x['t0'] for k in ('broll', 'layout', 'titles') for x in tl.get(k, []))
    done = []
    for it in covers:
        e = it['t1']
        v = next((s for s in starts if e - 0.8 <= s <= e + 0.25), None)
        if v is None:
            continue
        new = round((v + lead) * fps) / fps
        nxt = min((s for s in starts_all if s > e - 1e-3), default=1e9)
        if new <= e + 1e-3 or new > nxt - 0.05 or new > tl.get('duration', 1e9):
            continue
        it['t1'] = new
        done.append((round(v, 3), round(new, 3)))
    return done


def prepare(tl, st, base='.'):
    """渲染前跑一次：声音先入改画面结束点、排好配乐（放进 tl['_music']），换曲处的音效并进 sounds。"""
    if tl.get('_audio_ready'):
        return tl
    tl['_audio_ready'] = True
    tl['_jcut'] = auto_jcut(tl, base)
    if tl.get('audio', {}).get('bgm') or tl.get('audio', {}).get('tracks'):
        plan = music_plan(tl, st, base)
        tl['_music'] = plan
        tl['_bgm'] = plan['bgm']
        tl['sounds'] = list(tl.get('sounds', [])) + plan['cues']
    return tl
