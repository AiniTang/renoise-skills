"""scripts/ 共用：skill 目录、工作区、UTF-8 输出。

工作区（一个目录放所有期）：命令行 --ws，否则环境变量 VK_WS，否则 ~/vibe-knowledge。
  <ws>/cine/        代码成片引擎（new_film.py 从 skill 的 engine/ 拷过来，字体在 cine/fonts/）
  <ws>/lessons/<期号>/  每一期：narration.json、film.js、facts.md、assets.json、assets/、build/
  <ws>/vk.json      工作区设置（默认 BGM、配音引擎），见 references/08-tiers.md"""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL = Path(__file__).resolve().parent.parent
CACHE = Path.home() / ".cache/vibe-knowledge"


def workspace(argv=None):
    argv = sys.argv if argv is None else argv
    if "--ws" in argv:
        return Path(argv[argv.index("--ws") + 1]).expanduser().resolve()
    return Path(os.environ.get("VK_WS") or Path.home() / "vibe-knowledge").expanduser().resolve()


def lesson_dir(ref, argv=None):
    """期号（如 05）或期目录路径都行。"""
    p = Path(ref).expanduser()
    if p.is_dir() and (p / "narration.json").exists():
        return p.resolve()
    return workspace(argv) / "lessons" / str(ref)


def arg(name, default=None, argv=None):
    argv = sys.argv if argv is None else argv
    return argv[argv.index(name) + 1] if name in argv else default
