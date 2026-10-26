---
name: digital-human-koubo
description: 用数字人主播做口播视频：主播来自用户本人照片（或已授权的人）或 AI 生成的形象，先按内容推荐剪辑风格让用户选（网红花字竖屏口播 / 发布解读 / 保姆级教程 / 多主播多语言），套上 47 个包装组件（开场钩子、数字钉子、人身后的景深字、证据截图、地图路线、弹幕、投票、复盘板…），再写稿 → 按 15 秒切段 → Renoise 分段生成（先报价、用户确认才生成）→ 逐段回听 → 逐字对齐 → Remotion 出片。Use when the user asks for 数字人口播、口播视频、AI 主播讲解、数字人带货 / 解读 / 教程 / 种草视频、talking-head or AI presenter video, 加花字、加包装、文字放在人身后. 不用于：冒充真人、未经同意用他人的脸或声音。
license: MIT
compatibility: Needs a shell (the Renoise sandbox, or macOS / Linux / Windows) with Node.js 18+ (Remotion), Python 3.8+ with numpy, pillow, faster-whisper and rembg, and ffmpeg. Generation needs a Renoise connection (MCP). The Renoise sandbox has all of it preinstalled.
---

# 数字人口播

> 路径约定：`<skill>` 指本 SKILL.md 所在的目录，`scripts/`、`references/`、`templates/` 都在它下面；命令里的 `<skill>/scripts/…` 换成这个目录的绝对路径再执行。Windows 上把 `python3` 换成 `python`。

已验证的提示词、动作、语速和切段规则在 `persona.json`；剪辑风格在 `references/style-menu.md`。主播形象不随 skill 分发，每个工程登记在 `brief.json` 的 `hosts` 里。

## 红线
- 生成花用户的 Renoise credits：create_tasks 之前先用 estimate_cost 报「段数 · 秒数 · 预估 credits · 余额」，然后停下，等用户在对话里明确同意（宿主的工具授权弹窗不算）。先拍第 1 段给用户确认形象和音色，再批量。重拍也要先报价。
- 主播只用用户本人、已明确同意的人，或 AI 生成的形象；不用公众人物、名人或任何未授权的真人照片和声音。用户本人的形象只用在用户自己的片子里。
- 成片标「内容由 AI 数字人演绎」；场景、动物片段角上标「AI 生成」。
- 学头部博主只学结构和剪辑手法：不用真实创作者的脸、声音、布景和原句。
- 点名评价第三方产品的说法，要有出处或标「网友分析 / 个人体验」。展示素材只用用户自己的作品；带歌词字幕的片子不用。

## 在哪跑
- **Renoise sandbox**（有 `sandbox` 工具时）：远程 Linux，ffmpeg、Python 包、Node 都已装好，有外网。工程放 `~/projects/<yyyy-mm-dd-短名>`；超过 45 秒的命令（npm install、回听、渲染）用 background 跑。你看不到画面：抽帧和联系表用 `rn sheet` 出图后通过 image_paths 看。
- **用户本机 shell**：剪辑前跑 `python3 <skill>/scripts/doctor.py`，有的打 ✓，缺的给装法；系统软件让用户自己装，Python 包可以在用户同意后帮装。
- **都没有**：只做到写稿 + 生成，把各段视频和剪辑方案交给用户，说明这里剪不了。

## 流程

### 准备（每次新对话第一次用时做，有就一句带过）
1. **Renoise**：调 `get_account`。成功就说一句「Renoise 已连接，余额 X」；余额为 0 先告诉用户需要充值。工具不存在就停下，让用户先连上 Renoise（renoise.ai），装好后重开对话。
2. **模型**：先 `load_skill model-routing`（插件里是 model-routing skill）。默认链路是 Grok Video 1.5 参考图模式分段生成、自带配音（本 skill 的提示词和语速都按它实测）；要用用户自己的声音或单条超过 15 秒的长镜头，按 references/voice.md 换成「配音 → OmniHuman」链路。上限和参数以 `list_models` 为准。
3. **主播**：brief.json 里还没有 hosts 时，按 references/new-avatar.md 做：用户的照片走 request_upload / upload_files，或用图片模型生成一个 AI 主播。

### 0. 看内容 → 推荐风格 → 让用户选
按 `references/style-menu.md`：
1. 一行诊断（内容类型、有没有可展示的素材、适合的平台和时长）。
2. 推荐 2 个风格并说理由（每种风格的画面在 style-menu.md 里有文字描述）。
3. 一次问完：风格 · 比例和时长 · 花字强度（克制 / 标准 / 热闹）· 主播（用户本人 / AI 主播 / 两人接力 / 动物）。每题第一个选项是推荐项。有提问工具就用，没有就列编号。
4. 用户回「你定」就按推荐，并说一句按了什么。结果写进 `brief.json`，后面每一步按它来。

| 风格 | 比例 | 时长 | 剪辑实现 |
|---|---|---|---|
| B 网红花字口播 | 9:16 | 30–120 秒 | `templates/huazi-916`（edit.json 驱动，三档花字） |
| C 发布解读 | 16:9 | 30–90 秒 | 参考实现 `templates/reference/launch-169` |
| D 保姆级教程 | 16:9 | 3–8 分钟 | 参考实现 `templates/reference/tutorial-169` |
| E 多主播多语言 | 16:9 | 3–7 分钟 | 参考实现 `templates/reference/multihost-169` |

### 1. 写稿 → script.json
按选定风格的稿子写法（style-menu.md 里每种都有）。每段一句或两句，10 秒左右（约 40–55 字，Grok 中文约 5.4 字/秒），标 `shot`：`full`（全屏出镜）/ `pip`（画中画讲解）/ `vlog`（随意自拍口吻）/ `depth`（要做「文字在人身后」的段：中景、头顶两侧留背景）；多主播时标 `host`。英文缩写、网址写成好念的样子。外语段直接写目标语言的台词，标 `lang`。

### 2. 切段 + 报价
`python3 <skill>/scripts/build_tasks.py script.json tasks.json --brief brief.json --purpose "teaching a beginner tutorial step by step"`
→ 打印段数和各分辨率秒数。full 段 720p，pip 段 480p（画中画里看不出差别，便宜约四成）。把 tasks.json 交给 `estimate_cost` 报价，连同余额报给用户，等确认。

### 3. 生成
用 estimate_cost 返回的 task，每 10 个一批 create_tasks → wait_tasks。要进场景（直播间、门店、街景）时先用图片模型合成开场画面（人物参考图 + 场景描述，模型按 model-routing 选），把这张图当 Grok 的参考图。

### 4. 下载
`download_results` 拿到一条 curl 命令，在工程目录的 `gen/` 里跑；写 `clips.json`（`{段 id: "gen/文件名"}`）。本机离 Renoise CDN 远、下载很慢时，把链接整理成 `urls.txt`（每行 `<taskId>.<ext> <url>`）用 `python3 <skill>/scripts/rangedl.py`：分段并发、断点续传、下完解码校验。

### 5. 回听 + 抽帧 + 拼接
`python3 <skill>/scripts/assemble.py script.json clips.json --out 成片_完整版.mp4`：faster-whisper 逐段转写比对文稿、只保留到说完后 0.25 秒、拼接、loudnorm -16。准确率 < 85% 的段打 ⚠。
- 外语段在 script.json 里标 `lang_code`（en / ja / ko …）按语言转写。
- **每段抽 4 帧看一眼**（`rn sheet` 或 ffmpeg 抽帧）：Grok 横屏口播偶尔自己烧字幕（提示词写了也挡不住），有就重拍那段（先报价）。
- Grok 有时漏念开头的语气词：没影响意思就按实际口播改字幕，别为这个重拍。

### 6. 对齐 + 剪辑
`python3 <skill>/scripts/align.py script.json --out <工程>/src/tl.json` 出逐字时间轴，然后按 brief.json 的风格剪：
- **B 花字口播**：`python3 <skill>/scripts/new_edit.py huazi-916 <工程>` → 写 `src/edit.json`（关键词、表情、卡片、作品展示、号召，字段见 references/huazi.md）→ `python3 <skill>/scripts/check_edit.py <工程>/src` → 抽帧 → 渲染。
- **C / D / E**：`python3 <skill>/scripts/new_edit.py reference/<目录> <工程>`，换 tl.json，按段重写 Scene（templates/reference/README.md）。
- **包装（每种风格都做）**：按 `references/packaging-presets.json` 里这个风格的默认包装排——开场 30 秒按 open 顺序、正文保证 stimulus_every_s 秒内有一个新视觉事件、讲到 per_beat 里那类内容就用对应组件、recurring 全片挂着。组件写进 `pack` 数组（字段见 references/packaging.md），手法依据见 references/packaging-playbook.md。用户点名要的手法（「加地图」「开场加预告」「加弹幕」「节奏再快点」）在默认基础上加减。景深字（文字在人身后）要先跑 `scripts/cutout_video.py` 抠像，见 references/packaging.md。
- 表情用 Noto 动态 emoji：new_edit.py 已下好常用的一套，要别的用 `python3 <skill>/scripts/fetch_noto_emoji.py <工程> 🚀 🎯`；用了动态 emoji 就在片尾或简介里加一行「Animated emoji: Google Noto」。
- 声音：数字人视频轨一定 `muted`，人声单独铺一条；多段 Grok 原声用 `python3 <skill>/scripts/voicefx/unify.py <输出目录> <片段…>` 统一频谱 + 同一个小房间混响（复用旧段时加 `--ref 旧片段目录`，场景/动物片段加 `--scene`）。BGM 压在人声下约 20 dB；占位配乐可以换成用户有授权的曲子。
- 渲染：`npx remotion render src/index.ts <Composition> out/raw.mp4 --concurrency=6`，再 `ffmpeg -af loudnorm=I=-16:TP=-1.5:LRA=11` 出片（references/edit-styles.md）。
- 抽帧检查一定看过渡的中间帧和零间隔衔接处（上一条的尾巴会盖住下一条）；有 `rn qa` 就跑一遍格式检查。

### 7. 交付
在 sandbox 里：upload_files 上传成片，show_result 按 materialId 交付。在本机：给出成片路径。都附一句用了哪些模型、花了多少 credits，以及「内容由 AI 数字人演绎」标注在哪。

## 参考
- references/style-menu.md：四种风格、内容诊断、怎么问用户、brief.json
- references/new-avatar.md：登记主播（用户照片 / AI 生成）、多模型试拍
- references/voice.md：Grok 原声 vs 用户自己的声音（配音 → OmniHuman）
- references/packaging.md：47 个包装组件的用法和参数（pack 写法、9:16 自动适配）
- references/packaging-playbook.md：头部博主实测结论（节奏、开场公式、字幕、声音、号召、红线），完整报告在 references/research/
- references/packaging-presets.json：各风格的默认包装
- references/huazi.md：花字模板 edit.json 字段、九种卡片、三档强度、写法习惯
- references/edit-styles.md：各剪辑工程的入口文件、渲染和声音统一做法
- persona.json：提示词模板（自拍 / 棚拍）、动作库、语速、多语言实测
