#!/usr/bin/env python3
"""起一个剪辑工程：python3 new_edit.py <模板> <工程目录>
  模板：huazi-916（B 网红花字口播，数据驱动）
        reference/launch-169 · reference/tutorial-169 · reference/multihost-169（C / D / E 参考实现，按段重写 Scene）
复制模板 → npm install → 合成音效和占位配乐（make_assets.py）→ 下载默认的 Noto emoji（fetch_noto_emoji.py）。"""
import shutil, subprocess, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if len(sys.argv) < 3: sys.exit(__doc__)
SKILL = Path(__file__).resolve().parent.parent
tpl, dst = sys.argv[1], Path(sys.argv[2]).resolve()
src = SKILL / "templates" / tpl
if not (src / "package.json").exists():
    sys.exit(f"没有模板 {tpl}（可用：huazi-916、reference/launch-169、reference/tutorial-169、reference/multihost-169）")
if (dst / "src").exists(): sys.exit(f"{dst} 里已经有 src/，不覆盖")
shutil.copytree(src, dst, dirs_exist_ok=True)
npm = shutil.which("npm") or sys.exit("没有 npm：先装 Node 18+（python3 doctor.py 看装法）")
subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=dst, check=True)
subprocess.run([sys.executable, str(SKILL / "scripts/make_assets.py"), str(dst / "public")], check=True)
emoji = (SKILL / "templates/emoji.txt").read_text(encoding="utf-8").split()
subprocess.run([sys.executable, str(SKILL / "scripts/fetch_noto_emoji.py"), str(dst), *emoji], check=True, stdout=subprocess.DEVNULL)
if tpl == "huazi-916":
    print(f"✓ {dst} 已就绪。放入 public/main.mp4、public/voice.wav、src/tl.json，改 src/edit.json，然后：\n"
          f"  python3 {SKILL / 'scripts/check_edit.py'} {dst / 'src'}")
else:
    print(f"✓ {dst} 已就绪（参考实现）。换 src 里的时间轴，按本期稿子重写 Scene；素材路径看代码里的 staticFile(…)")
