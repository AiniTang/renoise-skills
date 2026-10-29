"""打码：把图片或视频里指定区域做模糊、马赛克或纯色遮挡，输出新文件（原文件不动）。

用法一：按检测结果打码（只打用户同意的那几处）
  python mask.py --from sensitive.json --ids 0 2 5 [--mode pixelate] [--pad 0.3] [--outdir masked/]
用法二：手动指定区域
  python mask.py 素材.mov --box 0.1 0.62 0.5 0.05 [--t0 3 --t1 8] [--mode blur] -o 素材_masked.mov
box 是 [x, y, 宽, 高]，都是相对画面宽高的比例（0~1）。

mode：pixelate 马赛克（默认，最常见也最「看得出是故意打码」）、blur 高斯模糊（更柔和）、solid 纯色色块（最彻底）。
滚动的录屏内容会移动，检测是按帧抽样的，--pad 默认把框往四周扩 30%，必要时再加大或改用整行遮挡。
打码后把 timeline.json 里对应素材的 src 换成新文件。
"""
import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from kvlib import probe, is_image, to_png


def expand(box, pad):
    x, y, w, h = box
    dx, dy = w * pad / 2, max(h * pad / 2, 0.004)
    x0, y0 = max(0.0, x - dx), max(0.0, y - dy)
    x1, y1 = min(1.0, x + w + dx), min(1.0, y + h + dy)
    return [x0, y0, x1 - x0, y1 - y0]


def mask_image(src, regions, out, mode):
    from PIL import Image, ImageFilter
    im = Image.open(to_png(src, str(Path(out).parent))).convert('RGB')
    W, H = im.size
    for r in regions:
        x, y, w, h = r['box']
        b = (int(x * W), int(y * H), int((x + w) * W) + 1, int((y + h) * H) + 1)
        part = im.crop(b)
        if mode == 'blur':
            part = part.filter(ImageFilter.GaussianBlur(max(6, part.height / 3)))
        elif mode == 'solid':
            part = Image.new('RGB', part.size, (30, 30, 30))
        else:
            cell = max(6, part.height // 3)
            part = part.resize((max(1, part.width // cell), max(1, part.height // cell)), Image.BILINEAR).resize(part.size, Image.NEAREST)
        im.paste(part, b[:2])
    im.save(out)


def mask_video(src, regions, out, mode):
    info = probe(src)
    W, H = info['w'], info['h']
    fc, cur = [], '[0:v]'
    for i, r in enumerate(regions):
        x, y, w, h = r['box']
        cw, ch = max(2, int(w * W) // 2 * 2), max(2, int(h * H) // 2 * 2)
        cx, cy = int(x * W), int(y * H)
        en = f":enable='between(t,{r['t0']},{r['t1']})'" if r.get('t0') is not None else ''
        fc.append(f"{cur}split=2[m{i}][c{i}]")
        if mode == 'blur':
            proc = f"boxblur={max(4, ch // 3)}:3"
        elif mode == 'solid':
            proc = "drawbox=c=0x1E1E1E:t=fill"
        else:
            cell = max(6, ch // 3)
            proc = f"scale=max(1\\,iw/{cell}):max(1\\,ih/{cell}):flags=bilinear,scale={cw}:{ch}:flags=neighbor"
        fc.append(f"[c{i}]crop={cw}:{ch}:{cx}:{cy},{proc}[p{i}]")
        fc.append(f"[m{i}][p{i}]overlay={cx}:{cy}{en}[o{i}]")
        cur = f'[o{i}]'
    fc.append(f"{cur}null[v]")
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '0:a?', '-c:a', 'copy',
           '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', out]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', nargs='?')
    ap.add_argument('--from', dest='from_json')
    ap.add_argument('--ids', type=int, nargs='*')
    ap.add_argument('--box', type=float, nargs=4)
    ap.add_argument('--t0', type=float)
    ap.add_argument('--t1', type=float)
    ap.add_argument('--mode', default='pixelate', choices=['pixelate', 'blur', 'solid'])
    ap.add_argument('--pad', type=float, default=0.3)
    ap.add_argument('-o', '--out')
    ap.add_argument('--outdir', default='masked')
    a = ap.parse_args()

    jobs = defaultdict(list)
    if a.from_json:
        items = json.load(open(a.from_json, encoding='utf-8'))
        for it in items:
            if a.ids is not None and it['id'] not in a.ids:
                continue
            if not it.get('box'):
                print(f"[{it['id']}] {it['kind']} 在口播声音里，不能打码画面：建议剪掉这句或用「哔」声盖住")
                continue
            jobs[it['file']].append({'box': expand(it['box'], a.pad), 't0': it.get('t0'), 't1': it.get('t1')})
    elif a.src and a.box:
        jobs[a.src].append({'box': expand(a.box, a.pad), 't0': a.t0, 't1': a.t1})
    else:
        raise SystemExit('用 --from sensitive.json --ids ...，或者给出素材路径加 --box')

    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    for src, regs in jobs.items():
        p = Path(src)
        if a.out and len(jobs) == 1:
            out = a.out
        else:
            ext = '.png' if is_image(src) else '.mp4'
            out = str(Path(a.outdir) / f'{p.stem}_masked{ext}')
        if is_image(src):
            mask_image(src, regs, out, a.mode)
        else:
            mask_video(src, regs, out, a.mode)
        print(f'{p.name}：打码 {len(regs)} 处 → {out}')


if __name__ == '__main__':
    main()
