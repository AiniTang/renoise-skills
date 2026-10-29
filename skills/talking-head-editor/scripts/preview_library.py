"""手法库样本册：把已实现手法的每个变体放在同一段口播上各渲一小段，拼成一条样片和一张缩略图墙，
用来看效果、也用来查改代码有没有改坏。

用法：
  python preview_library.py --aroll 口播.mp4 [--start 10] -o 样本册.mp4 [--only flank_pair,list_accumulate] [--style premium --tone web]
  横屏：python preview_library.py --aroll 横屏口播.mp4 --canvas 1920x1080 -o 横屏样本册.mp4
  --canvas 不给就按口播方向选 1080P。
  --aroll 用一段人居中、正在说话的口播（至少 4 秒），--start 从第几秒开始截；每段样片 3.6 秒，左上角印「手法名 · 变体」。
  另外渲字幕样子、强调词样子、字体基调这几个全片一次选定的手法（--globals 0 不渲）。
  画面与镜头类手法（library.FIELDS）用 --assets 目录里的 screenshot.png、photo.jpg、screen_recording.mov 当素材，
  默认是口播文件旁边的 assets/。声音与粗剪类还要：music/main.mp3 主配乐和 Curiosity、Beating_Break、Non_Stop 三首演示曲
  （同名 .beats.json 没有会自动生成），raw_koubo.mov 没粗剪过的口播，rough/web、rough/premium 两档粗剪结果（auto_edl + rough_cut 生成），
  rec_wait.mov 带等待段的竖屏录屏；口播文件旁边的同名 .lines.json 是它的逐字时间，也可用 --lines 指定（声音先入要用）。
  插入影视梗片段用 meme_demo.mp4（横版占位片段，真用时换成用户给的片段）。
  声音类样片较长（示例里写 dur），底部叠一条实时波形。
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from fonts import font
from kvlib import canvas_for_source, canvas_size, unit, is_landscape, safe_zones, probe
from library import FIELDS, GLOBAL, IMPL, allowed, catalog, vname

HERE = Path(__file__).resolve().parent
FONT = font('SourceHanSansCN-Medium.otf')
CLIP = 3.6
SUB = {'text': '真正拉开差距的是信息密度', 'hl': ['信息密度']}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"失败：{' '.join(map(str, cmd[:6]))}…\n{r.stderr[-1500:]}")
    return r


def samples(style, tone, only, A):
    cat = catalog()
    for tid, T in IMPL.items():
        if only and tid not in only:
            continue
        if not allowed(T['style'], style, tone):
            continue
        vs = [v for v, tags in (T.get('variants') or {}).items() if allowed(tags, style, tone)] or [None]
        name = cat.get(tid, {}).get('name') or T.get('name', tid)
        vnames = {v.get('key'): v.get('name') for v in cat.get(tid, {}).get('variants', [])}
        for v in vs:
            demo = dict(T['demo'])
            demo.update((T.get('demo_v') or {}).get(v, {}))   # 变体专用的示例字段
            sub = lambda x: A[x[1:]] if isinstance(x, str) and x[:1] == '@' and x[1:] in A else ([sub(y) for y in x] if isinstance(x, list) else
                                                                                                   {k: sub(y) for k, y in x.items()} if isinstance(x, dict) else x)
            demo = {k: sub(x) for k, x in demo.items()}   # '@photo' 这类换成样本素材路径
            if v and not T.get('variant_ok', {}).get(v, lambda b: True)(demo):
                demo.update({'items': ['选题', '脚本', '剪辑', '复盘'][:3 if v != 'bilingual' else 1]})
                if v == 'roll':
                    demo.update({'from': 0, 'to': 1.729, 'decimals': 3, 'suffix': ' s', 'lead': '首帧耗时', 'text': '换了模型以后', 'log': '[ok] first frame 1.729s'})
            yield (f'{name}' + (f' · {vname(tid, v)}' if v else ''),
                   {'beats': [{'t0': 0.25, 't1': CLIP - 0.1, **demo, 'use': tid, **({'variant': v} if v else {})}],
                    'subs': [{'t0': 0.2, 't1': CLIP - 0.1, 'text': '口播字幕在这里', 'level': 'base'}]})


def field_samples(style, tone, only, A):
    cat = catalog()
    for tid, F in FIELDS.items():
        if only and tid not in only:
            continue
        if not allowed(F['style'], style, tone):
            continue
        if not F['demo']:   # 规律类手法不产生画面
            continue
        name = cat.get(tid, {}).get('name', tid)
        vs = [(v, d) for v, (tags, d) in F['variants'].items() if allowed(tags, style, tone)] or [(None, '')]
        for v, d in vs:
            yield name + (f" · {d.split('：')[0].split('（')[0].split('，')[0]}" if v else ''), \
                {'subs': [{'t0': 0.2, 't1': CLIP - 0.1, 'text': '口播字幕在这里', 'level': 'base'}], **F['demo'](A, v)}


def global_samples(style, only=()):
    title = [{'t0': 0.3, 't1': CLIP - 0.1, 'layout': 'side', 'lead': '这一步叫', 'text': '版本管理', 'hl': ['版本'], 'en': 'Version control', 'sfx': False}]
    for key, (field, opts) in GLOBAL.items():
        if field == 'titles[].anim' or (only and key not in only):
            continue
        for opt, zh in opts.items():
            extra = {'titles': title} if field == 'font_palette' else {}
            sub = {'t0': 0.2, 't1': CLIP - 0.1, **SUB, 'level': 'key' if field == 'sub_key_look' else 'base'}
            yield f'{field} · {zh}', {field: opt, 'subs': [sub], **extra}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--aroll', required=True)
    ap.add_argument('--canvas', type=canvas_size, help='画布 WxH；默认跟随口播方向')
    ap.add_argument('--start', type=float, default=0)
    ap.add_argument('-o', '--out', default='library_preview.mp4')
    ap.add_argument('--only', default='')
    ap.add_argument('--style', default='premium')
    ap.add_argument('--tone', default='web')
    ap.add_argument('--globals', type=int, default=1)
    ap.add_argument('--assets')
    ap.add_argument('--lines', help='口播逐字时间 JSON；默认用口播同名的 .lines.json')
    ap.add_argument('--keep', action='store_true', help='保留每段样片的目录（时间线、分轨），可以逐段跑 audio_check.py')
    a = ap.parse_args()
    ad = Path(a.assets or Path(a.aroll).resolve().parent / 'assets').resolve()
    A = {'shot': str(ad / 'screenshot.png'), 'photo': str(ad / 'photo.jpg'), 'rec': str(ad / 'screen_recording.mov'), 'rec2': str(ad / 'screen_recording2.mov'),
         # 第 5 批声音与粗剪：配乐、没粗剪的口播、两档粗剪结果、带等待段的录屏、样本口播的逐字时间
         'bgm': str(ad / 'music/main.mp3'), 'calm': str(ad / 'music/Curiosity.mp3'), 'dense': str(ad / 'music/Beating_Break.mp3'),
         'hype': str(ad / 'music/Non_Stop.mp3'), 'raw': str(ad / 'raw_koubo.mov'), 'rough_web': str(ad / 'rough/web'),
         'rough_premium': str(ad / 'rough/premium'), 'rec_wait': str(ad / 'rec_wait.mov'),
         'meme': str(ad / 'meme_demo.mp4'),   # 第 8 批插入梗片段的占位片段
         'lines': str(Path(a.lines).resolve()) if a.lines else str(Path(a.aroll).resolve().with_suffix('.lines.json'))}
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    cv = canvas_for_source(a.aroll, a.canvas)
    W, H, FPS = cv['w'], cv['h'], cv['fps']
    S = unit(W, H)
    work = Path(tempfile.mkdtemp(prefix='kv_lib_', dir=out.parent))
    only = set(filter(None, a.only.split(',')))
    jobs = list(samples(a.style, a.tone, only, A)) + list(field_samples(a.style, a.tone, only, A)) + \
        (list(global_samples(a.style, only)) if a.globals else [])
    if not jobs:
        ap.error('--only 没有匹配当前风格的手法')
    parts = []
    source_sizes = {}
    for i, (label, extra) in enumerate(jobs):
        jd = work / f'j{i:02d}'   # 每段样片单独一个目录：逐字时间、缓存互不影响
        jd.mkdir()
        dur = extra.pop('dur', CLIP)
        own = '_aroll' in extra
        src, t_in, k = extra.pop('_aroll', a.aroll), extra.pop('_aroll_in', 0 if own else a.start), extra.pop('_speed', 1.0)
        if src not in source_sizes:
            source_sizes[src] = probe(src)
        room = source_sizes[src]['duration']
        if t_in + dur * k > room:   # 素材不够长：起点往前挪，还不够就缩短这一段
            t_in = max(0.0, room - dur * k)
            dur = min(dur, (room - t_in) / k)
        af = f'atempo={k},' if k != 1 else ''
        cut_vf = f"{f'setpts=PTS/{k},' if k != 1 else ''}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"
        if is_landscape(W, H):
            size = source_sizes[src]
            if not is_landscape(size['w'], size['h']):
                # 声音示例会换回竖屏原片，横屏补虚化侧边，不能把脸裁掉。
                cut_vf = (f"{f'setpts=PTS/{k},' if k != 1 else ''}split[bg][fg];"
                          f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2[blur];"
                          f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fit];"
                          f"[blur][fit]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}")
        run(['ffmpeg', '-y', '-ss', str(t_in), '-i', str(Path(src).resolve()), '-t', str(dur * k + 0.2), '-vf',
             cut_vf,
             '-af', f'{af}aresample=48000', '-c:v', 'libx264', '-crf', '16', '-c:a', 'aac', str(jd / 'aroll.mp4')])
        lines = extra.pop('_lines', None)
        if lines:
            ls = json.loads(Path(lines).read_text(encoding='utf-8'))
            if not own and t_in:   # 样本口播是从中间截的：逐字时间跟着挪到截出来的这一段
                ls = [{**ln, 't0': ln['t0'] - t_in, 't1': ln['t1'] - t_in, 'chars': [[c, x - t_in] for c, x in ln.get('chars', [])],
                       'cuts': [x - t_in for x in ln.get('cuts', [])]} for ln in ls if ln['t1'] > t_in and ln['t0'] < t_in + dur]
            (jd / 'lines.json').write_text(json.dumps(ls, ensure_ascii=False), encoding='utf-8')
            from init_timeline import subs_from_lines
            extra['subs'] = subs_from_lines(ls, dur)
        elif src != a.aroll:   # 换了口播又没有逐字时间：不放示意字幕
            extra.pop('subs', None)
        wave = extra.pop('_wave', False)
        if is_landscape(W, H) and extra.get('broll'):
            focus = [t for t in extra.get('titles', []) if t.get('layout') == 'focus']
            if focus:
                # 截图移到侧栏后，演示框也跟着圈住截图；固定卡片，避免框和素材越漂越远。
                l, top, r, bot = safe_zones(W, H)['text'][0]
                cx = (max(0.05, l) + r) / 2
                for b in extra['broll']:
                    b.update(x=cx, y=0.45, motion='none')
                for t in focus:
                    t['box'] = [cx - 0.09, 0.41, 0.18, 0.08]
        tl = {'canvas': cv, 'style': a.style, 'tone': a.tone, 'aroll': 'aroll.mp4', 'duration': dur,
              'audio': {'voice': {'lufs': -16}}, 'opening': False, **extra}   # 开场冲击只在它自己的样片里出现
        tl['audio'] = {'voice': {'lufs': -16}, **extra.get('audio', {})}
        p = jd / 'timeline.json'
        p.write_text(json.dumps(tl, ensure_ascii=False), encoding='utf-8')
        raw = jd / 'raw.mp4'
        print(f'[{i + 1}/{len(jobs)}] {label}', flush=True)
        run(['python3', str(HERE / 'render.py'), str(p), '-o', str(raw)] + (['--stems'] if a.keep else []))
        lab = work / f'p_{i:02d}.mp4'
        txt = label.replace(':', '\\:').replace("'", '')
        vf = (f"drawtext=fontfile='{FONT}':text='{txt}':x={36*S:g}:y={48*S:g}:fontsize={40*S:g}:fontcolor=white:"
              f"box=1:boxcolor=black@0.55:boxborderw={14*S:g}")
        if wave:   # 声音类样片：底部叠一条实时波形，静音看也知道声音在哪变
            if is_landscape(W, H):
                # 演示波形放在左侧留白，底部留给真实字幕。
                l, top, r, bot = safe_zones(W, H)['text'][0]
                wx, wy = round(W * max(0.05, l)), round(H * 0.64)
                ww, wh = round(W * (r - max(0.05, l))), round(H * 0.12)
                fc = (f"[0:a]asplit=2[a1][a2];[a2]aformat=channel_layouts=mono,showwaves=s={ww}x{wh}:mode=cline:rate=30:colors=0xFFD23F:scale=sqrt[w];"
                      f"[0:v]drawbox=x={wx}:y={wy}:w={ww}:h={wh}:color=black@0.55:t=fill[bg];[bg][w]overlay={wx}:{wy},{vf}[v]")
            else:
                fc = (f"[0:a]asplit=2[a1][a2];[a2]aformat=channel_layouts=mono,showwaves=s=1000x170:mode=cline:rate=30:colors=0xFFD23F:scale=sqrt[w];"
                      f"[0:v]drawbox=x=30:y=ih-330:w=iw-60:h=210:color=black@0.55:t=fill[bg];[bg][w]overlay=40:H-310,{vf}[v]")
            run(['ffmpeg', '-y', '-i', str(raw), '-filter_complex', fc, '-map', '[v]', '-map', '[a1]', '-c:v', 'libx264', '-crf', '18',
                 '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(lab)])
        else:
            run(['ffmpeg', '-y', '-i', str(raw), '-vf', vf, '-c:v', 'libx264', '-crf', '18', '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(lab)])
        frames = run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-count_packets', '-show_entries', 'stream=nb_read_packets',
                      '-of', 'csv=p=0', str(lab)]).stdout.strip()
        parts.append((lab, int(frames) / FPS))   # 按实际帧数记段长：插入镜头这类手法会把样片拉长，按 dur 算会抽错格
    lst = work / 'list.txt'
    lst.write_text(''.join(f"file '{x}'\n" for x, _ in parts), encoding='utf-8')
    run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(out)])
    sheet = out.with_suffix('.jpg')
    cols = min(6, len(parts))
    starts, t = [], 0.0
    for _, d in parts:   # 每段样片取第 2.6 秒（短于 3 秒的取 72% 处）一帧
        starts.append(t + min(2.6, d * 0.72))
        t += d
    sel = '+'.join(f"eq(n\\,{round(x * 30)})" for x in starts)   # 按帧号抽：按时间窗抽会漏帧或一处抽到两帧
    # 图片素材的段是全色域、口播段是有限色域，拼起来后参数中途会变；不让滤镜重建，否则已攒进 tile 的前几格会丢
    run(['ffmpeg', '-y', '-reinit_filter', '0', '-i', str(out), '-vf', f"select='{sel}',scale=270:-2,"
         f"tile={cols}x{(len(parts) + cols - 1) // cols}:padding=6", '-frames:v', '1', '-vsync', 'vfr', str(sheet)])
    if a.keep:
        print('每段样片的目录：', work)
    else:
        shutil.rmtree(work, ignore_errors=True)
    print(f'样本册：{out}（{len(parts)} 段），缩略图墙：{sheet}')


if __name__ == '__main__':
    main()
