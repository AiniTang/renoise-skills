# youware-ladder · 概念阶梯 · 标本册示例（YouWare 品牌片：60s 人文版 `Film60.tsx` + 40s 快版 `Film.tsx`）

用 `src/cinematic/specimen/` 组件拼的完整成片，规则见 `references/style-pack-03.md`。
点 → 线 → 面 → 体 → 场：一个想法 → Vibe Coding → 人人的办公文档 → 打磨的产品 → 协作的 AI 团队，结尾由那个点写出 Logo。

**60s 人文版（推荐基线）**：每章在几何之外挂一个价值——从小到大、包容（多色多形点阵）、倾听（`drawVoice` → 48 条山脊线）、Vibe Coding 起家、品味（色板）、细节（`GlyphAnatomy` + Eames 引语）、人人可用（走马灯 + Truchet）、体验（魔方）、创新（细分黏土团）、协作（粒子 `together.` → 标志 + Made with people, for people.），结尾 From answers to outcomes.
配乐钢琴 Silent Descent（71.8 BPM 半拍网格，曲子 69.8s 的爆发落在粒子那一刀）：`ffmpeg -ss 20.521 -t 65.2 -i assets/music/mixkit-614-silent-descent.mp3 -ar 48000 -ac 2 public/music/bgm60.wav`，淡入 1.2s / 淡出 2.8s 用 Python 做（Remotion 自带 ffmpeg 没有 afade）。
v3（当前）：色板后那段是 Apple 式产品细节变形链 `YouWareChain.tsx`（头像颜色取自官网 agent 头像）；v2 曾用 AI 人物两镜（已弃用，用户评价突兀）：`public/gen/v5-craft-a.mp4`（从 0.8s 用）、`public/gen/v2-listen-b.mp4`（从 1.9s 用），由 `scripts/hiapi_task.py` 生成，提示词和任务记录见原工程 `gen/jobs-*.json`、`gen/*/hiapi-log.json`（流程见 references/ai-footage.md）。旧版字形镜头的数据 `glyph-a.json`：`python3 scripts/glyph_outline.py public/fonts/HeptaSlab.woff2 a src/glyph-a.json --wght 400`。

用法：把本目录复制到工程 `src/youware-ladder/`，在 `Root.tsx` 注册
`<Composition id="Film" component={Film} width={1920} height={1080} fps={30} durationInFrames={FILM_FRAMES} />`（60s 版同理：`Film60` / `FILM60_FRAMES`）。4K 用 `--scale=2`：画布和粒子已按 devicePixelRatio 自适应。

需要的素材（放 public/）：
- `brand/logo-mark.svg`、`brand/logo-wordmark.svg`（官方矢量，黑色填充，片中用作 CSS mask 上色）
- `fonts/DMSans-{300,400,500,700,900,400i}.woff2`（@fontsource/dm-sans）、`fonts/HeptaSlab.woff2`（可变字重 1–900）
- `music/bgm.wav`：`pick_music.py --track mixkit-160-minimal-emotion.mp3 --seconds 40.6 --hit-at 30.0 --bpm 128`（曲子 break 落在 26.3–28.1s，drop 落在粒子爆开）

样帧：`node stills.mjs Film out/stills 45 134 197 316 377 422 485 560 605 640 724 790 841 914 970 1055 1167`（一次打包、一个浏览器，每帧 < 1s）。

