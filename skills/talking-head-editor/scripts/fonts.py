"""字体按需下载：清单在 assets/fonts/fonts.json（每款字体的发布地址、大小和 sha256），第一次用到时从字体发布方下载，
核对 sha256 后放进 ~/.cache/koubo/fonts/（KOUBO_HOME 可以换目录），授权原文一起复制到那里的 licenses/。
  python scripts/fonts.py fetch    一次下齐（约 80 MB）
  python scripts/fonts.py check    列出还缺哪些
kvlib 被导入时会自动补齐缺的字体，所以平时不用手动跑；没网的环境先在有网时跑一次 fetch。"""
import hashlib
import io
import json
import os
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
CATALOG = ASSETS / 'fonts.json'
FONTS = Path(os.environ.get('KOUBO_HOME', Path.home() / '.cache/koubo')).expanduser() / 'fonts'


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'talking-head-editor'})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))['fonts']


def missing():
    return [f for f in catalog() if not (FONTS / f['file']).exists() or (FONTS / f['file']).stat().st_size != f['bytes']]


def _fetch(f, archives):
    if f.get('member'):
        # 字体在发布方的压缩包里：同一个包只下一次，核对包和字体两层 sha256
        if f['url'] not in archives:
            data = _get(f['url'])
            if f.get('archive_sha256') and _sha256(data) != f['archive_sha256']:
                raise RuntimeError(f"{f['url']} 的 sha256 对不上，没有使用")
            archives[f['url']] = zipfile.ZipFile(io.BytesIO(data))
        data = archives[f['url']].read(f['member'])
    else:
        data = _get(f['url'])
    if _sha256(data) != f['sha256']:
        raise RuntimeError(f"{f['file']} 的 sha256 对不上，没有使用（来源 {f['url']}）")
    tmp = FONTS / (f['file'] + '.part')
    tmp.write_bytes(data)
    tmp.replace(FONTS / f['file'])
    lic = ASSETS / 'licenses' / f['license']
    (FONTS / 'licenses').mkdir(exist_ok=True)
    shutil.copyfile(lic, FONTS / 'licenses' / f['license'])


def ensure(quiet=False):
    """补齐缺的字体，返回字体目录。下载失败只提示不中断：渲染时会退回系统字体，样子会差一些。"""
    todo = missing()
    if not todo:
        return FONTS
    FONTS.mkdir(parents=True, exist_ok=True)
    if not quiet:
        mb = sum(f['bytes'] for f in todo) / 1e6
        print(f'第一次使用，下载 {len(todo)} 款字体（约 {mb:.0f} MB）到 {FONTS} ……', file=sys.stderr)
    archives, failed = {}, []
    for f in todo:
        try:
            _fetch(f, archives)
        except Exception as e:
            failed.append(f"{f['file']}：{e}")
    if failed:
        print('这些字体没下载成功，渲染会退回系统字体，有网时运行 python scripts/fonts.py fetch 重试：\n  '
              + '\n  '.join(failed), file=sys.stderr)
    return FONTS


def font(name):
    """某个字体文件的路径（缺就先下载）。"""
    if not (FONTS / name).exists():
        ensure()
    return FONTS / name


if __name__ == '__main__':
    cmd = sys.argv[1:] or ['']
    if cmd == ['fetch']:
        ensure()
        left = missing()
        print('字体都齐了：' + str(FONTS) if not left else f'还缺 {len(left)} 款，见上面的报错')
        sys.exit(1 if left else 0)
    elif cmd == ['check']:
        left = missing()
        print('字体都齐了' if not left else '缺：' + '、'.join(f['file'] for f in left))
        sys.exit(1 if left else 0)
    else:
        sys.exit(__doc__)
