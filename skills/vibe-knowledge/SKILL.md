---
name: vibe-knowledge
description: 精品知识短片工作室：一个知识点 → 一条 45 秒～5 分钟、有旁白、每句有出处的知识短片（抖音 / B 站 / 视频号知识区，16:9）。从 15 条爆款反推出的 6 种脚本母版（猜谜概念片、两难选择片、痛点原理片、一条主线片、闯关片、六面轮转片）→ 带出处的事实清单 → 旁白稿 + 对抗审查 → Renoise 配音（用户本人或授权的音色参照，faster-whisper 逐字对齐）→ 44 套风格（8 个家族）× 两档画面：基础档画面全代码（手写 SVG 分层插画、粒子、数据组件、默认 BGM、earshot 代码音效），增强档按镜头挑用 Renoise 配图 / 动态镜头 / 音效（先报价、用户确认才生成）→ cine 代码成片 1080p60 逐帧渲染 → OCR 回读质检 → 发布包。Use when the user asks for 知识短片、知识科普视频、把一个概念做成知识视频、一口气讲清楚某个原理、如果你活在古代那种历史科普、冷知识视频、Vibe知识大赏, or a narrated explainer short with sources. 不用于：系列课程、财经口播、品牌宣传片、数字人出镜口播。
license: MIT
compatibility: Needs a shell (the Renoise sandbox, or macOS / Linux / Windows) with Python 3.8+ (numpy, scipy, pillow, playwright with Chromium, faster-whisper) and ffmpeg; rapidocr_onnxruntime and rembg are optional. scripts/doctor.py checks them. Voice and the enhanced tier need a Renoise connection (MCP).
---

# 精品知识短片工作室

> 路径约定：`<skill>` 指本 SKILL.md 所在的目录，命令里的 `scripts/…` 换成 `<skill>/scripts/…` 的绝对路径再执行。Windows 上把 `python3` 换成 `python`。所有脚本都接受 `--ws <工作区>`（默认环境变量 `VK_WS`，否则 `~/vibe-knowledge`）。

一期 = 一个知识点 → 一条有旁白的精品短片（默认 16:9 1080p60）。**时长由用户定**：先按复杂度给四档建议（速览 / 精讲 / 标准 / 深挖），每档写清能讲多细、要砍什么（references/13-duration.md）。

一期 = **母版 × 风格 × 手法（≤2）× 档位**：
- **6 种脚本母版**（讲法，references/01-templates.md）。
- **风格库**（长相 + 讲法，`styles/`）：44 套、8 个家族（东方、暗场概念、明亮流行、印刷与纸、图解与设计、剪辑与纪实、电影感、游戏），每套有 STYLE.md 和风格图；敦煌壁画、青花、木刻、半调拼贴、长卷、铜版博物是增强档风格（每段约 2 张生图）。风格可以用库里的、改成自己的、或从空白做（references/09-style-studio.md）。
- **知识片组件 know.js**（references/07-kit.md）和 **cine 代码成片引擎**（references/16-cine.md）。
- **两档**（references/08-tiers.md）：基础档画面全代码（手写 SVG 分层插画 + 粒子 / 3D + 数据组件 + 默认 BGM + earshot 代码音效）；增强档只把代码做不好的镜头（写实场景、最需要被记住的 1–3 个时刻、真实运动）交给 Renoise。同一份 film.js 两档通用（`ENH` 开关）。

## 红线

- **没出处不上屏**：数字、人名、年份、引文全部进 facts.md（T1/T2/T3 分级、原文摘录）；示意画面标明；分歧两说并列。
- **花钱先确认**：配音、配图、视频、音效，生成前把提示词、模型、参照素材、数量、estimate_cost 总价和余额列给用户，**用户在对话里明确同意**才 create_tasks；宿主的工具授权弹窗不算，之前说过「直接生成」也不算；改了任何一项就重新报价。
- **声音和肖像**：音色参照只用用户本人或明确授权的声音；不模仿真实博主、名人的声音、脸、布景和原句（对标作品只学结构和手法）。不生成在世真人的脸；历史人物写「造型为示意」；AI 画面角标「AI 示意图」（plate、vclip 默认带）。
- 不把用户的私人素材传给 Renoise，除非用户明确要用。

## 在哪跑

一个能跑命令的 shell：Renoise sandbox 或用户本机（macOS / Linux / Windows）。开工前跑 `python3 scripts/doctor.py`，缺什么按它说的装。第一次用、或者用户说「先看看能做什么」：
- `python3 scripts/welcome.py`：在工作区生成「风格图鉴」网页（`gallery/index.html`，本机加 `--open` 打开），在对话里用 5–6 句话介绍：母版 × 风格 × 档位、8 个家族各举一两套、三种开口方式，最后问「想先做哪个选题？」。
- `python3 scripts/demo.py`：不花积分的约 10 秒演示期，检查引擎、渲染和质检都正常。

## 流水线（三个确认点）

| 段 | 做什么 | 产出 |
|---|---|---|
| ① 选题 | 三问：能不能让人 3 秒内先猜 / 先选？有没有贯穿道具？有没有反转？给用户 3–5 个候选 + 推荐母版 | 选题 |
| **确认 1** | 一次问完：选题、母版、**时长**（`scripts/duration.py` 按复杂度给四档，推荐档排第一；用户选的档跟复杂度差两级以上要提醒）、**风格**（`scripts/recommend.py "<选题>"` 出 3 套，推荐第一排第一、附风格图和理由；用户点名了就跳过）、**档位**（基础 / 增强轻 / 标准 / 旗舰）、**音色**（用户自己的录音 / 按描述配） | |
| ② 查 | 事实清单（T1/T2/T3 分级、原文摘录、用在哪拍） | `facts.md` |
| ③ 写 | `scripts/new_film.py <期号> --template A --title "…"` 建好这一期 → 按母版骨架写旁白（字数上限见骨架 `_guide`）→ 子 agent 对抗审查（钩子、出处、字数）→ 改 | `narration.json` |
| ④ 分镜 / 资产单 | 每拍画面分镜（哪些镜头代码做、哪些增强）；配音按 `voice.py plan` 切 take；增强档写 assets.json | `voice_plan.json`、`assets.json` |
| **确认 2** | 用户看旁白稿 + 分镜 + 一张报价（配音 take + 增强镜头，estimate_cost 总价和余额），明确同意后才生成 | |
| ⑤ 配音 | 先出开场试听定音色语速 → 全部 take → `voice.py align` 逐字对齐 → `check_timings.py` → 需要时 `speed.py`（目标 5.5–6 字/秒）→ 可选 `voice_post.py`（references/15-voice.md） | `build/timings.json` |
| ⑥ 生成 | 增强档：Renoise 先图 + 音效 → 用户挑图 → 视频（首帧用选中的图）→ 下载、改名、`clip2frames.py`（references/04-renoise.md）。基础档跳过 | `assets/` |
| ⑦ 编 | film.js（know.js 组件）→ `render.py stills` 接触表逐张看（含动画中途帧） | `stills/` |
| ⑧ 渲 | `render.py film <期号> --title 片名`（clips → record → finish → deliver） | `out/` |
| ⑨ 质检 | `qa.py` 接触表 + OCR 回读对照 facts.md + 响度 + 冻结 + BGM；接触表里整段画面不变 = 录制出事，重录 | `qa/` |
| **确认 3** | 用户看成片；改完出发布包，`cover_first.py` 把封面接成开头帧（references/05-publish.md） | `post.txt`、封面 |

## 核心主张（不能丢）

1. **精品标准是硬门槛**（references/02-premium.md）：三层构图、没有静止超 3 秒的画面、每章一个「王炸」镜头（增强档动态镜头 / 基础档代码粒子、视差）、分层声音、整期一个视觉系统、科技博主快节奏。
2. **没出处不上屏**（见红线）。
3. **旁白讲故事，画面给关键词**：画面字 ≤8 字一组、同屏最多两组；整句交给旁白和自动字幕。
4. **先猜后讲、标题延后、一个主道具贯穿、结尾回问**（母版共用规则，references/01-templates.md）。
5. **旁白对位**：没念到不露面、计数在念到时落定、强调有预算、最长静止 ≤3 秒（references/11-absorbed.md 第一节）。
6. **能代码就代码**：Renoise 只补代码做不好的镜头（references/08-tiers.md）。

## 默认 BGM

每期默认带同一首 BGM（`engine/music/vibe-bgm.m4a`，112.9 BPM，节拍网格在同名 .json），音量统一：混音时按人声校准，说话时比人声低 10 dB，停顿处自动抬起。film.js 不放也会自动补；想卡点读 `fit_bgm.py` 写的 `bgm.beats.json`。用户要换曲、或这期 / 整个工作区不要 BGM，见 references/08-tiers.md「默认 BGM」。

## 常用命令

```bash
python3 scripts/new_film.py 05 --template A --title "本福特定律" [--series "系列名"]   # 第一次会建工作区：引擎、字体、vk.json
python3 scripts/voice.py plan 05                         # 切 take、打印提示词 → 报价确认 → create_tasks → 下载
python3 scripts/voice.py align 05 take1.wav take2.wav    # 逐字对齐 → build/audio、narration.wav、timings.json
python3 scripts/check_timings.py 05 && python3 scripts/speed.py 05 1.1
python3 <ws>/cine/tools/fit_bgm.py <ws>/lessons/05/assets/audio/bgm.wav --lesson <ws>/lessons/05   # 可选：手动裁 BGM + 节拍表
python3 scripts/clip2frames.py <ws>/lessons/05/assets/clips/v01.mp4 <ws>/lessons/05/assets/clips/v01   # Renoise 视频 → 帧序列（vclip 用）
python3 scripts/layers.py a03.jpg <ws>/lessons/05/assets/img/a03                              # 生图拆主体层 / 底层
python3 scripts/render.py stills 05 <ws>/lessons/05/stills/sheet.png 1 B01+1 B02.title B05.count+0.5
python3 scripts/render.py film 05 --title 本福特定律 --poster 12
python3 scripts/render.py audio 05                       # 只改了音效 / BGM：只重做混音
python3 scripts/qa.py <ws>/lessons/05/build/lesson05.mp4
python3 scripts/cover_first.py <ws>/out/05_本福特定律.mp4 cover_16x9.jpg <ws>/out/05_本福特定律/05_本福特定律.mp4
python3 scripts/earshot.py install                       # film.js 用 earshot 代码音效前装一次
```

## 参考文件

| 文件 | 什么时候读 |
|---|---|
| references/01-templates.md | 选母版、写旁白前：6 种母版每拍做什么、画面、对标作品 |
| references/02-premium.md | 编排前和交付前：精品标准（画面、声音、内容、交付规格） |
| references/03-visual-systems.md | 选风格时：5 套视觉系统 + Renoise 画风前缀 + 时代拼贴 |
| references/04-renoise.md | 增强档：选模型、流程、提示词写法、实测坑、安全 |
| references/05-publish.md | 确认 3 之后：标题、话题、简介、封面、交付文件夹 |
| references/06-benchmarks.md | 选题和写稿时：对标作品数据与共性 |
| references/07-kit.md | 写 film.js 时：know.js 组件 API |
| references/08-tiers.md | 确认 1 定档位、确认 2 列增强清单时；默认 BGM 的设置 |
| references/09-style-studio.md | 用户要改风格或从空白做风格时 |
| references/10-earshot.md | 写音效时：earshot 代码音效，知识片角色 → 音效对照表 |
| references/11-absorbed.md | 写稿和编排时：旁白对位规则、9 种解说语法、质检流程、许可证边界 |
| references/12-style-families.md | 扩风格、做增强档风格时：家族划分与踩坑 |
| references/13-duration.md | 确认 1 问时长前：五项复杂度打分、四档时长 |
| references/14-pitfalls.md | 每个环节开工前扫一眼：真实踩过的坑 |
| references/15-voice.md | 配音前：音色、切 take、提示词、对齐、挑 take、可选 MiMo |
| references/16-cine.md | 第一次写 film.js、改渲染流程时：引擎目录、契约、流水线 |
| styles/INDEX.md、styles/catalog.json | 选风格：44 套按家族分组；每套 STYLE.md + still.jpg，样片源码在 styles/_samples/ |
| templates/ | 6 个母版旁白骨架、film.js 骨架、facts.md、assets.json、演示期 |

改编自 Berryxia（[@andyhuo520](https://github.com/andyhuo520)）的 vibe-knowledge skill，MIT 协议，见本目录 LICENSE。
