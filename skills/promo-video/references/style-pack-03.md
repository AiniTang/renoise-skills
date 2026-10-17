# 风格扩展包 03：概念阶梯 · 标本册

> 状态：**组件已建（`src/cinematic/specimen/`）。YouWare 样片两版（`examples/youware-ladder/`）：40s 快版 → 用户反馈「鼓点太多、故事没展开」→ 60s 钢琴人文版（推荐基线）**。口碑记录见 style-router.md。

学自抖音 @聆岚「Opus 5.5 炫技之作」（Claude Motion Reel，63s，1280×720 转载，原片 1920×1080 60p，Remotion + Three.js）。拆解方法：1s/0.25s 精确取帧拼图 + 响度包络 + BPM（约 118）。

一句话：**用一个可以数出来的概念阶梯当骨架（点 → 线 → 面 → 体 → 场），每一章是一组「生成艺术标本」，上一章最后一个物体长成下一章第一个物体，最后缩回开场那个点，由它写出签名和 Logo。**

## 什么时候用

- 适合：品牌形象片、品牌升级/调性片、发布会开场、年度片、「秀实力」的作品集；设计/创作/AI 工具（产品本身就是「从无到有」）；产品能力天然有「由小到大」的层级（一句话 → 一页 → 一个网站 → 一个产品 → 一整个团队）。35–60s，可以完全不露界面（叙事升华，不做功能演示）。
- 不适合：投流转化片主体（太抽象，前 3 秒没有产品）；要逐条讲清功能的讲解片；没有可数层级的产品（阶梯编不出来就别硬套）。投流只借它做 3–5s 钩子或 15s 精简版（两章 + 签名收尾）。

## 五条精髓（写分镜时逐条对照）

1. **阶梯骨架**：章节是一个可数的递进（0D→1D→2D→3D→∞），观众不用读字也能感到「在升维」。给客户用时换成产品自己的阶梯，章节数 4–5，每章名字一个词。
2. **章节级接力**：每章的出口物体 = 下一章的入口物体。原片：弹跳球落地长出点阵 → 点阵塌成一个点 →「点出去散步」画出线（引 Klee）→ 线加粗成珊瑚色长条 = 面 → 所有平面卡片折成立方体展开图 → 立方体 → 魔方 → 炸成体素地面 → 二十面体升起 → 细分成球 → 球散成粒子 → 粒子塌成线 → 点 → 点写签名 → 点炸开成 Logo。**开场的点就是结尾写签名的笔尖。**
3. **字即其义**：每章标题字的排印本身就是这个概念——`point.` 的句点就是那个点，字母像球一样弹走；`line` 是一笔画出的单线手写；`PLANE` 是填充/描边交替的满屏走马灯（平面铺满）；`field.` 由粒子组成。比 KineticWord 的「词义匹配」更进一步：字就是标本。
4. **规格书 HUD + 真实技术注释**：四角括号，左上「品牌 — MOTION REEL」，右上「2026 · 1920×1080 · 60P」，左下「01 POINT · 0D」（章号 + 章名 + 维度），右下「TC 00:13:38」（秒:帧），底部细进度条带章节刻度。每个标本配一行等宽注释，写的都是画面里真实的参数：`i → 3.76 · i (mod 180)`、`3 × 3 × 3 · 27 CUBELETS`、`SUBDIVISION · 20 FACES → 320 FACES`、`60,000 PARTICLES · ONE SHADER`。HUD 颜色随底色反转。
5. **明暗交替 + 呼吸再落**：点/线在暗墨底，面炸成满屏色块再到暖纸，体在暖纸上有真实阴影，场回到暗底，Logo 落在暖纸。配乐在每个章节接缝前约 1s 收一口气（响度掉一半），接缝处落 impact（原片 16.0 / 28.0 / 40.0 / 56.0s 四个峰）。

## 原片章节配方

| 章 | 时间 | 底色 | 标题字 | 标本（每个约 2.5–3s） | 出口 → 下一章入口 |
|---|---|---|---|---|---|
| 01 POINT · 0D | 0–8.2 | 暗墨 | `point.` 衬线，句点是主角 | 聚焦环里一个点 → 飞成句点 → 字母沿抛物线弹走；弹跳球 + 关键帧曲线（F150 / F180 / 播放头 F198，挤压拉伸）；点阵半调径向波（珊瑚/米白）；点阵 3D 倾斜 + 运动模糊 | 点阵塌成一个点 |
| 02 LINE · 1D | 8.2–15.2 | 暗墨 | `line` 单线手写，下附 Klee 引语 | 点拖出一笔；Joy Division 山脊线（一条珊瑚色）；线段碎成折线弧；模乘弦图（圆上 N 点连 k·i mod N，k 连续变化） | 弦图压扁成一条水平线 |
| 03 PLANE · 2D | 15.2–26.6 | 珊瑚 → 暖纸 → 蓝 | `PLANE` 粗黑体，实心/描边行反向走马灯 | 线加粗成满屏色块；Figma 式选框（Ellipse 400×400）圆变星（Polygon），带光标；Truchet 圆弧拼砖旋转；蓝底 metaballs；分屏网格 2 → 4 → 6 格收集前面所有画面 | 网格缩成拼贴卡片 → 排成立方体展开图 |
| 04 VOLUME · 3D | 26.6–39.8 | 暖纸 + 软阴影 | 无大字，立方体面上的 `Aa` | 展开图折成立方体（每面是上一章的画面）；3×3×3 魔方；炸进体素地面，高度场波纹；二十面体升起 → 细分 → 噪声位移成亮釉黏土团 → 松弛回圆球 | 底色翻暗，球只剩边缘光，表面散成粒子 |
| 05 FIELD · ∞ | 39.8–49.8 | 暗墨 | `field.` 由粒子组成 | 粒子爆开（impact）；星系旋臂；聚成 `field.`；彩色点云地形；curl noise 光迹 | 全部塌成一条线 → 一个点 |
| 签名 | 49.8–56.2 | 暗墨，HUD 退场 | 「A MOTION REEL BY」小字 | 发光笔尖写出单线手写品牌名 + 下划线；再倒着擦回去 | 笔尖闪一下 |
| Logo | 56.2–63.1 | 暖纸 + 暗角 | 品牌字标 + 斜体标语 | 从点开圆形揭示暖纸；Logo 笔画放射长出、转一下；字标从 Logo 后滑出；标语淡入 | —（与开场的点首尾呼应） |

镜头几乎全程锁定居中，动势全在物体上；只有走马灯、点阵倾斜这类快动作开运动模糊；3D 段慢速环绕 + 接触阴影。

## 组件（`templates/remotion/src/cinematic/specimen/`）

```tsx
import { SpecimenCanvas, SpecimenHud, BounceGraph, StrokeDraw, CubeStage, VolumeScene, ParticleField,
  drawHalftone, drawRidges, drawStrings, drawPalette, drawMarquee, drawTruchet,
  MARK_PATHS, VIBE_PATH, penAt, icoFaces, win, type SpecimenTheme } from "../cinematic/specimen";
```

**2D 标本是纯函数** `drawX(theme, opts) => (g, t) => void`，在 1920×1080 基准空间里画一帧；`<SpecimenCanvas draw t w h region />` 负责把它 cover 到任意尺寸。同一个标本因此能铺满全屏、缩进网格、贴在立方体面上、切成魔方贴纸——收集拍靠的就是这个。所有参数都是 0..1 进度，由片子按节拍算好传进来。

| 组件 | 做什么 | 关键参数 |
|---|---|---|
| `SpecimenHud` | 规格书 HUD：四角、片名、格式、章号·章名·维度（切章时滚动）、`TC mm:ss:ff`、带章节刻度的进度线、顶部技术注释（乱码打字）；`light` 区间自动反色，文字带同色光晕 | `chapters`、`captions`（text 可为 `f => string` 实时显示参数）、`light`、`hideAt` |
| `BounceGraph` / `bounceAt` | 弹跳球 + 挤压拉伸 + 洋葱皮轨迹 + 触地帧号 + 播放头标签 | `contacts`、`heights`、`x0→x1`、`floor` |
| `drawHalftone` | 点阵径向波，波峰换两种强调色；`spawn` 从落点长出，`collapse` 收成一个点 | `ox/oy`、`spawn`、`collapse`、`tx/ty` |
| `drawRidges` | Unknown Pleasures 山脊线（带遮挡）；`chord` 把线压成圆的水平弦 | `spread`、`reveal`、`amp`、`chord`、`R` |
| `drawStrings` | 模乘弦图 i → k·i (mod n)；`enter` 从 48 条弦摆到位（接 `chord`）；`squash` 压成一条线 | `k`、`enter`、`extra`、`squash` |
| `drawPalette` | 线加宽 → 加厚成满屏面 → 裂成品牌色板（序号/色名/HEX）→ 交错滑走 | `grow`、`split`、`labels`、`exit` |
| `drawMarquee` | 实心/描边交替走马灯，进出场自带多采样运动模糊 | `words`、`enter`、`exit` |
| `drawTruchet` | Truchet 圆弧砖，按距离波逐块旋转、弧线重新连通；`hole` 清出放字的椭圆 | `assemble`、`hole` |
| `CubeStage` | 收集拍：主面板从全屏缩进 3×2 网格 → 排成立方体展开图 → CSS 3D 折叠（同一批 DOM，无缝）→ 旋转 → 27 块魔方 → 两次拧层 → 炸开；面顺序 0 前 1 右 2 后 3 左 4 上 5 下 | `st: {grid, net, fold, rx, ry, lift, scale, rubik, twists, explode}`、`gridOrder`、`heroCell` |
| `VolumeScene` | three.js：体素高度场（落下 / 波纹 / 中心下沉 / `flat` 铺平成地砖）→ 二十面体升起 → 逐级细分（`icoFaces` 给真实面数）→ 噪声黏土团 → 球 → `dark` 翻暗成半月形 + 珊瑚轮廓光 | `s: {wave, drop, sink, field, flat, rise, detail, amp, dark, cam}` |
| `ParticleField` | 6 万粒子一个 ShaderMaterial：球壳 / 星系 / 文字 / 图片（Logo SVG）/ 直线 五套目标，按 `stage` 连续混合，`burst` `noise` `spin` `point` 全在 shader 里算 | `stage`（0..4）、`text`、`image`、`R`（与黏土球投影半径对齐） |
| `drawVoice` | 一条线颤动成人声波形（音节包络 × 载波，主声 + 两条回声），长度对齐山脊线，交接给 `drawRidges` | `grow`、`amp` |
| `drawHalftone({ diverse })` | 点阵每个点有自己的颜色和形状（圆 / 方 / 菱形 / 环），讲包容 | `diverse`（0..1） |
| `GlyphAnatomy` | 字形解剖：度量线（x 高 / 基线 / 降部 + 真实数值）、轮廓描出、锚点（方）与控制点（圆）+ 手柄、填充、放大镜标出一个点的真实坐标和「1 UNIT = x PX」；数据用 `scripts/glyph_outline.py` 从字体导出 | `metrics`、`outline`、`points`、`fill`、`loupe`、`loupeAt` |
| `StrokeDraw` / `penAt` | 按顺序画路径 + 发光笔尖，`erase` 倒着收回；`MARK_PATHS` 是 YouWare 标志四条环形笔画中心线（从官方 SVG 描出），`VIBE_PATH` 是单线手写 vibe | `p`、`erase`、`width`、`glow` |

样帧：工程根目录的 `stills.mjs` 一次打包、一个浏览器渲一串帧（`render.sh film-stills` 已改用它，每帧 < 1s）。

## 路由（已写进 style-router.md）

- ② 视觉基调「**标本册编辑风**」：暗墨 + 暖纸交替，一个品牌主色 + 2–3 个辅色，衬线 / 单线手写 / 粗黑体按章换，规格书 HUD。
- ③ 叙事骨架「**概念阶梯**」：4–5 章可数递进，章节级接力，首尾同一个点。
- ④ 增强层：单个标本可拆出来用（快剪片插一段 `drawStrings` 讲连接；结尾用 `StrokeDraw` + `MARK_PATHS` 写 Logo；`ParticleField` 聚成 Logo 当高潮）。
- 触发信号：「Claude 那种」「官方质感」「品牌调性 / 品牌升级 / 品牌片」「不要具体功能演示」，产品有由小到大的层级。

## 人文层（60s 版的关键：用户要的「苹果那种人文感」）

几何阶梯只是骨架；每一章再挂一个**价值**，用一句宣言式短句说出来（一镜一句，≤ 8 个词，衬线细体，读完再切）：

| 章 | 几何 | 价值 | 标本 | 句子 |
|---|---|---|---|---|
| 序 | 光标 | 从小到大 | 光标闪两下 | Everything big starts small. |
| POINT | 点 | 包容 | 多色多形点阵 | No two people are alike. |
| LINE | 线 | 倾听 | 人声波形 → 48 条山脊线 | So we listen first. |
| LINE | 线 | 起点 | 点写 vibe | Vibe coding — an idea that went for a walk. |
| PLANE | 面 | 产品本身，一次一个 | 色板滑走 → **Apple 式变形链**（`examples/youware-ladder/YouWareChain.tsx`）：点 → 输入框打字 → 网站 → 幻灯片扇开 → 表格长出柱状图 → 报告（环形图）→ YouWare 头像剪影 → 你 + AI 专家（两个头像相对，重叠处深色）→ 专家团队 → 收回一个点 | HUD 只标 PROMPT / WEBSITES / SLIDES / SHEETS / REPORTS / YOU + YOUR AI EXPERT |
| PLANE | 面 | 人人可用 | Truchet 从链尾那个点打开 | From vibe coding to work, for everyone. |
| VOLUME | 体 | 体验 / 创新 | 魔方 → 细分黏土团 | Every detail, considered. / Refined, then reinvented. |
| FIELD | 场 | 协作 | 粒子 together. → 标志 | Made with people, for people. |
| 收尾 | 点 | 品牌 | 笔尖写标志 | From answers to outcomes. |

**中段用产品自己的细节，一次一个（学 Apple「Give people wonderful tools」）**：用户看过 Apple 那支设计片后明确要「一个个」——一个干净的浅色舞台、画面里永远只有一个居中物体、每个物体都是产品的标志性细节、前一个变形成下一个、没有人物也没有硬切，颜色只在标志性时刻出现。AI 生成的人物短片插在中间被评价为「突兀」，不要再用；人物感改由品牌自己的头像剪影（官网 agent 头像，两个头相对、重叠处深色）来承担。实现：一个容器矩形连续变尺寸（药丸 → 窗口 → 16:9 → 表格 → 竖版报告），最后用 `morphD`（按弧长重采样的逐点插值）从矩形变成头像；每一站的内容在容器变形时淡入淡出。每站约 1–1.2 秒，头像两站各留 0.6–0.8 秒让人读懂。

**抽象标本不要连着超过两段**：60s 初版在色板后接「字形解剖 + Eames 引语」，用户反馈「中间跳戏、像 Claude」——参考片的招牌手法一旦原样出现，就成了别人家的片子。换成客户画风里的真实人物（[ai-footage.md](ai-footage.md)：GPT Image 2 关键帧 → Seedance 2.0 图生视频），抽象标本只留在开头的点线和结尾的粒子；`GlyphAnatomy` 保留给字体 / 设计工具类客户。

配乐要**钢琴 / 弦乐、鼓少**：40s 版用 128 BPM 极简 techno，用户反馈「全是鼓点」。选曲前先算打击感（频谱通量均值 + 每秒起音数：参考片约 0.21 / 2.4，techno 0.31 / 4.3，Silent Descent 0.16 / 1.7），给用户 2–3 段 60s 试听再定。时间轴用半拍网格（71.8 BPM ≈ 0.84 s 一拍），曲子的爆发点落在粒子那一刀。**不要直接截参考片的配乐**：来源和授权不明，商用片会被版权识别下架；用授权曲库里特征接近的曲子。

## YouWare 样片 · 40s 快版（`examples/youware-ladder/Film.tsx`，128 BPM，每拍 14.06 帧）

| 章 | 拍 | 阶梯 → 品牌意义 | 标本 | 屏幕字 |
|---|---|---|---|---|
| 01 POINT · 0D | 0–12 | 一个想法 | 光标闪两下缩成点 → 打出 `idea`，点就是句点 → 字母掉落、点弹跳（关键帧曲线）→ 落点长出点阵波 → 收回一个点 | `idea.` |
| 02 LINE · 1D | 12–24 | Vibe Coding 起家 | 点一笔写出 `vibe`，再跳上 i 当那个点 → 山脊线 → 压成弦 → 模乘弦图 → 压成一条线 | Vibe coding — an idea that went for a walk. |
| 03 PLANE · 2D | 24–40 | 人人的 AI 办公 | 线变面 → 品牌色板（配色升级）→ 走马灯 → Truchet（连通 = 协同）→ 六个标本收成网格 → 展开图 | WEBSITES • SLIDES • SHEETS • REPORTS / From vibe coding to work, for everyone. |
| 04 VOLUME · 3D | 40–60 | 体验与创新 | 折成立方体 → 魔方拧两下 → 炸进体素地面 → 二十面体逐级细分 → 黏土团 → 球 → 翻暗 | Every detail, considered. / Refined, then reinvented. |
| 05 FIELD · ∞ | 60–72 | 协作的 AI 专家团队 | 球散成粒子（配乐 drop）→ 星系 → `together.` → 粒子聚成标志（四个举手的人）→ 线 → 点 | together. / Your AI expert team. |
| 签名 · Logo | 72–86 | 品牌 | 点当笔尖画出标志四笔 → 从笔尖开圆揭示暖纸 → 细线加粗成实心标志、转 90°（四重对称，无缝）换成官方 SVG → 字标滑出 → 标语句点最后弹出 | A BRAND FILM BY / From answers to outcomes. |

配色：象牙 `#F5F0E6`、开心果 `#CFE3A0`（主色）、鼠尾草 `#BBC98D`、苔绿 `#7D8F57`、青绿 `#4FA597`、薰衣草 `#B4A5E4`、珊瑚 `#EE8C6C`、墨 `#151513`（按 painterly SKILL.md 的描述取值；客户给官方色值后只改 `TH`）。字体 DM Sans + Hepta Slab（YouWare 站点字体），标志和字标用官方 SVG 做 CSS mask 上色。配乐 Minimal Emotion，break 落在黏土球翻暗前，drop 落在粒子爆开。

## 坑（样片里踩过的）

- **three.js 过曝**：`flat`（无色调映射）+ `StudioEnv` 的环境光会把地面和浅色体素打成纯白。用 `scene.environmentIntensity` 整体压到 ~0.3，主光再补亮；翻暗时环境光归零，灯按相机方向摆（侧后方主光 + 背后轮廓光）才出半月形。
- **ShaderMaterial 颜色**：`THREE.Color` 存的是线性值，自写 shader 直接输出会发暗；用 `getRGB(o, SRGBColorSpace)` 取 sRGB。加法混合时输出 `vec4(col, a)`，别再乘 a。
- **字体先到位再量**：用 canvas `measureText` 排字、采样粒子文字之前必须等 FontFace 加载完；Film 根部 `ready` 之前不渲内容。
- **可变字体描边**：DM Sans 等可变字体有重叠轮廓，`strokeText` 会露出内部线（R 的腿）。先描 2 倍线宽，再用底色 `fillText` 盖住。
- **收集拍的连续性**：网格 / 展开图 / 折叠 / 魔方用同一套面内容和同一个 `region` 映射，魔方贴纸行列按面朝向算（`stickerOf`），切换那一帧逐像素一致。
- **粒子 ↔ 黏土球对齐**：黏土球相机距离按「投影半径 = 粒子球 R」反算（fov 32、R=2.2 → 距离 12.55 对应 330px）。
- 所有运动都是帧号的解析函数（粒子噪声、体素下落、魔方拧层都不累积状态），并行渲染不跳。整片 1210 帧渲染约 30s（M 系列芯片）。
- 章节间「呼吸」只降音乐不空画面：塌缩中的点、压成的线一直在动。
- 技术注释必须是真实参数（点数、面数、公式里的 k 实时变化）；编不出真实参数就不写。
