"""安装 earshot（github.com/Leonxlnx/earshot，MIT）到独立环境，给口播自动配音效用。只需一次，macOS、Linux、Windows 都能跑。
  python scripts/setup_earshot.py install
装好后 kvlib.all_sfx 会自动用它；没装就退回 Mixkit 音效库。环境变量 KOUBO_EARSHOT_PY 可以指定已有的 earshot 环境，
KOUBO_HOME 可以换安装目录（默认 ~/.cache/koubo）。"""
import os
import subprocess
import sys
import venv
from pathlib import Path

REPO = 'https://github.com/Leonxlnx/earshot'
COMMIT = '591fa3e028032e6dce56620a20e932e35667e8d8'
HOME = Path(os.environ.get('KOUBO_HOME', Path.home() / '.cache/koubo')).expanduser()
VENV = HOME / 'earshot-venv'


def venv_python(root=VENV):
    return root / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def install():
    if os.environ.get('KOUBO_EARSHOT_PY'):
        print(f"用 KOUBO_EARSHOT_PY={os.environ['KOUBO_EARSHOT_PY']}，不另装")
        return
    HOME.mkdir(parents=True, exist_ok=True)
    src = HOME / 'earshot'
    if not (src / '.git').exists():
        subprocess.run(['git', 'clone', '--filter=blob:none', REPO, str(src)], check=True)
    subprocess.run(['git', '-C', str(src), 'fetch', '-q', 'origin', COMMIT], check=False)
    subprocess.run(['git', '-C', str(src), 'checkout', '-q', COMMIT], check=True)
    py = venv_python()
    if not py.exists():
        venv.create(VENV, with_pip=True)
    subprocess.run([str(py), '-m', 'ensurepip', '-q'], capture_output=True)   # 老版本用 uv 建的环境没有 pip
    subprocess.run([str(py), '-m', 'pip', 'install', '-q', 'numpy', 'scipy', 'numba', 'soundfile', 'pyloudnorm'], check=True)
    subprocess.run([str(py), '-m', 'pip', 'install', '-q', '--no-deps', '-e', str(src)], check=True)
    r = subprocess.run([str(py), '-c', "from earshot.forge import bank, kit; y, m = bank.render('cut_hit/punch', sr=48000); print(len(y))"],
                       capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': ''})
    if r.returncode:
        sys.exit('earshot 装好了但渲染测试失败：\n' + r.stderr[-800:])
    print(f'✓ earshot {COMMIT[:7]} 已装好：{py}')


if __name__ == '__main__':
    if sys.argv[1:] != ['install']:
        sys.exit(__doc__)
    install()
