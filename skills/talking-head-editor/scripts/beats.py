"""配乐节拍分析：找出每一拍和每小节第一拍（重拍）的时间，给卡点用。

用法（librosa 依赖较重，用 uv 临时装）：
  uv run --python 3.12 --with librosa python scripts/beats.py bgm/song.mp3 -o bgm/song.beats.json
输出：{"bpm": 92.3, "beats": [秒, ...], "downbeats": [秒, ...], "energy": [[秒, 0~1], ...]}
  downbeats 是每 4 拍的第一拍，按「重拍上能量最强」挑相位；energy 是每拍的响度，用来找鼓点进来、情绪推高的位置。
"""
import argparse
import json
import sys

import librosa
import numpy as np

from audioload import load_audio
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--meter', type=int, default=4, help='每小节几拍')
    a = ap.parse_args()

    y, sr = load_audio(a.audio)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, units='frames')
    bpm = float(np.atleast_1d(tempo)[0])
    if bpm > 160:   # 识别成了两倍速：隔一拍取一拍，取起音更强的那一组
        st2 = onset[np.clip(frames, 0, len(onset) - 1)]
        ph = 0 if st2[0::2].mean() >= st2[1::2].mean() else 1
        frames, bpm = frames[ph::2], bpm / 2
    beats = librosa.frames_to_time(frames, sr=sr)
    strength = onset[np.clip(frames, 0, len(onset) - 1)]
    # 重拍相位：哪一个相位上的拍子平均起音最强
    phase = max(range(a.meter), key=lambda p: strength[p::a.meter].mean() if len(strength[p::a.meter]) else 0)
    downbeats = beats[phase::a.meter]
    rms = librosa.feature.rms(y=y)[0]
    rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    e = np.interp(beats, rt, rms)
    e = e / (e.max() or 1)
    res = {'bpm': round(bpm, 1), 'duration': round(len(y) / sr, 3),
           'beats': [round(float(t), 3) for t in beats], 'downbeats': [round(float(t), 3) for t in downbeats],
           'energy': [[round(float(t), 3), round(float(v), 3)] for t, v in zip(beats, e)]}
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"BPM {res['bpm']}，{len(res['beats'])} 拍，{len(res['downbeats'])} 个重拍 → {a.out}")


if __name__ == '__main__':
    main()
