#!/usr/bin/env python3
"""配音：Renoise 语音模型（默认）或小米 MiMo（可选，用户自己的密钥）→ faster-whisper 逐字对齐 → 每拍的音频 + timings.json。
规则和提示词写法见 references/15-voice.md。

Renoise（默认，narration.json 的 voice.engine = "renoise"）：
  python3 voice.py plan <期号>                       按拍切成几条 take（每条 ≤ 100 秒，切在拍与拍之间），写 build/voice_plan.json，
                                                     打印每条的提示词和建议时长。报价、确认、create_tasks 由 agent 按 SKILL.md 做。
  python3 voice.py align <期号> <take1> [<take2> …]  下好的 take（按 plan 的顺序，任何音频格式）→ 逐字对齐 → 切出每拍 →
                                                     build/audio/<拍>.wav、build/narration.wav、build/timings.json，并打印每拍的对齐率和听写稿。
MiMo（可选，voice.engine = "mimo"；密钥只从环境变量 MIMO_API_KEY / MIMO_BASE_URL 读，不写进任何文件）：
  python3 voice.py mimo <期号> [--jobs 2]            每拍整段合成（voice.ref 填本地参照 wav 时走克隆）→ 同样的对齐和输出。
共用参数：--gap 0.2（拍间停顿秒）--lead 0.3（片头留白）--model small（faster-whisper 模型，回读不稳时用 medium）
时间写法：timings.json 每拍有 start / end / text（去掉 [[cue]] 后的旁白）/ chars（每个字的开始秒）/ words / cues（[[cue]] 的秒）。"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from vk import arg, lesson_dir

CUE_RE = re.compile(r"\[\[([a-z][a-z0-9_-]*)\]\]")
PUNCT = set("，。！？；：、,.!?;:（）()「」『』“”\"'《》…—- 　")
SR = 16000
TAKE_MAX = 100.0          # 一条 take 的目标上限（秒）；语音模型单条最长约 120 秒，留余量
CN_NUM = str.maketrans("零〇一二三四五六七八九", "00123456789")


# ── 文本 ──
def strip_cues(text):
    out, cues, pos = [], {}, 0
    for m in CUE_RE.finditer(text):
        out.append(text[pos:m.start()])
        cues[m.group(1)] = sum(len(p) for p in out)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), cues


ROMANISH = re.compile(r"(?<![A-Za-z])[IVXLCDM]{2,4}(?![A-Za-z])")   # CLI、MD 这类缩写容易被念成罗马数字：拆成单个字母


def say_text(clean, lexicon, lang):
    for k in sorted(lexicon or {}, key=len, reverse=True):
        clean = clean.replace(k, lexicon[k])
    return clean if lang == "en" else ROMANISH.sub(lambda m: " ".join(m.group(0)), clean)


def load(L):
    d = json.loads((L / "narration.json").read_text(encoding="utf-8"))
    v = d.get("voice", {})
    lang = v.get("lang", "zh")
    beats = []
    for b in d["beats"]:
        clean, cues = strip_cues(b["narration"])
        if clean.startswith("（待写）"):
            sys.exit(f"{b['id']} 还是骨架（待写），先写完旁白")
        beats.append({"id": b["id"], "clean": clean, "cues": cues, "say": say_text(clean, d.get("lexicon"), lang),
                      "gap": max(b.get("gap", 0), b.get("min_hold_s", 0))})
    return d, v, lang, beats


def est_seconds(text, lang, cps):
    n = len(re.findall(r"[A-Za-z]+", text)) if lang == "en" else len([c for c in text if c not in PUNCT and not c.isspace()])
    return n / (2.6 if lang == "en" else cps)


# ── plan：Renoise 提示词 ──
PROMPT = """This is a short-video knowledge voiceover, not a reading, not an announcement, not a dubbing script.
The speaker: {speaker}
Delivery: {style}

Most important:
1. Pace: about {cps} characters per second, one sentence flowing into the next. Very short pauses between sentences (about 0.2 s), about 0.4 s between paragraphs. Do not stop at every comma, do not drag syllables.
2. Conversational: natural stress and linking, like explaining something fascinating to a friend. No announcer voice, no recital, no advert voice.
3. Numbers, names and key words land with a little weight; questions are crisp.
{pron}
Audio: clean voice only, no music, no sound effects, no reverb. Total length within {cap} seconds.
Say the paragraphs below word for word, in {lang_name}, adding and dropping nothing, and do not read these instructions:

{script}"""


def plan(L):
    d, v, lang, beats = load(L)
    cps = float(arg("--cps", 5.6))
    takes, cur, cur_s = [], [], 0.0
    for b in beats:
        s = est_seconds(b["say"], lang, cps) + 0.5
        if cur and cur_s + s > TAKE_MAX:
            takes.append(cur); cur, cur_s = [], 0.0
        cur.append(b); cur_s += s
    if cur:
        takes.append(cur)
    lex = d.get("lexicon") or {}
    pron = ("3b. Pronunciation: " + "; ".join(f'"{k}" as "{val}"' for k, val in lex.items()) + ".\n") if lex else ""
    out = []
    for i, tk in enumerate(takes, 1):
        need = sum(est_seconds(b["say"], lang, cps) + 0.5 for b in tk)
        cap = int(need * 1.25 + 3)
        prompt = PROMPT.format(speaker=v.get("speaker") or "a lively Mandarin-speaking science creator in their late twenties",
                               style=v.get("style") or "fast, tight, curious, with a sense of suspense", cps=cps, pron=pron, cap=cap,
                               lang_name={"zh": "Mandarin Chinese", "en": "English"}.get(lang, lang),
                               script="\n\n".join(b["say"] for b in tk))
        out.append({"take": i, "beats": [b["id"] for b in tk], "est_seconds": round(need, 1), "cap_seconds": cap,
                    "reference_audio": v.get("ref") or None, "prompt": prompt})
    (L / "build").mkdir(exist_ok=True)
    (L / "build/voice_plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in out:
        print(f"── take {t['take']}：{t['beats'][0]}–{t['beats'][-1]}（{len(t['beats'])} 拍），约 {t['est_seconds']}s，上限写 {t['cap_seconds']}s"
              + (f"，音色参照 {t['reference_audio']}" if t["reference_audio"] else "，没有音色参照（按 speaker 描述配）"))
        print(t["prompt"] + "\n")
    print(f"→ {L / 'build/voice_plan.json'}（{len(out)} 条 take；下载后按顺序交给 voice.py align）")


# ── 音频 ──
def read16(path):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.float32).copy()


def write_wav(path, x, sr=48000, src_sr=SR):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ac", "1", "-ar", str(src_sr), "-i", "-", "-ar", str(sr), str(path)], input=pcm, check=True)


def silences(x, thr_db=-38, min_len=0.22):
    win = int(0.02 * SR)
    n = len(x) // win
    if n == 0:
        return []
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    quiet = 20 * np.log10(rms) < thr_db
    out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.02 >= min_len:
                out.append((i * 0.02, j * 0.02))
            i = j
        else:
            i += 1
    return out


_MODEL = {}


def whisper():
    name = arg("--model", os.environ.get("WHISPER_MODEL", "small"))
    if name not in _MODEL:
        from faster_whisper import WhisperModel
        _MODEL[name] = WhisperModel(name, device="cpu", compute_type="int8")
    return _MODEL[name]


def transcribe_chars(x, lang, hint):
    """按停顿切块逐块转写（长 take 一次转写会压缩前面的时间、在静音里编词），返回 [(字, 开始秒)]。中文按字，英文按词。"""
    dur = len(x) / SR
    sil = silences(x)
    cuts = [0.0] + [(a + b) / 2 for a, b in sil if b - a > 0.3] + [dur]
    # 块太碎就合并到 ≥ 8 秒
    merged = [cuts[0]]
    for c in cuts[1:-1]:
        if c - merged[-1] >= 8:
            merged.append(c)
    merged.append(dur)
    model = whisper()
    out = []
    for a, b in zip(merged, merged[1:]):
        seg = x[int(a * SR):int(b * SR)]
        if b - a < 0.25 or np.sqrt((seg ** 2).mean()) < 0.003:
            continue
        segs, _ = model.transcribe(seg, language=lang, word_timestamps=True, initial_prompt=hint, vad_filter=False, beam_size=5,
                                   condition_on_previous_text=False)
        for s in segs:
            for w in s.words or []:
                t0, t1 = a + w.start, a + w.end
                if lang == "en":
                    word = w.word.strip()
                    if word:
                        out.append((word.lower(), t0))
                else:
                    chars = [c for c in w.word if not c.isspace()]
                    for k, c in enumerate(chars):
                        out.append((c, t0 + (t1 - t0) * k / max(1, len(chars))))
    return out


def norm_units(text, lang):
    """原文 → 对齐单位（中文按字，英文按词），附原文下标。"""
    if lang == "en":
        return [(m.group(0).lower(), m.start()) for m in re.finditer(r"[A-Za-z0-9']+", text)]
    return [(c.lower().translate(CN_NUM), i) for i, c in enumerate(text) if c not in PUNCT and not c.isspace()]


def align_units(units, heard, t_end):
    """原文每个单位的开始秒：对得上的用听写时间，对不上的在前后已知点之间插值。返回 (times, 对上了的单位下标集合)。"""
    a = [u for u, _ in units]
    b = [h.translate(CN_NUM) for h, _ in heard if h not in PUNCT]
    bt = [t for h, t in heard if h not in PUNCT]
    known = {}
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            known[blk.a + k] = bt[blk.b + k]
    last = 0.0
    for k in sorted(known):
        known[k] = max(known[k], last); last = known[k]
    anchors = [(-1, max(0.0, (min(known.values()) if known else 0) - 0.3))] + sorted(known.items()) + [(len(a), t_end)]
    times = [0.0] * len(a)
    for (k0, t0), (k1, t1) in zip(anchors, anchors[1:]):
        for k in range(k0 + 1, k1):
            times[k] = t0 + (t1 - t0) * (k - k0) / (k1 - k0)
        if 0 <= k1 < len(a):
            times[k1] = t1
    return times, set(known)


# ── 输出 ──
def finish(L, beats, lang, engine, gap, lead):
    """beats 里每拍已有 wav（16 kHz 单声道 numpy，首尾已裁）与 rel（每个原文字符相对本拍开头的秒）、cover。"""
    B = L / "build"
    (B / "audio").mkdir(parents=True, exist_ok=True)
    timings = {"voice": {"engine": engine}, "beats": {}}
    t, parts = lead, []
    for b in beats:
        clean, dur = b["clean"], len(b["x"]) / SR
        starts = [round(t + v, 3) for v in b["rel"]]
        words = []
        if lang == "en":
            for m in re.finditer(r"[A-Za-z0-9](?:[A-Za-z0-9'’\-]|\.(?=[A-Za-z0-9]))*", clean):
                i, i1 = m.start(), m.end()
                nxt = next((starts[k] for k in range(i1, len(clean)) if starts[k] > starts[i] and clean[k].isalnum()), round(t + dur, 3))
                words.append({"text": m.group(0), "start": starts[i], "end": min(nxt, round(t + dur, 3)), "i0": i, "i1": i1})
        else:
            for i, ch in enumerate(clean):
                if ch.isspace() or ch in PUNCT:
                    continue
                nxt = next((starts[k] for k in range(i + 1, len(clean)) if starts[k] > starts[i]), round(t + dur, 3))
                words.append({"text": ch, "start": starts[i], "end": min(nxt, round(t + dur, 3)), "i0": i, "i1": i + 1})
        cues = {name: next((w["start"] for w in words if w["i0"] >= k), round(t + dur, 3)) for name, k in b["cues"].items()}
        write_wav(B / "audio" / f"{b['id']}.wav", b["x"])
        timings["beats"][b["id"]] = {"file": f"audio/{b['id']}.wav", "text": clean, "start": round(t, 3), "end": round(t + dur, 3),
                                     "duration": round(dur, 3), "words": words, "chars": starts, "cues": cues, "align": round(b["cover"], 3)}
        n = len([c for c in clean if c not in PUNCT and not c.isspace()])
        print(f"{b['id']}  {dur:5.2f}s  {n:3d} 字  {n / max(dur, 0.1):.2f} 字/秒  对齐 {b['cover']:.0%}" + ("  ⚠ 对齐偏低，听一下这拍" if b["cover"] < 0.85 else ""))
        if b.get("heard") is not None and b["cover"] < 0.95:
            print(f"      听写：{b['heard']}")
        parts.append((b["x"], t))
        t += dur + max(gap, b["gap"])
    total = round(t - gap + lead, 3)
    timings["total"] = total
    mix = np.zeros(int(round(total * SR)) + SR, np.float32)
    for x, start in parts:
        i0 = int(round(start * SR)); mix[i0:i0 + len(x)] += x
    write_wav(B / "narration.wav", mix[: int(round(total * SR))])
    for f in ("timings.orig.json", "narration.orig.wav"):   # speed.py 的原件作废
        (B / f).unlink(missing_ok=True)
    (B / "timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"合计 {total:.2f}s → {B / 'timings.json'}、{B / 'narration.wav'}")


def trim(x, pad=0.06):
    """去掉首尾静音，留一点余量。返回 (裁好的音频, 开头裁掉了多少采样)。"""
    win = int(0.01 * SR)
    n = len(x) // win
    if n == 0:
        return x, 0
    rms = 20 * np.log10(np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12))
    loud = np.where(rms > -42)[0]
    if not len(loud):
        return x, 0
    a = max(0, loud[0] * win - int(pad * SR)); z = min(len(x), (loud[-1] + 1) * win + int(pad * SR))
    return x[a:z], a


def hint_for(lang, text):
    terms = "、".join(dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z0-9.\-]*|《[^》]+》", text)))[:200]
    if lang == "zh":
        return "以下是普通话，用简体中文。" + (f"会提到：{terms}。" if terms else "")
    return f"Terms: {terms}." if terms else None


def align_takes(L, takes):
    d, v, lang, beats = load(L)
    plan_f = L / "build/voice_plan.json"
    groups = [p["beats"] for p in json.loads(plan_f.read_text(encoding="utf-8"))] if plan_f.exists() else [[b["id"] for b in beats]]
    if len(groups) != len(takes):
        sys.exit(f"voice_plan.json 有 {len(groups)} 条 take，给了 {len(takes)} 个文件：按 plan 的顺序一条一个")
    by_id = {b["id"]: b for b in beats}
    for ids, path in zip(groups, takes):
        x = read16(path)
        dur = len(x) / SR
        group = [by_id[i] for i in ids]
        full, spans = "", []
        for b in group:
            spans.append((len(full), len(full) + len(b["clean"])))
            full += b["clean"] + "\n"
        heard = transcribe_chars(x, lang, hint_for(lang, full))
        units = norm_units(full, lang)
        times, known = align_units(units, heard, dur)
        cover = len(known) / max(1, len(units))
        pos = [i for _, i in units]
        print(f"take {Path(path).name}：{dur:.1f}s，整条对齐 {cover:.0%}")
        if cover < 0.6:
            print("  ⚠ 对齐率很低：这条可能念错了段落、漏了大段或语言不对。听一遍，必要时重新生成（新报价）。")
        for b, (s0, s1) in zip(group, spans):
            ks = [k for k, i in enumerate(pos) if s0 <= i < s1]
            if not ks:
                sys.exit(f"{b['id']} 没有可对齐的字")
            nxt = next((times[k] for k, i in enumerate(pos) if i >= s1), dur)
            a = max(0.0, times[ks[0]] - 0.12)
            z = min(dur, nxt - 0.05) if nxt > times[ks[-1]] else dur
            seg, cut = trim(x[int(a * SR):int(z * SR)])
            base = a + cut / SR
            rel_units = {pos[k] - s0: max(0.0, times[k] - base) for k in ks}
            rel, last = [], 0.0
            for i, c in enumerate(b["clean"]):
                if i in rel_units:
                    last = max(last, rel_units[i])
                rel.append(min(last, len(seg) / SR))
            b["x"], b["rel"] = seg, rel
            hb = [h for h, t in heard if a - 0.05 <= t < z]
            b["heard"] = ("" if lang == "zh" else " ").join(hb)
            b["cover"] = sum(1 for k in ks if k in known) / len(ks)
    finish(L, beats, lang, "renoise", float(arg("--gap", 0.2)), float(arg("--lead", 0.3)))


# ── MiMo（可选）──
def mimo(L):
    import base64
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    d, v, lang, beats = load(L)
    key, base = os.environ.get("MIMO_API_KEY"), os.environ.get("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
    if not key:
        sys.exit("MiMo 要用户自己的密钥：export MIMO_API_KEY=…（只放在环境变量里，不写进任何文件）。没有就用默认的 Renoise 配音。")
    ref = v.get("ref") or ""
    clone = None
    if ref and not ref.startswith(("material:", "task:")):
        p = Path(ref) if Path(ref).is_absolute() else (L / ref)
        clone = "data:audio/wav;base64," + base64.b64encode(p.read_bytes()).decode()
    model = "mimo-v2.5-tts-voiceclone" if clone else "mimo-v2.5-tts"
    style = v.get("style") or ""

    def call(body):
        req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body, ensure_ascii=False).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        for k in range(8):
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    return json.loads(r.read())
            except Exception as e:  # noqa: BLE001  限流（429）和网络抖动都退避重试
                wait = min(60, 10 * (k + 1))
                print(f"  {wait}s 后重试：{e}", file=sys.stderr)
                time.sleep(wait)
        sys.exit("MiMo 调用一直失败")

    def synth(b):
        msgs = ([{"role": "user", "content": style}] if style else []) + [{"role": "assistant", "content": b["say"]}]
        audio = {"format": "wav", "voice": clone} if clone else {"format": "wav", "voice": v.get("mimo_voice", "茉莉")}
        r = call({"model": model, "messages": msgs, "audio": audio})
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(base64.b64decode(r["choices"][0]["message"]["audio"]["data"]))
        x = trim(read16(f.name))[0]; os.unlink(f.name)
        return x

    with ThreadPoolExecutor(int(arg("--jobs", 2))) as ex:
        xs = list(ex.map(synth, beats))
    for b, x in zip(beats, xs):
        heard = transcribe_chars(x, lang, hint_for(lang, b["clean"]))
        units = norm_units(b["clean"], lang)
        times, known = align_units(units, heard, len(x) / SR)
        cover = len(known) / max(1, len(units))
        rel_units = {i: t for (_, i), t in zip(units, times)}
        rel, last = [], 0.0
        for i in range(len(b["clean"])):
            if i in rel_units:
                last = rel_units[i]
            rel.append(last)
        b.update(x=x, rel=rel, cover=cover, heard=("" if lang == "zh" else " ").join(h for h, _ in heard))
    finish(L, beats, lang, "mimo", float(arg("--gap", 0.2)), float(arg("--lead", 0.3)))


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("plan", "align", "mimo"):
        sys.exit(__doc__)
    L = lesson_dir(sys.argv[2])
    if sys.argv[1] == "plan":
        plan(L)
    elif sys.argv[1] == "align":
        takes = [a for a in sys.argv[3:] if not a.startswith("--") and a not in {arg(k) for k in ("--gap", "--lead", "--model", "--ws")}]
        if not takes:
            sys.exit("给出下载好的 take 文件（按 voice_plan.json 的顺序）")
        align_takes(L, takes)
    else:
        mimo(L)


if __name__ == "__main__":
    main()
