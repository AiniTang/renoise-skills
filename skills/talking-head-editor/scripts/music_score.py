"""给候选配乐的「节奏感」打分排序：口播配乐要鼓点清楚、有推进力，又不能乱。

用法（librosa 较重，用 uv 临时装）：
  uv run --python 3.12 --with librosa python scripts/music_score.py bgm/候选/*.mp3 -o bgm/scores.json
每首输出：
  bpm        速度（自动把半速识别纠正到 70~160 之间）
  drums      鼓点能量占比（打击乐成分 / 整体），越高鼓越重
  pulse      节拍清晰度（拍点上的起音强度 / 平均起音强度），越高越好卡点
  density    每秒起音数，越高越密
  drums_in   鼓点真正进来的秒数（前奏太长的曲子从这里开始用）
  score      综合分 0~100：速度落在 100~130 加分，鼓重、拍清、密度适中加分
"""
import argparse
import json
from pathlib import Path
import sys

import librosa
import numpy as np

from audioload import load_audio
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")



def analyse(path):
    y, sr = load_audio(path, duration=120)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    while bpm < 70:
        bpm *= 2
    while bpm > 160:
        bpm /= 2
    harm, perc = librosa.effects.hpss(y)
    drums = float(np.sqrt(np.mean(perc ** 2)) / (np.sqrt(np.mean(y ** 2)) + 1e-9))
    pulse = float(onset[beats].mean() / (onset.mean() + 1e-9)) if len(beats) else 0.0
    n_on = len(librosa.onset.onset_detect(onset_envelope=onset, sr=sr))
    density = n_on / (len(y) / sr)
    # 鼓点进来：打击乐成分的 2 秒滑动能量第一次到达全曲中位数的 70%
    rms = librosa.feature.rms(y=perc, frame_length=2048, hop_length=512)[0]
    win = max(1, int(2 * sr / 512))
    smooth = np.convolve(rms, np.ones(win) / win, mode='same')
    idx = np.argmax(smooth >= 0.7 * np.median(smooth))
    drums_in = float(librosa.frames_to_time(idx, sr=sr, hop_length=512))
    return dict(file=str(path), bpm=round(bpm, 1), drums=round(drums, 3), pulse=round(pulse, 2), density=round(density, 2),
                drums_in=round(drums_in, 2))


def score(rows):
    def norm(key):
        v = np.array([r[key] for r in rows], dtype=float)
        lo, hi = v.min(), v.max()
        return (v - lo) / (hi - lo) if hi > lo else np.ones_like(v)
    d, p = norm('drums'), norm('pulse')
    for i, r in enumerate(rows):
        tempo = max(0.0, 1 - max(0.0, abs(r['bpm'] - 115) - 15) / 30)       # 100~130 满分，往外 30 拍降到 0
        dens = max(0.0, 1 - abs(r['density'] - 4.0) / 4.0)                  # 每秒 4 个起音左右最合适，太稀没劲、太密太乱
        r['score'] = round(100 * (0.35 * d[i] + 0.25 * p[i] + 0.2 * tempo + 0.2 * dens), 1)
    return sorted(rows, key=lambda r: -r['score'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()
    rows = score([analyse(f) for f in a.files])
    json.dump(rows, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in rows:
        print(f"{r['score']:5.1f}  {r['bpm']:6.1f} BPM  鼓 {r['drums']:.2f}  拍 {r['pulse']:.2f}  密 {r['density']:.1f}/s  鼓进 {r['drums_in']:4.1f}s  {Path(r['file']).name}")


if __name__ == '__main__':
    main()
