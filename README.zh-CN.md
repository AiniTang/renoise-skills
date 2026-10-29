# Renoise Skills

[English](README.md) · **简体中文**

用 AI agent 做视频的生产级 skill，遵循开放的 [Agent Skills](https://agentskills.io) 标准。每个 skill 是一个文件夹，里面有 `SKILL.md`，以及它用到的参考文档、脚本和模板。同一个 skill 在 Claude Code、Codex、Cursor、Gemini CLI，以及任何支持 Agent Skills 的 agent 里都能用。

| Skill | 能做什么 |
|---|---|
| [`promo-video`](skills/promo-video/SKILL.md) | 用 Remotion 渲染产品片、品牌片和发布片。模板片由分镜驱动；电影级片子加上 3D、真实产品界面演示、动效设计和卡拍配乐。也能做作品合集和单形状 UI 动效循环片。交给客户前，会先过一遍细节审片和交付检查。 |
| [`digital-human-koubo`](skills/digital-human-koubo/SKILL.md) | 数字人口播：用户本人照片或 AI 生成的主播，稿子按 15 秒切段在 Renoise 生成（先报价、确认后才生成），faster-whisper 逐段回听、逐字对齐，再用 Remotion 按四种风格（竖屏花字口播 / 发布解读 / 保姆级教程 / 多主播多语言）和 47 个包装组件出片。改编自 [andyhuo520/digital-human-koubo](https://github.com/andyhuo520/digital-human-koubo)（MIT）。 |
| [`pixel-breakdown`](skills/pixel-breakdown/SKILL.md) | 像素风拆解视频（16:9，60–90 秒），讲一条爆款原片和它的 AI 复刻：两片同步对比、实测硬切和转场的像素图解、带报价卡和实时进度的模拟 agent 对话、成片和结尾。配音和配乐在 Renoise 生成（先报价、确认后才生成），faster-whisper 逐字对齐；每一帧由确定性的画布引擎在无头 Chromium 里绘制，配芯片音效，另出 3:4 封面。 |
| [`vibe-knowledge`](skills/vibe-knowledge/SKILL.md) | 精品知识短片（45 秒～5 分钟，16:9），屏幕上每句话都有出处：从爆款知识视频反推的 6 种脚本母版、事实清单、Renoise 配音（先报价、确认后才生成）+ faster-whisper 逐字对齐，再用代码成片引擎在无头 Chromium 里逐帧画出 44 套风格（8 个家族：手写 SVG 分层插画、粒子、数据组件、默认 BGM、代码音效）。增强档只在代码做不好的镜头用 Renoise 配图、动态镜头和音效。OCR 回读屏幕文字对照事实清单质检。 |
| [`talking-head-editor`](skills/talking-head-editor/SKILL.md) | 口播剪辑：把对着镜头说话的素材（真人拍的，或在 Renoise 生成的数字人口播）剪成竖屏或横屏成片，也能出剪映草稿。素材检查、转写、去重录和气口、逐句剪辑方案、找或做 B-roll，再从 212 个包装手法里按内容自动搭配（大字、信息卡片、抠像、画中画、转场），配上对准画面的代码音效和免版权配乐，敏感信息打码。高级感（默认）和综艺感两种风格。生成 B-roll 和数字人口播先报价、确认后才生成。 |

## 安装

[`skills`](https://github.com/vercel-labs/skills) 安装器会把 skill 放到每个 agent 读取的位置：本体只在标准目录 `.agents/skills/` 里放一份，对于读取自己专属目录的 agent（Claude Code 读 `.claude/skills/`），再建一个链接指过去。

```sh
npx skills add renoise-ai/renoise-skills                                   # 交互式选择 skill 和 agent
npx skills add renoise-ai/renoise-skills -s promo-video -a claude-code -a codex -y
npx skills add renoise-ai/renoise-skills -s promo-video -g -y              # 装到用户级，而不是当前项目
```

也可以手动安装，把 `skills/promo-video/` 复制到 agent 的 skill 目录：

- Codex 等遵循标准的 agent：项目里的 `.agents/skills/`，或 `~/.agents/skills/`。
- Claude Code：项目里的 `.claude/skills/`，或 `~/.claude/skills/`。

## promo-video 的运行依赖

macOS、Linux、Windows 都能用：skill 的脚本都是 Python，不需要 bash。在 Windows 上，skill 里写 `python3` 的地方用 `python`（或 `py -3`）。

- **Node.js 18+**：Remotion 负责渲染画面和混音。找不到 Node 时，`setup_project.py` 会下载一个便携版。
- **ffmpeg 7+**（需要带 libass）：
  - macOS：`brew install ffmpeg-full && export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"`
  - Debian / Ubuntu：`apt install ffmpeg`
  - Windows：`winget install Gyan.FFmpeg`（full 版），装完新开一个终端
- **[`rn`](https://github.com/renoise-ai/renoise-kit)**：负责每次渲染之后的编码收尾、交付检查和审计。用 `uv tool install "renoise-kit[all]"` 或 `pipx install "renoise-kit[all]"` 安装。
- **Python 3.8+ 和 numpy**：skill 自带的脚本要用。
- **可选：生成 AI 素材**。生成关键帧和图生视频需要接入 [Renoise](https://renoise.ai)，各 agent 的接入方式见 [renoise-plugins-official](https://github.com/renoise-ai/renoise-plugins-official)。

音乐文件不随仓库分发。skill 里的曲库目录记录了每首 Mixkit 曲子的下载地址和校验值，`pick_music.py` 第一次用到某首时再下载；字体也是同样的处理方式。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## digital-human-koubo 的运行依赖

需要一个 shell：Renoise sandbox（下面的都已预装），或 macOS、Linux、Windows。脚本都是 Python，`scripts/doctor.py` 会列出缺什么。

- **接入 Renoise**（MCP），用来生成主播口播。
- **Node.js 18+**（Remotion）和 **ffmpeg**。
- **Python 3.8+**，装 `numpy`、`pillow`、`faster-whisper`，以及 `rembg`（只有「文字在人身后」的镜头要用）。

skill 不带任何主播形象和声音：每个工程在 `brief.json` 里登记自己的主播。

## pixel-breakdown 的运行依赖

需要一个 shell：Renoise sandbox（下面的都已预装），或 macOS、Linux、Windows。脚本都是 Python，`scripts/doctor.py` 会列出缺什么，`scripts/demo.py` 能不花钱渲染一期演示。

- **接入 Renoise**（MCP），用来生成配音、配乐和可选的主持人像素头像。
- **ffmpeg**：探测、转码和成片编码。
- **Python 3.8+**，装 `numpy`、`scipy`、`pillow`、`playwright`（以及它的 Chromium：`python -m playwright install chromium`）和 `faster-whisper`。

skill 不带任何素材、主持人、声音和品牌：每一期都用用户自己的。像素字体（Fusion Pixel，SIL OFL 1.1）第一次用到时下载，并核对 sha256。

## vibe-knowledge 的运行依赖

一个能跑命令的 shell：Renoise sandbox，或 macOS、Linux、Windows。脚本都是 Python；`scripts/doctor.py` 检查缺什么，`scripts/demo.py`
做一条不花积分的 10 秒演示期。

- **Renoise 连接**（MCP）：配音；增强档的配图、动态镜头和音效。
- **ffmpeg**：探测、混音、成片编码。
- **Python 3.8+**，装 `numpy`、`scipy`、`pillow`、`playwright`（再装它的 Chromium：`python -m playwright install chromium`）和
  `faster-whisper`。可选：`rapidocr_onnxruntime`（回读屏幕文字核对事实）、`rembg`（生图拆层）。

引擎字体（SIL OFL 1.1）第一次用时下载并核对 sha256；earshot 代码音效库（MIT）按需装进独立环境。默认 BGM 随 skill 提供。不带任何音色、主播或素材。

## talking-head-editor 的运行依赖

需要一个 shell：Renoise sandbox，或 macOS、Linux、Windows。脚本都是 Python，`scripts/doctor.py` 会列出缺什么，`evals/smoke.py` 能用合成素材不花钱渲染一条 8 秒的测试成片。

- **ffmpeg**（需要带 libass，压字幕要用）。
- **Python 3.10+**，装 `pillow`、`numpy`、`opencv-python-headless`、`faster-whisper`（`pip install -r requirements.txt`）。可选：`jieba`（字幕断句更准）、`pyJianYingDraft`（出剪映草稿）、`pypinyin`（拼音标注）、`uv`（抠像、文字识别、配乐节拍分析的依赖按需临时装）。
- **可选：接入 Renoise**（MCP），用来生成 B-roll 和数字人口播，或者把整个剪辑放到 Renoise sandbox 里跑。

27 款字体（SIL OFL 1.1）第一次用到时从发布方下载，并核对 sha256；earshot 代码音效库（MIT）按需装进独立环境（`python scripts/setup_earshot.py install`）；配乐和 Mixkit 音效选中时再下载。skill 不带任何素材、主播和声音。

## 目录结构

```text
skills/
  promo-video/
    SKILL.md         agent 加载的主说明
    references/      按需阅读的参考：风格、运镜、字体、配乐、细节审片……
    scripts/         建工程、渲染、选曲、字体、文字检查、旁白
    templates/       Remotion 工程模板和示例片
    assets/          音效，以及曲库目录和字体目录
```

## 许可

[MIT](LICENSE)。第三方内容，以及哪些内容是按需下载、不随仓库分发的，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
