# 风格扩展包 05：商用风格库 · 第一批（风格目录片 / 综艺花字 / 贴纸风 / 等轴 2.5D）

> 状态：**第一批（P0）已建**，样片 `examples/style-catalog/`（YouWare · 四种商用风格，54s，Remotion id `StyleReel`，每种风格也有独立 10s 组合 `Variety` / `Stickers` / `Iso` / `Morph`）。第四种风格复用 style-pack-03 的形变链。

由来：拆解视频号「Opus 5.5 做视频达到商业制作水准的 15 种风格」（179s，15 种 × 约 11s）。逐项对照后，我们已有 2 种（线条动画、形变动画）、近似 1 种（弥散渐变玻璃）、部分 10 种、缺 2 种。第一批补最常用的三种画风 + 目录片这个「形式」本身；其余见文末路线图。

## 什么时候用

| 组件 | 适合 | 不适合 |
|---|---|---|
| `StyleCatalog` 风格目录片 | 一个产品换多种画风讲、作品集、模型/工具能力盘点、「N 种风格」合集、给客户选风格的提案片 | 单一卖点的投流片（用快剪或场景三连） |
| `variety/` 综艺花字 | 社媒投流、产品录屏的「反应」时刻（等等？！太快了！）、日韩市场（接近日本电视テロップ）、竖屏 9:16 | 品牌调性片、需要克制的发布片 |
| `sticker/` 贴纸风 | 科普讲解、「一个产品 N 种能力」、功能盘点、年轻消费品、教育 | 暗场科技调性；素材只有长截图时（贴纸要能一眼认出） |
| `iso/` 等轴 2.5D | 讲「搭建 / 生长 / 规模 / 生态」：一句话长出一座城、数据中心、工作流街区；SaaS、基础设施、城市/地产 | 需要真实产品界面的演示段（界面可以做成广告牌/卡片贴图，但读不清细节） |

## 组件

```tsx
import { StyleCatalog, CATALOG, catalogLength, type CatalogItem } from "../cinematic/catalog";
import { HuaZi, HUAZI, Burst, SpeedLines, Mark, Confetti, Telop, zoomPunch, shake } from "../cinematic/variety";
import { Sticker, StickerDefs, StickerBoard, Tape, Label, Doodle } from "../cinematic/sticker";
import { IsoCanvas, IsoTile, House, Billboard, Bars, Library, Tree, Mark3D, IsoCard, useCanvasTexture, ISO_ELEV } from "../cinematic/iso";
```

**StyleCatalog**：`items: CatalogItem[]`（`no / zh / en / desc[] / tags[] / work / tint / accent / Sample`），`fonts`，`header`，`Intro`，`Lockup`。每格 330 帧（开窗 18 · 样片 300 · 收窗 16），片头 105、片尾 195：`catalogLength(n)`。窗口从圆点开出、收回圆点，圆点弹簧移到下一个窗口中心（信息卡左右交替），**全程没有硬切**；片尾所有样片 2×2 仍在播放，再落 Lockup。样片组件用自己的 `useCurrentFrame()`（放在 `<Sequence>` 里），所以任何 10s 片子都能直接当一格。

**综艺花字**：
- `HuaZi`：多层描边 + 渐变填充 + 硬投影，**每个字叠层绘制**（最宽描边在最底、填充在最上），可变字体的重叠轮廓和描边内侧永远被上一层盖住。`pop`: `spring`（弹出）/ `slam`（砸下）/ `drop`（从上掉）/ `wave`（波浪）；`\n` 换行；`out` 帧缩小淡出。预设 `HUAZI.shock / cute / cool / fresh / note`（外 → 内的描边层 + 填充）。
- `Burst` 爆炸星形衬底、`SpeedLines` 漫画速度线（每 2 帧重新随机，像手绘）、`Mark` 反应符号（汗滴 / 闪光 / !! / ? / 爱心）、`Confetti` 彩纸、`Telop` 电视底栏（带状态小标签，文字逐字出）、`zoomPunch()` 冲击推镜、`shake()` 震屏。
- 字体：`bold-playful`（Bricolage Grotesque 800 · 站酷庆科黄油体 · Mochiy Pop One），用户选定。

**贴纸风**：
- `<StickerDefs />` 每个组合挂一次，提供 `url(#stk-6|8|12|18)` 模切滤镜：alpha 膨胀 → 轻模糊 → 阈值 → 白色，**沿内容 alpha 走**（透明 PNG 得到轮廓切割，圆角截图得到圆角白边）。
- `Sticker`：「啪」地落下（大 → 过冲 → 稳），落地时阴影由远变近变实；`from` 上方 / 左 / 右；`out` 揭走。`Tape` 和纸胶带（锯齿边）、`Label` 药丸标签、`Doodle` 手绘箭头/圈（描线动画 + 箭头）、`StickerBoard` 点阵切割垫底。
- 批注用 Caveat（hand-note），标题用品牌衬线（本例 Hepta Slab）。

**等轴 2.5D**：
- `IsoCanvas`：真等轴正交相机（45° / 35.264°）、`zoom`（1 世界单位 = zoom 像素）、`yaw` 慢转、`target`、NeutralToneMapping、PCF 软阴影、`TiltShift2` 移轴（**水平焦带** `start [0,0.52] → end [1,0.52]`，blur 0.08）。
- 构件都收 `t, at` 并按弹簧从地面长出：`IsoTile`、`House`（挤出屋顶）、`Billboard`（面板贴 canvas 纹理，**旋转 +π/4 才朝向相机**）、`Bars`（柱子依次长）、`Library`（分层落下 + 穹顶）、`Tree`、`Mark3D`（SVGLoader 挤出品牌标志，品牌 2.0 的 mark.svg 直接可用）、`IsoCard`（始终朝向相机的数据卡，canvas 文字）。

## 做法与坑（样片里踩过的）

- **花字要有「素材里的真反应」**：三拍（提问 → 加速 → 震惊）都卡在录屏的真实节点上；屏幕上的倍速标签写真实播放倍率（`▶▶ ×7` = `playbackRate 7`），不编「省时 90%」这类数字。
- 贴纸：先排「中心留空」——标签贴在每张截图的**外角**，胶带跨在截图接缝上，中心留给主角贴纸（本例大「4」）。标题别被第一张贴纸压住（标题 72px 足够）。
- 贴纸落地后的轻呼吸（0.4% 缩放）让静帧也是活的；超过 5 张就错开 7–26 帧，别同时落。
- 等轴：卡片数字必须等于场景里真实数量（`HOUSES · ${lot.length}`）。高楼放在远离视线的两翼，不要放在镜头与中心塔之间；标志要**朝向相机**（绕 Y 转到 45°+yaw，再往相机仰 0.55×35°），一直自转会变成侧面的黑色花瓣。
- **目录片的样片先预渲染成视频**（`CatalogItem.video`），再在窗口和片尾墙里播放。直接把 Three.js 样片放进 CSS 缩放的窗口会出错：R3F 用 `getBoundingClientRect` 量画布，量到的是缩放后的尺寸，场景只画在左上角一小块；片尾墙（缩到 0.4）里更是整块空白（单帧 still 却是好的，只有整片渲染才暴露）。纯 DOM/SVG/canvas 的样片可以用 `Sample` 现场渲染。
- 每个样片比屏幕上多渲 30 帧（330），窗口收回圆点的 16 帧里画面仍在动；否则素材先结束，收窗时露出空底色，`rn cuts` 会报硬切。
- 片尾墙样片从第 150 帧开始播（`startFrom`），展示每种风格的高潮段。页眉在片尾墙出现前隐藏。
- 字体子集：信息卡中文 141 字，Noto Serif SC 24.5MB → 122KB（`fonts.py subset`），否则每个渲染标签页都要加载 40MB 字体。

## 路线图（15 种里剩下的）

> **已全部完成**，见 [style-pack-06.md](style-pack-06.md)（2026-09-30）。下表保留当时的差距分析。

| 批次 | 风格 | 我们现在 | 要补的 |
|---|---|---|---|
| P1 | 赛博朋克 HUD / FUI | `Hud`、规格书 HUD、`XRayReveal` | 线框地球、雷达扫描、锁定准星、滚动数据列、跳动读数 |
| P1 | 像素风 | 像素头像、体素、像素字体 | 320×180 低分辨率画布最近邻放大、精灵/瓦片地图、调色板轮换光效、芯片音乐 |
| P1 | 复古 Synthwave | — | 霓虹网格地面、条纹太阳、铬/霓虹字、VHS 扫描线 + 合成器配乐 |
| P1 | 液态 / 玻璃拟态升级 | `Goo`、`aurora`、`GlassBar` | 高光折射的液滴与液态字、真实毛玻璃折射 + 边缘光、流动网格渐变 |
| P2 | 逐帧手绘 | ai-teardown 极简手绘（图示） | 抖动笔刷线（一拍二）+ 角色骨骼（挤压、眼睛、嘴） |
| P2 | 拼贴剪贴 | 剪纸、古画档案镜头 | 撕纸遮罩、网点印刷、印章胶带、人像剪影拼贴 |
| P2 | 几何构成 · 包豪斯 | `SHAPES` | 三原色构成海报系统：构成线、几何块飞入归位 |
| P2 | 扁平矢量插画 | lucide、`IconTile` | 形状拼出的场景库（天空/城市/人物/道具） |
| P2 | 3D 软萌字 + 胶囊阵 | 金属 Logo、黏土球、6 万粒子 | 挤出 3D 字 + 软材质，受滚球冲击的胶囊阵（原片用 Blender Cycles，我们用 Three.js 近似） |
| 形式 | 每种风格配专属音乐 | 曲库 + `synth_bgm.py` 五种情绪 | 芯片音乐、合成器琶音、马林巴等按风格合成 |
