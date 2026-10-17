#!/usr/bin/env python3
"""Flag VO takes with junk after the last real word (MiMo sometimes appends a mumble, e.g. "Alakavis").
usage: tailcheck.py <audio dir> <narration.json>   -> prints OK / TAIL per beat"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
W = Path.home() / ".cache/history-epic/whisper/ggml-medium-q5_0.bin"
adir, spec = Path(sys.argv[1]), json.load(open(sys.argv[2], encoding="utf-8"))
bad = 0
for b in spec["beats"]:
    text = re.sub(r"\[\[\w+\]\]", "", b["narration"])
    last = re.findall(r"[A-Za-z]+", text)[-1].lower()
    wav = adir / f"{b['id']}.wav"
    with tempfile.TemporaryDirectory() as td:
        w16 = Path(td) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ar", "16000", "-ac", "1", str(w16)], check=True)
        subprocess.run(["whisper-cli", "-m", str(W), "-l", "en", "-f", str(w16), "-ojf", "-of", str(Path(td) / "o"), "-np"], capture_output=True, check=True)
        d = json.loads((Path(td) / "o.json").read_bytes().decode("utf-8", "ignore"))
        toks = [(t["text"].strip().lower(), t["offsets"]["from"] / 1000, t["offsets"]["to"] / 1000) for s in d["transcription"] for t in s.get("tokens", []) if t["text"].strip() and not t["text"].startswith("[")]
        heard = " ".join(s["text"] for s in d["transcription"]).strip()
        x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(w16), "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
    # end of the last real word = last token that is part of the final word of the script
    ends = [e for tk, s, e in toks if re.sub(r"[^a-z]", "", tk) and last.startswith(re.sub(r"[^a-z]", "", tk)[:3])]
    end = ends[-1] if ends else len(x) / 16000
    tail = x[int((end + 0.18) * 16000):]
    w = 1600
    n = len(tail) // w
    loud = [20 * np.log10(np.sqrt((tail[i * w:(i + 1) * w] ** 2).mean()) + 1e-9) for i in range(n)]
    extra = heard.lower().split(last)[-1] if last in heard.lower() else heard
    flag = (loud and max(loud) > -32) or re.search(r"[a-z]{2,}", re.sub(r"[^a-z ]", "", extra.lower()))
    bad += bool(flag)
    print(f"{b['id']} {'TAIL' if flag else 'OK  '} end {end:.2f}s / {len(x)/16000:.2f}s  tail max {max(loud) if loud else -99:.0f} dB  heard: {heard}")
sys.exit(1 if bad else 0)
