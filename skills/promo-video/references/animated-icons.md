# 动效图标与动态 emoji

两套素材，都在 `templates/remotion/src/icons/`，逐帧渲染（不依赖浏览器时钟），可以放心并行渲染和跳帧。样片源码：`examples/animated-icons/Reel.tsx`（Remotion id `Reel`）。

| 素材 | 数量 | 格式 | 授权 | 用在哪 |
|---|---|---|---|---|
| lucide-animated（github.com/pqoqubbw/icons） | 467 | Lucide 线条 + 每个图标自带的动作 | MIT，可打包、片中无需署名 | 功能节点、流程图、卖点卡——任何原本放 Lucide 图标又想让它「动一下」的地方 |
| Google Noto Animated Emoji | 881 动态（其余退回 Noto 静态 SVG） | Lottie 矢量 1024，60fps | 动态版按 CC BY 处理：片尾/声明写「Animated emoji: Google Noto」；静态 SVG 为 Apache 2.0 | 课程、社媒、轻松向的片子；用户明确想要 emoji 时 |

**不要再用 Apple Color Emoji（系统 emoji 字体）做商用成片**：Apple 的 emoji 图形有版权，用在公开宣传片里属于灰色地带。需要 emoji 就用 Noto。

## 动效图标

```tsx
import { AnimatedIcon } from "../icons/AnimatedIcon";
<AnimatedIcon name="rocket" at={at(4)} size={64} color="#fff" />          // 在 at 帧开始播
<IconTile anim="settings" playAt={land + 2} on={p} size={150} />          // 放进应用图标底板
```

- `name` 是 lucide-animated 的文件名（`src/icons/la/index.ts` 里的 `ICON_NAMES`，TS 会补全）。它和 lucide-react 的名字大多相同，但不是全集（没有 `target`、`mail`、`code` 等）；找不到时换近义词，或用静态 Lucide。
- `at` 之前是静止姿态；`at` 之后播原图标的 `startAnimation()`，原作者写的多段串联（`await` 链、`Promise.all`、stagger、弹簧）都按原样还原。
- `cycles`：原图标里无限循环的部分播几轮，默认 1（播一次停住）。宣传片里保持默认。
- `stop`：可选帧号，在该帧调原图标的 `stopAnimation()` 回到常态。
- `strokeWidth` 默认 1.75，与静态 Lucide 一致；同一画面里静态和动效图标可以混用，线条看不出差别。
- 想让同一个图标在后面某一拍再播一次：把 `at` 换成新的帧号（例如 `at={f >= again ? again : land}`），见样片的图标墙。

### 节奏规则

- **只在接触帧播一次**：图标底板落地、节点点亮、光标点中的那一帧（+0–2 帧）开始播，播完停住。不要让满屏图标一直循环。
- 一屏里同时在动的图标 ≤ 3 个；图标墙用波浪错开（每个间隔 ½ 拍左右）。
- 有字要读的段落，图标动作要短（≤ 0.6 s 的动作优先，如 check、send、bell、settings）。

### 原理与验证（改动适配层后必须重跑）

`src/icons/motion-shim.tsx` 替代 `motion/react`：编排（variants、controls、await 串联、staggerChildren、transitionOverride）自己实现，数值直接调用 motion-dom 12.43 的关键帧/弹簧生成器、`mix` 和 `buildSVGAttrs`，所以缓动、默认过渡、描边动画、`transform-origin` 与原库一致。已对全部 467 个图标做过对照：Playwright 虚拟时钟（`clock.install` + `pause_at`，并删除 `Element.prototype.animate` 让 motion 不走 WAAPI）跑真 motion，逐帧与适配层比较，误差在参照页 1 个 rAF（约 12 ms）以内。已知例外：`volume` 的静音 × 由 React state 控制，静止帧会不显示 ×。

更新图标库：`python3 scripts/vendor_lucide_animated.py <icons 仓库目录> src/icons/la`（重写 import、把 `Math.random()` 换成确定性随机、生成 index.ts）。

## 动态 emoji

```bash
python3 <skill>/scripts/fetch_noto_emoji.py <项目目录> 🚀 🎯 ✅ 💡     # 下载到 public/emoji/
python3 <skill>/scripts/fetch_noto_emoji.py <项目目录> --list rocket  # 查有哪些动态版
```

```tsx
import { NotoEmoji } from "../icons/NotoEmoji";
<NotoEmoji char="🚀" at={at(3)} size={200} />
```

- `at` 之前停在第 0 帧（Noto 的起止姿态相同）；`speed` 调快慢，`cycles` 默认 1。
- 没有动态版的 emoji（如 📂 🧰 💼）脚本会自动下静态 SVG，组件照常使用。
- 帧率已换算（Lottie 60fps → 片子 fps），不要改用 `@remotion/lottie`：它按视频帧号一比一取 Lottie 帧，30fps 片子里会慢一半。
- 大号 emoji 做主角时 160–240 px；和文字并排时与字号同高。

## 样帧检查

- 抽图标开始后 3–6 帧的中间帧：必须看到动作中的形态（不是只有静止和结束两态）。
- 有 await 串联的图标（heart-pulse、phone-call、layers、battery-*、chart-*）抽 0.3 s、0.6 s、1 s 三帧，确认顺序对。
- emoji 抽播放中帧，确认不是空白（manifest 缺项会直接报错）。
