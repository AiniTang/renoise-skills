"""口播转写：按静音切成语音岛，逐岛识别，输出逐字时间。

为什么逐岛识别：整段识别会把「说了半句又重来」的废话并进正文，粗剪时分不出哪遍是重录；
纯音乐或长静音段还容易让模型反复输出同一句幻觉（如「请不吝点赞订阅」）。逐岛识别两个问题都没有。

用法：
  python transcribe.py 口播1.mov 口播2.mov -o transcript.json [--prompt "专有名词词表"] [--backend auto|whispercpp|faster|openai]

输出 transcript.json：
  {"backend": "...", "files": [{"src": 路径, "duration": 秒, "islands": [
      {"id": "0-12", "t0": 起, "t1": 止, "text": "这一岛说的话", "chars": [["字", 起始秒], ...], "suspect": false}]}]}
suspect=true 表示疑似幻觉或识别失败，粗剪时人工看一眼。
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from kvlib import probe, save_json

HALLUCINATIONS = ['请不吝点赞', '订阅', '转发', '打赏支持', '明镜', '字幕志愿者', '中文字幕', '谢谢观看', '感谢观看', '本歌曲来自',
                  'CaptionCube', 'Amara']

WHISPER_CPP_MODELS = [os.environ.get('KV_WHISPER_CPP_MODEL', ''), '~/.cache/hyperframes/whisper/models/ggml-large-v3.bin',
                      '~/.cache/whisper/ggml-large-v3.bin', '~/.cache/whisper.cpp/ggml-large-v3.bin', '~/models/ggml-large-v3.bin']


def islands(wav, noise=-35, min_sil=0.25, min_len=0.18):
    """用 ffmpeg silencedetect 找出说话的片段 [(t0, t1)]。"""
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', wav, '-af', f'silencedetect=noise={noise}dB:d={min_sil}', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: (-?[\d.]+)', err)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
    dur = probe(wav)['duration']
    if len(en) < len(st):
        en.append(dur)
    res, prev = [], 0.0
    for a, b in zip(st, en):
        if a - prev >= min_len:
            res.append((round(max(0, prev), 3), round(a, 3)))
        prev = b
    if dur - prev >= min_len:
        res.append((round(prev, 3), round(dur, 3)))
    return res


def suspicious(text, length):
    t = text.strip()
    if not t:
        return True
    if any(h in t for h in HALLUCINATIONS):
        return True
    rate = len(re.sub(r'\s', '', t)) / max(length, 0.1)
    return rate > 12  # 一秒十几个字不可能，多半是幻觉


def spread_chars(text, t0, t1):
    """把一段文字的时间均匀分到每个字上（标点不占时间）。"""
    chars = [c for c in text if not c.isspace()]
    spoken = [c for c in chars if re.match(r'[\w一-鿿]', c)]
    n = max(len(spoken), 1)
    out, k = [], 0
    for c in chars:
        out.append([c, round(t0 + (t1 - t0) * k / n, 3)])
        if re.match(r'[\w一-鿿]', c):
            k += 1
    return out


# ---------------------------------------------------------------- 三种识别后端

def find_whispercpp():
    exe = shutil.which('whisper-cli') or shutil.which('whisper-cpp')
    if not exe:
        return None, None
    for m in WHISPER_CPP_MODELS:
        if m and Path(m).expanduser().exists():
            return exe, str(Path(m).expanduser())
    return None, None


def run_whispercpp(chunks, prompt, lang):
    exe, model = find_whispercpp()
    out = {}
    for i in range(0, len(chunks), 80):  # 一次进程处理多段，只加载一次模型
        batch = chunks[i:i + 80]
        cmd = [exe, '-m', model, '-l', lang, '-oj', '-mc', '0', '-t', str(os.cpu_count() or 4), '--prompt', prompt or '以下是普通话口播。']
        for c in batch:
            cmd += ['-f', c]
        subprocess.run(cmd, capture_output=True, text=True)
        for c in batch:
            js = c + '.json'
            segs = []
            if os.path.exists(js):
                data = json.load(open(js, encoding='utf-8', errors='replace'))
                for s in data.get('transcription', []):
                    segs.append((s['offsets']['from'] / 1000, s['offsets']['to'] / 1000, s['text']))
            out[c] = segs
    return out


def run_faster(chunks, prompt, lang, model_name):
    from faster_whisper import WhisperModel
    m = WhisperModel(model_name, compute_type='auto')
    out = {}
    for c in chunks:
        segs, _ = m.transcribe(c, language=lang, initial_prompt=prompt, condition_on_previous_text=False, word_timestamps=True, vad_filter=False)
        res = []
        for s in segs:
            if s.words:
                for w in s.words:
                    res.append((w.start, w.end, w.word))
            else:
                res.append((s.start, s.end, s.text))
        out[c] = res
    return out


def run_openai(chunks, prompt, lang, model_name):
    import whisper
    m = whisper.load_model(model_name)
    out = {}
    for c in chunks:
        r = m.transcribe(c, language=lang, initial_prompt=prompt, condition_on_previous_text=False, word_timestamps=True)
        res = []
        for s in r['segments']:
            for w in s.get('words', []) or []:
                res.append((w['start'], w['end'], w['word']))
            if not s.get('words'):
                res.append((s['start'], s['end'], s['text']))
        out[c] = res
    return out


def pick_backend(name):
    if name in ('auto', 'whispercpp') and find_whispercpp()[0]:
        return 'whispercpp'
    if name in ('auto', 'faster'):
        try:
            import faster_whisper  # noqa
            return 'faster'
        except ImportError:
            pass
    if name in ('auto', 'openai'):
        try:
            import whisper  # noqa
            return 'openai'
        except ImportError:
            pass
    raise SystemExit('没有可用的语音识别：pip install faster-whisper（推荐），或安装 whisper.cpp 并设置 KV_WHISPER_CPP_MODEL')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('-o', '--out', default='transcript.json')
    ap.add_argument('--prompt', default='', help='专有名词词表，提高识别准确率')
    ap.add_argument('--lang', default='zh')
    ap.add_argument('--backend', default='auto')
    ap.add_argument('--model', default=os.environ.get('KV_WHISPER_MODEL', 'medium'), help='faster/openai 后端的模型名')
    ap.add_argument('--noise', type=float, default=-35, help='静音阈值 dB，底噪大时调高到 -30')
    a = ap.parse_args()

    backend = pick_backend(a.backend)
    prompt = ('以下是普通话口播，使用简体中文。' + a.prompt).strip()
    tmp = tempfile.mkdtemp(prefix='kv_asr_')
    plan = []  # (文件序号, 岛序号, 起, 止, 切片路径)
    files = []
    for fi, f in enumerate(a.files):
        wav = f'{tmp}/f{fi}.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
        isl = islands(wav, noise=a.noise)
        files.append({'src': str(Path(f).resolve()), 'duration': probe(wav)['duration'], 'islands': []})
        for ii, (t0, t1) in enumerate(isl):
            s0, s1 = max(0, t0 - 0.08), t1 + 0.12
            c = f'{tmp}/f{fi}_{ii:04d}.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s0:.3f}', '-i', wav, '-t', f'{s1 - s0:.3f}', c], check=True)
            plan.append((fi, ii, t0, t1, s0, c))
        print(f'{f}: {len(isl)} 个语音岛')

    chunks = [p[5] for p in plan]
    if backend == 'whispercpp':
        res = run_whispercpp(chunks, prompt, a.lang)
    elif backend == 'faster':
        res = run_faster(chunks, prompt, a.lang, a.model)
    else:
        res = run_openai(chunks, prompt, a.lang, a.model)

    for fi, ii, t0, t1, s0, c in plan:
        segs = res.get(c, [])
        text = ''.join(s[2] for s in segs).strip()
        chars = []
        for st, en, tx in segs:
            chars += spread_chars(tx, s0 + st, s0 + en)
        files[fi]['islands'].append({'id': f'{fi}-{ii}', 't0': t0, 't1': t1, 'text': text, 'chars': chars,
                                     'suspect': suspicious(text, t1 - t0)})

    save_json({'backend': backend, 'files': files}, a.out)
    shutil.rmtree(tmp, ignore_errors=True)
    for f in files:
        print('==', f['src'])
        for x in f['islands']:
            flag = '  ⚠️' if x['suspect'] else ''
            print(f"  {x['id']:>6} {x['t0']:7.2f}-{x['t1']:7.2f}  {x['text']}{flag}")


if __name__ == '__main__':
    main()
