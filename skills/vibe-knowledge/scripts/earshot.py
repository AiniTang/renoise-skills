#!/usr/bin/env python3
"""earshot 代码音效（github.com/Leonxlnx/earshot，MIT，252 个音效以「配方代码」存放，按编号渲染，不联网、不花积分）。
  python3 earshot.py install     装到 ~/.cache/vibe-knowledge/earshot/（独立的虚拟环境，固定版本；只装音效库要的 numpy / scipy / numba / soundfile）
  python3 earshot.py list        列出全部音效编号
装好后 film.js 的 music 条目写 src: "earshot:<类别>/<成员>"，render.py film 的 finish 步骤会自动渲染（写法见 references/10-earshot.md）。
EARSHOT_PY 环境变量可以指定已有的 earshot 环境。"""
import os
import subprocess
import sys
import venv

from vk import CACHE

REPO = "https://github.com/Leonxlnx/earshot"
COMMIT = "591fa3e028032e6dce56620a20e932e35667e8d8"
HOME = CACHE / "earshot"
PY = HOME / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def install():
    if os.environ.get("EARSHOT_PY"):
        print(f"用 EARSHOT_PY={os.environ['EARSHOT_PY']}，不另装"); return
    HOME.mkdir(parents=True, exist_ok=True)
    src = HOME / "src"
    if not (src / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", REPO, str(src)], check=True)
    subprocess.run(["git", "-C", str(src), "checkout", "-q", COMMIT], check=True)
    if not PY.exists():
        venv.create(HOME / ".venv", with_pip=True)
    subprocess.run([str(PY), "-m", "pip", "install", "-q", "numpy", "scipy", "numba", "soundfile", "pyloudnorm"], check=True)
    subprocess.run([str(PY), "-m", "pip", "install", "-q", "--no-deps", "-e", str(src)], check=True)
    r = subprocess.run([str(PY), "-c", "from earshot.forge import bank; y, m = bank.render('cut_hit/punch', sr=48000); print(len(y))"],
                       capture_output=True, text=True, env={**os.environ, "PYTHONPATH": ""})
    if r.returncode:
        sys.exit("earshot 装好了但渲染测试失败：\n" + r.stderr[-800:])
    print(f"✓ earshot {COMMIT[:7]} → {HOME}（测试音效渲染 {r.stdout.strip()} 个采样）")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "list"):
        sys.exit(__doc__)
    if sys.argv[1] == "install":
        install()
    else:
        py = os.environ.get("EARSHOT_PY") or str(PY)
        subprocess.run([py, "-m", "earshot", "sfx", "list"], check=True, env={**os.environ, "PYTHONPATH": ""})
