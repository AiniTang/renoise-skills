"""成片截图拼图：按固定间隔或指定时间点截帧，带时间标签拼成一张图，用来检查排版和节奏。

用法：
  python contact_sheet.py out/final.mp4                     # 每 2 秒一帧
  python contact_sheet.py out/final.mp4 --every 1 --cols 6
  python contact_sheet.py out/final.mp4 --at 3.2 8.5 12     # 指定时间点
输出默认写到当前目录的 视频名_sheet.jpg（多页时 _sheet2.jpg ...），不会往素材所在目录写文件。
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from kvlib import probe, find_font


def grab(video, t, out, width):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', video, '-frames:v', '1', '-vf', f'scale={width}:-2', out], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--every', type=float, default=2.0)
    ap.add_argument('--at', type=float, nargs='*')
    ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--rows', type=int, default=3)
    ap.add_argument('--width', type=int, default=270)
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    dur = probe(a.video)['duration']
    times = a.at if a.at else [round(x * a.every, 2) for x in range(int(dur / a.every) + 1) if x * a.every < dur - 0.05]
    tmp = Path(tempfile.mkdtemp())
    frames = []
    for i, t in enumerate(times):
        p = tmp / f'{i:04d}.jpg'
        grab(a.video, t, str(p), a.width)
        frames.append((t, p))
    try:
        font = ImageFont.truetype(find_font()[0], 20)
    except SystemExit:
        font = ImageFont.load_default()
    per = a.cols * a.rows
    base = a.out or Path(a.video).stem + '_sheet.jpg'
    outs = []
    for page in range(0, len(frames), per):
        chunk = frames[page:page + per]
        w, h = Image.open(chunk[0][1]).size
        rows = (len(chunk) + a.cols - 1) // a.cols
        sheet = Image.new('RGB', (w * a.cols, h * rows), 'black')
        for k, (t, p) in enumerate(chunk):
            im = Image.open(p)
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 76, 26], fill='black')
            d.text((5, 2), f'{t:.1f}s', fill='yellow', font=font)
            sheet.paste(im, ((k % a.cols) * w, (k // a.cols) * h))
        out = base if page == 0 else base.replace('_sheet.jpg', f'_sheet{page // per + 1}.jpg')
        sheet.save(out, quality=85)
        outs.append(out)
    print('\n'.join(outs))


if __name__ == '__main__':
    main()
