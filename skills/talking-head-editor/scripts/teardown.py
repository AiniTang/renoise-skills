"""拉片量化复盘（teardown_audit）：拿别人的成片或自己的成片，数包装点、算镜头占比、找配乐的换段和留白。

用法：
  python teardown.py 成片.mp4 [--timeline timeline.json] [--music 配乐分轨.wav] [-o 报告.json]
- 包装点：ffmpeg 场景检测（画面突变）当作「这里换了一次包装或镜头」，给时间表和平均间隔（参考：一条头部财经知识口播 5 分 25 秒 18 处，约 18 秒一处）。
- 镜头占比：给了 timeline 就按版式算口播全屏 / 画中画和整屏包装 / 气口留白的时长占比（信息卡片式口播参考 30% / 65% / 5%，超出 25%~35%、60%~70% 报一句）。
- 配乐：给了配乐分轨（render.py --stems 出的 music 轨）就每 0.5 秒算响度，找停顿和换段；没给就用成片整轨，结果只作参考。
  装了 demucs 时 --separate 会先把人声分离掉再听配乐。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kvlib import fullscreen_windows, load_json, probe   # noqa: E402


def scene_points(video, thr=0.3):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(video), '-vf', f"select='gt(scene,{thr})',showinfo", '-an', '-f', 'null', '-'],
                       capture_output=True, text=True)
    ts = [float(m) for m in re.findall(r'pts_time:([\d.]+)', r.stderr)]
    out = []
    for t in ts:   # 0.5 秒内连着的算一次
        if not out or t - out[-1] > 0.5:
            out.append(round(t, 2))
    return out


def loud_windows(audio, step=0.5):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(audio), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    n = int(16000 * step)
    rms = [float(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-9) for i in range(0, len(x) - n, n)]
    return [round(20 * np.log10(v), 1) for v in rms]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--timeline')
    ap.add_argument('--music')
    ap.add_argument('--separate', action='store_true')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    dur = probe(a.video)['duration']
    rep = {'duration': round(dur, 2)}
    pts = scene_points(a.video)
    rep['packaging_points'] = pts
    rep['avg_interval'] = round(dur / max(1, len(pts)), 1)
    print(f'包装点（画面突变）：{len(pts)} 处，平均 {rep["avg_interval"]} 秒一处')
    if a.timeline:
        tl = load_json(a.timeline)
        tl.setdefault('duration', dur)
        talk = sum(b - x for x, b in fullscreen_windows(tl))
        subs = sorted((s['t0'], s['t1']) for s in tl.get('subs', []))
        gaps = sum(max(0.0, b[0] - a_[1]) for a_, b in zip(subs, subs[1:]) if b[0] - a_[1] > 0.25)
        cover = max(0.0, dur - talk)
        rep['ratio'] = {'talk': round(talk / dur, 3), 'covered': round(cover / dur, 3), 'gaps': round(gaps / dur, 3)}
        r = rep['ratio']
        print(f"镜头占比：口播全屏 {r['talk']:.0%}，画中画和整屏包装 {r['covered']:.0%}，气口留白 {r['gaps']:.0%}")
        if not 0.25 <= r['talk'] <= 0.35 or not 0.6 <= r['covered'] <= 0.7:
            print('  和信息卡片式口播的参考比例（口播 25%~35%、画中画 60%~70%）不一样；大字报式和网感口播比例本来就不同，只作参考')
    music = a.music
    if a.separate and not music:
        try:
            out = Path(a.video).with_suffix('') / 'demucs'
            subprocess.run([sys.executable, '-m', 'demucs', '--two-stems', 'vocals', '-o', str(out), str(a.video)], check=True)
            music = next(out.rglob('no_vocals.wav'))
        except Exception as e:
            print(f'demucs 分离不了（{e}），改用成片整轨')
    lv = loud_windows(music or a.video)
    med = float(np.median(lv)) if lv else -30
    pauses = [round(i * 0.5, 1) for i, v in enumerate(lv) if v < med - 12]
    jumps = [round(i * 0.5, 1) for i in range(1, len(lv)) if abs(lv[i] - lv[i - 1]) > 8]
    rep['music'] = {'source': str(music or a.video), 'pauses': pauses, 'jumps': jumps}
    print(f"配乐{'分轨' if music else '（成片整轨，含人声）'}：明显停顿 {len(pauses)} 处，响度跳变（可能换段）{len(jumps)} 处")
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
        print('报告：', a.out)


if __name__ == '__main__':
    main()
