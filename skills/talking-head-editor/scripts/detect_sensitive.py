"""敏感信息检测：在截图、录屏、口播画面和转写里找邮箱、手机号、身份证号、银行卡号、密钥、二维码、疑似姓名和地址。

只负责「找出来」，打不打码由用户决定（有些是用户故意展示的，比如自己的公众号二维码）。

用法：
  uv run --python 3.12 --with rapidocr-onnxruntime --with opencv-python python detect_sensitive.py 素材或目录... \
      [--transcript transcript.json] [--every 1.0] -o sensitive.json
  （已经 pip install rapidocr-onnxruntime opencv-python 的话直接 python 运行）

输出 sensitive.json：[{"id", "file", "t", "kind", "text", "box": [x, y, w, h]（相对画面宽高的比例）}]
视频按 --every 秒抽帧识别，同一位置同一内容会合并成一个时间段 t0~t1。
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from kvlib import probe, is_image, to_png, save_json

PATTERNS = [
    ('邮箱', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
    ('手机号', re.compile(r'(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}(?!\d)')),
    ('身份证号', re.compile(r'(?<![\dA-Za-z])\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?![\dA-Za-z])')),
    ('银行卡号', re.compile(r'(?<!\d)(?:\d[\s-]?){15,18}\d(?!\d)')),
    ('护照号', re.compile(r'(?<![A-Za-z0-9])[EGDSP]\d{8}(?![A-Za-z0-9])')),
    ('密钥', re.compile(r'(?:sk-[A-Za-z0-9_-]{16,}|sk_live_[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bap]-[A-Za-z0-9-]{10,}'
                     r'|AIza[0-9A-Za-z_-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+)')),
    ('座机号', re.compile(r'(?<!\d)0\d{2,3}-\d{7,8}(?!\d)')),
]
LABELS = [('姓名', re.compile(r'(?:姓名|联系人|收件人|收货人|户主|持卡人|申请人)[:：\s]*([一-龥·]{2,4})')),
          ('地址', re.compile(r'[一-龥]{2,}(?:省|市)[一-龥]{1,}(?:区|县)[一-龥\d]{2,}(?:路|街|道|号|弄|室|栋|楼)'))]


def luhn(num):
    d = [int(x) for x in re.sub(r'\D', '', num)][::-1]
    s = sum(x if i % 2 == 0 else (x * 2 - 9 if x * 2 > 9 else x * 2) for i, x in enumerate(d))
    return s % 10 == 0


def classify(text):
    hits = []
    for kind, pat in PATTERNS:
        for m in pat.finditer(text):
            v = m.group(0)
            if kind == '银行卡号' and not luhn(v):
                continue
            hits.append((kind, v))
    for kind, pat in LABELS:
        for m in pat.finditer(text):
            hits.append((kind, m.group(0)))
    return hits


def preview(v):
    """给用户看的打码预览，不在报告里原样复述敏感信息。"""
    v = v.strip()
    if len(v) <= 4:
        return v[0] + '*' * (len(v) - 1)
    return v[:3] + '*' * max(3, len(v) - 6) + v[-3:]


_ocr = None


def ocr(img_path):
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    res, _ = _ocr(img_path)
    return res or []


def qr_boxes(img_path):
    try:
        import cv2
        im = cv2.imread(img_path)
        ok, pts = cv2.QRCodeDetector().detectMulti(im)[:2] if im is not None else (False, None)
        if not ok or pts is None:
            return []
        h, w = im.shape[:2]
        out = []
        for p in pts:
            xs, ys = p[:, 0], p[:, 1]
            out.append([float(xs.min() / w), float(ys.min() / h), float((xs.max() - xs.min()) / w), float((ys.max() - ys.min()) / h)])
        return out
    except Exception:
        return []


def scan_image(path, w, h):
    found = []
    for box, text, conf in ocr(path):
        if conf < 0.5:
            continue
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        bx = [min(xs) / w, min(ys) / h, (max(xs) - min(xs)) / w, (max(ys) - min(ys)) / h]
        for kind, v in classify(text):
            # 只框住命中的那部分文字（按字符比例估算横向位置）
            i = text.find(v)
            if i >= 0 and len(text) > 0:
                x0 = bx[0] + bx[2] * i / len(text)
                ww = bx[2] * len(v) / len(text)
                bx2 = [x0, bx[1], ww, bx[3]]
            else:
                bx2 = bx
            found.append({'kind': kind, 'text': preview(v), 'box': [round(x, 4) for x in bx2]})
    for b in qr_boxes(path):
        found.append({'kind': '二维码', 'text': '（二维码）', 'box': [round(x, 4) for x in b]})
    return found


def scan_file(path, every, tmp):
    path = str(path)
    if is_image(path):
        src = to_png(path, tmp)
        from PIL import Image
        w, h = Image.open(src).size
        return [{'file': path, 't': None, **f} for f in scan_image(src, w, h)]
    info = probe(path)
    if not info['w']:
        return []
    res = []
    n = int(info['duration'] / every) + 1
    for k in range(n):
        t = round(k * every, 2)
        fp = f'{tmp}/frame_{k:05d}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', path, '-frames:v', '1', '-vf', 'scale=1280:-2,format=yuvj420p', fp],
                       capture_output=True)
        if not Path(fp).exists():
            continue
        from PIL import Image
        w, h = Image.open(fp).size
        for f in scan_image(fp, w, h):
            res.append({'file': path, 't': t, **f})
    # 合并：同类、同内容、位置相近的连续帧并成一段
    merged = []
    for r in res:
        last = next((m for m in reversed(merged) if m['kind'] == r['kind'] and m['text'] == r['text']
                     and abs(m['box'][0] - r['box'][0]) < 0.08 and abs(m['box'][1] - r['box'][1]) < 0.08
                     and r['t'] - m['t1'] <= every * 1.5), None)
        if last:
            last['t1'] = r['t']
            last['box'] = [min(last['box'][0], r['box'][0]), min(last['box'][1], r['box'][1]),
                           max(last['box'][2], r['box'][2]), max(last['box'][3], r['box'][3])]
        else:
            merged.append({**r, 't0': r['t'], 't1': r['t']})
    for m in merged:
        m['t0'] = max(0, m['t0'] - every / 2)
        m['t1'] = min(info['duration'], m['t1'] + every / 2)
        m.pop('t')
    return merged


def scan_transcript(path):
    data = json.load(open(path, encoding='utf-8'))
    out = []
    items = []
    if isinstance(data, dict) and 'files' in data:
        for f in data['files']:
            for isl in f['islands']:
                items.append((f['src'], isl['t0'], isl['text']))
    elif isinstance(data, list):  # lines.json
        for ln in data:
            items.append(('lines.json', ln['t0'], ln['text']))
    for src, t, text in items:
        for kind, v in classify(text):
            out.append({'file': src, 't0': t, 't1': t, 'kind': '口播里念出的' + kind, 'text': preview(v), 'box': None})
        if re.search(r'(?:[零一二三四五六七八九幺两]\s*){7,}|\d{7,}', text):
            out.append({'file': src, 't0': t, 't1': t, 'kind': '口播里念出的一串数字（可能是电话或卡号）', 'text': preview(text), 'box': None})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--transcript')
    ap.add_argument('--every', type=float, default=1.0, help='视频抽帧间隔秒数，滚动录屏建议 0.5')
    ap.add_argument('-o', '--out', default='sensitive.json')
    a = ap.parse_args()
    files = []
    for p in a.inputs:
        p = Path(p)
        if p.is_dir():
            files += sorted(x for x in p.rglob('*') if x.is_file() and not x.name.startswith('.'))
        else:
            files.append(p)
    tmp = tempfile.mkdtemp(prefix='kv_sens_')
    found = []
    for f in files:
        try:
            r = scan_file(f, a.every, tmp)
        except Exception as e:
            print('跳过', f, e)
            continue
        found += r
    if a.transcript:
        found += scan_transcript(a.transcript)
    for i, f in enumerate(found):
        f['id'] = i
    save_json(found, a.out)
    if not found:
        print('没有发现敏感信息')
        return
    print(f'发现 {len(found)} 处疑似敏感信息：')
    for f in found:
        when = '' if f.get('t0') is None else f"  {f['t0']:.1f}-{f['t1']:.1f}s"
        print(f"  [{f['id']}] {f['kind']}  {f['text']}  {Path(f['file']).name}{when}")


if __name__ == '__main__':
    main()
