#!/usr/bin/env python3
"""渲染：起一个本地静态服务器（工作区根目录），再调用 <ws>/cine/tools/ 里的录制 / 混音工具。
  python3 render.py stills <期号> <输出.png> <时间…> [--cols 4] [--w 480]   接触表；时间写秒（12.5）或旁白位置（B07.ring、B03@三千、B05+1.2）
  python3 render.py film <期号> [--title 片名] [--poster 秒] [--from-step clips|record|finish|deliver]
      clips（裁案例片段）→ record（逐帧录 1080p60 画面）→ finish（代码音效 + BGM + 混音 + 合成）→ deliver（交付版 + 封面）
      交付：<ws>/out/<期号>_<片名>.mp4（H.264 CRF 23，码率封顶 6M）+ <ws>/out/<期号>_<片名>.jpg（封面帧）
  python3 render.py audio <期号>        只重做混音（改了音效 / BGM 时）
  python3 render.py retail <期号> <拍号>  只重录某一拍以后的画面，接回 picture.mp4
同一工作区同一时间只能有一个 film 渲染（锁文件 <ws>/cine/.render.lock）：两路录制会写坏同一个 picture.mp4。
Linux / Windows 上没有 GPU 时 WebGL 走 SwiftShader 软件渲染，比 macOS 慢几倍，属正常。"""
import functools
import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time

from vk import arg, workspace


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    handler = functools.partial(Quiet, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, str(srv.server_address[1])


def tool(ws, name, *args, log=None):
    cmd = [sys.executable, str(ws / "cine/tools" / name), *args]
    if log is None:
        subprocess.run(cmd, check=True, cwd=ws / "cine/tools")
        return
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, cwd=ws / "cine/tools", stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        tail = open(log, encoding="utf-8", errors="replace").read().splitlines()[-15:]
        sys.exit(f"{name} 失败（日志 {log}）：\n" + "\n".join(tail))


def deliver(ws, n, title, poster):
    src = ws / "lessons" / n / "build" / f"lesson{n}.mp4"
    out = ws / "out"
    out.mkdir(exist_ok=True)
    name = f"{n}_{title}" if title else n
    mp4, jpg = out / f"{name}.mp4", out / f"{name}.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "6M",
                    "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(mp4)], check=True)   # 粒子满屏时码率会飙到 20M+，封顶 6M
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(poster), "-i", str(src), "-frames:v", "1", "-q:v", "2", str(jpg)], check=True)
    print(f"交付 → {mp4}\n封面帧 → {jpg}")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("stills", "film", "audio", "retail"):
        sys.exit(__doc__)
    cmd, n = sys.argv[1], sys.argv[2]
    ws = workspace()
    if not (ws / "cine/engine/core.js").exists():
        sys.exit(f"{ws} 里没有引擎：先跑 new_film.py（或用 --ws 指到工作区）")
    srv, port = serve(ws)
    try:
        if cmd == "stills":
            rest = [a for a in sys.argv[3:] if a != "--ws" and a != arg("--ws")]
            tool(ws, "stills.py", n, *rest, "--port", port)
        elif cmd == "audio":
            tool(ws, "finish.py", n, "--port", port, "--audio-only")
        elif cmd == "retail":
            tool(ws, "retail.py", n, sys.argv[3], "--port", port)
        else:
            lock = ws / "cine/.render.lock"
            if lock.exists() and time.time() - lock.stat().st_mtime < 6 * 3600:
                sys.exit(f"已有渲染在跑（{lock.read_text(encoding='utf-8').strip()}）。等它结束；确定没有在跑就删掉 {lock}")
            lock.write_text(f"第 {n} 期，pid {os.getpid()}，{time.strftime('%H:%M')} 开始", encoding="utf-8")
            try:
                steps = ["clips", "record", "finish", "deliver"]
                start = steps.index(arg("--from-step", "clips"))
                B = ws / "lessons" / n / "build"
                B.mkdir(parents=True, exist_ok=True)
                for step in steps[start:]:
                    t0 = time.time()
                    print(f"== {time.strftime('%H:%M')} {step}", flush=True)
                    if step == "deliver":
                        deliver(ws, n, arg("--title", ""), arg("--poster", "3"))
                    else:
                        tool(ws, f"{step}.py", n, "--port", port, log=B / f"{step}.log")
                        print("   " + (open(B / f"{step}.log", encoding="utf-8", errors="replace").read().strip().splitlines() or [""])[-1])
                    print(f"   {time.time() - t0:.0f}s", flush=True)
            finally:
                lock.unlink(missing_ok=True)
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
