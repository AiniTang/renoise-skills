# 04 · Renoise 增强层：图、视频、音效

所有生成都走 Renoise（estimate_cost / create_tasks / wait_tasks / download_results）。
**花积分的硬规矩**：把整期的 assets.json 列成一张表（模型、提示词、参数、数量、estimate_cost 总价、余额）发给用户，**等用户在对话里明确说可以**才 create_tasks。宿主的工具授权弹窗不算确认；之前说过「直接生成」也不算。改了任何提示词、模型、数量就要重新报价确认。

开工前：`get_account` 看余额；`load_skill model-routing` 读路由规则（下面是本 skill 用到的结论，模型以 list_models 实时为准）。

## 选模型

模型先 `load_skill model-routing` 再定，参数和限制以 list_models 为准，价格一律以 estimate_cost 为准（不要凭记忆报价）。本 skill 实测好用的搭配：

| 资产 | 常用模型 | 用在 |
|---|---|---|
| 场景 / 氛围配图 | Midjourney（`mj-v8.2`） | 时代场景、主视觉、氛围（画风最好） |
| 带结构的示意图、地图底图、精确构图 | GPT Image 2.5（`gpt-image-2.5-sunburst`） | 地图、需要准确布局的画面 |
| 同一角色 / 同一场景多张一致、超宽画幅 | Nano Banana 2（`nano-banana-2`） | 系列角色、长卷（4:1） |
| 主视觉动态镜头 | Wan 3.0（便宜，短镜头）/ Seedance 2.5（默认，复杂运动） | 首帧 = 已生成的配图 |
| 单个音效 | ElevenLabs SFX（`eleven-sfx-v2`） | 钟声、翻书、风、人群 |

配乐默认用工作区的 BGM（08-tiers.md），不另外生成整段配乐。配音见 15-voice.md。
**一期预算**：按 08-tiers.md 的增强等级挑镜头，报价时把每一项和总价都列出来。

## 流程

1. **写 assets.json**：每一项写清 `use`（哪一拍、做什么用）、`kind`、`model`、`ratio`、提示词。提示词 = `style_prefix` + 本张内容 + `no text, no letters, no watermark`。
2. **先图后视频**：动态镜头一律用已生成的配图做首帧（`references: [{ref: "task:<图的任务号>", role: "first_frame"}]`），保证动静一致；所以分两轮报价：第一轮图 + 配乐 + 音效，第二轮视频（第一轮出图后用户挑图）。也可以一次把两轮都列进预览、一次确认（预览里写明第二轮的首帧取自第一轮哪张）。
3. **create_tasks**（每次 ≤10 个）→ **wait_tasks** 直到 done → **download_results**（返回下载命令，在 shell 里跑，下到 `lessons/NN/assets/_dl/`）→ 按 assets.json 的 `file` 改名放好，`status` 改 done，记下 task 号。
4. **视频进画面**（Wan 3.0 720p 实测输出顶部带 66 像素纯黑信箱边，clip2frames.py 会自动检测裁掉；拆完抽一帧确认首行不是黑的）：`python3 scripts/clip2frames.py assets/clips/v01.mp4 assets/clips/v01 --fps 30` → 打印帧数 n → film.js 里 `vclip(s, { dir: A("clips/v01"), n })`。原视频的环境声另存在 `assets/clips/v01/audio.wav`，要用就加一条 music：`{ src: P("clips/v01/audio.wav"), at, dur, gain: -20 }`。
5. 不满意的单张：只重做那一张（新报价、新确认），别整批重来。

## 提示词写法

### 配图（Midjourney v8.2）
短句视觉描述，不写需求文档：
`[style_prefix], [主体], [环境], [光线], [构图：wide shot / low angle / negative space on the right for text], no text, no letters, no watermark`
- 给关键词留位置：写明 `negative space on the left/right/top`。
- 16:9；人物不写具体面部，写剪影 / 背影 / 远景，减少「像某个真人」的风险。

### 地图 / 示意（GPT Image 2.5 Sunburst）
```
USE: background plate for a documentary explainer
SCENE: antique paper map of Tang dynasty China, Yellow River and major prefectures as subtle ink lines
COMPOSITION: 16:9, map centered, wide margins, no labels
AVOID: any text, letters, numbers, legend, watermark
```
地名、数字全部由代码叠加（spread / keyword），不让模型写字。

### 动态镜头（Wan 3.0 / Seedance 2.5）
首帧模式，只写**变化**，不重复描述静态画面：
`[主体的动作 / 环境的变化], [一个镜头运动：slow push-in / slow dolly left], [光线变化], no text, no subtitles`
- 8 秒足够，一个镜头一个动作；需要多拍叙事或更长、更复杂的运动用 Seedance 2.5。
- 原生音频默认开着，可当环境声；不要对白。

### 音效（ElevenLabs SFX）
物理描述 + 真实长度：`a single temple bell struck once in a cold stone courtyard, long natural decay` · 3 秒。一条一个音效。

## 实测坑（第 01 期）

- Midjourney 每个任务只出 1 张 1456×816：要候选就多提交几个任务；放进成片前用超分（如 Real-ESRGAN x4plus）放大再缩到 1080p，推拉镜头才不糊。
- 统一画风前缀会压过单张描述：时代不同的那张（如宋代书房）要换前缀，否则会被画成战国城楼。
- 首帧视频不一定照提示词演：v02 没有「关门」而是走进来一个斗篷人，先看片再决定用不用，别默认能用。

## 安全

- 不生成在世真人的脸、不模仿品牌 logo；历史人物写「人物造型为示意」。
- 生成画面一律角标「AI 示意图 / AI 生成画面」（plate、vclip 默认带）。
- 不把用户的私人素材传给 Renoise，除非用户明确要用。
