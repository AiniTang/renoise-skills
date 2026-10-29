"""读音频给 librosa 分析用：librosa 读不了的格式（m4a、mp4、扩展名和内容不符的文件，比如剪映缓存里的曲子）先用 ffmpeg 转成 wav。"""
import subprocess
import tempfile

import librosa


def load_audio(path, sr=22050, duration=None):
    try:
        return librosa.load(path, sr=sr, mono=True, duration=duration)
    except Exception:
        with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-ac', '1', '-ar', str(sr), tmp.name], check=True)
            return librosa.load(tmp.name, sr=sr, mono=True, duration=duration)
