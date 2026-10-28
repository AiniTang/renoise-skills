#!/usr/bin/env python3
"""下载引擎用的字体（assets/fonts.json：固定版本的 URL + sha256，全部 SIL OFL 1.1），拷进工作区。
  python3 fonts.py fetch [--ws 工作区] [--no-optional]
先下到 ~/.cache/vibe-knowledge/fonts/（下过且校验通过就不再下），再拷进 <ws>/cine/fonts/，协议原文一并拷过去。
--no-optional：不下宋体 / 楷体后备（Noto Serif SC、霞鹜文楷，各约 25 MB；macOS 自带宋体楷体，可以不下）。
new_film.py 建工作区时会调用它。"""
import hashlib
import json
import shutil
import sys
import urllib.request

from vk import CACHE, SKILL, workspace


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def get(item, dst_dir):
    dst = dst_dir / item["file"]
    if dst.exists() and sha(dst) == item["sha256"]:
        return dst
    tmp = dst.with_suffix(dst.suffix + ".part")
    print(f"  下载 {item['file']}（{item.get('bytes', 0) / 1e6:.1f} MB）…", flush=True)
    req = urllib.request.Request(item["url"], headers={"User-Agent": "vibe-knowledge"})
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    if sha(tmp) != item["sha256"]:
        tmp.unlink()
        sys.exit(f"{item['file']} 校验不对（sha256），没有用它：{item['url']}")
    tmp.replace(dst)
    return dst


def fetch(ws, optional=True):
    cat = json.loads((SKILL / "assets/fonts.json").read_text(encoding="utf-8"))
    cache = CACHE / "fonts"
    cache.mkdir(parents=True, exist_ok=True)
    out = ws / "cine/fonts"
    out.mkdir(parents=True, exist_ok=True)
    want = [f for f in cat["fonts"] if optional or not f.get("optional")]
    lic = {f["license"] for f in want}
    for item in want + [x for x in cat["licenses"] if x["file"] in lic]:
        src = get(item, cache)
        dst = out / item["file"]
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copy(src, dst)
    faces = {"NotoSerifSC-VF.ttf": 'font-family: "NotoSerifSC"; font-weight: 200 900;', "LXGWWenKai-Regular.ttf": 'font-family: "LXGWWenKai";'}
    css = "".join(f"@font-face {{ {rule} src: url({name}); }}\n" for name, rule in faces.items() if (out / name).exists())
    (out / "fonts.css").write_text("/* scripts/fonts.py 生成：只登记已下载的宋体 / 楷体后备 */\n" + css, encoding="utf-8")
    print(f"✓ 字体 {len(want)} 个 → {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "fetch":
        sys.exit(__doc__)
    fetch(workspace(), "--no-optional" not in sys.argv)
