"""按 timeline.json 生成剪映草稿（与 render.py 同一份时间线、同一批预处理素材）。

用法：python build_draft.py timeline.json --name 草稿名 [--draft-root 剪映草稿目录]

剪映草稿目录默认取 macOS 剪映专业版的位置；Windows 一般是
  C:/Users/<用户名>/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft
生成后在剪映首页找到草稿打开即可（看不到就重启剪映）。草稿引用素材的绝对路径，素材不要挪动。

和成片的差别：
  - 剪映做不出来的版式和大字（见 baked_ranges）在最上面一条「成片画面」轨铺不压字幕的成片，字幕仍是剪映文字。
  - 竖屏 fx 里剪映有对应特效的放真特效，没有的那几秒铺成片；横屏 fx 铺成片，保留安全区和动画位置；插入的梗片段不进草稿。
  - timeline 里的 jy 字段只在草稿里生效：subs/titles 的 "jy_flower"（花字名）、"effects"（剪映特效名）、"stickers"（剪映贴纸名），
    名字和编号见 assets/jianying_resources.json 与 pyJianYingDraft 的特效枚举。
  - 字号按「剪映字号 × 6.1 ≈ 1080 宽画布上的像素字高」换算，坐标换成剪映的中心原点、半画布单位。
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pyJianYingDraft as dj
from pyJianYingDraft import (TransitionType, TrackSpec, TrackType, VideoSegment, AudioSegment, TextSegment, TextStyle, TextBorder, TextShadow,
                             TextBackground, ClipSettings, FontType, TextIntro, TextOutro, IntroType, KeyframeProperty,
                             StickerSegment, VideoSceneEffectType, VideoCharacterEffectType)

from typeset import layout_title, text_w
from library import expand_beats
import audiomix
from kvlib import unit, is_landscape, load_json, paper_ink, probe, style_preset, hex_rgba, pip_clip, is_image, to_png, pip_sub_ranges, expand_shots, pip_params, zoom_preset, find_role_font, bgm_gain_db, sfx_gain_db, all_sfx, auto_zoom, auto_transitions, TRANSITIONS, expand_bgm, GRAPHIC_LAYOUTS
from render import prep_broll, subtitle_scale
import effects
import structure
from annot import side_box, side_center
from kvlib import fx_jy, phrase_subs

MAC_ROOT = Path.home() / 'Movies/JianyingPro/User Data/Projects/com.lveditor.draft'
RES = load_json(Path(__file__).resolve().parent.parent / 'assets/jianying_resources.json')
PX_PER_SIZE = 6.1


def us(sec):
    return int(round(sec * 1_000_000))


def rng(t0, t1):
    return dj.Timerange(us(t0), max(1, us(t1) - us(t0)))


def col(hexc):
    r, g, b, _ = hex_rgba(hexc)
    return (r / 255, g / 255, b / 255)


def tx(x):  # 0~1 画面横向位置 → 剪映横向坐标
    return (x - 0.5) * 2


def ty(y):  # 0~1 画面纵向位置（向下为正）→ 剪映纵向坐标（向上为正）
    return (0.5 - y) * 2


def size_of(px, W):
    # 剪映的字号要按画布宽归一，这是输出单位换算，不是尺寸倍率。
    return round(px * (1080 / W) / PX_PER_SIZE, 1) if W else round(px / PX_PER_SIZE, 1)


def enum_get(enum, name):
    try:
        return enum[name]
    except KeyError:
        return None


class RichText(TextSegment):
    """关键词分段上色。"""

    def __init__(self, *a, hl=None, hl_color='#FFD23F', **k):
        super().__init__(*a, **k)
        self.hl, self.hl_color = hl or [], hl_color

    def export_material(self):
        ret = super().export_material()
        if not self.hl:
            return ret
        mark = [False] * len(self.text)
        for w in self.hl:
            for m in re.finditer(re.escape(w), self.text):
                for i in range(m.start(), m.end()):
                    mark[i] = True
        if not any(mark):
            return ret
        c = json.loads(ret['content'])
        base = c['styles'][0]
        styles, i = [], 0
        while i < len(self.text):
            j = i
            while j < len(self.text) and mark[j] == mark[i]:
                j += 1
            s = json.loads(json.dumps(base))
            s['range'] = [i, j]
            if mark[i]:
                s['fill']['content']['solid']['color'] = list(col(self.hl_color))
            styles.append(s)
            i = j
        c['styles'] = styles
        ret['content'] = json.dumps(c, ensure_ascii=False)
        return ret


def vseg(path, t0, t1, **kw):
    """视频片段：素材比要铺的时长短时放慢铺满（成片渲染那边是定格最后一帧），图片直接铺。"""
    if is_image(path):
        return VideoSegment(path, rng(t0, t1), **kw)
    dur = probe(path)['duration'] - 0.002
    src = rng(0, min(dur, t1 - t0)) if dur < t1 - t0 else None
    return VideoSegment(path, rng(t0, t1), source_timerange=src, volume=0, **kw)


NATIVE_MODES = ('full', 'pip', 'aside', 'hidden')   # 剪映草稿能原样搭出来的版式；其余版式用成片画面
BAKE_TITLE_LAYOUTS = ('count', 'number', 'bignum', 'mixline')   # 数字滚动、浮现、一行里大小字混排这类剪映文字做不出


def baked_ranges(tl, st, W, H):
    """剪映做不出来的时间段：抠像、纸页、目录、画框这些版式，带色块、手绘、压暗或人压字的大字，开场冲击。
    这些段落在草稿里铺成片画面（不压字幕的那版），压在上面的大字一起烤进去，避免和剪映文字叠两层。"""
    rs = [(l['t0'], l['t1']) for l in tl.get('layout', [])
          if l['mode'] not in NATIVE_MODES or (l['mode'] == 'aside' and l.get('stack'))]
    if is_landscape(W, H):
        # 横屏手绘和特效沿用成片的安全区与动画，避免剪映原生预设又回到胸口。
        rs += [(x['t0'], x['t1']) for key in ('doodles', 'fx') for x in tl.get(key, [])]
    for t in tl.get('titles', []):
        if t.get('behind') or t.get('layout') in BAKE_TITLE_LAYOUTS + GRAPHIC_LAYOUTS or \
                any(it.get('kind') in ('shape', 'doodle', 'dim') for it in layout_title(t, st, W, H)):
            rs.append((t['t0'], t['t1']))
    if tl.get('_opening'):
        rs.append((0.0, min(0.6, tl['_opening']['dur'])))
    for f in tl.get('fx', []):   # 整屏特效：剪映里有对应特效的放真的，没有的（或人物特效名剪映里没有的）铺成片画面
        if f.get('_from') == 'face':
            continue
        names = fx_jy(f)
        if not names or not all(enum_get(VideoCharacterEffectType, n) or enum_get(VideoSceneEffectType, n) for n in names):
            rs.append((f['t0'], f['t1']))
    while True:   # 和这些段落沾边的大字整条并进来，再合并相邻段
        grown = [(min([a] + [t['t0'] for t in tl.get('titles', []) if t['t0'] < b and t['t1'] > a]),
                  max([b] + [t['t1'] for t in tl.get('titles', []) if t['t0'] < b and t['t1'] > a])) for a, b in rs]
        out = []
        for a, b in sorted(grown):
            if out and a <= out[-1][1] + 0.1:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
        if out == rs:
            return out
        rs = out


TEXT_ANIM = {'pop': '弹入', 'fade': '渐显', 'blur_in': '渐显', 'slide_up': '向上滑动', 'slide_left': '向左滑动', 'type': '打字机_II'}
VIDEO_ANIM = {'fade': '渐显', 'slide_up': '向上滑动', 'slide_left': '向左滑动', 'pop': '放大'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('timeline')
    ap.add_argument('--name', required=True)
    ap.add_argument('--draft-root', default=str(MAC_ROOT))
    ap.add_argument('--film', help='不压字幕的成片（render.py --no-subs）；不给就自动渲一版放 out/draft_assets/clean.mp4')
    a = ap.parse_args()

    tl_path = Path(a.timeline).resolve()
    os.chdir(tl_path.parent)
    tl = load_json(tl_path)
    st = style_preset(tl)
    tl['titles'] = tl.get('titles', []) + expand_beats(tl, st)   # beats 按内容展开的大字（library.py）
    paper_ink(tl)   # 米白纸页上的大字换深色
    structure.prepare(tl, st)   # 首帧封面、一词一镜快剪、段落收尾，和成片一致
    phrase_subs(tl)   # 一词一镜字幕和景别，和成片一致
    audiomix.prepare(tl, st, tl_path.parent)   # 声音先入、按段落排配乐，和成片一致
    expand_shots(tl, st)
    effects.prepare(tl, st)
    cv = tl.get('canvas', {'w': 1080, 'h': 1920, 'fps': 30})
    W, H, FPS = cv['w'], cv['h'], cv['fps']
    aroll = str(Path(tl['aroll']).resolve())
    DUR = tl.get('duration') or probe(aroll)['duration']
    asset = (tl_path.parent / 'out' / 'draft_assets').resolve()   # 草稿引用的素材落在项目目录里，别放临时目录
    asset.mkdir(parents=True, exist_ok=True)

    df = dj.DraftFolder(a.draft_root)
    sf = df.create_draft(a.name, W, H, fps=FPS, allow_replace=True)
    tracks = {}

    def track(kind, name):
        tracks[name] = sf.append_track(TrackSpec(kind, name=name))
        return tracks[name]

    def multi(kind, prefix):
        """可能互相重叠的片段自动分到多条轨道。"""
        lanes = []

        def put(seg, t0, t1):
            for k, (ref, end) in enumerate(lanes):
                if end <= t0 + 1e-6:
                    lanes[k] = (ref, t1)
                    sf.add_segment(seg, ref)
                    return
            ref = sf.append_track(TrackSpec(kind, name=f'{prefix}{len(lanes) + 1}'))
            lanes.append((ref, t1))
            sf.add_segment(seg, ref)
        return put

    # ---------------- 口播主轨：在版式和推近的边界处切段
    track(TrackType.video, '口播')
    layout = tl.get('layout', [])
    zooms = [zoom_preset(z) for z in tl.get('zoom', [])] + auto_zoom(tl, st, tl_path.parent)   # 手写推近 + 自动景别三档
    trans = auto_transitions(tl, st)
    cuts = sorted({0.0, DUR, *[x for l in layout for x in (l['t0'], l['t1'])], *[x for z in zooms for x in (z['t0'], z['t1'])],
                   *[tr['t'] for tr in trans]})
    cuts = [c for c in cuts if 0 <= c <= DUR]
    lufs = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', subprocess.run(['ffmpeg', '-i', aroll, '-af', 'ebur128', '-f', 'null', '-'],
                                                                      capture_output=True, text=True).stderr)[-1])
    vol = round(min(10 ** ((tl.get('audio', {}).get('voice', {}).get('lufs', st['voice_lufs']) - lufs) / 20), 8.0), 3)
    ay = tl.get('zoom_anchor_y', 0.38)
    for t0, t1 in zip(cuts, cuts[1:]):
        if t1 - t0 < 1 / FPS:
            continue
        mid = (t0 + t1) / 2
        mode = next((l['mode'] for l in layout if l['t0'] <= mid < l['t1']), 'full')
        seg = VideoSegment(aroll, rng(t0, t1), source_timerange=rng(t0, t1), volume=vol)
        if mode in ('aside', 'hidden'):
            seg.clip_settings.transform_x = 2.6          # 人移出画面，只留背景填充
            if mode == 'aside':
                seg.add_background_filling('blur', blur=0.375)
            else:
                seg.add_background_filling('color', color='#000000FF')
        z = next((z for z in zooms if z['t0'] <= mid < z['t1']), None)
        if z and mode == 'full':
            e = z.get('ease', st['punch']['dur'])
            f0, f1 = z.get('from', 1.0), z.get('to', st['punch']['scale'])
            off = (0.5 - ay) * 2   # 以人脸附近为锚点放大：放大时同步下移
            for tt, sc in ((0, f0), (min(e, t1 - t0), f1)):
                seg.add_keyframe(KeyframeProperty.uniform_scale, us(tt), sc)
                seg.add_keyframe(KeyframeProperty.position_y, us(tt), -off * (sc - 1))
        tr = next((x for x in trans if abs(x['t'] - t1) < 1e-3), None)
        if tr:   # 剪映的转场挂在切点前面那段上
            tt_ = enum_get(TransitionType, TRANSITIONS.get(tr['type'], {}).get('jy', ''))
            if tt_:
                seg.add_transition(tt_, duration=us(TRANSITIONS[tr['type']]['dur']))
        sf.add_segment(seg, tracks['口播'])

    # ---------------- B-roll（与成片同一批预处理素材）
    put_b = multi(TrackType.video, 'B-roll')
    for i, b in enumerate(tl.get('broll', [])):
        path, bw, bh, img, alpha = prep_broll(i, b, W, H, FPS, st, str(asset), False)
        dst = asset / Path(path).name
        if Path(path).resolve() != dst:
            shutil.copy2(path, dst)
        fit = b.get('fit', 'cover')
        if fit in ('cover', 'double'):
            cs = ClipSettings()
        else:
            default = min(W / bw, H / bh)                 # 剪映默认把素材完整放进画布
            sc = 1 / default
            cs = ClipSettings(scale_x=sc, scale_y=sc, transform_x=tx(b.get('x', 0.5)), transform_y=ty(b.get('y', 0.5)))
        seg = vseg(str(dst), b['t0'], b['t1'], clip_settings=cs) if not img else \
            VideoSegment(str(dst), rng(b['t0'], b['t1']), clip_settings=cs)
        enter = b.get('enter', 'none' if fit in ('cover', 'double') else 'fade')
        an = enum_get(IntroType, VIDEO_ANIM.get(enter, ''))
        if an:
            seg.add_animation(an, us(0.3))
        if b.get('motion', st.get('card_motion')) == 'rise' and fit not in ('cover', 'double'):
            seg.add_keyframe(KeyframeProperty.position_y, 0, ty(b.get('y', 0.5)))
            seg.add_keyframe(KeyframeProperty.position_y, us(b['t1'] - b['t0']), ty(b.get('y', 0.5)) + 0.06)
        put_b(seg, b['t0'], b['t1'])

    # ---------------- 圆形人像小窗
    pips = [l for l in layout if l['mode'] == 'pip']
    if pips:
        track(TrackType.video, '人像小窗')
        for pi, l in enumerate(pips):
            p = pip_params(l, st)
            d = int(W * p['d']) // 2 * 2
            bw_ = int(p.get('border', 0) * unit(W, H))
            f = asset / f'pip{pi}.mov'
            D = pip_clip(aroll, l['t0'], l['t1'], W, H, FPS, d, l.get('crop'), bw_, p.get('border_color', '#FFFFFF'), f, p.get('feather', 0))
            # 剪映默认把正方形按短边放进画布，横屏不能再除以画宽。
            sc = D / (H if is_landscape(W, H) else W)
            sf.add_segment(vseg(str(f), l['t0'], l['t1'],
                                clip_settings=ClipSettings(scale_x=sc, scale_y=sc, transform_x=tx(p['x']), transform_y=ty(p['y']))),
                           tracks['人像小窗'])

    # ---------------- 叠加物（贴纸图、透明动画）
    put_o = multi(TrackType.video, '叠加')
    for i, o in enumerate(tl.get('overlays', [])):
        src = to_png(o['src'], str(asset)) if is_image(o['src']) else str(Path(o['src']).resolve())
        info = probe(src)
        ow = 1080 * unit(W, H) * o.get('w', 0.3)
        ox, oy = 0.5, 0.5
        if is_landscape(W, H):
            x0, y0, x1, y1 = side_box(o, W, H)
            ow = min(ow, x1 - x0, (y1 - y0) * info['w'] / info['h'])
            cx, cy = side_center(o, W, H)
            ox, oy = cx / W, cy / H
        sc = ow / (info['w'] * min(W / info['w'], H / info['h']))
        put_o(vseg(src, o['t0'], o['t1'], clip_settings=ClipSettings(scale_x=sc, scale_y=sc, transform_x=tx(o.get('x', ox)),
                                                                                  transform_y=ty(o.get('y', oy)))), o['t0'], o['t1'])
    for s in tl.get('stickers', []):  # 剪映自带贴纸，只在草稿里有
        rid = (RES['sticker'].get(s['name']) or {}).get('resource_id') or s.get('resource_id')
        if rid:
            sx, sy = side_center(s, W, H) if is_landscape(W, H) else (W / 2, H / 2)
            sf.add_segment(StickerSegment(rid, rng(s['t0'], s['t1']), clip_settings=ClipSettings(
                scale_x=s.get('scale', 0.5), scale_y=s.get('scale', 0.5), transform_x=tx(s.get('x', sx / W)), transform_y=ty(s.get('y', sy / H)))),
                sf.append_track(TrackSpec(TrackType.sticker, name=f"贴纸{s['name'][:6]}{s['t0']}")))

    # ---------------- 剪映做不出来的段落：铺不压字幕的成片画面，剪映文字字幕照常叠在上面
    baked = baked_ranges(tl, st, W, H)
    if baked:
        film = Path(a.film).resolve() if a.film else asset / 'clean.mp4'
        if not a.film and (not film.exists() or film.stat().st_mtime < tl_path.stat().st_mtime):
            print('渲染不压字幕的成片，给剪映做不出来的段落用……')
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'render.py'), str(tl_path), '-o', str(film), '--no-subs'],
                           check=True, stdout=subprocess.DEVNULL)
        track(TrackType.video, '成片画面')
        end = probe(str(film))['duration'] - 0.002
        for t0, t1 in baked:
            t1 = min(t1, end)
            sf.add_segment(VideoSegment(str(film), rng(t0, t1), source_timerange=rng(t0, t1), volume=0), tracks['成片画面'])
        print(f"成片画面 {len(baked)} 段，共 {sum(b - a for a, b in baked):.1f} 秒（剪映做不出来的版式和大字）")

    # ---------------- 剪映特效（只在草稿里有）
    effect_end = {}
    native = [{'t0': f['t0'], 't1': f['t1'], 'name': n} for f in tl.get('fx', []) if f.get('_from') != 'face'
              for n in fx_jy(f) if enum_get(VideoCharacterEffectType, n) or enum_get(VideoSceneEffectType, n)]
    for x in tl.get('inserts', []):
        print(f"梗片段 {x['src']} 要在剪映里手动插到 {x['t']:.1f} 秒（草稿不插，插了后面整条要后移）")
    if tl.get('points') or tl.get('hud'):   # 常驻层只在成片里叠
        print('角落要点编号、系列名水印、进度条只在成片里有，草稿里要的话在剪映加文字轨')
    if tl.get('badge_bar'):
        print('口播上移底部留黑只在成片里有，草稿里要的话在剪映底部加一条黑色色块和角标贴纸')
    if any(t.get('layout') == 'jytpl' for t in tl.get('titles', [])):
        print('剪映综艺文字模板（前方高能、警告、OUT、啊啊啊）成片里是近似画法，草稿里铺的是成片画面，想换真模板在剪映文字模板里搜同名替换')
    for e in tl.get('effects', []) + [x for x in native if not any(b0 <= x['t0'] and x['t1'] <= b1 for b0, b1 in baked)]:
        et = enum_get(VideoCharacterEffectType, e['name']) or enum_get(VideoSceneEffectType, e['name'])
        if not et:
            print('剪映里没有这个特效，跳过：', e['name'])
            continue
        lane = None
        for k in range(20):
            name = f'特效{k + 1}'
            if name not in tracks:
                tracks[name] = sf.append_track(TrackSpec(TrackType.effect, name=name))
                effect_end[name] = 0
            if effect_end[name] <= e['t0'] + 1e-6:
                lane = name
                break
        sf.add_effect(et, rng(e['t0'], e['t1']), track_name=lane)
        effect_end[lane] = e['t1']

    # ---------------- 字幕与大字
    # 字体按角色取剪映里对应的字体；timeline 的 fonts.jy_<角色> 可以指定剪映字体名
    fover = tl.get('fonts') or {}

    def jy_font(role):
        name = fover.get(f'jy_{role}') or find_role_font(role, tl.get('style', 'premium'))[2]
        return enum_get(FontType, name) or FontType.SourceHanSansCN_Bold

    font = jy_font('sub')
    sub = st['sub']
    pip_ranges = pip_sub_ranges(pips, st)
    track(TrackType.text, '字幕')

    def text_kw(cfg, color=None):
        kw = dict(style=TextStyle(size=size_of(cfg['size'] * unit(W, H), W), color=col(color or cfg['color']), bold=cfg.get('bold', False), align=1,
                                  letter_spacing=int(cfg.get('spacing', 0))))
        if cfg.get('outline'):
            kw['border'] = TextBorder(color=col(cfg.get('outline_color', '#000000')), width=min(100, cfg['outline'] * 10))
        if cfg.get('shadow_alpha') is not None:
            kw['shadow'] = TextShadow(alpha=cfg['shadow_alpha'] / 255, color=(0, 0, 0), diffuse=18, distance=4, angle=-60)
        if cfg.get('box'):   # 半透明圆角底条：剪映文字自带「背景」
            kw['background'] = TextBackground(color=cfg['box']['color'][:7], alpha=cfg['box']['alpha'], round_radius=1.0,
                                              height=0.18, width=0.12)
        return kw

    for s in tl.get('subs', []):
        key = s.get('level') == 'key'
        cfg = sub['key'] if key else sub['base']
        shrink = subtitle_scale(s['text'], cfg, sub, W, H)
        if shrink != 1:
            cfg = {**cfg, 'size': cfg['size'] * shrink, 'spacing': cfg.get('spacing', 0) * shrink}
        mid = (s['t0'] + s['t1']) / 2
        y = s.get('y', sub['pip_y'] if any(x <= mid < y_ for x, y_ in pip_ranges) else cfg['y'])
        seg = RichText(s['text'], rng(s['t0'], s['t1']), font=jy_font('sub_key' if key else 'sub'), clip_settings=ClipSettings(transform_y=ty(y)), hl=s.get('hl'),
                       hl_color=sub['hl_color'], **text_kw(cfg))
        if key:
            an = enum_get(TextIntro, TEXT_ANIM.get(s.get('anim', 'pop'), '弹入'))
            if an:
                seg.add_animation(an, us(0.3))
        fl = RES['flower'].get(s.get('jy_flower', ''))
        if fl:
            seg.add_effect(fl['effect_id'])
        sf.add_segment(seg, tracks['字幕'])

    put_t = multi(TrackType.text, '大字')
    tcfg = st['title']
    # 大字：和成片共用 typeset.layout_title 的排版结果，每个文字项落成一段剪映文字
    for t in tl.get('titles', []):
        if any(a_ <= t['t0'] and t['t1'] <= b_ for a_, b_ in baked):
            continue          # 已经在成片画面里
        kind = t.get('anim', tcfg.get('anim', 'blur_in'))
        for it in layout_title(t, st, W, H):
            if it.get('kind') in ('shape', 'doodle'):   # 色块、标签底板、手绘元素还没同步到剪映草稿（效果定了再做）
                continue
            if it.get('kind') == 'dim':
                continue          # 整屏压暗在剪映里用「背景」或调节层更方便，草稿里不做
            lines = it['text'].replace('\\N', '\n').split('\n')
            w = max(text_w(l, it['size'], it.get('condense', 100)) for l in lines)
            h = it['size'] * len(lines)
            an = it['an']
            cx = it['x'] + (w / 2 if an == 7 else -w / 2 if an == 9 else 0)
            cy = it['y'] + (h / 2 if an in (7, 8, 9) else 0)
            if is_landscape(W, H):
                # 侧栏也会用左中、右中和底部锚点，先换成剪映需要的中心位置。
                cx = it['x'] + (w / 2 if an in (1, 4, 7) else -w / 2 if an in (3, 6, 9) else 0)
                cy = it['y'] + (h / 2 if an in (7, 8, 9) else -h / 2 if an in (1, 2, 3) else 0)
            alpha = it.get('alpha', 1) * (0.35 if it.get('hollow') else 1)
            style = TextStyle(size=size_of(it['size'], W), color=col(it['color']), alpha=alpha, align={7: 0, 9: 2}.get(an, 1),
                              letter_spacing=int(it.get('spacing', 0) / max(unit(W, H), 0.01) / 4))
            if is_landscape(W, H):
                style.align = 0 if an in (1, 4, 7) else 2 if an in (3, 6, 9) else 1
            kw = dict(style=style)
            if it.get('shadow'):
                kw['shadow'] = TextShadow(alpha=tcfg.get('shadow_alpha', 0x90) / 255, color=(0, 0, 0), diffuse=18, distance=5, angle=-60)
            if it.get('outline'):
                kw['border'] = TextBorder(color=col(it.get('outline_color', '#000000')), width=min(100, it['outline'] * 10))
            if it.get('box'):
                kw['background'] = TextBackground(color=it['box'][:7], alpha=hex_rgba(it['box'])[3] / 255, round_radius=0.3)
            t0 = t['t0'] + it.get('delay', 0)
            seg = RichText('\n'.join(lines), rng(t0, t['t1']), font=jy_font(it['role']), hl=it.get('hl'), hl_color=it.get('hl_color', it['color']),
                           clip_settings=ClipSettings(transform_x=tx(cx / W), transform_y=ty(cy / H), scale_x=it.get('condense', 100) / 100,
                                                      rotation=-it.get('rot', 0)), **kw)
            an_name = enum_get(TextIntro, TEXT_ANIM.get(kind, '渐显'))
            if an_name:
                seg.add_animation(an_name, us(min(0.4, (t['t1'] - t0) / 2)))
            fl = RES['flower'].get(t.get('jy_flower', ''))
            if fl:
                seg.add_effect(fl['effect_id'])
            put_t(seg, t0, t['t1'])

    # ---------------- 声音
    au = tl.get('audio', {})
    bgm_list = tl.get('_bgm') or expand_bgm(tl, tl_path.parent)   # 按段落排好的配乐（audiomix.music_plan）
    put_m = multi(TrackType.audio, 'BGM')   # 换曲交叉淡化时两段重叠，放两条轨
    if bgm_list:
        for m in bgm_list:
            d = m['t1'] - m['t0']
            src_dur = dj.AudioMaterial(m['src']).duration / 1e6 - 0.002
            src_in = m.get('src_in', 0)
            t, k = m['t0'], 0
            while t < m['t1'] - 1e-3:          # 配乐不够长就首尾相接循环
                piece = min(m['t1'] - t, src_dur - (src_in if k == 0 else 0))
                seg = AudioSegment(m['src'], rng(t, t + piece), source_timerange=rng(src_in if k == 0 else 0, (src_in if k == 0 else 0) + piece),
                                   volume=round(10 ** (bgm_gain_db(m, st) / 20), 3))
                fin = us(m.get('fade_in', 0.5)) if k == 0 else 0
                fout = us(m.get('fade_out', 1.0)) if t + piece >= m['t1'] - 1e-3 else 0
                if fin or fout:
                    seg.add_fade(fin, fout)
                put_m(seg, t, t + piece)
                t += piece
                k += 1
    put_s = multi(TrackType.audio, '音效')
    for s in all_sfx(tl, st, tl_path.parent):
        d = min(dj.AudioMaterial(s['src']).duration / 1e6 - 0.002, DUR - s['t'], s.get('dur') or 1e9)   # 升调串的音高剪映里要手调
        put_s(AudioSegment(s['src'], rng(s['t'], s['t'] + d), volume=round(10 ** (sfx_gain_db(s, st) / 20), 3)), s['t'], s['t'] + d)

    sf.save()
    dp = Path(a.draft_root) / a.name
    shutil.copy(dp / 'draft_content.json', dp / 'draft_info.json')   # 剪映 Mac 11.x 读 draft_info.json
    print('剪映草稿已生成：', dp)


if __name__ == '__main__':
    main()
