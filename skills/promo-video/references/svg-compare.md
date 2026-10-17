# 模型输出对比片（动画 SVG 并排 + YouWare 钩子）

> 样片：`examples/svg-compare/`（2026-09-30，YouWare × GPT-6 Sol vs GPT-6.1 Sol，12 秒 4K）。

## 什么时候用
新模型发布当天的「同题对比」投流短片：两家或两代模型对同一提示词产出的 SVG / HTML 小作品，原样并排，再用 YouWare 的输入框和模型菜单讲「你也能在这里做」。和 x-hotride 的「同题对比」打法配套使用，文案用它的借势包。

## 事实先行（发之前问清楚）
- **模型名和推理强度用官方英文**。例如 OpenAI 的推理强度界面叫 Low / Medium / High / Extra High / Max / Ultra，API 值分别是 low / medium / high / xhigh / max / ultra。简体中文界面里 xhigh 叫「极高」，Ultra 也被错译成「极高」（openai/codex #31963）。用户说「极高」时，先确认是排在「最高」上面的那个（Extra High）。
- 画面里打字的提示词要用**原文或忠实翻译**，拿不到就注明是意译。
- 文件的下载来源可以用 `mdls -name kMDItemWhereFroms` 查。`app://-/` 表示桌面 app（比如 Codex），不是 youware.com。如果视频展示的是「在 YouWare 里生成」，就要先在 YouWare 里重跑，把重跑结果换进片子。
- 模型菜单的行要照**最新截图**。片尾说「在 YouWare 试」之前，先确认模型真的能在 YouWare 里选。

## 做法
- **两个 SVG 同页播放**：`tools/prep_svgs.py` 给所有 id、class、@keyframes、url(#)、href 加前缀；把会作用到全页的 `svg{}` 规则收窄到自己的根节点；删掉 `<title>` / `<desc>`；把 `<use>` 展开成真实节点；外包一个 `#<p>-zoom` 组用来推近。
- **逐帧确定**（`SvgPlayer.tsx`）：
  - SMIL 动画用 `pauseAnimations()` + `setCurrentTime(t)`。
  - CSS 动画在样式里一律写成 `animation-play-state: paused` + `animation-delay: calc(var(--t) * -1s)`，每帧只改 `--t`。
  - 不要用 `getAnimations()` 去拨时间：首次挂载时动画还没创建，会按真实时钟跑，同一帧渲染两次的结果会不一样（实测最大像素差 202）。
- **推近**：变换包裹组，不要改根 viewBox。结果是矢量级清晰，4K 下依然锐利。
- **宽高比不同**：把较窄的那个 SVG 的 viewBox 两侧加宽，用它自己的纸色补边。
- **回归校验**：`ScarfTest` 对比原 viewBox 和加宽后的版本，`RaysTest` 对比组变换推近和改 viewBox 推近。两项的像素差都应为 0。

## 坑
- `<use>` 克隆出来的节点在 shadow tree 里，上面的 CSS 动画不受控制，会按真实时钟乱转（这次是车轮）。要在预处理时展开。
- Chrome 把 `transform-box: view-box` 的参考框放在用户坐标原点，不在 viewBox 的 (min-x, min-y)。所以加宽 viewBox 时，px 单位的 transform-origin **不用**跟着平移。平移了反而错：实测平移后的版本和原版差了 7263 个像素。
- 镜头推近或拉回 1.6 倍，至少要 10–11 帧，用 sine 曲线。7 帧的 power3 中段每帧缩放变化约 0.2，`rn cuts` 会把它当成硬切，人眼看也像一下甩镜。
- 输入框要从画面外带着速度进入。如果从画面边缘开始慢速起步，挂载那一帧底边会先露出一条几乎不动的白边。
- 白字放在白框上，由墨色圆扩散把它「显影」出来。这样结尾没有灰色中间态，CTA 也能贴着收尾和弦出现。
- 手机上的可读性：投流片里必须读的字，在 1920 宽的画面上至少 48–72 px。切换模型这一拍要推镜头，880 宽的对话框里文字只有 21 px。
