"""画面特效与转场（手法库第 8 批）。

整屏特效：timeline 顶层写 "fx": [{t0, t1, type, variant, ...}]，种类和压在哪一层见 kvlib.FX。render.py 在两处调 apply：
pic 层压在常驻字幕下面（只改画面），screen 层连字幕一起（震动、裂屏、黑边、全剧终）。
- bw 变黑白、shake 震动、crack 裂开了、magnifier 放大镜、the_end 全剧终、blur 模糊遮挡（screen_reaction_fx）
- spotlight 聚光灯暗角（spotlight_vignette）、crt 扫描线老电视（crt_scanline）、halftone 网点丝印（halftone_texture）
- grade 调色变化（color_grade_shift）、letterbox 宽银幕黑边（letterbox_bars）、dimbox 压暗聚光框游走（dim_spotlight_box）
- face 人脸情绪特效（face_effect_emotion）：剪映人物特效名，成片里用抠像放大头、头边贴 3D 表情和手写符号近似，草稿里放剪映真特效

效果转场（kvlib.TRANSITIONS）：glitch RGB 故障闪切、whip 动态模糊甩切、iris 圆形光圈、light_leak 漏光扫过、tear 撕纸揭开、
occlude 主题物遮挡扫屏，transition 按种类往滤镜图里接；闪白、压黑、竖向模糊还在 render.py 里。

逐帧大字（titles 的 layout，cards.title_clip 转过来）：boom 放射爆炸底（radial_burst_bg）、persist 字不动底在换（text_persist_bg_swap）、
glitchswap 文字故障换字（rgb_glitch 的 text_swap）。
版式（layout 的 mode）：morph 窗口按节拍变形（window_shape_morph）。
插片：timeline 顶层 "inserts"，成片渲完后在口播里硬切插入用户给的影视梗片段（meme_clip_insert），片子变长。
白场载体接力转场（panel_carrier_transition）在 cards.fog 里：enter cover、exit door、shapes 换形旋转。
尺寸按 短边 1080 的像素值乘 S。
"""
import json
import os
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kvlib import unit, is_landscape, safe_zones, FACE_FX, FX, hex_rgba, is_image, probe, to_png, tr_window
from keytext import BRUSH, HAND, HEAVY, _clamp, blur, eback, fade_out, fit_word, frames, icon_png, put, rough, scale, vblur, with_shadow, word
from annot import side_center, side_fit
from motion import Writer, ease, keyed, over, read, resize, rotate_rgba, trim

LAYOUTS = ('boom', 'persist', 'glitchswap')
LAYOUT_MODES = ('morph',)


def _even(x):
    return int(x) // 2 * 2


def _png_input(add_input, path, d, FPS):
    return add_input(['-loop', '1', '-framerate', str(FPS), '-t', f'{d:.3f}', '-i', str(path)])


def _overlay_clip(fc, cur, add_input, path, t0, t1, tag, fades=None, x=0, y=0):
    """把一段整屏透明 .mov（时间从 0 起）叠到 t0~t1。"""
    idx = add_input(['-i', str(path)])
    fc.append(f"[{idx}:v]setpts=PTS-STARTPTS+{t0:.3f}/TB,format=rgba{fades or ''}[{tag}v]")
    fc.append(f"{cur}[{tag}v]overlay={x}:{y}:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


def _overlay_png(fc, cur, add_input, path, t0, t1, tag, FPS, fin=0.0, fout=0.0, x=0, y=0):
    d = t1 - t0
    idx = _png_input(add_input, path, d, FPS)
    fades = (f",fade=t=in:st=0:d={fin:.3f}:alpha=1" if fin else '') + (f",fade=t=out:st={max(0.0, d - fout):.3f}:d={fout:.3f}:alpha=1" if fout else '')
    fc.append(f"[{idx}:v]format=rgba{fades},setpts=PTS-STARTPTS+{t0:.3f}/TB[{tag}v]")
    fc.append(f"{cur}[{tag}v]overlay={x}:{y}:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


def _branch(fc, cur, tag, t0, t1, chain):
    """从当前画面分出 t0~t1 这一小段做 chain（裁切、缩放这类不支持按时间开关的滤镜），时间挪回原处。返回 (主流, 支流)。"""
    fc.append(f"{cur}split[{tag}m][{tag}s]")
    fc.append(f"[{tag}s]trim=start={t0:.3f}:end={t1:.3f},setpts=PTS-STARTPTS,{chain},setpts=PTS+{t0:.3f}/TB[{tag}b]")
    return f'[{tag}m]', f'[{tag}b]'


# ---------------------------------------------------------------- 整屏特效
def prepare(tl, st):
    """渲染前把特效需要的附带动作补进时间线：聚光加推近、段落质感的推近写进 zoom，人脸特效里带震动的补一段 shake，
    白场载体的开门、换形补声音。可以重复调用。"""
    from props import prepare_overlays
    prepare_overlays(tl)
    for f in tl.get('fx', []):
        if f.get('type') not in FX:
            raise SystemExit(f"fx「{f.get('type')}」不存在，可选：{'、'.join(FX)}")
        if f.get('_prep'):
            continue
        f['_prep'] = True
        d = f['t1'] - f['t0']
        if f['type'] == 'spotlight' and f.get('variant', 'push') == 'push' and f.get('push', True):
            tl.setdefault('zoom', []).append({'t0': f['t0'], 't1': f['t1'], 'from': 1.0, 'to': 1.12, 'ease': min(1.5, d)})
        if f['type'] == 'crt' and f.get('variant') == 'section' and f.get('push', True):
            tl.setdefault('zoom', []).append({'t0': f['t0'], 't1': f['t1'], 'from': 1.0, 'to': 1.06, 'ease': d})
        if f['type'] == 'face':
            names = f.get('names') or []
            bad = [n for n in names if n not in FACE_FX]
            if bad:
                raise SystemExit(f"人脸特效没有「{'、'.join(bad)}」，可选：{'、'.join(FACE_FX)}")
            if any(FACE_FX[n].get('shake') for n in names):
                tl['fx'].append({'t0': f['t0'], 't1': min(f['t1'], f['t0'] + 0.4), 'type': 'shake', 'sfx': False, '_prep': True, '_from': 'face'})
    fogs = sorted((t for t in tl.get('titles', []) if t.get('layout') == 'fog'), key=lambda t: t['t0'])
    for p_, q_ in zip(fogs, fogs[1:]):   # 底部面板后面紧接放大盖屏：面板不淡出，接力给下一页
        if p_.get('variant', 'panel') == 'panel' and q_.get('enter') == 'cover' and abs(q_['t0'] - p_['t1']) < 0.15:
            p_['_relay'] = True
    for t in tl.get('titles', []):
        if t.get('layout') != 'fog' or t.get('_prep'):
            continue
        t['_prep'] = True
        if t.get('exit') == 'door':
            tl.setdefault('sounds', []).append({'t': round(t['t1'] - 0.5, 3), 'type': 'door', 'prio': 1})
        if t.get('shapes'):
            tl.setdefault('sounds', []).append({'t': round(t['t0'] + t.get('shape_at', 1.0), 3), 'type': 'whoosh', 'prio': 1})


def apply(fc, cur, tl, layer, add_input, W, H, FPS, work, aroll, preview=False):
    """把这一层的整屏特效接进滤镜图，返回新的当前画面标签。"""
    S = unit(W, H)
    items = sorted((f for f in tl.get('fx', []) if FX[f['type']]['layer'] == layer), key=lambda f: f['t0'])
    for k, f in enumerate(items):
        kind, v = f['type'], f.get('variant')
        t0, t1 = float(f['t0']), float(f['t1'])
        d = t1 - t0
        tag = f'fx{layer}{k}'
        en = f"between(t,{t0:.3f},{t1:.3f})"
        if kind == 'bw':   # 前后各 0.15 秒渐变成黑白
            p = f"clip((t-{t0:.3f})/0.15,0,1)*clip(({t1:.3f}-t)/0.15,0,1)"
            fc.append(f"{cur}hue=s='1-{p}':enable='{en}'[{tag}]")
            cur = f'[{tag}]'
        elif kind == 'grade' and (v or 'desat_cool') == 'desat_cool':
            fc.append(f"{cur}eq=saturation=0.62:contrast=1.1:brightness=-0.03:enable='{en}',"
                      f"colorbalance=rs=-0.05:gs=0.02:bs=0.07:rm=-0.03:bm=0.04:enable='{en}',vignette=angle=PI/5:enable='{en}'[{tag}]")
            cur = f'[{tag}]'
        elif kind == 'grade':
            cur = _band_recolor(fc, cur, f, tag, W, H, FPS)
        elif kind == 'spotlight':
            png = _vignette_png(W, H, work, f.get('y', 0.40), 0.9 if v != 'drama' else 0.95)
            cur = _overlay_png(fc, cur, add_input, png, t0, t1, tag, FPS, fin=0.3, fout=0.3)
            if v == 'drama':   # 戏剧聚焦：再叠荧幕噪点
                fc.append(f"{cur}noise=alls=22:allf=t:enable='{en}'[{tag}n]")
                cur = f'[{tag}n]'
        elif kind == 'crt':
            if v == 'section':   # 段落质感：桶形弯曲加强暗角
                fc.append(f"{cur}lenscorrection=k1=0.06:k2=0.02:enable='{en}'[{tag}l]")
                cur = f'[{tag}l]'
            png = _crt_png(W, H, work, strong=v == 'section')
            cur = _overlay_png(fc, cur, add_input, png, t0, t1, tag, FPS, fin=0.1, fout=0.1)
        elif kind == 'halftone':
            if v == 'bg_grain':
                import backgrounds
                png = backgrounds.halftone(W, H, work, gap=7, alpha=0.30)
                cur = _overlay_png(fc, cur, add_input, png, t0, t1, tag, FPS, fin=0.3, fout=0.3)
            else:
                mov = _screenprint(f, W, H, FPS, work, aroll, f'{tag}.mov')
                cur = _overlay_clip(fc, cur, add_input, mov, t0, t1, tag)
        elif kind == 'blur':
            x, y, w, h = _box_px(f.get('box', [0.2, 0.4, 0.6, 0.12]), W, H)
            blur_ = 'boxblur=26:3'
            if is_landscape(W, H):
                # 矮遮挡条的色度平面更矮，不能照搬亮度半径。
                r = min(round(26 * S), min(w, h) // 2)
                blur_ = f'boxblur={r}:3:{min(r, min(w, h) // 4)}:3'
            m, b = _branch(fc, cur, tag, t0, t1, f"crop={w}:{h}:{x}:{y},{blur_}")
            fc.append(f"{m}{b}overlay={x}:{y}:enable='{en}':eof_action=pass[{tag}]")
            cur = f'[{tag}]'
        elif kind == 'magnifier' and v == 'reach':   # 手柄从画外伸进来（一星第 15 批）
            import props
            cur = props.magnifier_reach(fc, cur, f, tag, add_input, W, H, FPS, work)
        elif kind == 'magnifier':
            cur = _magnifier(fc, cur, f, tag, add_input, W, H, FPS, work)
        elif kind == 'dimbox':
            mov = _dimbox(f, W, H, FPS, work, aroll, f'{work}/{tag}.mov')
            cur = _overlay_clip(fc, cur, add_input, mov, t0, t1, tag)
        elif kind == 'face':
            mov = _face(f, W, H, FPS, work, aroll, f'{work}/{tag}.mov')
            cur = _overlay_clip(fc, cur, add_input, mov, t0, t1, tag)
        elif kind == 'shake':
            cur = _shake(fc, cur, tag, t0, t1, W, H, f.get('amp', 0.012))
        elif kind == 'crack':
            cur = _shake(fc, cur, tag + 's', t0, min(t1, t0 + 0.35), W, H, 0.014)
            png = _crack_png(W, H, work, f.get('at', [0.74, 0.2]), int(t0 * 100))
            cur = _overlay_png(fc, cur, add_input, png, t0, t1, tag, FPS, fin=0.06, fout=0.2)
        elif kind == 'letterbox':
            mov = _letterbox(f, W, H, FPS, f'{work}/{tag}.mov')
            cur = _overlay_clip(fc, cur, add_input, mov, t0, t1, tag)
        elif kind == 'tilt':
            import vfx
            cur = vfx.tilt_fx(fc, cur, f, tag, W, H)
        elif kind == 'the_end':
            mov = _the_end(f, W, H, FPS, f'{work}/{tag}.mov')
            cur = _overlay_clip(fc, cur, add_input, mov, t0, t1, tag)
    return cur


def _box_px(box, W, H):
    x, y, w, h = box
    return _even(x * W), _even(y * H), max(2, _even(w * W)), max(2, _even(h * H))


def _vignette_png(W, H, work, cy=0.40, dark=0.9):
    """聚光灯：中间约 0.6 宽的椭圆亮，往外压到八九成黑。"""
    out = Path(work) / f'spot_{cy}_{dark}.png'
    if not out.exists():
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        e = np.hypot((xx - W * 0.5) / (W * 0.40), (yy - H * cy) / (H * 0.30))
        a = np.clip((e - 0.8) / 0.75, 0, 1) ** 1.3 * dark
        rgba = np.zeros((H, W, 4), np.uint8)
        rgba[..., 3] = (a * 255).astype(np.uint8)
        Image.fromarray(rgba, 'RGBA').save(out)
    return out


def _crt_png(W, H, work, strong=False):
    """扫描线老电视：每 4 像素一条细黑线，四角暗角；段落质感版线更重、暗角更强。"""
    out = Path(work) / f"crt_{'s' if strong else 'e'}.png"
    if not out.exists():
        S = unit(W, H)
        pitch = max(3, round(4 * S))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        line = ((yy.astype(int) % pitch) < max(1, round(1.4 * S))).astype(np.float32) * (0.26 if strong else 0.2)
        e = np.hypot((xx - W / 2) / (W * 0.62), (yy - H / 2) / (H * 0.62))
        vig = np.clip((e - 0.55) / 0.6, 0, 1) ** 1.4 * (0.85 if strong else 0.55)
        a = 1 - (1 - line) * (1 - vig)
        rgba = np.zeros((H, W, 4), np.uint8)
        rgba[..., 1] = 8   # 线带一点点绿，像荧光屏
        rgba[..., 3] = (a * 255).astype(np.uint8)
        Image.fromarray(rgba, 'RGBA').save(out)
    return out


def _band_recolor(fc, cur, f, tag, W, H, FPS):
    """黑白加色块扫：整段先变黑白，几条红、绿、橙横色块依次从脸部往下扫过，色块里恢复原色再染一层颜色。"""
    t0, t1 = float(f['t0']), float(f['t1'])
    d = t1 - t0
    cols = f.get('colors') or ['#C8102E', '#2E9E4F', '#E8781E']
    bh = _even(H * 0.12)
    sw, gap = f.get('sweep_s', 0.6), f.get('gap_s', 0.35)
    y0, y1 = H * 0.10, H * 0.62
    en = f"between(t,{t0:.3f},{t1:.3f})"
    fc.append(f"{cur}split[{tag}a][{tag}b]")
    fc.append(f"[{tag}a]hue=s=0:enable='{en}'[{tag}g]")
    fc.append(f"[{tag}b]trim=start={t0:.3f}:end={t1:.3f},setpts=PTS-STARTPTS,split={len(cols)}" + ''.join(f'[{tag}c{k}]' for k in range(len(cols))))
    cur = f'[{tag}g]'
    for k, col in enumerate(cols):
        s0 = 0.15 + k * gap
        if s0 >= d:
            fc.append(f"[{tag}c{k}]nullsink")
            continue
        yl = f"trunc(({y0:.1f}+{y1 - y0:.1f}*clip((t-{s0:.3f})/{sw:.3f},0,1))/2)*2"
        yg = f"trunc(({y0:.1f}+{y1 - y0:.1f}*clip((t-{t0 + s0:.3f})/{sw:.3f},0,1))/2)*2"
        win = f"between(t,{t0 + s0:.3f},{min(t1, t0 + s0 + sw + 0.05):.3f})"
        fc.append(f"[{tag}c{k}]crop={W}:{bh}:0:'{yl}',setpts=PTS+{t0:.3f}/TB[{tag}r{k}]")
        fc.append(f"{cur}[{tag}r{k}]overlay=0:'{yg}':enable='{win}':eof_action=pass[{tag}o{k}]")
        r, g, b, _ = hex_rgba(col)
        fc.append(f"color=c=0x{r:02X}{g:02X}{b:02X}@0.32:s={W}x{bh}:r={FPS}:d={d:.3f},format=rgba,setpts=PTS+{t0:.3f}/TB[{tag}t{k}]")
        fc.append(f"[{tag}o{k}][{tag}t{k}]overlay=0:'{yg}':enable='{win}':eof_action=pass[{tag}p{k}]")
        cur = f'[{tag}p{k}]'
    return cur


def _magnifier(fc, cur, f, tag, add_input, W, H, FPS, work):
    """放大镜：at 那一点为中心，半径 r（画面宽的比例）的圆里放大 zoom 倍，带镜框和手柄，0.15 秒弹出。"""
    S = unit(W, H)
    t0, t1 = float(f['t0']), float(f['t1'])
    cx, cy = f.get('at', [0.5, 0.5])
    cx, cy = cx * W, cy * H
    R = _even(W * f.get('r', 0.17))
    if is_landscape(W, H):
        R = max(2, _even(min(R, H * 0.18, cx - W * 0.05, W * 0.95 - cx, cy - H * 0.05, (H * 0.8 - cy) / 1.7)))
    z = f.get('zoom', 2.0)
    sw = _even(2 * R / z)
    if is_landscape(W, H):
        sw = max(2, min(sw, _even(min(W, H))))
    sx, sy = int(min(max(0, cx - sw / 2), W - sw)), int(min(max(0, cy - sw / 2), H - sw))
    m, b = _branch(fc, cur, tag, t0, t1, f"crop={sw}:{sw}:{sx}:{sy},scale={2 * R}:{2 * R},format=rgba")
    mask = Path(work) / f'lens_mask_{R}.png'
    if not mask.exists():
        im = Image.new('L', (2 * R * 2, 2 * R * 2), 0)
        ImageDraw.Draw(im).ellipse([4, 4, 4 * R - 4, 4 * R - 4], fill=255)
        im.resize((2 * R, 2 * R), Image.LANCZOS).save(mask)
    mi = _png_input(add_input, mask, t1 - t0, FPS)
    fc.append(f"[{mi}:v]format=gray,setpts=PTS-STARTPTS+{t0:.3f}/TB[{tag}k]")
    fc.append(f"{b}[{tag}k]alphamerge,fade=t=in:st={t0:.3f}:d=0.15:alpha=1[{tag}l]")
    fc.append(f"{m}[{tag}l]overlay={int(cx - R)}:{int(cy - R)}:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}x]")
    rim = Path(work) / f'lens_rim_{R}.png'
    if not rim.exists():   # 镜框：深灰外圈、白色内圈，右下 45 度一根手柄
        pad = int(R * 0.9)
        k = 2
        D = (2 * R + 2 * pad) * k
        im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        c = D / 2
        ang = np.pi / 4
        hx0, hy0 = c + np.cos(ang) * R * k * 1.02, c + np.sin(ang) * R * k * 1.02
        hx1, hy1 = c + np.cos(ang) * (R + pad * 0.95) * k, c + np.sin(ang) * (R + pad * 0.95) * k
        dr.line([(hx0, hy0), (hx1, hy1)], fill=(40, 40, 46, 255), width=int(R * 0.22 * k))
        dr.line([(hx0, hy0), (hx1, hy1)], fill=(92, 92, 102, 255), width=int(R * 0.12 * k))
        rr = R * k
        dr.ellipse([c - rr - 14 * S * k, c - rr - 14 * S * k, c + rr + 14 * S * k, c + rr + 14 * S * k], outline=(40, 40, 46, 255), width=int(16 * S * k))
        dr.ellipse([c - rr - 3 * S * k, c - rr - 3 * S * k, c + rr + 3 * S * k, c + rr + 3 * S * k], outline=(255, 255, 255, 230), width=int(4 * S * k))
        a = np.array(im.resize((D // k, D // k), Image.LANCZOS))
        Image.fromarray(with_shadow(a, 8 * S, 0.45, dy=int(6 * S))).save(rim)
    rw = Image.open(rim).size[0]
    ri = _png_input(add_input, rim, t1 - t0, FPS)
    fc.append(f"[{ri}:v]format=rgba,fade=t=in:st=0:d=0.15:alpha=1,setpts=PTS-STARTPTS+{t0:.3f}/TB[{tag}rv]")
    fc.append(f"[{tag}x][{tag}rv]overlay={int(cx - rw / 2)}:{int(cy - rw / 2)}:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


def _shake(fc, cur, tag, t0, t1, W, H, amp=0.012):
    """整屏震动：先放大 3% 留出余量，每帧按两个不同频率的正弦错开，约 12 Hz，越抖越轻。"""
    mg = 0.03
    d = max(0.05, t1 - t0)
    dec = f"max(0.25,1-t/{d:.3f})"
    x = f"iw*{mg}+iw*{amp}*sin(n*2.4)*cos(n*0.7)*{dec}"
    y = f"ih*{mg}+ih*{amp * 0.6:.4f}*sin(n*1.9+1.3)*{dec}"
    m, b = _branch(fc, cur, tag, t0, t1, f"crop=iw*{1 - 2 * mg}:ih*{1 - 2 * mg}:'{x}':'{y}',scale={W}:{H}")
    fc.append(f"{m}{b}overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[{tag}]")
    return f'[{tag}]'


def _crack_png(W, H, work, at, seed):
    """玻璃裂纹：从撞击点放射十几条折线，几圈碎环把相邻的线连起来，白色亮线压一层深色阴影。"""
    out = Path(work) / f'crack_{seed}.png'
    if out.exists():
        return out
    S = unit(W, H)
    rng = random.Random(seed)
    cx, cy = at[0] * W, at[1] * H
    rays = []
    n = 14
    for k in range(n):
        ang = 2 * np.pi * k / n + rng.uniform(-0.18, 0.18)
        pts, r = [(cx, cy)], 0.0
        L = rng.uniform(0.25, 0.7) * W   # 裂纹集中在撞击点周围，别一路裂到脸上
        while r < L:
            r += rng.uniform(40, 95) * S
            a2 = ang + rng.uniform(-0.14, 0.14)
            pts.append((cx + np.cos(a2) * r, cy + np.sin(a2) * r))
        rays.append(pts)

    def at_r(pts, rad):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            r0, r1 = np.hypot(x0 - cx, y0 - cy), np.hypot(x1 - cx, y1 - cy)
            if r0 <= rad <= r1:
                q = (rad - r0) / max(1e-6, r1 - r0)
                return x0 + (x1 - x0) * q, y0 + (y1 - y0) * q
        return None
    segs = [p for p in rays]
    for rad in (60 * S, 140 * S, 250 * S, 380 * S):
        for a, b in zip(rays, rays[1:] + rays[:1]):
            pa, pb = at_r(a, rad * rng.uniform(0.85, 1.15)), at_r(b, rad * rng.uniform(0.85, 1.15))
            if pa and pb and rng.random() < 0.7:
                mid = ((pa[0] + pb[0]) / 2 + rng.uniform(-10, 10) * S, (pa[1] + pb[1]) / 2 + rng.uniform(-10, 10) * S)
                segs.append([pa, mid, pb])
    k = 2
    im = Image.new('RGBA', (W * k, H * k), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    sc = lambda pts: [(x * k, y * k) for x, y in pts]
    for pts in segs:
        dr.line(sc(pts), fill=(0, 0, 0, 140), width=int(9 * S * k), joint='curve')
    for pts in segs:
        dr.line(sc(pts), fill=(255, 255, 255, 245), width=int(4.5 * S * k), joint='curve')
    for _ in range(16):   # 撞击点附近的碎块发白
        a = rng.uniform(0, 2 * np.pi)
        rr = rng.uniform(10, 60) * S
        pts = [(cx + np.cos(a + j * 2.1) * rr * rng.uniform(0.5, 1.2), cy + np.sin(a + j * 2.1) * rr * rng.uniform(0.5, 1.2)) for j in range(3)]
        dr.polygon(sc(pts), fill=(255, 255, 255, 70))
    im = im.resize((W, H), Image.LANCZOS)
    im.save(out)
    return out


def _screenprint(f, W, H, FPS, work, aroll, name):
    """整体丝印叠加：细密网点略偏蓝，扣掉人像，只在背景上看得出来（人脸出现网点很难看）。"""
    import matte
    out = f'{work}/{name}'
    S = unit(W, H)
    g = max(4, round(7 * S))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.hypot((xx % g) - g / 2, ((yy + (xx // g % 2) * g / 2) % g) - g / 2)
    dots = np.clip(g * 0.30 + 0.5 - dd, 0, 1) * f.get('opacity', 0.24)
    tint = hex_rgba(f.get('tint', '#2B3A8F'))[:3]
    t0, t1 = float(f['t0']), float(f['t1'])
    d = t1 - t0
    w = Writer(out, W, H, FPS, alpha=True)
    for i, a in enumerate(matte.cutouts(aroll, t0, d, W, H, FPS)):
        tt = i / FPS
        e = min(1.0, tt / 0.3) * min(1.0, (d - tt) / 0.3)
        c = np.zeros((H, W, 4), np.uint8)
        c[..., :3] = tint
        c[..., 3] = (dots * (1 - a) * e * 255).astype(np.uint8)
        w.put(c)
    w.close()
    return out


def _dashed(dr, pts, dash, gap, width, fill):
    """沿一圈点画虚线。"""
    acc, on = 0.0, True
    seg = [pts[0]]
    for p, q in zip(pts, pts[1:]):
        L = float(np.hypot(q[0] - p[0], q[1] - p[1]))
        acc += L
        seg.append(q)
        if acc >= (dash if on else gap):
            if on and len(seg) > 1:
                dr.line(seg, fill=fill, width=width)
            on, acc, seg = not on, 0.0, [q]
    if on and len(seg) > 1:
        dr.line(seg, fill=fill, width=width)


def _round_rect_pts(x, y, w, h, r, n=240):
    r = max(0.0, min(r, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -np.pi / 2), (x + w - r, y + h - r, 0), (x + r, y + h - r, np.pi / 2), (x + r, y + r, np.pi)):
        for j in range(n // 4 + 1):
            a = a0 + np.pi / 2 * j / (n // 4)
            pts.append((cx + np.cos(a) * r, cy + np.sin(a) * r))
    return pts + pts[:1]


def _dimbox(f, W, H, FPS, work, aroll, out):
    """压暗聚光框游走：整屏压到四成亮，一个白色虚线框里保持原亮度，框在脸、胸口之间移动变形，每次 0.4 秒缓入缓出。
    boxes 写 [{at, box: [x, y, w, h], shape: rect / circle}]（at 相对这段开始）；不写就先框脸、一半时移到胸口。"""
    S = unit(W, H)
    t0, t1 = float(f['t0']), float(f['t1'])
    dur, n = t1 - t0, max(1, round((t1 - t0) * FPS))
    boxes = f.get('boxes')
    if not boxes:
        fw0 = W * 0.4
        if is_landscape(W, H):
            x0, _, x1, _ = safe_zones(W, H)['face']
            fw0 = W * (x1 - x0) * 0.55
        fb = face_box(next(read(aroll, t0 + 0.1, 1 / FPS, (W, H), FPS))) or (W / 2, H * 0.1, fw0, H * 0.3)
        cx, top, fw, fh = fb
        bw_ = fw * 1.35
        boxes = [{'at': 0.0, 'box': [(cx - bw_ / 2) / W, max(0.02, top / H - 0.02), bw_ / W, fh * 1.08 / H], 'shape': 'rect'},
                 {'at': round(dur * 0.5, 2), 'box': [0.18, (top + fh * 1.2) / H, 0.64, 0.2], 'shape': 'rect'}]
        if is_landscape(W, H):
            # 胸口框只跟人物占宽，不把两侧留白也圈进来，下沿给字幕让开。
            x0, _, x1, _ = safe_zones(W, H)['face']
            boxes[1]['box'] = [x0, min(0.6, (top + fh * 1.2) / H), x1 - x0, 0.2]
    dim = f.get('dim', 0.6)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        bx = []
        for j in range(4):   # 关键帧：在 at 处开始动，0.4 秒到位
            seq = [(0.0, boxes[0]['box'][j], 'inout')]
            for b_prev, b in zip(boxes, boxes[1:]):
                seq += [(b['at'], b_prev['box'][j], 'inout'), (b['at'] + f.get('move_s', 0.4), b['box'][j], 'inout')]
            bx.append(keyed(seq, tt))
        rseq = [(0.0, 0.5 if boxes[0].get('shape') == 'circle' else 0.05, 'inout')]
        for b_prev, b in zip(boxes, boxes[1:]):
            rseq += [(b['at'], rseq[-1][1], 'inout'), (b['at'] + f.get('move_s', 0.4), 0.5 if b.get('shape') == 'circle' else 0.05, 'inout')]
        rr = keyed(rseq, tt)
        x, y, bw, bh = bx[0] * W, bx[1] * H, bx[2] * W, bx[3] * H
        r = rr * min(bw, bh)
        e = min(1.0, tt / 0.25) * min(1.0, (dur - tt) / 0.2)
        m = Image.new('L', (W, H), int(255 * dim * e))
        dm = ImageDraw.Draw(m)
        dm.rounded_rectangle([x, y, x + bw, y + bh], radius=int(r), fill=0)
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = np.array(m)
        line = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        _dashed(ImageDraw.Draw(line), _round_rect_pts(x, y, bw, bh, r), 24 * S, 14 * S, max(2, int(6 * S)), (255, 255, 255, int(255 * e)))
        over(c, np.array(line), 0, 0)
        w.put(c)
    w.close()
    return out


def _letterbox(f, W, H, FPS, out):
    """宽银幕黑边：上下两条黑边 0.2 秒滑进来（各 0.11 画面高），停住，最后 0.2 秒滑出；text 写了在下黑边里横向滚动。"""
    S = unit(W, H)
    t0, t1 = float(f['t0']), float(f['t1'])
    dur, n = t1 - t0, max(1, round((t1 - t0) * FPS))
    bh = H * f.get('bar', 0.11)
    if is_landscape(W, H):
        bh = min(bh, H * 0.06)
    io = f.get('in_out_s', 0.2)
    tick = None
    if f.get('text'):
        tile = word(f['text'] + '   ·   ', H * 0.026, '#F2F2F2', HEAVY, spacing=int(3 * S))
        reps = int(W * 2 / tile.shape[1]) + 2
        tick = np.concatenate([tile] * reps, axis=1)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        p = ease(tt / io, 'out') * (1 - ease((tt - (dur - io)) / io, 'in'))
        c = np.zeros((H, W, 4), np.uint8)
        hh = int(round(bh * p))
        if hh > 0:
            c[:hh, :, 3] = 255
            c[H - hh:, :, 3] = 255
        if tick is not None and hh > tick.shape[0]:
            off = int((tt * 0.15 * W) % (tick.shape[1] / reps * 1.0))
            seg = tick[:, off:off + W]
            over(c, seg, 0, ((hh - seg.shape[0]) / 2 if is_landscape(W, H) else H - hh + (hh - seg.shape[0]) / 2), 0.85 * p)
        w.put(c)
    w.close()
    return out


def _the_end(f, W, H, FPS, out):
    """全剧终：整屏 0.6 秒压暗，毛笔「全剧终」大字从大一点落定，下面一行小字 THE END。"""
    S = unit(W, H)
    t0, t1 = float(f['t0']), float(f['t1'])
    dur, n = t1 - t0, max(1, round((t1 - t0) * FPS))
    big = with_shadow(fit_word(f.get('text', '全剧终'), H * 0.13, W * 0.8, '#F4EFE4', BRUSH, spacing=int(30 * S)), 10 * S, 0.6)
    en = word(f.get('en', 'THE  END'), H * 0.022, '#D9D2C2', HEAVY, spacing=int(14 * S))
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = int(255 * 0.78 * ease(tt / 0.6))
        p = ease((tt - 0.2) / 0.6, 'out')
        put(c, scale(big, 1.12 - 0.12 * p), W / 2, H * 0.46, p)
        put(c, en, W / 2, H * 0.46 + big.shape[0] * 0.62, ease((tt - 0.6) / 0.4))
        w.put(c)
    w.close()
    return out


_CASCADE = []


def face_box(fr):
    """一帧画面里最大的那张脸：(中心 x, 头顶 y, 脸宽, 头顶到下巴的高)，像素；没检测到返回 None。
    OpenCV 自带的正脸检测框住的是眉毛到嘴，往上补额头、往下补下巴。"""
    import cv2
    if not _CASCADE:
        _CASCADE.append(cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'))
    H, W = fr.shape[:2]
    k = 360 / W
    g = cv2.cvtColor(cv2.resize(fr, (360, int(H * k))), cv2.COLOR_RGB2GRAY)
    fs = _CASCADE[0].detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    if not len(fs):
        return None
    x, y, w, h = max(fs, key=lambda r: r[2] * r[3]) / k
    return x + w / 2, y - h * 0.32, w * 0.95, h * 1.42


def _head_track(frs, W, H):
    """每帧的脸（face_box），每 3 帧检测一次，没检测到沿用上一次，做一点平滑防抖。"""
    out, sm, last = [], None, (W / 2, H * 0.1, W * 0.4, H * 0.3)
    if is_landscape(W, H):
        x0, y0, x1, _ = safe_zones(W, H)['face']
        last = (W / 2, H * y0, W * (x1 - x0) * 0.55, H * 0.3)
    for i, fr in enumerate(frs):
        if i % 3 == 0:
            last = face_box(fr) or last
        b = np.array(last, np.float32)
        sm = b if sm is None else sm * 0.6 + b * 0.4
        out.append(tuple(sm))
    return out


def _face(f, W, H, FPS, work, aroll, out):
    """人脸情绪特效的成片近似：抠像把头放大、头边贴 3D 表情和手写问号、头部染色或整个人变灰、头边一个小标签。
    names 写剪映人物特效名（kvlib.FACE_FX），常叠两个。"""
    import matte
    S = unit(W, H)
    t0, t1 = float(f['t0']), float(f['t1'])
    dur, n = t1 - t0, max(1, round((t1 - t0) * FPS))
    specs = [FACE_FX[x] for x in f.get('names') or []]
    head = max([s.get('head', 1.0) for s in specs] + [1.0])
    tint = next((s['tint'] for s in specs if s.get('tint')), None)
    gray = any(s.get('gray') for s in specs)
    glitch = any(s.get('glitch') for s in specs)
    emojis = [s['emoji'] for s in specs if s.get('emoji')][:2]
    marks = ''.join(s.get('marks', '') for s in specs)[:3]
    tag = next((s['tag'] for s in specs if s.get('tag')), None)
    spark = any(s.get('sparkle') for s in specs)
    frs = list(read(aroll, t0, dur, (W, H), FPS))
    als = list(matte.cutouts(aroll, t0, dur, W, H, FPS))
    heads = _head_track(frs, W, H)
    em = [np.array(Image.open(icon_png(e)).convert('RGBA').resize((int((H if is_landscape(W, H) else W) * 0.17), int((H if is_landscape(W, H) else W) * 0.17)), Image.LANCZOS)) for e in emojis]
    mk = [with_shadow(word(ch, H * 0.07, '#FFD23F', HAND, stroke=int(5 * S), stroke_color='#1A1A1A'), 4 * S, 0.5) for ch in marks]
    tg = None
    if tag:
        tw = word(tag, H * 0.03, '#16161A', HEAVY)
        pad = int(18 * S)
        im = Image.new('RGBA', (tw.shape[1] + 2 * pad, tw.shape[0] + pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=int(16 * S), fill=(255, 255, 255, 240))
        tg = np.array(im)
        over(tg, tw, pad, pad / 2)
        tg = with_shadow(tg, 5 * S, 0.4)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr, a = frs[min(i, len(frs) - 1)], als[min(i, len(als) - 1)]
        cx, top, fw, fh = heads[min(i, len(heads) - 1)]
        e_out = min(1.0, (dur - tt) / 0.15)
        c = np.zeros((H, W, 4), np.uint8)
        if gray or glitch:
            person = fr.astype(np.float32)
            if gray:   # 石化：人变灰、偏一点石头的冷灰
                g = person.mean(2, keepdims=True) * np.array([0.95, 0.97, 1.0], np.float32)
                person = person * (1 - ease(tt / 0.3)) + g * ease(tt / 0.3)
            if glitch and int(tt / 0.12) % 2 == 0:   # 宕机：人像红蓝错开
                sh = int(10 * S)
                person[..., 0] = np.roll(person[..., 0], sh, axis=1)
                person[..., 2] = np.roll(person[..., 2], -sh, axis=1)
            c[..., :3] = np.clip(person, 0, 255).astype(np.uint8)
            c[..., 3] = (a * 255 * e_out).astype(np.uint8)
        hy0, hy1 = int(max(0, top - fh * 0.12)), int(min(H, top + fh * 1.1))   # 头顶上面一点到下巴下面一点
        hx0, hx1 = int(max(0, cx - fw * 0.85)), int(min(W, cx + fw * 0.85))
        k = 1.0 + (head - 1.0) * eback(tt / 0.25) * e_out if head > 1 else 1.0
        if is_landscape(W, H):
            ay = hy0 + (hy1 - hy0) * 0.62
            kw = min(2 * (cx - W * 0.05), 2 * (W * 0.95 - cx)) / max(1, hx1 - hx0)
            kh = min((ay - H * 0.05) / max(1, (hy1 - hy0) * 0.62), (H * 0.8 - ay) / max(1, (hy1 - hy0) * 0.38))
            k = min(k, max(1.0, min(kw, kh)))
        if k > 1.01 or tint:
            crop = np.zeros((hy1 - hy0, hx1 - hx0, 4), np.uint8)
            crop[..., :3] = c[hy0:hy1, hx0:hx1, :3] if (gray or glitch) else fr[hy0:hy1, hx0:hx1]
            hh_, ww_ = hy1 - hy0, hx1 - hx0
            fall = np.clip(np.arange(hh_)[::-1] / (hh_ * 0.14), 0, 1)[:, None]   # 下缘渐隐接回脖子，两边渐隐接回头发
            side = np.clip(np.minimum(np.arange(ww_), np.arange(ww_)[::-1]) / (ww_ * 0.12), 0, 1)[None, :]
            crop[..., 3] = (a[hy0:hy1, hx0:hx1] * fall * side * 255).astype(np.uint8)
            if tint:   # 只染脸：以脸为中心的柔边椭圆
                tr_, tg_, tb_, _ = hex_rgba(tint)
                yy_, xx_ = np.mgrid[hy0:hy1, hx0:hx1].astype(np.float32)
                ell = np.exp(-(((xx_ - cx) / (fw * 0.55)) ** 2 + ((yy_ - (top + fh * 0.55)) / (fh * 0.55)) ** 2) ** 2)
                q = (0.45 * ease(tt / 0.3) * ell)[..., None]
                crop[..., :3] = (crop[..., :3] * (1 - q) + np.array([tr_, tg_, tb_], np.float32) * q).astype(np.uint8)
            big = scale(crop, k)
            ay = hy0 + (hy1 - hy0) * 0.62   # 以鼻子附近为中心放大，头顶不至于顶出画面太多
            over(c, big, cx - big.shape[1] / 2, ay - big.shape[0] * 0.62)
            hy_top = ay - big.shape[0] * 0.62
        else:
            hy_top = hy0
        ey0 = max(H * 0.1, hy_top + fh * 0.3 * k)   # 表情贴在太阳穴高度，不出画
        for j, e in enumerate(em):   # 3D 表情：第一个在头右上，第二个在左边，弹出后轻轻上下浮
            p = eback((tt - 0.08 - j * 0.12) / 0.25)
            if p <= 0:
                continue
            spr = scale(e, max(0.05, p))
            side = fw * 0.85 * k + W * 0.04
            if emojis[j] == 'Kitchen knife':   # 刀插在头侧，刀尖朝里
                spr = rotate_rgba(scale(spr, 1.4), 35)
                side = fw * 0.6 * k + W * 0.03
            ex = min(W - spr.shape[1] * 0.45, cx + side) if j == 0 else max(spr.shape[1] * 0.45, cx - side)
            ey = ey0 + np.sin(tt * 5 + j) * 6 * S
            if is_landscape(W, H):
                ex = np.clip(ex, W * 0.05 + spr.shape[1] / 2, W * 0.95 - spr.shape[1] / 2)
                ey = np.clip(ey, H * 0.05 + spr.shape[0] / 2, H * 0.78 - spr.shape[0] / 2)
            put(c, spr, ex, ey, e_out)
        for j, m in enumerate(mk):   # 手写问号、感叹号：错开蹦出来
            p = eback((tt - 0.05 - j * 0.1) / 0.22)
            if p <= 0:
                continue
            pos = [(-0.2, 0.02), (0.08, -0.05), (0.22, 0.0)][j]
            spr = rotate_rgba(scale(m, max(0.05, p)), [-12, 8, 16][j])
            mx, my = cx + pos[0] * W, max(H * 0.08, hy_top + fh * 0.1 + pos[1] * H)
            if is_landscape(W, H):
                mx = W * (0.76 if j % 2 == 0 else 0.24)
                my = H * (0.2 + j * 0.08)
            put(c, spr, mx, my, e_out)
        if spark:
            for j in range(4):
                ph = (tt * 3 + j * 0.25) % 1
                r = 6 * S * (1 - abs(ph - 0.5) * 2) + 1
                sx, sy = cx + fw * 0.85 * k + W * (0.02 + 0.07 * np.cos(j * 1.7)), ey0 + H * (-0.05 + 0.04 * np.sin(j * 2.3))
                star = Image.new('RGBA', (int(8 * r), int(8 * r)), (0, 0, 0, 0))
                ImageDraw.Draw(star).polygon([(4 * r, 0), (4.8 * r, 3.2 * r), (8 * r, 4 * r), (4.8 * r, 4.8 * r), (4 * r, 8 * r), (3.2 * r, 4.8 * r),
                                              (0, 4 * r), (3.2 * r, 3.2 * r)], fill=(255, 236, 140, 255))
                if is_landscape(W, H):
                    sx = np.clip(sx, W * 0.05 + 4 * r, W * 0.95 - 4 * r)
                    sy = np.clip(sy, H * 0.05 + 4 * r, H * 0.8 - 4 * r)
                put(c, np.array(star), sx, sy, e_out)
        if tg is not None:
            put(c, tg, (side_center(f, W, H)[0] if is_landscape(W, H) else cx), (H * 0.55 if is_landscape(W, H) else max(tg.shape[0] / 2 + H * 0.09, hy_top - H * 0.02)), ease((tt - 0.1) / 0.2) * e_out)
        w.put(c)
    w.close()
    return out


# ---------------------------------------------------------------- 效果转场
def transition(fc, cur, tr, ti, add_input, W, H, FPS, work):
    """第 8 批的效果转场接进滤镜图，返回新标签；不是这里管的种类返回 None（闪白、压黑、竖向模糊还在 render.py）。"""
    kind, v = tr['type'], tr.get('variant')
    if kind in ('blocks', 'tunnel'):   # 一星第 14 批：色块碎片擦屏、隧道穿梭
        import vfx
        return vfx.transition(fc, cur, tr, ti, add_input, W, H, FPS, work)
    if kind not in ('glitch', 'whip', 'iris', 'tear', 'occlude', 'light_leak'):
        return None
    S = unit(W, H)
    a0, d = tr_window(tr)
    t = float(tr['t'])
    tag = f'tx{ti}'
    en = f"between(t,{a0:.3f},{a0 + d:.3f})"
    if kind == 'glitch':   # 红青通道错开，几条横切片左右错位、按 0.05 秒来回跳
        rng = random.Random(int(t * 1000))
        k = 4
        fc.append(f"{cur}split[{tag}m][{tag}s]")
        fc.append(f"[{tag}s]trim=start={a0:.3f}:duration={d:.3f},setpts=PTS-STARTPTS,split={k}" + ''.join(f'[{tag}c{j}]' for j in range(k)))
        fc.append(f"[{tag}m]rgbashift=rh={int(11 * S)}:bh={-int(11 * S)}:enable='{en}',noise=alls=30:allf=t:enable='{en}'[{tag}b0]")
        c = f'[{tag}b0]'
        for j in range(k):
            h = _even(H * rng.uniform(0.035, 0.11))
            y = _even(min(H - h, max(0, H * rng.uniform(0.05, 0.92) - h / 2)))
            dx = rng.choice([-1, 1]) * rng.uniform(35, 95) * S
            fl = f"if(lt(mod((t-{a0:.3f})*{rng.uniform(14, 22):.1f},1),0.5),1,-0.6)"
            fc.append(f"[{tag}c{j}]crop={W}:{h}:0:{y},setpts=PTS+{a0:.3f}/TB[{tag}l{j}]")
            fc.append(f"{c}[{tag}l{j}]overlay=x='{dx:.0f}*{fl}':y={y}:enable='between(t,{a0 + 0.02:.3f},{a0 + d - 0.04:.3f})':eof_action=pass[{tag}b{j + 1}]")
            c = f'[{tag}b{j + 1}]'
        fc.append(f"{c}null[{tag}]")
        return f'[{tag}]'
    if kind == 'whip':   # 整屏往一边甩走（越来越快），切点之后下一段从另一边甩进来（越来越慢），带同方向强动态模糊
        dr = tr.get('dir', 'left')
        horiz = dr in ('left', 'right')
        span = W if horiz else H
        sign = -1 if dr in ('left', 'up') else 1
        A = span * 0.6
        tc = t
        off = (f"if(lt(t,{tc:.3f}),{sign * A:.1f}*pow((t-{a0:.3f})/{max(0.01, tc - a0):.3f},2),"
               f"{-sign * A:.1f}*pow(1-(t-{tc:.3f})/{max(0.01, a0 + d - tc):.3f},2))")
        wrap = f"if(lt({off},0),{off}+{span},{off}-{span})"
        fc.append(f"{cur}split[{tag}m][{tag}s]")
        fc.append(f"[{tag}s]trim=start={a0:.3f}:duration={d:.3f},setpts=PTS-STARTPTS,dblur=angle={0 if horiz else 90}:radius={int(70 * S)},"
                  f"setpts=PTS+{a0:.3f}/TB,split[{tag}w1][{tag}w2]")
        xy1, xy2 = (f"x='{off}':y=0", f"x='{wrap}':y=0") if horiz else (f"x=0:y='{off}'", f"x=0:y='{wrap}'")
        fc.append(f"[{tag}m][{tag}w1]overlay={xy1}:enable='{en}':eof_action=pass[{tag}o]")
        fc.append(f"[{tag}o][{tag}w2]overlay={xy2}:enable='{en}':eof_action=pass[{tag}]")
        return f'[{tag}]'
    if kind == 'iris':
        mov = _iris_mov(tr, W, H, FPS, work, f'{work}/{tag}.mov')
        return _overlay_clip(fc, cur, add_input, mov, a0, a0 + d, tag)
    if kind == 'occlude':
        mov = _occlude_mov(tr, W, H, FPS, work, f'{work}/{tag}.mov')
        return _overlay_clip(fc, cur, add_input, mov, a0, a0 + d, tag)
    if kind == 'light_leak':
        if (v or 'flash') == 'zoom_reveal':   # 光退去后下一段从 0.6 倍放大回满屏，底是暖白
            z0, zd = t, min(0.45, d)
            zz = f"(0.6+0.4*(1-pow(1-clip(t/{zd:.3f},0,1),3)))"
            fc.append(f"{cur}split[{tag}zm][{tag}zs]")
            fc.append(f"[{tag}zs]trim=start={z0:.3f}:duration={zd:.3f},setpts=PTS-STARTPTS,"
                      f"scale=w='trunc({W}*{zz}/2)*2':h='trunc({H}*{zz}/2)*2':eval=frame,setpts=PTS+{z0:.3f}/TB[{tag}zb]")
            fc.append(f"color=c=0xFFE7C2:s={W}x{H}:r={FPS}:d={zd:.3f},setpts=PTS+{z0:.3f}/TB[{tag}zw]")
            fc.append(f"[{tag}zm][{tag}zw]overlay=0:0:enable='between(t,{z0:.3f},{z0 + zd:.3f})':eof_action=pass[{tag}zx]")
            fc.append(f"[{tag}zx][{tag}zb]overlay=x='(W-w)/2':y='(H-h)/2':enable='between(t,{z0:.3f},{z0 + zd:.3f})':eof_action=pass[{tag}z]")
            cur = f'[{tag}z]'
        mov = _leak_mov(tr, W, H, FPS, f'{work}/{tag}.mov')
        return _overlay_clip(fc, cur, add_input, mov, a0, a0 + d, tag)
    # tear：撕纸揭开。切点前最后一帧定格，按撕边遮罩一点点撕掉，露出下面已经换好的下一段
    n = max(2, round(d * FPS))
    fc.append(f"{cur}split[{tag}a][{tag}f0]")
    fc.append(f"[{tag}f0]trim=start={max(0.0, t - 1 / FPS):.4f}:duration={1 / FPS:.4f},setpts=PTS-STARTPTS,loop=loop={n + 2}:size=1,"
              f"setpts=N/{FPS}/TB+{t:.3f}/TB,format=rgba[{tag}f]")
    if (v or 'diagonal') == 'split':   # 中间撕开：上半往上、下半往下退
        top_m, bot_m, top_e, bot_e = _tear_split_pngs(W, H, work, int(t * 100))
        fc.append(f"[{tag}f]split[{tag}f1][{tag}f2]")
        mv = f"pow(clip((t-{t:.3f})/{d:.3f},0,1),1.6)*{H * 0.6:.0f}"
        c = f'[{tag}a]'
        for j, (mk, eg, sg) in enumerate(((top_m, top_e, -1), (bot_m, bot_e, 1))):
            mi = _png_input(add_input, mk, d, FPS)
            fc.append(f"[{mi}:v]format=gray,setpts=PTS-STARTPTS+{t:.3f}/TB[{tag}k{j}]")
            fc.append(f"[{tag}f{j + 1}][{tag}k{j}]alphamerge[{tag}h{j}]")
            ei = _png_input(add_input, eg, d, FPS)
            fc.append(f"[{ei}:v]format=rgba,setpts=PTS-STARTPTS+{t:.3f}/TB[{tag}e{j}]")
            win = f"between(t,{t:.3f},{t + d:.3f})"
            fc.append(f"{c}[{tag}h{j}]overlay=0:'{sg}*{mv}':enable='{win}':eof_action=pass[{tag}x{j}]")
            fc.append(f"[{tag}x{j}][{tag}e{j}]overlay=0:'{sg}*{mv}':enable='{win}':eof_action=pass[{tag}y{j}]")
            c = f'[{tag}y{j}]'
        fc.append(f"{c}null[{tag}]")
        return f'[{tag}]'
    mask, edge = _tear_movs(tr, W, H, FPS, work, f'{work}/{tag}')
    mi = add_input(['-i', mask])
    fc.append(f"[{mi}:v]setpts=PTS-STARTPTS+{t:.3f}/TB,alphaextract[{tag}k]")
    fc.append(f"[{tag}f][{tag}k]alphamerge[{tag}fm]")
    fc.append(f"[{tag}a][{tag}fm]overlay=0:0:enable='between(t,{t:.3f},{t + d:.3f})':eof_action=pass[{tag}o]")
    return _overlay_clip(fc, f'[{tag}o]', add_input, edge, t, t + d, tag)


def _iris_mov(tr, W, H, FPS, work, out):
    """圆形光圈：swap 画面收成画面中下部 0.6 宽的圆，切点在圆里换成下一段，再放大到满屏；
    open 黑底上一个小圆从脸那里张开到 0.6 宽的圆头像，停一下再打开到满屏。圆外是黑的。"""
    S = unit(W, H)
    v = tr.get('variant') or 'swap'
    a0, d = tr_window(tr)
    lead = tr['t'] - a0
    n = max(1, round(d * FPS))
    cx, cy = W * tr.get('x', 0.5), H * tr.get('y', 0.30 if v == 'open' else 0.42)
    full = float(np.hypot(max(cx, W - cx), max(cy, H - cy))) + 4
    radius = 0.30 * (H if is_landscape(W, H) else W)
    if v == 'open':
        kf = [(0, 0.03 * W, 'inout'), (min(0.5, d * 0.62), radius, 'out'), (d - 0.18, radius, 'inout'), (d, full, 'in')]
    else:
        kf = [(0, full, 'inout'), (lead, radius, 'in'), (lead + 0.04, radius, 'inout'), (d, full, 'out')]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.hypot(xx - cx, yy - cy)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        r = keyed(kf, i / FPS)
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = (np.clip(dist - r + 0.5, 0, 1) * 255).astype(np.uint8)
        if r < full * 0.85:   # 圆边一道细白线
            ring = np.clip(1.5 * S - np.abs(dist - r), 0, 1)
            c[..., :3] = np.maximum(c[..., :3], (ring[..., None] * 255).astype(np.uint8))
            c[..., 3] = np.maximum(c[..., 3], (ring * 200).astype(np.uint8))
        w.put(c)
    w.close()
    return out


def _leak_mov(tr, W, H, FPS, out):
    """漏光闪过：几团橙黄暖光从左往右扫过，切点前后几乎铺满整屏，再退出去。"""
    a0, d = tr_window(tr)
    lead = (tr['t'] - a0) / d
    n = max(1, round(d * FPS))
    q = 4
    w_, h_ = W // q, H // q
    yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
    blobs = [((1.0, 0.28), (0.55, 0.30), (255, 138, 61)), ((0.8, 0.62), (0.6, 0.34), (255, 210, 122)), ((1.15, 0.85), (0.5, 0.28), (255, 98, 40))]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        p = i / max(1, n - 1)
        sweep = -0.9 + 1.9 * ease(p, 'inout')   # 光团整体从左边外面扫到右边
        peak = np.exp(-((p - lead) / 0.28) ** 2)
        rgb = np.zeros((h_, w_, 3), np.float32)
        al = np.zeros((h_, w_), np.float32)
        for (bx, by), (rx, ry), col in blobs:
            g = np.exp(-(((xx / w_) - (bx + sweep - 0.5)) / rx) ** 2 - (((yy / h_) - by) / ry) ** 2)
            al = 1 - (1 - al) * (1 - g * 0.95)
            rgb += np.array(col, np.float32) * g[..., None]
        rgb = np.clip(rgb / np.maximum(1e-3, al[..., None] * 1.6) , 0, 255)
        al = np.clip(al * (0.55 + 0.45 * peak) + 0.55 * peak, 0, 0.97)
        c = np.zeros((h_, w_, 4), np.uint8)
        c[..., :3] = np.clip(rgb * (1 - 0.25 * peak) + 255 * 0.25 * peak, 0, 255).astype(np.uint8)
        c[..., 3] = (al * 255).astype(np.uint8)
        w.put(resize(c, W, H))
    w.close()
    return out


def _occlude_mov(tr, W, H, FPS, work, out):
    """主题物遮挡扫屏：主题物（src 图或 emoji 名）放大到比画面还宽，带纵向强动态模糊从下往上冲过，切点那两帧完全盖住。"""
    a0, d = tr_window(tr)
    lead = tr['t'] - a0
    n = max(1, round(d * FPS))
    src = tr.get('src')
    im = Image.open(to_png(src, work) if src else icon_png(tr.get('emoji', 'Rocket'))).convert('RGBA')
    bb = im.getbbox() or (0, 0, im.width, im.height)
    im = im.crop(bb)
    k = W * tr.get('w', 1.7) / im.width
    spr = np.array(im.resize((int(im.width * k), int(im.height * k)), Image.BILINEAR))
    spr = vblur(spr, H * 0.05)
    fill = spr[..., :3][spr[..., 3] > 128].mean(0) if (spr[..., 3] > 128).any() else np.array([30, 30, 30])
    h = spr.shape[0]
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        cy = keyed([(0, H + h / 2, 'inout'), (lead, H / 2, 'inout'), (d, -h / 2, 'inout')], tt)
        c = np.zeros((H, W, 4), np.uint8)
        if abs(tt - lead) <= 1.01 / FPS:   # 切点前后各一帧整屏盖满
            c[..., :3] = fill.astype(np.uint8)
            c[..., 3] = 255
        put(c, spr, W / 2, cy)
        w.put(c)
    w.close()
    return out


def _jag(n, seed, amp):
    """撕边：随机游走再平滑，不规则但连贯。"""
    rng = np.random.default_rng(seed)
    x = np.cumsum(rng.normal(0, 1, n))
    x = np.convolve(x - np.linspace(x[0], x[-1], n), np.ones(9) / 9, mode='same')
    x = x / (np.abs(x).max() + 1e-6) * amp
    return x + rng.normal(0, amp * 0.12, n)


def _tear_movs(tr, W, H, FPS, work, stem):
    """斜向撕开：一条约 -15 度、带白色纸芯的不规则撕边从上往下划过，上面是撕掉露出的下一段，下面是还没撕的上一画面。
    返回 (遮罩 .mov：透明度 = 上一画面还留着的部分，撕边 .mov：白纸芯和阴影)。"""
    S = unit(W, H)
    a0, d = tr_window(tr)
    n = max(1, round(d * FPS))
    ang = np.deg2rad(tr.get('angle', -15))
    xs = np.arange(W, dtype=np.float32)
    jag = _jag(W, int(tr['t'] * 100), 12 * S)
    core = 10 * S + np.abs(_jag(W, int(tr['t'] * 100) + 1, 6 * S))
    yy = np.arange(H, dtype=np.float32)[:, None]
    span = H + W * abs(np.tan(ang)) + 80 * S
    mw, ew = Writer(f'{stem}_mask.mov', W, H, FPS, alpha=True), Writer(f'{stem}_edge.mov', W, H, FPS, alpha=True)
    for i in range(n):
        p = ease(i / max(1, n - 1), 'inout')
        yc = -W * abs(np.tan(ang)) / 2 - 40 * S + span * p
        line = (yc + np.tan(ang) * (xs - W / 2) + jag)[None, :]
        keep = np.clip(yy - line + 0.5, 0, 1)
        m = np.zeros((H, W, 4), np.uint8)
        m[..., :3] = 255
        m[..., 3] = (keep * 255).astype(np.uint8)
        mw.put(m)
        e = np.zeros((H, W, 4), np.uint8)
        paper = np.clip(yy - line + 0.5, 0, 1) * np.clip(line + core[None, :] - yy + 0.5, 0, 1)
        shade = np.clip(1 - (line - yy) / (16 * S), 0, 1) * (yy < line) * 0.45
        e[..., :3] = (paper[..., None] * np.array([250, 248, 242])).astype(np.uint8)
        e[..., 3] = (np.maximum(paper, shade) * 255).astype(np.uint8)
        ew.put(e)
    mw.close()
    ew.close()
    return f'{stem}_mask.mov', f'{stem}_edge.mov'


def _tear_split_pngs(W, H, work, seed):
    """中间撕开用的静态图：上下两半的遮罩（灰度）和各自的白纸芯撕边。"""
    S = unit(W, H)
    names = [Path(work) / f'tear_{seed}_{x}.png' for x in ('tm', 'bm', 'te', 'be')]
    if all(p.exists() for p in names):
        return names
    xs = np.arange(W, dtype=np.float32)
    yy = np.arange(H, dtype=np.float32)[:, None]
    mid = H * 0.5 + np.tan(np.deg2rad(-4)) * (xs - W / 2)
    top_line = (mid + _jag(W, seed, 14 * S))[None, :]
    bot_line = (mid + _jag(W, seed + 7, 14 * S) + 2 * S)[None, :]
    tm = np.clip(top_line - yy + 0.5, 0, 1)
    bm = np.clip(yy - bot_line + 0.5, 0, 1)
    Image.fromarray((tm * 255).astype(np.uint8), 'L').save(names[0])
    Image.fromarray((bm * 255).astype(np.uint8), 'L').save(names[1])
    for line, out, up in ((top_line, names[2], True), (bot_line, names[3], False)):
        core = 10 * S + np.abs(_jag(W, seed + (3 if up else 5), 5 * S))[None, :]
        band = (np.clip(line - yy + 0.5, 0, 1) * np.clip(yy - (line - core) + 0.5, 0, 1)) if up else \
            (np.clip(yy - line + 0.5, 0, 1) * np.clip(line + core - yy + 0.5, 0, 1))
        e = np.zeros((H, W, 4), np.uint8)
        e[..., :3] = (250, 248, 242)
        e[..., 3] = (band * 255).astype(np.uint8)
        Image.fromarray(e, 'RGBA').save(out)
    return names


# ---------------------------------------------------------------- 逐帧大字
def clip(t, W, H, FPS, st, work, aroll, out):
    {'boom': boom, 'persist': persist, 'glitchswap': glitchswap}[t['layout']](t, W, H, FPS, st, work, aroll, out)


BOOM_VARIANTS = {
    'behind': '身后爆闪：人不动，背后 0.3 秒变成玫红放射锯齿爆炸图，同时红黑毛笔字砸在胸口',
    'cartoon': '卡通爆炸炸成单字页：米黄爆炸云带彩屑从人身前炸开铺满，变成粉色放射底，正中一个深红毛笔字停两秒',
}


def _rays(W, H, cx, cy, n, c1, c2, rot=0.0, jag=None, jag_col=None, seed=1):
    """放射底：n 条交替的扇形，jag 给了就在中间画一圈锯齿爆炸星。"""
    im = Image.new('RGBA', (W, H), c1)
    dr = ImageDraw.Draw(im)
    R = float(np.hypot(W, H))
    for k in range(n):
        if k % 2:
            continue
        a0, a1 = rot + 2 * np.pi * k / n, rot + 2 * np.pi * (k + 1) / n
        dr.polygon([(cx, cy), (cx + np.cos(a0) * R, cy + np.sin(a0) * R), (cx + np.cos(a1) * R, cy + np.sin(a1) * R)], fill=c2)
    if jag:
        rng = random.Random(seed)
        pts = []
        m = 26
        for k in range(m):
            a = rot + 2 * np.pi * k / m
            r = jag * (1.0 if k % 2 == 0 else 0.62) * rng.uniform(0.9, 1.1)
            pts.append((cx + np.cos(a) * r, cy + np.sin(a) * r))
        dr.polygon(pts, fill=jag_col)
    return np.array(im)


def _cloud(r, seed, S):
    """卡通爆炸云：米黄底、深色描边的一圈鼓包。"""
    rng = random.Random(seed)
    D = int(r * 2.6)
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    c = D / 2
    pts = []
    m = 15
    for k in range(m * 4):
        a = 2 * np.pi * k / (m * 4)
        bump = 1 + 0.13 * abs(np.sin(a * m / 2)) + rng.uniform(-0.02, 0.02)
        pts.append((c + np.cos(a) * r * bump, c + np.sin(a) * r * bump))
    dr.polygon(pts, fill=(36, 24, 20, 255))
    inner = [(c + (x - c) * 0.94, c + (y - c) * 0.94) for x, y in pts]
    dr.polygon(inner, fill=(246, 227, 180, 255))
    inner2 = [(c + (x - c) * 0.55, c + (y - c) * 0.55) for x, y in pts]
    dr.polygon(inner2, fill=(255, 241, 205, 255))
    return np.array(im)


def boom(t, W, H, FPS, st, work, aroll, out):
    import matte
    S = unit(W, H)
    v = t.get('variant', 'behind')
    dur, n = frames(t, FPS)
    seed = int(t['t0'] * 100)
    text = t.get('text', '')
    w = Writer(out, W, H, FPS, alpha=True)
    if v == 'cartoon':
        bgs = [_rays(W, H, W / 2, H / 2, 28, (246, 201, 184, 255), (240, 176, 158, 255), rot=k * 0.02) for k in range(0, 3)]
        ch = rough(word(text[:2], H * 0.30, t.get('color', '#C8203F'), BRUSH), seed, 0.25)
        ch = with_shadow(ch, 10 * S, 0.35, dy=int(8 * S))
        rng = random.Random(seed)
        bits = [(rng.uniform(0, 2 * np.pi), rng.uniform(0.5, 1.3), rng.choice([(232, 23, 77), (41, 182, 246), (255, 210, 63), (76, 193, 122)]),
                 rng.uniform(26, 48) * S) for _ in range(34)]
        cloud = _cloud(W * 0.5, seed, S)
        burst_s = t.get('burst_s', 0.15)
        for i in range(n):
            tt = i / FPS
            if tt < burst_s + 0.12:   # 爆炸云从人身前炸开，0.15 秒铺满
                c = np.zeros((H, W, 4), np.uint8)
                p = ease(tt / burst_s, 'out')
                cl = scale(cloud, 0.15 + 1.9 * p)
                put(c, cl, W / 2, H * 0.5)
                dr = ImageDraw.Draw(im := Image.fromarray(c, 'RGBA'))
                for a, sp, col, sz in bits:
                    r = W * sp * (0.2 + 1.2 * p)
                    x, y = W / 2 + np.cos(a) * r, H * 0.5 + np.sin(a) * r
                    dr.polygon([(x, y - sz), (x + sz, y + sz * 0.8), (x - sz, y + sz * 0.8)], fill=col + (255,))
                c = np.array(im)
                if tt > burst_s:   # 云退成放射底
                    q = (tt - burst_s) / 0.12
                    bg = bgs[0].copy()
                    bg[..., 3] = (bg[..., 3] * q).astype(np.uint8)
                    over(c, bg, 0, 0)
            else:
                c = bgs[(i // 3) % len(bgs)].copy()
                p = eback((tt - burst_s - 0.05) / 0.25)
                put(c, scale(ch, max(0.05, 1.5 - 0.5 * p)), W / 2, H * 0.48, _clamp(p * 1.5))
            c[..., 3] = (c[..., 3] * fade_out(tt, dur, 0.15)).astype(np.uint8)
            w.put(c)
        w.close()
        return
    flash = t.get('flash_s', 0.3)
    cx, cy = W / 2, H * 0.36
    bg = _rays(W, H, cx, cy, 24, (242, 92, 138, 255), (232, 23, 77, 255), jag=W * 0.42, jag_col=(255, 214, 224, 255), seed=seed)
    nf = max(1, round(flash * FPS))
    frs = list(read(aroll, t['t0'], nf / FPS, (W, H), FPS))
    als = list(matte.cutouts(aroll, t['t0'], nf / FPS, W, H, FPS))
    spr = None
    if text:
        spr = rough(word(text[:4], H * 0.15, t.get('color', '#E8174D'), BRUSH, stroke=int(9 * S), stroke_color='#141414'), seed, 0.2)
        spr = rotate_rgba(with_shadow(spr, 8 * S, 0.5, dy=int(6 * S)), 6)
        if is_landscape(W, H):
            spr = side_fit(spr, t, W, H, 0.6)
        if spr.shape[1] > W * 0.9:
            spr = scale(spr, W * 0.9 / spr.shape[1])
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        if i < nf:   # 背后爆闪：放射图在人后面
            a = als[min(i, len(als) - 1)][..., None]
            c[..., :3] = (bg[..., :3] * (1 - a) + frs[min(i, len(frs) - 1)] * a).astype(np.uint8)
            c[..., 3] = 255 if i < nf - 1 else 160
        if spr is not None:
            p = eback((tt - 0.04) / 0.16)
            if p > 0:
                put(c, scale(spr, max(0.05, 1.7 - 0.7 * p)), (side_center(t, W, H)[0] if is_landscape(W, H) else W / 2), H * t.get('y', 0.48 if is_landscape(W, H) else 0.64), _clamp(p * 2) * fade_out(tt, dur))
        w.put(c)
    w.close()


def _hsmear(a, r):
    """横向拉丝：每一行沿 x 方向做长距离均值。"""
    if r < 1:
        return a
    k = int(r) * 2 + 1
    f = a.astype(np.float32)
    pad = np.pad(f, ((0, 0), (k // 2, k // 2), (0, 0)), mode='edge')
    c = np.cumsum(pad, axis=1)
    c = np.concatenate([np.zeros((f.shape[0], 1, f.shape[2]), np.float32), c], axis=1)
    return ((c[:, k:] - c[:, :-k]) / k).astype(np.uint8)


def persist(t, W, H, FPS, st, work, aroll, out):
    """字不动底在换：一组大字从头到尾一个像素不动，底下的画面连着换（口播、黑场、横向拉丝、白底、口播），
    换完字在 2.5 秒里慢慢变暗到三成多。bgs 写底的顺序，seg 每个底停几秒（快换 0.12~0.5）。"""
    S = unit(W, H)
    dur, n = frames(t, FPS)
    bgs = t.get('bgs') or ['aroll', 'black', 'whip', 'white', 'aroll']
    seg = t.get('seg', 0.3)
    segs = seg if isinstance(seg, list) else [seg] * (len(bgs) - 1)
    starts = [0.0]
    for s_ in segs[:len(bgs) - 1]:
        starts.append(starts[-1] + s_)
    lines = t['text'].replace('\\N', '\n').split('\n')
    light = [fit_word(x, H * 0.088, W * 0.86, '#FFFFFF', HEAVY) for x in lines]
    dark = [fit_word(x, H * 0.088, W * 0.86, '#16161A', HEAVY) for x in lines]
    def block(imgs, sh):
        gap = int(H * 0.012)
        h = sum(x.shape[0] for x in imgs) + gap * (len(imgs) - 1)
        wd = max(x.shape[1] for x in imgs)
        b = np.zeros((h, wd, 4), np.uint8)
        y = 0
        for x in imgs:
            over(b, x, (wd - x.shape[1]) / 2, y)
            y += x.shape[0] + gap
        return with_shadow(b, 8 * S, 0.55) if sh else with_shadow(b, 6 * S, 0.12)
    tl_, td_ = block(light, True), block(dark, False)
    cy = H * t.get('y', 0.6)
    cx = W / 2
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)
        tl_, td_ = side_fit(tl_, t, W, H, 0.9), side_fit(td_, t, W, H, 0.9)
    fade_at = t.get('fade_at', starts[-1] + 0.4)
    frs = read(aroll, t['t0'], dur, (W, H), FPS)
    w = Writer(out, W, H, FPS, alpha=True)
    for i in range(n):
        tt = i / FPS
        fr = next(frs)
        j = max(k for k, s_ in enumerate(starts) if s_ <= tt + 1e-6)
        kind = bgs[j]
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = 255
        if kind == 'aroll':
            c[..., :3] = fr
        elif kind == 'black':
            c[..., :3] = 8
        elif kind == 'white':
            c[..., :3] = 246
        elif kind == 'whip':   # 只甩底：口播画面横向拉丝往一边扫，叠几道蓝橙白条纹
            q = (tt - starts[j]) / max(0.05, (starts[j + 1] if j + 1 < len(starts) else dur) - starts[j])
            sm = _hsmear(resize(fr, W // 4, H // 4), W * 0.06)
            sm = np.roll(sm, int(-q * W / 4 * 0.6), axis=1)
            c[..., :3] = resize(sm, W, H)
            rng = random.Random(seed := int(t['t0'] * 100) + j)
            for _ in range(7):
                yb, hb = rng.uniform(0, H), rng.uniform(4, 22) * S
                col = rng.choice([(70, 140, 255), (255, 150, 60), (255, 255, 255)])
                y0, y1 = int(max(0, yb)), int(min(H, yb + hb))
                c[y0:y1, :, :3] = (c[y0:y1, :, :3] * 0.4 + np.array(col) * 0.6).astype(np.uint8)
        dk = 1 - 0.62 * ease((tt - fade_at) / 2.5)
        spr = td_ if kind == 'white' else tl_
        put(c, spr, cx, cy, dk)
        c[..., 3] = (c[..., 3] * min(1.0, tt / 0.06) * fade_out(tt, dur, 0.12)).astype(np.uint8)
        w.put(c)
    w.close()


def glitchswap(t, W, H, FPS, st, work, aroll, out):
    """文字故障换字：一句大字被红青错位、横切片撕开，故障中间一帧换成下一句（学会了吗 → 收藏起来吧）。"""
    S = unit(W, H)
    dur, n = frames(t, FPS)
    sw = t.get('swap_at', dur * 0.45)
    a = with_shadow(fit_word(t['text'], 150 * S, W * 0.86, '#FFFFFF', HEAVY, stroke=int(3 * S)), 7 * S)
    b = with_shadow(fit_word(t['text2'], 150 * S, W * 0.86, t.get('color2', '#FFE24A'), HEAVY, stroke=int(3 * S)), 7 * S)
    cx, cy = W / 2, H * t.get('y', 0.62)
    if is_landscape(W, H):
        cx, cy = side_center(t, W, H)
        a, b = side_fit(a, t, W, H, 0.85), side_fit(b, t, W, H, 0.85)
    w = Writer(out, W, H, FPS, alpha=True)
    rng = random.Random(int(t['t0'] * 100))
    for i in range(n):
        tt = i / FPS
        c = np.zeros((H, W, 4), np.uint8)
        c[..., 3] = int(255 * 0.25 * min(1, tt / 0.15) * fade_out(tt, dur))
        spr = a if tt < sw else b
        g = abs(tt - sw) < 0.14
        if g:
            off = int(rng.uniform(8, 16) * S)
            m = spr.copy()
            red, cyan = m.copy(), m.copy()
            red[..., :3] = (255, 45, 85)
            cyan[..., :3] = (25, 224, 255)
            put(c, red, cx - off, cy, 0.85)
            put(c, cyan, cx + off, cy, 0.85)
            sl = spr.copy()
            for _ in range(4):
                y0 = rng.randint(0, max(1, sl.shape[0] - 8))
                hh = rng.randint(int(6 * S), max(int(7 * S), sl.shape[0] // 5))
                sl[y0:y0 + hh] = np.roll(sl[y0:y0 + hh], rng.randint(-int(40 * S), int(40 * S)), axis=1)
            put(c, sl, cx, cy)
            for _ in range(5):   # 几道横向噪点条
                y0 = int(cy + rng.uniform(-0.12, 0.12) * H)
                c[max(0, y0):y0 + int(3 * S), :, :3] = 255
                c[max(0, y0):y0 + int(3 * S), :, 3] = 120
        else:
            p = eback(tt / 0.2) if tt < sw else 1.0
            put(c, scale(spr, 0.85 + 0.15 * p), cx, cy, min(1, tt / 0.08) * fade_out(tt, dur))
        w.put(c)
    w.close()


# ---------------------------------------------------------------- morph 窗口按节拍变形
MORPH_STEPS = [   # (宽占画面宽, 高占画面高, 圆角占短边, 中心高)：小圆 → 大圆 → 圆角方 → 竖长圆角 → 接近满屏
    (0.30, 0.30 * 9 / 16, 0.5, 0.30), (0.45, 0.45 * 9 / 16, 0.5, 0.31), (0.62, 0.62 * 9 / 16, 0.18, 0.35),
    (0.70, 0.60, 0.12, 0.44), (0.92, 0.90, 0.05, 0.48)]


def layout_clip(l, tl, W, H, FPS, st, work, aroll, preview=False):
    out = f"{work}/morph_{l['t0']:.2f}.mp4"
    morph(l, W, H, FPS, aroll, out, preview)
    return out


def morph_times(l):
    """每一步变形开始的相对秒数：写了 at 就用写的，否则在这段里均匀排开。"""
    k = len(l.get('steps') or MORPH_STEPS)
    d = l['t1'] - l['t0']
    return l.get('at') or [round(d * j / k, 3) for j in range(k)]


def morph(l, W, H, FPS, aroll, out, preview=False):
    """人装在小窗里，背后是同一画面放大 1.2 倍、虚化压暗；窗口形状随口播节拍一下一下变，每次 0.3 秒带一点回弹。"""
    S = unit(W, H)
    dur = l['t1'] - l['t0']
    n = max(1, round(dur * FPS))
    steps = [tuple(x) for x in (l.get('steps') or MORPH_STEPS)]
    if is_landscape(W, H) and not l.get('steps'):
        steps = [(0.16, 0.16 * W / H, 0.5, 0.32), (0.24, 0.24 * W / H, 0.5, 0.36),
                 (0.35, 0.55, 0.18, 0.4), (0.6, 0.58, 0.12, 0.43), (0.86, 0.70, 0.05, 0.43)]
    ats = morph_times(l)
    sd = l.get('step_s', 0.3)
    w = Writer(out, W, H, FPS, preview=preview)
    for i, fr in enumerate(read(aroll, l['t0'], dur, (W, H), FPS)):
        tt = i / FPS
        j = max([k for k, a in enumerate(ats) if a <= tt + 1e-6] or [0])
        prev = steps[max(0, j - 1)] if j > 0 else (steps[0][0] * 0.2, steps[0][1] * 0.2, 0.5, steps[0][3])
        p = eback((tt - ats[j]) / sd, 1.2)
        ww, hh, rr, cyf = [a + (b - a) * p for a, b in zip(prev, steps[j])]
        small = resize(fr, W // 4, H // 4)
        bg = np.array(Image.fromarray(small).filter(ImageFilter.GaussianBlur(6 * S)))
        bg = resize(bg, W * 1.2, H * 1.2)
        y0, x0 = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2
        canvas = (bg[y0:y0 + H, x0:x0 + W].astype(np.float32) * 0.72).astype(np.uint8)
        bw_, bh_ = max(4, ww * W), max(4, hh * H)
        cx, cy = W / 2, H * cyf
        if is_landscape(W, H):
            bw_ = min(bw_, W * 0.9)
            bh_ = min(bh_, 2 * min(cy - H * 0.05, H * 0.8 - cy))
        r = rr * min(bw_, bh_)
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2, cx + bw_ / 2, cy + bh_ / 2], radius=int(r), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(0.8))
        sh = np.array(m.filter(ImageFilter.GaussianBlur(18 * S)), np.float32)[..., None] / 255
        canvas = (canvas * (1 - 0.45 * np.roll(sh, int(10 * S), axis=0))).astype(np.uint8)
        mm = np.array(m, np.float32)[..., None] / 255
        canvas = (canvas * (1 - mm) + fr * mm).astype(np.uint8)
        ring = Image.new('L', (W, H), 0)
        ImageDraw.Draw(ring).rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2, cx + bw_ / 2, cy + bh_ / 2], radius=int(r),
                                               outline=255, width=max(2, int(5 * S)))
        rg = np.array(ring, np.float32)[..., None] / 255 * 0.9
        canvas = (canvas * (1 - rg) + 255 * rg).astype(np.uint8)
        w.put(canvas)
    w.close()


# ---------------------------------------------------------------- 插入影视梗片段
def splice_inserts(path, tl, W, H, FPS, preview=False):
    """成片渲完后，在 t 秒处硬切插入用户给的片段（横版居中黑底，不带字幕和头像，用片段自己的声音），再硬切回口播。
    inserts: [{t, src, in, dur, text}]；dur 默认取片段长度和 1.5 秒里短的那个，text 是叠在片段上的荧光绿花字（反应镜头用）。片子会变长 dur 秒。"""
    ins = sorted(tl.get('inserts') or [], key=lambda x: x['t'])
    if not ins:
        return
    path = Path(path)
    main = path.with_name(path.stem + '.noinsert' + path.suffix)
    os.replace(path, main)
    total = probe(main)['duration']
    inputs, fc, parts, prev, pngs = ['-i', str(main)], [], [], 0.0, []
    for k, x in enumerate(ins):
        t = min(float(x['t']), total)
        info = probe(x['src'])
        d = float(x.get('dur', min(1.5, info['duration'] - x.get('in', 0))))
        fc.append(f"[0:v]trim=start={prev:.3f}:end={t:.3f},setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[0:a]atrim=start={prev:.3f}:end={t:.3f},asetpts=PTS-STARTPTS[a{k}]")
        inputs += ['-ss', f"{x.get('in', 0):.3f}", '-t', f'{d:.3f}', '-i', str(Path(x['src']).resolve())]
        j = inputs.count('-i') - 1
        fc.append(f"[{j}:v]scale={W}:-2:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={FPS},format=yuv420p,"
                  f"trim=duration={d:.3f},setpts=PTS-STARTPTS[m{k}{'r' if x.get('text') else ''}]")
        if x.get('text'):   # 反应镜头上的荧光绿花字（插入反应镜头 host_cam 的片尾那条「嘿嘿」）
            png = path.with_name(f'{path.stem}.insert{k}.png')
            g = with_shadow(word(x['text'], H * 0.06, x.get('color', '#B4F532'), HEAVY, stroke=int(6 * unit(W, H)), stroke_color='#1A1A1A'), 8 * unit(W, H))
            Image.fromarray(g).save(png)
            inputs += ['-loop', '1', '-t', f'{d:.3f}', '-i', str(png)]
            pj = inputs.count('-i') - 1
            fc.append(f"[m{k}r][{pj}:v]overlay=(W-w)/2:H*{x.get('y', 0.66)}-h/2:shortest=1,format=yuv420p[m{k}]")
            pngs.append(png)
        if info['has_audio']:
            fc.append(f"[{j}:a]aformat=channel_layouts=stereo:sample_rates=48000,loudnorm=I=-17:TP=-2,apad,atrim=duration={d:.3f},asetpts=PTS-STARTPTS[ma{k}]")
        else:
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={d:.3f}[ma{k}]")
        parts += [f'[v{k}][a{k}]', f'[m{k}][ma{k}]']
        prev = t
    k = len(ins)
    fc.append(f"[0:v]trim=start={prev:.3f},setpts=PTS-STARTPTS[v{k}]")
    fc.append(f"[0:a]atrim=start={prev:.3f},asetpts=PTS-STARTPTS[a{k}]")
    parts.append(f'[v{k}][a{k}]')
    fc.append(''.join(parts) + f"concat=n={len(parts)}:v=1:a=1[vo][ao]")
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', '[vo]', '-map', '[ao]',
                        '-c:v', 'libx264', '-preset', 'ultrafast' if preview else 'medium', '-crf', '30' if preview else '18',
                        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(path)], capture_output=True, text=True)
    if r.returncode:
        os.replace(main, path)
        raise SystemExit('插入梗片段失败：' + r.stderr[-800:])
    main.unlink()
    for x in pngs:
        x.unlink()
    print(f"插入梗片段 {len(ins)} 段，共 {sum(float(x.get('dur', 1.2)) for x in ins):.1f} 秒")
