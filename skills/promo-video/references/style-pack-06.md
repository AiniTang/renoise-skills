# 风格扩展包 06：商用风格库 · 第二批（补齐 15 种）

> 状态：**已建**。样片 `examples/style-catalog/`：11 个新 10s 样片 + 完整目录片 `Reel15.tsx`（YouWare · 十五种商用风格，175s，Remotion id `StyleReel15`）。第一批（目录片模板、综艺花字、贴纸风、等轴 2.5D、形变）见 style-pack-05。

来源同 style-pack-05（视频号「Opus 5.5 做视频达到商业制作水准的 15 种风格」）。这一批把剩下的 11 种都做成了可复用组件，每种都用 YouWare 当主体拍了一支样片。

## 什么时候用哪一种

| 组件 | 风格 | 适合 | 不适合 |
|---|---|---|---|
| `handdrawn/` | 逐帧手绘 | 温暖科普、儿童/教育、品牌吉祥物、「想法诞生」的时刻 | 需要大量真实界面的演示 |
| `lineart/` | 线条艺术（一笔画） | 叙事串联：一根线穿过所有产出；极简高级、编辑风 | 快节奏投流 |
| `collage/` | 拼贴风 | 作品集、年轻潮牌、「我们做过的东西」、复古杂志 | 精密科技调性 |
| （场景片，无单独组件）`FlatDemo` | 扁平插画 | 办公协作、SaaS 讲解、品牌插画体系已存在时（YouWare 头像） | 追求电影质感的品牌片 |
| （样片）`BauhausDemo` | 包豪斯动态海报 | 设计/艺术/字体相关、发布会海报、强记忆点的片头 | 需要温情叙事 |
| `glossy/` | 液态流动 | 品牌色展示、消费品/饮料/美妆、Logo 演绎 | 信息密度高的讲解 |
| `glass/` | 弥散渐变 · 玻璃拟态 | App/OS 风格界面展示、AI 助手、苹果系审美 | 纸质、复古调性 |
| `soft3d/` | 3D 软萌字 + 胶囊针阵 | 年轻、可爱、玩具感、节日；针阵浮雕做 Logo 揭示 | 严肃金融/医疗 |
| `fui/` | 赛博 HUD / FUI | 数据、安全、AI Agent 控制台、「任务执行中」 | 温暖生活方式 |
| `pixel/` | 像素风 | 游戏化、成就/闯关叙事、开发者社区、复古 | 高端奢华 |
| `retro/` | 复古合成波 Synthwave | 夜间/速度/音乐/80 年代怀旧、发布倒计时 | 浅色品牌、极简 |

## 组件

```tsx
import { SketchDefs, Paper, Stroke, penAt, Oneline, chainPen, segU, pathLen } from "../cinematic/lineart";
import { onTwos, BoilDefs, Rough, Hatch, Sparkle, Smear } from "../cinematic/handdrawn";
import { tornPath, Torn, Halftone, Ransom, Tape, Kraft, jitter } from "../cinematic/collage";
import { GlossyDefs, dropAt, Reflect } from "../cinematic/glossy";
import { Aurora, Grain, Glass, GlassMark, Thumb } from "../cinematic/glass";
import { SoftCanvas, PinField, usePuffGeometry, candy } from "../cinematic/soft3d";
import { WireGlobe, FuiPanel, Radar, Reticle, DataColumn, Readout, Scanlines, FUI } from "../cinematic/fui";
import { PixelStage, px, sprite, pixText, cycle, ridge } from "../cinematic/pixel";
import { SynthSky, StripedSun, NeonGrid, WireMountains, Palm, RoadSign, ChromeText, VhsOverlay, project, HORIZON, SYN } from "../cinematic/retro";
```

- **逐帧手绘**：`onTwos(t)` 把时间量化成一拍二；关键姿势写成数据表（`[帧, {dy, sx, sy, rot}]`），按两帧替换，不做平滑补间。`BoilDefs` 提供 `boil-a / boil-b`（两次不同扰动 → 双铅笔线）和 `crayon`（蜡笔颗粒）；`Rough` 画双线并可 `u` 写出；`Hatch` 蜡笔排线填色（逐笔写出）；`Sparkle` 四角星、`Smear` 速度线。
- **线条艺术**：`Oneline` 由首尾相接的段组成，每段有自己的帧窗口：在图形上慢、在基线上快；`chainPen` 给笔尖和镜头跟随；细节线用 `Stroke`，缩放后的路径加 `nonScaling`。**线 = 答案，填色 = 成果**：填色在线条闭合后才出，并错版 9px（印刷感）。
- **客户自己的线条画按笔顺画出来**（2026-10-02 某新茶饮品牌片）：品牌有现成的线描小人 / 插画时，不要自己重画，让原画「被画出来」。`scripts/pen_order.py <png> --start x,y [--group 名=x0,y0,x1,y1]` 把原画细化成中心线、在分叉处拆笔画、从起点按「就近接着画」排出笔顺，笔刷宽度跟随局部线宽（实心块自动是粗笔）；`scripts/vectorize_lineart.py` 把原画描成矢量（4K 不糊）；`cinematic/lineart/PenArt.tsx` 用笔画做遮罩、显示的永远是原画。`--group` 让一部分（如「hey!」字）单独弹出。起点选在细节端（杯子、手）而不是实心大块（头发），否则先冒出一个黑团。
- **拼贴风**：`Torn` 撕纸（白纤维边 + 内层再撕一次）；`Halftone` 是**真网点**：亮度×0.5 与径向网点×0.5 用 `plus-lighter` 相加，再 `contrast(40)` 在 0.5 处阈值，暗部大点、亮部小点，`ink` 上色、纸色正片叠底透出；`Ransom` 勒索信字母（混字体、混纸色、剪刀角）；`jitter` 一拍二抖动；`Kraft` 牛皮纸。
- **液态流动**：`GlossyDefs` = 模糊 + alpha 阈值（元球）+ 以自身 alpha 为高度图的漫反射/镜面光，`blur / dome / light` 都可逐帧动画；`dropAt` 下落、压扁、两次回弹、果冻抖动；`Reflect` 镜面倒影（遮罩渐隐）。
- **玻璃拟态**：`Aurora` 品牌色弥散光斑（`screen` 叠加）+ `Grain` 颗粒防 H.264 色带；`Glass` 真 `backdrop-filter` 磨砂 + 顶部高光边 + `sheen` 扫光；`GlassMark` 同样的磨砂裁成标志形状（mask）；`Thumb` 截图裁切进卡片（用 `<Img>`，等图片加载）。
- **3D 软萌字**：`SoftCanvas`（透视相机、Studio 环境反射、软阴影、轻移轴、透明背景）；`PinField` 实例化胶囊针阵，高度和颜色都是 `(i, j, x, z, t)` 的纯函数，每帧重算（2000+ 根没问题）；`usePuffGeometry` 把 SVG 字形挤出成圆鼓鼓的软字（深倒角）；`candy()` 糖果清漆材质。
- **赛博 HUD**：`WireGlobe`（经纬网、程序化陆地点、弧线 `setDrawRange` 生长、脉冲、辉光）、`FuiPanel`、`Radar`、`Reticle` 锁定准星、`DataColumn` 滚动数据列、`Readout` 跳动读数、`Scanlines`。
- **像素风**：`PixelStage` 真 320×180 画布最近邻放大；`sprite` 字符串精灵；`pixText` 5×7 点阵字；`cycle` 调色板轮换（天空/湖面流光）；Bayer 4×4 抖动淡入。
- **复古合成波**：`project(x, z)` 2D 透视投影（地平线 600）；`StripedSun`（mask 挖出标志）、`NeonGrid`、`WireMountains`、`Palm`、`RoadSign` 路牌呼啸、`ChromeText` 铬字、`VhsOverlay`（扫描线、色偏、OSD）。

## 配乐与音效（`examples/style-catalog/tools/build_audio.py`）

- 3 分钟目录片没有够长的曲库曲：**按小节无缝延长**——`precise_grid` 测 BPM 和首个强拍，在能量最接近的两处小节边界之间重复 16 小节（40ms 交叉淡化）；片尾不要直接取「最后 N 小节」——曲库曲常以一记重音 + 混响淡出收尾，最后几小节只有 −37 dB 的尾音，会像静音。脚本找到那记收尾重音（后半段第一个比中位响度低 12 dB 的小节），取它前 2 小节 + 重音 + 2.35s 尾音做 `ending.wav`，让重音落在片尾标语升起那一帧；主曲的重复长度也按「到重音为止」计算，否则第 13 格前就唱到结尾，片尾又唱一遍。
- 最后三格换成代码合成的复古配乐：HUD 暗脉冲（无鼓）、芯片音乐（25% 方波主旋律 + 三角波贝斯 + 轻噪声镲）、合成波（去谐锯齿铺底 + 16 分琶音 + 轻底鼓）。各段前后 18 帧交叉淡化，**鼓都压得很轻**（用户不喜欢鼓点多）。
- **只改配乐时不用重渲画面**：`npx remotion render … out/mix.wav --codec=wav --config=remotion.audio.config.ts`（主配置里的 CRF 会让 wav 报错），再 `rn finish out/film.mp4 -o out/film-v2.mp4 --audio out/mix.wav --copy-video`：画面原样复制，音频按样本数裁到画面长度，不会少帧。
- 合成方波低音（55Hz）要先低通（~320Hz）：原始方波边沿太陡，`rn qa` 的 `clicks` 会每个八分音符报一次，听感也刺耳。
- 像素样片的音效也是合成的：`chip-jump / chip-bump / chip-coin / chip-fanfare`，时间点来自 `PIXEL_CUES`。

## 坑（样片里踩过的）

- **SVG 滤镜的 `userSpaceOnUse` 区域在被变换的局部坐标里计算**：把带滤镜的路径放进 `translate/scale` 过的组，局部坐标一旦为负就被裁掉（手绘头像只剩一条线）。解决：用 `@remotion/paths` 的 `warpPath` 把路径变换到世界坐标，滤镜放在不变换的外层组上。
- **three.js `geometry.scale()` 会原地重算 `boundingBox`**：先存的 `bb = g.boundingBox` 被改成缩放后的值，居中/落地位移全错（软字母偏到一边、沉到针阵下面）。先 `.clone()`。
- **只镜像 y 会让三角形绕序反转**，背面剔除把整个字吃掉。SVG → three 用 `scale(k, -k, -k)`（等于绕 x 转 180°）。
- 液态：滤镜模糊约为最小液滴半径的 0.2；字母要 ≤10 才保住字怀。大液滴用大 `dome`（30）才有球面高光，转成字时降到 11。
- 包豪斯里「用原色几何拼回标志」：先看清标志结构（YouWare 标志 = 四条同样的「波浪 + 水滴环」绕中心），拆真实路径的四边上色，比自己用拱形/折线重画更像。`markPath.ts` 里已有 `MARK_SIDES`。
- 玻璃：`backdrop-filter` 不要放进 3D 变换；模糊 < 24px 会透出色块而不是磨砂；弥散光斑太满会发浑，留出暗部。
- 拼贴：勒索信字母别用手写体（Caveat 的 U、W 认不出）；网点单元 6–7px 在 1080p 下读成印刷质感。
- 手绘：姿势表里给挤压/拉伸（落地 1.18×0.8）、预备、过冲；眨眼只要两帧。
- 目录片 15 格：片尾墙改成 5×3 网格（`wallGrid`，从中间一圈圈飞出）。**片尾墙必须用低清代理**（`CatalogItem.thumb`，640×360、`-g 6`）：15 路 1080p 同时解码，单帧 37s，整片渲染到第 23 分钟 delayRender 超时失败；换代理后 1.1s/帧。整片渲染加 `--timeout=120000`；每个样片都预渲染（Three.js 必须）；信息卡中文定稿后重新 `fonts.py subset`。
- 数字只写真的：针阵写「两千根」是因为 62×34=2108；拼贴批注「3 scenarios」来自截图里真实的 Bear/Base/Bull 三列。

## 字体（本批新增，均 OFL）

包豪斯 `Unbounded`；拼贴 `Anton` + `DM Serif Display`（勒索信混用全部已有字体）；液态/软萌 `Bricolage Grotesque`、`Fredoka`；手绘/线条 `Caveat`；标语统一品牌 `Hepta Slab`。
