"""节奏检查：按头部知识口播成片量出来的数字检查一条片子会不会让人审美疲劳，列出不合格的时间点。

用法：
  python rhythm_check.py timeline.json                 渲染前查时间线
  python rhythm_check.py timeline.json --video out.mp4 渲染后再对成片做场景检测，量实际画面变化
输出一份大白话报告，同时写 rhythm_report.json（交付说明里引用平均变化间隔、最长静止）。

依据：拆解的口播成片统计（原片平均 2.4 秒一次画面变化、90% 的镜头不超过 4.8 秒、
口播全屏单段最长 8 秒、重包装约 15 秒一处、同一模板隔 30 秒以上、效果转场只在章节点），
开头 10 秒每 2 秒至少一次画面变化（实剪测试里开头画面不动，前 10 秒留不住人）。
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from library import expand_beats
import audiomix
import effects
import structure
from kvlib import CHAPTER_LAYOUTS, phrase_subs, SFX_DENSITY, auto_transitions, auto_zoom, expand_shots, fullscreen_windows, load_json, style_preset, sfx_cues, thin_cues

STILL_MAX = 4.0        # 任何 4 秒内至少一次画面变化
STILL_MAX_MOVING = 11  # 画面里有东西在动（播放中的录屏、缓推）时最长
OPEN_WIN, OPEN_GAP = 10, 2.0   # 开头 10 秒是留人的关键，每 2 秒内至少一次画面变化
MEAN_RANGE = (2.0, 3.2)
AROLL_MAX = {'premium': 8.0, 'variety': 5.0}
HEAVY_GAP = 40         # 最长 40 秒内必须有一处重包装
TEMPLATE_GAP = 30      # 同一种大字版式隔 30 秒以上


def visual_events(tl, st, base):
    """画面变化的时刻：[(秒, 是什么)]。"""
    ev = []
    for l in tl.get('layout', []):
        ev += [(l['t0'], f"版式切到{l['mode']}"), (l['t1'], '版式切回')]
        # 同一个版式里一张张出来的卡片、截图也是画面变化（at 是相对版式开始的秒数）
        at = l.get('at')
        ats = (at if isinstance(at, list) else []) + [s['at'] for s in l.get('stack', []) if isinstance(s, dict) and 'at' in s]
        ats += [l['at2']] if 'at2' in l else []
        ev += [(l['t0'] + x, '卡片进') for x in ats if x and x > 0.3]
    for b in tl.get('broll', []):
        ev += [(b['t0'], '素材进'), (b['t1'], '素材出')]
    for t in tl.get('titles', []):
        if t['t1'] - t['t0'] <= 6:
            ev += [(t['t0'], f"大字 {t.get('layout', '')}"), (t['t1'], '大字收')]
        for k in ('item_at', 'chunk_at', 'right_at', 'switch_at', 'hit_at', 'open_at', 'swap_at'):   # 大字里后出现的那几块
            v = t.get(k)
            ev += [(t['t0'] + x, '大字追加') for x in (v if isinstance(v, list) else [v]) if x is not None and x > 0.3]
    for o in tl.get('overlays', []):
        ev.append((o['t0'], '叠加物'))
    for d in tl.get('doodles', []):   # 手绘圈注、放射线这类贴纸
        ev.append((d['t0'], '手绘贴纸'))
    for z in tl.get('zoom', []) + auto_zoom(tl, st, base):
        ev += [(z['t0'], f"景别 {z.get('to', '')}"), (z['t1'], '景别回')]
    for tr in auto_transitions(tl, st):
        ev.append((tr['t'], f"转场 {tr.get('type', '')}"))
    for f in tl.get('fx', []):   # 整屏特效（第 8 批）：出现算一次变化，压暗框每移一次、窗口变形每一步也算
        ev.append((f['t0'], f"特效 {f['type']}"))
        if f['t1'] - f['t0'] <= 6:
            ev.append((f['t1'], '特效收'))
        ev += [(f['t0'] + b['at'], '聚光框移动') for b in (f.get('boxes') or [])[1:]]
    for l in tl.get('layout', []):
        if l['mode'] == 'morph':
            ev += [(l['t0'] + x, '窗口变形') for x in effects.morph_times(l)[1:]]
    f = Path(base) / 'lines.json'
    if f.exists():
        for ln in load_json(f):
            ev.append((ln.get('clip_start', 0), '粗剪接缝'))
    dur = tl.get('duration', 0) + tl.get('tail', 0)
    return sorted({(round(t, 2), w) for t, w in ev if 0 < t < dur - 0.05}), dur


def moving(tl, a, b):
    """a~b 这段画面里有没有在动的东西：播放中的视频素材、缓推的图片、带动画的大字。"""
    for x in tl.get('broll', []):
        if x['t0'] <= a + 0.1 and x['t1'] >= b - 0.1:
            return True
    return False


def scene_cuts(video):
    err = subprocess.run(['ffmpeg', '-hide_banner', '-i', video, '-an', '-vf', "scale=320:-2,select='gt(scene,0.25)',showinfo",
                          '-f', 'null', '-'], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r'pts_time:([\d.]+)', err)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('timeline')
    ap.add_argument('--video')
    a = ap.parse_args()
    path = Path(a.timeline).resolve()
    base = path.parent
    tl = load_json(path)
    st = style_preset(tl)
    tl['titles'] = tl.get('titles', []) + expand_beats(tl, st, base)
    structure.prepare(tl, st, base)
    phrase_subs(tl, base)
    audiomix.prepare(tl, st, base)
    expand_shots(tl, st)
    effects.prepare(tl, st)
    style = tl.get('style', 'premium')
    issues, notes = [], []

    ev, dur = visual_events(tl, st, base)
    merged = []
    for t in sorted({t for t, _ in ev}):   # 0.5 秒内的几个变化观众看来是一次
        if not merged or t - merged[-1] > 0.5:
            merged.append(t)
    times = [0.0] + merged + [dur]
    gaps = [(x, y) for x, y in zip(times, times[1:])]
    mean = dur / max(1, len(times) - 1)
    notes.append(f'画面变化 {len(times) - 2} 次，平均 {mean:.1f} 秒一次（目标 {MEAN_RANGE[0]}~{MEAN_RANGE[1]} 秒）')
    if mean > MEAN_RANGE[1] + 0.8:
        issues.append(f'平均 {mean:.1f} 秒才有一次画面变化，偏慢')
    elif mean < 1.3:
        notes.append(f'变化很密（平均 {mean:.1f} 秒），确认不乱：同一时刻只有一个视觉焦点')
    longest = max(gaps, key=lambda g: g[1] - g[0])
    notes.append(f'最长一段没变化：{longest[0]:.1f}~{longest[1]:.1f} 秒（{longest[1] - longest[0]:.1f} 秒）')
    for x, y in gaps:
        lim = STILL_MAX_MOVING if moving(tl, x, y) else STILL_MAX
        if y - x > lim:
            issues.append(f'{x:.1f}~{y:.1f} 秒 {y - x:.1f} 秒没有画面变化（上限 {lim} 秒）：加景别跳档、大字、素材或贴纸')

    for x, y in gaps:
        if x < OPEN_WIN and min(y, OPEN_WIN) - x > OPEN_GAP:
            issues.append(f'开头 {x:.1f}~{y:.1f} 秒 {y - x:.1f} 秒没有画面变化（开头 {OPEN_WIN} 秒内上限 {OPEN_GAP} 秒）：'
                          f'跟着口播的词加大字、换背景、素材或推近')

    for w0, w1 in fullscreen_windows(tl):
        if w1 - w0 > AROLL_MAX.get(style, 8):
            issues.append(f'{w0:.1f}~{w1:.1f} 秒口播全屏连续 {w1 - w0:.1f} 秒（上限 {AROLL_MAX.get(style, 8)} 秒）：插一段 B-roll 或换版式')

    heavy = sorted([t['t0'] for t in tl.get('titles', []) if t['t1'] - t['t0'] <= 6] +
                   [b['t0'] for b in tl.get('broll', [])])
    hv = [0.0] + heavy + [dur]
    for x, y in zip(hv, hv[1:]):
        if y - x > HEAVY_GAP:
            issues.append(f'{x:.1f}~{y:.1f} 秒 {y - x:.0f} 秒没有一处包装（上限 {HEAVY_GAP} 秒）')

    tts = [t for t in sorted(tl.get('titles', []), key=lambda t: t['t0']) if t['t1'] - t['t0'] <= 6]
    def look(t):   # 版式、左右、字体：大字报式字幕教程的规则是相邻两个大字至少换两个维度，这里三样全一样就算重复
        return (t.get('layout', st['title'].get('layout')), t.get('variant'), t.get('side', 'left'), t.get('font', 'title'))
    for p, q in zip(tts, tts[1:]):
        if look(p) == look(q) and look(p)[0] not in CHAPTER_LAYOUTS and q['t0'] - p['t0'] < TEMPLATE_GAP:
            issues.append(f"{p['t0']:.1f} 秒和 {q['t0']:.1f} 秒的大字长得一样（{look(p)[0]}、同一变体、同一侧、同字体，隔 {q['t0'] - p['t0']:.0f} 秒）："
                          f"换版式、换到另一侧或换字体")

    if tl.get('inserts'):
        notes.append(f"插入梗片段 {len(tl['inserts'])} 段：成片会比时间线长 {sum(float(x.get('dur', 1.2)) for x in tl['inserts']):.1f} 秒，"
                     "插入点后面的时间都要往后加")
    trs = sorted(auto_transitions(tl, st), key=lambda x: x['t'])
    for p, q in zip(trs, trs[1:]):
        if q['t'] - p['t'] < 30:
            issues.append(f"{p['t']:.1f} 秒和 {q['t']:.1f} 秒两个效果转场隔不到 30 秒")
        if p.get('type') == q.get('type'):
            issues.append(f"{p['t']:.1f} 秒和 {q['t']:.1f} 秒连用同一种转场 {p.get('type')}")

    # 开场第一秒必须有一个画面动作加一个音效（规律 opening_first_second）
    first = [x['t0'] for k in ('titles', 'broll', 'layout') for x in tl.get(k, []) if x['t0'] < 0.3]
    if not tl.get('_opening') and not first:
        issues.append('开场第一秒没有画面动作：写 opening（zoom / spotlight / flash / iris / boom），或第一秒就放大字、素材')
    # 同类包装全片用同一个模板只改内容（规律 same_role_same_template）
    for role, lays in (('章节页', CHAPTER_LAYOUTS), ('数据卡', ('statcard',))):
        looks = sorted({f"{t['layout']}·{t.get('variant', '')}" for t in tl.get('titles', []) if t.get('layout') in lays
                        and t.get('enter') != 'cover'})   # 白场接力放大出来的整屏页是同一个章节页的延续
        if len(looks) > 1:
            issues.append(f"{role}用了 {len(looks)} 种样子（{'、'.join(looks)}）：全片同一种{role}只换内容")

    per_min = SFX_DENSITY.get(tl.get('audio', {}).get('sfx_density')) or st.get('sfx_per_min', 12)
    cues = thin_cues(sfx_cues(tl, base, st), per_min, dur, base)
    n_sfx = len({c['g'] for c in cues})
    notes.append(f'音效 {n_sfx} 处，每分钟 {n_sfx * 60 / dur:.0f} 个（上限 {per_min}）')
    # 先按结构切段再包装（规律 script_segment_plan）：3 个章节以上或 3 分钟以上的口播要在 timeline 写 sections
    n_ch = sum(1 for t in tl.get('titles', []) if t.get('layout') in CHAPTER_LAYOUTS)
    if not tl.get('sections') and (n_ch >= 3 or dur >= 180):
        issues.append('3 段以上或 3 分钟以上的口播没写 sections：先按开场、第一点、第二点、结束语切段，写起止、段名、情绪（见 plan.md）')

    report = {'duration': round(dur, 2), 'events': len(times) - 2, 'mean_interval': round(mean, 2),
              'longest_still': [round(longest[0], 2), round(longest[1], 2)], 'sfx_per_min': round(n_sfx * 60 / dur, 1)}
    if a.video:
        cuts = scene_cuts(a.video)
        ct = [0.0] + cuts + [dur]
        cg = max(((x, y) for x, y in zip(ct, ct[1:])), key=lambda g: g[1] - g[0])
        notes.append(f'成片场景检测：硬变化 {len(cuts)} 次，平均 {dur / max(1, len(cuts)):.1f} 秒一次，最长 {cg[1] - cg[0]:.1f} 秒'
                     f'（{cg[0]:.1f}~{cg[1]:.1f}；景别跳档、字幕弹出这类小变化检测不到，超长段要对照上面的时间线结果）')
        report['scene_cuts'] = len(cuts)

    print('节奏检查')
    for n in notes:
        print('  ·', n)
    print(f'不合格 {len(issues)} 处' + ('：' if issues else '，可以渲染'))
    for i in issues:
        print('  ✗', i)
    report['issues'] = issues
    (base / 'rhythm_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
