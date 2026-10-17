---
name: promo-video
description: 为产品、品牌或服务制作宣传视频：分析用户素材，判断行业与受众，推荐风格与时长，提炼脚本分镜并经用户确认后，用 Remotion 渲染 MP4：模板片（storyboard 驱动的动态排版、SVG、图片）或电影级短片（3D 金属 Logo、还原真实产品界面的打字与点击演示、3D 画廊与景深、运动模糊、真实键盘音效），并从内置开源曲库自动选曲对拍（或用用户音乐、合成兜底）；每支片都叠一层动效设计（匹配剪辑、动态字、形状变形、遮罩转场、粒子高潮）；也能做作品合集、纯动态图形作品集（动态字、形状变形、3D、粒子、遮罩节奏）和单形状 UI 动效循环片（一个形状连续变形、弹簧、光标直接操控、无缝循环）。Use when the user asks for 宣传视频、宣传片、产品发布视频、产品介绍动画、动态设计作品集、片头、promo video, product launch video, explainer video, brand video or motion graphics showreel, or a looping one-shape UI morph animation.
license: MIT
compatibility: Needs Node.js 18+ (Remotion renders), Python 3 with numpy, ffmpeg 7+ and the rn CLI (pip package renoise-kit). AI footage needs a Renoise connection (MCP).
---

# 宣传视频

> 路径约定：`<skill>` 指本 SKILL.md 所在的目录，`scripts/`、`references/`、`assets/`、`templates/` 都在它下面；命令里的 `<skill>/scripts/…` 换成这个目录的绝对路径再执行。

## 默认值

- 画幅 16:9（1920×1080，30 fps）。用户指定尺寸时按用户要求，支持 `16:9`、`9:16`、`1:1`、`4:5`；用户提到抖音、小红书、视频号、Reels 等竖屏平台时用 `9:16`。
- 语言跟随用户素材。第一阶段不做配音；屏幕文字已承载信息时字幕默认关闭。
- 字体不默认落到 DM Sans / SF Pro / 苹方：按 [references/typography.md](references/typography.md) 做「字体提案」——官网或品牌手册的字体 + 按调性挑 3 组配对，用 `fonts.py specimen` 以片子的真实文案出图给用户选，选定后写进选型卡第五行。
- 转折不硬切、声音不落数字静音、文字过细节清单：交付前按 [references/detail-pass.md](references/detail-pass.md) 过一遍（切换点清单 → `rn sheet --around` → `rn qa` / `rn cuts` → `typo_lint.py` / `font_check.py`），用户发现的「突兀」「音频有问题」「不够优雅」大多出在这里。
- Logo 由用户提供。未提供 Logo 时用品牌名文字标，并在 `brand.disclaimer` 写明声明，例如「示例品牌，仅用于演示」。用户没有给出的统计数据一律视为示例，也写进声明，不得编造成真实数据。
- 配乐优先级：用户提供 > 内置曲库 `pick_music.py`（默认，自动避开最近用过的曲子）> 在线开源曲库补充 > `synth_bgm.py` 合成兜底。

## 依赖：`rn`（renoise-kit）

画面和混音由 Remotion 渲染；所有**机械、易错**的环节交给 `rn`：帧精确取帧与接触表、读音乐（响度 / 拍点 / 速度）、成片编码与母带、交付检查、硬切 / 无声 / 爆音审计。`render.sh` 已经接好，手动时直接用 `rn <命令> --help` 查参数。

```bash
brew install ffmpeg-full && export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"   # rn 调用系统 ffmpeg（Linux：apt install ffmpeg）
uv tool install 'renoise-kit[all]'                                                 # 提供 rn 命令
```

| 要做的事 | 命令 |
|---|---|
| 看素材 / 预览 / 静帧文件夹 | `rn sheet <视频或文件夹> [--fps 4 \| --around 帧时间,.. --span 4 --diff]` |
| 读配乐：响度、拍点、BPM（含半 / 倍速候选） | `rn listen bgm.wav --json out/music.json` |
| 逐帧亮度 / 运动 / 频段 / 鼓点 / 爆音 | `rn signal <文件> -o out/signal.png --json out/signal.json` |
| 成片编码、母带、换声音、出 1080p | `rn finish raw.mp4 -o out.mp4 [--audio mix.wav] [--height 1080]` |
| 交付检查（格式、响度、true peak、无声、电平跳变、爆音、黑帧、冻帧、固定帧率） | `rn qa out.mp4 [--accept CHECK@秒]` |
| 硬切清单 + 每刀前后帧 | `rn cuts out.mp4 --sheet out/audit/cuts.jpg` |
| 和上一版 / 参考片对比 | `rn compare 新.mp4 旧.mp4 --cuts` |
| 画面文字（审字、读参考片字幕） | `rn text out.mp4` |

## 选模式与风格路由

每支片先按 [references/style-router.md](references/style-router.md) 做四层选型：① 模式 ② 视觉基调 ③ 叙事骨架 ④ 增强层（≤2），再加 ⑤ 字体（typography.md），写成五行「选型卡」放在分镜表上方给用户确认；**只读选中那几份文档**。冲突时：用户明说 > 路由表里的口碑记录 > 行业默认。下表是①模式与各扩展包的入口：

| 用户要什么 | 模式 | 先读 | 示例 |
|---|---|---|---|
| 产品/服务宣传片、发布片 | 电影级宣传片（默认） | cinematic.md → motion-craft.md | `examples/youware/`、`examples/renoise/` |
| 快速讲解、社媒批量 | 模板片 | storyboard.md、styles.md | `storyboard.json` |
| 个人介绍、账号宣传 | 个人品牌片 | cinematic.md「个人品牌与像素头像」 | — |
| 手机、设备等硬件概念 | 硬件概念片 | cinematic.md「实体硬件产品」 | — |
| 把多支成片剪成合集 | 作品合集 | recap.md | — |
| 秀动效手艺、片头、频道 ID | 动效作品集 | motion-craft.md | `examples/motion-reel/` |
| 音乐驱动、液态融合、数据图表、无限穿越、透视揭示 | 风格扩展包 01（叠加在电影级宣传片上） | style-pack-01.md（音乐驱动先跑 `audio_features.py`） | — |
| 一镜到底、不要硬切、学参考片那种连续感；产品有「输入→产出→持续运行」链路 | 风格扩展包 02：一镜到底接力（叙事骨架，配旁白） | style-pack-02.md（旁白先跑 `narrate_mimo.py`，可克隆客户本人声音） | `src/cinematic/relay/` 组件 |
| 图标会动、动态 emoji、流程节点逐个亮起 | 动效图标（叠加在任何模式上） | animated-icons.md（emoji 先跑 `fetch_noto_emoji.py`） | `examples/animated-icons/` |
| 品牌调性片、品牌升级、「Claude 那种」官方质感、苹果式人文感、不演示具体功能 | 风格扩展包 03：概念阶梯 · 标本册（点→线→面→体→场，每章一个价值句，结尾点写 Logo；60s，钢琴） | style-pack-03.md（字形标本先跑 `glyph_outline.py`） | `examples/youware-ladder/` |
| 模型/产品发布片、要"既有质感又要证明实力"；名字能做文字游戏；有官方数量级事实（可数的奇观） | 风格扩展包 04：十四行诗 · 3D 景深（剧本就是一首诗，一行一小节；规格书 HUD 只引官方原话；68 万笔画对齐成品牌星形） | style-pack-04.md | — |
| 「N 种风格」合集、一个产品换多种画风讲、给客户选风格；综艺花字 / 贴纸风科普 / 等轴 2.5D 微缩城 | 风格扩展包 05：商用风格库（风格目录片模板 + 花字 + 贴纸 + 等轴；也可单独叠在任何模式上） | style-pack-05.md（Three.js 样片先预渲染成视频再进目录片） | `examples/style-catalog/` |
| 逐帧手绘 / 一笔画线条 / 拼贴 / 扁平插画 / 包豪斯海报 / 液态 / 弥散玻璃 / 3D 软萌字针阵 / 赛博 HUD / 像素 / 合成波，或要完整 15 种风格合集 | 风格扩展包 06：商用风格库第二批（11 种画风组件 + 15 格目录片 + 按小节延长配乐 / 复古合成配乐） | style-pack-06.md（滤镜区域与 three 包围盒两个坑必看） | `examples/style-catalog/`（`Reel15.tsx`） |
| 新模型发布当天的「同题对比」短片：两个模型的动画 SVG / 小作品原样并排 + YouWare 输入框和模型菜单 + 结尾钩子 | 模型输出对比片（逐帧确定的 SVG 播放器、命名隔离、同倍率推近、按小节接配乐） | svg-compare.md（先确认模型官方名、推理强度、提示词原文和生成来源） | `examples/svg-compare/` |
| Dribbble 级 UI 动效、一个形状连续变形讲完产品流程 | 单形状宣传片（默认 16:9 宣传片版；纯 1:1 循环版可选） | one-shape.md（先要状态清单、配色、曲子，排好节拍网格再写代码） | `examples/morph-promo/`、`examples/morph-loop/` |

所有模式共用同一套设计原则、动效层、曲库和音效库。

## 设计原则（默认执行）

所有片子按 [references/design-principles.md](references/design-principles.md) 制作：Apple 式一屏一想法、大字留白、克制用色与可信材质；统一的 `lucide-react` 图标（1.75 线宽，功能节点用 `IconTile`；要动就用 lucide-animated，接触帧播一次），emoji 只用 Noto 动态版且默认不用，不用占位图形；每一帧先定焦点与情绪，运镜有动机（推轨、焦点转移、穿越、甩镜、猛推）；声音落在动作接触帧。交付前逐条过文中的「大师审片」清单。

内容层搭好后再加「动效层」（[references/motion-craft.md](references/motion-craft.md)）：**先用官网素材，再把粒子、变形、遮罩叠在这些画面上**（例如粒子在产品截图上聚成口号）。不要单独切一段和产品无关的黑底秀。段与段之间写清转场（优先匹配剪辑），开场物件在结尾回来。

## 工作流程

复制此清单并跟踪进度：

```
- [ ] 1. 素材分析：产品、行业、受众、卖点
- [ ] 2. 一次性确认：目的、风格、时长、画幅、语言、配乐
- [ ] 2b. 字体提案：按调性出 3 组配对 + 品牌现用字体的提案图（fonts.py specimen）→ 用户选
- [ ] 3. 脚本分镜（含每段主手艺与转场列）→ 等用户确认
- [ ] 4. 建工程 → 样帧 → 等用户确认画面
- [ ] 5. 配乐：pick_music.py 选曲对拍，时间轴按曲子 BPM 重排
- [ ] 6. 低清预览 → 修改
- [ ] 6b. 细节审片：切换点清单 + 前后 4 帧（rn sheet --around）+ rn qa / rn cuts + typo_lint.py（给用户看预览之前先自己过）
- [ ] 7. 成片交付与校验
```

### 1. 素材分析

读完用户给的全部内容（文案、PDF、网址、截图、Logo）。用户只给了网址时，按 [references/brand-from-website.md](references/brand-from-website.md) 从官网提取 Logo、字体、配色和高清产品图。提炼：

- 产品是什么，一句话价值主张（≤ 20 字）
- 3–4 个卖点，每个配一个图标意象
- 用户明确给出的数据（只用这些）
- 已有视觉资产：截图、Logo、品牌色、字体
- 行业分类与受众：按 [references/industries.md](references/industries.md) 判断，得到推荐风格、运镜和配乐情绪

### 2. 一次性确认

一次问完，只问推断不出的项，每项把推荐选项放第一位并标注「（推荐）」。宿主有选择题式的提问工具就用它（这类工具一次能问的题数有限，题多就按重要性分两轮），没有就在一条消息里列成编号选项：

- 视频目的：产品发布、功能演示、品牌形象、融资路演、社媒广告
- 制作模式：电影级（真实界面演示 + 3D + 音效，产品发布/品牌片推荐）或模板片（出片快，适合讲解、社媒批量）
- 电影级风格：暗场科技 / 剪纸 / 浅色编辑，按行业推荐（见 cinematic.md「风格」）
- 风格：按行业表给 3 个预设，每个附一句画面描述（预设见 [references/styles.md](references/styles.md)）
- 时长：按目的给档位（见 [references/storyboard.md](references/storyboard.md)），提示「时长越短，每屏文字越少」
- 画幅：只有素材暗示竖屏或多平台投放时才问，否则直接用 16:9
- 语言
- 配乐来源：内置曲库（推荐，给出 2–3 首候选的曲风描述）/ 自己提供 / 合成

用户已明确说过的项不再问。

### 2b. 字体提案

按 [references/typography.md](references/typography.md) §1：定调性 → `fonts.py pairs --tone <调性>`（官网是商业字体时先 `fonts.py similar "<字体名>"`）→ 用片子的真实标题、副标题、正文、中文 / 日文出提案图，3 组配对 + 1 组品牌现用字体：

```bash
python3 <skill>/scripts/fonts.py specimen --pair warm-soft --pair editorial-italic --pair bold-youth --combo <品牌标题字>+<品牌正文字> \
  --title "..." --sub "..." --body "..." [--zh "..."] [--ja "..."] --out <项目目录>/out/type-proposal.png
```

发图给用户选；选定后 `fonts.py fetch <ids> --to <项目目录>`，写完文案再 `fonts.py subset <项目目录> --text-file copy.txt`（中日文）。授权按 typography.md §8：Fontshare 字体不子集化、不随工程交给第三方。

### 3. 脚本分镜

用户提供了脚本就按脚本拆成场景；否则按 [references/storyboard.md](references/storyboard.md) 的结构编写。表格上方先写选型卡（style-router.md），再以表格给用户确认：

| # | 时长 | 场景类型 | 画面 | 屏幕文字 | 运镜 | 主手艺 / 转场 |
|---|------|----------|------|----------|------|------|

**未经用户确认不进入渲染。** 用户修改后更新表格再确认一次。

### 4. 建工程与样帧

```bash
bash <skill>/scripts/setup_project.sh <项目目录>
```

电影级：`storyboard.json` 只提供品牌信息，画面在 `src/Film.tsx` 里按 [references/cinematic.md](references/cinematic.md) 编写（参考 `templates/remotion/examples/youware/`），样帧用 `render.sh <项目目录> film-stills <帧号...>` 逐段抽查，预览 `film-preview`，成片 `film`（输出 `out/film.mp4` 并做响度检查）。以下 storyboard 校验与 `render.sh` 针对模板片。

- 把确认后的分镜写入 `<项目目录>/storyboard.json`（字段见 storyboard.md）。
- 素材放进 `public/`：`brand/`（Logo）、`fonts/`（`fonts.py fetch` 下载，含 `fonts.json` 与 `LICENSES.md`）、`images/`（截图）、`music/`。`storyboard.json` 里的路径相对 `public/`。
- 校验并渲染样帧（每个场景的中间帧）：

```bash
python3 <skill>/scripts/check_storyboard.py <项目目录>/storyboard.json
bash <skill>/scripts/render.sh <项目目录> stills
```

- `ERROR` 必须修复。`WARN 阅读时长` 表示文字读不完：缩短文字或延长场景。
- 逐张看 `out/stills/scene-N.png`（`out/stills-sheet.jpg` 是一页总览），按 design-principles.md「大师审片」清单检查（焦点、留白、溢出、图标、对比度），修完再把样帧给用户看（宿主能发文件就直接发图，否则给出文件路径）。
- 用户想比较风格时，改 `style` 重新出样帧，把旧样帧另存为 `out/stills-<风格>/` 以便并排对比。

### 5. 配乐

按 [references/music.md](references/music.md) 处理。无论哪种来源都要设置 `music.bpm`（`rn listen` 读出），时间轴会把每个剪辑点对齐到节拍。

需要旁白时按 cinematic.md「旁白配音」用 `voiceover.py` 生成（小米 MiMo TTS 或本机 `say`），时间轴改由配音时长驱动。成片响度要改时只重做音轨、不重渲画面：`rn finish out/film.mp4 -o out/film-loud.mp4 --copy-video --lufs -12`。

### 6. 预览

```bash
bash <skill>/scripts/render.sh <项目目录> preview
```

半分辨率快速出片。把 `out/preview.mp4` 路径给用户，按反馈修改 `storyboard.json` 后重渲。

### 6b. 细节审片

给用户看预览之前，按 [references/detail-pass.md](references/detail-pass.md) 自己过一遍：

```bash
rn sheet out/film-preview.mp4 --around <切换点秒数,...> --span 4 -o out/seam.jpg                       # 每个挂载 / 卸载 / 参数切换点前后 4 帧（秒数 = 帧号 / 30）
rn qa out/film-preview.mp4                                                                             # 黑帧、冻帧、数字静音、电平跳变、爆音（render.sh 已自动跑）
rn cuts out/film-preview.mp4 --sheet out/audit/cuts.jpg                                                # 硬切清单，每刀前后各一帧
python3 <skill>/scripts/typo_lint.py storyboard.json                             # 或 --ts src/film/*.ts*；--fix 自动修 JSON
python3 <skill>/scripts/font_check.py public/fonts                               # 光学字号轴、真标点字形
```

每一条要么修掉，要么写进项目根目录的 `qa-accept.txt`（一行一个 `检查项` 或 `检查项@秒`，`#` 后写原因）并在交付说明里写明「有意为之」；之后的审计不再重复报它。

### 7. 成片

```bash
bash <skill>/scripts/render.sh <项目目录> final
```

产出 `out/final.mp4`、`out/cover.png`，有 `caption` 时还有 `out/captions.srt`。**交给用户的文件一律是 `rn finish` 的输出**（`render.sh` 的 `film` / `final` 会自动做：画面单独渲染、混音另渲 WAV，再由 `rn finish --audio` 合成）。Remotion 直出的 MP4 在一些播放器和上传平台里只显示一半时长（用户反馈「发出去 38 秒，打开只有 19 秒」），根因见 [references/detail-pass.md](references/detail-pass.md)「交付编码」。自己手动渲染 4K 时：

```bash
npx remotion render src/index.ts Film out/film-raw-4k.mp4 --muted                # 构图本身是 3840×2160；1080p 构图加 --scale=2
npx remotion render src/index.ts Film out/mix.wav --codec=wav --config=remotion.audio.config.ts
rn finish out/film-raw-4k.mp4 -o out/<名字>.mp4 --audio out/mix.wav
rn finish out/<名字>.mp4 -o out/<名字>-1080p.mp4 --height 1080 --lufs keep                          # 给微信 / 社媒
rn qa out/<名字>.mp4                                                                               # 任何要发出去的文件都先过这一步
```

核对 `rn qa` 的结果（FAIL 必须为 0；WARN 修掉或写进 `qa-accept.txt`）和 `out/audit/cuts.jpg` 的硬切，查看封面帧，再交付文件路径和简短说明（风格、时长、配乐来源及授权、声明内容、有意保留的 WARN）。用户看完给出评价（喜欢 / 不如之前 / 要重做）后，把「组合 → 片子 → 反应」记进 style-router.md 的口碑记录。

## 渲染约束

- 所有动画必须由 `useCurrentFrame()` 推导。禁止 CSS transition/animation、Framer Motion 自动播放、`setTimeout`、无种子的 `Math.random()`，否则逐帧渲染会闪烁或错位。GSAP 仅可按帧 seek 使用。
- `render.sh` 需要在命令沙箱外运行（headless Chrome 要读取 CPU 核数和 GPU）：宿主给 shell 命令加了沙箱时，按宿主的方式对这条命令放开。
- 整片渲染（`preview`、`final`、`film-preview`、`film`）和首次 `setup_project.sh`（`npm install`）要几分钟，会超过多数宿主的单条命令超时：放到后台跑（宿主有后台运行能力就用它，没有就 `nohup … > out/render.log 2>&1 &`，之后看日志），不要高频轮询；`stills`、`film-stills` 抽几帧可前台跑，超时放宽到 10 分钟。
- 无需全局 Node：`setup_project.sh` 会找已有 Node，找不到就下载便携版到 `~/.cache/promo-video/node`。ffmpeg 与 `rn` 要装在系统里（见「依赖」），`setup_project.sh` 缺了会提示。
- `hero3d` 渲染最慢，一支片保持 1–2 个。
- 常用工具：`rn finish`（交付编码：fixed_frame_rate_flag=1、BT.709 TV 范围、moov 前置、−14 LUFS 与编码后 true peak ≤ −1 dBTP、`--audio` 换成 WAV 混音、`--height 1080` 出小版本）；`rn qa`（交付检查 + 黑帧 / 冻帧 / 数字静音 / 电平跳变 / 爆音，`render.sh` 自动跑）；`rn cuts --sheet`（硬切清单）；`rn sheet`（精确取帧拼图，视频或静帧文件夹，选镜和审片都用它，不要用 `ffmpeg -r 1`）；`rn listen`（BPM、拍点、响度）；`typo_lint.py`（屏幕文字的直撇号、三个点、`--`、全角标点、悬挂分隔符、孤字）；`font_check.py`（字体文件的轴、特性、真标点字形，缺 opsz 会警告）；`fonts.py`（字体目录 / 配对 / 提案图 / 下载 / 子集化 / 商业字体平替，见 typography.md）；`audio_features.py`（配乐逐帧特征，`AudioReactive.tsx` 读它的格式）；`pick_music.py`（选曲对拍）；`narrate_mimo.py`（旁白：MiMo 预设音色或克隆客户本人几秒录音，输出逐字时间 timings.json 驱动画面，`--qa` 回读校验）。
- shell 是 zsh：`for t in $LIST` 不会按空格拆分，把列表直接写在 `for t in 1 2 3` 里；heredoc 里有反引号或 `${}` 时用 `<<'EOF'`，否则会被 shell 展开。

## 扩展

- 新增场景类型：在 `src/scenes/` 写组件，加入 `src/types.ts` 的 `Scene` 联合类型和 `src/Promo.tsx` 的 `SceneBody`，并同步 `check_storyboard.py` 的 `SCENE_TYPES` 与 `scene_text`。
- 图片用 `<Img>`；GIF 装 `@remotion/gif`；Lottie 装 `@remotion/lottie`。`@remotion/*` 包版本必须与 `remotion` 完全一致。
- AI 素材补充：客户拍不到的人物和场景，用 **Renoise** 生成关键帧和图生视频（需安装 Renoise 插件并登录），画风取自客户自己的设计规范；模型按 Renoise 的 model-routing skill 选，每批先 `estimate_cost` 报数量和估价、用户同意再提交。流程、提示词规则和底线见 [references/ai-footage.md](references/ai-footage.md)。

## 参考资料

- [references/brand-from-website.md](references/brand-from-website.md)：从官网提取文案、配色、字体、Logo 和产品图
- [references/design-principles.md](references/design-principles.md)：设计原则、图标规范、导演运镜、声音与大师审片清单（默认执行）
- [references/detail-pass.md](references/detail-pass.md)：**细节审片**：连续 / 不空 / 精三条原则，切换点清单流程，明→暗转折的画面与声音配方，`rn qa` 的判定阈值与豁免，交付编码，踩过的坑（交付前必做）
- [references/typography.md](references/typography.md)：**字体系统**：字体提案工作流、11 个调性 → 首选字体、17 组配对（中 / 日文对应）、顶级广告片用什么字体（已核实）与开源替身实测、**字体文件必须带 opsz 轴**、视频排版规则与 Display 参数、授权（OFL / ITF FFL / 厂商协议）、动效字组件（`src/cinematic/type/`：VarType、OutlineFill、HandReveal、TrackIn、Decode）、细节与审片清单
- `assets/fonts/catalog.json`：99 款精选字体（Google Fonts / Fontshare / GitHub 发行版，拉丁 + 中文 + 日文）、17 组配对、商业字体平替表、需手动下载的厂商字体清单；`scripts/fonts.py` 读取它
- [references/cinematic.md](references/cinematic.md)：电影级 Film 模式：风格、场景组件、产品界面与报告还原、3D、动效与音效设计
- [assets/sfx/README.md](assets/sfx/README.md)：可免费商用的音效库目录（打字、鼠标、UI、转场、纸张、翻页），`preview.wav` 可试听
- `assets/music/catalog.json`：曲库目录（情绪、BPM、能量到达点、授权、下载地址与 sha256）；曲子不随仓库分发，`pick_music.py` 首次使用时从 Mixkit 官方地址下载到 `~/.cache/promo-video/music/` 并校验
- [references/industries.md](references/industries.md)：行业分类 → 推荐风格、运镜、配乐、合规提示
- [references/styles.md](references/styles.md)：4 套风格预设与品牌色覆盖规则
- [references/camera.md](references/camera.md)：运镜词汇、经典手法映射与节奏规则
- [references/storyboard.md](references/storyboard.md)：`storyboard.json` 字段、时长档位、叙事结构与文案规则
- [references/music.md](references/music.md)：内置曲库与 `pick_music.py`、扩充开源曲库、BPM 对拍、合成兜底、响度与授权
- [references/motion-craft.md](references/motion-craft.md)：动效层：克制/表现两个档位、手艺地图、转场设计、动效作品集
- [references/recap.md](references/recap.md)：多支成片剪成合集（Apple 式轮播回顾）
- [references/animated-icons.md](references/animated-icons.md)：动效图标（lucide-animated 467 个，逐帧替身已对照验证）与 Noto 动态 emoji（`fetch_noto_emoji.py`），节奏规则与授权
- [references/style-router.md](references/style-router.md)：**风格路由**：四层选型、按信号推荐、选型卡、口碑记录（每次交付后更新）、扩展包生命周期
- [references/style-pack-02.md](references/style-pack-02.md)：风格扩展包 02：一镜到底接力（学 Fastlane）——接力规则、贯穿线索、12 个 relay 组件、旁白逐字驱动时间轴
- [references/style-pack-03.md](references/style-pack-03.md)：风格扩展包 03：概念阶梯 · 标本册（学 Claude Motion Reel）——章节级接力、字即其义、规格书 HUD、13 个 specimen 组件（点阵 / 山脊线 / 弦图 / 色板 / 走马灯 / Truchet / 立方体→魔方 / 体素→黏土球 / 6 万粒子 / 笔尖写 Logo）
- [references/style-pack-04.md](references/style-pack-04.md)：风格扩展包 04：十四行诗 · 3D 景深——"诗 + 证据"的发布片：形式即概念、纸墙滑动变焦穿洞、68 万笔画 GPU 实例化对齐、暗→金→奶白、官方视频读取法、配乐按小节重排、踩坑清单
- [references/style-pack-05.md](references/style-pack-05.md)：风格扩展包 05：商用风格库第一批——风格目录片模板（信息卡 + 播放器窗口 + 圆点串联 + 片尾四宫格）、综艺花字（叠层描边、弹簧、爆炸星、速度线、テロップ）、贴纸风（alpha 模切、落地弹簧、胶带、手绘批注）、等轴 2.5D（正交相机微缩城、移轴、挤出标志）；15 种风格对照与后续路线图
- [references/style-pack-06.md](references/style-pack-06.md)：风格扩展包 06：商用风格库第二批——逐帧手绘（一拍二、双铅笔线、蜡笔排线）、一笔画线条、拼贴（撕纸、真网点阈值、勒索信字母）、扁平插画（品牌头像叠色）、包豪斯、液态光泽滤镜、弥散玻璃（backdrop-filter）、3D 软萌字 + 胶囊针阵、赛博 HUD、像素、合成波；15 格目录片、配乐按小节延长 + 复古合成配乐；踩坑清单
- [references/svg-compare.md](references/svg-compare.md)：模型输出对比片——两段动画 SVG 同页逐帧确定播放（SMIL 用 setCurrentTime；CSS 用暂停 + 负延迟 + `--t`；`<use>` 展开；推近变换包裹组；像素差回归校验）、YouWare 输入框和模型菜单组件、官方模型名与推理强度对照（Extra High = xhigh = 极高）、踩坑清单
- [references/style-pack-01.md](references/style-pack-01.md)：风格扩展包 01：音乐驱动（`audio_features.py` 逐帧频谱/鼓点）、液态融合、数据叙事、无限穿越、透视揭示，含适用场景与坑
- [references/inspiration-sources.md](references/inspiration-sources.md)：扩展包的社区灵感出处（只记出处，不搬提示词）
- [references/one-shape.md](references/one-shape.md)：单形状宣传片：一个形状连续变形演产品流程，左侧大字卖点，闭式弹簧、光标直接操控、双弹簧边缘、首尾帧一致
- [references/ai-footage.md](references/ai-footage.md)：AI 素材补充——用 Renoise 生成关键帧与图生视频，按客户画风写风格块，花钱前确认，进片方式与底线
- [references/compliance.md](references/compliance.md)：演示阶段的声明与广告用语底线
