# 电影级宣传片（Film 模式）

模板片（`Promo` 合成，storyboard 驱动）快，但观感接近 PPT。产品发布、品牌片、用户要求「酷炫 / 有设计感」时用 Film 模式：手写一个 `src/Film.tsx`，用 `src/cinematic/` 的场景组件拼接，核心是**还原真实产品界面并演示一次完整操作**。

参考实现：`templates/remotion/examples/youware/`（`Film.tsx` + `ProductUI.tsx`，约 33 秒，暗场科技风）；`examples/kit-lab/KitLab.tsx`（剪纸风 + 报告生成，约 13 秒）；`examples/renoise/`（AI 视频平台品牌片，约 28 秒，全部用官网视频素材）。复制到项目 `src/` 后改内容，再在 `Root.tsx` 注册：

```tsx
<Composition id="Film" component={Film} defaultProps={storyboard as unknown as Storyboard}
  width={1920} height={1080} fps={30} durationInFrames={FILM_FRAMES} />
```

渲染（沙箱外、整片后台跑，见 SKILL.md「渲染约束」）：`render.py <项目目录> film-stills 50 400 …` 抽帧，`film-preview` 半分辨率预览，`film` 出成片 `out/film.mp4`。

## 风格

先读 [design-principles.md](design-principles.md)：它是所有风格共用的底线（一屏一想法、统一图标、有动机的运镜、审片清单）。`IconTile` 提供应用图标式的功能图标底板。

先定风格，再选组件。同一支片只用一种主风格，其他风格的组件只作点缀。

| 风格 | 适合 | 主要组件 | 画面与声音 |
|---|---|---|---|
| 暗场科技（默认） | AI、SaaS、开发者工具、金融科技 | `Opener`、`Carousel3D`、`Gallery3D`、`EndCard` | 深底、金属 Logo、Bloom 与景深、快速推拉；`whoosh`、`slam`、`impact` |
| 剪纸 | 教育、文旅、消费品、公益、节日营销、儿童 | `PaperCut3D`，配浅底 `KineticList`、`DeviceSwing` | 多层纸片、真实投影、慢推与视差、纸签标题；`paper-place`、`swish`、`cut`、`page` |
| 浅色编辑 | 内容、办公、设计、生活方式 | `KineticList`、`ProofBeats`、`ReportBuild`、`DeviceSwing` | 米白底、衬线大字、按拍翻色；`slam`、`tap`、`page` |
| 东方星图 | 带中文诗意/国风品牌、工具类 App、文化产品 | `VerticalPoem`、`SolarSystem3D`，截图界面动效，米白底口碑/定价页 | 深空 + 宋体竖排诗句、行星与主题色一一对应，明暗段落交替；配乐 `eastern`，`page`、`tap`、`pop` |
| 温馨暖色 | 个人助理、家庭、生活服务、情感向品牌 | 吉祥物圆窗（羽化遮罩让素材白底变成柔光）、按一天时间推进的任务卡片、夜晚收尾 | 桃色晨光 → 暖紫傍晚 → 台灯夜色，圆体字，柔和散景；配乐 `calm`，只用 `pop`、`done`、`swish` 等轻音效，响度约 −18 dBFS |

浅色编辑风的常见结构：大字 `◆ 词` 标题 + 浮动作品卡片开幕，随后左插画、右重建产品面板的分屏演示，一幕一个动作。

「场景模拟」不是独立风格：任何风格都用自写的产品界面（`ProductUI`）或 `ReportBuild` 还原真实使用过程，这是宣传片说服力的核心。

新增风格时：定一套调色、材质（纸、金属、玻璃……）、镜头节奏和音效组合，做成 `src/cinematic/` 下的一个场景组件，导出时长函数和 `xxxCues()`，用样帧验证后登记到上表。

## 结构

| 段落 | 组件 | 时长 | 作用 | 接下一段的转场 |
|---|---|---|---|---|
| 冷开场 | 物理弹跳 / 品牌物件飞入（motion-craft.md） | 2–4 s | 用一个动作抓住眼睛，引出口号 | 匹配剪辑：物件变成线、光标或 Logo |
| 开场 | `Opener` 或自写 3D Logo | ~3 s | 3D 金属 Logo 旋入 → 口号揭示 | 穿越 Logo 或猛推 |
| 主演示 | 自写 `ProductUI` | 7–9 s | 真实界面：打字 → 选项 → 点击发送 → 界面变形 → 任务进行 → 成果生成 | 成果卡片飞出，接卖点 |
| 卖点 ×3–5 | 优先用官网图：`Carousel3D`（头像）、`Gallery3D`（成品截图）、`DeviceSwing`（真机图）、`ProofBeats`（产品里的核查/公式）。`KineticList` / `CubeField` 只在该卖点没有产品视觉时才用 | 各 3.5–4.5 s | 每个卖点换一种镜头语言，画面主体必须是用户的素材 | `CircleWipe`、`SlatReveal`、匹配剪辑交替使用 |
| 高潮 | 默认用成品截图或 CTA 猛推；`ParticleText` 仅当用户明确要秀动效、且口号能叠在产品画面上 | ~2.5 s | 把产品成果推到最大 | 匹配剪辑接收尾 |
| 收尾 | `EndCard` | ~2.5 s | 开场物件回来 → Logo 落位 + 字标 + CTA + 网址 | — |

主演示占全片 25–30%，是说服力来源；卖点段按「人 → 规模 → 可信 → 成果 → 场景」这类递进排序。

## 品牌接入

```tsx
<BrandProvider brand={brandFromStoryboard(sb, { ink: "#141414" })}>…</BrandProvider>
```

- `brandFromStoryboard` 读 `brand.fonts / colors / logo / wordmark`；`primary → accent`、`accent → accent2`、`dark → ink`、`background → paper`。电影段落底色宜比品牌 `dark` 更深，用第二个参数覆盖。
- DOM 场景用 `V.accent`、`V.display` 等 CSS 变量；Three.js 材质需要具体色值，用 `useBrand()`。
- SVG 的 `fill/stroke` 要写在 `style` 里，CSS 变量不能用在表现属性上。
- `Opener/EndCard` 把 `brand.logo` 挤出成 3D，Logo 必须是纯路径 SVG（无位图、无渐变）。没有 SVG 时改用平面 `<Img>` 做 2.5D 版本。

## 场景组件

| 组件 | 关键参数 | 时长 |
|---|---|---|
| `Opener` | `headline: string[]`（最后一行用强调色） | 96 帧，建议 Sequence 给到 98 |
| `EndCard` | `cta?`、`url?` | ≥ 70 帧 |
| `Carousel3D` | `items: {img,name,status}[]`、`step=20`、`title` | `12 + n*step + 14` |
| `KineticList` | `intro`、`outro`、`items: {label,icon?}[]`、`beat`、`tag?`、`palette?` | `beat * (n + 4)` |
| `ProofBeats` | `beats: {text, visual}[]`、`each=40`、`eyebrow?`；visual 为 `checklist / formula / lock` | `n * each + 10` |
| `Gallery3D` | `panels: {img,label}[]`、`title`、`aspect` | `galleryFrames(n)` |
| `PaperCut3D` | `title`、`subtitle?`、`palette?`（后→前）、`layers=6` | ~130 帧；音效 `paperCutCues(offset)` |
| `ReportBuild` | `title`、`kicker?`、`meta?`、`sections: {heading, paragraphs?, chart?, table?, insight?}[]`、`background?` | `reportFrames(props)`；音效 `reportCues(props, offset)` |
| `VoxelIntro` / `VoxelOutro` | `data: VoxelData`（像素图转体素）、`name`、`role`、`tag?`、`explodeAt?`；结尾 `handle`、`line`、`links?` | 开场 90 帧、结尾 ≥ 90 帧；音效 `voxelIntroCues` / `voxelOutroCues` |
| `TerminalDemo` | `window`、`prompt`、`steps: {label, detail}[]`、`result`、`outputs?: {title, kind}[]`、`caption?` | `terminalFrames(props)`；音效 `terminalCues(props, offset)` |
| `RepoStack` | `repos: {name, desc, stars, lang, langColor}[]`、`title`、`total?`、`totalLabel?`、`owner?` | `repoStackFrames(n)`；音效 `repoStackCues(n, offset)` |
| `StatSlam` | `stats: {value, prefix?, suffix?, label}[]`、`beat`、`title?` | `statSlamFrames(n, beat)`；音效 `statSlamCues` |
| `FlowPipeline` | `nodes: {icon: LucideIcon, label, sub}[]`、`title`、`kicker?`、`base?` | `flowFrames(n)`；音效 `flowCues(n, offset)` |
| `VideoMontage` | `clips: {src, from?, label?}[]`、`beat`、`beatsPerClip=2`、`words?: {beat, text, accent?, clear?}[]`、`letterbox` | `montageFrames(n, beat)`；音效 `montageCues` |
| `PromptToVideo` | `prompt`、`models`、`pick`、`startModel`、`heroVideo`、`result`、`nav / tools: {label, icon: LucideIcon}[]`、`scenarios`、`mark?` | `promptFrames(props)`；音效 `promptCues(props, offset)` |
| `TemplateWall` | `templates: {src, from?, title}[]`、`center`、`title`、`subtitle`、`cta`、`upload: {img, name, hint}` | 150 帧；音效 `templateWallCues` |
| `ToolBeats` | `items: {src, from?, word, effect: upscale / expand / consistent / reshoot, badge?}[]`、`beat` | `toolBeatsFrames(n, beat)`；音效 `toolBeatsCues` |
| `DeviceSwing` | `image`、`title`、`body` | ~110 帧 |
| `SolarSystem3D` | `sun: {img, size, label}`、`bodies: {img, r, size, speed, phase, label}[]`、`cam`（x/y/z + 注视点关键帧）、`dive?: {index, at, dur}` | ~140 帧；行星用抠图 sprite，结尾可冲向某颗星接下一章 |
| `VerticalPoem` | `lines`、`at`、`stagger=3`、`size=64`、`out?` | 竖排从右到左，逐字由模糊晕开 |
| `FoldablePhone3D` | `keys: PhoneKey[]`（`open` 0 合上/1 展平、`ry/rx/rz`、`x/y`、`camX/Y/Z`、`lookX/Y`、`inner/outer` 屏幕亮度、`focus`、`ease`）、`screens: {from, mode: wallpaper / split}[]`、`dof?` | 任意；一支片内多段可共用一个实例一镜到底 |
| `ChipReveal3D` | `title`、`sub`、`accent?` | ~120 帧；芯片从电路板升起，走线脉冲，俯视转斜侧推近 |
| `DualBattery` | `value`、`unit`、`label`、`note` | ~90 帧；双电芯充能 + 数字滚动 |
| `CubeField` | 无（改文件内 `N / LOW / HIGH`） | 75 帧；576 个实例方块按距离做正弦波，镜头俯视 → 斜侧环绕 → 回俯视塌平 |
| `MotionKit` | `KineticHeadline`（逐字标题，中文可用）、`Stage`（2.5D 镜头 + 甩镜）、`beatPulse`、`KineticWord`（`step / elastic / wave / strips / rise`）、`IrisReveal`、`CircleWipe`、`SlatReveal`、`ShapeMorph` + `SHAPES / morphPath`、`Hud`、`FilmGrain`、`ELASTIC` | 用法见 motion-craft.md「手艺地图」 |
| `ParticleText` | `text`、`size`、`colors`、`count`、`font`、`background` | 75 帧；Canvas 画 6500 个粒子：旋涡 → 汇成文字 → 抖动停留 → 径向炸开带拖尾 |

段落之间 Sequence 重叠 6 帧，靠组件自带的淡入淡出衔接。`beat = 30 * 60 / bpm`，列表类场景按拍切换。

## 还原产品界面（主演示）

1. 从官网截图/录屏确定真实布局：输入框、侧栏、消息气泡、结果面板。用 DOM 重建，不贴整张截图；截图只作为结果面板里的内容。
2. 打字：`typingSchedule(text, start, perChar, seed)` 生成带抖动的逐字时间，`typed(text, times, f)` 取当前文本；空格和标点后停顿更长。光标闪烁按帧算。
3. 鼠标：贝塞尔路径移动到按钮 → 按下缩放 0.92 → 点击涟漪；点击帧导出为常量（如 `CLICK_AT`）供音效对齐。
4. 状态变形：输入框缩放平移成对话输入栏，工作区窗口从下方升起，不要硬切。
5. 任务进度：代理/步骤逐个出现，spinner → 对勾，进度条推进；结果区逐块搭建（标题打字、色块弹出、柱状图生长、扫光）。
6. 2.5D 镜头：整个界面放在一个 stage 上，用 `track(f, keys)` 做关键帧推拉摇（`x/y/scale/rotateX/rotateY`），在关键动作处推近，结尾猛推（slam）接下一段。只在镜头偏离中心时给远处加 CSS blur 模拟景深。
7. 所有时间点（`PROMPT_T`、`CHIP_AT`、`CLICK_AT`、`TOAST_AT`、`UI_FRAMES`）从 ProductUI 导出，Film 用它们排音效和后续段落。

## 动效规则

- 缓动来自 `motion.ts` 的 `E`（GSAP `parseEase`，按帧求值）：入场 `E.out`（expo），离场 `E.in`，强调 `E.back`，推拉 `E.inOut`。`seg(f, start, dur, ease)` 得到 0–1 进度，`mix(a, b, p)` 插值。
- 标题逐字/逐词揭示：每个字 `translateY(110%) + rotate + blur` → 0，间隔 0.9 帧；逐词揭示要给每个词单独的 overflow 遮罩，词间用 `columnGap`（不要依赖空格字符）。
- 运动模糊 `CameraMotionBlur` 只包裹快速帧（镜头猛推、列表切换前 4 帧），samples 5–6；全程开启会糊且渲染时间乘以 samples。
- 每段至少有一个「主动作」（旋转、穿越、猛推、翻色）和一个「细节动作」（打勾、计数、光标、扫光）。主动作从 motion-craft.md 的手艺地图里挑，段落接缝按其中「转场设计」写进分镜。

## 用截图做界面动效

官网只有高清截图、没有可交互界面时，不要整张贴图平移，而是让截图「活」起来：

1. 测出窗口边界，裁成只含窗口、带圆角透明边的 PNG（去掉桌面壁纸），统一放进品牌背景。
2. 用 `scripts/screenshot_regions.py` 把要动的区域（标签栏、行星/主视觉、数字、列表行、卡片、色块）按左右邻近背景逐行插值抹掉，得到 `empty-<页>.png` 与 `regions.json`，并输出红绿框预览核对坐标。
3. 片中先放空状态，再按时间表把原图对应区域裁出来逐块长回（淡入 + 上移 + 0.97→1 缩放）；数字类用 DOM 重写并滚动计数，标签栏用 DOM 重建，让选中胶囊在章节间滑动。
4. 章节开头让主视觉（行星、产品图）全屏出现，再飞进截图里它原本的位置完成匹配剪辑；位置用像素检测测准到 1–2 px。
5. 镜头推近要读的细节（残留路径、清单、进程表），说明文字在推近前淡出，避免压住焦点内容；右键菜单、光标、点击涟漪等交互只演示官网写明的功能。

## 用产品自己的视频素材

产品本身产出视频或图片（AI 生成平台、相机、剪辑工具、游戏）时，官网 `<video>` 素材就是最好的镜头：

- 在浏览器里执行脚本收集 `video.currentSrc` 与 `poster`，按 brand-from-website.md 下载到 `public/video/`；带过期签名的链接要当场下载。逐个用 `npx remotion ffprobe` 看时长和分辨率，截 3 帧看内容再分配镜头。
- 视频用 `<OffthreadVideo muted startFrom={秒 * fps}>`，`objectFit: cover`。竖版素材放进竖卡片（`TemplateWall`），不要硬塞进横版全屏。
- 混剪每拍一切，镜头标签只写能确认的事实（首页大片对应的模型名、官网场景分类），不给素材编造模型或参数。
- 界面演示里的生成结果用真实素材，模板/上传类交互只演示操作流程，不伪造「照片 → 成片」的结果。
- Logo 是「底框 + 图形」时，只取白色图形路径另存 SVG 做 3D 挤出；字标颜色写死在 `var(--fill-0, …)` 里的，另存一份纯黑版给 `EndCard` 反色。

## 作品合集与动效作品集

- 多支成片剪成一分钟内的合集：见 [recap.md](recap.md)。
- 动效层（每段的主手艺、段间转场、首尾呼应）和纯动效作品集：见 [motion-craft.md](motion-craft.md)。

## 个人品牌与像素头像

个人介绍片用 `VoxelIntro/VoxelOutro` 把头像做成 3D 体素：头像缩到约 56×56（`ffmpeg -i avatar.png -vf scale=56:56 small.png`），逐像素读色，去掉背景色后存成 `{w, h, voxels: [[x, y, "#rrggbb"], ...]}`（y 向上），约 1500 个方块。像素风或插画头像效果最好；真人照片先转成像素风再用。简历里的手机号、邮箱等私人信息不上屏。

## 报告与文档模拟

`ReportBuild` 把一页报告「现场写出来」：标题与小标题打字，段落逐行出现（先灰条后文字）并弹出引用角标，柱状图生长、数字滚动，表格逐行填入，结论框扫亮；镜头在每块开始时推到位并停住，写完后拉远露出整叠纸。

- 内容要像真报告：具体数字、单位、来源数，不写占位文字；用户没给的数据标注为示例。
- 每节最多 1 个图表或表格，整份 2–3 节，时长 8–10 秒。中文段落自动按字宽估算行数。
- 做幻灯片、表格、网页等其他产出时照同样思路：真实版式 + 逐块生成 + 镜头跟随写入点。

## 实体硬件产品

手机、耳机、手表等实体产品用程序化 3D 模型演示，不用渲染图贴片。组件见 `src/cinematic/` 下的 3D 设备与芯片组件（折叠屏、芯片揭示、景深相机）。

- 先查官方规格（尺寸、屏幕、芯片、影像、续航、价格、发售日），标题只写查到的事实；用户给的名称与官方不符时按官方名并在回复里说明。
- 一个模型实例贯穿开场 → 外观 → 形态变化 → 细节：用关键帧驱动开合角度与镜头，而不是每段重建模型，镜头才连贯。
- 必拍镜头：黑场侧光揭幕（边框一条亮线）、正面亮屏、形态变化（展开/折叠）、侧面薄度（`ry ≈ π/2`，标题移到下方）、背面摄像头微距（相机距离约 4，镜头放在画面上半部）。
- 镜头要分层：金属环 → 黑色遮光圈 → 镜片环 → 虹彩镀膜中心 → 半透明深色玻璃罩；屏幕上盖一层透明反射玻璃，转动时有光扫过。
- 不出现品牌 Logo 和官方广告素材；结尾加一行小字「Independent concept film · Not affiliated with <品牌>」。
- 为品牌自己做片、官网只有正反面产品渲染图时：把两张透明底 PNG 贴在按真实尺寸比例建的圆角卡片两面，侧边用半透明材质补出厚度；测出屏幕在图中的像素区域，叠一块可替换内容的屏幕平面（静态图或逐帧 canvas），让设备在不同段落「运行」身份卡、安装进度、游戏；爆炸图把正面层与背面层沿 z 轴拉开，外加两块带描边的透明盖板；部件标签用同一套相机参数投影到屏幕，部件所在面背对镜头时隐藏。只标注在图上能确认位置的部件，其余部件用文字列出。

## 旁白配音

需要配音时用 `scripts/voiceover.py`：

```bash
python3 <skill>/scripts/voiceover.py vo/lines.json public/vo --engine mimo --voice Milo   # 小米 MiMo TTS
python3 <skill>/scripts/voiceover.py vo/lines.json public/vo --engine say --rate 140   # 本机系统语音试音：macOS say / Windows SAPI / Linux espeak-ng
```

- `lines.json`：`{"style": "音色与语气描述", "lines": [{"id", "text"}]}`。每句一个 wav，并写出 `timing.json`（每句时长），自动去掉首尾静音、峰值归一到 −3 dBFS。
- MiMo 的 Key 只从 `MIMO_API_KEY` 环境变量或 `MIMO_API_KEY_FILE` 指向的文件（chmod 600）读取，不写进代码、日志或成片；接口拒绝或余额不足时停止并告知用户，不重试、不购买。`say` 需要在沙箱外运行。
- 时间轴由配音驱动：Film 读取 `timing.json`，每段长度 = 前留白 + 这句时长 + 后留白，标题在这句开口时出现。换音色后重新生成配音，画面会自动对齐。
- 数字按读法写（"Forty-eight megapixel"），句子短，每句一个卖点，全片 8–10 句。
- 混音：有旁白时 BGM 音量压到约 0.22，旁白间隙回到 0.4（比人声低 6–10 dB）。

## Three.js 规则

- `ThreeCanvas` 必须传 `width/height`；贴图用 `useLoader(THREE.TextureLoader, staticFile(...))`，Remotion 会等待加载。
- **`ThreeCanvas` 一律传 `resize={{ offsetSize: true, scroll: false }}`**（2026-10-02，某 3D 科普片 v1「画面抖动厉害」）：R3F 用 `getBoundingClientRect()` 量画布，量到的是**带 CSS 变换**的尺寸；镜头容器在转场里有 `scale()` 时挂载，合成器就按放大的尺寸建、一直不改。多标签并行渲染时每个标签挂载时刻不同 → 相邻帧缩放不同 → 来回跳。单独渲几帧看不出来，要渲 300+ 帧测相邻帧差（物体边缘位置应单调）。镜头里的推拉放进 3D 相机做，CSS 只做透明度 / 滤镜。
- 环境光用 `StudioEnv`（RoomEnvironment + PMREM，离线），不要加载远程 HDR。
- 截图贴片：`meshBasicMaterial` + `toneMapped={false}` + `SRGBColorSpace`，Bloom 阈值 ≥ 0.9，否则白色界面会过曝。
- 景深 `DepthOfField worldFocusDistance={相机到焦点距离} worldFocusRange={2.5}`，焦点随最近的面板切换。
- 环形排列的卡片用 billboard（不旋转，始终正对镜头）并按前后缩放/透明度，避免侧面变成一条线。
- 剪纸层次靠投影：主光放在前下方（低于纸片顶部），影子才会落在后一层上沿；光从上方打时影子藏在纸片背后，画面会变平。`shadows="variance"` 让影子更柔。
- 渲染速度参考：33 秒 Film（含 4 个 3D 场景与运动模糊）在 Apple Silicon 上约 1 分钟。
- **切换点连续**（detail-pass.md）：场景组件按帧号挂载 / 卸载时，卸载点要晚于「看不见」（灯光落到 0、面板亮度 0），天空球等背景物要早于「露出」挂载并跟随背景色；泛光 / 暗角 / 景深 / 雾这些后期参数用一个暗度函数 `mix` 出来，不要 `inCloud ? a : b` 一帧切换；相机推向切点用 `sine` 或二次 inOut，别用 `expo.in`。
- **加法混合的光晕精灵**要设 `renderOrder` 高于同场景的透明面板（`Panel3D` 的面是 `transparent` 且 `renderOrder=2`），否则被面板盖住，等面板卸载才「突然出现」。发光小球用 HDR 颜色（×2 以上）让泛光吃得到。

## 音效设计

音效让画面「有手感」，与配乐一起做。`setup_project.py` 会把 `assets/sfx/` 复制到 `public/sfx/`，目录与用途见 `assets/sfx/README.md`（全部可免费商用，`preview.wav` 可整套试听）。Film 里用 `<SoundCues cues={[{ at, name, volume }]} />` 排布：

- 打字：`keyCues(text, times, offset)` 为每个字随机选 `key-1..8`，空格用 `key-space`，并限制为每 2 帧最多一次（约 15 键/秒）：画面打字通常比真人快，逐字发声会糊成连续的嗡嗡声。
- 操作：鼠标点击 `click`，选项/标签 `tap`，元素出现 `pop`，打勾 `done`，最终成功 `ding`（整片最多一次）。
- 节拍切换（大字翻色、列表逐项）：`slam-1..3` 轮流用。不要用带音高的电子音做重复音效，听感廉价。
- 镜头：快速转场 `whoosh`，轻柔移动 `swish-1..3`，开场/收尾落点 `impact`，收尾前 1.2 秒 `riser`。
- 纸质与文档：翻页 `page-1..3`，纸片落下 `paper-place-1..2`，剪开 `cut`。
- AI 工作中：`processing` 垫底，音量 ≤ 0.15。
- 音量参考：按键 0.5、点击 0.9、tap/pop 0.5、whoosh 0.3–0.8、impact 0.3–0.9；音效密集时 BGM 降到 0.3。成片后看 `rn qa` 的响度、true peak 和爆音（`render.py` 自动跑）。
- 整体偏小声时不要重渲：`rn finish out/film.mp4 -o out/film-loud.mp4 --copy-video --lufs -12`（只重做音轨：按 LUFS 补增益、限幅，并在 AAC 编码后复测 true peak ≤ −1 dBTP）。
- 新增音效只用 CC0 / 公有领域来源（如 [Kenney](https://kenney.nl/assets)、OpenGameArt 标注 CC0 的素材），处理成 48 kHz WAV、裁掉开头空白，并登记到 README。

## 样帧检查

每段取 2–3 帧（动作中段 + 定格）打开查看：文字是否被 Logo/卡片遮挡、长标签是否溢出、3D 卡片是否侧面朝镜头、截图是否过曝、景深是否把主体也糊掉。每个切换点另看前后各 4 帧（`rn sheet out/film-preview.mp4 --around <秒,...> --span 4`）。修完再渲整片，预览给用户之前看 `rn qa` / `rn cuts` 的结果（`render.py` 自动跑）并跑 `typo_lint.py`（detail-pass.md）。
