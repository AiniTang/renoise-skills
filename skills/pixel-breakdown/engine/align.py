"""Transcribe one narration take (faster-whisper, word timestamps) and align it to the script in episode.js.
  python3 align.py audio/vo_A.wav [--model small] [--threads 8]
Writes audio/vo_A_align.json and prints a report: per-chunk transcript (read it against the script for added, dropped or misread
words), matched-character share, and whether the take ends in silence (no silence = cut off mid-word).
The take is split at its pauses and each chunk transcribed on its own: on long takes whisper compresses early word times and
invents words in padded silence; words that land on silence are dropped."""
import difflib, json, sys
import numpy as np
from common import ROOT, read_ep, read_wav, resample, silences, norm_chars


def main():
    wav = sys.argv[1]
    model_name = sys.argv[sys.argv.index('--model') + 1] if '--model' in sys.argv else 'small'
    threads = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 8
    ep = read_ep()
    lines = [l.strip() for l in ep['script'] if l.strip()]
    lang = (ep.get('lang') or 'en').split('-')[0]
    full = (ep.get('lang') or 'en').lower()
    default_hint = {'zh-tw': '以下是國語的句子，使用繁體中文。', 'zh-hk': '以下是國語的句子，使用繁體中文。'}.get(full, '以下是普通话的句子，使用简体中文。' if lang == 'zh' else None)
    hint = ep.get('asrHint') or default_hint                     # Chinese: steer the script (simplified / traditional) to match the text
    remap = ep.get('asrMap') or {}

    x, sr = read_wav(wav)
    x16 = resample(x, sr, 16000).astype(np.float32)
    dur = len(x16) / 16000
    sil = silences(x16, 16000, -38, .22)
    tail_ok = bool(sil) and sil[-1][1] >= dur - .05 and sil[-1][1] - sil[-1][0] >= .15
    cuts = [0.0] + [(a + b) / 2 for a, b in sil] + [dur]

    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device='cpu', compute_type='int8', cpu_threads=threads)
    pad = .2
    def loud(t0, t1):
        w = x16[int(t0 * 16000):max(int(t0 * 16000) + 160, int(t1 * 16000))]
        return w.size and 20 * np.log10(np.sqrt((w ** 2).mean()) + 1e-9) > -36
    words, report = [], []
    for a, b in zip(cuts, cuts[1:]):
        seg = x16[int(a * 16000):int(b * 16000)]
        if b - a < .25 or np.sqrt((seg ** 2).mean()) < .003:
            continue
        audio = np.pad(seg, (int(pad * 16000), int(pad * 16000)))
        segs, _ = model.transcribe(audio, language=lang, word_timestamps=True, initial_prompt=hint, condition_on_previous_text=False, vad_filter=False, beam_size=5)
        chunk = []
        for s in segs:
            for w in s.words or []:
                t0, t1 = min(b, max(a, w.start - pad + a)), min(b, max(a, w.end - pad + a))
                if loud(t0, t1):
                    chunk.append((w.word, t0, t1))
        if chunk:
            words += chunk
            report.append(f'{chunk[0][1]:6.2f}-{chunk[-1][2]:6.2f} ' + ''.join(w for w, _, _ in chunk))

    # ASR characters with interpolated per-character times
    asr = []
    for w, t0, t1 in words:
        cs = norm_chars(''.join(remap.get(ch, ch) for ch in w))
        for k, ch in enumerate(cs):
            asr.append((ch, t0 + (t1 - t0) * k / len(cs), t0 + (t1 - t0) * (k + 1) / len(cs)))
    S, owner = [], []
    for li, l in enumerate(lines):
        for ch in norm_chars(l):
            S.append(ch); owner.append(li)
    A = ''.join(c for c, _, _ in asr)
    t0s, t1s = [None] * len(S), [None] * len(S)
    for i, j, n in difflib.SequenceMatcher(None, ''.join(S), A, autojunk=False).get_matching_blocks():
        for k in range(n):
            t0s[i + k], t1s[i + k] = asr[j + k][1], asr[j + k][2]
    known = [i for i in range(len(S)) if t0s[i] is not None]
    if not known:
        raise SystemExit('nothing matched: wrong take, wrong language or empty transcript')
    for i in range(len(S)):
        if t0s[i] is None:
            p = max([k for k in known if k < i], default=None); q = min([k for k in known if k > i], default=None)
            if p is None: t0s[i] = t1s[i] = t0s[q]
            elif q is None: t0s[i] = t1s[i] = t1s[p]
            else:
                f = (i - p) / (q - p); t0s[i] = t1s[p] + (t0s[q] - t1s[p]) * f; t1s[i] = t0s[i] + .1
    out = {'take': wav, 'dur': round(dur, 3), 'matched': len(known), 'total': len(S), 'tail_silence': tail_ok, 'transcript': report, 'lines': []}
    for li, l in enumerate(lines):
        idx = [i for i in range(len(S)) if owner[i] == li]
        out['lines'].append({'text': l, 's': round(t0s[idx[0]], 3), 'e': round(t1s[idx[-1]], 3), 'chars': [[S[i], round(t0s[i], 3), round(t1s[i], 3)] for i in idx]})
    dst = wav.rsplit('.', 1)[0] + '_align.json'
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('\n'.join(report))
    print(f'matched {len(known)}/{len(S)} characters ({100 * len(known) / len(S):.0f}%), {dur:.2f}s,',
          'tail silence ok' if tail_ok else '!! NO tail silence: the take may be cut off mid-word', '->', dst)


if __name__ == '__main__':
    main()
