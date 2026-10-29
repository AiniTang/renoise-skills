"""公开可商用素材检索与下载（Pexels、Pixabay）。

两家都免费商用、不强制署名，但不能把未改动的素材单独转卖。需要免费的 API Key：
  Pexels：https://www.pexels.com/api/  → 环境变量 PEXELS_API_KEY
  Pixabay：https://pixabay.com/api/docs/ → 环境变量 PIXABAY_API_KEY
没有 Key 时告诉用户去注册（一两分钟），或改用 Renoise 生成 / 代码动画。

用法：
  python broll_search.py "city night traffic" --kind video --orientation portrait -n 5 -o broll/
  python broll_search.py "rocket launch" --kind video --min-dur 4 --download 2 -o broll/
关键词用英文搜效果好得多；先 --download 0 看候选列表（含预览图链接），选好再下载。
下载的文件旁边会生成同名 .json，记录来源链接和作者，方便在简介里注明出处。
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from kvlib import canvas_size


def get(url, headers=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'talking-head-editor/1.0', **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def pexels(q, kind, orientation, n, min_dur):
    key = os.environ.get('PEXELS_API_KEY')
    if not key:
        return []
    qs = urllib.parse.urlencode({'query': q, 'per_page': min(80, n * 3), 'orientation': orientation})
    if kind == 'video':
        data = get(f'https://api.pexels.com/videos/search?{qs}', {'Authorization': key})
        out = []
        for v in data.get('videos', []):
            if v.get('duration', 0) < min_dur:
                continue
            files = sorted([f for f in v['video_files'] if f.get('width')], key=lambda f: f['width'] * f['height'])
            best = next((f for f in files if min(f['width'], f['height']) >= 1080), files[-1] if files else None)
            if best:
                out.append({'site': 'pexels', 'id': v['id'], 'url': best['link'], 'w': best['width'], 'h': best['height'],
                            'duration': v['duration'], 'preview': v.get('image'), 'page': v.get('url'), 'author': v.get('user', {}).get('name')})
        return out[:n]
    data = get(f'https://api.pexels.com/v1/search?{qs}', {'Authorization': key})
    return [{'site': 'pexels', 'id': p['id'], 'url': p['src']['original'], 'w': p['width'], 'h': p['height'], 'preview': p['src']['medium'],
             'page': p['url'], 'author': p.get('photographer')} for p in data.get('photos', [])][:n]


def pixabay(q, kind, orientation, n, min_dur):
    key = os.environ.get('PIXABAY_API_KEY')
    if not key:
        return []
    params = {'key': key, 'q': q, 'per_page': max(3, min(200, n * 3)), 'safesearch': 'true'}
    if kind == 'video':
        data = get('https://pixabay.com/api/videos/?' + urllib.parse.urlencode(params))
        out = []
        for v in data.get('hits', []):
            if v.get('duration', 0) < min_dur:
                continue
            vids = v.get('videos', {})
            best = vids.get('large') if vids.get('large', {}).get('url') else vids.get('medium')
            if not best or not best.get('url'):
                continue
            w, h = best['width'], best['height']
            if (orientation == 'portrait' and w > h or orientation == 'landscape' and w < h
                    or orientation == 'square' and w != h):
                continue
            out.append({'site': 'pixabay', 'id': v['id'], 'url': best['url'], 'w': best['width'], 'h': best['height'],
                        'duration': v.get('duration'), 'preview': best.get('thumbnail'), 'page': v.get('pageURL'), 'author': v.get('user')})
        return out[:n]
    params['orientation'] = 'vertical' if orientation == 'portrait' else 'horizontal' if orientation == 'landscape' else 'all'
    data = get('https://pixabay.com/api/?' + urllib.parse.urlencode(params))
    return [{'site': 'pixabay', 'id': h['id'], 'url': h.get('largeImageURL'), 'w': h.get('imageWidth'), 'h': h.get('imageHeight'),
             'preview': h.get('webformatURL'), 'page': h.get('pageURL'), 'author': h.get('user')} for h in data.get('hits', [])][:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('query')
    ap.add_argument('--kind', default='video', choices=['video', 'photo'])
    ap.add_argument('--orientation', default=None, choices=['portrait', 'landscape', 'square'])
    ap.add_argument('-n', type=int, default=6)
    ap.add_argument('--min-dur', type=float, default=3)
    ap.add_argument('--download', type=int, default=0, help='下载前几个结果，0 只列出候选')
    ap.add_argument('--pick', type=int, nargs='*', help='按候选序号下载')
    ap.add_argument('-o', '--outdir', default='broll')
    ap.add_argument('--canvas', type=canvas_size, default=(1080, 1920), help='素材方向默认跟随画布 WxH')
    a = ap.parse_args()
    if not a.orientation:
        w, h = a.canvas
        a.orientation = 'landscape' if w > h else 'portrait' if h > w else 'square'
    if not os.environ.get('PEXELS_API_KEY') and not os.environ.get('PIXABAY_API_KEY'):
        raise SystemExit('没有素材库的 API Key：请设置 PEXELS_API_KEY 或 PIXABAY_API_KEY（都免费注册），或改用 Renoise 生成 / 代码动画')
    res = []
    for fn in (pexels, pixabay):
        try:
            res += fn(a.query, a.kind, a.orientation, a.n, a.min_dur)
        except Exception as e:
            print(fn.__name__, '检索失败：', e)
    for i, r in enumerate(res):
        print(f"[{i}] {r['site']} {r['w']}x{r['h']} {r.get('duration', '')}s  预览 {r['preview']}")
    pick = a.pick if a.pick else list(range(min(a.download, len(res))))
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    for i in pick:
        r = res[i]
        ext = Path(urllib.parse.urlparse(r['url']).path).suffix or ('.mp4' if a.kind == 'video' else '.jpg')
        out = Path(a.outdir) / f"{r['site']}_{r['id']}{ext}"
        req = urllib.request.Request(r['url'], headers={'User-Agent': 'talking-head-editor/1.0'})
        with urllib.request.urlopen(req, timeout=120) as resp, open(out, 'wb') as f:
            f.write(resp.read())
        Path(str(out) + '.json').write_text(json.dumps({**r, 'query': a.query}, ensure_ascii=False, indent=1), encoding='utf-8')
        print('已下载', out)


if __name__ == '__main__':
    main()
