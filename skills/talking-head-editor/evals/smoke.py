"""不花钱的端到端冒烟：合成一段口播素材 → 时间线骨架 → 手法库自动搭配 → 渲染成片，竖屏和横屏各一条。

用法：python evals/smoke.py <工作目录> [--canvas 1080x1920|1920x1080]
不需要真人素材和语音识别：素材是 FFmpeg 合成的画面加正弦波，逐字时间按字数摊开。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
LINES = ['剪口播最累的是什么', '第一步把气口剪掉', '第二步给重点加大字', '三个步骤十分钟搞定']


def run(name, *args, cwd=None):
    subprocess.run([sys.executable, str(SCRIPTS / (name + '.py')), *map(str, args)], check=True, cwd=cwd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--canvas', default='1080x1920')
    a = ap.parse_args()
    w, h = map(int, a.canvas.split('x'))
    proj = Path(a.work).resolve()
    proj.mkdir(parents=True, exist_ok=True)
    per = 2.0
    dur = per * len(LINES)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=s={w // 2}x{h // 2}:r=30:d={dur}',
                    '-f', 'lavfi', '-i', f'sine=frequency=220:duration={dur}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', str(proj / 'aroll.mp4')], check=True)
    lines = []
    for i, text in enumerate(LINES):
        t0, t1 = i * per + 0.1, (i + 1) * per - 0.2
        step = (t1 - t0) / len(text)
        lines.append({'i': i, 'text': text, 't0': t0, 't1': t1,
                      'chars': [[c, round(t0 + k * step, 3)] for k, c in enumerate(text)]})
    (proj / 'lines.json').write_text(json.dumps(lines, ensure_ascii=False), encoding='utf-8')

    run('init_timeline', proj, '--style', 'premium', '--canvas', a.canvas)
    tl_path = proj / 'timeline.json'
    tl = json.loads(tl_path.read_text(encoding='utf-8'))
    tl['beats'] = [
        {'t0': 0.1, 't1': 1.8, 'beat': 'hook', 'text': '剪口播'},
        {'t0': 2.1, 't1': 3.8, 'beat': 'list', 'items': ['剪气口', '加大字', '配音效']},
        {'t0': 4.1, 't1': 5.8, 'beat': 'emphasis', 'text': '大字'},
        {'t0': 6.1, 't1': 7.8, 'beat': 'number', 'text': '10 分钟'},
    ]
    tl_path.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')

    run('library', 'arrange', tl_path)
    out = proj / 'out' / 'final.mp4'
    run('render', tl_path, '-o', out, '--preview', cwd=proj)
    info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height:format=duration',
                                      '-of', 'json', str(out)], capture_output=True, text=True, check=True).stdout)
    vw, vh = info['streams'][0]['width'], info['streams'][0]['height']
    length = float(info['format']['duration'])
    assert (vw > vh) == (w > h), f'画幅方向不对：{vw}x{vh}'
    assert abs(length - dur) < 1.5, f'时长不对：{length:.2f}s'
    print(f'✓ {out}  {vw}x{vh}  {length:.1f}s')


if __name__ == '__main__':
    main()
