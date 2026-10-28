"""cine 工具共用：启动无头 Chromium（WebGL 出图）。
CINE_CHROME（或 CHROME）环境变量指定浏览器；否则交给 Playwright 自带的 Chromium（python -m playwright install chromium）。
macOS 走 Metal；Linux / Windows 没有可用 GPU 时用 SwiftShader 软件渲染（慢一些，结果一样）。"""
import os
import sys

if sys.platform == "darwin":
    GPU = ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"]
else:
    GPU = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def launch(p):
    exe = os.environ.get("CINE_CHROME") or os.environ.get("CHROME")
    kw = {"args": GPU, "headless": True}
    if exe:
        kw["executable_path"] = exe
    return p.chromium.launch(**kw)
