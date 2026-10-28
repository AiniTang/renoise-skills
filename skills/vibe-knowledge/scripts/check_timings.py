#!/usr/bin/env python3
"""配音后检查逐字时间有没有「断」：一长串字挤在同一时刻 = 对齐从那里失败了（常见原因：英文名带连字符、旁白和读音差太多、念漏了）。
用法：python3 check_timings.py <期号或期目录> [--ws 工作区]"""
import json
import sys

from vk import lesson_dir

if len(sys.argv) < 2:
    sys.exit(__doc__)
t = json.loads((lesson_dir(sys.argv[1]) / "build" / "timings.json").read_text(encoding="utf-8"))
bad = 0
for b, bt in t["beats"].items():
    ch, txt, run = bt["chars"], bt["text"], 0
    for i in range(1, len(ch)):
        run = run + 1 if abs(ch[i] - ch[i - 1]) < 1e-6 and txt[i].strip() else 0
        if run == 8:
            bad += 1
            print(f"{b}：从「{txt[i - 8:i + 8]}」开始对齐断了（卡在 {ch[i]:.2f}s，这一拍结束 {bt['end']:.2f}s）")
            break
    late = [k for k, v in bt.get("cues", {}).items() if v >= bt["end"] - 0.02]
    if late:
        print(f"{b}：这些 cue 落在拍尾，多半是对齐断了：{late}")
print("没有发现问题" if not bad else f"{bad} 拍有问题：改旁白写法（或 lexicon 写读音）后重新配这几拍")
