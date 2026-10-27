"""Put the chosen take on the video clock.
  python3 layout.py audio/vo_A.wav audio/vo_A_align.json
Each script line is cut out of the take (snapped to the pauses around it) and placed after a gap (EP.pacing per line, EP.gap
default), so the picture gets room for its actions. Writes timeline.js (lines, subtitle phrases, anchors, mouth envelope, duration)
and audio/vo_track.wav (48 kHz mono, on the video clock)."""
import json, re, sys
import numpy as np
from common import ROOT, read_ep, read_wav, write_wav, resample, silences, norm_chars, spaced, PUNCT_SPLIT

FPS, SR = 30, 48000


def main():
    wav, aln = sys.argv[1], json.load(open(sys.argv[2], encoding='utf-8'))
    ep = read_ep()
    x, sr = read_wav(wav)
    x = resample(x, sr, SR)
    sil = silences(x, SR, -40, .2)
    ss, se = [a for a, _ in sil], [b for _, b in sil]
    snap_s = lambda t: min([e for e in se if -.5 <= e - t <= .8], key=lambda e: abs(e - t), default=t)
    snap_e = lambda t: min([s for s in ss if -.3 <= s - t <= .6], key=lambda s: abs(s - t), default=t)
    pacing = {int(k): float(v) for k, v in (ep.get('pacing') or {}).items()}
    gap0, tail = float(ep.get('gap', .3)), float(ep.get('tail', 2.6))

    t, lines, segs = 0.0, [], []
    for n, L in enumerate(aln['lines'], 1):
        s, e = snap_s(L['s']), snap_e(L['e'])
        a, b = max(0, s - .06), e + .14
        t += pacing.get(n, gap0)
        off = t - a
        segs.append((a, b, t)); t += b - a
        ch = [[c, round(c0 + off, 3), round(c1 + off, 3)] for c, c0, c1 in L['chars']]
        ch[0][1] = max(ch[0][1], round(s + off, 3)); ch[-1][2] = round(e + off, 3)
        phr, k = [], 0
        for p in PUNCT_SPLIT.split(L['text']):
            core = norm_chars(p)
            if not core:
                continue
            txt = re.sub(r'^[—\s]+|[，。：；、,.:;\s]+$', '', p.replace('"', '').replace('“', '').replace('”', '')).strip()
            j = min(k + len(core) - 1, len(ch) - 1)
            phr.append({'text': txt, 's': ch[min(k, len(ch) - 1)][1], 'e': ch[j][2]}); k += len(core)
        lines.append({'n': n, 'text': L['text'], 's': round(s + off, 3), 'e': round(e + off, 3), 'chars': ch, 'phr': phr, 'spaced': spaced(L['text'])})
    dur = round(t + tail, 3)

    out = np.zeros(int((dur + 1) * SR))
    for a, b, d in segs:
        seg = x[int(a * SR):int(b * SR)].copy(); f = int(.015 * SR)
        seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        out[int(d * SR):int(d * SR) + len(seg)] += seg
    (ROOT / 'audio').mkdir(exist_ok=True)
    write_wav(ROOT / 'audio/vo_track.wav', out[:int(dur * SR)], SR)
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(out[i * hop:(i + 1) * hop] ** 2)) for i in range(int(dur * FPS))])
    env = np.clip((20 * np.log10(env + 1e-6) + 42) / 24, 0, 1)
    env = np.round(np.convolve(env, [.25, .5, .25], 'same'), 2)

    anchors, problems = {}, []
    for name, spec in (ep.get('anchors') or {}).items():
        n, word, occ = spec[0], spec[1], (spec[2] if len(spec) > 2 else 0)
        if not 1 <= n <= len(lines):
            problems.append(f'{name}: no line {n}'); continue
        L = lines[n - 1]; txt = ''.join(c for c, _, _ in L['chars']); w = ''.join(norm_chars(word)); i = -1
        for _ in range(occ + 1):
            i = txt.find(w, i + 1)
        if i < 0:
            problems.append(f'{name}: "{word}" is not in line {n}'); continue
        anchors[name] = L['chars'][i][1]
    if problems:
        raise SystemExit('anchor errors:\n  ' + '\n  '.join(problems))
    TL = {'dur': dur, 'fps': FPS, 'lines': lines, 'a': anchors, 'env': env.tolist()}
    (ROOT / 'timeline.js').write_text('window.TL=' + json.dumps(TL, ensure_ascii=False) + ';\n', encoding='utf-8')
    for L in lines:
        print(f"L{L['n']:<2} {L['s']:7.2f}-{L['e']:7.2f}  " + ' | '.join(p['text'] for p in L['phr']))
    print('anchors', {k: round(v, 2) for k, v in anchors.items()})
    print('duration', dur, '-> timeline.js, audio/vo_track.wav')


if __name__ == '__main__':
    main()
