#!/usr/bin/env python3
"""Create a promo video project from the Remotion template and install its dependencies. macOS, Linux and Windows.

Usage: python3 setup_project.py <project-dir>      (Windows: python or py -3)

Finds a Node.js 18+ (PROMO_NODE, PATH, nvm, the usual install folders), else downloads a portable one into
~/.cache/promo-video/node. Writes <project>/.promo-env (NODE_BIN, PROMO_VIDEO_SKILL), which render.py and the
examples' tools read.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK copy or emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).resolve().parent.parent
NODE_VERSION = "v22.14.0"
NODE_CACHE = Path.home() / ".cache" / "promo-video" / "node"
WINDOWS = sys.platform == "win32"
NODE_EXE = "node.exe" if WINDOWS else "node"


def node_major(node: Path) -> int:
    try:
        out = subprocess.run([str(node), "-p", "process.versions.node.split('.')[0]"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return int(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def candidate_dirs():
    if os.environ.get("PROMO_NODE"):
        yield Path(os.environ["PROMO_NODE"])
    on_path = shutil.which("node")
    if on_path:
        yield Path(on_path).resolve().parent
    yield NODE_CACHE if WINDOWS else NODE_CACHE / "bin"
    home = Path.home()
    if WINDOWS:
        for root in (os.environ.get("NVM_HOME"), os.environ.get("APPDATA") and Path(os.environ["APPDATA"]) / "nvm"):
            if root and Path(root).is_dir():
                yield from sorted(Path(root).glob("v*"), reverse=True)
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                yield Path(base) / "nodejs"
    else:
        yield from sorted((home / ".nvm" / "versions" / "node").glob("*/bin"), reverse=True)
        yield from (Path("/opt/homebrew/bin"), Path("/usr/local/bin"))


def find_node() -> Path | None:
    for d in candidate_dirs():
        if (d / NODE_EXE).is_file() and node_major(d / NODE_EXE) >= 18:
            return d
    return None


def download_node() -> Path:
    system = {"darwin": "darwin", "win32": "win"}.get(sys.platform, "linux")
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(machine, machine)
    ext = "zip" if WINDOWS else "tar.gz"
    pkg = f"node-{NODE_VERSION}-{system}-{arch}"
    url = f"https://nodejs.org/dist/{NODE_VERSION}/{pkg}.{ext}"
    print(f"Node.js 18+ not found; downloading portable {pkg} to {NODE_CACHE}", file=sys.stderr)
    NODE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=NODE_CACHE.parent) as tmp:
        archive = Path(tmp) / f"node.{ext}"
        with urllib.request.urlopen(url, timeout=120) as response, open(archive, "wb") as f:
            shutil.copyfileobj(response, f)
        if WINDOWS:
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)
        else:
            with tarfile.open(archive) as t:
                t.extractall(tmp, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        if NODE_CACHE.exists():
            shutil.rmtree(NODE_CACHE)
        shutil.move(str(Path(tmp) / pkg), str(NODE_CACHE))
    return NODE_CACHE if WINDOWS else NODE_CACHE / "bin"


def cached_headless_shell(project: Path) -> Path | None:
    """A chrome-headless-shell another project already downloaded (Remotion keeps one per project), within 7 levels of home."""
    home = Path.home()
    tail = ("node_modules", ".remotion", "chrome-headless-shell")
    for root, dirs, _ in os.walk(home):
        here = Path(root)
        depth = len(here.relative_to(home).parts)
        if here.parts[-3:] == tail:
            if project not in here.parents:
                return here
            dirs[:] = []
            continue
        if depth >= 7:
            dirs[:] = []
            continue
        if here.name == "node_modules":
            dirs[:] = [d for d in dirs if d == ".remotion"]
        elif here.name == ".remotion":
            dirs[:] = [d for d in dirs if d == "chrome-headless-shell"]
        else:  # skip hidden folders and the OS's own big trees
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("Library", "AppData", "Applications")]
    return None


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: setup_project.py <project-dir>")
    target = Path(sys.argv[1]).resolve()

    node_bin = find_node() or download_node()
    os.environ["PATH"] = str(node_bin) + os.pathsep + os.environ.get("PATH", "")
    version = subprocess.run([str(node_bin / NODE_EXE), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    print(f"Using node {version} from {node_bin}")

    if (target / "package.json").exists():
        print(f"Project already exists at {target}; installing deps only.")
    else:
        shutil.copytree(SKILL_DIR / "templates" / "remotion", target, dirs_exist_ok=True)
        for sub in ("public/music", "public/brand", "public/images", "out"):
            (target / sub).mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_DIR / "assets" / "sfx", target / "public" / "sfx", dirs_exist_ok=True)
        (target / "public" / "sfx" / "preview.wav").unlink(missing_ok=True)

    # Plain KEY=value lines, no shell quoting: read the same way on every OS.
    (target / ".promo-env").write_text(f"NODE_BIN={node_bin}\nPROMO_VIDEO_SKILL={SKILL_DIR}\n", encoding="utf-8")

    npm = shutil.which("npm.cmd" if WINDOWS else "npm", path=os.environ["PATH"])  # by full path, so the .cmd runs without a shell
    if not npm:
        sys.exit(f"npm not found next to node in {node_bin}")
    subprocess.run([npm, "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=target, check=True)

    shell_dir = target / "node_modules" / ".remotion" / "chrome-headless-shell"
    if not shell_dir.is_dir():
        cached = cached_headless_shell(target)
        if cached:
            shutil.copytree(cached, shell_dir)
            print(f"Reused headless browser from {cached}")
        else:
            print("Remotion will download its headless browser on first render.")

    # rn (renoise-kit) finishes, checks and audits every render; it drives a system ffmpeg built with libass.
    if not shutil.which("rn"):
        print('WARNING: rn not found. Install renoise-kit before rendering: uv tool install "renoise-kit[all]"', file=sys.stderr)
    if not shutil.which("ffmpeg"):
        hint = {"darwin": 'brew install ffmpeg-full && export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"',
                "win32": "winget install Gyan.FFmpeg (then open a new terminal)"}.get(sys.platform, "apt install ffmpeg")
        print(f"WARNING: ffmpeg not on PATH. {hint}", file=sys.stderr)

    print(f"Ready: {target}")


if __name__ == "__main__":
    main()
