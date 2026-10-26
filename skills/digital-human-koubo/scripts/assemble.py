#!/usr/bin/env python3
"""逐段回听 → 剪掉段尾空白 → 统一规格 → 拼接。
用法：python3 assemble.py script.json clips.json [--out 成片_完整版.mp4] [--lang zh] [--size 宽x高（默认保持源尺寸）]
- script.json：[{"id","t",...}]（和 build_tasks.py 同一份）；clips.json：{"s1": "gen/xxx.mp4", ...}（段 id → 下载好的文件）
- 每段：faster-whisper 转写（中性提示，不用原文当提示，免得漏前半句）→ 和文稿比准确率 → 只保留到说完后 0.25 秒
- 输出 cut/<id>.mp4（30fps、48k 立体声）、cut/<id>.json（逐词时间，align.py 用）、cut/qa.json、拼接好的 --out（-16 LUFS）
- 准确率 < 85% 的段打 ⚠，先人工听；真念错就单独重拍那段
- 模型：WHISPER_MODEL 环境变量（默认 small，Renoise sandbox 里自带；medium 更准，第一次用会下载）"""
import json, subprocess, difflib, re, os, sys, wave
import numpy as np
from pathlib import Path
from faster_whisper import WhisperModel

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
a = sys.argv[1:]
if len(a) < 2: sys.exit(__doc__)
S = json.loads(Path(a[0]).read_text(encoding="utf-8")); CLIPS = json.loads(Path(a[1]).read_text(encoding="utf-8"))
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out_name, lang, size = opt('--out', '成片_完整版.mp4'), opt('--lang', 'zh'), opt('--size', '')
model = WhisperModel(os.environ.get('WHISPER_MODEL', 'small'), device='cpu', compute_type='int8')
clean = lambda s: re.sub(r'[\s，。、：；！？,.:;!?“”]', '', s).lower()
Path('cut').mkdir(exist_ok=True); rep = []
for s in S:
    sid = s['id']; src = CLIPS[sid]; wav = f'cut/{sid}.wav'
    lg = s.get('lang_code', lang)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-ar', '16000', '-ac', '1', wav], check=True)
    with wave.open(wav) as wf:     # 自己读 ffmpeg 出的 16k wav，不走 faster-whisper 的 PyAV 解码（版本常不兼容）
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
    segs, _ = model.transcribe(pcm, language=lg, initial_prompt='以下是普通话的句子。' if lg == 'zh' else None, word_timestamps=True)
    words = [dict(t=w.word, a=round(w.start, 3), b=round(w.end, 3)) for sg in segs for w in sg.words if w.word.strip()]
    Path(f'cut/{sid}.json').write_text(json.dumps(dict(words=words), ensure_ascii=False), encoding='utf-8')
    heard = ''.join(w['t'] for w in words).strip()
    st = words[0]['a'] if words else 0; en = words[-1]['b'] if words else 0
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
    w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.split(','))
    sz = size or f'{w - w % 2}x{h - h % 2}'          # 保持源尺寸（Grok 9:16 720p 是 720×1280，别拉成 720×1440）
    acc = difflib.SequenceMatcher(None, clean(s['t']), clean(heard)).ratio()
    keep = min(dur, en + 0.25)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', src, '-t', f'{keep:.3f}', '-vf', f'scale={sz.replace("x", ":")}:flags=lanczos,fps=30,format=yuv420p',
                    '-af', f'aresample=48000,afade=t=out:st={max(0, keep - 0.12):.3f}:d=0.12', '-ac', '2', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', f'cut/{sid}.mp4'], check=True)
    rep.append(dict(id=sid, acc=round(acc, 3), speech=[round(st, 2), round(en, 2)], keep=round(keep, 2), src_dur=round(dur, 2), heard=heard))
    print(f"{'⚠' if acc < 0.85 else ' '}{sid:5s} 准确率 {acc:.0%}  说话 {st:.2f}–{en:.2f}s  保留 {keep:.2f}/{dur:.2f}s  听到：{heard}")
Path('cut/qa.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
Path('cut/list.txt').write_text(''.join(f"file '{s['id']}.mp4'\n" for s in S), encoding='utf-8')
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'cut/list.txt', '-c', 'copy', 'cut/joined.mp4'], check=True)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', 'cut/joined.mp4', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out_name], check=True)
print('拼接完成', out_name, round(sum(r['keep'] for r in rep), 2), '秒')
