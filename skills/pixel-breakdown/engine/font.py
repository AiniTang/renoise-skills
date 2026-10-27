"""Extract the glyphs this episode uses from the Fusion Pixel 12px BDF into font.js (bitmap, no anti-aliasing).
  python3 font.py fonts/fusion-pixel-12px-proportional-latin.bdf
Collects every character in episode.js plus printable ASCII and a few symbols; rerun after changing any on-screen text.
Characters the font lacks are drawn by the engine from a system font at 12 px."""
import json, sys
from common import ROOT

bdf = sys.argv[1]
need = set((ROOT / 'episode.js').read_text(encoding='utf-8')) | {chr(c) for c in range(32, 127)} | set('✓♥×·…—→←↑↓↻★？！，。：；、（）「」《》')
need = {c for c in need if c >= ' '}
g, cur, font = {}, None, {}
with open(bdf, encoding='utf-8') as f:
    for line in f:
        k = line.split()
        if not k:
            continue
        if k[0] in ('FONT_ASCENT', 'FONT_DESCENT'):
            font[k[0]] = int(k[1])
        elif k[0] == 'STARTCHAR':
            cur = {'rows': []}
        elif cur is None:
            continue
        elif k[0] == 'ENCODING':
            cur['ch'] = chr(int(k[1])) if int(k[1]) >= 0 else None
        elif k[0] == 'DWIDTH':
            cur['dx'] = int(k[1])
        elif k[0] == 'BBX':
            cur['bbx'] = list(map(int, k[1:5]))
        elif k[0] == 'BITMAP':
            cur['bm'] = True
        elif k[0] == 'ENDCHAR':
            if cur.get('ch') in need:
                w, h, xo, yo = cur['bbx']
                g[cur['ch']] = [cur['dx'], w, h, xo, yo, ''.join(r.ljust(((w + 7) // 8) * 2, '0') for r in cur['rows'])]
            cur = None
        elif cur.get('bm'):
            cur['rows'].append(k[0])
(ROOT / 'font.js').write_text('window.FONT=' + json.dumps({'ascent': font['FONT_ASCENT'], 'descent': font['FONT_DESCENT'], 'g': g}, ensure_ascii=False) + ';\n', encoding='utf-8')
missing = sorted(c for c in need - set(g) if not c.isspace())
print(len(g), 'glyphs -> font.js', '| drawn from a system font:', ''.join(missing[:60]) or 'none')
