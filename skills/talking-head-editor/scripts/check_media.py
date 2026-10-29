"""素材检查：分辨率、帧率、方向、时长、响度、峰值、底噪、静音占比。

用法：python check_media.py 口播1.mov 口播2.mov ... [--broll 截图.png 录屏.mov ...] -o check.json
口播素材查画面和声音；--broll 后面的素材只查画面（不评响度和停顿）。
输出每个文件的指标和「问题」列表，问题用大白话写，可以直接转述给用户。
"""
import argparse
import re
import subprocess

from kvlib import probe, is_image, save_json, canvas_size


def loudness(path):
    """整体响度 LUFS、真峰值 dBTP、底噪估计（最安静 10% 片段的平均音量 dB）。"""
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
    pk = re.findall(r'Peak:\s+(-?[\d.inf]+) dBFS', err)
    mom = [float(x) for x in re.findall(r'M:\s*(-?[\d.]+)', err) if float(x) > -120]
    floor = None
    if mom:
        mom.sort()
        q = mom[:max(1, len(mom) // 10)]
        floor = round(sum(q) / len(q), 1)
    return (float(i[-1]) if i else None), (float(pk[-1]) if pk and pk[-1] != '-inf' else None), floor


def silence_ratio(path, dur, noise=-38, d=0.4):
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', f'silencedetect=noise={noise}dB:d={d}',
                          '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', err)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
    if len(en) < len(st):
        en.append(dur)
    total = sum(b - a for a, b in zip(st, en))
    return round(total / dur, 2) if dur else 0


def image_size(path):
    """图片真实尺寸。HEIC 用 ffprobe 只能读到缩略图，优先用 PIL 或 macOS 的 sips。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        pass
    try:
        out = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(path)], capture_output=True, text=True).stdout
        w = int(re.search(r'pixelWidth: (\d+)', out).group(1)); h = int(re.search(r'pixelHeight: (\d+)', out).group(1))
        return w, h
    except Exception:
        return 0, 0


def real_alpha(path, image):
    """像素格式带透明通道不等于真的有透明区域：抽几帧看透明通道里有没有不透明以外的值。"""
    if image:
        try:
            from PIL import Image
            with Image.open(path) as im:
                if 'A' not in im.getbands():
                    return False
                return im.getchannel('A').getextrema()[0] < 250
        except Exception:
            return False
    dur = probe(path)['duration']
    for t in (dur * 0.4, dur * 0.7):   # 只看中段：首尾常有从透明淡入淡出的帧，不代表画面本身透明
        r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(path), '-frames:v', '1', '-vf',
                            'alphaextract,scale=96:-2,format=gray', '-f', 'rawvideo', '-'], capture_output=True)
        if r.stdout and sum(v < 250 for v in r.stdout) / len(r.stdout) > 0.02:
            return True
    return False


def check(path, role='aroll', canvas=None):
    try:
        info = probe(path)
    except Exception:
        return {'file': str(path), 'kind': 'unreadable', 'w': 0, 'h': 0, 'duration': 0, 'issues': ['文件读不了：路径不对或格式损坏']}
    rep = {'file': str(path), 'role': role, **info, 'issues': []}
    iss = rep['issues']
    if is_image(path) or info['is_image']:
        rep['kind'] = 'image'
        w, h = image_size(path)
        if w:
            rep.update(w=w, h=h)
        if max(rep['w'], rep['h']) < 1000:
            iss.append(f"图片分辨率偏低（{rep['w']}×{rep['h']}），放大后会糊，尽量换原图")
        rep['alpha'] = bool(info.get('alpha')) and real_alpha(path, True)
        if rep['alpha']:
            iss.append('带透明底：用 card 或 contain 叠在画面上')
        return rep
    rep['kind'] = 'video'
    if canvas and info['h'] and ((info['w'] > info['h']) - (info['w'] < info['h']) != (canvas[0] > canvas[1]) - (canvas[0] < canvas[1])):
        iss.append('素材方向和请求画布不同：铺满会裁切，也可用双层构图保留画面')
    if min(info['w'], info['h']) < 1080:
        iss.append(f"分辨率 {info['w']}×{info['h']} 低于 1080P，铺满画布会偏糊")
    if info['fps'] and info['fps'] < 24:
        iss.append(f"帧率只有 {info['fps']:.0f}，画面会卡")
    rep['alpha'] = bool(info.get('alpha')) and real_alpha(path, False)
    if rep['alpha']:
        iss.append('带透明底的动画：用 contain 或 card 叠放，配 aside（人物移出留虚化背景）或 hidden（黑底）版式；'
                   '用 cover 铺满会让透明处直接露出底下的口播画面')
    if role == 'broll':
        return rep
    if info['has_audio']:
        lufs, peak, floor = loudness(path)
        rep.update(lufs=lufs, peak_db=peak, noise_floor_db=floor, silence_ratio=silence_ratio(path, info['duration']))
        if lufs is not None and lufs < -24:
            iss.append(f'声音偏小（{lufs:.0f} LUFS），会统一提升到 -16 LUFS 左右')
        if peak is not None and peak > -0.5:
            iss.append('有爆音（峰值接近 0 dB），爆掉的部分修不回来，严重的话建议补录')
        if floor is not None and floor > -45:
            iss.append(f'底噪偏大（安静处约 {floor:.0f} dB），会做降噪')
        if rep['silence_ratio'] > 0.35:
            iss.append(f"静音和停顿占 {rep['silence_ratio']:.0%}，粗剪后会明显变短")
    else:
        iss.append('没有音轨（B-roll 不需要声音可以忽略；口播素材没声音就要检查）')
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*', help='口播素材')
    ap.add_argument('--broll', nargs='*', default=[], help='B-roll 素材：截图、录屏、动画')
    ap.add_argument('--canvas', type=canvas_size, help='目标 WxH；不指定就跟随源，不提示方向问题')
    ap.add_argument('-o', '--out', default='check.json')
    a = ap.parse_args()
    reps = [check(f, canvas=a.canvas) for f in a.files] + [check(f, 'broll', a.canvas) for f in a.broll]
    save_json(reps, a.out)
    for r in reps:
        dur = f"{r['duration']:.1f}s" if r['kind'] == 'video' else '图片'
        print(f"{r['file']}  {r['w']}x{r['h']}  {dur}")
        for i in r['issues']:
            print('   -', i)


if __name__ == '__main__':
    main()
