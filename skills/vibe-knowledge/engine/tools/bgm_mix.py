"""默认 BGM 与音量校准（finish.py 混音时调用）。

设置在工作区的 vk.json（new_film.py 建好；没有就用下面的默认值）：
  {"bgm": "cine/music/vibe-bgm.m4a", "force_bgm": true, "voice_gap_db": 10}
- force_bgm 为 true（默认）：film.js 没放 BGM（src 文件名是 bgm.wav / bgm_auto.wav 的条目）就按片长自动补上默认 BGM；
  其他 ≥20 秒的整段配乐停用，短音效和镜头原声保留。
- 换曲：film.js 里那条音乐写 bgm: true，它就是这期的 BGM，默认曲让位（音量照样校准）。
- 关掉：vk.json 写 "force_bgm": false，或 film.js 导出 meta = { bgm: false }（这一期不要 BGM）。
- 不管 film.js 写了多大 gain，BGM 整体音量都按人声重新校准：说话时 BGM 比人声低 voice_gap_db dB；
  gain_curve 只保留起伏形状，绝对音量由这里定。没说话的地方照 finish.py 的压低逻辑自动抬起。
- 写 build/bgm.json（有没有 BGM、校准前后的人声比），qa.py 读它。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LONG = 20.0


def config():
    cfg = {"bgm": "cine/music/vibe-bgm.m4a", "force_bgm": True, "voice_gap_db": 10.0}
    f = ROOT / "vk.json"
    if f.exists():
        cfg.update(json.loads(f.read_text(encoding="utf-8")))
    return cfg


def is_bgm(m):
    return bool(m.get("bgm")) or Path(str(m.get("src", ""))).name in ("bgm.wav", "bgm_auto.wav")


def prepare(info, total, B):
    cfg = config()
    music = info.get("music", [])
    if (info.get("meta") or {}).get("bgm") is False or not cfg.get("force_bgm", True):
        for m in music:
            if is_bgm(m):
                m["_bgm"] = True
        return {"forced": False, "auto": False, "dropped": [], "user_bgm": None, "voice_gap_target_db": cfg["voice_gap_db"]}
    explicit = [m for m in music if m.get("bgm")]
    keep, dropped = [], []
    for m in music:
        name = Path(str(m.get("src"))).name
        if explicit and is_bgm(m) and not m.get("bgm"):
            dropped.append(name); continue          # 这期换了曲：默认曲让位
        if is_bgm(m):
            m["_bgm"] = True; keep.append(m)
        elif float(m.get("dur", 0)) >= LONG and not str(m.get("src", "")).startswith("earshot:"):
            dropped.append(name)
        else:
            keep.append(m)
    auto = False
    if not any(m.get("_bgm") for m in keep):
        src = ROOT / cfg["bgm"]
        out = Path(B) / "bgm_auto.wav"
        subprocess.run([sys.executable, str(Path(__file__).with_name("fit_bgm.py")), str(out), "--seconds", f"{total:.3f}", "--src", str(src)],
                       check=True, stdout=subprocess.DEVNULL)
        keep.insert(0, {"src": str(out), "from": 0, "at": 0, "dur": total, "gain": 0, "fade_in": 0.3, "fade_out": 1.8, "_bgm": True})
        auto = True
        print(f"  BGM：film.js 没放 BGM，已按片长 {total:.1f}s 自动补上 {src.name}")
    if dropped:
        print(f"  BGM：停用整段配乐 {', '.join(dropped)}（每期只留一首 BGM）")
    info["music"] = keep
    user = explicit[0] if explicit else None
    return {"forced": True, "auto": auto, "dropped": dropped, "user_bgm": Path(str(user["src"])).name if user else None,
            "voice_gap_target_db": cfg["voice_gap_db"]}


def calibrate(bgmt, narr, speech, B, state):
    """bgmt：已乘过 gain_curve 形状和压低包络的 BGM 轨（n×2）；narr：人声轨；speech：说话的采样掩码。"""
    import numpy as np
    gap = float(state["voice_gap_target_db"])
    rep = {"has_bgm": bool(np.any(bgmt)), **state}
    if rep["has_bgm"] and speech.any():
        rv = np.sqrt(np.mean(narr[speech] ** 2)); rb = np.sqrt(np.mean(bgmt[speech] ** 2))
        before = 20 * np.log10(rv / max(rb, 1e-9))
        g = 10 ** ((before - gap) / 20)
        bgmt = bgmt * g
        quiet = ~speech
        rq = np.sqrt(np.mean(bgmt[quiet] ** 2)) if quiet.any() else 0
        rep.update(voice_gap_before_db=round(float(before), 1), gain_applied_db=round(float(20 * np.log10(g)), 1), voice_gap_db=gap,
                   gap_in_pauses_db=round(float(20 * np.log10(rv / max(rq, 1e-9))), 1) if quiet.any() else None)
        print(f"  BGM 校准：说话时人声比 BGM 高 {before:.1f} → {gap:.1f} dB（BGM {20 * np.log10(g):+.1f} dB）；停顿处 {rep['gap_in_pauses_db']} dB")
    (Path(B) / "bgm.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return bgmt
