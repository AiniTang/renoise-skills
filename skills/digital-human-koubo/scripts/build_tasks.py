#!/usr/bin/env python3
"""口播稿 → Grok 分段任务（create_tasks 的 tasks 数组）。

用法：
  python3 build_tasks.py script.json out_tasks.json [--brief brief.json] [--purpose "teaching a beginner tutorial step by step"] [--all-720p]

script.json：[{"id": "s1", "shot": "full|pip|vlog|depth", "t": "这一段要念的台词", "host": "a", "lang": "Mandarin Chinese|English|Japanese|…"}, ...]
brief.json 的 hosts：{"a": {"ref": "material:123", "who": "young woman", "framing": "selfie|studio", "ratio": "9:16", "voice": "young friendly female voice, clear and lively"}}
- host：不写就用 hosts 里的第一位
- lang：不写就是普通话；外语段台词直接写目标语言
- 每段时长 = ceil(字数 / 5.4 + 1.0)，夹在 4–15 秒（Grok 单段上限 15 秒；5.4 字/秒是实测语速）
- full 段 720p，pip 段 480p（画中画里看不出差别，便宜四成）；--all-720p 全部 720p
- 超过 15 秒的段会报错：先把台词拆短再跑
输出的数组先交给 estimate_cost 报价（它返回的 task 就是 create_tasks 要提交的），用户在对话里确认后每 10 个一批 create_tasks。
"""
import json, math, re, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent.parent
P = json.loads((HERE / "persona.json").read_text(encoding="utf-8"))

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    purpose = arg("--purpose", "explaining clearly")
    all720 = "--all-720p" in sys.argv
    hosts = json.loads(Path(arg("--brief", "brief.json")).read_text(encoding="utf-8")).get("hosts") or {}
    if not hosts: sys.exit("brief.json 里没有 hosts：先按 references/new-avatar.md 登记主播")
    S = json.loads(Path(src).read_text(encoding="utf-8"))
    tasks, by_res = [], {}
    for s in S:
        lang = s.get("lang", "Mandarin Chinese")
        if lang.startswith("Mandarin") or lang == "Chinese":
            d = math.ceil(len(re.sub(r"[\s，。、：；！？,.:;!?“”]", "", s["t"])) / P["speed_cps"] + 1.0)
        elif re.search(r"[぀-ヿ가-힯]", s["t"]):     # 日文 / 韩文：约 7 字/秒
            d = math.ceil(len(re.sub(r"\s", "", s["t"])) / 7 + 1.0)
        else:                                                    # 拉丁 / 阿拉伯等按词：约 2.6 词/秒
            d = math.ceil(len(s["t"].split()) / 2.6 + 1.0)
        if d > P["model"]["max_seconds"]:
            sys.exit(f"{s['id']} 约 {d} 秒，超过 {P['model']['max_seconds']} 秒：拆成两段再跑")
        d = max(4, d)
        shot = s.get("shot", "full")
        res = P["model"]["full_shot_resolution"] if (all720 or shot != "pip") else P["model"]["pip_shot_resolution"]
        by_res[res] = by_res.get(res, 0) + d
        hid = s.get("host") or next(iter(hosts))
        if hid not in hosts: sys.exit(f"{s['id']} 的 host「{hid}」不在 brief.json 的 hosts 里")
        H = hosts[hid]
        prompt = P["prompt_templates"][H.get("framing", "selfie")].format(
            who=H.get("who", "person"), ref="@" + H["ref"], purpose=purpose, act=P["acts"].get(shot, P["acts"]["full"]),
            language=lang, voice=H.get("voice", "natural, friendly voice"), line=s["t"])
        tasks.append({"model": P["model"]["name"], "kind": "video", "ratio": H.get("ratio", "9:16"), "resolution": res, "duration": d,
                      "label": f"口播 {s['id']}", "idempotencyKey": f"dh-{Path(src).stem}-{s['id']}-v1",
                      "references": [{"ref": H["ref"], "role": "reference_image"}], "prompt": prompt})
    Path(dst).write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    secs = " + ".join(f"{res} {n} 秒" for res, n in by_res.items())
    print(f"{len(tasks)} 段 · {secs} · 分 {math.ceil(len(tasks) / 10)} 批提交 → 先用 estimate_cost 报价")

if __name__ == "__main__":
    main()
