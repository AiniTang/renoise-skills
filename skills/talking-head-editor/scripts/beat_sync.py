"""画面卡点：让 B-roll、版式切换、大字、推近、音效落在配乐的节拍上。

用法：python beat_sync.py timeline.json [--tol 0.25] [--anchor 8.18] [--dry]
前提：timeline 的 audio.bgm 已经写好，第一首配乐旁边有节拍文件（同名 .beats.json，没有就自动调 beats.py 生成）。

做两件事：
1. 选配乐的起点 src_in：把一个重拍对准 anchor（默认是第一个章节或第一处 B-roll 的开始，也就是开场钩子结束、正片进来的那一刻），
   在所有可选的重拍里挑「卡上节拍的画面事件最多」的那个。timeline 里已经手写了 src_in 的配乐不动。
2. 吸附：每个画面事件的开始时间，离最近的拍子不超过 tol 秒就挪到拍子上；离重拍更近时优先重拍。
   同一时刻的多个事件（比如 B-roll 和版式同时切换）一起挪，挪完前后关系不变。字幕跟着说话走，不动。
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from kvlib import CHAPTER_LAYOUTS, load_json, save_json

HERE = Path(__file__).resolve().parent


def beats_for(src):
    bj = Path(src).with_suffix('.beats.json')
    if not bj.exists():
        subprocess.run(['uv', 'run', '--quiet', '--python', '3.12', '--with', 'librosa', 'python', str(HERE / 'beats.py'), str(src),
                        '-o', str(bj)], check=True)
    return json.loads(bj.read_text(encoding='utf-8'))


def event_refs(tl):
    """所有可以挪的画面事件：(列表名, 下标, 字段)。"""
    refs = []
    for name, fields in (('broll', ('t0', 't1')), ('layout', ('t0', 't1')), ('titles', ('t0',)), ('zoom', ('t0',)),
                         ('overlays', ('t0',))):
        for i, _ in enumerate(tl.get(name, [])):
            refs += [(name, i, f) for f in fields]
    for i, _ in enumerate(tl.get('audio', {}).get('sfx', [])):
        refs.append(('sfx', i, 't'))
    return refs


def get_list(tl, name):
    return tl['audio']['sfx'] if name == 'sfx' else tl[name]


def nearest(t, grid):
    return min(grid, key=lambda g: abs(g - t)) if grid else t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('timeline')
    ap.add_argument('--tol', type=float, default=0.25, help='最多挪多少秒')
    ap.add_argument('--anchor', type=float, help='让重拍落在这个时间（秒）')
    ap.add_argument('--dry', action='store_true', help='只报告不改')
    a = ap.parse_args()

    path = Path(a.timeline)
    tl = load_json(path)
    base = path.parent
    bgms = tl.get('audio', {}).get('bgm', [])
    if not bgms:
        sys.exit('timeline 里没有配乐（audio.bgm），先选好配乐再卡点')
    m = bgms[0]
    bt = beats_for(base / m['src'])
    refs = event_refs(tl)
    times = sorted({round(get_list(tl, n)[i][f], 3) for n, i, f in refs if get_list(tl, n)[i][f] > m['t0'] + 0.3})

    def grid(src_in):
        to_tl = lambda b: m['t0'] + b - src_in
        return ([to_tl(b) for b in bt['beats'] if m['t0'] <= to_tl(b) <= m['t1']],
                [to_tl(b) for b in bt['downbeats'] if m['t0'] <= to_tl(b) <= m['t1']])

    def score(src_in):
        beats, downs = grid(src_in)
        return sum(1 for t in times if beats and abs(nearest(t, beats) - t) <= a.tol) + \
            sum(0.5 for t in times if downs and abs(nearest(t, downs) - t) <= a.tol)

    if 'src_in' not in m:
        anchor = a.anchor
        if anchor is None:
            firsts = [x['t0'] for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS] or [x['t0'] for x in tl.get('broll', [])]
            anchor = min(firsts) if firsts else m['t0']
        span = m['t1'] - m['t0']
        cands = [d - (anchor - m['t0']) for d in bt['downbeats']]
        cands = [c for c in cands if c >= 0 and c + span <= bt['duration'] + 0.01] or [0.0]
        m['src_in'] = round(max(cands, key=score), 3)
    beats, downs = grid(m['src_in'])

    moved = {}
    for t in times:
        d = nearest(t, downs) if downs else t
        b = nearest(t, beats) if beats else t
        tgt = d if abs(d - t) <= a.tol and abs(d - t) <= abs(b - t) + 0.08 else b
        if abs(tgt - t) <= a.tol and abs(tgt - t) > 0.01:
            moved[t] = round(tgt, 3)
    for n, i, f in refs:
        it = get_list(tl, n)[i]
        it[f] = moved.get(round(it[f], 3), it[f])
    for n in ('broll', 'layout'):
        for it in tl.get(n, []):
            if it['t1'] - it['t0'] < 0.3:
                it['t1'] = round(it['t0'] + 0.3, 3)

    hit = sum(1 for t in times if beats and abs(nearest(moved.get(t, t), beats) - moved.get(t, t)) <= 0.02)
    print(f"配乐 {Path(m['src']).name}：{bt['bpm']} BPM，起点 src_in={m['src_in']} 秒")
    print(f"画面事件 {len(times)} 个，挪动 {len(moved)} 个，卡在拍上 {hit} 个")
    for t, v in list(moved.items())[:30]:
        print(f'  {t:7.2f} → {v:7.2f}')
    if not a.dry:
        shutil.copy(path, path.with_suffix('.before_sync.json'))
        save_json(tl, path)


if __name__ == '__main__':
    main()
