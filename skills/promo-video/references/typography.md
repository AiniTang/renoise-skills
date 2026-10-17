# 字体：选字、配对、授权、动效与细节

字体是品牌调性的一半。两次用户反馈把这一页推了出来：

- 某 AI 模型概念片（2026-09-29）：左下角的诗行「不够优雅」。根因不是换一款字，而是**字体文件里少了光学字号轴**，外加一串排版细节没做（§5、§7）。
- 同日，用户对整个 skill 的评价：「现在的字体都比较常规、不符合品牌调性，设计短板明显」。以前的片子要么直接用官网字体，要么落回 DM Sans / SF Pro / 苹方。从现在起**每支片都有一步「字体提案」**（§1）。

工具：
- `scripts/fonts.py`：目录、下载、提案图、子集化、商业字体平替。
- `assets/fonts/catalog.json`：99 款精选字体、17 组配对、平替表。
- `src/cinematic/type/`：载入器与动效字组件。

## 1. 工作流（写分镜之前完成）

1. **读品牌**：官网字体按 brand-from-website.md 提取；有品牌手册以手册为准。用户给了字体文件就放进 `public/fonts/`，并问清授权。
2. **定调性**：从 §2 的 11 个调性里选 1 个主调（可再加 1 个副调）。依据产品气质和受众，不按行业惯例。
3. **找候选**：`python3 fonts.py pairs --tone warm`。官网用的是商业字体（Söhne、Canela、苹方……）时，`python3 fonts.py similar "Söhne"` 找开源平替。
4. **出字体提案图（必做）**：3 组配对 + 1 组品牌现用字体，用片子的真实标题、副标题、正文、中文、日文：

```bash
python3 <skill>/scripts/fonts.py specimen \
  --pair warm-soft --pair editorial-italic --pair bold-youth --combo hepta-slab+manrope \
  --zh-fonts noto-serif-sc+noto-sans-sc --ja-fonts zen-old-mincho+zen-kaku-gothic-new \
  --title "From answers to outcomes." --sub "Give everyone an expert team." \
  --body "Build websites. Create slides, spreadsheets and reports." --eyebrow "YouWare · Brand film" \
  --zh "从答案，到成果。" --ja "答えから、成果へ。" --italic-word "outcomes." --out out/type-proposal.png
```

   提案图由 headless Chrome 渲染，字距、OpenType 特性、可变轴都和成片一致。每组一栏：调性、字体名、授权、适用理由、推荐动效。发给用户选，**选定后写进选型卡第五行**（见 style-router.md）。
5. **下载进工程**：`fonts.py fetch fraunces manrope caveat --to <工程>`，生成三样东西：
   - `public/fonts/<id>/`：字体文件。
   - `fonts.json`：每个字面的真实字重范围、宽度范围、斜体标记和可变轴。**下载的是完整可变字体，opsz 等轴都在**，§5 的坑不会出现。
   - `LICENSES.md`：授权记录。
6. **中日文子集化**：写完文案后跑 `fonts.py subset <工程> --text-file copy.txt`。实测霞鹜文楷从 24.9 MB 降到 25 KB。改文案加了新字就重跑。只对允许子集化的字体生效（§8）。
7. **在片里用**：`useFontManifest()` 载入，`fam("Fraunces")` 取字体栈，动效用 §9 的组件。

## 2. 11 个调性 → 首选字体

| 调性 | 标题 | 正文 / 等宽 | 中文 | 日文 | 适合 |
|---|---|---|---|---|---|
| 精密科技 tech | Geist、Mona Sans（变宽）、Hubot Sans、Supreme | Geist / Inter；Geist Mono、JetBrains Mono、Martian Mono | 思源黑体 | M PLUS 2、Zen Kaku Gothic New | 开发者工具、AI 基础设施、数据 |
| 极简中性 minimal | Inter（opsz）、Switzer、Host Grotesk、Satoshi | Inter、Hanken Grotesk | 思源黑体 | Zen Kaku Gothic New | Apple 式发布、B2B、金融 |
| 人文温暖 warm | Fraunces（SOFT，短标题）、Young Serif、Erode、Hepta Slab | Manrope、Figtree、DM Sans | 霞鹜文楷 + 思源黑体 | Zen Maru Gothic、Klee One | AI 助手、教育、生活方式、社区 |
| 编辑高级 editorial | Newsreader（opsz）、Instrument Serif、Gambetta、Sentient | Instrument Sans、Inter | 思源宋体（细）+ 思源黑体 | Shippori Mincho B1、Zen Old Mincho | 品牌宣言、诗句、官方质感、高端 SaaS |
| 奢华典雅 luxe | Gloock、Bodoni Moda、Boska、Zodiak、Italiana、Cormorant | Hanken Grotesk、Inter Tight；Pinyon Script 点缀 | 思源宋体 | Shippori Mincho B1 | 美妆、珠宝、酒店、香氛、时装 |
| 活力潮流 bold | Clash Display、Cabinet Grotesk、Bricolage Grotesque、Syne、Unbounded | Satoshi、Figtree、Onest | 得意黑、站酷庆科黄油体 | Dela Gothic One、Mochiy Pop One | 社媒广告、年轻消费品、活动 |
| 粗犷海报 poster | Anton、Big Shoulders、Archivo（窄 / 宽）、Anybody、Panchang | Space Grotesk、Space Mono | 得意黑 | Dela Gothic One | 体育、促销、强节奏快剪 |
| 友好圆润 friendly | Fredoka、Parkinsans、Chillax、Pally、Funnel Display | Nunito、Quicksand、Funnel Sans | 站酷快乐体 | Zen Maru Gothic、Mochiy Pop One | 儿童、宠物、萌系、工具类 App |
| 手写温度 hand | Caveat、Kalam、Nothing You Could Do、Homemade Apple、Telma | DM Sans、Manrope | 霞鹜文楷、龙藏体 | Klee One | 用户原话、便签、批注、「人」的声音 |
| 复古数字 retro | Departure Mono、Pixelify Sans、Space Mono、Recursive | Space Grotesk | 思源黑体 | DotGothic16 | 游戏、极客、复古科技 |
| 东方诗意 eastern | Cormorant、Newsreader | Manrope | 霞鹜臻楷、马善政楷书、志莽行书、思源宋体 | Zen Old Mincho、Hina Mincho | 国风、茶、文旅、节气 |

完整 99 款：`fonts.py list [--tone] [--script zh|ja|latin] [--role display|text|mono] -v`。

## 3. 17 组配对（catalog.json → pairings）

`fonts.py pairs` 会列出每组的标题 × 正文 × 点缀、对应的中文 / 日文、适用场景和推荐动效。17 组是：warm-soft · warm-editorial · editorial-italic · luxe-contrast · luxe-didone · tech-precise · tech-wide · minimal-apple · swiss-grotesk · bold-youth · bold-playful · wide-expressive · poster-impact · friendly-round · hand-note · retro-digital · eastern-poetic。

配对原则：
- **一个主角**：标题字有性格，正文字退后。两款都个性强就会打架。
- **对比要够**：衬线 × 无衬线、宽 × 窄、重 × 轻，至少占一项。两款几何无衬线放一起，是最常见的「平庸」来源。
- **同源更稳**：Instrument Serif × Instrument Sans、DM Serif × DM Sans、Mona × Hubot、Funnel Display × Funnel Sans。
- **点缀只给一个词**：斜体、手写体、等宽体，每屏最多一处。
- **中日文单独配**：Latin 字体不带中日文字形。中文最稳的高级感是标题用宋体 / 楷体、正文用黑体。不要让系统回落到苹方或 Hiragino。

## 4. 顶级广告片实际用什么（已核实）+ 开源替身实测

| 品牌 | 字体 | 要点 |
|---|---|---|
| **Claude / Anthropic** | 自研 **Anthropic Serif / Sans / Mono**（Chester Jenkins @ BSPK × Geist）；此前是 Tiempos（Klim）+ Styrene（Commercial Type） | 每款都有 **Text** 和 **Display** 两个光学字号。Display「更锐的形态、更紧的间距、更强的笔画对比」，Text「更开放、x 高更大、对比更低」。官网设计系统提取值：显示字 **400 字重，字距 −0.3 ~ −1.5px（64px 处约 −0.023em），行高 1.05–1.1，永不加粗** |
| OpenAI | 自研 OpenAI Sans（ABC Dinamo × Studio Dumbar，2025 改版） | 用一款定制字体统一了原先的六七种字体 |
| Apple | SF Pro（Text / Display 两套光学尺寸，在 17–28pt 之间平滑过渡） | 大字字距更紧、细节更细 |

来源：gooova.com/en/anthropic-designed-its-own-type-family、type.today/en/journal/anthropic、VoltAgent/awesome-design-md（claude/DESIGN.md）、developer.apple.com（WWDC20 10175）、OpenAI 改版报道（Design Compass / DesignRush）。**共同点：一款带光学字号的衬线或无衬线，用在 Display 尺寸，字重 400，负字距，行高紧。** 买不到自研字体时用开源替身。不要去下「Anthropic Serif 免费下载」之类的站点，那是盗版字体文件。

开源替身（在同一 x 高下对比，深底和奶底各看一次，`size = 目标x高 / xh`）：

| 字体 | 光学字号轴 | x 高 | 观感 | 结论 |
|---|---|---|---|---|
| **Newsreader** | opsz 6–72 | 0.426 | Display 切：锐、对比高、暖，最像 Tiempos Headline / Anthropic Serif Display | ★ 首选 |
| Source Serif 4 | opsz 8–60 | 0.475 | 更冷、更「技术」，同样精致 | 备选 |
| Literata | opsz 7–72 | 0.507 | 温暖，但不如 Newsreader 利落 | 可用 |
| Fraunces | opsz 9–144 | 0.482 | 个性强，长句里字距容易糊，数字挤 | 短标题 + SOFT 用（warm-soft），长诗行别用 |
| Instrument Serif | 无 | 0.510 | 窄而时髦，不适合长诗行 | 标题用 |
| Cormorant Garamond | 无 | 0.386 | 旧式数字，婚礼请柬感 | 有规格数字时避免 |
| Bodoni Moda / Playfair | opsz 6–96 | 0.46 / 0.51 | Didone，时装杂志感 | 与 Anthropic 气质不符 |
| EB Garamond / Spectral / Crimson | 无 | ~0.40–0.45 | 书籍感 | 正文可以，大字偏软 |

x 高对比实验：把多个候选字体放在同一 x 高下、深 / 奶两种底上一次出图（`render.sh <项目> film-stills` 会拼成 `out/stills-sheet.jpg` 便于对比）。

## 5. 最大的坑：字体文件必须带 opsz 轴

`@fontsource-variable/<字体>` 提供 `wght` / `opsz` / `standard` / `full` 几种文件。**只拷 `wght` 文件，字体会被锁死在正文光学字号**（Newsreader 默认 opsz 18），66px 的大字又粗又松。这就是诗行「不够优雅」的根因。

- `fonts.py fetch` 从 Google Fonts 官方仓库下载完整可变字体，所有轴都在，下载后看 `fonts.json` 的 `axes` 里有没有 `opsz`。
- 如果从 fontsource 拷文件，要拷 **`*-latin-standard-normal.woff2`** 和 **`*-latin-standard-italic.woff2`**（wght + opsz）。
- CSS 默认 `font-optical-sizing: auto`，opsz 自动等于字号（px），Canvas 文字同样生效；也可以显式写 `font-variation-settings: "opsz" 72`。
- 用 fontTools 验证：`TTFont(p)["fvar"].axes` 里要有 `opsz`。拷字体时顺手看 GSUB 特性（`liga`、`smcp`、`tnum` 有没有），别指望字体里没有的小型大写。

## 6. 视频里的排版规则（1080p；4K 输出按同样的 px 设计）

| 项 | 规则 |
|---|---|
| 字号 | 主标题 90–160；副标题 30–40；正文 ≥ 28（考虑手机观看）；caption ≥ 22；全大写标签 15–18 |
| 字距 | 标题从 −0.01 em（40 px）到 −0.035 em（≥ 160 px），用 `tracking(size, "display")` 计算；全大写标签 +0.12～0.16 em；正文 0。**中日文不用负字距**：标题 +0.01 em，正文 +0.02 em |
| 行高 | 标题 0.95–1.05；正文 1.4–1.5；中日文标题 1.25、正文 1.6 |
| 字重 | 用对比说话：标题 700 × 正文 400，或标题 300 细衬线 × 标签 600。不要全片都是 400/500 |
| 光学尺寸 | 有 opsz 轴的字（Newsreader、Fraunces、Inter、Bodoni Moda、Literata）设 `font-optical-sizing: auto`；canvas / three.js 里手动传 `opsz(px)` |
| 细线 | Didone 和细衬线（Bodoni、Gloock、Italiana、Cormorant）只用在 ≥ 64 px，否则 1080p 会闪；字重 < 300 的字不要小于 40 px |
| 数字 | 计数器、价格、时间码用 `tabular-nums`；编辑风正文用 lining 或 `onum` |
| 斜体 | 只给一个关键词，而且必须是真斜体文件（catalog 里带 Italic 的才行）；全局 `font-synthesis: none`，杜绝伪斜体和伪粗体 |
| 中文 | 全角标点，行首不放「，。、」；竖排用 `writing-mode: vertical-rl`；中英混排时英文用品牌 Latin 字体，中文用中文字体，中文字号约为英文的 0.92 |

**「官方质感」Display 档**（编辑高级 / Claude 那种衬线字幕）：
- 字重：浅底 **400**，深底约 **375**，永远不用 ≥ 500。深底的光晕会让字显粗，但字重再细，发丝笔画在平台二次压缩后会闪。两篇资料对深底该加重还是减重说法相反，这里取中间值，以实拍帧为准。
- 字距 **−0.02 ~ −0.025em**；逐词用 inline-block 排时，词距约 0.235em（写成 margin-right）。
- 行高 **1.05–1.08**，深底再加约 0.03。
- 颜色：深底用暖白 **#F4F2EC**，不用纯白；浅底墨色 #141413。深底加极轻的 `text-shadow: 0 2px 30px rgba(0,0,0,.4)`。
- 字号层级参考（那支概念片）：诗行 74 / 标签 66 / 字标 138 / HUD 16–20 / 脚注 13。
- 等宽 HUD：**IBM Plex Mono** 400/500（比 JetBrains Mono 文气）或 DM Mono（更轻），全大写，字距 0.1–0.24em。JetBrains Mono 只留给代码编辑器实景里的代码。

## 7. 细节清单（逐条过）

1. **真标点**：撇号 ’、破折号 —、省略号 …、引号 “ ”。直撇号 `'` 是排版事故。
2. **手工断行**：在语义处断（`"a bug is gone,\nthe build turns green;"`），不要靠自动折行；`text-wrap: balance` 只是兜底。
3. **禁止孤字（widow）和悬挂分隔符**：换行落在 `·` 上就把 `·` 删掉、分成两行；破折号署名放到下一行行首。
4. **连字保持开启**（fi/fl），字距对（kern）开启。
5. **数字**：正文 lining；表格和计数器用等宽或 `tnum`。
6. **文字不和 3D 物体相撞**：逐帧抽样看文字区域周围。那支概念片里，小火花在镜头漂移时滑到了最后一行下面，用反向漂移补偿。
7. **层级少而清楚**：一个大衬线声部 + 一个小等宽声部。
8. **动效**：逐词上升 0.2em + 5px 模糊，20–24 帧，expo.out；逐词时间要和声音（钢琴音）对齐。
9. **验收**：把每行字完全显现的那一帧裁出来拼图看（`stills.mjs` + `ffmpeg xstack`），再抽 4K 帧看细节。

## 8. 授权（每次选字都要过）

| 来源 | 协议 | 能做 | 不能做 |
|---|---|---|---|
| Google Fonts（catalog 里的 `gf`）、得意黑、霞鹜文楷 / 霞鹜臻楷、Departure Mono | OFL-1.1（少数 Apache-2.0） | 商用、视频、子集化、改格式 | 单独售卖字体文件；修改后沿用保留名称分发 |
| Fontshare（`fontshare`：Satoshi、General Sans、Switzer、Clash、Cabinet、Gambetta、Zodiak、Erode、Boska…） | ITF Free Font License 2.0 | 免费商用，条款明确允许视频、广告、广播 | **子集化和格式转换都不行**，只能原样使用官方文件（fonts.py 已照此处理）。**不能把字体文件交给第三方**（外包、客户、公开仓库）：每台机器自己下载，不要打包进 skill，交付工程时删掉这些文件 |
| catalog 里的 `manual` 列表（阿里巴巴普惠体、HarmonyOS Sans、MiSans、抖音美好体、优设标题黑、阿里妈妈字体） | 各自的免费商用协议 | 按各自条款使用 | 不自动下载；由用户下载并确认协议后放进 `public/fonts/` |
| 品牌商业字体（Söhne、Canela、方正、汉仪…） | 客户的授权 | 客户提供文件并确认授权后使用 | 没有授权时不要用系统里装的副本，用 `fonts.py similar` 找平替 |
| 系统字体（SF Pro、苹方、Hiragino） | 仅限在 Apple 设备上使用 | 本机预览 | 不在商用成片里当主字体 |

`fetch` 会在工程里生成 `public/fonts/LICENSES.md`，交付说明照抄。

## 9. 动效字：按调性选手法（`src/cinematic/type/`）

```tsx
import { useFontManifest, fam, tracking, VarType, OutlineFill, HandReveal, TrackIn, Decode } from "../cinematic/type";
const faces = useFontManifest(); // 读 public/fonts/fonts.json；字体到位前 delayRender
<VarType text="Fresh flowers" family={fam("Fraunces")} size={110} weight={[300, 560]} axes={{ SOFT: [0, 100], WONK: [0, 1] }} at={0} />
<VarType text="STRETCH" family={fam("Anybody")} size={120} axes={{ wdth: [50, 140] }} weight={[800, 800]} stagger={2} blur={0} />
<OutlineFill parts={[{ t: "From answers " }, { t: "to outcomes.", fill: true }]} family={fam("Instrument Serif")} size={74} writeAt={20} fillAt={95} />
<HandReveal text="a website for my flower shop?" family={fam("Caveat")} size={70} weight={600} cps={16} />
<TrackIn text="MAISON FLEUR" family={fam("Gloock")} size={84} from={0.6} to={0.04} />
<Decode text="SIGNAL · 290+ SUBREDDITS" family={fam("Departure Mono")} size={40} />
```

| 调性 | 手法 | 组件 |
|---|---|---|
| 人文温暖 | 字母软软升起，SOFT 0→100 让字变圆；关键词用 WONK 歪一下头 | `VarType` + Fraunces |
| 编辑高级 | 正体 → 斜体的词义切换；线框写出再填实；逐词上升 + 轻模糊（§7 第 8 条） | `OutlineFill`，同位置交叉淡入的斜体 |
| 奢华典雅 | 字距从宽慢慢收紧，不弹跳 | `TrackIn` |
| 活力潮流 / 粗犷海报 | 宽度轴和字重轴一起弹；按拍砸入 | `VarType`（Anybody / Archivo / Mona Sans 的 wdth，Bricolage 的 opsz + wdth） |
| 精密科技 / 复古数字 | 乱码解码、打字机、等宽数字滚动 | `Decode` + 等宽字 |
| 手写温度 | 笔迹从左到右写出 | `HandReveal`（Caveat / 霞鹜文楷 / Klee One） |
| 东方诗意 | 竖排逐字由模糊晕开 | `VerticalPoem` + 楷体 / 明朝 |

一支片只挑 1–2 种手法，与视觉基调一致。所有动效都由帧号推导，并行渲染不会跳帧。完整示例见 `examples/type-motion/TypeMotionLab.tsx`：6 种手法一屏展示，所需字体用 `fonts.py fetch fraunces caveat gloock anybody instrument-serif departure-mono lxgw-wenkai --to <工程>` 下载。

## 10. 技术坑

- **字体先到位再画**：canvas `measureText`、three.js 的 CanvasTexture、粒子文字采样，都要等 `useFontManifest()` 返回之后再做，否则量到的是回落字体的宽度。
- **伪粗体 / 伪斜体**：请求了字体文件里没有的字重或斜体，Chrome 会自己描粗、倾斜，字会发糊、重影（提案图里 Dela Gothic One 就被描糊过）。`@font-face` 按文件声明真实范围（`fonts.json` 已写好），样式里加 `fontSynthesis: "none"`。
- **可变轴写法**：`font-weight` / `font-stretch` 控制 wght / wdth，其余轴用 `fontVariationSettings: "'SOFT' 100, 'WONK' 1"`。轴名区分大小写，自定义轴是大写。
- **文件名带方括号**（`Fraunces[SOFT,WONK,opsz,wght].ttf`）：`staticFile()` 会自动编码，别手动拼 URL。
- **中日文字体太大**：完整文件 10–25 MB，每个渲染标签页都要加载，务必 `subset`。Fontshare 字体不许子集化，好在都是拉丁小文件。
- **4K**：`--scale=2` 时 DOM 字体按矢量放大；canvas 里的字要按 devicePixelRatio 画。

## 11. 审片清单（字体）

- [ ] 字体提案图给用户看过，选型卡第五行写着字体
- [ ] 标题字有性格、正文字退后；全片最多 3 款字体（中日文各另配 1–2 款）
- [ ] 没有系统回落字体（出现苹方 / Hiragino / Arial 就是漏载了），没有伪粗体 / 伪斜体
- [ ] 字距、行高符合 §6，中日文没有负字距；有 opsz 轴的字确认轴在（§5）
- [ ] 细线字只出现在大字号，小字在手机上读得清
- [ ] 细节清单 §7 逐条过（真标点、手工断行、孤字）
- [ ] 每款字体都有授权记录（`LICENSES.md`），Fontshare 字体没有被子集化，也没有随工程交出去
