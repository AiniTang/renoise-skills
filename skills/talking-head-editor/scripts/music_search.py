"""从公开免版权曲库检索、下载配乐和音效（不用 AI 生成，不需要密钥）。

来源和授权：
  mixkit       Mixkit Free License：可商用、不用署名；不能把曲子单独转卖或打包分发。曲风多、现代感强，首选。
  incompetech  Kevin MacLeod，CC BY 4.0：可商用，但必须在视频简介里署名（脚本会写进 credits.json）。
               1400 多首，每首标了 BPM 和情绪，按节奏挑歌方便。

用法：
  python music_search.py music --genre hip-hop                    列出 Mixkit 某个曲风的曲子
  python music_search.py music --source incompetech --feel "Bright, Driving" --bpm 90-120 --max-min 4
  python music_search.py sfx whoosh                               列出 Mixkit 的「嗖」类音效
  加 --download 1 3 -o bgm/   下载列表里第 1、3 首到 bgm/（音效用 -o sfx/），授权信息追加到 <目录>/credits.json

Mixkit 常用曲风（--genre）：hip-hop、chillout、downtempo、corporate-music、electronic、deep-house、
  future-bass、funk、cinematic、film-score、ambient、indie-pop、jazz、breakbeat、edm、dance-pop
常用音效（sfx 的类别）：whoosh、transition、swoosh、impact、boom、bass、pop、click、camera、
  typing、notification、bell、cinematic、glitch、rise
"""
import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import sys

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) talking-head-editor'}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def iso_dur(s):
    m = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', s or '')
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0) if m else 0


def mixkit_music(genre):
    url = f'https://mixkit.co/free-stock-music/{genre}/'
    h = get(url).decode('utf-8', 'ignore')
    out = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            d = json.loads(block)
        except json.JSONDecodeError:
            continue
        for g in d.get('@graph', []):
            if g.get('@type') == 'ItemList':
                for it in g['itemListElement']:
                    out.append({'source': 'mixkit', 'title': it.get('name'), 'artist': it.get('byArtist'), 'genre': it.get('genre'),
                                'seconds': iso_dur(it.get('duration')), 'url': it.get('url'),
                                'license': 'Mixkit Stock Music Free License（可商用，不用署名）', 'license_url': it.get('license')})
    return out


def mixkit_sfx(category):
    h = get(f'https://mixkit.co/free-sound-effects/{category}/').decode('utf-8', 'ignore')
    ids = re.findall(r'active_storage/sfx/(\d+)/\1-preview\.mp3', h)
    titles = re.findall(r'item-grid-card__title">\s*([^<]+?)\s*<', h)
    return [{'source': 'mixkit', 'title': t, 'url': f'https://assets.mixkit.co/active_storage/sfx/{i}/{i}.wav',
             'license': 'Mixkit Sound Effects Free License（可商用，不用署名）', 'license_url': 'https://mixkit.co/license/#sfxFree'}
            for i, t in zip(ids, titles)]


def incompetech(feel='', genre='', bpm=None, max_min=None):
    d = json.loads(get('https://incompetech.com/music/royalty-free/pieces.json'))
    want = [w.strip().lower() for w in feel.split(',') if w.strip()]
    out = []
    for p in d:
        f = (p.get('feel') or '').lower()
        if want and not all(w in f for w in want):
            continue
        if genre and genre.lower() not in json.dumps(p, ensure_ascii=False).lower():
            continue
        try:
            b = int(p.get('bpm') or 0)
        except ValueError:
            b = 0
        if bpm and not (bpm[0] <= b <= bpm[1]):
            continue
        mm, ss = (p.get('length') or '0:0:0').split(':')[-2:]
        sec = int(mm) * 60 + int(ss)
        if max_min and sec > max_min * 60:
            continue
        out.append({'source': 'incompetech', 'title': p['title'], 'artist': 'Kevin MacLeod', 'bpm': b, 'feel': p.get('feel'),
                    'instruments': p.get('instruments'), 'seconds': sec,
                    'url': 'https://incompetech.com/music/royalty-free/mp3-royaltyfree/' + urllib.parse.quote(p['filename']),
                    'license': 'CC BY 4.0（必须署名）',
                    'credit': f"\"{p['title']}\" Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['music', 'sfx'])
    ap.add_argument('category', nargs='?', help='sfx 的类别，如 whoosh')
    ap.add_argument('--source', default='mixkit', choices=['mixkit', 'incompetech'])
    ap.add_argument('--genre')
    ap.add_argument('--feel', default='')
    ap.add_argument('--bpm', help='如 90-120')
    ap.add_argument('--max-min', type=float)
    ap.add_argument('--download', nargs='*', type=int, help='下载列表里的第几项（从 1 数）')
    ap.add_argument('-o', '--outdir', default='.')
    a = ap.parse_args()

    if a.kind == 'sfx':
        items = mixkit_sfx(a.category or 'whoosh')
    elif a.source == 'incompetech':
        bpm = tuple(int(x) for x in a.bpm.split('-')) if a.bpm else None
        items = incompetech(a.feel, a.genre or '', bpm, a.max_min)
    else:
        items = mixkit_music(a.genre or 'hip-hop')
        if a.max_min:
            items = [x for x in items if x['seconds'] <= a.max_min * 60]

    if a.download is None:
        for n, x in enumerate(items, 1):
            extra = ' · '.join(str(x[k]) for k in ('genre', 'bpm', 'feel') if x.get(k))
            print(f"{n:3d}. {x['title']}  {x.get('seconds', '?')}s  {extra}")
        return
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    cred_path = out / 'credits.json'
    credits = json.loads(cred_path.read_text(encoding='utf-8')) if cred_path.exists() else []
    for n in a.download:
        x = items[n - 1]
        ext = Path(urllib.parse.urlparse(x['url']).path).suffix or '.mp3'
        name = re.sub(r'[^\w一-鿿-]+', '_', x['title']).strip('_') + ext
        (out / name).write_bytes(get(x['url']))
        credits.append({**x, 'file': name})
        print('已下载', out / name, '·', x['license'])
    cred_path.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
