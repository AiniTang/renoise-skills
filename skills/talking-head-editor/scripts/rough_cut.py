"""粗剪：按 edl.json 保留的段落剪切、拼接口播，输出 aroll.mp4 和 lines.json。

edl.json 由你根据 transcript.json 写（留哪些岛、文字改成带标点的正确版本）：
{
  "canvas": {"w": 1080, "h": 1920, "fps": 30},
  "speed": 1.0,                 # 整体提速：真人 1.05~1.09（超过 1.1 听得出来），AI 配音写 "ai_voice": true 可到 1.2
  "breath": "premium_breath",   # 气口档：premium_breath 高级感留气口 / web_tight 网感紧剪（见 BREATH）
  "pad": [0.06, 0.12],          # 可选：每段前后各留多少秒，写了就不用气口档的值
  "clips": [
    {"src": "口播01.mov", "t0": 1.05, "t1": 9.33, "text": "Vibe coding 一年半以来，我踩了无数的坑。"},
    {"src": "口播02.mov", "t0": 2.05, "t1": 6.43, "text": "……", "para": true},   # 段落结尾：高级感档在这里多留一口气
    ...
  ]
}
t0/t1 用 transcript.json 里语音岛的时间；一个岛可以拆成多段，也可以只留其中一部分。edl 初稿可以用 auto_edl.py 从转写生成。
同一素材里前后相接的两段，余量在两段中间对半分，不会把同一段声音播两遍。
气口档除了句间留多少，还会把一句话中间超过一定长度的停顿收短（紧剪 0.15 秒以上收成 0.08 秒，留气口档 0.6 秒以上收成 0.35 秒），
口播在这里会跳一下，这正是网感紧剪「一句里也切」的样子。

输出：
  aroll.mp4    已裁成画布尺寸的口播（时间线上的 0 秒就是成片 0 秒）
  lines.json   [{"i", "text", "t0", "t1", "chars": [["字", 秒], ...]}]，时间都是新时间线上的
"""
import argparse
import difflib
import re
import subprocess
from pathlib import Path

# 气口两档（rough_cut_breath_trim）：pad 句首句尾余量；tighten 句中停顿超过多少秒收短到 keep 秒；para 段落结尾多留几秒
BREATH = {
    'web_tight': dict(pad=(0.03, 0.05), tighten=0.15, keep=0.08, para=0.0),       # 网感紧剪：句间只剩 0.05~0.1 秒
    'premium_breath': dict(pad=(0.08, 0.22), tighten=0.6, keep=0.35, para=1.0),   # 高级感：句间 0.2~0.4 秒气口，段落之间再留 1 秒
}

from kvlib import load_json, save_json, probe, canvas_for_source, canvas_size


def asr_chars(transcript, src, a, b):
    """取转写里落在 [a, b] 内的字和时间。"""
    src = str(Path(src).resolve())
    out = []
    for f in transcript.get('files', []):
        if f['src'] != src:
            continue
        for isl in f['islands']:
            for ch, t in isl['chars']:
                if a - 0.05 <= t <= b + 0.05 and re.match(r'[\w一-鿿]', ch):
                    out.append((ch.lower(), t))
    return out


def align(text, asr, t0, t1):
    """把（改过错字、加了标点的）正确文本对齐到识别出的逐字时间上，对不上的字线性插值。"""
    times = [None] * len(text)
    keys = [c.lower() for c in text]
    sm = difflib.SequenceMatcher(None, keys, [c for c, _ in asr], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('equal', 'replace') and j2 > j1:
            for k in range(i1, i2):
                j = j1 + min(int((k - i1) * (j2 - j1) / max(i2 - i1, 1)), j2 - j1 - 1)
                times[k] = asr[j][1]
    known = [(i, t) for i, t in enumerate(times) if t is not None]
    for i in range(len(times)):
        if times[i] is None:
            p = next(((j, t) for j, t in reversed(known) if j < i), (-1, t0))
            q = next(((j, t) for j, t in known if j > i), (len(times), t1))
            times[i] = p[1] + (q[1] - p[1]) * (i - p[0]) / max(q[0] - p[0], 1)
    # 保证单调递增
    for i in range(1, len(times)):
        times[i] = max(times[i], times[i - 1])
    return times


def pauses(src, a, b, min_len):
    """素材 [a, b] 里超过 min_len 秒的停顿 [(开始, 结束)]（-35 dB 以下算停）。"""
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', src, '-vn', '-af',
                          f'silencedetect=noise=-35dB:d={min_len}', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) + a for x in re.findall(r'silence_start: (-?[\d.]+)', err)]
    en = [float(x) + a for x in re.findall(r'silence_end: ([\d.]+)', err)]
    return [(x, y) for x, y in zip(st, en) if x > a + 0.05 and y < b - 0.05]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl')
    ap.add_argument('-t', '--transcript', default=None, help='transcript.json，用来给字幕对齐逐字时间')
    ap.add_argument('-o', '--outdir', default='.')
    ap.add_argument('--canvas', type=canvas_size, help='画布 WxH；优先于 edl 的 canvas，否则跟随源方向')
    ap.add_argument('--crf', type=int, default=14)
    a = ap.parse_args()

    edl = load_json(a.edl)
    tr = load_json(a.transcript) if a.transcript else {}
    for f in tr.get('files', []):
        f['src'] = str((Path(a.transcript).resolve().parent / f['src']).resolve())
    if not edl.get('clips'):
        ap.error('粗剪单没有保留片段')
    for c in edl['clips']:
        c['src'] = str((Path(a.edl).resolve().parent / c['src']).resolve())
    cv = edl.get('canvas')
    if a.canvas or not cv:
        cv = canvas_for_source(edl['clips'][0]['src'], a.canvas, (cv or {}).get('fps', 30))
    W, H, FPS = cv['w'], cv['h'], cv['fps']
    speed = float(edl.get('speed', 1.0))
    if speed > 1.1 and not edl.get('ai_voice'):
        print(f'提醒：真人口播提速超过 1.1 倍（现在 {speed}）听得出来，建议 1.05~1.09')
    br = BREATH.get(edl.get('breath', 'premium_breath'), BREATH['premium_breath'])
    pre, post = edl.get('pad', br['pad'])
    out = Path(a.outdir)
    cut = out / 'cut'
    cut.mkdir(parents=True, exist_ok=True)

    lines, listing, t, n_pieces = [], [], 0.0, 0
    clips = edl['clips']
    for n, c in enumerate(clips):
        src = c['src']
        dur_src = probe(src)['duration']
        s0, s1 = max(0.0, c['t0'] - pre), min(dur_src, c['t1'] + post)
        prv = clips[n - 1] if n else None
        nxt = clips[n + 1] if n + 1 < len(clips) else None
        if prv and prv['src'] == src and prv['t1'] <= c['t0'] < prv['t1'] + pre + post:
            s0 = max(s0, (prv['t1'] + c['t0']) / 2)
        if nxt and nxt['src'] == src and c['t1'] <= nxt['t0'] < c['t1'] + pre + post:
            s1 = min(s1, (c['t1'] + nxt['t0']) / 2)
        if c.get('para') and nxt:   # 段落结尾多留一口气（画面是人说完停住的样子）
            s1 = min(dur_src, s1 + br['para'])
        # 句中停顿收短：一个片段拆成几块
        keep = c.get('keep_pause', br['keep'])
        pieces, x = [], s0
        for p0, p1 in pauses(src, c['t0'], c['t1'], c.get('tighten', br['tighten'])):
            pieces.append((x, p0 + keep / 2))
            x = p1 - keep / 2
        pieces.append((x, s1))
        new_starts = []
        for k, (q0, q1) in enumerate(pieces):
            d_out = round((q1 - q0) / speed * FPS) / FPS          # 按帧取整，避免累计漂移
            if d_out <= 0:
                continue
            seg = cut / f'c{n:03d}_{k:02d}.mov'
            vf = f'scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps={FPS}'
            af = 'aresample=48000'
            if abs(speed - 1) > 1e-3:
                vf = f'setpts=PTS/{speed},' + vf
                af = f'atempo={speed},' + af
            af += f',afade=t=in:d=0.012,afade=t=out:st={max(0, d_out - 0.025):.3f}:d=0.025'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{q0:.3f}', '-i', src, '-t', f'{(q1 - q0):.4f}', '-vf', vf, '-af', af,
                            '-t', f'{d_out:.4f}', '-c:v', 'libx264', '-preset', 'fast', '-crf', str(a.crf), '-pix_fmt', 'yuv420p',
                            '-c:a', 'pcm_s16le', '-ac', '1', str(seg)], check=True)
            listing.append(f"file '{seg.name}'")
            new_starts.append((q0, q1, t))
            t += d_out
            n_pieces += 1

        def to_new(xx, ns=new_starts):
            for q0, q1, t_new in ns:
                if xx <= q1 + 1e-6:
                    return round(t_new + (max(xx, q0) - q0) / speed, 3)
            q0, q1, t_new = ns[-1]
            return round(t_new + (q1 - q0) / speed, 3)

        text = c.get('text', '')
        asr = asr_chars(tr, src, c['t0'], c['t1']) if tr else []
        times = align(text, asr, c['t0'], c['t1']) if text else []
        lines.append({'i': n, 'text': text, 't0': to_new(c['t0']), 't1': to_new(c['t1']), 'clip_start': new_starts[0][2],
                      'clip_end': round(t, 3), 'src': src, 'src_in': s0, 'para': bool(c.get('para')),
                      'cuts': [round(x[2], 3) for x in new_starts[1:]],   # 句中停顿收短留下的刀口，auto_zoom 在这里跳景别遮跳剪
                      'chars': [[ch, to_new(tt)] for ch, tt in zip(text, times)]})

    (cut / 'list.txt').write_text('\n'.join(listing) + '\n', encoding='utf-8')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(cut / 'list.txt'), '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '256k', str(out / 'aroll.mp4')], check=True)
    save_json(lines, out / 'lines.json')
    save_json(cv, out / 'canvas.json')
    gaps = sum(y - x for x, y in pauses(str(out / 'aroll.mp4'), 0, t, 0.15))   # 听得出来的停顿（0.15 秒以上）
    print(f'粗剪完成：{len(lines)} 句、{n_pieces} 刀，总长 {t:.2f} 秒，平均 {t / max(n_pieces, 1):.1f} 秒一刀，'
          f'停顿占 {gaps / max(t, 0.1):.0%} → {out / "aroll.mp4"}')


if __name__ == '__main__':
    main()
