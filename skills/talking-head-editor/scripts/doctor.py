"""环境自检：开剪之前跑一次，看缺什么、怎么装。

用法：python scripts/doctor.py
必需的缺了会退出码 1；可选的缺了只提示，用到对应功能时再装。
"""
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import fonts
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OK, MISS, OPT = '✓', '✗', '·'


def has_mod(name):
    return importlib.util.find_spec(name) is not None


def ffmpeg_libass():
    try:
        out = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return False
    return ' subtitles ' in out or ' ass ' in out


def main():
    bad = 0
    rows = []

    def need(ok, what, fix):
        nonlocal bad
        bad += not ok
        rows.append((OK if ok else MISS, what, '' if ok else fix))

    def maybe(ok, what, fix):
        rows.append((OK if ok else OPT, what, '' if ok else fix))

    brew = platform.system() == 'Darwin'
    need(sys.version_info >= (3, 10), f'Python 3.10+（现在 {platform.python_version()}）', '装 Python 3.10 或更新的版本')
    need(bool(shutil.which('ffmpeg') and shutil.which('ffprobe')), 'ffmpeg / ffprobe',
         'brew install ffmpeg' if brew else 'apt install ffmpeg，Windows 用 winget install Gyan.FFmpeg')
    if shutil.which('ffmpeg'):
        need(ffmpeg_libass(), 'ffmpeg 带 libass（压字幕要用）', 'brew install ffmpeg-full，或换一个带 libass 的 ffmpeg 版本')
    for mod, pkg in [('PIL', 'pillow'), ('numpy', 'numpy'), ('cv2', 'opencv-python-headless')]:
        need(has_mod(mod), pkg, 'pip install -r requirements.txt')
    need(has_mod('faster_whisper') or has_mod('whisper'), 'faster-whisper（转写）', 'pip install faster-whisper')
    need(not fonts.missing(), 'Skill 用的字体（第一次用时下载，约 80 MB）', 'python scripts/fonts.py fetch')

    maybe(has_mod('jieba'), 'jieba（自动断句更准）', 'pip install jieba')
    maybe(has_mod('pyJianYingDraft'), 'pyJianYingDraft（出剪映草稿）', 'pip install pyJianYingDraft')
    maybe(has_mod('pypinyin'), 'pypinyin（拼音标注手法）', 'pip install pypinyin')
    maybe(bool(shutil.which('uv')), 'uv（抠像、文字识别、配乐节拍分析按需临时装依赖）', 'pip install uv')
    earshot = Path(os.environ.get('KOUBO_EARSHOT_PY') or Path(os.environ.get('KOUBO_HOME', Path.home() / '.cache/koubo')).expanduser()
                   / 'earshot-venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python'))
    maybe(earshot.exists(), 'earshot 音效库（自动配音效；没装会退回 Mixkit 音效）', 'python scripts/setup_earshot.py install')

    w = max(len(r[1]) for r in rows)
    for mark, what, fix in rows:
        print(f'{mark} {what.ljust(w)}  {fix}')
    print()
    print('必需项都齐了，可以开剪。' if not bad else f'缺 {bad} 个必需项，按右边的命令装好再开剪。')
    print('✓ 已就绪  ✗ 必需但缺  · 可选，用到对应功能时再装')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
