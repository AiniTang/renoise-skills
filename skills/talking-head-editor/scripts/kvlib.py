"""口播剪辑脚本共用的工具：媒体信息、字体查找、风格预设、卡片绘制。

render.py 和 build_draft.py 都从这里取样式，保证成片和剪映草稿长得一样。
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from fonts import ensure as ensure_fonts
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- 画布

def unit(W, H):
    """字号、描边、圆角等尺寸的倍率：短边 / 1080。竖屏仍是原来的 W / 1080。"""
    return min(W, H) / 1080


def is_landscape(W, H):
    """宽大于高才算横屏，正方形沿用竖屏规则。"""
    return W > H


def safe_zones(W, H):
    """人物居中的默认留白，都是画面比例，矩形写 (左, 上, 右, 下)。不是人脸检测结果。
    横屏中间四成留给人，两侧可放字；竖屏字放胸口。sub 是字幕中心，sub_width 是最大行宽。
    """
    if is_landscape(W, H):
        return dict(face=(0.30, 0.10, 0.70, 0.78), text=((0.04, 0.15, 0.30, 0.75), (0.70, 0.15, 0.96, 0.75)),
                    sub=(0.5, 0.88), sub_width=0.70)
    return dict(face=(0.20, 0.10, 0.80, 0.47), text=((0.06, 0.55, 0.94, 0.75),), sub=(0.5, 0.80), sub_width=0.90)


def canvas_size(value):
    """命令行 WxH，编码要求宽高是正偶数。"""
    m = re.fullmatch(r'([0-9]+)[xX×]([0-9]+)', value)
    if not m or any(int(n) < 2 or int(n) % 2 for n in m.groups()):
        raise ValueError('画布请写正偶数宽高，例如 1920x1080')
    return tuple(map(int, m.groups()))


def canvas_for_source(src=None, canvas=None, fps=30):
    """显式画布优先，否则按源的显示方向选 1080P；没有源就沿用竖屏。"""
    if canvas:
        w, h = canvas_size(canvas) if isinstance(canvas, str) else canvas_size(f'{canvas[0]}x{canvas[1]}')
    else:
        p = probe(src) if src else dict(w=1080, h=1920)
        w, h = (1920, 1080) if is_landscape(p['w'], p['h']) else (1080, 1920)
    return dict(w=w, h=h, fps=fps)


def face_crop(W, H, crop=None):
    """人像正方形 (边长, 左, 上)，像素值。手写 crop 仍相对宽度，越界就缩小并收回画内。"""
    c = crop or (dict(x=(W - H) / (2 * W), y=0, s=H / W) if is_landscape(W, H) else dict(x=0, y=0.08, s=1))
    s = min(W, H, max(2, c['s'] * W))
    return s, min(max(0, c['x'] * W), W - s), min(max(0, c['y'] * W), H - s)

# ---------------------------------------------------------------- 媒体信息

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe(path):
    """返回 {'duration', 'w', 'h', 'fps', 'has_audio', 'rotation', 'is_image', 'alpha'}。alpha 表示带透明通道。"""
    out = run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]).stdout
    info = json.loads(out)
    v = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    res = {'duration': float(info['format'].get('duration', 0) or 0), 'has_audio': a is not None,
           'w': 0, 'h': 0, 'fps': 0.0, 'rotation': 0, 'is_image': False, 'alpha': False}
    if v:
        w, h = int(v.get('width', 0)), int(v.get('height', 0))
        rot = 0
        for sd in v.get('side_data_list', []) or []:
            if 'rotation' in sd:
                rot = int(float(sd['rotation']))
        rot = int(v.get('tags', {}).get('rotate', rot)) % 360
        if rot in (90, 270, -90):
            w, h = h, w
        res.update(w=w, h=h, rotation=rot)
        num, _, den = (v.get('avg_frame_rate') or '0/1').partition('/')
        res['fps'] = float(num) / float(den or 1) if float(den or 1) else 0.0
        pf = v.get('pix_fmt', '')
        res['alpha'] = pf.startswith(('yuva', 'rgba', 'argb', 'bgra', 'abgr', 'ya', 'gbrap')) or pf in ('pal8',)
        res['is_image'] = v.get('codec_name') in ('png', 'mjpeg', 'webp', 'bmp', 'tiff', 'gif') and res['duration'] < 0.5
    return res


IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.heic', '.gif', '.tif', '.tiff'}


def is_image(path):
    return Path(path).suffix.lower() in IMAGE_EXT


def to_png(path, out_dir):
    """HEIC 等格式转成 PNG，返回可被 ffmpeg/PIL 读取的路径。"""
    p = Path(path)
    if p.suffix.lower() not in ('.heic', '.heif'):
        return str(p)
    out = Path(out_dir) / (p.stem + '.png')
    if not out.exists():
        if shutil.which('sips'):
            run(['sips', '-s', 'format', 'png', str(p), '--out', str(out)])
        else:
            run(['ffmpeg', '-v', 'error', '-y', '-i', str(p), str(out)])
    return str(out)


# ---------------------------------------------------------------- 字体

FONT_CANDIDATES = {
    # 高级感偏好硬朗黑体；综艺感偏好圆润粗体。都没有就退到系统中文字体。
    'premium': ['欣意冠黑体', 'XinYiGuanHeiTi', '思源黑体', 'Source Han Sans SC', 'SourceHanSansSC', 'Noto Sans SC', 'NotoSansSC',
                'Noto Sans CJK SC', 'PingFang SC', 'Hiragino Sans GB'],
    'variety': ['得意黑', 'Smiley Sans', 'SmileySans', '站酷快乐体', 'ZCOOL KuaiLe', '思源黑体', 'Noto Sans SC', 'NotoSansSC',
                'Noto Sans CJK SC', 'PingFang SC', 'Hiragino Sans GB'],
}

FONT_DIRS = [Path.home() / 'Library/Fonts', Path('/Library/Fonts'), Path('/System/Library/Fonts'),
             Path('/System/Library/Fonts/Supplemental'), Path('/usr/share/fonts'), Path.home() / '.fonts',
             Path.home() / '.local/share/fonts', ensure_fonts(quiet=False)]


def _font_files():
    for d in FONT_DIRS:
        if d.exists():
            for p in d.rglob('*'):
                if p.suffix.lower() in ('.ttf', '.otf', '.ttc'):
                    yield p


def font_family(path):
    """读出字体文件的族名（libass 用族名找字体）。"""
    try:
        from PIL import ImageFont
        return ImageFont.truetype(str(path), 20).getname()[0]
    except Exception:
        return Path(path).stem


def find_font(style='premium', explicit=None):
    """返回 (字体文件路径, 族名)。explicit 可以是文件路径或族名。"""
    if explicit and Path(explicit).exists():
        return str(explicit), font_family(explicit)
    wanted = ([explicit] if explicit else []) + FONT_CANDIDATES.get(style, FONT_CANDIDATES['premium'])
    files = list(_font_files())
    for name in wanted:
        key = name.lower().replace(' ', '')
        for f in files:
            if key in f.stem.lower().replace(' ', '').replace('-', ''):
                return str(f), font_family(f)
    for f in files:
        fam = font_family(f)
        if any(n.lower().replace(' ', '') == fam.lower().replace(' ', '') for n in wanted):
            return str(f), fam
    raise SystemExit('找不到中文字体：请安装思源黑体 / Noto Sans SC，或在 timeline.json 的 fonts 里指定字体文件路径')


# ---------------------------------------------------------------- 字体角色
# 每种风格给每个「角色」指定字体（按优先顺序），字体第一次用时下载（清单见 assets/fonts/fonts.json，说明见那里的 README）。
# 名字写「族名 字重」，libass 能据此精确选中字重。jy 是剪映里最接近的字体（剪映自带优设标题黑、毛笔行楷等，草稿里直接用）。
FONT_ROLES = {
    'premium': {
        'sub':        (['Source Han Sans CN Bold', 'Noto Sans SC', 'PingFang SC'], 'SourceHanSansCN_Bold'),
        'sub_key':    (['Source Han Sans CN Heavy', 'Source Han Sans CN Bold', 'Noto Sans SC'], 'SourceHanSansCN_Bold'),
        'title':      (['Source Han Sans CN Heavy', 'Source Han Sans CN Bold', 'Noto Sans SC'], '优设标题黑'),
        'serif':      (['Source Han Serif CN Heavy', 'Source Han Serif CN Bold', 'Songti SC'], '思源粗宋'),
        'body':       (['Source Han Sans CN Medium', 'Noto Sans SC', 'PingFang SC'], 'SourceHanSansCN_Medium'),
        'hand':       (['Ma Shan Zheng', 'Zhi Mang Xing'], '毛笔行楷'),
        'note':       (['Zhi Mang Xing', 'Ma Shan Zheng'], '飞扬行书'),
        'en':         (['Oswald SemiBold', 'Bebas Neue', 'Helvetica Neue'], 'Anton'),
        'en_display': (['Anton', 'Bebas Neue', 'Oswald Bold'], 'Anton'),
        'en_serif':   (['Instrument Serif Italic', 'DM Serif Display Italic', 'Cormorant Garamond Medium Italic'], 'PlayfairDisplay_Italic'),
    },
    'variety': {
        'sub':        (['DouyinSans Bold', 'Source Han Sans CN Heavy', 'Noto Sans SC'], '抖音美好体'),
        'sub_key':    (['ZCOOL QingKe HuangYou', 'DouyinSans Bold', 'Source Han Sans CN Heavy'], '抖音美好体'),
        'title':      (['ZCOOL QingKe HuangYou', 'Smiley Sans Oblique', 'Source Han Sans CN Heavy'], '得意黑'),
        'serif':      (['Source Han Serif CN Heavy', 'Songti SC'], '思源粗宋'),
        'body':       (['DouyinSans Bold', 'Source Han Sans CN Bold', 'Noto Sans SC'], '抖音美好体'),
        'hand':       (['ZCOOL KuaiLe', 'Smiley Sans Oblique'], '得意黑'),
        'note':       (['ZCOOL KuaiLe', 'Zhi Mang Xing'], '得意黑'),
        'en':         (['Montserrat ExtraBold', 'Oswald Bold'], 'Montserrat_Black'),
        'en_display': (['Anton', 'Montserrat ExtraBold'], 'Anton'),
        'en_serif':   (['DM Serif Display Italic', 'Instrument Serif Italic'], 'PlayfairDisplay_Italic'),
    },
}
ROLES = list(FONT_ROLES['premium'])


def _font_index():
    idx = {}
    for f in _font_files():
        try:
            from PIL import ImageFont
            fam, sty = ImageFont.truetype(str(f), 20).getname()
        except Exception:
            continue
        for key in {f'{fam} {sty}'.lower(), fam.lower(), f.stem.lower()}:
            idx.setdefault(key, (str(f), fam, sty))
    return idx


_FIDX = None


def _ass_name(path, fam, sty):
    """libass 用的字体名。常规字重写族名；Bold、Italic 这类「标准字重」按全名找会找错并悄悄换成别的字体，
    改成族名加 \\b1、\\i1 标记；SemiBold、Heavy 这类非标准字重写「族名 字重」。"""
    flags = {'Bold': '\\b1\\i0', 'Italic': '\\b0\\i1', 'Bold Italic': '\\b1\\i1'}.get(sty)
    if flags:
        return fam + flags
    return (fam if sty in ('Regular', 'Book', 'Normal') else f'{fam} {sty}') + '\\b0\\i0'   # 显式清掉上一个字体的粗斜体标记


def find_role_font(role, style='premium', override=None):
    """返回 (字体文件, libass 用的名字, 剪映字体枚举名)。override 可以是文件路径或「族名 字重」。"""
    global _FIDX
    names, jy = FONT_ROLES.get(style, FONT_ROLES['premium']).get(role, FONT_ROLES['premium']['sub'])
    if override and Path(override).exists():
        from PIL import ImageFont
        fam, sty = ImageFont.truetype(str(override), 20).getname()
        return str(override), _ass_name(override, fam, sty), jy
    if _FIDX is None:
        _FIDX = _font_index()
    for n in ([override] if override else []) + names:
        hit = _FIDX.get(n.lower())
        if hit:
            path, fam, sty = hit
            return path, _ass_name(path, fam, sty), jy
    p, fam = find_font(style)
    return p, fam, jy


# ---------------------------------------------------------------- 音量测量
_LOUD = {}


def audio_level(path):
    """返回 (整体响度 LUFS, 峰值 dBFS)，结果按文件缓存。配乐按响度对齐，音效按峰值对齐，曲库里每首音量差很多。"""
    key = str(Path(path).resolve())
    if key not in _LOUD:
        err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', key, '-vn', '-af', 'ebur128=peak=sample', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr
        i = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
        pk = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', err)
        _LOUD[key] = (float(i[-1]) if i else -20.0, float(pk[-1]) if pk else -1.0)
    return _LOUD[key]


def bgm_gain_db(m, st):
    """配乐增益：把这首曲子拉到风格的目标响度，再加上 timeline 里写的 db 微调。"""
    lufs, _ = audio_level(m['src'])
    return round(m.get('lufs', st['bgm_lufs']) - lufs + m.get('db', 0), 2)


def sfx_gain_db(s, st):
    """音效增益：earshot 按配乐算好的增益（gain）优先；否则峰值对齐到风格的目标峰值。两种都再加 db 微调。"""
    if 'gain' in s:
        return round(s['gain'] + s.get('db', 0), 2)
    _, peak = audio_level(s['src'])
    return round(st['sfx_peak'] - peak + s.get('db', 0), 2)


# ---------------------------------------------------------------- 自动配音效的音效库
# Mixkit 音效（可商用、不用署名，授权不允许随 Skill 分发，用到时下载到项目 sfx/kit/）。
# 每类准备几种，按顺序轮换，相邻两次不重复，避免听觉疲劳。title 大字出现，chapter 章节页，broll 素材出场。
SFX_KITS = {
    'premium': {
        'title': [
            dict(name='Fast small sweep transition', url='https://assets.mixkit.co/active_storage/sfx/166/166.wav'),
            dict(name='Short wind swoosh', url='https://assets.mixkit.co/active_storage/sfx/1461/1461.wav'),
            dict(name='Fast transitions swoosh', url='https://assets.mixkit.co/active_storage/sfx/3115/3115.wav'),
            dict(name='Fast whoosh transition', url='https://assets.mixkit.co/active_storage/sfx/1490/1490.wav'),
        ],
        'chapter': [
            dict(name='Short bass hit', url='https://assets.mixkit.co/active_storage/sfx/2299/2299.wav'),
            dict(name='Futuristic bass hit', url='https://assets.mixkit.co/active_storage/sfx/2303/2303.wav'),
            dict(name='Cinematic whoosh deep impact', url='https://assets.mixkit.co/active_storage/sfx/1143/1143.wav'),
        ],
        'broll': [
            dict(name='Explainer video pops whoosh light pop', url='https://assets.mixkit.co/active_storage/sfx/3005/3005.wav', db=-5),
            dict(name='Camera shutter click', url='https://assets.mixkit.co/active_storage/sfx/1133/1133.wav', db=-6),
            dict(name='Hard pop click', url='https://assets.mixkit.co/active_storage/sfx/2364/2364.wav', db=-6),
            dict(name='Modern technology select', url='https://assets.mixkit.co/active_storage/sfx/3124/3124.wav', db=-6),
        ],
    },
    'variety': {
        'title': [
            dict(name='Explainer video pops whoosh light pop', url='https://assets.mixkit.co/active_storage/sfx/3005/3005.wav'),
            dict(name='Long pop', url='https://assets.mixkit.co/active_storage/sfx/2358/2358.wav'),
            dict(name='Soap bubble sound', url='https://assets.mixkit.co/active_storage/sfx/2925/2925.wav'),
            dict(name='Hard pop click', url='https://assets.mixkit.co/active_storage/sfx/2364/2364.wav'),
        ],
        'chapter': [
            dict(name='Knocking sub bass', url='https://assets.mixkit.co/active_storage/sfx/2300/2300.wav'),
            dict(name='Quick bass switch', url='https://assets.mixkit.co/active_storage/sfx/2301/2301.wav'),
            dict(name='Wood hard hit', url='https://assets.mixkit.co/active_storage/sfx/2182/2182.wav'),
        ],
        'broll': [
            dict(name='Select click', url='https://assets.mixkit.co/active_storage/sfx/1109/1109.wav', db=-4),
            dict(name='Cool interface click tone', url='https://assets.mixkit.co/active_storage/sfx/2568/2568.wav', db=-4),
            dict(name='Short wind swoosh', url='https://assets.mixkit.co/active_storage/sfx/1461/1461.wav', db=-4),
            dict(name='Camera shutter click', url='https://assets.mixkit.co/active_storage/sfx/1133/1133.wav', db=-4),
        ],
    },
}


def kit_file(item, base, full=False):
    """音效库里的一个音效：第一次用时下载，剪到最长 2 秒、最后 50 毫秒淡出（铺满一段的环境声留 30 秒，用时按长度截），
    记下起音（响到峰值十分之一）和最响的那一刻在第几秒。返回 (文件路径, {'onset', 'peak'})。"""
    import urllib.request
    kit = Path(base) / 'sfx/kit'
    stem = re.sub(r'[^\w-]+', '_', item['name']).strip('_') + ('_full' if full else '')
    f, meta = kit / f'{stem}.wav', kit / f'{stem}.json'
    if not (f.exists() and meta.exists() and json.loads(meta.read_text(encoding='utf-8')).get('v') == 2):
        kit.mkdir(parents=True, exist_ok=True)
        raw = kit / f'{stem}.raw.wav'
        req = urllib.request.Request(item['url'], headers={'User-Agent': 'Mozilla/5.0 talking-head-editor'})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw.write_bytes(r.read())
        n = 30 if full else 2.0
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-t', str(n), '-af', f'afade=t=out:st={n - 0.05}:d=0.05',
                        '-ar', '48000', '-ac', '2', str(f)], check=True)
        raw.unlink()
        meta.write_text(json.dumps({**onset_peak(f), 'v': 2}), encoding='utf-8')
    return f, json.loads(meta.read_text(encoding='utf-8'))


def onset_peak(path, rate=16000):
    """音效文件的起音和峰值时刻（秒）：起音 = 包络第一次到峰值的十分之一（-20 dB），和剪辑里「波形起来的那一下」一致。"""
    import array
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'],
                         capture_output=True).stdout
    a = [abs(x) for x in array.array('h', pcm)]
    if not a:
        return {'onset': 0.0, 'peak': 0.0}
    w = max(1, rate // 500)   # 2 毫秒包络（采样率不能低，打字、点击这类高频声音降采样后起音会量晚）
    env = [max(a[i:i + w]) for i in range(0, len(a), w)]
    pk = max(range(len(env)), key=env.__getitem__)
    on = next(i for i, v in enumerate(env) if v >= env[pk] * 0.1)
    return {'onset': round(on * w / rate, 3), 'peak': round(pk * w / rate, 3)}


# 声音清单：Agent 在时间线里给动画、关键词标的 sound 只能从这里选（受控字段，代码能校验）。
# role = earshot launch 预设里的角色；bank = earshot 音效库编号（按需渲染）；mixkit = (类别, 曲名)，earshot 没有的生活音效。
# span = 铺满一段时间的声音（打字、滴答）；没写 span 的是一下。fallback = 没装 earshot 时用的 Mixkit 音效。
SOUNDS = {
    'whoosh':     dict(role='whoosh.short', use='快速划过、切换、元素飞入', fallback=('swoosh', 'Fast small sweep transition')),
    'whoosh_big': dict(role='whoosh.long', use='大段转场、章节切换', fallback=('transition', 'Cinematic whoosh fast transition')),
    'pop':        dict(role='pop', use='气泡、卡片、标签弹出', fallback=('pop', 'Explainer video pops whoosh light pop')),
    'click':      dict(role='click', use='点按钮、选中', fallback=('click', 'Select click')),
    'tap':        dict(role='land.light', use='轻轻放下、轻点', fallback=('click', 'Modern technology select')),
    'knock':      dict(role='tock', use='木块敲击，强调一个词', fallback=('pop', 'Hard pop click')),
    'thump':      dict(role='land', use='东西落地、大字砸下来', fallback=('bass', 'Short bass hit')),
    'snap':       dict(role='snap', use='快门、截图、定格、快速推近', fallback=('click', 'Camera shutter click')),
    'hit':        dict(role='hit', use='重击：重点数字、结论落地（全片少用）', fallback=('bass', 'Short bass hit')),
    'drop':       dict(role='drop', use='低音下沉：转折、坏消息', fallback=('bass', 'Knocking sub bass')),
    'swell':      dict(role='swell', use='反向镲片：揭晓前的吸气感', fallback=('swoosh', 'Cinematic wind swoosh')),
    'riser':      dict(role='riser', use='上升音：期待、数字往上涨', fallback=('transition', 'Air zoom vacuum')),
    'bell':       dict(role='bell', use='清脆铃声：关键词、灵感、对了', fallback=('click', 'Cool interface click tone')),
    'ding':       dict(role='click.confirm', use='提示音：消息、完成一步', fallback=('click', 'Cool interface click tone')),
    'typing':     dict(bank='pro_typing_run/soft', span=True, use='打字动画、输入框里出字、代码一行行出现', fallback=('typewriter', 'Keyboard typing')),
    'tick':       dict(role='tick', span=True, every=0.09, use='数字滚动、进度条、倒计时、列表滚动', fallback=('click', 'Select click')),
    'glitch':     dict(bank='glitch/hit', use='出错、故障、画面撕裂、AI 失忆', fallback=('wrong', 'Wrong answer fail notification')),
    'shimmer':    dict(bank='pro_shimmer/m3', use='闪光、AI 生成、变魔术、高光时刻', fallback=('magic', 'Magic sparkle whoosh')),
    'zip_up':     dict(bank='pro_zip/up', use='往上滑、数值变好', fallback=('swoosh', 'Short wind swoosh')),
    'zip_down':   dict(bank='pro_zip/down', use='往下滑、数值变差', fallback=('swoosh', 'Short wind swoosh')),
    'fall':       dict(bank='downlifter/tape', use='往下掉、崩了、额度耗尽', fallback=('wrong', 'Funny fail low tone')),
    'drip':       dict(bank='drip/plink', use='一滴一滴、逐个出现的小元素', fallback=('pop', 'Soap bubble sound')),
    'trash':      dict(mixkit=('trash', 'Trash can whoosh tone'), use='清空、删除、扔掉、文件夹被清空'),
    'crumple':    dict(mixkit=('paper', 'Papers being moved or wrinkling'), use='揉纸、推翻重来'),
    'page':       dict(mixkit=('paper', 'Page turn single'), use='翻页、文档、报告'),
    'error':      dict(mixkit=('wrong', 'Wrong answer fail notification'), use='报错、答错、翻车（综艺感更常用）'),
    'success':    dict(mixkit=('success', 'Success software tone'), use='成功、搞定、通过'),
    'coins':      dict(mixkit=('cash', 'Clinking coins'), use='钱、付费、省钱'),
    'door':       dict(mixkit=('door', 'Heavy sliding door'), use='开门转场：推开一扇门进入下一段'),
    'mech_door':  dict(mixkit=('robot', 'Mechanical technology movements'), use='机械开合：分屏左右拉开、面板展开'),
    'mech_robot': dict(mixkit=('robot', 'Machine activation short'), use='机器启动：工具、Agent 开始干活'),
    'mech_wind':  dict(mixkit=('clock', 'Watch clock knob spin'), use='上发条：准备、蓄力、倒计时开始'),
    'zoom_in':    dict(mixkit=('robot', 'User interface zoom in'), use='画面推近、卡片放大铺满'),
    'zoom_out':   dict(mixkit=('robot', 'UI zoom out'), use='画面拉远、口播缩成卡片或小窗'),
    'suspense_tap': dict(mixkit=('game-show', 'Game show suspense waiting'), span=True, use='疑惑、悬念：抛出问题等答案'),
    'dun_dun_duun': dict(mixkit=('game-show', 'Ominous drums'), heavy=True, use='戏剧性重音：反转、真相揭晓（全片一两次）'),
    'cheer_shout': dict(mixkit=('crowd', 'Stadium joy shouting crowd'), heavy=True, use='欢呼吆喝：情绪突变换曲、高光时刻'),
    'bass_hit':   dict(mixkit=('robot', 'Quick bass switch'), use='贝斯单音：包装出现前垫一下低音'),
    'blade_swish': dict(mixkit=('sword', 'Sword blade swish'), use='利刃划过：切开、斩断、一刀两断'),
    'ambience_calm': dict(mixkit=('room-tone', 'Cinematic room tone loop'), span=True, db=-14, use='平静氛围底：留白、定格、安静的段落'),
    # 第 6 批：综艺梗音效（sfx_comic_sting）和写字声，earshot 里没有，从 Mixkit 下
    'pen_scribble': dict(mixkit=('writing', 'Writing scribble on paper'), use='手写批注、在截图上写字'),
    'punch':      dict(mixkit=('cartoon', 'Soft quick punch'), comic=True, use='打脸、被怼、反转那一下'),
    'boing':      dict(mixkit=('cartoon', 'Boing hit sound'), comic=True, use='弹回去、被驳回、想法撞墙'),
    'dizzy':      dict(mixkit=('cartoon', 'Cartoon dazzle hit and birds'), comic=True, use='被绕晕、懵了、信息太多'),
    'honk':       dict(mixkit=('horn', 'Clown horn at circus'), comic=True, use='搞笑提醒、犯傻、离谱'),
    'rimshot':    dict(mixkit=('funny', 'Drum joke accent'), comic=True, use='梗句收尾、自嘲'),
    'sad_trombone': dict(mixkit=('sad', 'Slow sad trombone fail'), comic=True, use='翻车、失败、白忙一场'),
    'fail_piano': dict(mixkit=('cartoon', 'Cartoon failure piano'), comic=True, use='心碎、失落、坏消息'),
    'fart':       dict(mixkit=('cartoon', 'Cartoon fart sound'), comic=True, use='尴尬、泄气、拉胯（综艺感才用）'),
    'laugh':      dict(mixkit=('funny', 'Crowd laugh'), comic=True, use='观众笑声：自嘲、包袱抖响'),
}
for _k in ('dun_dun_duun',):
    SOUNDS[_k]['comic'] = True
# 梗音效轮换（sfx_comic_sting）：负面、翻车配失落类，情绪、吐槽配滑稽类；戏剧三连全片一次
STINGS = {'negative': ['sad_trombone', 'fail_piano', 'error', 'fart'], 'emotion': ['punch', 'boing', 'dizzy', 'honk', 'rimshot']}
STING_GAP = 12          # 两个梗音效至少隔 12 秒，多了就不好笑了
BASS_PRE = ('statcard', 'ring', 'count', 'number', 'bignum', 'word') + ('chapter', 'fog', 'chapter_page')   # 包装前垫低音的重包装
for _k in ('hit', 'drop'):
    SOUNDS[_k]['heavy'] = True     # 重音类每种全片最多两次（sfx_impact），多了观众会疲劳
SOUNDS['swell']['align'] = SOUNDS['riser']['align'] = 'peak'   # 蓄力类声音最响处对准事件，其余起音对准事件开始那一帧
HEAVY_MAX = 2
UI_SOUNDS = ('click', 'tap', 'ding', 'pop', 'tick', 'snap', 'rising_ui')   # 提示音类：一句话里最多 3 个

# 组合声音：几个清单里的声音按先后叠成一个（sfx_impact 的挥动落定、sfx_whoosh 的穿梭）。(声音, 相对秒)
COMBOS = {
    'swing':   dict(parts=[('whoosh', 0.0), ('thump', 0.22)], use='挥动落定：人物冲出来、元素甩进来，嗖一声再落定'),
    'shuttle': dict(parts=[('whoosh', 0.0), ('shimmer', 0.04)], use='穿梭：高音闪光扫过，配隧道冲出、光效转场'),
    'rising_ui': dict(parts=[('tick', 0.0)], use='升调 UI 串：重点词一个个蹦出，每个高一个音（写 step 0、1、2…）'),
}
RISING_STEPS = [0, 2, 4, 5, 7, 9, 11, 12]   # 升调串每一步升几个半音（大调音阶，听着是往上走）


def sound_alias(name):
    """声音名：清单里的受控名或组合名原样返回；剪映音效原名（如「综艺叮」「唰」）按手法库的对照表换成受控名。
    对照表里写「a + b」的是组合，返回列表。认不出返回 None。"""
    if name in SOUNDS or name in COMBOS:
        return name
    m = _jianying_map().get(name)
    if not m:
        return None
    m = re.sub(r'（.*?）', '', m).replace('new:', '').strip()
    if '升调' in _jianying_map().get(name, ''):
        return 'rising_ui'
    parts = [x.strip() for x in m.split('+')]
    parts = [x for x in parts if x in SOUNDS]
    return parts[0] if len(parts) == 1 else (parts or None)


_JY = {}


def _jianying_map():
    if not _JY:
        cat = json.loads((Path(__file__).resolve().parent.parent / 'assets/library/catalog.json').read_text(encoding='utf-8'))
        t = next((x for x in cat['techniques'] if x['id'] == 'sfx_event_engine'), {})
        _JY.update(t.get('params', {}).get('jianying_to_controlled', {}))
    return _JY


_MIXKIT_URLS = {}


def mixkit_item(cat, name):
    """Mixkit 音效的下载地址（按类别页查一次，缓存）。"""
    key = (cat, name)
    if key not in _MIXKIT_URLS:
        from music_search import mixkit_sfx
        hit = next((x for x in mixkit_sfx(cat) if x['title'] == name), None)
        _MIXKIT_URLS[key] = hit['url'] if hit else None
    return {'name': name, 'url': _MIXKIT_URLS[key]} if _MIXKIT_URLS[key] else None


def word_time(word, base, after=0.0):
    """口播里说出某个词的时刻（成片时间）：按 lines.json 的逐字时间找 after 秒之后第一次出现。找不到返回 None。"""
    f = Path(base) / 'lines.json'
    if not f.exists():
        return None
    chars = [c for ln in json.loads(f.read_text(encoding='utf-8')) for c in ln.get('chars', [])]
    text = ''.join(c[0] for c in chars)
    i = 0
    while True:
        i = text.find(word, i)
        if i < 0:
            return None
        if chars[i][1] >= after - 1e-3:
            return chars[i][1]
        i += 1


PHRASE_TIERS = [1.0, 1.18, 1.32, 1.1]   # 一词一镜的景别轮换
TECH_WORDS = ['会话', '上下文', '终端', '命令', '模型', '任务', '后台', '子代理', '插件', '提示词', '口播', '剪辑', '字幕', '素材', '镜头']


def _phrases(chars, lo=2, hi=6):
    """一句字幕按逐字时间拆成 2~6 字的短语：先用 jieba 分词，词不拆开；标点处必断；
    其余在「短语长度接近 4」和「断在停顿长的地方」之间找最好的切法。chars: [(字, 秒)]。返回 [(文字, 起点秒)]。"""
    import logging
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        import jieba
    jieba.setLogLevel(logging.ERROR)
    for wd in TECH_WORDS:   # jieba 词典里没有或排得低的常用词，免得「会话」被拆成「的会 / 话」
        jieba.add_word(wd, 20000)
    text = ''.join(c for c, _ in chars)
    toks, i = [], 0
    for wd in jieba.lcut(text):
        t = chars[i][1] if i < len(chars) else chars[-1][1]
        if toks and wd.strip() and wd.isascii() and re.search(r'[A-Za-z0-9]$', toks[-1][0].rstrip()) and \
                (toks[-1][0].endswith(' ') or not wd[0].isalnum()):
            toks[-1] = (toks[-1][0] + wd, toks[-1][1])   # 英文词组（Claude Code）不拆
        elif toks and wd == ' ' and re.search(r'[A-Za-z0-9]$', toks[-1][0]):
            toks[-1] = (toks[-1][0] + ' ', toks[-1][1])
        else:
            toks.append((wd, t))
        i += len(wd)
    groups, cur = [], []
    for wd, t in toks:   # 标点、空格先切开
        if re.fullmatch(r'[\s，。！？、；：,.!?;:…“”"]+', wd):
            if cur:
                groups.append(cur)
            cur = []
        else:
            cur.append((wd, t))
    if cur:
        groups.append(cur)
    size = lambda ws: sum(1 if not w.isascii() else 0.5 for w, _ in ws for _c in w if _c.strip())
    gaps = sorted(b[1] - a[1] for g in groups for a, b in zip(g, g[1:]))
    med = gaps[len(gaps) // 2] if gaps else 0.0
    out = []
    for g in groups:
        n = len(g)
        best = {0: (0.0, [])}
        for j in range(1, n + 1):   # 动态规划：best[j] = 前 j 个词的最优切法
            for i0 in range(j):
                if i0 not in best:
                    continue
                L = size(g[i0:j])
                if L > hi and j - i0 > 1:
                    continue
                gap = (g[j][1] - g[j - 1][1]) if j < n else 1.0
                cost = best[i0][0] + (L - 4) ** 2 * 0.2 + 1.6 + (3 if L < lo else 0) - min(max(0.0, gap - med), 0.6) * 4 + \
                    (1.5 if g[i0][0][:1] in '了的地得着过吗呢吧啊么' else 0)   # 别让短语以虚词开头
                if j not in best or cost < best[j][0]:
                    best[j] = (cost, best[i0][1] + [(i0, j)])
        for i0, j in best[n][1]:
            out.append((''.join(w for w, _ in g[i0:j]).strip(), g[i0][1]))
    return out


def phrase_subs(tl, base='.'):
    """快剪一词一镜字幕（sub_phrase_per_cut）：timeline 顶层 "phrase_subs": [{t0, t1, cut}] 这几段里，
    跟读字幕按逐字时间拆成一个镜头一个 2~6 字短语；短语的起止吸附到附近 0.2 秒内的切点（素材、版式、粗剪刀口）。
    cut 为 true 时每个短语换一档景别（100% / 118% / 132% / 110% 轮换硬切），只有一个机位也像在快剪。"""
    rs = tl.get('phrase_subs') or []
    f = Path(base) / 'lines.json'
    if not rs or not f.exists():
        return
    lines = json.loads(f.read_text(encoding='utf-8'))
    chars = [(c[0], c[1]) for ln in lines for c in ln.get('chars', [])]
    cuts = sorted({x for ln in lines for x in ln.get('cuts', [])} | {x for b in tl.get('broll', []) for x in (b['t0'], b['t1'])} |
                  {x for l in tl.get('layout', []) for x in (l['t0'], l['t1'])})
    snap = lambda x: min(cuts, key=lambda c: abs(c - x)) if cuts and min(abs(c - x) for c in cuts) < 0.2 else x
    hand = [(z['t0'], z['t1']) for z in tl.get('zoom', [])]
    subs, k = [], 0
    for s in tl.get('subs', []):
        r = next((r for r in rs if r['t0'] <= (s['t0'] + s['t1']) / 2 < r['t1']), None)
        cs = [c for c in chars if s['t0'] - 0.03 <= c[1] < s['t1'] - 0.02] if r else []
        ps = _phrases(cs, r.get('min', 2), r.get('max', 6)) if cs else []
        if len(ps) < 2:
            subs.append(s)
            continue
        ts = [s['t0']] + [snap(t) for _, t in ps[1:]] + [s['t1']]
        j = 0
        while j < len(ps) and len(ps) > 1:   # 一个短语至少停 0.4 秒，太快的并进后一个（最后一个并进前一个）
            if ts[j + 1] - ts[j] < 0.4:
                k_ = j if j + 1 < len(ps) else j - 1
                ps[k_:k_ + 2] = [(ps[k_][0] + (' ' if ps[k_][0][-1:].isascii() and ps[k_ + 1][0][:1].isascii() else '') + ps[k_ + 1][0], ps[k_][1])]
                del ts[k_ + 1]
                j = 0
                continue
            j += 1
        for j, (txt, _) in enumerate(ps):
            p = {**s, 't0': round(ts[j], 3), 't1': round(ts[j + 1], 3), 'text': txt, 'hl': [h for h in s.get('hl') or [] if h in txt]}
            subs.append(p)
            if r.get('cut') and not any(a < p['t1'] and p['t0'] < b for a, b in hand):
                z = PHRASE_TIERS[k % len(PHRASE_TIERS)]
                tl.setdefault('zoom', []).append({'t0': p['t0'], 't1': p['t1'], 'from': z, 'to': z, 'ease': 0.01, '_phrase': True})
            k += 1
    tl['subs'] = subs


def _sound_cues(v, start, length, prio, g):
    """把 sound 字段（字符串，或 {type, at, dur, step, db}）展开成音效时刻 [{t, sound, dur, prio, g, event, ...}]。
    at 是相对这个元素出现的秒数；type 可写声音清单里的名字、组合名，或剪映音效原名（按手法库对照表换算）。
    t 是这个声音起音该落的时刻（组合的后几个声音按自己的偏移往后排），event 是画面事件开始那一帧；g 相同的几个声音一起留、一起砍。"""
    if isinstance(v, str):
        v = {'type': v}
    raw = v.get('type') or v.get('sound')
    name = sound_alias(raw)
    if not name:
        raise SystemExit(f'sound「{raw}」不在声音清单里，可选：{"、".join(list(SOUNDS) + list(COMBOS))}，或手法库对照表里的剪映音效名')
    at = start + v.get('at', 0)
    out = []
    if isinstance(name, list) or name in SOUNDS:
        for nm in ([name] if isinstance(name, str) else name):   # 对照表里的「a + b」：同一刻叠放
            out.append({'t': at, 'sound': nm, 'dur': v.get('dur', max(0.3, length - v.get('at', 0))) if SOUNDS[nm].get('span') else None})
    elif name == 'rising_ui':   # 写了 step 是一串里的第几个；没写就单独来一串 4 个往上走
        steps = [v['step']] if 'step' in v else range(4)
        for j, s in enumerate(steps):
            out.append({'t': at + (0 if 'step' in v else j * 0.09), 'sound': 'tick', 'dur': None,
                        'rate': round(2 ** (RISING_STEPS[s % len(RISING_STEPS)] / 12), 4)})
    else:
        out = [{'t': at + dt, 'sound': nm, 'dur': None} for nm, dt in COMBOS[name]['parts']]
    for c in out:
        c.update(kind='semantic', prio=prio, g=g, event=round(at, 3), **({'db': v['db']} if 'db' in v else {}))
    return out


# 效果转场自带的声音（sfx_whoosh）：起音对准转场开始那一帧。硬切不配，每个硬切都响会吵
TRANSITION_SFX = {'flash': 'whoosh', 'blur_swipe': 'whoosh', 'light_leak': 'shuttle', 'dip_black': 'whoosh_big', 'glitch': 'glitch',
                  'whip': 'whoosh', 'iris': 'whoosh', 'tear': 'crumple', 'occlude': 'whoosh_big',
                  'blocks': 'glitch', 'tunnel': 'shuttle'}


def sfx_cues(tl, base='.', st=None):
    """需要配音效的时刻：[{t, kind, prio, g, event, sound?, dur?}]，prio 越小越重要，超出密度上限时先砍大的。
    0 对着内容的声音：素材、大字、版式写了 sound，或 timeline 的 sounds 里按关键词、时间点写的；
    1 章节页、效果转场、冲焦和定格，以及整屏冲击的大包装自带的声音（sound_hit：单字页、数字滚动、砸屏、字墙等，画面砸下来必须有声）；2 素材出场（相隔不到 0.6 秒的一串素材算一次，整串一起配）、手法自带的声音；3 大字出现。
    章节页、素材、大字没写 sound 的自动配，按风格在几种角色之间轮换；素材从侧面滑入、移入的配嗖。
    大字或素材写 "sfx": false 不配；常驻超过 6 秒的大字角标不自动配。"""
    st = st or style_preset(tl)
    au = tl.get('audio', {})
    cues, n = [], [0]

    def gid():
        n[0] += 1
        return n[0]

    for name, items in (('titles', tl.get('titles', [])), ('broll', tl.get('broll', [])), ('overlays', tl.get('overlays', [])),
                        ('layout', tl.get('layout', []))):
        last_t, run = -9.0, None
        for it in items:
            if name == 'layout' and not it.get('sound'):
                continue
            if it.get('sound'):
                src = gid()   # 同一个元素自带的一串声音（标签逐个弹出、节点逐个点亮）是成串设计的，筛选时不算重复
                for v in (it['sound'] if isinstance(it['sound'], list) else [it['sound']]):
                    for c in _sound_cues(v, it['t0'], it['t1'] - it['t0'], 1 if it.get('sound_hit') else 2 if it.get('sound_auto') else 0, src):
                        cues.append({**c, 'src': src})   # 一个元素的整串声音算一组，一起留一起砍，占一个名额
                continue
            if it.get('sfx') is False or not au.get('auto_sfx', True) or name == 'overlays':
                continue
            if it.get('punch'):   # 冲焦那一下配快门声
                cues += _sound_cues('snap', it['t0'] + it['punch'].get('t', 0.4), 0, 1, gid())
            if name == 'titles':
                if it.get('sfx') is None and it['t1'] - it['t0'] > 6:
                    continue
                kind = it['sfx'] if isinstance(it.get('sfx'), str) else ('chapter' if it.get('layout') in CHAPTER_LAYOUTS else 'title')
                cues.append({'t': it['t0'], 'kind': kind, 'prio': 1 if kind == 'chapter' else 3, 'g': gid(), 'event': it['t0']})
            elif str(it.get('enter', '')).startswith(('slide', 'move')) and it['t0'] - last_t > 0.6:   # 滑入、移入的卡片配嗖
                cues += _sound_cues('whoosh', it['t0'], 0, 2, gid())
                last_t = it['t0']
            else:
                if it['t0'] - last_t > 0.6 or run is None:
                    run = gid()
                cues.append({'t': it['t0'], 'kind': 'broll', 'prio': 2, 'g': run, 'event': it['t0']})
                last_t = it['t0']
    tone = st.get('tone', 'web')
    # 包装前垫低音（bass_pre_entry）：数据卡、数字、整屏单字、章节页出现前 0.4 秒先响一个贝斯单音；综艺感不用，audio.bass_pre 写 false 关
    if au.get('bass_pre', tone != 'variety' and tl.get('style') != 'variety'):
        for it in tl.get('titles', []):
            if it.get('layout') in BASS_PRE and it.get('sfx') is not False and it['t0'] >= 0.5:
                cues += _sound_cues('bass_hit', it['t0'] - 0.4, 0, 2, gid())
    # 综艺梗音效（sfx_comic_sting）：beats 里情绪、负面句，网感档和综艺感在句末配一声，轮换、隔 12 秒；beat 写 "sting" 指定或写 false 关
    if tone != 'calm' and au.get('stings', True):
        last, k = -99.0, {}
        for b in sorted(tl.get('beats') or [], key=lambda b: b['t0']):
            want = b.get('sting')
            if want is False or (want is None and b.get('beat') != 'emotion') or b['t0'] - last < STING_GAP:   # 负面句要写 sting 才配，提醒类负面句配梗会错位
                continue
            if want in (None, True):
                pool = [x for x in STINGS.get(b['beat'], STINGS['emotion']) if x != 'fart' or tl.get('style') == 'variety']
                want = pool[k.get(b['beat'], 0) % len(pool)]
                k[b['beat']] = k.get(b['beat'], 0) + 1
            cues += _sound_cues(want, max(b['t0'], b['t1'] - 0.15), 0, 1, gid())
            last = b['t0']
    # 氛围铺垫音（sfx_ambience）：提问、悬念句底下铺一段悬念小鼓；beat 写 "ambience": suspense / calm / false
    for b in tl.get('beats') or []:
        amb = b.get('ambience', 'suspense' if b.get('beat') == 'question' and tone != 'calm' else None)
        if not amb:
            continue
        d = min(4.0, b['t1'] - b['t0'])
        if amb == 'suspense':
            cues += _sound_cues({'type': 'suspense_tap', 'dur': d, 'db': -4}, b['t0'], d, 2, gid())
        elif amb == 'calm':
            g = gid()
            cues += _sound_cues('shimmer', b['t0'], 0, 2, g) + _sound_cues({'type': 'ambience_calm', 'dur': d}, b['t0'], d, 2, g)
    for fz in tl.get('freezes', []):   # 定格那一下配快门声
        cues += _sound_cues('snap', fz['t0'], 0, 1, gid())
    for tr in auto_transitions(tl, st):
        snd = tr.get('sound', TRANSITION_SFX.get(tr['type']))
        if snd and tr.get('sfx') is not False:
            cues += _sound_cues(snd, tr_window(tr)[0], 0, 1, gid())
    for f in tl.get('fx', []):   # 整屏特效自带的声音（第 8 批）
        if f.get('sfx') is False:
            continue
        for v in fx_sounds(f):
            cues += _sound_cues(v, f['t0'], f['t1'] - f['t0'], 1, gid())
    for v in tl.get('sounds', []):   # 按关键词或时间点挂的声音
        t = v['t'] if 't' in v else word_time(v['word'], base, v.get('after', 0))
        if t is None:
            print(f"sounds：口播里没找到「{v.get('word')}」，跳过")
            continue
        cues += _sound_cues(v, t, v.get('dur', 1.0), v.get('prio', 0), gid())
    return sorted(cues, key=lambda c: (c['t'], c['prio']))


SFX_DENSITY = {'sparse': 12, 'dense': 30}


def packaging_per_min(tl, duration):
    """每分钟有几次包装出现（大字、素材、版式，0.3 秒内连着的算一次），给音效密度上限用。"""
    ts = sorted(it['t0'] for k in ('titles', 'broll', 'layout') for it in tl.get(k, []) if 't0' in it)
    n, last = 0, -9.0
    for t in ts:
        if t - last > 0.3:
            n += 1
        last = t
    return int(n * 60 / max(duration, 1) + 0.5)   # 每分钟上限：高级感稀疏约 6 个（最多 12），综艺感密集约 20 个（10~31）


def _sentences(base):
    f = Path(base) / 'lines.json'
    return [(ln['t0'], ln['t1']) for ln in json.loads(f.read_text(encoding='utf-8'))] if f.exists() else []


def thin_cues(cues, per_min, duration, base='.'):
    """按密度上限挑，同一组（一串素材、组合声音）一起留一起砍。
    - 对着内容的声音、章节页、转场一定留（同一种声音 3 秒内只留一次）；素材出场、大字按重要程度往里加，直到全片每分钟 per_min 组；
    - 同一时刻（0.3 秒内）最多叠两组：两组都是 0、1 级、声音不同才叠（入场加强调），其余只留一组；
    - 重音类（hit、drop 等）每种全片最多 HEAVY_MAX 次；
    - 提示音类（点击、叮、啵）一句话里最多 3 个，多出来的自动配的去掉、手写的压低 6 dB；升调串是成串设计的，不算。"""
    cap = max(1, int(per_min * duration / 60 + 0.5))
    groups = {}
    for c in cues:
        groups.setdefault(c['g'], []).append(c)
    reps = sorted(groups.values(), key=lambda g: (min(c['prio'] for c in g), g[0]['t']))
    keep, heavy, sents = [], {}, _sentences(base)
    ui = {}
    for g in reps:
        c, prio = g[0], min(x['prio'] for x in g)
        if prio > 1 and len(keep) >= cap:
            continue
        snd = {x.get('sound') for x in g} - {None}
        if snd and not any('rate' in x for x in g) and any(k[0].get('sound') in snd and abs(k[0]['t'] - c['t']) < 3
                                                          and not (c.get('src') and k[0].get('src') == c['src']) for k in keep):
            continue   # 升调串、同一个元素自带的一串声音是成串设计的，不算重复
        near = [k for k in keep if abs(k[0]['t'] - c['t']) < 0.3]
        if near and not (len(near) == 1 and prio <= 1 and min(x['prio'] for x in near[0]) <= 1
                         and (near[0][0].get('sound') or near[0][0]['kind']) != (c.get('sound') or c['kind'])):
            continue
        hv = [s for s in snd if SOUNDS.get(s, {}).get('heavy')]
        if any(heavy.get(s, 0) >= HEAVY_MAX for s in hv):
            if prio > 1:
                continue
            for x in g:   # 必留的冲击（手写、章节、大包装）重音用满了就换成轻一档的落地声，不让画面砸下来没声音
                if SOUNDS.get(x.get('sound'), {}).get('heavy'):
                    x['sound'] = 'thump'
            hv = []
        if snd & set(UI_SOUNDS) and not any('rate' in x for x in g):
            si = next((i for i, (a, b) in enumerate(sents) if a - 0.2 <= c['t'] <= b + 0.2), None)
            if si is not None:
                ui[si] = ui.get(si, 0) + 1
                if ui[si] > 3:
                    if prio > 0:
                        continue
                    for x in g:
                        x['db'] = x.get('db', 0) - 6
        for s in hv:
            heavy[s] = heavy.get(s, 0) + 1
        keep.append(g)
    return sorted([c for g in keep for c in g], key=lambda c: c['t'])


EARSHOT_PY = Path(os.environ.get('KOUBO_EARSHOT_PY') or Path(os.environ.get('KOUBO_HOME', Path.home() / '.cache/koubo')).expanduser()
                  / 'earshot-venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python'))


def all_sfx(tl, st, base='.'):
    """timeline 里手写的音效 + 自动配的音效（见 sfx_cues）。密度按 audio.sfx_density（sparse / dense）或风格的 sfx_per_min。
    装了 earshot（`python scripts/setup_earshot.py install`）就用它的代码音效库；声音清单里的生活音效、新加的音效从 Mixkit 下载。
    摆放规则（sfx_event_engine）：起音对准画面事件开始那一帧（蓄力类的反向镲、上升音是最响处对准）。
    每条输出 {src, t, db 或 gain, at, event, anchor, sound, rate?, dur?}：at 是起音（或最响处，看 anchor）该落的时刻，
    event 是它对的画面事件开始那一帧，audio_check.py 拿它们核对齐。
    audio.sfx_engine 写 "mixkit" 强制只用 Mixkit。"""
    au = tl.get('audio', {})
    manual = list(au.get('sfx', []))
    dur = tl.get('duration', 60) + tl.get('tail', 0)
    per_min = SFX_DENSITY.get(au.get('sfx_density')) or st.get('sfx_per_min', 12)
    if not au.get('sfx_density') and st.get('tone') != 'calm':   # 包装越密音效上限越高：画面每换一次包装就该有一声，克制档不跟
        per_min = max(per_min, int(packaging_per_min(tl, dur) * 1.5))   # 一个包装常配两三声（嗖接砸），按 1.5 倍给
    cues = [c for c in thin_cues(sfx_cues(tl, base, st), per_min, dur, base)
            if not any(abs(m['t'] - c['t']) < 0.25 for m in manual)]
    if not cues:
        return manual
    use_es = au.get('sfx_engine', 'earshot') == 'earshot' and EARSHOT_PY.exists()
    out, es_cues = list(manual), []

    def put(item, c, spec):
        f, m = kit_file(item, base, full=bool(spec.get('span')))
        anchor = spec.get('align', 'onset')
        rate = c.get('rate') or 1.0
        out.append({'src': str(f), 't': round(max(0.0, c['t'] - m[anchor] / rate), 3),
                    'db': item.get('db', 0) + (spec.get('db', -3) if c.get('sound') else 0) + c.get('db', 0) - (3 if c.get('sound') in UI_SOUNDS else 0),
                    'at': c['t'], 'event': c.get('event', c['t']), 'anchor': anchor, 'sound': c.get('sound') or c['kind'],
                    **({'rate': c['rate']} if c.get('rate') else {}), **({'dur': c['dur']} if c.get('dur') else {})})

    for c in cues:
        spec = SOUNDS.get(c.get('sound'), {})
        mk = spec.get('mixkit') or (None if use_es else (spec.get('fallback') if c.get('sound') else None))
        if c.get('sound') and mk:
            item = mixkit_item(*mk)
            if item:
                put(item, c, spec)
            continue
        es_cues.append(c)
    if es_cues and use_es:
        r = subprocess.run([str(EARSHOT_PY), str(Path(__file__).with_name('earshot_sfx.py')), '--base', str(base)],
                           input=json.dumps({'timeline': {**tl, 'audio': {**au, 'bgm': tl.get('_bgm', expand_bgm(tl, base))}}, 'cues': es_cues,
                                             'sounds': SOUNDS, 'style': tl.get('style', 'premium'), 'tone': st.get('tone'),
                                             'bgm_gain': [bgm_gain_db(m, st) for m in tl.get('_bgm', expand_bgm(tl, base))]}),
                           capture_output=True, text=True)
        if r.returncode == 0:
            return sorted(out + json.loads(r.stdout), key=lambda x: x['t'])
        print('earshot 配音效失败，改用 Mixkit：', r.stderr.strip()[-300:])
    kit = SFX_KITS.get(st.get('sfx_kit')) if isinstance(st.get('sfx_kit'), str) else st.get('sfx_kit')
    turn, last = {}, None
    for c in es_cues:   # Mixkit 兜底
        if c.get('sound'):
            item = mixkit_item(*SOUNDS[c['sound']]['fallback'])
        else:
            items = (kit or {}).get(c['kind']) or []
            if not items:
                continue
            n = turn.get(c['kind'], 0)
            item = items[n % len(items)]
            if item['name'] == last and len(items) > 1:
                n += 1
                item = items[n % len(items)]
            turn[c['kind']], last = n + 1, item['name']
        if item:
            put(item, c, SOUNDS.get(c.get('sound'), {}))
    return sorted(out, key=lambda x: x['t'])


# ---------------------------------------------------------------- 纸页底
PAPER_INK = {'color': '#2A2622', 'lead_color': '#5C544A'}   # 米白纸上的大字用深色墨


def paper_ink(tl):
    """大字落在米白纸页（layout 的 paper: cream）上时换深色字、去掉投影；手写了 color 的不动。"""
    cream = [(l['t0'], l['t1']) for l in tl.get('layout', []) if l.get('mode') == 'paper' and l.get('paper') == 'cream']
    for t in tl.get('titles', []):
        mid = (t['t0'] + t['t1']) / 2
        if 'color' not in t and any(a <= mid <= b for a, b in cream):
            t.update(PAPER_INK, on_light=True)


def paper_texture(out, W, H, kind='kraft', seed=3):
    """代码生成的纸页底：kraft 牛皮纸、cream 米白纸。纤维噪点 + 几块淡淡的污渍 + 四周压暗，不涉及素材版权。"""
    import numpy as np
    from PIL import Image, ImageFilter
    rng = np.random.default_rng(seed)
    base = {'kraft': (190, 152, 108), 'cream': (236, 229, 214)}.get(kind, (190, 152, 108))
    img = np.ones((H, W, 3), np.float32) * np.array(base, np.float32)
    grain = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    grain = np.array(Image.fromarray(((grain * 18) + 128).clip(0, 255).astype(np.uint8)).resize((W, H)).filter(ImageFilter.GaussianBlur(0.8)),
                     np.float32) - 128
    fib = rng.normal(0, 1, (H // 8, W)).astype(np.float32)
    fib = np.array(Image.fromarray(((fib * 30) + 128).clip(0, 255).astype(np.uint8)).resize((W, H)), np.float32) - 128   # 横向拉长的纤维
    stain = np.zeros((H // 16, W // 16), np.float32)
    for _ in range(6):
        cy, cx, r = rng.integers(0, H // 16), rng.integers(0, W // 16), rng.integers(4, 14)
        yy, xx = np.ogrid[:H // 16, :W // 16]
        stain += np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * r * r)) * rng.uniform(4, 12)
    stain = np.array(Image.fromarray(stain).resize((W, H), Image.BICUBIC), np.float32)
    yy, xx = np.ogrid[:H, :W]
    vig = 1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    img = (img + grain[..., None] * 0.35 + fib[..., None] * 0.12 - stain[..., None]) * vig[..., None]
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(out)
    return out


# ---------------------------------------------------------------- 节奏：口播景别跳档
def _minus(windows, cuts):
    """区间 windows 减去 cuts（都是 [(t0, t1)]）。"""
    out = []
    for a, b in windows:
        segs = [(a, b)]
        for c0, c1 in cuts:
            segs = [s for x0, x1 in segs for s in ((x0, min(x1, c0)), (max(x0, c1), x1)) if s[1] - s[0] > 1e-3]
        out += segs
    return out


MATTE_MODES = ('matte', 'corner', 'breakout')
COVER_TITLES = ('cardpair', 'meme', 'persist', 'circletext', 'splitswap', 'topcard', 'vflank',
                'montage', 'textfirst', 'qframe', 'poster', 'coverframe', 'askpage', 'gesture', 'cutnum', 'slogan',
                'flow', 'stepwall', 'typerow', 'photostack', 'quotetype', 'labelcol', 'products', 'translate',
                'splitwin', 'window', 'bands', 'matteband', 'papercollage', 'figure', 'moodword', 'parallax',
                'overlapframe', 'credits', 'darkenword', 'searchhook',
                'shapecut', 'radial', 'extend', 'screenblend', 'diagram', 'trail', 'orbitcover', 'framesticker', 'painpoint', 'spinring')   # 自己压暗或铺黑底、盖住口播的逐帧大字（口播全屏判定时扣掉；别再垫 aside 这类挪口播的版式，会连大字一起挪走）   # 抠像版式（matte.py）：换底、人缩角、人物出框
COVER_MODES = ('aside', 'hidden', 'pip', 'paper', 'frame', 'bg', 'inset', 'circle', 'split',
               'mockup', 'combo', 'overview', 'endcard', 'morph') + MATTE_MODES   # 口播不再是全屏的版式
CHAPTER_LAYOUTS = ('chapter', 'fog', 'chapter_page', 'topcard', 'vflank', 'gesture', 'cutnum')   # 章节载体：经典章节页、白雾镂空序号、章节标题页、顶部整句卡、竖排双列页、圆头像手势卡、剪纸大数字页
GRAPHIC_LAYOUTS = ('statcard', 'ring', 'fog', 'chapter_page',   # 逐帧合成的大字版式（cards.py、keytext.py 画，不走 ASS）
                   'slam', 'burst', 'knockout', 'crack', 'swap', 'finish', 'patch', 'note', 'qmark', 'scribble', 'icons', 'recframe',
                   'qmarks', 'bubble', 'meme', 'shout', 'crossin', 'wipe', 'perchar', 'cursor', 'arrow', 'focus', 'cardpair', 'divider',
                   'boom', 'persist', 'glitchswap',
                   'giant', 'ghostword', 'boxed', 'corners', 'circletext', 'splitswap', 'topcard', 'vflank', 'typepanel',
                   'montage', 'collage', 'textfirst', 'qframe', 'poster', 'coverframe', 'askpage', 'gesture', 'cutnum', 'inkecho', 'actionrow', 'slogan',
                   'callout', 'widget', 'flow', 'axis', 'stepwall', 'reslist', 'typerow', 'photostack', 'comments', 'fanwin', 'ticker',
                   'quotetype', 'labelcol', 'person', 'products', 'translate',
                   'splitwin', 'window', 'bands', 'matteband', 'papercollage', 'figure', 'moodword', 'parallax',
                   'grid2x2', 'persp3d', 'stairs', 'overlapframe', 'orbit', 'wordwall', 'pinyin', 'credits', 'readygo', 'darkenword', 'tape', 'searchhook',
                   'shapecut', 'radial', 'whitefade', 'particles', 'extend', 'idwall', 'panels', 'screenblend', 'swatch', 'diagram',
                   'trail', 'spinring', 'gesturetext', 'paperpanels', 'orbitcover', 'armwipe', 'mics', 'framesticker', 'painpoint', 'jytpl')
# 逐帧画面里直接读口播画面或抠像的大字（第 9 批）：这段时间不自动推近，否则底下推近了、画出来的人没推近，会错位
AROLL_TITLES = ('giant', 'ghostword', 'boxed', 'corners', 'circletext', 'splitswap', 'topcard', 'vflank', 'typepanel',
                'collage', 'textfirst', 'qframe', 'poster', 'coverframe', 'askpage', 'gesture', 'cutnum', 'inkecho', 'actionrow', 'slogan',
                'widget', 'flow', 'axis', 'photostack', 'comments', 'fanwin', 'quotetype', 'products',
                'splitwin', 'bands', 'matteband', 'papercollage', 'figure', 'parallax',
                'overlapframe', 'orbit', 'wordwall', 'credits', 'darkenword',
                'radial', 'whitefade', 'extend', 'idwall', 'panels', 'screenblend', 'swatch', 'trail', 'framesticker', 'painpoint')
FULL_FITS = ('cover', 'double', 'band')   # 铺满整个画面的 B-roll


def fullscreen_windows(tl):
    """口播全屏的时间段：去掉人物移出、黑底、小窗版式，去掉铺满的 B-roll。"""
    dur = tl.get('duration', 0)
    cuts = [(l['t0'], l['t1']) for l in tl.get('layout', []) if l['mode'] in COVER_MODES]
    cuts += [(b['t0'], b['t1']) for b in tl.get('broll', []) if b.get('fit', 'cover') in FULL_FITS]
    cuts += [(t['t0'], t['t1']) for t in tl.get('titles', []) if t.get('layout') in COVER_TITLES or t.get('cover')]   # 盖住口播的逐帧大字
    return _minus([(0.0, dur)], sorted(cuts))


def auto_zoom(tl, st, base='.'):
    """口播景别：每次回到口播全屏换一档（100% / 115% / 125% 三档轮换，相邻不同档），单段超过 4 秒就在句子停顿处再跳一档。
    timeline 的 auto_zoom 选做法（手法 talk_zoom_punch）：
      jump  跳切三档（财经知识口播原片，克制档默认）
      snap  再加句首快推：粗剪接缝或重点句开口那一刀 0.15 秒推进 7%，遮跳剪也给重音加力，每 3 刀最多一次
      mixed 跳档 + 句首快推 + 一句两推（重点句超过 2.5 秒：先推 5%，说到第二个强调词再推 5%），网感档和综艺感默认
      false 关掉
    手写了 zoom 的地方、字在人后、白雾数字窗这些要和抠像对齐的地方不动。"""
    tiers = st.get('zoom_tiers')
    mode = tl.get('auto_zoom', st.get('zoom_mode', 'jump'))
    if not tiers or mode is False:
        return []
    mode = 'jump' if mode is True else mode
    keys = [x for x in tl.get('subs', []) if x.get('level') == 'key']
    busy = [(z['t0'], z['t1']) for z in tl.get('zoom', [])] + [(m['t0'], m['t1']) for m in tl.get('mattes', [])] + \
        [(t['t0'], t['t1']) for t in tl.get('titles', []) if t.get('behind') or t.get('layout') in AROLL_TITLES or
         (t.get('layout') == 'fog' and t.get('variant') == 'window')]
    wins = [w for w in _minus(fullscreen_windows(tl), sorted(busy)) if w[1] - w[0] >= 0.8]
    cuts = set()
    f = Path(base) / 'lines.json'
    if f.exists():   # 粗剪的接缝本来就是一刀，跳档放在这里看起来像换了机位
        for ln in json.loads(f.read_text(encoding='utf-8')):
            cuts.add(round(ln.get('clip_start', 0), 3))
            cuts.update(round(c, 3) for c in ln.get('cuts', []))
    phrase = sorted({round(s['t0'], 3) for s in tl.get('subs', [])})
    out, k, prev, since = [], 0, None, 2
    for a, b in wins:
        pts = [a] + sorted(c for c in cuts if a + 1.2 < c < b - 1.2) + [b]
        segs = []
        for x0, x1 in zip(pts, pts[1:]):
            while x1 - x0 > 4.0:            # 太长的段在中间附近的句子停顿处再切一刀
                mid = min((p for p in phrase if x0 + 1.5 < p < x1 - 1.5), key=lambda p: abs(p - (x0 + x1) / 2), default=None)
                if mid is None:
                    break
                segs.append((x0, mid))
                x0 = mid
            segs.append((x0, x1))
        for x0, x1 in segs:
            z = tiers[k % len(tiers)]
            if z == prev:
                k += 1
                z = tiers[k % len(tiers)]
            k += 1
            prev = z
            since += 1
            key = next((x for x in keys if abs(x['t0'] - x0) < 0.35 or (x0 <= x['t0'] < x1 - 1.0)), None)
            seam = any(abs(c - x0) < 0.05 for c in cuts)
            if mode == 'mixed' and key and key['t1'] - key['t0'] >= 2.5 and since >= 3:   # 一句两推
                hl = key.get('hl') or []
                tm = (word_time(hl[1][:4], base, key['t0']) if len(hl) > 1 else None) or (key['t0'] + key['t1']) / 2
                tm = min(max(tm, max(x0, key['t0']) + 0.6), x1 - 0.6)
                ta = max(x0, key['t0'])
                if tm > ta + 0.5:
                    if ta > x0 + 0.05 and z != 1.0:
                        out.append({'t0': round(x0, 3), 't1': round(ta - 0.001, 3), 'from': z, 'to': z, 'ease': 0.01, 'auto': True})
                    out.append({'t0': round(ta, 3), 't1': round(tm - 0.001, 3), 'from': z, 'to': round(z * 1.05, 3), 'ease': 0.12, 'auto': 'two_step'})
                    out.append({'t0': round(tm, 3), 't1': round(x1, 3), 'from': round(z * 1.05, 3), 'to': round(z * 1.10, 3), 'ease': 0.12, 'auto': 'two_step'})
                    since = 0
                    continue
            if mode in ('snap', 'mixed') and (seam or key) and since >= 3:   # 句首快推
                out.append({'t0': round(x0, 3), 't1': round(x1, 3), 'from': z, 'to': round(z * 1.07, 3), 'ease': 0.15, 'auto': 'snap'})
                since = 0
                continue
            if z != 1.0:
                out.append({'t0': round(x0, 3), 't1': round(x1, 3), 'from': z, 'to': z, 'ease': 0.01, 'auto': True})
    return out


# ---------------------------------------------------------------- 画面与镜头（手法库第 2 批）
# 手写 zoom 的缓推预设（slow_push_drift）：suspense 开场铺悬念 1.5 秒推到 115%；settle 段尾整段慢推到 112%。
# 都可以再写 dx（横向漂移，占画面宽的比例，正数往右）。
ZOOM_PUSH = {'suspense': dict(to=1.15, ease=1.5), 'settle': dict(to=1.12)}
CARD_FITS = ('card', 'contain', 'tilt', 'pages')
STACK_Y = {1: [0.45], 2: [0.32, 0.62], 3: [0.25, 0.48, 0.71]}


def zoom_preset(z):
    if not z.get('push'):
        return z
    if z['push'] not in ZOOM_PUSH:
        raise SystemExit(f"zoom 的 push「{z['push']}」不存在，可选：{'、'.join(ZOOM_PUSH)}")
    p = ZOOM_PUSH[z['push']]
    return {'from': 1.0, 'to': p['to'], 'ease': p.get('ease', z['t1'] - z['t0']), **z}


def expand_shots(tl, st):
    """第 2 批画面手法的展开（成片、剪映草稿、节奏检查共用；只改内存里的 timeline，不改文件）：
    - aside 版式写了 stack：几张截图卡片依次进场、错位叠放（aside_blur_stack）
    - tilt 卡片没写方向的左右交替（perspective_card）
    - 两张卡片首尾相接时，前一张往左移出、后一张从右边同速接着移入，像一个连续的动作（match_motion_cut）；
      写 "link": "left|right|up" 指定方向，timeline 写 "auto_link": false 关掉自动
    - inset 缩放配推近或拉远声、circle 收圆配拉远声、split 分屏配机械开合声（按音效密度上限取舍）
    第 3 批卡片与章节：
    - 开场第一秒入场冲击（opening_entry_hit）：按 opening_plan 补第一声音效和推近
    - 章节页、目录回顾、关注尾帧在画面上时常驻字幕让开（两层字不打架）
    - 样机、头像图文版、目录回顾、关注尾帧、纸页飞入、截图划重点自带音效；装饰边框卡默认放胸口、从下往上滑入"""
    if tl.get('_shots'):
        return tl
    tl['_shots'] = True
    layout = [dict(l) for l in tl.get('layout', [])]
    broll = [dict(b) for b in tl.get('broll', [])]
    for l in layout:
        if l['mode'] == 'aside' and l.get('stack'):
            n = len(l['stack'])
            ys = STACK_Y.get(n) or [0.2 + 0.55 * i / (n - 1) for i in range(n)]
            enters = ['slide_left', 'slide_right', 'slide_up']
            for i, it in enumerate(l['stack']):
                it = {'src': it} if isinstance(it, str) else dict(it)
                t0 = l['t0'] + it.pop('at', i * l.get('interval', 0.5))
                cv = tl.get('canvas', {'w': 1080, 'h': 1920})
                if is_landscape(cv['w'], cv['h']):
                    # 人物已移开，截图沿横幅排成列，每列给投影和进场留出空隙。
                    broll.append({'t0': round(t0, 3), 't1': l['t1'], 'fit': 'card', 'w': 0.90 / n - 0.045,
                                  'max_h': 0.62, 'x': 0.05 + (i + 0.5) * 0.90 / n, 'y': 0.44,
                                  'enter': 'slide_up', 'dim': False, 'stack': True, **it})
                    continue
                broll.append({'t0': round(t0, 3), 't1': l['t1'], 'fit': 'card', 'w': 0.80, 'max_h': round(0.66 / n, 3),
                              'x': 0.5 + (0.025 if i % 2 else -0.025) * (n > 1), 'y': ys[i], 'enter': enters[i % 3],
                              'dim': False, 'stack': True, **it})
    broll.sort(key=lambda b: b['t0'])
    for b in broll:
        if b.get('fit') == 'pages' and 'src' not in b:
            b['src'] = b['srcs'][0]
        if b.get('frame'):   # 装饰边框素材卡（clip_card_frame）：胸口到腰之间的横版卡，从下往上滑入
            b.setdefault('w', 0.68)
            b.setdefault('y', 0.57)
            b.setdefault('enter', 'slide_up')
    k = 0
    for b in broll:
        if b.get('fit') == 'tilt' and not b.get('tilt'):
            b['tilt'] = ('left', 'right')[k % 2]
            k += 1
    for a, b in zip(broll, broll[1:]):
        if a.get('fit') not in CARD_FITS or b.get('fit') not in CARD_FITS or a.get('stack') or b.get('stack') or 'pages' in (a['fit'], b['fit']):
            continue
        if not -0.02 <= b['t0'] - a['t1'] < 0.1:
            continue
        d = b.get('link') or (tl.get('auto_link', True) and 'enter' not in b and 'exit' not in a and 'left')
        if d:
            a['exit'], b['enter'] = f'move_{d}', f'move_{d}'
    for l in layout:
        if l['mode'] in ('inset', 'circle', 'split', 'frame') and 'sound' not in l and l.get('sfx') is not False:
            anim = l.get('anim', 'static')
            at = 0 if l['mode'] != 'inset' else (None if anim == 'static' else
                                                  l.get('at', min(1.0, (l['t1'] - l['t0']) * 0.4) if anim == 'expand' else 0))
            if at is not None:   # 推拉、形变、分屏配机械声（sfx_event_engine）：分屏像两扇门拉开，缩小配拉远，放大配推近
                snd = {'split': 'mech_wind', 'circle': 'zoom_out', 'frame': 'mech_robot'}.get(l['mode']) or \
                    ('mech_door' if anim in ('expand', 'shrink') else 'zoom_out' if anim != 'static' else 'whoosh')
                l['sound'], l['sound_auto'] = [{'type': snd, 'at': at}], True
        elif l['mode'] in ('mockup', 'combo', 'overview', 'endcard') + MATTE_MODES and 'sound' not in l and l.get('sfx') is not False:
            l['sound'], l['sound_auto'] = layout_sounds(l, tl), True
    for b in broll:
        if 'sound' in b or b.get('sfx') is False:
            continue
        if b.get('fit') == 'pages':
            b['sound'], b['sound_auto'] = [{'type': 'page', 'at': 0.05}], True
        elif b.get('marks'):
            b['sound'], b['sound_auto'] = [{'type': 'zip_up', 'at': a} for a in mark_times(b)], True
    for x in tl.get('voice_fx', []):   # 变声段的画面（voice_fx_swap）：扩音器叠录制边框，哔声在嘴边贴「消音」
        if any(t.get('_vfx') == (x['t0'], x['t1']) for t in tl.get('titles', [])):
            continue
        if x['type'] == 'megaphone':
            tl.setdefault('titles', []).append({'t0': x['t0'], 't1': x['t1'], 'layout': 'recframe', 'sfx': False, '_vfx': (x['t0'], x['t1'])})
        elif x['type'] == 'bleep':
            tl.setdefault('titles', []).append({'t0': x['t0'], 't1': x['t1'], 'layout': 'note', 'variant': 'tag', 'text': x.get('label', '消音'),
                                                'x': 0.5, 'y': 0.4, 'size_h': 0.05, 'color': '#FFE24A', 'sfx': False, '_vfx': (x['t0'], x['t1'])})
    hush = [(t['t0'], t['t1']) for t in tl.get('titles', []) if t.get('layout') in CHAPTER_LAYOUTS] + \
        [(l['t0'], l['t1']) for l in layout if l['mode'] in ('overview', 'endcard')]
    if hush and tl.get('subs'):   # 章节页、目录、尾帧上已经有字，常驻字幕这几秒让开
        tl['subs'] = [x for x in tl['subs'] if not any(a <= (x['t0'] + x['t1']) / 2 < b for a, b in hush)]
    op = opening_plan({**tl, 'layout': layout, 'broll': broll}, st)
    if op:
        tl['_opening'] = op
        tl['sounds'] = list(tl.get('sounds', [])) + [{'t': 0.0, 'type': op['sound']}]
        if op.get('zoom'):
            tl['zoom'] = list(tl.get('zoom', [])) + [op['zoom']]
    tl['layout'], tl['broll'] = layout, broll
    return tl


# ---------------------------------------------------------------- 卡片与章节（手法库第 3 批）
# 开场第一秒入场冲击（opening_entry_hit，规律「开场第一秒必须有一个画面动作加一个音效」）。timeline 顶层写 "opening"，
# 不写按强度档自动选（网感档 zoom、克制档 spotlight、综艺感 flash），写 false 关掉。开头就是铺满素材或别的版式时不自动加。
OPENINGS = {
    'flash': dict(dur=0.3, sound='bell', use='闪白响铃：过曝白光加竖向动态模糊 0.2 秒闪入，落定时略放大'),
    'zoom': dict(dur=0.45, sound='click', use='从小放大：画面先以 45% 大小出现在黑底中间，0.4 秒放大铺满'),
    'boom': dict(dur=0.6, sound='thump', use='综艺咚加冲刺：放射速度线冲 0.6 秒，画面从 115% 弹回'),
    'iris': dict(dur=0.8, sound='whoosh', use='光圈打开：黑底上一个小圆从人脸处张开到 60% 宽，再打开到全屏'),
    'spotlight': dict(dur=None, sound='tap', use='聚光推近：第一句四周压成椭圆暗角只有人亮，同时整句缓推到 112%'),
}


def opening_plan(tl, st):
    kind = tl.get('opening', st.get('opening'))
    if not kind:
        return None
    if kind not in OPENINGS:
        raise SystemExit(f"opening「{kind}」不存在，可选：{'、'.join(OPENINGS)}")
    if 'opening' not in tl and (any(l['t0'] < 0.3 and l['mode'] in COVER_MODES for l in tl.get('layout', []))
                                or any(b['t0'] < 0.3 and b.get('fit', 'cover') in FULL_FITS for b in tl.get('broll', []))
                                or any(t['t0'] < 0.3 and (t.get('layout') in COVER_TITLES or t.get('cover')) for t in tl.get('titles', []))):
        return None
    subs = sorted(tl.get('subs', []), key=lambda x: x['t0'])
    first = subs[0]['t1'] if subs else 3.0
    dur = OPENINGS[kind]['dur'] or round(min(4.0, max(1.5, first)), 3)
    plan = {'type': kind, 'dur': dur, 'sound': OPENINGS[kind]['sound']}
    if kind == 'spotlight':
        plan['zoom'] = {'t0': 0.0, 't1': dur, 'from': 1.0, 'to': 1.12, 'ease': dur}
    elif kind == 'boom':
        plan['zoom'] = {'t0': 0.0, 't1': dur, 'from': 1.15, 'to': 1.0, 'ease': 0.2}
    return plan


# 目录回顾（points_overview）每张卡或每一行出现的间隔（秒），cards.py 和音效共用
OVERVIEW_EVERY = {'toc': 0.3, 'list': 0.08, 'grid': 0.6, 'tilted_collage': 0.25}


def item_times(l, n, every):
    """版式里第 i 个内容出现的相对秒数：写了 at 列表就用写的，否则从 start 起每隔 every 一个。"""
    at = l.get('at') if isinstance(l.get('at'), list) else None
    return [at[i] if at and i < len(at) else l.get('start', 0.3) + i * l.get('every', every) for i in range(n)]


def layout_sounds(l, tl):
    """第 3、4 批版式自带的声音（相对这段版式开始的秒数）。抠像虚化背景、只加描边是静的。"""
    m, v = l['mode'], l.get('variant')
    if m == 'mockup':
        return [{'type': 'whoosh', 'at': 0.0}] + ([{'type': 'whoosh', 'at': l.get('at2', 0.8)}] if v == 'stack' else [])
    if m == 'combo':
        return [{'type': 'pop', 'at': a} for a in item_times(l, len(l.get('cards') or []), 0.5)][:3] or [{'type': 'pop', 'at': 0.0}]
    if m == 'overview':
        v = v or 'grid'
        if v == 'list':
            return [{'type': 'tick', 'at': 0.3, 'dur': 0.9}]
        if v == 'tilted_collage':
            return [{'type': 'whoosh', 'at': 0.0}]
        n = len(l.get('items') or []) or max(1, sum(1 for t in tl.get('titles', []) if t.get('layout') in CHAPTER_LAYOUTS))
        return [{'type': 'pop', 'at': a} for a in item_times(l, min(n, 4), OVERVIEW_EVERY[v])]
    if m == 'endcard':
        return [{'type': 'ding', 'at': 0.3}] if v == 'name' else [{'type': 'pop', 'at': 0.05}, {'type': 'ding', 'at': 0.75}]
    if m == 'corner':   # 人缩进角落一声嗖，卡片一张一声啵
        n = len(l.get('items') or [])
        start = 0.5 if (v or 'point_cards') in ('point_cards', 'glass_cards') else 0.4
        return [{'type': 'whoosh', 'at': 0.0}] + [{'type': 'pop', 'at': a} for a in item_times({'start': start, **l}, min(n, 3), 0.3)]
    if m == 'morph':   # 窗口按节拍变形：每变一次啵一声
        k = len(l.get('steps') or [0] * 5)
        d = l['t1'] - l['t0']
        return [{'type': 'pop', 'at': a} for a in (l.get('at') or [round(d * j / k, 3) for j in range(k)])]
    if m == 'breakout' or (m == 'matte' and (l.get('src') or l.get('bg') not in (None, 'blur', 'keep'))):
        return [{'type': 'pop', 'at': 0.0}]   # 出框、换话题背景硬切的那一下
    return []


def mark_times(b):
    """截图划重点每一道开始划的相对秒数。"""
    mk = b['marks']
    return item_times(mk, len(mk.get('boxes', [])), 0.6) if isinstance(mk, dict) else []

# ---------------------------------------------------------------- 转场
# 效果转场只放在章节点（原片九成以上是硬切），30 秒内最多一个，同一种不连用。jy 是剪映里对应的转场名。
# lead 是转场在切点前占的比例（默认 0.35），variants 里的变体可以改时长和 lead。第 8 批的几种由 effects.transition 画。
TRANSITIONS = {
    'flash':      dict(dur=0.5, jy='闪白', use='闪白：换小节、换话题'),
    'dip_black':  dict(dur=0.4, jy='闪黑', use='压黑：段落收尾、情绪沉下来'),
    'blur_swipe': dict(dur=0.35, jy='竖向模糊', use='动态模糊扫屏：节奏快的段落切换'),
    'light_leak': dict(dur=0.6, lead=0.5, jy='复古漏光', use='漏光闪过：几团橙黄暖光从一侧扫过，几乎铺满时换段（温和、怀旧、换场景）',
                       variants={'flash': {}, 'zoom_reveal': {'dur': 0.7, 'lead': 0.4}}),
    'glitch':     dict(dur=0.3, lead=0.5, jy='信号故障', use='RGB 故障闪切：红青通道错开、几条横切片左右错位（出错、科技、综艺感）'),
    'whip':       dict(dur=0.3, lead=0.5, jy='横向模糊', use='动态模糊甩切：整屏往一边甩走，下一段同方向甩进来（列举、话题切换），dir 写 left / right / up / down'),
    'iris':       dict(dur=0.7, lead=0.43, jy='圆形遮罩', use='圆形光圈：画面收成中下部一个圆，圆里换成下一段再放大；open 从黑底小圆打开',
                       variants={'swap': {}, 'open': {'dur': 0.85, 'lead': 0.0}}),
    'tear':       dict(dur=0.45, lead=0.0, jy='撕纸', use='撕纸揭开：上一画面被一道带白纸芯的撕边撕掉，露出下一段；split 从中间上下撕开',
                       variants={'diagonal': {}, 'split': {'dur': 0.5}}),
    'blocks':     dict(dur=0.4, lead=0.45, jy='色块故障', use='色块碎片擦屏：橙红深色矩形碎块几帧内铺满整屏再散开露出下一段；bars 黑色竖条随机升起擦屏',
                       variants={'random': {}, 'bars': {'dur': 0.5}}),
    'tunnel':     dict(dur=0.45, lead=0.15, jy='穿越', use='隧道穿梭：中心放射光柱冲出来，下一段从中间 20% 冲到满屏（开场第一下、章节页进正片）'),
    'occlude':    dict(dur=0.4, lead=0.5, jy='竖向模糊', use='主题物遮挡扫屏：主题物带纵向模糊从下往上冲过，盖满那一帧换段（src 写主题物图，或 emoji 写 3D 表情名）'),
}


def tr_window(tr):
    """转场的起点和时长：(a0, d)。"""
    T = TRANSITIONS.get(tr['type'], {})
    V = (T.get('variants') or {}).get(tr.get('variant'), {})
    d = float(tr.get('dur', V.get('dur', T.get('dur', 0.5))))
    lead = V.get('lead', T.get('lead', 0.35))
    return max(0.0, tr['t'] - d * lead), d


# ---------------------------------------------------------------- 整屏特效（手法库第 8 批，effects.py 画）
# timeline 顶层写 "fx": [{t0, t1, type, variant, ...}]。layer：pic 压在常驻字幕下面，screen 连字幕一起。
# sound 是自带声音（写 "sound" 换、"sfx": false 关）；jy 是剪映草稿里对应的特效名，没有的那几秒草稿里铺成片画面。
FX = {
    'bw':        dict(layer='pic', sound='drop', jy='变黑白', use='变黑白：失落、听不懂，整屏去色，前后 0.15 秒渐变'),
    'shake':     dict(layer='screen', sound='thump', jy='震动', use='震动：冲击、惊讶，整屏约 12 Hz 抖动、越抖越轻（amp 改幅度）'),
    'crack':     dict(layer='screen', sound='hit', jy='裂开了', use='裂开了：崩溃，屏幕从 at 那一点（默认右上角，避开脸）裂开，跟着抖一下'),
    'magnifier': dict(layer='pic', sound='zoom_in', use='放大镜：at 那一点放大 zoom 倍（默认 2），带镜框手柄，0.15 秒弹出；variant reach 手柄从画外 from 伸进来、镜片滑到 at 再移走（默认 1.5 倍）'),
    'the_end':   dict(layer='screen', sound='swell', jy='全剧终', use='全剧终：片尾整屏压暗，毛笔「全剧终」大字加 THE END'),
    'blur':      dict(layer='pic', sound=None, use='模糊遮挡：box 框里强模糊遮隐私，优先于马赛克'),
    'spotlight': dict(layer='pic', sound='thump', jy='聚光灯', use='聚光灯暗角：四周压成黑色椭圆暗角只有人亮；push 同时缓推到 112%，drama 加荧幕噪点',
                      variants={'push': '聚光加推近', 'drama': '戏剧聚焦：加荧幕噪点，配重音'}),
    'crt':       dict(layer='pic', sound='glitch', jy='复古电视', use='扫描线老电视：细横向扫描线加暗角；emphasis 一句话强调，section 段落收尾加桶形弯曲和推近',
                      variants={'emphasis': '一句话强调', 'section': '段落质感'}),
    'halftone':  dict(layer='pic', sound=None, jy={'screenprint': '网点丝印'}, use='网点丝印质感：screenprint 细密网点略偏蓝、扣掉人像只在背景上；bg_grain 压暗背景上的颗粒',
                      variants={'screenprint': '整体丝印叠加', 'bg_grain': '暗背景颗粒'}),
    'grade':     dict(layer='pic', sound=None, use='调色变化：desat_cool 整段降饱和偏冷灰；band 先变黑白，红绿橙色块依次从脸部扫过',
                      variants={'desat_cool': '去色冷灰', 'band': '黑白加色块扫'}),
    'letterbox': dict(layer='screen', sound='whoosh', use='宽银幕黑边：上下黑边 0.2 秒滑进来，停 1~3 秒滑走；text 写了在下黑边里横向滚动'),
    'dimbox':    dict(layer='pic', sound='tick', use='压暗聚光框游走：整屏压到四成亮，白色虚线框里保持原亮度，在脸、胸口之间移动变形（boxes 写框）'),
    'tilt':      dict(layer='screen', sound='whoosh', use='画面歪头倾斜：0.3 秒整屏转到 angle（默认 -10 度）略放大，back 写了最后转回来（高级感慎用）'),
    'face':      dict(layer='pic', sound=None, use='人脸情绪特效：names 写剪映人物特效名，草稿里放剪映真特效，成片用抠像放大头、头边贴表情和手写符号近似'),
}

# 人脸情绪特效（face_effect_emotion）：剪映人物特效名 → 成片里的近似做法和声音。
# head 头放大倍数、emoji 头边的 3D 表情（Fluent Emoji 英文名）、marks 头边蹦出的手写符号、tag 头顶小标签、
# tint 头部染色、gray 整个人变灰、glitch 人像红蓝错开、sparkle 头边星光、shake 整屏抖一下
FACE_FX = {
    '大头':     dict(head=1.4, sound='boing'),
    '红温大头': dict(head=1.4, tint='#FF2A1A', emoji='Face with steam from nose', sound='boing'),
    '一脸问号': dict(marks='???', sound='dizzy'),
    '懵':       dict(marks='?', emoji='Face with spiral eyes', sound='dizzy'),
    '迷茫':     dict(marks='?', emoji='Thinking face', sound='dizzy'),
    '惊讶':     dict(head=1.2, marks='!', emoji='Face with open mouth', sound='boing'),
    '中刀':     dict(emoji='Kitchen knife', shake=True, sound='blade_swish'),
    '打击':     dict(emoji='Collision', shake=True, sound='punch'),
    '石化了':   dict(gray=True, emoji='Rock', tag='石化了', sound='drop'),
    '宕机中':   dict(glitch=True, emoji='Hourglass not done', tag='宕机中…', sound='glitch'),
    '尴尬住了': dict(emoji='Sweat droplets', tag='尴尬住了', sound='rimshot'),
    '灵机一动': dict(emoji='Light bulb', sparkle=True, sound='bell'),
    '真的会谢': dict(emoji='Wilted flower', tag='真的会谢', sound='sad_trombone'),
    '秘密':     dict(emoji='Shushing face', sound='pop'),
}


def fx_sounds(f):
    """整屏特效自带的声音：[sound 字段]，at 相对特效开始。压暗聚光框每移一次一声，人脸特效按特效名，戏剧聚焦配重音。"""
    if 'sound' in f:
        return f['sound'] if isinstance(f['sound'], list) else [f['sound']]
    kind = f['type']
    if kind == 'dimbox':
        return [{'type': 'tick', 'at': 0.0}] + [{'type': 'tick', 'at': b['at']} for b in (f.get('boxes') or [])[1:]] if f.get('boxes') else \
            [{'type': 'tick', 'at': 0.0}, {'type': 'tick', 'at': round((f['t1'] - f['t0']) * 0.5, 2)}]
    if kind == 'face':
        return [{'type': FACE_FX[n]['sound'], 'at': 0.05 + 0.12 * j} for j, n in enumerate((f.get('names') or [])[:2]) if FACE_FX.get(n, {}).get('sound')]
    if kind == 'spotlight' and f.get('variant') == 'drama':
        return ['hit']
    if kind == 'grade' and f.get('variant') == 'band':
        return [{'type': 'whoosh', 'at': 0.15 + 0.35 * j} for j in range(3)]
    snd = FX[kind]['sound']
    return [snd] if snd else []


def fx_jy(f):
    """草稿里放的剪映特效名列表；剪映做不出来的返回空。"""
    if f['type'] == 'face':
        return list(f.get('names') or [])
    jy = FX[f['type']].get('jy')
    if isinstance(jy, dict):
        jy = jy.get(f.get('variant') or next(iter(FX[f['type']].get('variants', {'': 0}))))
    return [jy] if jy else []


def auto_transitions(tl, st):
    """章节页开始处自动加效果转场，按风格轮换、相邻不同、30 秒内最多一个。timeline 写了 transitions 就用写的；
    写 "auto_transitions": false 关掉。"""
    if 'transitions' in tl:
        return tl['transitions']
    kinds = st.get('transition_kinds')
    if not kinds or tl.get('auto_transitions') is False:
        return []
    out, last_t, k = [], -99.0, 0
    for t in sorted(x['t0'] for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS and x.get('enter') != 'cover'):   # 白场接力页是章节页的延续
        if t - last_t < 30:
            continue
        out.append({'t': round(t, 3), 'type': kinds[k % len(kinds)]})
        k, last_t = k + 1, t
    return out


def expand_bgm(tl, base='.'):
    """配乐换段：只有一首配乐时，在每个章节页的位置跳到同一首曲子里能量最高的另一段，并让那一段的重拍正好落在章节页上。
    依据一条头部财经知识口播原片：5 分半换了 8 段配乐，一条音乐铺到底就显得平。需要配乐旁边的节拍文件（beat_sync 会生成）。
    timeline 写 "music_sections": false 关掉。返回展开后的 bgm 列表（render 和 build_draft 用它代替 audio.bgm）。"""
    bgms = tl.get('audio', {}).get('bgm', [])
    if len(bgms) != 1 or tl.get('music_sections') is False:
        return bgms
    m = bgms[0]
    src = Path(m['src']) if Path(m['src']).is_absolute() else Path(base) / m['src']
    bj = src.with_suffix('.beats.json')
    chapters = sorted(x['t0'] for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS and m['t0'] + 5 < x['t0'] < m['t1'] - 3)
    if not bj.exists() or not chapters:
        return bgms
    bt = json.loads(bj.read_text(encoding='utf-8'))
    energy = dict((round(t, 3), e) for t, e in bt.get('energy', []))
    downs = bt['downbeats']
    segs, start, src_in, used = [], m['t0'], m.get('src_in', 0.0), []
    for c in chapters:
        pos = src_in + (c - start)                        # 不跳的话此刻放到曲子哪里
        rest = (m['t1'] - c)
        cands = [d for d in downs if abs(d - pos) > 8 and d + min(rest, 20) <= bt['duration'] and all(abs(d - u) > 8 for u in used)]
        if not cands:
            continue
        d = max(cands, key=lambda d: (energy.get(round(d, 3), 0), -d))
        segs.append({**m, 't0': start, 't1': c, 'src_in': round(src_in, 3), 'fade_out': 0.12, **({'fade_in': m.get('fade_in', 0.5)} if not segs else {'fade_in': 0.05})})
        used.append(d)
        start, src_in = c, d
    if not segs:
        return bgms
    segs.append({**m, 't0': start, 't1': m['t1'], 'src_in': round(src_in, 3), 'fade_in': 0.05})
    return segs


def music_breaks(tl, st):
    """配乐留白：章节页出现前把配乐压下去一小会儿，章节页那一下再回来（配上章节音效），像一口气停住再进。
    依据一条头部财经知识口播原片：约 46 秒一次 0.5~2 秒的音乐留白，停完总是接一个大变化。返回 [(开始秒, 结束秒)]，相隔至少 30 秒。
    timeline 写 "music_breaks": [[t0, t1], ...] 就用写的，写 false 关掉。"""
    extra = [tuple(x) for x in tl.get('_breaks', [])]   # 段落收尾推高收束：章节页那一下停 1.2 秒（structure.prepare 写）
    if 'music_breaks' in tl:
        return [tuple(x) for x in (tl['music_breaks'] or [])] + extra
    length = st.get('break_len', 0.7)
    out, last = [(fz['t0'], fz['t1']) for fz in tl.get('freezes', [])], -99.0   # 定格时配乐静音
    for t in sorted(x['t0'] for x in tl.get('titles', []) if x.get('layout') in CHAPTER_LAYOUTS and x.get('enter') != 'cover'):   # 白场接力页是章节页的延续
        if t <= length + 1:
            continue
        if t - last >= 30:
            out.append((round(t - length, 3), round(t, 3)))
            last = t
        else:   # 离上一次留白不到 30 秒：配乐换段的地方只轻轻停 0.3 秒，让换段不突兀
            out.append((round(t - 0.3, 3), round(t, 3)))
    return out + extra


# ---------------------------------------------------------------- 风格预设
# 尺寸都以短边 1080 为基准，渲染时乘 unit(W, H)。位置仍按各自宽高的比例。
# y 是文字中心的纵向位置（0 顶部，1 底部）。

STYLES = {
    'premium': {
        'sub': {  # 跟读字幕：半透明黑色圆角底条 + 白色思源黑体粗体，任何背景上都清楚；重点句底条更深、字更大，强调词再加粗，不变色
            'base': dict(size=54, color='#FFFFFF', y=0.80, spacing=1, box=dict(color='#000000', alpha=0.45, pad_x=30, pad_y=16)),
            'key': dict(size=60, color='#FFFFFF', y=0.80, spacing=1, box=dict(color='#000000', alpha=0.6, pad_x=34, pad_y=18)),
            'pip_y': 0.70,
            'hl_color': '#FFFFFF',      # 字幕里的强调词只加粗（换 sub_key 字体），颜色留给大字
            'hl_weight': True,
        },
        'title': dict(size=200, color='#F7F5F0', hl_color='#D7262D', condense=82, lead_size=52, lead_color='#EEF0F2',
                      en_size=60, tag_size=38, anim='blur_in', layout='side', ink_color='#16161A', shadow_alpha=0x90),
        'blur_bg': dict(blur=30, darken=0.55),
        'card': dict(radius=26, shadow=40, shadow_alpha=140, border=0, border_color='#FFFFFF'),
        'pip': dict(d=0.30, x=0.79, y=0.845, border=4, border_color='#F7F5F0'),
        'punch': dict(scale=1.08, dur=0.15),
        'zoom_tiers': [1.0, 1.15, 1.25],   # 口播景别三档
        'card_motion': 'rise',             # 卡片、截图默认缓缓上浮
        'transition_kinds': ['flash', 'blur_swipe', 'light_leak', 'dip_black'],
        'bgm_lufs': -23, 'sfx_peak': -9, 'voice_lufs': -16,   # 配乐不压人声时 -23 LUFS，说话时侧链再压 6~8 dB
        'sfx_kit': 'premium',   # 没装 earshot 时自动配音效用的 Mixkit 音效库，见 SFX_KITS
        'sfx_per_min': 12,      # 音效密度上限：财经知识口播原片每分钟约 6 个，对着内容的声音不受限
    },
    'variety': {
        'sub': {
            'base': dict(size=62, color='#FFFFFF', outline=2.2, outline_color='#000000CF', y=0.79, spacing=1),   # 抖音美好体 + 细黑边
            'key': dict(size=80, color='#FFD23F', outline=4, outline_color='#000000E0', y=0.78, spacing=1),
            'pip_y': 0.68,
            'hl_color': '#FFD23F',
        },
        'title': dict(size=150, color='#FFD23F', hl_color='#FF4D4F', condense=100, outline=9, outline_color='#000000',
                      lead_size=48, lead_color='#FFFFFF', en_size=56, tag_size=36, anim='pop', layout='plain', shadow_alpha=0x60),
        'blur_bg': dict(blur=22, darken=0.30),
        'card': dict(radius=24, shadow=24, shadow_alpha=120, border=6, border_color='#FFFFFF'),
        'pip': dict(d=0.36, x=0.76, y=0.82, border=8, border_color='#FFD23F'),
        'punch': dict(scale=1.14, dur=0.10),
        'zoom_tiers': [1.0, 1.15, 1.3],
        'card_motion': 'rise',
        'transition_kinds': ['flash', 'glitch', 'whip', 'tear', 'blur_swipe'],
        'bgm_lufs': -21, 'sfx_peak': -6, 'voice_lufs': -15,
        'sfx_kit': 'variety',
        'sfx_per_min': 25,
    },
}


def deep_merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


# 高级感的两个强度档：网感档（默认）节奏快、信息密，可以用打字机、标签卡、闪现这类网感手法；
# 克制档更安静，只用纯高级感手法、音效更少。综艺感没有强度档。
# opening 是开场第一秒的入场冲击（见 OPENINGS），chapter_look 是全片统一的章节载体（library.expand_beats 用）。
TONES = {
    'premium': {
        'web': {'tone': 'web', 'sfx_per_min': 18, 'title': {'en_look': 'tracked'}, 'zoom_mode': 'mixed', 'opening': 'zoom', 'chapter_look': 'fog',
                'transition_kinds': ['whip', 'light_leak', 'iris', 'tear', 'flash']},
        'calm': {'tone': 'calm', 'sfx_per_min': 8, 'title': {'en_look': 'serif'}, 'zoom_mode': 'jump', 'opening': 'spotlight', 'chapter_look': 'chapter'},
    },
    'variety': {'web': {'tone': 'variety', 'zoom_mode': 'mixed', 'opening': 'flash', 'chapter_look': 'chapter_page'}},
}
DEFAULT_TONE = {'premium': 'web', 'variety': 'web'}

# 常驻字幕的样子（timeline 写 "sub_look"）。手法库 sub_soft_shadow 的几个变体 + 默认底条。
SUB_LOOKS = {
    'box': {},   # 风格默认：高级感半透明黑底条，综艺感细黑边
    'shadow': {'base': dict(size=54, color='#FFFFFF', y=0.80, spacing=1, box=None, shadow_alpha=0x70),
               'key': dict(size=60, color='#FFFFFF', y=0.80, spacing=1, box=None, shadow_alpha=0x60)},
    'serif': {'base': dict(size=52, color='#FDFBF7', y=0.70, spacing=2, box=None, shadow_alpha=0x66),
              'key': dict(size=58, color='#FDFBF7', y=0.70, spacing=2, box=None, shadow_alpha=0x5A),
              'pip_y': 0.62, '_fonts': {'sub': 'Source Han Serif CN Bold', 'sub_key': 'Source Han Serif CN Heavy'}},
    'low': {'base': dict(size=44, color='#FFFFFF', y=0.90, spacing=2, box=None, shadow_alpha=0x80),
            'key': dict(size=48, color='#FFFFFF', y=0.90, spacing=2, box=None, shadow_alpha=0x70)},
    # 黑底条访谈字幕（sub_box）：不透明黑条、小圆角，像访谈节目
    'bar': {'base': dict(size=52, color='#FFFFFF', y=0.80, spacing=1, box=dict(color='#000000', alpha=1.0, pad_x=26, pad_y=14, r=6)),
            'key': dict(size=58, color='#FFFFFF', y=0.80, spacing=1, box=dict(color='#000000', alpha=1.0, pad_x=30, pad_y=16, r=6))},
    # 描边综艺字幕（sub_outline）：outline 白字黑边（综艺感默认就是这种）/ chest 胸口深蓝圆体白边 / huazi 整句蓝边黄字垫黑底
    'outline': {'base': dict(size=60, color='#FFFFFF', outline=2.6, outline_color='#000000', y=0.79, spacing=1, box=None),
                'key': dict(size=72, color='#FFFFFF', outline=3.4, outline_color='#000000', y=0.78, spacing=1, box=None),
                '_fonts': {'sub': 'Source Han Sans CN Heavy', 'sub_key': 'Source Han Sans CN Heavy'}},
    'chest': {'base': dict(size=64, color='#2F5BA8', outline=1.8, outline_color='#FFFFFF', y=0.62, spacing=2, box=None),
              'key': dict(size=76, color='#2F5BA8', outline=2.4, outline_color='#FFFFFF', y=0.62, spacing=2, box=None),
              'pip_y': 0.56, '_fonts': {'sub': 'ZCOOL KuaiLe', 'sub_key': 'ZCOOL KuaiLe'}},
    'huazi': {'base': dict(size=62, color='#FFD21F', outline=3.2, outline_color='#1F5BD8', y=0.79, spacing=2,
                           box=dict(color='#000000', alpha=0.88, pad_x=24, pad_y=12, r=8)),
              'key': dict(size=74, color='#FFD21F', outline=3.8, outline_color='#1F5BD8', y=0.78, spacing=2,
                          box=dict(color='#000000', alpha=0.9, pad_x=28, pad_y=14, r=8)),
              '_fonts': {'sub': 'DouyinSans Bold', 'sub_key': 'DouyinSans Bold'}},
    # 双行滚动字幕（sub_rolling_two_line）：左下角两行，当前句在下、上一句变灰在上，换句整体上滚；只适合无人出镜的解说、测评
    'rolling': {'base': dict(size=64, color='#FFFFFF', y=0.9, spacing=1, box=None), 'key': dict(size=64, color='#FFFFFF', y=0.9, spacing=1, box=None),
                'rolling': True, 'prev_color': '#9A9A9A'},
    'rolling_ink': {'base': dict(size=64, color='#1E1714', y=0.9, spacing=1, box=None), 'key': dict(size=64, color='#1E1714', y=0.9, spacing=1, box=None),
                    'rolling': True, 'ink': True, 'prev_color': '#6B5F55'},
}
# 字幕里强调词的样子（timeline 写 "sub_key_look"）：weight 换粗一档（高级感默认）/ red 同号深红 / yellow 亮黄放大 /
# bracket 加【】不变色 / stripe 黄字黑边放大弹一下（综艺感默认）。一行只强调一个词。
SUB_KEY_LOOKS = {
    'weight': {'hl_weight': True, 'hl_color': '#FFFFFF'},
    'red': {'hl_weight': False, 'hl_color': '#C4161C'},
    'yellow': {'hl_weight': False, 'hl_color': '#F5C518', 'hl_scale': 1.2},
    'bracket': {'hl_weight': False, 'hl_color': None, 'hl_bracket': True},
    'stripe': {'hl_weight': False, 'hl_color': '#FFD23F', 'hl_scale': 1.4, 'hl_pop': True},
}
# 全片字体基调（timeline 写 "font_palette"），全片不超过三种字体：sans 干货黑体（高级感默认）/ serif 杂志宋体 /
# heavy 网感粗斜黑 / hand 标题换毛笔字。只换角色对应的字体，模板不写死字体名。
FONT_PALETTES = {
    'sans': {},
    'serif': {'title': 'Source Han Serif CN Heavy', 'sub': 'Source Han Serif CN Bold', 'sub_key': 'Source Han Serif CN Heavy',
              'body': 'Source Han Serif CN Bold'},
    'heavy': {'title': 'Smiley Sans Oblique', 'sub_key': 'Source Han Sans CN Heavy'},
    'hand': {'title': 'Ma Shan Zheng'},
}


def style_preset(timeline):
    """风格预设：风格默认 → 强度档（tone）→ 字幕样子（sub_look / sub_key_look）→ timeline 的 style_overrides
    （任意层级只覆盖写到的键）。字体换法放在 st['_fonts']，渲染时和 timeline 的 fonts 合并。"""
    style = timeline.get('style', 'premium')
    base = json.loads(json.dumps(STYLES.get(style, STYLES['premium'])))
    tone = timeline.get('tone', DEFAULT_TONE.get(style, 'web'))
    deep_merge(base, json.loads(json.dumps(TONES.get(style, {}).get(tone) or TONES.get(style, {}).get('web') or {})))
    look = json.loads(json.dumps(SUB_LOOKS.get(timeline.get('sub_look', 'box'), {})))
    fonts = dict(FONT_PALETTES.get(timeline.get('font_palette', 'sans'), {}))
    fonts.update(look.pop('_fonts', {}))
    for lv in ('base', 'key'):
        if lv in look:
            base['sub'][lv] = look.pop(lv)
    deep_merge(base['sub'], look)
    kl = timeline.get('sub_key_look')
    if kl:
        deep_merge(base['sub'], dict(SUB_KEY_LOOKS[kl]))
    cv = timeline.get('canvas', dict(w=1080, h=1920))
    if is_landscape(cv['w'], cv['h']):
        W, H = cv['w'], cv['h']
        base['_canvas'] = (W, H)
        for lv in ('base', 'key'):
            base['sub'][lv]['y'] = safe_zones(W, H)['sub'][1]
        base['sub']['pip_y'] = 0.88
        base['pip'].update(d=0.26 * H / W, x=1 - 0.17 * H / W, y=0.17)
    base['_fonts'] = fonts
    return deep_merge(base, timeline.get('style_overrides') or {})


def role_font_overrides(tl, st):
    """渲染用的字体覆盖：字体基调和字幕样子带来的换字体，再叠 timeline 里手写的 fonts。"""
    return {**st.get('_fonts', {}), **(tl.get('fonts') or {})}


# 小窗位置预设（pip_circle_avatar）：pos 写名字。center 是定格强调时放大到正中
PIP_POS = {'top_right': dict(x=0.78, y=0.23, d=0.25), 'top_left': dict(x=0.22, y=0.23, d=0.25), 'bottom_left': dict(x=0.18, y=0.70, d=0.25),
           'bottom_right': dict(x=0.82, y=0.75, d=0.25), 'center': dict(x=0.50, y=0.52, d=0.47)}
# 小窗样子：ring 细环硬边（默认）/ feather 羽化虚边，适合纸页和例子页 / shadow 白描边加投影，压在长录屏上
PIP_LOOKS = {'ring': {}, 'feather': dict(border=0, feather=0.2), 'shadow': dict(border=6, border_color='#FFFFFF', shadow=True)}


def pip_params(l, st):
    """一段 pip 版式的小窗参数：风格默认 → pos 位置预设 → look 样子 → 手写的 pip。"""
    pos = PIP_POS.get(l.get('pos'), {})
    if st.get('_canvas') and pos:
        W, H = st['_canvas']
        center = l['pos'] == 'center'
        d = (0.47 if center else 0.26) * H / W
        pos = dict(d=d, x=0.5 if center else (0.17 * H / W if 'left' in l['pos'] else 1 - 0.17 * H / W),
                   y=0.5 if center else (0.17 if 'top' in l['pos'] else 0.68))
    return {**st['pip'], **pos, **PIP_LOOKS.get(l.get('look', 'ring'), {}), **(l.get('pip') or {})}


HEAVY_LAYOUTS = ('chapter', 'fog', 'chapter_page', 'word', 'concept', 'number', 'bignum', 'giant', 'circletext', 'splitswap', 'topcard', 'vflank',
                 'montage', 'textfirst', 'qframe', 'poster', 'askpage', 'gesture', 'cutnum', 'slogan',
                 'flow', 'stepwall', 'typerow', 'photostack', 'quotetype', 'labelcol', 'products', 'translate',
                 'splitwin', 'window', 'bands', 'matteband', 'papercollage', 'moodword', 'parallax',
                 'overlapframe', 'credits', 'searchhook', 'shapecut', 'radial', 'diagram', 'orbitcover', 'painpoint')


def pip_hide_ranges(tl, transitions=()):
    """视觉高潮时小窗让开（hide_on_peak）：整屏大字、章节页、巨数字出现的时段，加章节转场前后，小窗整个消失再回来。"""
    out = [(t['t0'], t['t1']) for t in tl.get('titles', []) if t.get('layout') in HEAVY_LAYOUTS]
    out += [(tr_window(tr)[0], tr_window(tr)[0] + tr_window(tr)[1]) for tr in transitions]
    return out


def pip_sub_ranges(pips, st):
    """小窗落在字幕区（画面下 40%）的时间段：这些时段字幕要让到 pip_y。"""
    out = []
    for l in pips:
        p = pip_params(l, st)
        aspect = st['_canvas'][0] / st['_canvas'][1] if st.get('_canvas') else 9 / 16
        if p['y'] + p['d'] * aspect / 2 > 0.6:
            out.append((l['t0'], l['t1']))
    return out


def hex_rgba(c):
    """'#RRGGBB' 或 '#RRGGBBAA' → (r,g,b,a) 0-255。"""
    c = c.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    a = int(c[6:8], 16) if len(c) >= 8 else 255
    return r, g, b, a


# ---------------------------------------------------------------- 卡片与蒙版图

def rounded_mask(w, h, radius):
    from PIL import Image, ImageDraw
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return m


def make_card(src, out, box_w, style, max_h=None):
    """把截图/照片做成圆角加投影的卡片 PNG（透明底）。返回 (out, 卡片宽, 卡片高)。

    box_w: 卡片内容宽度（像素）。投影外扩 style['shadow'] 像素，卡片放置时以图片中心对齐。
    """
    from PIL import Image, ImageFilter
    img = Image.open(src).convert('RGBA')
    scale = box_w / img.width
    w, h = box_w, max(1, round(img.height * scale))
    if max_h and h > max_h:
        h = max_h
        w = max(1, round(img.width * h / img.height))
    img = img.resize((w, h), Image.LANCZOS)
    r, pad = style.get('radius', 24), style.get('shadow', 0)
    canvas = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if pad:
        sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        sh.paste(Image.new('RGBA', (w, h), (0, 0, 0, style.get('shadow_alpha', 100))), (pad, pad + pad // 3), rounded_mask(w, h, r))
        canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(pad / 2)))
    bw = style.get('border', 0)
    if bw:
        border = Image.new('RGBA', (w + bw * 2, h + bw * 2), hex_rgba(style.get('border_color', '#FFFFFF')))
        canvas.paste(border, (pad - bw, pad - bw), rounded_mask(w + bw * 2, h + bw * 2, r + bw))
    canvas.paste(img, (pad, pad), rounded_mask(w, h, r))
    canvas.save(out)
    return out, canvas.width, canvas.height


def circle_mask_png(d, out):
    from PIL import Image, ImageDraw
    m = Image.new('L', (d * 4, d * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
    m.resize((d, d), Image.LANCZOS).save(out)
    return out


def ring_png(d, width, color, out):
    from PIL import Image, ImageDraw
    s = 4
    im = Image.new('RGBA', (d * s, d * s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([0, 0, d * s - 1, d * s - 1], outline=hex_rgba(color), width=width * s)
    im.resize((d, d), Image.LANCZOS).save(out)
    return out


def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save_json(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def is_mac():
    return platform.system() == 'Darwin'


def pip_clip(aroll, t0, t1, W, H, FPS, d, crop, border, border_color, out, feather=0):
    """导出圆形人像小窗（带透明通道的 ProRes 4444），成片和剪映草稿共用。

    crop: {'x','y','s'} 相对画面宽度。竖屏默认顶部 8% 处取整宽正方形，横屏默认居中取短边正方形。
    feather: 羽化比例（0.15~0.25 是虚边头像），这时不画描边。返回小窗总直径（含描边）。
    """
    b = int(border)
    D = d + 2 * b
    c = crop or {'x': 0.0, 'y': 0.08, 's': 1.0}
    s, x, y = face_crop(W, H, crop)
    # 合法竖屏保留原滤镜和取整方式，保证旧片像素不变。
    valid = not is_landscape(W, H) and (s, x, y) == (W * c['s'], W * c['x'], W * c['y'])
    crop_filter = f"crop=iw*{c['s']}:iw*{c['s']}:iw*{c['x']}:iw*{c['y']}" if valid else f'crop={s}:{s}:{x}:{y}'
    rgb = hex_rgba(border_color)[:3]
    fc = (f"[0:v]scale={W}:{H},{crop_filter},scale={d}:{d},format=rgba,"
          + (f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*clip((W/2-hypot(X-W/2,Y-H/2))/(W/2*{feather}),0,1)'[face];" if feather else
             "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2-1),255,0)'[face];")
          + f"color=c=0x{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}:s={D}x{D}:r={FPS},format=rgba,"
          f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2-1),{255 if b else 0},0)'[ring];"
          f"[ring][face]overlay={b}:{b}:shortest=1[v]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-t', f'{t1 - t0:.3f}', '-i', str(aroll), '-filter_complex', fc,
                    '-map', '[v]', '-an', '-r', str(FPS), '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', str(out)],
                   check=True, capture_output=True)
    return D
