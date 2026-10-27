"""Sound design + mix: synthesized chiptune SFX from audio/events.json (render.py cues), the music bed ducked under the narration.
  python3 mix.py            -> audio/mix.wav (48 kHz stereo, not loudness-normalised: that happens at delivery)
Music comes from EP.music: {file: 'audio/music.wav' (48 kHz WAV), offset: seconds into the file to start, gain: dB (default -13),
sections: [[video_t, music_t], ...] optional re-cuts that jump the music to music_t at video_t (pick bar lines), fade: end fade s}."""
import json
import numpy as np
from scipy.signal import butter, sosfilt
from common import ROOT, read_ep, read_wav, write_wav, resample

SR = 48000
EV = json.load(open(ROOT / 'audio/events.json', encoding='utf-8')); DUR = EV['dur']; EP = read_ep(); MUS = EP.get('music') or {}
N = int((DUR + .5) * SR)
rng = np.random.default_rng(7)
T = lambda d: np.arange(int(d * SR)) / SR
db = lambda v: 10 ** (v / 20)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f): return sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
def hp(x, f): return sosfilt(butter(2, f, 'high', fs=SR, output='sos'), x)
def dec(d, tau, att=.002): t = T(d); return np.minimum(1, t / att) * np.exp(-t / tau)
def sweep(f0, f1, d, shape='sine'):
    t = T(d); ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * t / d) / SR
    return np.sin(ph) if shape == 'sine' else np.sign(np.sin(ph)) * .6
def noise(d): return rng.standard_normal(int(d * SR))
def norm(x, peak=1.0): m = np.abs(x).max(); return x / m * peak if m > 0 else x
def cat(*parts):
    n = max(int(o * SR) + len(p) for o, p in parts); x = np.zeros(n)
    for o, p in parts: i = int(o * SR); x[i:i + len(p)] += p
    return x

# ---------------------------------------------------------------- SFX
def tick(): return norm(np.sin(2 * np.pi * 3200 * T(.012)) * dec(.012, .002, .0005), .5)
def pop(): return norm(sweep(520, 1150, .07) * dec(.07, .025, .001), .8)
def blip(): return norm(lp(np.concatenate([sweep(1046, 1046, .045, 'sq') * dec(.045, .03, .001), sweep(1568, 1568, .06, 'sq') * dec(.06, .03, .001)]), 6000), .6)
def click(): a = tick(); return norm(cat((0, a), (.035, a * .7)), .6)
def type_():
    return norm(cat((0, hp(noise(.025), 1800) * dec(.025, .006, .0005)), (0, np.sin(2 * np.pi * 180 * T(.03)) * dec(.03, .008) * .5)), rng.uniform(.5, .8))
def bell(f, d=.9, tau=.35): t = T(d); return (np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .08)) * dec(d, tau, .002)
def chime(): return norm(cat(*[(k * .07, bell(f, .9, .4)) for k, f in enumerate([1318.5, 1975.5, 2637.0])]), .8)
def ding(): return norm(cat(*[(k * .08, bell(f, .6, .22)) for k, f in enumerate([1046.5, 1568.0])]), .8)
def swish(d=.24):
    t = T(d); x = noise(d); out = sum(bp(x, lo, hi) * np.exp(-((t / d - (k + .5) / 3) ** 2) / .02) for k, (lo, hi) in enumerate([(600, 1500), (1200, 3000), (2400, 6000)]))
    return norm(out * np.sin(np.pi * t / d), .7)
def whoosh():
    d = .45; t = T(d); x = noise(d)
    return norm(sum(bp(x, f * .7, f * 1.3) * np.exp(-((t / d - c) ** 2) / .04) for f, c in [(600, .3), (1400, .55), (3000, .75)]) * np.sin(np.pi * t / d) ** 2, .8)
def whip():
    d = .16; t = T(d); x = noise(d)
    return norm(sum(bp(x, max(200, f * .7), min(20000, f * 1.3)) * np.exp(-((t / d - c) ** 2) / .02) for f, c in [(5000, .2), (2850, .5), (700, .8)]) * np.sin(np.pi * t / d), .8)
def blocks(): return norm(lp(cat(*[(k * .042, sweep(f, f, .04, 'sq') * dec(.04, .02, .001)) for k, f in enumerate([523, 659, 784, 1046, 1318, 1568, 2093])]), 6000), .5)
def crt():
    return norm(cat((0, np.sin(2 * np.pi * 70 * T(.12)) * dec(.12, .04, .002)), (0, hp(noise(.18), 2000) * dec(.18, .06, .001) * .5), (0, np.sin(2 * np.pi * 7800 * T(.4)) * dec(.4, .15, .01) * .15)), .9)
def stamp():
    d = .5; t = T(d); thump = np.sin(2 * np.pi * np.cumsum(95 - 50 * t / d) / SR) * dec(d, .14, .002)
    return norm(cat((0, thump), (0, hp(noise(.04), 1200) * dec(.04, .008) * .7), (0, bp(noise(.12), 300, 2500) * dec(.12, .03) * .5)))
def sparkle(): return norm(cat(*[(k * .055, np.sin(2 * np.pi * rng.uniform(2000, 4200) * T(.18)) * dec(.18, .05, .001)) for k in range(6)]), .6)
def count(d=.4): return norm(lp(cat(*[(k / 14 * d, sweep(600 * 2 ** (k / 10), 600 * 2 ** (k / 10), .035, 'sq') * dec(.035, .015, .001)) for k in range(14)]), 6000), .5)
def step(): return norm(lp(noise(.05), 260) * dec(.05, .012), .3)
GEN = {'tick': tick, 'pop': pop, 'blip': blip, 'click': click, 'type': type_, 'chime': chime, 'ding': ding, 'swish': swish, 'whoosh': whoosh, 'whoosh2': whoosh,
       'whip': whip, 'blocks': blocks, 'crt': crt, 'stamp': stamp, 'sparkle': sparkle, 'count': count, 'step': step}
LV = {'tick': -26, 'pop': -20, 'blip': -23, 'click': -14, 'type': -24, 'chime': -15, 'ding': -16, 'swish': -22, 'whoosh': -15, 'whoosh2': -17, 'whip': -17,
      'blocks': -22, 'crt': -14, 'stamp': -6, 'sparkle': -20, 'count': -22, 'step': -22}
sfx = np.zeros((N, 2))
for e in EV['events']:
    k = e['type']
    if k not in GEN:
        print('skip unknown cue', k); continue
    x = GEN[k](e['dur']) if k == 'count' and 'dur' in e else GEN[k]()
    g = LV[k] - (7 if e.get('soft') else 0) + e.get('gain', 0)
    i = int(e['t'] * SR); x = x[:max(0, N - i)] * db(g)
    sfx[i:i + len(x)] += x[:, None]

# ---------------------------------------------------------------- narration (speech RMS about -17 dBFS)
vo, sr = read_wav(ROOT / 'audio/vo_track.wav'); vo = resample(vo, sr, SR); vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
act = vo[np.abs(vo) > 1e-4]
if act.size:
    vo *= db(-17) / np.sqrt((act ** 2).mean())
vo = hp(vo, 70)

# ---------------------------------------------------------------- music bed
bed = np.zeros((N, 2))
if MUS.get('file'):
    m, msr = read_wav(ROOT / MUS['file'], mono=False); m = resample(m, msr, SR) if msr != SR else m
    if m.shape[1] == 1: m = np.repeat(m, 2, 1)
    secs = MUS.get('sections') or [[0, MUS.get('offset', 0)]]
    for j, (vt, mt) in enumerate(secs):
        end = secs[j + 1][0] if j + 1 < len(secs) else DUR
        n, i, src = int((end - vt) * SR), int(vt * SR), int(mt * SR)
        piece = np.zeros((n, 2)); filled = 0
        while filled < n:                                       # loop the track if it is shorter than the section
            chunk = m[src:src + n - filled] if filled == 0 else m[int(MUS.get('loopFrom', mt) * SR):][:n - filled]
            if not len(chunk): break
            piece[filled:filled + len(chunk)] = chunk; filled += len(chunk)
        fi, fo = int(.02 * SR), int((MUS.get('fade', 1.4) if j + 1 == len(secs) else .2) * SR)
        env = np.ones(n); env[:fi] = np.linspace(0, 1, fi); env[max(0, n - fo):] *= np.linspace(1, 0, min(fo, n))
        bed[i:i + n] += piece * env[:, None]
    blk = SR // 100; e = np.array([np.sqrt((vo[i:i + blk] ** 2).mean()) for i in range(0, N, blk)])
    on = np.clip((20 * np.log10(e + 1e-9) + 45) / 12, 0, 1); sm = np.zeros_like(on)
    for k in range(1, len(on)):
        sm[k] = sm[k - 1] + (on[k] - sm[k - 1]) * (.45 if on[k] > sm[k - 1] else .022)
    duck = np.repeat(1 - .7 * sm, blk)[:N]
    bed *= (duck * db(MUS.get('gain', -13)))[:, None]
    sfx *= (1 - .3 * np.repeat(sm, blk)[:N])[:, None]

mix = np.tanh((bed + sfx + vo[:, None]) * 1.1) / 1.1
write_wav(ROOT / 'audio/mix.wav', mix[:int(DUR * SR)], SR)
print('mix -> audio/mix.wav', f'{DUR:.2f}s', 'peak', round(float(np.abs(mix).max()), 3), '| music', 'yes' if MUS.get('file') else 'none')
