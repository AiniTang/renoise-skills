#!/usr/bin/env python3
"""Generate a voiceover line by line and write a timing file the film can align to.

Usage:
  python3 voiceover.py lines.json <project>/public/vo --engine mimo [--voice Milo]
  python3 voiceover.py lines.json <project>/public/vo --engine say [--voice <system voice> --rate 150]

lines.json: {"style": "<delivery instructions>", "lines": [{"id": "open", "text": "..."}, ...]}
Output: <out>/<id>.wav (48 kHz mono 16-bit) and <out>/timing.json
        {"lines": [{"id", "text", "file", "seconds"}]}

mimo: Xiaomi MiMo `mimo-v2.5-tts`. Reads the key from MIMO_API_KEY or from the file named by
MIMO_API_KEY_FILE; never prints it. Stops on the first API error (no retries, no purchases).
say:  the computer's own voice, a free scratch track for timing: macOS `say` (default voice Daniel), Windows SAPI
      through PowerShell (--voice "Microsoft David Desktop"; default: the system voice), Linux espeak-ng (--voice en-us).
      Converted to 48 kHz mono with ffmpeg.
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave

if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK copy or emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"


def mimo_key():
    key = os.environ.get("MIMO_API_KEY", "").strip()
    path = os.environ.get("MIMO_API_KEY_FILE", "")
    if not key and path and os.path.exists(os.path.expanduser(path)):
        key = open(os.path.expanduser(path), encoding="utf-8").read().strip()
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


# Windows: SAPI through PowerShell. Text, voice and file come in as environment variables, so nothing needs quoting.
SAPI = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "if ($env:VO_VOICE) { $s.SelectVoice($env:VO_VOICE) }; $s.Rate = [int]$env:VO_RATE; $s.SetOutputToWaveFile($env:VO_OUT); "
        "$s.Speak([IO.File]::ReadAllText($env:VO_TEXT, [Text.Encoding]::UTF8)); $s.Dispose()")


def tts_say(text, voice, rate):
    with tempfile.TemporaryDirectory() as d:
        env = None
        if sys.platform == "darwin":
            raw = os.path.join(d, "l.aiff")
            cmd = ["say", *(["-v", voice] if voice else []), "-r", str(rate), "-o", raw, text]
        elif sys.platform == "win32":
            raw, text_file = os.path.join(d, "l.wav"), os.path.join(d, "l.txt")
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(text)
            # SAPI's rate runs -10..10 around its normal ~150 words per minute.
            env = {**os.environ, "VO_VOICE": voice or "", "VO_RATE": str(max(-10, min(10, round((rate - 150) / 15)))),
                   "VO_OUT": raw, "VO_TEXT": text_file}
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", SAPI]
        else:
            espeak = shutil.which("espeak-ng") or shutil.which("espeak")
            if not espeak:
                sys.exit("--engine say on Linux needs espeak-ng (apt install espeak-ng)")
            raw = os.path.join(d, "l.wav")
            cmd = [espeak, *(["-v", voice] if voice else []), "-s", str(rate), "-w", raw, text]
        subprocess.run(cmd, check=True, env=env)
        wav = os.path.join(d, "l48.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
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
    spec = json.load(open(args.lines, encoding="utf-8-sig"))
    os.makedirs(args.out, exist_ok=True)
    key = mimo_key() if args.engine == "mimo" else None
    voice = args.voice or ("Milo" if args.engine == "mimo" else "Daniel" if sys.platform == "darwin" else None)
    timing = []
    for ln in spec["lines"]:
        audio = tts_mimo(ln["text"], spec.get("style", ""), voice, key) if key else tts_say(ln["text"], voice, args.rate)
        path = os.path.join(args.out, f"{ln['id']}.wav")
        secs = normalize(audio, path)
        timing.append({"id": ln["id"], "text": ln["text"], "file": os.path.basename(path), "seconds": round(secs, 3)})
        print(f"{ln['id']:10s} {secs:5.2f}s  {ln['text']}")
    with open(os.path.join(args.out, "timing.json"), "w", encoding="utf-8") as f:
        json.dump({"engine": args.engine, "voice": voice or "default", "lines": timing}, f, ensure_ascii=False, indent=2)
    print(f"total speech {sum(t['seconds'] for t in timing):.2f}s -> {args.out}/timing.json")


if __name__ == "__main__":
    main()
