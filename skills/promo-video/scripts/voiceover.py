#!/usr/bin/env python3
"""Generate a voiceover line by line and write a timing file the film can align to.

Usage:
  python3 voiceover.py lines.json <project>/public/vo --engine mimo [--voice Milo]
  python3 voiceover.py lines.json <project>/public/vo --engine say [--voice Daniel --rate 150]

lines.json: {"style": "<delivery instructions>", "lines": [{"id": "open", "text": "..."}, ...]}
Output: <out>/<id>.wav (48 kHz mono 16-bit) and <out>/timing.json
        {"lines": [{"id", "text", "file", "seconds"}]}

mimo: Xiaomi MiMo `mimo-v2.5-tts`. Reads the key from MIMO_API_KEY or from the file named by
MIMO_API_KEY_FILE; never prints it. Stops on the first API error (no retries, no purchases).
say:  macOS system voice, useful as a free scratch track for timing.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave

MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"


def mimo_key():
    key = os.environ.get("MIMO_API_KEY", "").strip()
    path = os.environ.get("MIMO_API_KEY_FILE", "")
    if not key and path and os.path.exists(os.path.expanduser(path)):
        key = open(os.path.expanduser(path)).read().strip()
    if not key:
        sys.exit("MIMO_API_KEY (or MIMO_API_KEY_FILE) is not set")
    return key


def tts_mimo(text, style, voice, key):
    body = {
        "model": "mimo-v2.5-tts",
        "messages": [{"role": "user", "content": style}, {"role": "assistant", "content": text}],
        "audio": {"format": "wav", "voice": voice},
    }
    req = urllib.request.Request(MIMO_URL, data=json.dumps(body).encode(), headers={"api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"MiMo error {e.code}: {e.read().decode(errors='replace')[:300]}")
    return base64.b64decode(data["choices"][0]["message"]["audio"]["data"])


def tts_say(text, voice, rate):
    with tempfile.TemporaryDirectory() as d:
        aiff = os.path.join(d, "l.aiff")
        subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", aiff, text], check=True)
        wav = os.path.join(d, "l.wav")
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@48000", "-c", "1", aiff, wav], check=True)
        return open(wav, "rb").read()


def normalize(wav_bytes, out_path, target_peak_db=-3.0):
    """Trim leading/trailing silence, convert to mono 16-bit, peak-normalize."""
    import array
    import io

    w = wave.open(io.BytesIO(wav_bytes))
    sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
    raw = w.readframes(w.getnframes())
    if sw != 2:
        sys.exit(f"unsupported sample width {sw}")
    a = array.array("h", raw)
    if ch > 1:
        a = array.array("h", [sum(a[i : i + ch]) // ch for i in range(0, len(a), ch)])
    peak = max(1, max(abs(x) for x in a))
    thr = peak * 0.02
    start = next((i for i, x in enumerate(a) if abs(x) > thr), 0)
    end = len(a) - next((i for i, x in enumerate(reversed(a)) if abs(x) > thr), 0)
    pad = int(sr * 0.04)
    a = a[max(0, start - pad) : min(len(a), end + pad)]
    gain = (10 ** (target_peak_db / 20) * 32767) / peak
    a = array.array("h", [max(-32768, min(32767, int(x * gain))) for x in a])
    o = wave.open(out_path, "wb")
    o.setnchannels(1)
    o.setsampwidth(2)
    o.setframerate(sr)
    o.writeframes(a.tobytes())
    o.close()
    return len(a) / sr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lines")
    ap.add_argument("out")
    ap.add_argument("--engine", choices=["mimo", "say"], default="mimo")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", type=int, default=150)
    args = ap.parse_args()
    spec = json.load(open(args.lines))
    os.makedirs(args.out, exist_ok=True)
    key = mimo_key() if args.engine == "mimo" else None
    voice = args.voice or ("Milo" if args.engine == "mimo" else "Daniel")
    timing = []
    for ln in spec["lines"]:
        audio = tts_mimo(ln["text"], spec.get("style", ""), voice, key) if key else tts_say(ln["text"], voice, args.rate)
        path = os.path.join(args.out, f"{ln['id']}.wav")
        secs = normalize(audio, path)
        timing.append({"id": ln["id"], "text": ln["text"], "file": os.path.basename(path), "seconds": round(secs, 3)})
        print(f"{ln['id']:10s} {secs:5.2f}s  {ln['text']}")
    json.dump({"engine": args.engine, "voice": voice, "lines": timing}, open(os.path.join(args.out, "timing.json"), "w"), indent=2)
    print(f"total speech {sum(t['seconds'] for t in timing):.2f}s -> {args.out}/timing.json")


if __name__ == "__main__":
    main()
