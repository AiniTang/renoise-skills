"""录屏变速（speed_adjust 的 screenrec_ramp）：录屏比它在时间线上的位置长时，等待、加载这类画面不动的段落先加速；
比位置短时整体放慢，让录屏和讲解一起结束。

broll 写 "speed": "auto" 时渲染自动调用；结果按素材和时长缓存在项目的 .cache/retime/。
- 等待段：连续 1 秒以上画面几乎不变（低清灰度帧差很小）。按正好塞进时长算倍率，最多 10 倍（一般 2~10 倍）；
- 等待段全加到 10 倍还长：其余部分一起提速，最多 1.5 倍（再快看不清操作），仍放不下就从结尾截掉并提醒；
- 录屏比位置短：整体放慢，最慢 0.36 倍，再不够就停在最后一帧。
加速 2 倍以上的段落右上角标「快进 ×N」（broll 写 "speed_badge": false 不标）。
"""
import hashlib
import os
import subprocess
from pathlib import Path

import numpy as np

from fonts import font

VERSION = 2
AW, AH, AFPS = 96, 170, 10   # 分析用的低清帧
STILL_DIFF = 1.2             # 帧差均值低于它算「画面没动」（0~255 灰度）
STILL_MIN = 1.0              # 连续多久算等待段
FAST = (2.0, 10.0)
REST_MAX = 1.5
SLOW_MIN = 0.36
FONT = font('SourceHanSansCN-Bold.otf')


def still_runs(src, t_in, length):
    """[(开始, 结束)]：素材 t_in 之后 length 秒里画面不动的段落（相对 t_in 的秒数）。"""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t_in:.3f}', '-t', f'{length:.3f}', '-i', str(src), '-vf',
                          f'fps={AFPS},scale={AW}:{AH},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8)
    n = fr.size // (AW * AH)
    if n < 2:
        return []
    fr = fr[:n * AW * AH].reshape(n, AH, AW).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    still = np.concatenate([[False], d < STILL_DIFF])
    runs, i = [], 0
    while i < n:
        if still[i]:
            j = i
            while j < n and still[j]:
                j += 1
            if (j - i) / AFPS >= STILL_MIN:
                runs.append(((i - 1) / AFPS + 0.2, j / AFPS - 0.2))   # 两头各留 0.2 秒原速，变速不突兀
            i = j
        else:
            i += 1
    return [(a, b) for a, b in runs if b - a > 0.5]


def plan(src, t_in, slot, length=None):
    """变速方案：[(素材开始, 素材结束, 倍率)] 和说明。"""
    from kvlib import probe
    total = probe(src)['duration'] - t_in
    length = min(length or total, total)
    if length <= slot + 0.05:   # 录屏比位置短：整体放慢
        k = max(SLOW_MIN, length / slot)
        return [(0.0, length, k)], f'放慢到 {k:.2f} 倍' + ('，最后停在最后一帧' if k == SLOW_MIN else '')
    runs = still_runs(src, t_in, length)
    wait = sum(b - a for a, b in runs)
    act = length - wait
    if runs and act < slot:
        k = min(FAST[1], max(1.0, wait / (slot - act)))   # 只差一点时等待段稍微快一点就够，不硬加到 2 倍再停在最后一帧
    else:
        k = FAST[1] if runs else 1.0
    out_len = act + wait / k
    r = min(REST_MAX, max(1.0, out_len / slot))
    segs, t = [], 0.0
    for a, b in runs:
        if a > t:
            segs.append((t, a, r))
        segs.append((a, b, k))
        t = b
    if t < length:
        segs.append((t, length, r))
    note = (f'{len(runs)} 段等待加速 {k:.1f} 倍' if runs else '没有等待段') + (f'，其余提速 {r:.2f} 倍' if r > 1.001 else '')
    if act / r + wait / k > slot + 0.1:
        note += f'，仍长 {act / r + wait / k - slot:.1f} 秒，结尾截掉'
    return segs, note


def retime(src, t_in, slot, fps, cache='.cache/retime', length=None, badge=True):
    """返回 (变速后的视频, 说明)。变速后的视频从 0 秒起、正好 slot 秒（不够长停最后一帧）。"""
    s = os.stat(src)
    key = hashlib.sha1(f'{Path(src).resolve()}|{s.st_size}|{int(s.st_mtime)}|{t_in:.3f}|{slot:.3f}|{length}|{fps}|{badge}|v{VERSION}'.encode()).hexdigest()[:16]
    out = Path(cache) / f'{key}.mp4'
    note_f = out.with_suffix('.txt')
    if out.exists() and note_f.exists():
        return str(out), note_f.read_text(encoding='utf-8')
    out.parent.mkdir(parents=True, exist_ok=True)
    segs, note = plan(src, t_in, slot, length)
    parts = []
    for i, (a, b, k) in enumerate(segs):
        p = out.with_name(f'{key}_{i}.mp4')
        vf = f'setpts=(PTS-STARTPTS)/{k},fps={fps}'
        if badge and k >= FAST[0]:   # 加速的那几段右上角标「快进 ×4」，观众知道是快进不是卡了
            vf += (f",drawtext=fontfile='{FONT}':text='快进 ×{k:.0f}':fontsize=h*0.032:fontcolor=white:x=w-tw-w*0.05:y=h*0.06:"
                   f"box=1:boxcolor=black@0.55:boxborderw=h*0.012")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t_in + a:.3f}', '-t', f'{b - a:.3f}', '-i', str(src), '-an', '-vf', vf,
                        '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', str(p)], check=True)
        parts.append(p)
    lst = out.with_suffix('.list')
    lst.write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-vf',
                    f'tpad=stop_mode=clone:stop_duration={slot:.3f},fps={fps}', '-t', f'{slot:.3f}', '-c:v', 'libx264', '-crf', '16',
                    '-preset', 'fast', '-pix_fmt', 'yuv420p', str(out)], check=True)
    for p in parts:
        p.unlink()
    lst.unlink()
    note_f.write_text(note, encoding='utf-8')
    return str(out), note
