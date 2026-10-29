"""按 timeline.json 渲染成片。格式说明见 references/timeline.md。

用法：python render.py timeline.json -o out/final.mp4 [--preview]
--preview 输出 540 宽的低清快速版本，用来自查节奏和排版。

实现思路：每个 B-roll 先单独预处理成「放好尺寸、带透明通道」的小片段（work/ 目录），
主滤镜图只负责按时间叠加，字幕和大字统一生成 ASS 交给 libass 渲染，配乐按人声自动压低。
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from typeset import layout_title, text_w
from doodle import events as doodle_events, resolve_target
from library import expand_beats
from kvlib import (unit, is_landscape, safe_zones, ROLES, SOUNDS, TRANSITIONS, tr_window, all_sfx, paper_ink, auto_transitions, auto_zoom, bgm_gain_db, sfx_gain_db, pip_sub_ranges, load_json, probe, is_image, to_png, find_role_font, style_preset, hex_rgba, make_card, save_json, pip_clip,
                   role_font_overrides, expand_shots, fullscreen_windows, pip_params, pip_hide_ranges, zoom_preset, phrase_subs, CARD_FITS, FULL_FITS, GRAPHIC_LAYOUTS,
                   MATTE_MODES)
import audiomix
import backgrounds
import cards
import effects
import structure
import motion as mfx   # 逐帧合成；prep_broll 里 motion 是素材运动方式的变量名

# ---------------------------------------------------------------- 小工具

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('ffmpeg 失败：\n' + ' '.join(map(str, cmd))[:2000] + '\n' + r.stderr[-3000:])
    return r


def ff_path(p):
    """滤镜参数里的文件路径：统一用正斜杠，Windows 盘符的冒号要转义，否则 FFmpeg 当成参数分隔符。"""
    return Path(p).as_posix().replace(':', r'\:')


def ass_color(c):
    r, g, b, a = hex_rgba(c)
    return f'&H{255 - a:02X}{b:02X}{g:02X}{r:02X}'


def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def esc(text):
    """转成 ASS 文本。换行可以写真换行，也可以写 \\N。"""
    text = text.replace('\\N', '\n').replace('\\', '＼')
    return text.replace('{', '｛').replace('}', '｝').replace('\n', '\\N')


def region_luma(video, t, cx, cy, w, h):
    """视频第 t 秒、以 (cx,cy) 为中心、宽高 w×h（都是 0~1 比例）区域的平均亮度 0~1。"""
    x0, y0 = max(0.0, cx - w / 2), max(0.0, cy - h / 2)
    vf = f"crop=iw*{min(w, 1 - x0):.3f}:ih*{min(h, 1 - y0):.3f}:iw*{x0:.3f}:ih*{y0:.3f},scale=1:1:flags=area,format=gray"
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(video), '-frames:v', '1', '-vf', vf,
                        '-f', 'rawvideo', '-'], capture_output=True)
    return r.stdout[0] / 255 if r.stdout else 0.0


def in_ranges(t, ranges):
    return any(a <= t < b for a, b in ranges)


# ---------------------------------------------------------------- B-roll 预处理

def bounded_broll(b, W, H):
    """横屏卡片和素材带最多占六成宽、七成高；竖屏沿用原尺寸。"""
    if is_landscape(W, H) and b.get('fit', 'cover') in ('card', 'contain', 'tilt', 'double', 'band'):
        return {**b, 'w': min(b.get('w', 0.62), 0.62), 'max_h': min(b.get('max_h', 0.72), 0.72)}
    return b


def landscape_broll(tl, W, H):
    """口播旁的浮卡收进侧栏；镜像三联独占一页，人物已让位的素材保留宽框。"""
    if not is_landscape(W, H):
        return
    for b in tl.get('broll', []):
        if b.get('fit') == 'tilt' and b.get('tilt') == 'pair':
            if not any(l['t0'] <= b['t0'] and l['t1'] >= b['t1'] for l in tl.get('layout', [])):
                tl.setdefault('layout', []).append({'t0': b['t0'], 't1': b['t1'], 'mode': 'hidden'})
    # 手写时间线可省略总时长，至少把所有素材区间纳入口播留白判断。
    plan = tl if tl.get('duration') else {**tl, 'duration': max((b['t1'] for b in tl.get('broll', [])), default=0)}
    wins = fullscreen_windows(plan)
    for j, b in enumerate(tl.get('broll', [])):
        if b.get('fit') not in ('card', 'contain', 'tilt') or not any(max(b['t0'], a) < min(b['t1'], z) for a, z in wins):
            continue
        right = b.get('side', 'right' if j % 2 else 'left') == 'right'
        # 显式横坐标仍是全画布比例，用它选择最近的安全侧栏。
        if 'x' in b:
            right = b['x'] >= 0.5
        l, top, r, bot = safe_zones(W, H)['text'][int(right)]
        l, r = max(l, 0.05), min(r, 0.95)
        b.update(w=min(b.get('w', 1), r - l - 0.055), max_h=min(b.get('max_h', 1), bot - top - 0.12),
                 x=min(r, max(l, b.get('x', (l + r) / 2))), y=min(bot, max(top, b.get('y', (top + bot) / 2))),
                 _side_box=(l, top, r, bot))


def punch_image(i, b, W, H, st, work):
    """冲焦用的第二张图：把截图里关键数字那一块按 scale 倍裁出来，做成和原卡片一样大的卡片（或铺满的画面）。
    b['punch'] = {"t": 相对秒, "dur": 2.0, "scale": 2.3, "cx": 0.5, "cy": 0.4}，cx, cy 是关键数字在截图里的位置。"""
    from PIL import Image
    b = bounded_broll(b, W, H)
    pu = b['punch']
    src = to_png(b['src'], work)
    im = Image.open(src).convert('RGBA')
    sc = pu.get('scale', 2.3)
    cw_, ch_ = im.width / sc, im.height / sc
    x0 = min(max(0, im.width * pu.get('cx', 0.5) - cw_ / 2), im.width - cw_)
    y0 = min(max(0, im.height * pu.get('cy', 0.5) - ch_ / 2), im.height - ch_)
    crop = im.crop((int(x0), int(y0), int(x0 + cw_), int(y0 + ch_))).resize((im.width, im.height), Image.LANCZOS)
    cp = f'{work}/b{i:03d}_punch_src.png'
    crop.save(cp)
    out = f'{work}/b{i:03d}_punch.png'
    fit = b.get('fit', 'cover')
    if fit == 'card':
        make_card(cp, out, int(W * b.get('w', 0.86)), st['card'], max_h=int(H * b.get('max_h', 0.62)))
    elif fit == 'contain':
        bw = int(W * b.get('w', 0.86))
        bh = round(crop.height * bw / crop.width)
        if is_landscape(W, H) and bh > H * b['max_h']:
            bw, bh = round(bw * H * b['max_h'] / bh), int(H * b['max_h'])
        crop.resize((bw, bh), Image.LANCZOS).save(out)
    else:
        r = max(W / crop.width, H / crop.height)
        c2 = crop.resize((int(crop.width * r) + 1, int(crop.height * r) + 1), Image.LANCZOS)
        c2.crop(((c2.width - W) // 2, (c2.height - H) // 2, (c2.width - W) // 2 + W, (c2.height - H) // 2 + H)).save(out)
    return out


def prep_broll(i, b, W, H, FPS, st, work, preview):
    """把一个 B-roll 处理成可直接叠加的片段，返回 (路径, 宽, 高, 是否图片, 是否带透明)。
    card / contain 写了 frame 就再套一层装饰边框（clip_card_frame）。"""
    b = bounded_broll(b, W, H)
    path, w, h, img, alpha = _prep_broll(i, b, W, H, FPS, st, work, preview)
    fit = b.get('fit', 'cover')
    if b.get('frame') and fit in ('card', 'contain'):
        pad = st['card'].get('shadow', 0) if fit == 'card' and (img or b.get('focus') or b.get('marks')) else 0
        path, w, h = frame_wrap(i, path, w, h, pad, b, st, W, H, FPS, work)
    return path, w, h, img, alpha


def frame_wrap(i, path, cw, ch, pad, b, st, W, H, FPS, work):
    """素材卡加装饰边框：glow 发光描边 / viewfinder 取景器。cw, ch 含四周 pad 像素的投影。返回 (路径, 宽, 高)。"""
    look = b['frame']
    if look not in mfx.CARD_FRAMES:
        raise SystemExit(f"broll 的 frame「{look}」不存在，可选：{'、'.join(mfx.CARD_FRAMES)}")
    radius = st['card']['radius'] if b.get('fit') == 'card' else 0
    if path.endswith('.png'):
        return mfx.frame_card_png(path, f'{work}/b{i:03d}_framed.png', look, pad, radius, W, H)
    from PIL import Image
    w, h = cw - 2 * pad, ch - 2 * pad
    under, top, g = mfx.frame_layers(w, h, radius, look, W, H)
    o = max(g, pad)
    up, tp = f'{work}/b{i:03d}_fu.png', f'{work}/b{i:03d}_ft.png'
    Image.fromarray(under).save(up)
    Image.fromarray(top).save(tp)
    out = f'{work}/b{i:03d}_framed.mov'
    dur = b['t1'] - b['t0']
    sh(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', up, '-i', path, '-loop', '1', '-i', tp, '-filter_complex',
        f"[0:v]format=rgba,pad={w + 2 * o}:{h + 2 * o}:{o - g}:{o - g}:color=black@0[u];[u][1:v]overlay={o - pad}:{o - pad}[a];"
        f"[a][2:v]overlay={o - g}:{o - g}:format=auto", '-t', f'{dur:.3f}', '-r', str(FPS), '-c:v', 'prores_ks', '-profile:v', '4444',
        '-pix_fmt', 'yuva444p10le', out])
    return out, w + 2 * o, h + 2 * o


def _prep_broll(i, b, W, H, FPS, st, work, preview):
    src = to_png(b['src'], work) if is_image(b['src']) else b['src']
    dur = round((b['t1'] - b['t0']) * FPS) / FPS
    fit = b.get('fit', 'cover')
    img = is_image(src)
    if b.get('speed') == 'auto' and not img:   # 录屏变速（speed_adjust）：等待段加速、太短整体放慢，正好填满这段
        import retime
        src, note = retime.retime(src, float(b.get('src_in', 0)), dur, FPS, badge=b.get('speed_badge', True),
                                  length=(b['src_out'] - b.get('src_in', 0)) if b.get('src_out') else None)
        print(f"录屏变速 {b['t0']:.1f}~{b['t1']:.1f} 秒：{note}")
        b = {**b, 'src_in': 0, 'speed': 1.0}
    speed = float(b.get('speed', 1.0))
    src_in = float(b.get('src_in', 0))
    motion = b.get('motion', 'push' if fit == 'cover' and img else 'none')   # 铺满的图片默认缓推，画面才「活着」
    focus = b.get('focus')  # {"t": 相对秒, "dur": 0.5, "scale": 2.4, "cx": 0.8, "cy": 0.6}
    crop = b.get('crop')    # [x, y, w, h] 相对素材的比例：只用素材的这一块（横版录屏、小字截图放进竖屏前先裁）
    if crop and img:
        from PIL import Image
        im = Image.open(src)
        x, y, w, h = crop
        src = f'{work}/b{i:03d}_crop.png'
        im.crop((int(x * im.width), int(y * im.height), int((x + w) * im.width), int((y + h) * im.height))).save(src)

    if fit == 'pages':   # 报告纸页飞入堆叠（doc_pages_fly_in），铺满画面的透明片段
        out, cw, ch = mfx.pages(b, W, H, FPS, st, work, f'b{i:03d}')
        return out, cw, ch, False, True

    if fit == 'tilt':   # 透视斜置卡（perspective_card）
        if not img:
            raise SystemExit(f"broll 第 {i + 1} 条：tilt 只支持图片")
        srcs = [to_png(x, work) for x in b.get('srcs', [src])]
        out, cw, ch = mfx.tilt(srcs, b.get('tilt', 'left'), W, H, st, work, f'b{i:03d}', b.get('w', 0.8), b.get('max_h', 0.55))
        if is_landscape(W, H):   # 三联卡也按整组收进内容框，不改卡片内部排法
            from PIL import Image
            im = Image.open(out)
            im.thumbnail((int(W * b['w']), int(H * b['max_h'])), Image.LANCZOS)
            im.save(out)
            cw, ch = im.size
        return out, cw, ch, True, True

    if (focus or b.get('marks')) and fit in ('card', 'contain'):   # 卡片里平滑放大看细节（punch_zoom_detail）、截图划重点（screenshot_highlight）
        out, cw, ch = mfx.live_card(src, b, W, H, FPS, st, work, f'b{i:03d}', preview)
        return out, cw, ch, False, True

    if fit == 'card' and img:
        bw = int(W * b.get('w', 0.86))
        out = f'{work}/b{i:03d}.png'
        _, cw, ch = make_card(src, out, bw, st['card'], max_h=int(H * b.get('max_h', 0.62)))
        return out, cw, ch, True, True

    if fit == 'contain' and img:
        from PIL import Image
        im = Image.open(src).convert('RGBA')
        bw = int(W * b.get('w', 0.86))
        bh = round(im.height * bw / im.width)
        if is_landscape(W, H) and bh > H * b['max_h']:
            bw, bh = round(bw * H * b['max_h'] / bh), int(H * b['max_h'])
        im.resize((bw, bh), Image.LANCZOS).save(f'{work}/b{i:03d}.png')
        return f'{work}/b{i:03d}.png', bw, bh, True, True

    # 以下输出为视频片段
    pre = []
    if img:
        inp = ['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', src]
    else:
        inp = ['-ss', f'{src_in:.3f}', '-i', src]
        pre.append(f'setpts=(PTS-STARTPTS)/{speed}')
        pre.append(f'fps={FPS}')
        if crop:
            pre.append(f'crop=iw*{crop[2]}:ih*{crop[3]}:iw*{crop[0]}:ih*{crop[1]}')
    frames = max(1, round(dur * FPS))

    def zoom_expr():
        if motion == 'push':
            return f"1+0.04*on/{frames}"   # 缓推 4%：教程量出来 4 到 6 秒推 2% 到 5%
        if motion == 'drift':
            return f"1+0.08*on/{frames}"   # 缓推加横向漂移：推到 108%，同时从左往右平移
        if motion == 'pull':
            return f"1.04-0.04*on/{frames}"
        return '1'

    if fit == 'cover':
        chain = pre + [f'scale={W}:{H}:force_original_aspect_ratio=increase', f'crop={W}:{H}', 'setsar=1']
        if (motion in ('push', 'pull', 'drift') or focus) and img:
            chain.append(f'scale={W * 4}:{H * 4}:flags=lanczos')   # 先放大 4 倍再推，否则 zoompan 取整会抖
        if motion in ('push', 'pull', 'drift') or focus:
            z = zoom_expr()
            cx, cy = 0.5, 0.5
            xe = f'iw*{cx}-iw/zoom*{cx}'
            if focus:   # 局部放大看细节；写了 hold 就停 hold 秒再平滑缩回全景
                ft, fd, fs = focus.get('t', 0.0), focus.get('dur', 0.5), focus.get('scale', 2.0)
                cx, cy = focus.get('cx', 0.5), focus.get('cy', 0.5)
                xe = f'iw*{cx}-iw/zoom*{cx}'
                p = f"clip((it-{ft})/{fd},0,1)"
                z = f"(1+({fs}-1)*(({p})*({p})*(3-2*({p})))"
                if focus.get('hold') is not None:
                    q = f"clip((it-{ft + fd + focus['hold']})/{fd},0,1)"
                    z += f"-({fs}-1)*(({q})*({q})*(3-2*({q})))"
                z += ')'
            elif motion == 'drift':
                xe = f'(iw-iw/zoom)*on/{frames}'
            chain.append(f"zoompan=z='{z}':x='{xe}':y='ih*{cy}-ih/zoom*{cy}':d=1:s={W}x{H}:fps={FPS}")
        out = f'{work}/b{i:03d}.mp4'
        sh(['ffmpeg', '-v', 'error', '-y', *inp, '-vf', ','.join(chain), '-t', f'{dur:.3f}', '-an', '-c:v', 'libx264',
            '-preset', 'ultrafast' if preview else 'fast', '-crf', '28' if preview else '16', '-pix_fmt', 'yuv420p', out])
        return out, W, H, False, False

    if fit in ('double', 'band'):
        # 双层构图 / 横版素材带（broll_band_layout）：上层按比例裁成横条放在固定高度，下层铺满做底。
        # 底：blur 同素材虚化压暗（double 默认）/ dim 同素材压暗加网点颗粒、不虚化（band 默认，财经知识口播常用的版式）/ metal 拉丝金属，横条加白边
        ratio = b.get('ratio', '4:3')
        rw, rh = [float(x) for x in ratio.split(':')]
        tw = int(W * b.get('w', 1.0)) // 2 * 2
        th = int(tw * rh / rw) // 2 * 2
        if is_landscape(W, H):
            f = min(1, W * 0.62 / tw, H * 0.72 / th)
            tw, th = int(tw * f) // 2 * 2, int(th * f) // 2 * 2
        y = int(H * b.get('y', 0.42 if fit == 'double' else 0.45) - th / 2)
        blur = st['blur_bg']
        look = b.get('bg', 'blur' if fit == 'double' else 'dim')
        extra = []
        fc = f"[0:v]{','.join(pre + ['split=2']) if pre else 'split=2'}[a][b];"
        if look == 'blur':
            fc += (f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur={blur['blur']}:2,"
                   f"eq=brightness=-{blur['darken'] / 2}[bg];")
        elif look == 'dim':
            extra = ['-loop', '1', '-i', backgrounds.halftone(W, H, work)]
            fc += (f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=brightness=-0.30:saturation=0.8[bd];"
                   f"[bd][1:v]overlay=0:0:shortest=1[bg];")
        elif look == 'video':   # 主题视频压暗做底（theme_video_dim_bg）：bg_src 一段话题视频循环铺满，压暗、轻虚化
            extra = ['-stream_loop', '-1', '-i', str(b['bg_src'])]
            fc += (f"[a]nullsink;[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=8:2,"
                   f"eq=brightness=-0.32:saturation=0.75,format=yuv420p[bg];")
        else:
            extra = ['-loop', '1', '-i', backgrounds.make('metal', None, W, H, work)['path']]
            fc += f"[a]nullsink;[1:v]scale={W}:{H},format=yuv420p[bg];"
        stroke = max(2, int(3 * unit(W, H))) if look == 'metal' else 0
        if is_landscape(W, H) and fit == 'band':
            # 横屏素材带展示整张截图，留白补齐比例，不能裁掉顶部标题。
            fc += f"[b]scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=0x151519"
        else:
            fc += f"[b]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"
        fc += f",pad=iw+{2 * stroke}:ih+{2 * stroke}:{stroke}:{stroke}:color=white[fg];" if stroke else '[fg];'
        fc += f"[bg][fg]overlay=(W-w)/2:{y - stroke},setsar=1[v]"
        out = f'{work}/b{i:03d}.mp4'
        sh(['ffmpeg', '-v', 'error', '-y', *inp, *extra, '-filter_complex', fc, '-map', '[v]', '-t', f'{dur:.3f}', '-an', '-c:v', 'libx264',
            '-preset', 'ultrafast' if preview else 'fast', '-crf', '28' if preview else '16', '-pix_fmt', 'yuv420p', '-r', str(FPS), out])
        return out, W, H, False, False

    # contain / card 的视频：缩放到宽度，圆角，透明底
    p = probe(src)
    bw = int(W * b.get('w', 0.86)) // 2 * 2
    cw, ch = (crop[2], crop[3]) if crop and not img else (1, 1)
    bh = int(bw * p['h'] * ch / max(p['w'] * cw, 1)) // 2 * 2
    if is_landscape(W, H) and bh > H * b['max_h']:
        bw, bh = int(bw * H * b['max_h'] / bh) // 2 * 2, int(H * b['max_h']) // 2 * 2
    r = st['card']['radius'] if fit == 'card' else 0
    chain = pre + [f'scale={bw}:{bh}', 'format=rgba']
    if r:
        chain.append(f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gt(abs(X-W/2),W/2-{r})*gt(abs(Y-H/2),H/2-{r}),"
                     f"if(lte(hypot(abs(X-W/2)-(W/2-{r}),abs(Y-H/2)-(H/2-{r})),{r}),255,0),255)'")
    out = f'{work}/b{i:03d}.mov'
    sh(['ffmpeg', '-v', 'error', '-y', *inp, '-vf', ','.join(chain), '-t', f'{dur:.3f}', '-an', '-c:v', 'prores_ks', '-profile:v', '4444',
        '-pix_fmt', 'yuva444p10le', '-r', str(FPS), out])
    return out, bw, bh, False, True


# ---------------------------------------------------------------- ASS 字幕与大字

def subtitle_scale(text, cfg, sub, W, H):
    """横屏长句收进七成画宽，成片和草稿共用；竖屏不改变字号。"""
    if not is_landscape(W, H):
        return 1.0
    padding = 2 * cfg['box']['pad_x'] if cfg.get('box') else 0
    lines = text.replace('\\N', '\n').split('\n')
    bracket = 2 * cfg['size'] if sub.get('hl_bracket') else 0
    width = (max(text_w(line, cfg['size']) for line in lines) + bracket + cfg.get('spacing', 0) * len(text) + padding) * unit(W, H)
    return min(1.0, W * safe_zones(W, H)['sub_width'] / max(1, width * sub.get('hl_scale', 1)))


def build_ass(tl, st, W, H, fonts, pip_ranges, part='front'):
    """生成 ASS 字幕。fonts: {角色: libass 字体名}。
    part='behind' 只输出标了 behind 的大字（画在抠像人像下面）；'front' 输出其余所有字幕和大字。"""
    k = unit(W, H)
    sub = st['sub']
    tcfg = st['title']
    plain_bg = [(l['t0'], l['t1']) for l in tl.get('layout', []) if l['mode'] in ('aside', 'hidden', 'bg')]

    def style_line(name, font, s, align=5):
        bold, ital = ('-1' if '\\b1' in font else '0'), ('-1' if '\\i1' in font else '0')
        return (f"Style: {name},{font.split(chr(92))[0]},{int(s['size'] * k)},{ass_color(s['color'])},{ass_color(s['color'])},"
                f"{ass_color(s.get('outline_color', '#000000'))},{ass_color(s.get('shadow_color', '#00000080'))},"
                f"{bold},{ital},0,0,100,100,{s.get('spacing', 0) * k:.1f},0,1,{s.get('outline', 0) * k:.1f},"
                f"{s.get('shadow', 0) * k:.1f},{align},0,0,0,1")

    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            + style_line('Base', fonts['sub'], sub['base']) + '\n' + style_line('Key', fonts['sub_key'], sub['key']) + '\n'
            + style_line('Title', fonts['title'], tcfg)
            + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ev = []

    def colored(text, hl, base_color, hl_color):
        out = esc(text)
        for w in sorted(hl or [], key=len, reverse=True):
            out = out.replace(esc(w), f'{{\\c{ass_color(hl_color)}}}{esc(w)}{{\\c{ass_color(base_color)}}}')
        return out

    def anim(kind, x, y, dur, delay=0, dx=0, blur=True, cond=100, pos=None):
        """入场动画标签。dur 是这个元素在画面上的总时长（秒），delay 是比整条晚多少秒出现。
        blur_in 模糊渐清加轻微位移（高级感默认）/ blur_still 原地模糊渐清 / pop 弹出（综艺感默认）/ zoom_in 从大落定 /
        shrink_in 从 150% 缩入 / drop 从上方落下 / slide_up 从下滑上 / slide_left 从左滑入 / fade_up 轻微上浮 /
        flash 先亮白闪一下再定住（闪现）/ fade 淡入 / none 直接出现。dx 表示从左（负）或右（正）滑入。
        pos 给了（让位动作要用 \\move）时，所有带位移的入场退化成原地版本。"""
        out_ms = min(220, int(dur * 300))
        d = int(delay * 1000)
        end = int(dur * 1000)
        fade = f'\\fade(255,0,255,{d},{d + 300},{end - out_ms},{end})'
        quick = f'\\fade(255,0,255,{d},{d + 60},{end - out_ms},{end})'
        P = pos or f'\\pos({x:.0f},{y:.0f})'
        c = cond
        if pos and kind in ('blur_in', 'drop', 'slide_up', 'slide_left', 'fade_up'):
            kind = 'blur_still' if kind == 'blur_in' else 'fade'
        if kind == 'blur_in':
            sx, sy = (x + dx, y) if dx else (x, y + int(26 * k))
            b = f'\\blur12\\t({d},{d + 420},\\blur0)' if blur else ''
            return f'\\move({sx:.0f},{sy:.0f},{x:.0f},{y:.0f},{d},{d + 420}){b}' + fade
        if kind == 'blur_still':
            return P + f'\\blur14\\t({d},{d + 300},\\blur0)' + fade
        if kind == 'pop':
            return (P + f'\\fscx{c * 0.55:.0f}\\fscy55\\t({d},{d + 140},\\fscx{c * 1.08:.0f}\\fscy108)\\t({d + 140},{d + 240},\\fscx{c}\\fscy100)'
                    + quick)
        if kind == 'zoom_in':
            return P + f'\\fscx{c * 1.3:.0f}\\fscy130\\t({d},{d + 300},0.6,\\fscx{c}\\fscy100)' + quick
        if kind == 'zoom_blur':   # 从 130% 带模糊落定（头顶关键词）
            return P + f'\\fscx{c * 1.3:.0f}\\fscy130\\blur8\\t({d},{d + 300},0.6,\\fscx{c}\\fscy100\\blur0)' + quick
        if kind == 'shrink_in':
            return P + f'\\fscx{c * 1.5:.0f}\\fscy150\\t({d},{d + 250},0.5,\\fscx{c}\\fscy100)' + quick
        if kind == 'flash':
            return (P + f'\\1c&HFFFFFF&\\3c&HFFFFFF&\\bord{max(3, int(18 * k))}\\blur{max(4, int(16 * k))}\\fscx{c * 1.08:.0f}\\fscy108'
                    f'\\t({d},{d + 110},\\1c{{COLOR}}\\bord0\\blur0\\fscx{c}\\fscy100)' + quick)
        if kind == 'drop':
            return f'\\move({x:.0f},{y - int(54 * k):.0f},{x:.0f},{y:.0f},{d},{d + 260})' + fade
        if kind == 'slide_up':
            return f'\\move({x:.0f},{y + int(60 * k):.0f},{x:.0f},{y:.0f},{d},{d + 260})' + fade
        if kind == 'slide_left':
            return f'\\move({x - int(90 * k):.0f},{y:.0f},{x:.0f},{y:.0f},{d},{d + 250})' + quick
        if kind == 'fade_up':
            return f'\\move({x:.0f},{y + int(24 * k):.0f},{x:.0f},{y:.0f},{d},{d + 220})' + quick
        if kind == 'fall':   # 上方落下：从上方一成画面高处落下，模糊变清，不回弹（克制入场）
            return f'\\move({x:.0f},{y - H * 0.1:.0f},{x:.0f},{y:.0f},{d},{d + 250})\\blur4\\t({d},{d + 250},\\blur0)' + quick
        if kind == 'graypop':   # 灰变白放大：灰色半透明小字放大成白字
            return (P + f'\\fscx{c * 0.6:.0f}\\fscy60\\1c&H808080&\\alpha&H60&'
                    f'\\t({d},{d + 250},0.5,\\fscx{c}\\fscy100\\1c{{COLOR}}\\alpha&H00&)' + quick)
        if kind == 'flip':   # 镜面翻转：像卡片一样绕竖轴翻进来
            return P + f'\\fry-180\\t({d},{d + 400},0.6,\\fry0)' + quick
        if kind == 'blur_down':   # 溶解飘下：模糊着从上方一点落下（一行大小字混排的突出变体）
            return f'\\move({x:.0f},{y - int(30 * k):.0f},{x:.0f},{y:.0f},{d},{d + 320})\\blur8\\t({d},{d + 320},\\blur0)' + fade
        if kind == 'none':
            return P
        return P + fade

    def add(t0, t1, style, tags, text, layer=2):
        ev.append(f"Dialogue: {layer},{ass_time(t0)},{ass_time(t1)},{style},,0,0,0,,{{{tags}}}{text}")

    def soft_shadow(t0, t1, style, tags, text, size, alpha, layer):
        """柔和投影：同样的字画一层模糊的黑色，往右下偏一点，比描边和硬阴影高级。"""
        off = max(2, size * 0.035)
        tags = re.sub(r'\\(pos|move)\(([-\d.]+),([-\d.]+)(?:,([-\d.]+),([-\d.]+))?', lambda m: (
            f"\\{m.group(1)}({float(m.group(2)) + off:.0f},{float(m.group(3)) + off * 1.4:.0f}"
            + (f",{float(m.group(4)) + off:.0f},{float(m.group(5)) + off * 1.4:.0f}" if m.group(4) else '')), tags, count=1)
        tags = re.sub(r'\\blur\d+(\\t\([^)]*\\blur0\))?', '', tags)
        plain = re.sub(r'\\1?c&H[0-9A-Fa-f]{6,8}&?', '', re.sub(r'\{\\c[^}]*\}', '', text)).replace('{}', '')   # 投影只要黑色：去掉字里的换色（含 \\t 里的）
        add(t0, t1, style, tags + f'\\c&H000000&\\3c&H000000&\\alpha&H{alpha:02X}&\\blur{max(4, int(size * 0.09))}', plain, layer)

    def shape_path(w, h, r, skew=0.0):
        """圆角矩形（skew>0 时是向右倾斜的平行四边形）的 ASS 矢量路径，坐标从左上角 0,0 起。"""
        if skew:
            o = h * skew
            return f"m {o:.0f} 0 l {w:.0f} 0 l {w - o:.0f} {h:.0f} l 0 {h:.0f}"
        r = min(r, h / 2, w / 2)
        if r < 1:
            return f"m 0 0 l {w:.0f} 0 l {w:.0f} {h:.0f} l 0 {h:.0f}"
        return (f"m {r:.0f} 0 l {w - r:.0f} 0 b {w:.0f} 0 {w:.0f} 0 {w:.0f} {r:.0f} l {w:.0f} {h - r:.0f} b {w:.0f} {h:.0f} {w:.0f} {h:.0f} {w - r:.0f} {h:.0f} "
                f"l {r:.0f} {h:.0f} b 0 {h:.0f} 0 {h:.0f} 0 {h - r:.0f} l 0 {r:.0f} b 0 0 0 0 {r:.0f} 0")

    # ---------------- 字幕区暗影：衣服印字、杂乱背景抢字幕时，在画面底部垫一条很柔的渐暗
    if part == 'front' and tl.get('subs') and tl.get('sub_scrim', sub.get('scrim', False)):
        top = int(H * (sub['base']['y'] - 0.08))
        end = max(x['t1'] for x in tl['subs'])
        alpha = tl.get('sub_scrim_alpha', 0x70)
        ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(end)},Base,,0,0,0,,{{\\an7\\pos(0,{top})\\bord0\\shad0\\1c&H000000&"
                  f"\\1a&H{alpha:02X}&\\blur{int(H * 0.04)}\\p1}}m 0 0 l {W} 0 l {W} {H - top + int(H * 0.05)} l 0 {H - top + int(H * 0.05)}{{\\p0}}")

    # ---------------- 双行滚动字幕（sub_rolling_two_line）：左下角只留两行，上一句变灰退到上面，当前句在下，换句时整体上滚一行
    if part == 'front' and sub.get('rolling'):
        rs = sorted(tl.get('subs', []), key=lambda x: x['t0'])
        cfg = sub['base']
        lh = cfg['size'] * k * 1.45
        x, y2 = int(W * 0.045), int(H * cfg['y'])
        align = 1
        if is_landscape(W, H):
            x, y2 = int(W * safe_zones(W, H)['sub'][0]), int(H * cfg['y'])
            align = 2
        y1 = y2 - lh
        cur_c, prev_c = ass_color(cfg['color']), ass_color(sub.get('prev_color', '#9A9A9A'))
        edge = '\\bord0\\shad0' if sub.get('ink') else f"\\bord{max(1, 2 * k):.1f}\\3c&H000000&\\shad0\\blur1"
        def rolling_tags(s):
            f = subtitle_scale(s['text'], cfg, sub, W, H)
            return f"\\fs{cfg['size'] * k * f:.1f}\\fsp{cfg.get('spacing', 0) * k * f:.1f}" if is_landscape(W, H) else ''
        for j, s in enumerate(rs):
            nxt = rs[j + 1]['t0'] if j + 1 < len(rs) else s['t1']
            t1 = max(s['t1'], min(nxt, s['t1'] + 1.5))
            add(s['t0'], t1, 'Base', f"\\an{align}\\b1{edge}{rolling_tags(s)}\\1c{cur_c}\\move({x},{y2 + lh:.0f},{x},{y2:.0f},0,150)", esc(s['text']))
            if j:
                pv = rs[j - 1]
                add(s['t0'], t1, 'Base', f"\\an{align}\\b1{edge}{rolling_tags(pv)}\\1c{cur_c}\\move({x},{y2:.0f},{x},{y1:.0f},0,150)\\t(0,150,\\1c{prev_c})", esc(pv['text']))
            if j > 1:
                add(s['t0'], s['t0'] + 0.15, 'Base', f"\\an{align}\\b1{edge}{rolling_tags(rs[j - 2])}\\1c{prev_c}\\move({x},{y1:.0f},{x},{y1 - lh:.0f},0,150)\\fad(0,150)",
                    esc(rs[j - 2]['text']))

    # ---------------- 跟读字幕
    for s in (tl.get('subs', []) if part == 'front' and not sub.get('rolling') else []):
        key = s.get('level') == 'key'
        lv = 'Key' if key else 'Base'
        cfg = sub['key'] if key else sub['base']
        sub_scale = subtitle_scale(s['text'], cfg, sub, W, H)
        y = sub['pip_y'] if in_ranges((s['t0'] + s['t1']) / 2, pip_ranges) else cfg['y']
        y = s.get('y', y)
        x, yy = W // 2, int(H * y)
        hls = (s.get('hl') or [])[:1]   # 一行只强调一个词
        if sub.get('hl_bracket'):   # 加【】不变色（教程类：操作名、参数一眼找到）
            text = esc(s['text'])
            for w in hls:
                text = text.replace(esc(w), f"【{esc(w)}】", 1)
        elif sub.get('hl_weight'):   # 强调词换粗一档字体，不变色
            text = esc(s['text'])
            for w in hls:
                text = text.replace(esc(w), f"{{\\fn{fonts['sub_key']}}}{esc(w)}{{\\fn{fonts['sub_key' if key else 'sub']}}}")
        else:
            text = colored(s['text'], hls, cfg['color'], sub['hl_color'])
            sc = sub.get('hl_scale')
            if sc and hls:   # 强调词放大（亮黄放大、综艺条纹花字）
                w = esc(hls[0])
                grow = f"\\t(0,140,\\fscx{sc * 112:.0f}\\fscy{sc * 112:.0f})\\t(140,240,\\fscx{sc * 100:.0f}\\fscy{sc * 100:.0f})" if sub.get('hl_pop') else ''
                text = text.replace(w, f"{{\\fscx{sc * 100:.0f}\\fscy{sc * 100:.0f}{grow}}}{w}{{\\fscx100\\fscy100}}", 1)
        dur = s['t1'] - s['t0']
        tags = f"\\an5\\fn{fonts['sub_key' if key else 'sub']}" + (anim(s.get('anim', 'fade' if cfg.get('box') else tcfg.get('anim', 'fade')), x, yy, dur, blur=False) if key
                                                                    else f'\\pos({x},{yy})')
        if sub_scale != 1:
            tags += f"\\fs{cfg['size'] * k * sub_scale:.2f}\\fsp{cfg.get('spacing', 0) * k * sub_scale:.2f}"
        if cfg.get('box'):   # 半透明圆角底条，宽度按这句字算
            bx = cfg['box']
            fs = cfg['size'] * k * sub_scale
            w = text_w(s['text'], fs) + cfg.get('spacing', 0) * k * sub_scale * len(s['text']) + bx['pad_x'] * 2 * k * sub_scale
            h = fs * 0.95 + bx['pad_y'] * 2 * k * sub_scale
            if is_landscape(W, H):
                lines = s['text'].replace('\\N', '\n').split('\n')
                w = max(text_w(line, fs) for line in lines) + (2 * fs if sub.get('hl_bracket') else 0) + (cfg.get('spacing', 0) * max(map(len, lines)) + bx['pad_x'] * 2) * k * sub_scale
                h = fs * 1.2 * (len(lines) - 1) + h
            r = min(h / 2, bx['r'] * k) if 'r' in bx else h / 2
            x0, y0 = x - w / 2, yy - h / 2
            path = shape_path(w, h, r)
            ev.append(f"Dialogue: 0,{ass_time(s['t0'])},{ass_time(s['t1'])},{lv},,0,0,0,,{{\\an7\\pos({x0:.0f},{y0:.0f})\\bord0\\shad0"
                      f"\\1c{ass_color(bx['color'])[:2]}{ass_color(bx['color'])[4:]}&\\1a&H{int(255 * (1 - bx['alpha'])):02X}&\\fad(80,80)\\p1}}{path}{{\\p0}}")
        elif cfg.get('shadow_alpha') is not None:
            soft_shadow(s['t0'], s['t1'], lv, tags, text, cfg['size'] * k, cfg['shadow_alpha'], 0)
        add(s['t0'], s['t1'], lv, tags, text, layer=1)

    # ---------------- 定格暂停的暂停图标：半透明圆里两道竖杠，画在头像右上
    for fz in (tl.get('freezes', []) if part == 'front' else []):
        r = int(1080 * unit(W, H) * 0.06)
        cx, cy = int(W / 2 + 1080 * unit(W, H) * fz.get('d', 0.5) * 0.36), int(H * fz.get('y', 0.45) - 1080 * unit(W, H) * fz.get('d', 0.5) * 0.36)
        circle = ' '.join(f"{'m' if i == 0 else 'l'} {r + r * math.cos(i * math.pi / 24):.0f} {r + r * math.sin(i * math.pi / 24):.0f}" for i in range(49))
        bar_w, bar_h = r * 0.28, r * 0.9
        bars = (f"m {r - bar_w * 1.6:.0f} {r - bar_h / 2:.0f} l {r - bar_w * 0.6:.0f} {r - bar_h / 2:.0f} l {r - bar_w * 0.6:.0f} {r + bar_h / 2:.0f} "
                f"l {r - bar_w * 1.6:.0f} {r + bar_h / 2:.0f} m {r + bar_w * 0.6:.0f} {r - bar_h / 2:.0f} l {r + bar_w * 1.6:.0f} {r - bar_h / 2:.0f} "
                f"l {r + bar_w * 1.6:.0f} {r + bar_h / 2:.0f} l {r + bar_w * 0.6:.0f} {r + bar_h / 2:.0f}")
        for lay_, path, col, al in ((3, circle, '&H000000&', '&H50&'), (4, bars, '&HFFFFFF&', '&H00&')):
            ev.append(f"Dialogue: {lay_},{ass_time(fz['t0'])},{ass_time(fz['t1'])},Base,,0,0,0,,{{\\an7\\pos({cx - r},{cy - r})\\bord0\\shad0"
                      f"\\1c{col}\\1a{al}\\fscx40\\fscy40\\t(0,140,\\fscx100\\fscy100)\\p1}}{path}{{\\p0}}")

    # ---------------- 手绘贴纸（圈注、下划线、箭头等），见 doodle.py
    for d in (tl.get('doodles', []) if part == 'front' else []):
        d = resolve_target(d, tl, st, W, H)
        ev.extend(doodle_events(d, W, H, ass_color(d.get('color', tcfg['hl_color']))[:2] + ass_color(d.get('color', tcfg['hl_color']))[4:] + '&',
                                ass_time, k))

    # ---------------- 大字：typeset.layout_title 排好位置，这里只负责画出来
    def draw_shape(t0, t1, it):
        """色块、标签底板：可弹出（pop）、侧滑（slide）、从左往右刷出（wipe，秒），fade_tail 让右端渐隐。"""
        a0 = t0 + it.get('delay', 0)
        a1 = t0 + it['until'] if it.get('until') else t1
        x, y, w, h = it['x'], it['y'], it['w'], it['h']
        col = ass_color(it['color'])
        tags = f"\\an7\\bord0\\shad0\\1c{col}\\1a&H{int(255 * (1 - it.get('alpha', 1))):02X}&\\fad(60,180)"
        if it.get('rot'):
            tags += f"\\org({x + w / 2:.0f},{y + h / 2:.0f})\\frz{it['rot']}"
        pos = f"\\pos({x:.0f},{y:.0f})"
        if it.get('anim') == 'slide' and it.get('slide'):
            pos = f"\\move({x + it['slide'] * W * 0.25:.0f},{y:.0f},{x:.0f},{y:.0f},0,260)"
        elif it.get('anim') == 'pop':
            tags += f"\\org({x + w / 2:.0f},{y + h / 2:.0f})\\fscx80\\fscy80\\t(0,160,\\fscx100\\fscy100)"
        if it.get('wipe'):
            w0 = it.get('wipe_from', 1)
            tags += (f"\\clip({x - 2:.0f},{y - 4:.0f},{x + w0:.0f},{y + h + 4:.0f})"
                     f"\\t(0,{int(it['wipe'] * 1000)},0.6,\\clip({x - 2:.0f},{y - 4:.0f},{x + w + 4:.0f},{y + h + 4:.0f}))")
        path = shape_path(w, h, it.get('r', 0), it.get('skew', 0))
        if it.get('fade_tail'):   # 右边 40% 分 6 段逐渐变透明
            base_a = 1 - it.get('alpha', 1)
            for j in range(6):
                sx0 = x + w * (0.6 + 0.4 * j / 6)
                seg = re.sub(r'\\clip\([^)]*\)|\\t\(0,\d+,0\.6,\\clip\([^)]*\)\)', '', tags)
                a = int(255 * min(1, base_a + (j + 1) / 7))
                ev.append(f"Dialogue: 1,{ass_time(a0)},{ass_time(a1)},Base,,0,0,0,,{{{pos}{seg}\\1a&H{a:02X}&"
                          f"\\clip({sx0:.0f},{y - 4:.0f},{sx0 + w * 0.4 / 6 + 1:.0f},{y + h + 4:.0f})\\p1}}{path}{{\\p0}}")
            tags += f"\\clip({x - 2:.0f},{y - 4:.0f},{x + w * 0.6:.0f},{y + h + 4:.0f})" if not it.get('wipe') else ''
        ev.append(f"Dialogue: 1,{ass_time(a0)},{ass_time(a1)},Base,,0,0,0,,{{{pos}{tags}\\p1}}{path}{{\\p0}}")

    def typed_text(text, m, hl, color, hl_color, cursor):
        """打字机：前 m 个字可见，后面跟光标，剩下的字透明占位（排版不跳）。"""
        vis = colored(text[:m], hl, color, hl_color)
        cur = f"{{\\alpha&H00&\\c{ass_color(color)}}}|" if cursor else ''
        rest = text[m:]
        return vis + cur + (f"{{\\alpha&HFF&}}{esc(rest)}" if rest else '')

    for t in tl.get('titles', []):
        if part == 'behind' and not t.get('behind'):
            continue
        tdur = t['t1'] - t['t0']
        kind0 = t.get('anim', tcfg.get('anim', 'blur_in'))
        on_plain = in_ranges((t['t0'] + t['t1']) / 2, plain_bg)
        for it in layout_title(t, st, W, H):
            if t.get('behind') and bool(it.get('front')) == (part == 'behind'):   # 人压字：front 的那项画在人前面
                continue
            if it.get('kind') == 'dim':
                if not on_plain:
                    ev.append(f"Dialogue: 0,{ass_time(t['t0'] + it.get('delay', 0))},{ass_time(t['t1'])},Base,,0,0,0,,{{\\an7\\pos(0,0)\\bord0\\shad0\\1c&H000000&"
                              f"\\1a&H{int(255 * (1 - it['alpha'])):02X}&\\fad(250,200)\\p1}}m 0 0 l {W} 0 l {W} {H} l 0 {H}{{\\p0}}")
                continue
            if it.get('kind') == 'shape':
                draw_shape(t['t0'], t['t1'], it)
                continue
            if it.get('kind') == 'doodle':
                dd = {**it, 't0': t['t0'] + it.get('delay', 0), 't1': t['t1']}
                col = ass_color(it.get('color', tcfg['hl_color']))
                ev.extend(doodle_events(dd, W, H, col[:2] + col[4:] + '&', ass_time, k))
                continue
            x, y, size = it['x'], it['y'], it['size']
            cond = it.get('condense', 100)
            t1 = t['t0'] + it['until'] if it.get('until') else t['t1']
            dur = t1 - t['t0']
            tags = (f"\\an{it['an']}\\fn{fonts.get(it['role'], fonts['title'])}\\fs{size:.0f}\\fscx{cond}"
                    f"\\fsp{it.get('spacing', 0):.1f}\\c{ass_color(it['color'])}\\bord0\\shad0")
            if it.get('rot'):
                tags += f"\\frz{it['rot']}"
            alpha = int(255 * (1 - it.get('alpha', 1)))
            if it.get('hollow'):
                tags += f"\\1a&HFF&\\bord{max(2, size * 0.012):.1f}\\3c{ass_color(it['color'])}\\3a&H{alpha:02X}&"
            elif alpha:
                tags += f"\\alpha&H{alpha:02X}&"
            if it.get('outline'):
                tags += f"\\bord{it['outline']:.1f}\\3c{ass_color(it.get('outline_color', '#000000'))}"
            if it.get('box'):
                tags += f"\\bord{size * 0.28:.0f}\\3c{ass_color(it['box'])}\\3a&H{255 - hex_rgba(it['box'])[3]:02X}&"
            kind = it.get('anim', kind0)
            mv = it.get('move')
            pos = None
            if mv:   # 出现以后的让位动作：缩小、挪开、变灰、变淡
                a, b = int(mv['at'] * 1000), int((mv['at'] + mv.get('dur', 0.25)) * 1000)
                pos = f"\\move({x:.0f},{y:.0f},{x + mv.get('dx', 0):.0f},{y + mv.get('dy', 0):.0f},{a},{b})"
            dx = 0
            if kind == 'blur_in' and it['an'] in (7, 9):
                dx = int(-40 * k) if it['an'] == 7 else int(40 * k)
            if kind == 'wipe_down':
                d = int(it.get('delay', 0) * 1000)
                tags += (f"\\pos({x:.0f},{y:.0f})\\clip({x - size:.0f},{y - size:.0f},{x + size:.0f},{y - size * 0.5:.0f})"
                         f"\\t({d},{d + 220},\\clip({x - size:.0f},{y - size:.0f},{x + size:.0f},{y + size:.0f}))\\fade(255,0,255,{d},{d + 40},{int(dur * 1000) - 200},{int(dur * 1000)})")
            elif kind != 'type':
                tags += anim(kind, x, y, dur, it.get('delay', 0), dx=dx, cond=cond, pos=pos).replace('{COLOR}', ass_color(it['color']))
            if t.get('dim_after') is not None and not it.get('hollow'):   # 读完压暗留底：说完后 2.5 秒慢慢暗到三成多，留在画面上
                a = int(t['dim_after'] * 1000)
                tags += f'\\t({a},{a + 2500},\\alpha&HA6&)'
            if mv:
                ch = ''
                if 'scale' in mv:
                    ch += f"\\fscx{cond * mv['scale']:.0f}\\fscy{100 * mv['scale']:.0f}"
                if 'color' in mv:
                    ch += f"\\1c{ass_color(mv['color'])}"
                if 'alpha' in mv:
                    ch += f"\\alpha&H{int(255 * (1 - mv['alpha'])):02X}&"
                if ch:
                    tags += f"\\t({a},{b},{ch})"
            text = it['rich'] if it.get('rich') else colored(it['text'], it.get('hl'), it['color'], it.get('hl_color', it['color']))   # rich：排版已写好行内样式（大小字混排）
            if it.get('glow'):   # 柔光：同样的字画一层模糊的同色光晕垫在下面
                gtags = re.sub(r'\\blur\d+(\\t\([^)]*\\blur0\))?', '', tags)
                add(t['t0'], t1, 'Title', gtags + f"\\bord{max(3, size * 0.05):.0f}\\3c{ass_color(it['color'])}\\blur{max(8, int(size * 0.16))}\\alpha&HA0&",
                    re.sub(r'\{\\c[^}]*\}', '', text), layer=1)
            if kind == 'type':   # 打字机：一个字一个字打出，末尾光标，打完闪两下消失
                chars = it['text']
                n = len(chars)
                cps = it.get('cps', 0.07)
                d0 = t['t0'] + it.get('delay', 0)
                ttags = tags + (pos or f"\\pos({x:.0f},{y:.0f})")
                steps = [(d0 + (m - 1) * cps, d0 + m * cps, m, True) for m in range(1, n + 1)]
                tend = d0 + n * cps
                for j in range(4):
                    steps.append((tend + j * 0.25, tend + (j + 1) * 0.25, n, j % 2 == 1))
                steps.append((tend + 1.0, t1, n, False))
                for s0, s1, m, cur in steps:
                    if s0 >= t1:
                        break
                    s1 = min(s1, t1)
                    txt = typed_text(chars, m, it.get('hl'), it['color'], it.get('hl_color', it['color']), cur)
                    last = s1 >= t1 - 1e-3
                    if it.get('shadow'):
                        soft_shadow(s0, s1, 'Title', ttags + ('\\fad(0,200)' if last else ''), txt, size, tcfg.get('shadow_alpha', 0x90), 1)
                    add(s0, s1, 'Title', ttags + ('\\fad(0,200)' if last else ''), txt, layer=2)
                continue
            if it.get('count'):   # 数字滚动：每 1/20 秒换一次数字，缓出地停在终值
                c = it['count']
                d0 = t['t0'] + it.get('delay', 0)
                n = max(2, int(c['dur'] * 20))
                for j in range(n + 1):
                    pgs = 1 - (1 - j / n) ** 3
                    v = c['from'] + (c['to'] - c['from']) * pgs
                    txt = esc(f"{c['prefix']}{v:,.{c['decimals']}f}{c['suffix']}")
                    a1 = d0 + (j + 1) * c['dur'] / n if j < n else t1
                    ftags = re.sub(r'\\(move|fade)\([^)]*\)', '', tags) + (f'\\pos({x:.0f},{y:.0f})' if '\\pos' not in tags else '')
                    ftags = ftags.replace('\\blur12', '')
                    if it.get('shadow'):
                        soft_shadow(d0 + j * c['dur'] / n, a1, 'Title', ftags, txt, size, tcfg.get('shadow_alpha', 0x90), 1)
                    add(d0 + j * c['dur'] / n, a1, 'Title', ftags + (f'\\fad(0,200)' if j == n else ''), txt, layer=2)
                continue
            if it.get('shadow') and not it.get('hollow'):
                soft_shadow(t['t0'], t1, 'Title', tags, text, size, tcfg.get('shadow_alpha', 0x90), 1)
            add(t['t0'], t1, 'Title', tags, text, layer=2)
    return head + '\n'.join(ev) + '\n'


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('timeline')
    ap.add_argument('-o', '--out', default='out/final.mp4')
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--keep', action='store_true', help='保留中间文件')
    ap.add_argument('--stems', action='store_true', help='另存人声、配乐、音效三条分轨 wav（audio_check.py 用来核对齐和音量）')
    ap.add_argument('--no-subs', action='store_true', help='不压常驻字幕（剪映草稿里剪映做不了的段落用这版画面，字幕留给剪映文字）')
    a = ap.parse_args()

    tl_path = Path(a.timeline).resolve()
    os.chdir(tl_path.parent)  # timeline 里的相对路径以它所在目录为准
    tl = load_json(tl_path)
    st = style_preset(tl)
    tl['titles'] = tl.get('titles', []) + expand_beats(tl, st)   # beats 按内容自动搭配成大字（library.py）
    paper_ink(tl)   # 米白纸页上的大字换深色
    structure.prepare(tl, st)   # 首帧封面、一词一镜快剪、段落收尾推高收束、要点编号按章节排（第 10 批）
    phrase_subs(tl)   # 快剪一词一镜字幕：指定段落里字幕拆成短语，可带每个短语换一档景别（第 9 批）
    audiomix.prepare(tl, st)   # 声音先入、按段落排配乐（audiomix）
    expand_shots(tl, st)   # 截图叠放、透视卡左右交替、相邻卡片同向衔接、版式自带音效（kvlib）
    effects.prepare(tl, st)   # 整屏特效附带的推近、震动、声音（第 8 批）
    if a.no_subs:
        tl['subs'] = []
    cv = tl.get('canvas', {'w': 1080, 'h': 1920, 'fps': 30})
    W, H, FPS = cv['w'], cv['h'], cv['fps']
    if a.preview:
        W, H = W // 2 // 2 * 2, H // 2 // 2 * 2
    landscape_broll(tl, W, H)
    work = Path(tempfile.mkdtemp(prefix='kv_render_', dir='.'))
    aroll = tl['aroll']
    TAIL = float(tl.get('tail', 0))   # 口播说完后再留几秒（定格最后一帧，可配片尾大字、配乐收尾）
    DUR = (tl.get('duration') or probe(aroll)['duration']) + TAIL

    fover = role_font_overrides(tl, st)
    style_name = tl.get('style', 'premium')
    fontsdir = work / 'fonts'
    fontsdir.mkdir()
    fonts = {}
    for role in ROLES:
        path, name, _ = find_role_font(role, style_name, fover.get(role))
        fonts[role] = name
        link = fontsdir / Path(path).name
        if not link.exists():
            try:
                os.symlink(path, link)
            except OSError:   # Windows 没开开发者模式不能建软链接，复制一份
                shutil.copyfile(path, link)

    inputs, fc = ['-i', aroll], []
    n_in = 1

    def add_input(args):
        nonlocal n_in
        inputs.extend(args)
        n_in += 1
        return n_in - 1

    # ---- 口播主画面：推近关键帧
    vpad = f"tpad=stop_mode=clone:stop_duration={TAIL:.3f}," if TAIL else ''
    zooms = [zoom_preset(z) for z in tl.get('zoom', [])] + auto_zoom(tl, st)   # 手写推近（含缓推预设）+ 自动景别
    if zooms:
        terms, drift = [], []
        for z in zooms:
            e = max(z.get('ease', st['punch']['dur']), 0.01)
            f0, f1 = z.get('from', 1.0), z.get('to', st['punch']['scale'])
            p = f"clip((it-{z['t0']})/{e},0,1)"
            terms.append(f"between(it,{z['t0']},{z['t1']})*(({f0})+(({f1})-({f0}))*({p})*({p})*(3-2*({p}))-1)")
            if z.get('dx'):   # 横向漂移
                drift.append(f"between(it,{z['t0']},{z['t1']})*{z['dx']}*({p})*({p})*(3-2*({p}))")
        zexpr = '1+' + '+'.join(terms)
        ay = tl.get('zoom_anchor_y', 0.38)
        xe = f"clip(iw/2-iw/zoom/2+iw*({'+'.join(drift)}),0,iw-iw/zoom)" if drift else 'iw/2-iw/zoom/2'
        fc.append(f"[0:v]{vpad}scale={W}:{H},setsar=1,zoompan=z='{zexpr}':x='{xe}':y='ih*{ay}-ih/zoom*{ay}':d=1:s={W}x{H}:fps={FPS}[ar_in]")
    else:
        fc.append(f"[0:v]{vpad}scale={W}:{H},setsar=1,fps={FPS}[ar_in]")
    op = tl.get('_opening')   # 开场第一秒入场冲击（opening_entry_hit），expand_shots 定的做法
    if op:
        f, d = mfx.opening(aroll, op, W, H, FPS, work, a.preview)
        idx = add_input(['-i', f])
        fc.append(f"[{idx}:v]format=rgba[opn]")
        fc.append(f"[ar_in][opn]overlay=0:0:enable='between(t,0,{d:.3f})':eof_action=pass[ar]")
    else:
        fc.append('[ar_in]null[ar]')

    layout = tl.get('layout', [])
    frames = [(l['t0'], l['t1']) for l in layout if l['mode'] == 'frame']
    aside = [(l['t0'], l['t1']) for l in layout if l['mode'] in ('aside',)] + frames   # 画框底的背景也是虚化口播
    hidden = [(l['t0'], l['t1']) for l in layout if l['mode'] == 'hidden']
    papers = [l for l in layout if l['mode'] in ('paper', 'bg')]
    pips = [l for l in layout if l['mode'] == 'pip']
    circles = [l for l in layout if l['mode'] == 'circle']
    pip_ranges = pip_sub_ranges(pips, st)
    nsplit = 1 + (1 if aside else 0) + (1 if frames else 0)
    if nsplit > 1:
        fc.append(f"[ar]split={nsplit}" + ''.join(f'[ar{j}]' for j in range(nsplit)))
        cur, j = '[ar0]', 1
    else:
        cur, j = '[ar]', 1
    if aside:
        bl = st['blur_bg']
        en = '+'.join(f'between(t,{x},{y})' for x, y in aside)
        fc.append(f"[ar{j}]boxblur={bl['blur']}:2,eq=brightness=-{bl['darken'] / 2:.3f}:saturation=0.85[arbg]")
        fc.append(f"{cur}[arbg]overlay=0:0:enable='{en}'[base0]")
        cur, j = '[base0]', j + 1
    if frames:   # 画框底：口播缩进一个带白边和投影的画框，后面是虚化口播，用在「第一招」这类小节编号点
        fw = int(W * 0.8) // 2 * 2
        bd = max(4, int(8 * unit(W, H)))
        en = '+'.join(f'between(t,{x},{y})' for x, y in frames)
        crop_frame = "crop=iw:iw*1.15:0:ih*0.06" if W * 1.15 <= H * 0.94 else "crop=iw:ih*0.94:0:ih*0.03"
        if is_landscape(W, H):
            fw = min(fw, int(H * 0.72 * W / (H * 0.94))) // 2 * 2
        fc.append(f"[ar{j}]{crop_frame},scale={fw}:-2,pad=iw+{bd * 2}:ih+{bd * 2}:{bd}:{bd}:color=0xF7F5F0[arfr]")
        fc.append(f"{cur}[arfr]overlay=(W-w)/2:H*0.43-h/2:enable='{en}'[basefr]")
        cur, j = '[basefr]', j + 1
    for pi_, l in enumerate(papers):   # 纸页底、网格底、点阵底：代码画的背景盖住口播画面（声音还在），人物用小窗或抠像放上面
        spec = backgrounds.make('paper', l.get('paper', 'kraft'), W, H, work) if l['mode'] == 'paper' else \
            backgrounds.make(l.get('bg', 'grid'), l.get('variant'), W, H, work)
        idx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f"{l['t1'] - l['t0']:.3f}", '-i', spec['path']])
        fc.append(f"[{idx}:v]{backgrounds.ffmpeg_chain(spec, W, H)},setpts=PTS-STARTPTS+{l['t0']}/TB[pp_bg{pi_}]")
        fc.append(f"{cur}[pp_bg{pi_}]overlay=0:0:enable='between(t,{l['t0']},{l['t1']})':eof_action=pass[pbase{pi_}]")
        cur = f'[pbase{pi_}]'
    if hidden:
        en = '+'.join(f'between(t,{x},{y})' for x, y in hidden)
        fc.append(f"color=c=black:s={W}x{H}:r={FPS}:d={DUR}[blk]")
        fc.append(f"{cur}[blk]overlay=0:0:enable='{en}'[base1]")
        cur = '[base1]'
    # 逐帧合成的版式：inset 口播缩成圆角卡片并缩放、split 分屏对比（motion.py），
    # mockup 样机、combo 头像图文版、overview 目录回顾、endcard 关注尾帧（cards.py），铺满画面盖在底上
    # matte 抠像换底、corner 人缩角让位、breakout 人物出框（matte.py），morph 窗口按节拍变形（effects.py）
    for li, l in enumerate(x for x in layout if x['mode'] in ('inset', 'split') + cards.LAYOUT_MODES + MATTE_MODES + effects.LAYOUT_MODES):
        if l['mode'] in effects.LAYOUT_MODES:
            f = effects.layout_clip(l, tl, W, H, FPS, st, work, aroll, a.preview)
        elif l['mode'] in MATTE_MODES:
            import matte
            f = matte.layout_clip(l, tl, W, H, FPS, st, work, aroll, a.preview)
        elif l['mode'] in cards.LAYOUT_MODES:
            f = cards.layout_clip(l, tl, W, H, FPS, st, work, aroll, a.preview)
        elif l['mode'] == 'inset':
            f = mfx.inset(aroll, l, W, H, FPS, st, work, a.preview)
        else:
            f = mfx.split(l, W, H, FPS, st, work, aroll, a.preview)
        idx = add_input(['-i', f])
        fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{l['t0']}/TB[ly{li}]")
        fc.append(f"{cur}[ly{li}]overlay=0:0:enable='between(t,{l['t0']},{l['t1']})':eof_action=pass[lyo{li}]")
        cur = f'[lyo{li}]'
    pip_streams = []
    for pi, l in enumerate(pips):
        p = pip_params(l, st)
        d = int(W * p['d']) // 2 * 2
        bw_ = int(p.get('border', 0) * unit(W, H))
        f = work / f'pip{pi}.mov'
        D = pip_clip(aroll, l['t0'], l['t1'], W, H, FPS, d, l.get('crop'), bw_, p.get('border_color', '#FFFFFF'), f, p.get('feather', 0))
        pip_streams.append((pi, l, p, D, f))

    # ---- B-roll
    # 背景压暗突出主体（bg_dim_focus）：卡片、截图浮在口播全屏上时，卡片下面先压暗一层。sync 同帧 0.3 秒压到六成亮；
    # pre 先暗后出，提前 0.4 秒压到四成亮。相接的几张卡片共用一层，不闪。高级感默认 sync，"dim": false 关掉。
    fs_wins = fullscreen_windows(tl)
    dims = []
    for i, b in enumerate(tl.get('broll', [])):
        mode = b.get('dim', 'sync' if style_name == 'premium' else False)
        if b.get('fit', 'cover') not in CARD_FITS or not mode:
            continue
        ov = sum(max(0.0, min(b['t1'], w1) - max(b['t0'], w0)) for w0, w1 in fs_wins)
        if ov < 0.5 * (b['t1'] - b['t0']):
            continue
        if dims and b['t0'] - dims[-1]['t1'] < 0.3:
            dims[-1]['t1'] = max(dims[-1]['t1'], b['t1'])
        else:
            dims.append({'t0': b['t0'], 't1': b['t1'], 'mode': mode, 'before': i})
    dim_at = {d['before']: d for d in dims}
    for i, b in enumerate(tl.get('broll', [])):
        if i in dim_at:
            dm = dim_at[i]
            lead, alpha_ = (0.4, 0.6) if dm['mode'] == 'pre' else (0.0, 0.4)
            s0 = max(0.0, dm['t0'] - lead)
            dd = dm['t1'] - s0
            fc.append(f"color=c=black:s={W}x{H}:r={FPS}:d={dd:.3f},format=rgba,colorchannelmixer=aa={alpha_},"
                      f"fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={max(0.0, dd - 0.2):.3f}:d=0.2:alpha=1,setpts=PTS-STARTPTS+{s0:.3f}/TB[dim{i}]")
            fc.append(f"{cur}[dim{i}]overlay=0:0:enable='between(t,{s0:.3f},{dm['t1']:.3f})':eof_action=pass[vd{i}]")
            cur = f'[vd{i}]'
        path, bw, bh, img, alpha = prep_broll(i, b, W, H, FPS, st, work, a.preview)
        dur = b['t1'] - b['t0']
        if img:
            idx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', path])
        else:
            idx = add_input(['-i', path])
        fit = b.get('fit', 'cover')
        full = fit in FULL_FITS
        x0 = f"{W * b.get('x', 0.5) - bw / 2:.1f}" if not full else '0'
        y0 = f"{H * b.get('y', 0.46 if fit == 'tilt' else 0.5) - bh / 2:.1f}" if not full else '0'
        t0, t1 = b['t0'], b['t1']
        enter = b.get('enter', 'none' if full or fit == 'pages' else ('rise_in' if fit == 'tilt' else 'fade'))  # 铺满类默认硬切，透视卡从下方升入
        exit_ = b.get('exit', 'none')
        x, y = x0, y0
        ease = f"(1-pow(1-clip((t-{t0})/0.35,0,1),3))"
        if enter == 'slide_up':
            y = f"{y0}+{int(H * 0.08)}*(1-{ease})"
        elif enter == 'slide_left':
            x = f"{x0}+{int(W * 0.25)}*(1-{ease})"
        elif enter == 'slide_right':
            x = f"{x0}-{int(W * 0.25)}*(1-{ease})"
        elif enter == 'rise_in':
            y = f"{y0}+{int(H * 0.12)}*(1-pow(1-clip((t-{t0})/0.5,0,1),3))"
        elif enter.startswith('move_'):   # 同向运动衔接：从反方向以同样速度移入，减速停下
            mv = f"(1-pow(1-clip((t-{t0})/0.4,0,1),3))"
            dx, dy = {'move_left': (0.35, 0), 'move_right': (-0.35, 0), 'move_up': (0, 0.25)}[enter]
            x, y = (f"{x0}+{int(W * dx)}*(1-{mv})", y) if dx else (x, f"{y0}+{int(H * dy)}*(1-{mv})")
        if exit_.startswith('move_'):     # 往同一方向加速移出，速度最快时切到下一张
            mo = f"pow(clip((t-{t1 - 0.4:.3f})/0.4,0,1),3)"
            dx, dy = {'move_left': (-0.35, 0), 'move_right': (0.35, 0), 'move_up': (0, -0.25)}[exit_]
            x, y = (f"({x})+{int(W * dx)}*{mo}", y) if dx else (x, f"({y})+{int(H * dy)}*{mo}")
        mo_ = b.get('motion', st.get('card_motion') if fit != 'pages' else None)
        if mo_ == 'rise' and not full:
            y = f"({y})-{int(H * (0.05 if fit == 'tilt' else 0.03))}*(t-{t0})/{max(dur, 0.1)}"
        elif mo_ == 'drift' and not full:   # 卡片漂移：一句里往右下漂 3% 宽、2% 高
            x, y = f"({x})+{int(W * 0.03)}*(t-{t0})/{max(dur, 0.1)}", f"({y})+{int(H * 0.02)}*(t-{t0})/{max(dur, 0.1)}"
        if is_landscape(W, H) and b.get('_side_box'):
            # 包括边框、投影和进出场在内的最终边界都限在同一侧，运动不穿过脸。
            l, top, r, bot = b['_side_box']
            x = f"clip({x},{W * l:.1f},{W * r - bw:.1f})"
            y = f"clip({y},{H * top:.1f},{H * bot - bh:.1f})"
        # 素材比区间短时定格最后一帧，避免后半段凭空消失
        chain = f"[{idx}:v]tpad=stop_mode=clone:stop_duration={b['t1'] - t0:.3f},setpts=PTS-STARTPTS+{t0}/TB,format=rgba"
        if enter.startswith('move_'):
            chain += f",fade=t=in:st={t0}:d=0.12:alpha=1"
        elif enter in ('fade', 'slide_up', 'slide_left', 'slide_right', 'rise_in'):
            chain += f",fade=t=in:st={t0}:d=0.25:alpha=1"
        if exit_ == 'fade':
            chain += f",fade=t=out:st={b['t1'] - 0.2}:d=0.2:alpha=1"
        elif exit_.startswith('move_'):
            chain += f",fade=t=out:st={b['t1'] - 0.12:.3f}:d=0.12:alpha=1"
        fc.append(chain + f"[b{i}]")
        fc.append(f"{cur}[b{i}]overlay=x='{x}':y='{y}':enable='between(t,{t0},{b['t1']})':eof_action=pass[v{i}]")
        cur = f'[v{i}]'
        if b.get('punch') and img:   # 冲焦：硬切到放大的关键数字，停一会儿再硬切回全图
            pu = b['punch']
            p0 = t0 + pu.get('t', 0.4)
            p1 = min(b['t1'], p0 + pu.get('dur', 2.0))
            pidx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', punch_image(i, b, W, H, st, work)])
            fc.append(f"[{pidx}:v]setpts=PTS-STARTPTS+{t0}/TB,format=rgba[pu{i}]")
            fc.append(f"{cur}[pu{i}]overlay=x='{x}':y='{y}':enable='between(t,{p0:.3f},{p1:.3f})':eof_action=pass[vp{i}]")
            cur = f'[vp{i}]'

    # ---- 贴纸、透明动画等叠加物
    for i, o in enumerate(tl.get('overlays', [])):
        src = to_png(o['src'], work) if is_image(o['src']) else o['src']
        dur = o['t1'] - o['t0']
        ow = int(1080 * unit(W, H) * o.get('w', 0.3)) // 2 * 2
        if is_image(src):
            idx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', src])
        else:
            idx = add_input(['-stream_loop', '-1', '-t', f'{dur:.3f}', '-i', src])
        fc.append(f"[{idx}:v]scale={ow}:-2,setpts=PTS-STARTPTS+{o['t0']}/TB,format=rgba,fade=t=in:st={o['t0']}:d=0.2:alpha=1[o{i}]")
        fc.append(f"{cur}[o{i}]overlay=x='{W * o.get('x', 0.5)}-w/2':y='{H * o.get('y', 0.5)}-h/2':enable='between(t,{o['t0']},{o['t1']})'"
                  f":eof_action=pass[ov{i}]")
        cur = f'[ov{i}]'

    # ---- 圆形人像小窗（压在 B-roll 上面）
    # ---- 定格暂停：画面停在这一帧、稍微压暗，头像放大到画面中间说这一句（原片 2:51 的手法）
    freezes = tl.get('freezes', [])
    for fi, fz in enumerate(freezes):
        f0, f1 = fz['t0'], fz['t1']
        fc.append(f"{cur}split[fza{fi}][fzb{fi}]")
        fc.append(f"[fzb{fi}]trim=start={f0:.3f}:duration={1 / FPS:.4f},setpts=PTS-STARTPTS,loop=loop={int((f1 - f0) * FPS) + 2}:size=1,"
                  f"setpts=N/{FPS}/TB+{f0:.3f}/TB,eq=saturation=0.7:brightness=-0.06[fzi{fi}]")
        fc.append(f"[fza{fi}][fzi{fi}]overlay=0:0:enable='between(t,{f0:.3f},{f1:.3f})':eof_action=pass[fzo{fi}]")
        cur = f'[fzo{fi}]'
    not_frozen = ''.join(f"*not(between(t,{fz['t0']:.3f},{fz['t1']:.3f}))" for fz in freezes)

    # 圆形蒙版收缩（pip_shrink_circle）：压在 B-roll 上面；bg 不是 none 时圆外整屏盖住
    for ci, l in enumerate(circles):
        f = mfx.circle(aroll, l, W, H, FPS, st, work, a.preview)
        idx = add_input(['-i', f])
        fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{l['t0']}/TB,format=rgba[ci{ci}]")
        fc.append(f"{cur}[ci{ci}]overlay=0:0:enable='between(t,{l['t0']},{l['t1']})':eof_action=pass[cio{ci}]")
        cur = f'[cio{ci}]'
    hide = pip_hide_ranges(tl, auto_transitions(tl, st))
    for pi, l, p, D, f in pip_streams:
        idx = add_input(['-i', str(f)])
        cx, cy = W * p['x'], H * p['y']
        off = not_frozen + (''.join(f"*not(between(t,{h0:.3f},{h1:.3f}))" for h0, h1 in hide) if l.get('hide_on_peak', True) else '')
        en = f"between(t,{l['t0']},{l['t1']}){off}"
        if p.get('shadow'):   # 描边加投影版：小窗下面垫一层模糊黑圆
            from PIL import Image, ImageDraw, ImageFilter
            shp = work / f'pip_shadow{pi}.png'
            pad = int(D * 0.18)
            im = Image.new('RGBA', (D + 2 * pad, D + 2 * pad), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse([pad, pad + pad // 4, pad + D, pad + D + pad // 4], fill=(0, 0, 0, 150))
            im.filter(ImageFilter.GaussianBlur(pad / 2.5)).save(shp)
            sidx = add_input(['-loop', '1', '-framerate', str(FPS), '-t', f"{l['t1'] - l['t0']:.3f}", '-i', str(shp)])
            fc.append(f"[{sidx}:v]setpts=PTS-STARTPTS+{l['t0']}/TB,format=rgba[pps{pi}]")
            fc.append(f"{cur}[pps{pi}]overlay={cx - D / 2 - pad:.0f}:{cy - D / 2 - pad:.0f}:enable='{en}':eof_action=pass[ppso{pi}]")
            cur = f'[ppso{pi}]'
        fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{l['t0']}/TB,format=rgba,fade=t=in:st={l['t0']}:d=0.2:alpha=1[pip{pi}]")
        fc.append(f"{cur}[pip{pi}]overlay={cx - D / 2:.0f}:{cy - D / 2:.0f}:enable='{en}':eof_action=pass[pp{pi}]")
        cur = f'[pp{pi}]'
    for fi, fz in enumerate(freezes):   # 定格时的大头像
        d = int(1080 * unit(W, H) * fz.get('d', 0.5)) // 2 * 2
        bw_ = int(st['pip'].get('border', 4) * unit(W, H))
        ff = work / f'freeze_head{fi}.mov'
        D = pip_clip(aroll, fz['t0'], fz['t1'], W, H, FPS, d, fz.get('crop'), bw_, st['pip'].get('border_color', '#FFFFFF'), ff)
        idx = add_input(['-i', str(ff)])
        fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{fz['t0']}/TB,format=rgba,fade=t=in:st={fz['t0']}:d=0.12:alpha=1[fzh{fi}]")
        fc.append(f"{cur}[fzh{fi}]overlay={W / 2 - D / 2:.0f}:{H * fz.get('y', 0.45) - D / 2:.0f}:"
                  f"enable='between(t,{fz['t0']:.3f},{fz['t1']:.3f})':eof_action=pass[fzho{fi}]")
        cur = f'[fzho{fi}]'

    # ---- 字在人后（behind_text）：先画 behind 大字，再盖上抠好的人像。人像按大字的时间段自动抠（person_matte 缓存），
    # 手写在 mattes 里的现成人像片段优先；这一段落在抠像换底版式里时，人像带上同样的描边
    mattes = list(tl.get('mattes', []))
    behind = [x for x in tl.get('titles', []) if x.get('behind')]
    if behind:
        import matte
    for bi, t in enumerate(behind):
        if 'color' not in t:
            t['_luma'] = region_luma(aroll, (t['t0'] + t['t1']) / 2, t.get('x', 0.5), t.get('y', 0.32), 0.9, 0.12)
        a_ref = next(matte.cutouts(aroll, t['t0'] + min(0.3, (t['t1'] - t['t0']) / 2), 1 / FPS, W, H, FPS))
        t['_head_top'] = matte.top_of(a_ref)
        for it in layout_title(t, st, W, H):   # 字被人挡住超过四成就看不清了：提醒换位置或缩短
            if 'text' in it and not it.get('front'):
                tw, th = text_w(it['text'], it['size'], it.get('condense', 100)), it['size'] * 0.8
                box = a_ref[max(0, int(it['y'] - th / 2)):int(it['y'] + th / 2), max(0, int(it['x'] - tw / 2)):int(it['x'] + tw / 2)]
                if box.size and box.mean() > 0.4:
                    print(f"人压字：{t['t0']:.1f} 秒「{it['text']}」被人挡住 {box.mean():.0%}，超过四成会看不清，挪一下 y 或换短词")
        if not any(m['t0'] <= t['t0'] + 0.01 and t['t1'] <= m['t1'] + 0.01 for m in mattes):
            look = next((l.get('outline') for l in layout if l['mode'] == 'matte' and l['t0'] <= t['t0'] < l['t1']), None)
            mattes.append({'t0': t['t0'], 't1': t['t1'],
                           'src': matte.person_clip(aroll, t['t0'], t['t1'], W, H, FPS, str(work / f'person{bi}.mov'), look)})
    if mattes and behind:
        ass_b = work / 'behind.ass'
        ass_b.write_text(build_ass(tl, st, W, H, fonts, pip_ranges, part='behind'), encoding='utf-8')
        fc.append(f"{cur}ass='{ff_path(ass_b)}':fontsdir='{ff_path(fontsdir)}'[vb]")
        cur = '[vb]'
    for mi, m in enumerate(mattes):
        idx = add_input(['-i', m['src']])
        fc.append(f"[{idx}:v]scale={W}:{H},setpts=PTS-STARTPTS+{m['t0']}/TB,format=rgba[mt{mi}]")
        fc.append(f"{cur}[mt{mi}]overlay=0:0:enable='between(t,{m['t0']},{m['t1']})':eof_action=pass[mo{mi}]")
        cur = f'[mo{mi}]'

    # ---- 逐帧合成的大字（数据卡、环形图、雾面章节、章节标题页，cards.py）：压在字幕下面
    plain = [(l['t0'], l['t1']) for l in layout if l['mode'] in ('aside', 'hidden', 'bg')]
    for gi, t in enumerate(sorted((x for x in tl.get('titles', []) if x.get('layout') in GRAPHIC_LAYOUTS), key=lambda x: x['t0'])):   # 后出现的压在上面
        t['_plain'] = in_ranges((t['t0'] + t['t1']) / 2, plain)   # 背景已经是虚化或黑底时不再压暗
        f = cards.title_clip(t, W, H, FPS, st, work, aroll, a.preview)
        idx = add_input(['-i', f])
        fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{t['t0']}/TB,format=rgba[gt{gi}]")
        fc.append(f"{cur}[gt{gi}]overlay=0:0:enable='between(t,{t['t0']},{t['t1']})':eof_action=pass[gto{gi}]")
        cur = f'[gto{gi}]'

    # ---- 整屏特效（第 8 批）：调色、暗角、扫描线、网点、放大镜、遮挡、压暗聚光框、人脸特效压在字幕下面
    cur = effects.apply(fc, cur, tl, 'pic', add_input, W, H, FPS, work, aroll, a.preview)
    cur = structure.apply(fc, cur, tl, add_input, W, H, FPS, work, DUR)   # 常驻层：角落要点编号、系列名水印、进度条（第 10 批）

    # ---- 字幕与大字
    ass = work / 'subs.ass'

    ass.write_text(build_ass(tl, st, W, H, fonts, pip_ranges), encoding='utf-8')
    fc.append(f"{cur}ass='{ff_path(ass)}':fontsdir='{ff_path(fontsdir)}'[vsub]")
    cur = '[vsub]'
    # 震动、裂屏、宽银幕黑边、全剧终连字幕一起
    cur = effects.apply(fc, cur, tl, 'screen', add_input, W, H, FPS, work, aroll, a.preview)

    # ---- 章节效果转场（整屏，连字一起）
    for ti, tr in enumerate(auto_transitions(tl, st)):
        nc = effects.transition(fc, cur, tr, ti, add_input, W, H, FPS, work)   # 故障、甩切、光圈、漏光、撕纸、遮挡扫屏
        if nc:
            cur = nc
            continue
        kind = tr['type']
        a0, d = tr_window(tr)
        if kind in ('flash', 'dip_black'):
            src = f"color=c={'white' if kind == 'flash' else 'black'}:s={W}x{H}:r={FPS}:d={d:.3f},format=rgba"
            fc.append(f"{src},fade=t=in:st=0:d={d * 0.3:.3f}:alpha=1,fade=t=out:st={d * 0.4:.3f}:d={d * 0.6:.3f}:alpha=1,"
                      f"setpts=PTS-STARTPTS+{a0:.3f}/TB[tr{ti}]")
            fc.append(f"{cur}[tr{ti}]overlay=0:0:enable='between(t,{a0:.3f},{a0 + d:.3f})':eof_action=pass[vt{ti}]")
        elif kind == 'blur_swipe':
            fc.append(f"{cur}dblur=angle=90:radius=60:enable='between(t,{a0:.3f},{a0 + d:.3f})'[vt{ti}]")
        else:
            continue
        cur = f'[vt{ti}]'
    fc.append(f"{cur}format=yuv420p[vout]")

    # ---- 声音
    au = tl.get('audio', {})
    vo = au.get('voice', {})
    lufs = vo.get('lufs', st['voice_lufs'])
    apad = f'apad=pad_dur={TAIL:.3f},' if TAIL else ''
    if vo.get('raw'):   # 原声不做任何处理（对比用）
        vsrc = f"[0:a]{apad}aformat=channel_layouts=stereo:sample_rates=48000"
    elif vo.get('cleanup', True):   # 原声降噪统一响度（voice_cleanup_loudness）：先单独处理成 wav，结果缓存
        vwav, vrep = audiomix.clean_voice(aroll, lufs, vo)
        print(f"人声：底噪 {vrep['noise_floor']} dB，处理后 {vrep['lufs']} LUFS，峰值 {vrep['tp']} dBFS")
        vwav = audiomix.voice_fx(vwav, tl.get('voice_fx'))   # 扩音器、哔声消音这几秒的人声
        vin = add_input(['-i', str(vwav)])
        vsrc = f"[{vin}:a]{apad}aformat=channel_layouts=stereo:sample_rates=48000"
    else:
        vsrc = (f"[0:a]{apad}highpass=f=70,loudnorm=I={lufs}:TP=-1.5:LRA=11,"
                f"aformat=channel_layouts=stereo:sample_rates=48000")
    mix = []
    plan = tl.get('_music') or {'bgm': [], 'env': [], 'dips': []}
    bgms = plan['bgm']
    fc.append(f"{vsrc},asplit=2[voice][vkey]" if bgms else f"{vsrc}[voice]")
    mix.append('[voice]')
    sfx = all_sfx(tl, st)
    heavy = [s_['event'] for s_ in sfx if SOUNDS.get(s_.get('sound'), {}).get('heavy') and 'event' in s_]
    bl = []
    for i, m in enumerate(bgms):
        idx = add_input(['-stream_loop', '-1', '-i', m['src']])
        d = m['t1'] - m['t0']
        db = bgm_gain_db(m, st)
        fi, fo = m.get('fade_in', 0.5), m.get('fade_out', 1.0)
        ms = int(m['t0'] * 1000)
        fc.append(f"[{idx}:a]atrim=start={m.get('src_in', 0)}:duration={d},asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo:sample_rates=48000,"
                  f"volume={db}dB,afade=t=in:d={fi},afade=t=out:st={max(0, d - fo)}:d={fo}{audiomix.env_expr(m, plan, heavy)},adelay={ms}|{ms}[bgm{i}]")
        bl.append(f'[bgm{i}]')
    if bl:
        if len(bl) > 1:
            fc.append(''.join(bl) + f"amix=inputs={len(bl)}:normalize=0[bgmall]")
        else:
            fc.append(f"{bl[0]}anull[bgmall]")
        if any(m.get('duck', True) for m in bgms):   # 人一说话配乐自动让开：阈值 -30 dB、压缩比 6
            fc.append("[bgmall][vkey]sidechaincompress=threshold=0.0316:ratio=6:attack=15:release=400:makeup=1[bgmd]")
            mix.append('[bgmd]')
        else:
            fc.append('[vkey]anullsink')
            mix.append('[bgmall]')
    sl = []
    for i, s_ in enumerate(sfx):
        idx = add_input(['-i', s_['src']])
        ms = int(s_['t'] * 1000)
        pitch = f"asetrate={48000 * s_['rate']:.0f},aresample=48000," if s_.get('rate') else ''   # 升调串
        cut = f"atrim=0:{s_['dur']:.3f},afade=t=out:st={max(0.0, s_['dur'] - 0.3):.3f}:d=0.3," if s_.get('dur') else ''
        fc.append(f"[{idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,{pitch}{cut}volume={sfx_gain_db(s_, st)}dB,adelay={ms}|{ms}[sfx{i}]")
        sl.append(f'[sfx{i}]')
    if sl:
        fc.append(''.join(sl) + (f"amix=inputs={len(sl)}:normalize=0[sfxall]" if len(sl) > 1 else 'anull[sfxall]'))
        mix.append('[sfxall]')
    stems = []
    if a.stems:   # 分轨：混音前各复制一份
        for k, lab in enumerate(mix):
            name = {'[voice]': 'voice', '[sfxall]': 'sfx'}.get(lab, 'music')
            fc.append(f"{lab}asplit=2[mx{k}][sp{k}]")
            fc.append(f"[sp{k}]apad=whole_dur={DUR:.3f}[st{k}]")   # 分轨补齐到成片长度，时间轴对得上
            mix[k] = f'[mx{k}]'
            stems += ['-map', f'[st{k}]', '-t', f'{DUR:.3f}', '-c:a', 'pcm_s16le', str(Path(a.out).with_suffix(f'.{name}.wav'))]
    if len(mix) > 1:
        fc.append(''.join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.8:attack=1:release=60:level=disabled[aout]")
    else:
        fc.append(f'{mix[0]}alimiter=limit=0.8:attack=1:release=60:level=disabled[aout]')

    (work / 'graph.txt').write_text(';\n'.join(fc), encoding='utf-8')
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    venc = ['-c:v', 'libx264', '-preset', 'ultrafast' if a.preview else 'medium', '-crf', '30' if a.preview else '18']
    # ffmpeg 7 换成 -/filter_complex 读文件，9 删掉了 -filter_complex_script；没版本号的 git 构建当新版
    v = re.search(r'version n?(\d+)\.', sh(['ffmpeg', '-version']).stdout)
    graph = ['-filter_complex_script' if v and int(v.group(1)) < 7 else '-/filter_complex', str(work / 'graph.txt')]
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs, *graph, '-map', '[vout]', '-map', '[aout]',
           *venc, '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', '-t', f'{DUR:.3f}', '-movflags', '+faststart', a.out, *stems]
    sh(cmd)
    effects.splice_inserts(a.out, tl, W, H, FPS, a.preview)   # 插入影视梗片段：成片在插入点硬切进去，片子变长
    if not a.keep:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    print('成片：', a.out)


if __name__ == '__main__':
    main()
