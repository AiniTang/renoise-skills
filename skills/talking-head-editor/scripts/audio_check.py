"""声音检查：看不了、也听不了成片时，用数字和一张图核对声音（sfx_event_engine 的检查图，EarShot 做法）。

用法：
  python render.py timeline.json -o out/final.mp4 --stems     # 渲染时另存人声、配乐、音效三条分轨
  python audio_check.py timeline.json out/final.mp4 [-o out/final.audio.png]

报告：
- 响度：成片、人声的整体响度和峰值（目标人声 -16 LUFS，峰值不超过 -1 dBFS）
- 配乐：说话时比人声低多少 dB（目标 18~22）、开头高一档有没有高出来、留白处是不是真停了
- 音效对齐：每个音效的起音（蓄力类是最响处）落在哪一帧，和该落的那一帧差几帧（目标 0，earshot 预设的提前量最多 2 帧）；
  在音效分轨里实测，渲染时偏了也查得出来
图：上面是成片频谱，下面三行是人声、配乐、音效的音量，红线 = 画面事件开始，绿色 = 实测音效起音，蓝线 = 段落分界。
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fonts import font
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SR = 16000
HOP = 0.01   # 10 毫秒一格


def pcm(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def env_db(x, win=HOP):
    n = int(SR * win)
    k = x.size // n
    r = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(r)


def loud(path):
    e = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', e)
    p = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', e)
    return (float(i[-1]) if i else None, float(p[-1]) if p else None)


def placements(tl_path):
    """和 render.py 同样的准备步骤后，算出每个音效放在哪（kvlib.all_sfx 是确定的，算两遍结果一样）。"""
    from audiomix import prepare
    from kvlib import all_sfx, expand_shots, load_json, style_preset, onset_peak
    from library import expand_beats
    cwd = os.getcwd()
    os.chdir(Path(tl_path).resolve().parent)
    try:
        tl = load_json(Path(tl_path).name)
        st = style_preset(tl)
        tl['titles'] = tl.get('titles', []) + expand_beats(tl, st)
        prepare(tl, st)
        expand_shots(tl, st)
        out = []
        for s in all_sfx(tl, st):
            if 'at' not in s:
                continue
            m = onset_peak(s['src'])
            r = s.get('rate') or 1.0
            out.append({**s, 'expect': s['t'] + m['peak' if s.get('anchor') == 'peak' else 'onset'] / r})
        return tl, out
    finally:
        os.chdir(cwd)


def measured_onset(sfx_env, t, anchor):
    """音效分轨里 t 附近（前后 0.15 秒）实际起音（或最响处）的时刻。"""
    i0, i1 = max(0, int((t - 0.15) / HOP)), min(len(sfx_env), int((t + 0.15) / HOP) + 1)
    seg = sfx_env[i0:i1]
    if seg.size == 0 or seg.max() < -60:
        return None
    if anchor == 'peak':
        return (i0 + int(seg.argmax())) * HOP
    # 起音：和 kvlib.onset_peak 同一口径，第一次响到这个声音峰值的十分之一（-20 dB）；峰值往后看 1 秒（尾巴长的声音最响处在后面）
    top = sfx_env[i0:min(len(sfx_env), int((t + 1.0) / HOP))].max()
    base = sfx_env[max(0, i0 - 10):i0 + 1].min() if i0 > 0 else -90
    above = np.nonzero(seg >= max(base + 6, top - 20))[0]
    return (i0 + int(above[0])) * HOP if above.size else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('timeline')
    ap.add_argument('video')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    v = Path(a.video)
    stems = {k: v.with_suffix(f'.{k}.wav') for k in ('voice', 'music', 'sfx')}
    stems = {k: p for k, p in stems.items() if p.exists()}   # 没有配乐或音效时那一轨不存在
    have = 'voice' in stems
    tl, pl = placements(a.timeline)
    fps = tl.get('canvas', {}).get('fps', 30)
    lines = []
    li, lp = loud(v)
    lines.append(f'成片 {li} LUFS，峰值 {lp} dBFS' + ('（峰值超过 -1）' if lp is not None and lp > -1 else ''))
    env = {}
    if have:
        for k, p in stems.items():
            env[k] = env_db(pcm(p))
        vi, vp = loud(stems['voice'])
        lines.append(f'人声 {vi} LUFS，峰值 {vp} dBFS')
        ve = env['voice']
        me = env.get('music', np.full(ve.size, -90.0))
        n = min(ve.size, me.size)
        sm = lambda x: np.convolve(x, np.ones(40) / 40, mode='same')   # 0.4 秒平滑
        vs, ms = sm(ve[:n]), sm(me[:n])
        talk = vs > -38
        quiet = (vs < -50)
        if 'music' in env and (ms > -70).any():
            d = np.median(vs[talk & (ms > -70)] - ms[talk & (ms > -70)]) if (talk & (ms > -70)).any() else None
            lines.append(f'说话时配乐比人声低 {d:.1f} dB（目标 18~22）' if d is not None else '说话时没有配乐')
            if quiet.any():
                lines.append(f'人声停顿处配乐 {np.median(ms[quiet & (ms > -70)]) if (quiet & (ms > -70)).any() else -90:.1f} dB')
            plan = tl.get('_music') or {}
            if plan.get('env'):
                o = plan['env'][0][1]
                io = int(o / HOP)
                lift = np.median(ms[:io][quiet[:io]]) - np.median(ms[io + 100:][quiet[io + 100:]]) if quiet[:io].any() and quiet[io + 100:].any() else None
                if lift is not None:
                    lines.append(f'开头 {o:.0f} 秒配乐比正文高 {lift:.1f} dB（只比人声停顿处）')
            gaps, i = [], 1
            while i < n:   # 配乐低于 -60 dB 持续 0.4 秒以上算真停下（留白、重音收住）
                if ms[i] < -60 <= ms[i - 1]:
                    j = i
                    while j < n and ms[j] < -60:
                        j += 1
                    if (j - i) * HOP >= 0.4:
                        gaps.append((i * HOP, (j - i) * HOP))
                    i = j
                i += 1
            if gaps:
                lines.append('配乐停下：' + '、'.join(f'{g:.1f} 秒起 {d:.1f} 秒' for g, d in gaps[:12]))
    # 音效对齐
    worst, rows = 0, []
    for s in pl:
        exp_f = round((s['expect'] - s['at']) * fps)
        alone = not any(o is not s and -0.6 < o['expect'] - s['expect'] < 0.3 for o in pl)   # 前后挨着别的音效时分轨里分不开，只看摆放
        real = measured_onset(env['sfx'], s['expect'], s.get('anchor')) if 'sfx' in env and alone else None
        real_f = round((real - s['at']) * fps) if real is not None else None
        lead = round(s.get('lead_ms', 0) / 1000 * fps)
        off = real_f if real_f is not None else exp_f   # at 里已经算进了预设的提前量
        worst = max(worst, abs(off))
        how = '在' if not lead else f"按预设{'提前' if lead < 0 else '延后'} {abs(lead)} 帧，在"
        rows.append(f"  {s['event']:6.2f} 秒 {s.get('sound', '?'):12s} {'最响处' if s.get('anchor') == 'peak' else '起音'}"
                    f"{how} {s['at']:.2f} 秒，摆放差 {exp_f} 帧"
                    + (f'，分轨实测差 {real_f} 帧' if real_f is not None else
                       ('，和旁边的音效叠在一起，分轨里分不开' if have and not alone else '，分轨里没测到（太轻）' if have else '')))
    lines.append(f'音效 {len(pl)} 个，对齐最大偏差 {worst} 帧（目标 0，超过 2 帧要查）')
    print('声音检查')
    for x in lines:
        print('  ·', x)
    print('\n'.join(rows))

    # 图
    out = Path(a.out) if a.out else v.with_suffix('.audio.png')
    x = pcm(v)
    dur = x.size / SR
    W, pps = 1800, None
    pps = W / dur
    nfft, hop = 1024, 160
    frames = (x.size - nfft) // hop
    if frames > 0:
        idx = np.arange(nfft)[None, :] + hop * np.arange(frames)[:, None]
        spec = np.abs(np.fft.rfft(x[idx] * np.hanning(nfft), axis=1)).T
        spec = 20 * np.log10(spec + 1e-6)
        fbins = np.geomspace(1, spec.shape[0] - 1, 260).astype(int)   # 对数频率
        sp = spec[fbins][::-1]
        sp = np.clip((sp - (sp.max() - 80)) / 80, 0, 1)
        img = Image.fromarray((sp * 255).astype(np.uint8)).resize((W, 300))
        spec_rgb = Image.merge('RGB', (img, img.point(lambda p: int(p * 0.75)), img.point(lambda p: int(p * 0.45))))
    else:
        spec_rgb = Image.new('RGB', (W, 300))
    rows_h = 90
    H = 300 + rows_h * 3 + 40
    im = Image.new('RGB', (W, H), (16, 16, 20))
    im.paste(spec_rgb, (0, 0))
    dr = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(font('SourceHanSansCN-Medium.otf')), 18)
    for k, key in enumerate(('voice', 'music', 'sfx')):
        y0 = 300 + k * rows_h
        dr.text((6, y0 + 4), {'voice': '人声', 'music': '配乐', 'sfx': '音效'}[key], font=font, fill=(200, 200, 200))
        if key in env:
            e = env[key]
            xs = (np.arange(e.size) * HOP * pps).astype(int)
            pts = [(int(px), int(y0 + rows_h - 4 - np.clip((val + 70) / 70, 0, 1) * (rows_h - 10))) for px, val in zip(xs[::2], e[::2])]
            dr.line(pts, fill={'voice': (120, 200, 255), 'music': (255, 200, 90), 'sfx': (140, 240, 140)}[key], width=1)
    for s in (tl.get('_music') or {}).get('sections', [])[1:]:
        X = int(s['t0'] * pps)
        dr.line([(X, 0), (X, H - 40)], fill=(80, 130, 255), width=2)
        dr.text((X + 4, 4), s.get('name', ''), font=font, fill=(150, 180, 255))
    for s in pl:
        X = int(s['event'] * pps)
        dr.line([(X, 300 + 2 * rows_h), (X, 300 + 3 * rows_h)], fill=(255, 70, 70), width=1)
        if 'sfx' in env:
            real = measured_onset(env['sfx'], s['expect'], s.get('anchor'))
            if real is not None:
                Xr = int(real * pps)
                dr.rectangle([Xr - 1, 300 + 2 * rows_h + 4, Xr + 1, 300 + 2 * rows_h + 24], fill=(60, 255, 120))
    for sec in range(0, int(dur) + 1):
        X = int(sec * pps)
        dr.line([(X, H - 40), (X, H - 30 if sec % 5 else H - 24)], fill=(160, 160, 160))
        if sec % 5 == 0:
            dr.text((X + 2, H - 24), f'{sec}s', font=font, fill=(160, 160, 160))
    im.save(out)
    print('检查图：', out)


if __name__ == '__main__':
    main()
