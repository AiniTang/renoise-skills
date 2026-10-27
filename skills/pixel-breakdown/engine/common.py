"""Shared helpers for the Pixel Breakdown tools: episode.js, WAV i/o, silence detection, text normalisation."""
import json, re, sys, wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
if sys.platform == 'win32':                                  # the reports print script text (CJK) to a cp1252 console
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def read_ep():
    """episode.js is `window.EP = { ...JSON... };`"""
    src = (ROOT / 'episode.js').read_text(encoding='utf-8')
    body = src[src.index('=') + 1:].strip().rstrip(';')
    return json.loads(body)


def read_wav(path, mono=True):
    """16-bit or 32-bit PCM WAV -> (float64 array in -1..1, sample rate); mono averages channels."""
    with wave.open(str(path), 'rb') as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, '<i2').astype(np.float64) / 32768
    elif sw == 4:
        x = np.frombuffer(raw, '<i4').astype(np.float64) / 2147483648
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        x = ((b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)) << 8 >> 8).astype(np.float64) / 8388608
    else:
        raise SystemExit(f'{path}: unsupported sample width {sw}')
    x = x.reshape(-1, ch)
    return (x.mean(1) if mono else x), sr


def write_wav(path, x, sr):
    x = np.asarray(x)
    ch = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


def resample(x, sr, to):
    if sr == to:
        return x
    from math import gcd
    from scipy.signal import resample_poly
    g = gcd(sr, to)
    return resample_poly(x, to // g, sr // g)


def silences(x, sr, thr_db=-40.0, min_len=0.22):
    """[(start, end)] of stretches quieter than thr_db for at least min_len seconds (10 ms RMS frames)."""
    hop = sr // 100
    n = len(x) // hop
    rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    quiet = 20 * np.log10(rms) < thr_db
    out, start = [], None
    for i, q in enumerate(np.append(quiet, False)):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) / 100 >= min_len:
                out.append((start / 100, i / 100))
            start = None
    return out


PUNCT_SPLIT = re.compile(r'(?<=[，。？！：；、…])|(?<=[,.?!;:])(?=\s)|(?<=——)')


def norm_chars(s):
    """Letters and digits only, lower-cased: the alphabet every timing in this pipeline is indexed by."""
    return [ch.lower() for ch in s if ch.isalnum()]


def spaced(s):
    return bool(re.search(r'[A-Za-zÀ-ɏЀ-ӿ]\s+[A-Za-zÀ-ɏЀ-ӿ]', s))
