"""人像抠像：口播任意一段按时间抠出人像透明度，结果缓存，同一段只抠一次。

模型用 RVM（Robust Video Matting，专门抠视频的模型）：头发丝能抠出来，前后帧连贯不闪。M4 上 CPU 每帧约 0.05 秒。
第一次用会把模型（15MB，官方发布页）下到 ~/.cache/koubo-matte/，透明度缓存也放这里（KOUBO_MATTE_CACHE 可改）。
依赖 onnxruntime：本机没装时自动用 `uv run --with onnxruntime` 临时装来跑，不用手动处理。

渲染时由 matte.py 按需调用，不用手动跑。命令行用法（单独导出一段带透明通道的人像，给剪映或别的软件用）：
  python person_matte.py aroll.mp4 --t0 3.2 --t1 6.0 -o mattes/m1.mov
"""
import argparse
import hashlib
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK text
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL_URL = 'https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx'
MODEL_SHA256 = '88d4531297118f595bf2fd60f6f566aec2e559393802d1f436c380f0cbbd2828'
CACHE = Path(os.environ.get('KOUBO_MATTE_CACHE', '~/.cache/koubo-matte')).expanduser()
PREROLL = 1.0   # 往前多抠 1 秒再开始记：模型要几帧「热身」，第一帧直接抠头顶会糊一块


def model_path():
    p = CACHE / 'rvm_mobilenetv3_fp32.onnx'
    if p.exists():
        return p
    CACHE.mkdir(parents=True, exist_ok=True)
    print('第一次抠像：下载 RVM 模型（15MB）…')
    tmp = p.with_suffix('.part')
    urllib.request.urlretrieve(MODEL_URL, tmp)
    if hashlib.sha256(tmp.read_bytes()).hexdigest() != MODEL_SHA256:
        tmp.unlink()
        raise SystemExit('抠像模型下载不完整（校验不对），重跑一次')
    tmp.rename(p)
    return p


def vf(W, H, FPS):
    """和 motion.read 一样的铺满裁切，抠出来的透明度和逐帧合成读到的画面逐像素对齐。"""
    return f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}'


def alpha_file(src, t0, dur, W, H, FPS):
    """这一段的透明度视频（灰度、无损，从第 round(t0×FPS) 帧起 max(1, round(dur×FPS)) 帧，素材不够长时只抠到素材结尾）。有缓存直接用。"""
    src = str(Path(src).resolve())
    s = os.stat(src)
    f0 = round(t0 * FPS)
    f1 = f0 + max(1, round(dur * FPS))
    key = hashlib.sha1(f'{src}|{s.st_size}|{int(s.st_mtime)}|{W}x{H}@{FPS}|{f0}-{f1}|rvm-mb3'.encode()).hexdigest()[:20]
    out = CACHE / 'alpha' / f'{key}.mkv'
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [src, str(f0), str(f1), str(W), str(H), str(FPS), str(out)]
    try:
        import onnxruntime  # noqa: F401
        compute(*args)
    except ImportError:
        subprocess.run(['uv', 'run', '-q', '--python', '3.12', '--with', 'onnxruntime', '--with', 'numpy', 'python', __file__, '_compute', *args],
                       check=True)
    return out


def compute(src, f0, f1, W, H, FPS, out):
    import onnxruntime as ort
    f0, f1, W, H, FPS = int(f0), int(f1), int(W), int(H), int(FPS)
    pre = min(f0, round(PREROLL * FPS))
    n = f1 - f0
    sess = ort.InferenceSession(str(model_path()), providers=['CPUExecutionProvider'])
    ratio = np.array([min(1.0, 480 / max(W, H))], np.float32)   # 模型内部缩到长边约 480 像素先找人，再回原尺寸细抠边缘
    rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4

    def run(fr):
        nonlocal rec
        x = fr.astype(np.float32).transpose(2, 0, 1)[None] / 255
        _, pha, *rec = sess.run(None, {'src': x, 'r1i': rec[0], 'r2i': rec[1], 'r3i': rec[2], 'r4i': rec[3], 'downsample_ratio': ratio})
        return (np.clip(pha[0, 0], 0, 1) * 255 + 0.5).astype(np.uint8)

    rd = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{(f0 - pre) / FPS:.4f}', '-i', src, '-vf', vf(W, H, FPS),
                           '-frames:v', str(pre + n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    wr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'ffv1', str(out) + '.tmp.mkv'], stdin=subprocess.PIPE)
    first, i = [], 0
    while True:
        buf = rd.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        if i == 0 and pre < FPS // 2:   # 开头没有 1 秒可以往前抠：先把前半秒过一遍热身，再从头正式抠
            first = [fr]
            for _ in range(FPS // 2 - 1):
                b2 = rd.stdout.read(W * H * 3)
                if len(b2) < W * H * 3:
                    break
                first.append(np.frombuffer(b2, np.uint8).reshape(H, W, 3))
            for x in first:
                run(x)
        for x in (first or [fr]):
            a = run(x)
            if i >= pre:
                wr.stdin.write(a.tobytes())
            i += 1
            if (i - pre) % 150 == 0 and i > pre:
                print(f'抠像 {i - pre}/{n} 帧')
        first = []
    rd.wait()
    wr.stdin.close()
    if wr.wait() or i <= pre:
        raise SystemExit(f'抠像失败：{src} 第 {f0} 帧起读不到画面')
    os.replace(str(out) + '.tmp.mkv', out)


def alphas(src, t0, dur, W, H, FPS):
    """逐帧透明度（0~1 的 H×W float32），正好 round(dur×FPS) 帧；素材不够长时停在最后一帧。"""
    n = max(1, round(dur * FPS))
    f = alpha_file(src, t0, dur, W, H, FPS)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(f), '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
    last = np.zeros((H, W), np.float32)
    got = 0
    while got < n:
        buf = p.stdout.read(W * H)
        if len(buf) < W * H:
            break
        last = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.float32) / 255
        got += 1
        yield last
    p.stdout.close()
    p.wait()
    for _ in range(n - got):
        yield last


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_compute':
        compute(*sys.argv[2:])
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--t0', type=float, required=True)
    ap.add_argument('--t1', type=float, required=True)
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import matte
    from kvlib import probe
    info = probe(a.video)
    W, H, FPS = info['w'], info['h'], round(info['fps'] or 30)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    matte.person_clip(a.video, a.t0, a.t1, W, H, FPS, a.out)
    print('人像抠像：', a.out)


if __name__ == '__main__':
    main()
