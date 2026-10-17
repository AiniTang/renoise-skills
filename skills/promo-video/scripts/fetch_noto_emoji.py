#!/usr/bin/env python3
"""下载 Google Noto 动态 emoji（Lottie）到 Remotion 工程，供 <NotoEmoji char="🚀" /> 使用。
用法: fetch_noto_emoji.py <项目目录> 🚀 🎯 ✅ ...      （也可传一个字符串："🚀🎯✅"）
      fetch_noto_emoji.py <项目目录> --list [关键词]   列出可用的动态 emoji
- 有动态版：public/emoji/<codepoint>.json（Lottie，1024 矢量，60fps）
- 没有动态版：退回 Noto 静态 SVG（Apache 2.0）public/emoji/<codepoint>.svg，并提示
- 写 public/emoji/manifest.json：{ "🚀": {"cp": "1f680", "kind": "lottie"} }
授权：动态版来自 googlefonts.github.io/noto-emoji-animation，片尾/声明里加一行
「Animated emoji: Google Noto」；静态 SVG 为 Apache 2.0。
"""
import json, pathlib, sys, urllib.request, ssl, subprocess

API = "https://googlefonts.github.io/noto-emoji-animation/data/api.json"
LOTTIE = "https://fonts.gstatic.com/s/e/notoemoji/latest/{cp}/lottie.json"
SVG = "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/2D/svg/emoji_u{cp}.svg"
CACHE = pathlib.Path.home() / ".cache/promo-video/noto-emoji-api.json"

def get(url):
    # 本机 Python 走代理偶发 SSL EOF：失败时退回 curl
    try:
        with urllib.request.urlopen(url, timeout=30, context=ssl.create_default_context()) as r:
            return r.read()
    except Exception:
        return subprocess.run(["curl", "-sfL", "--max-time", "60", url], capture_output=True, check=True).stdout

def api():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_bytes(get(API))
    return json.loads(CACHE.read_text())

def split_emoji(s):
    """把字符串拆成 emoji（按 ZWJ / 变体选择符 / 肤色 / 国旗粘连）。"""
    out, cur = [], ""
    chars = list(s)
    i = 0
    while i < len(chars):
        c = chars[i]; o = ord(c)
        if c.isspace():
            if cur: out.append(cur); cur = ""
            i += 1; continue
        joiner = cur and (o in (0x200D, 0xFE0F, 0x20E3) or 0x1F3FB <= o <= 0x1F3FF or cur[-1] == "‍"
                          or (0x1F1E6 <= o <= 0x1F1FF and len(cur) == 1 and 0x1F1E6 <= ord(cur[0]) <= 0x1F1FF))
        if joiner: cur += c
        else:
            if cur: out.append(cur)
            cur = c
        i += 1
    if cur: out.append(cur)
    return out

def cp_of(e, keep_vs=False):
    return "_".join(f"{ord(c):x}" for c in e if keep_vs or ord(c) != 0xFE0F)

def main():
    proj = pathlib.Path(sys.argv[1]); args = sys.argv[2:]
    data = api(); icons = {i["codepoint"]: i for i in data["icons"]}
    if args and args[0] == "--list":
        kw = args[1].lower() if len(args) > 1 else ""
        for cp, i in icons.items():
            ch = "".join(chr(int(x, 16)) for x in cp.split("_"))
            if kw in (i["name"] + " ".join(i["tags"]) + " ".join(i["categories"])).lower():
                print(ch, cp, " ".join(i["tags"]), "|", i["categories"][0])
        return
    out = proj / "public/emoji"; out.mkdir(parents=True, exist_ok=True)
    mf_path = out / "manifest.json"
    mf = json.loads(mf_path.read_text()) if mf_path.exists() else {}
    for e in [x for a in args for x in split_emoji(a)]:
        cp = cp_of(e)  # 静态 SVG 文件名去掉 FE0F；动态版的 codepoint 保留 FE0F（如 2764_fe0f）
        acp = next((c for c in (cp_of(e, True), cp) if c in icons), None)
        if acp:
            (out / f"{cp}.json").write_bytes(get(LOTTIE.format(cp=acp)))
            mf[e] = {"cp": cp, "kind": "lottie"}; print(f"{e} {cp} 动态 ✓")
        else:
            try:
                (out / f"{cp}.svg").write_bytes(get(SVG.format(cp=cp)))
                mf[e] = {"cp": cp, "kind": "svg"}; print(f"{e} {cp} 无动态版 → 静态 SVG")
            except Exception:
                print(f"{e} {cp} ✗ Noto 里找不到")
    mf_path.write_text(json.dumps(mf, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
