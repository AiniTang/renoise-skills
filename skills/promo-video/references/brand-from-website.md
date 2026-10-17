# 从官网提取品牌素材

用户只给网址时，按以下顺序拿到 Logo、字体、配色和产品图，再列出仍需用户补充的项。

## 1. 文案与功能

WebFetch 官网首页，提炼一句话价值主张、功能分组、受众案例、CTA 文案。官网原话可直接用于屏幕文字；数据（用户数、客户数）要请用户确认后才用。

## 2. 视觉与配色

用宿主提供的浏览器工具打开官网并截图（没有就用 Playwright；用户指定时按用户的），看明暗节奏与版式。再在页面里执行下面的脚本统计计算样式（浏览器工具的「执行 JavaScript」能力；只有 Playwright 时用 `page.evaluate`）：

```js
(() => {
  const count = (m, k) => m.set(k, (m.get(k) || 0) + 1);
  const bg = new Map(), fg = new Map(), fonts = new Map();
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    const cs = getComputedStyle(el);
    if (cs.backgroundColor !== "rgba(0, 0, 0, 0)") count(bg, cs.backgroundColor);
    if ([...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) {
      count(fg, cs.color);
      count(fonts, cs.fontFamily.split(",")[0] + " | " + cs.fontWeight);
    }
  }
  const top = (m, n) => [...m].sort((a, b) => b[1] - a[1]).slice(0, n);
  const h1 = getComputedStyle(document.querySelector("h1"));
  return { body: getComputedStyle(document.body).backgroundColor,
    h1: [h1.fontFamily, h1.fontWeight, h1.letterSpacing], bg: top(bg, 14), fg: top(fg, 10), fonts: top(fonts, 8) };
})()
```

插画、图标里的品牌色用 canvas `getImageData` 统计像素（同源图片才能读取）。

## 3. Logo、字体与产品图

- Logo：找 `img[alt*="logo" i]`、页头 `a[href="/"]` 里的 `img/svg`。优先下载 SVG；图形标志与字标分开时分别放 `brand.logo` 和 `brand.wordmark`。
- 字体：遍历 `document.styleSheets` 里的 `CSSFontFaceRule`，取品牌字体的 woff2 地址下载。Google Fonts 等开源字体可直接商用；商业字体只用于演示，并提醒用户确认授权。
- 字体提取出来只是起点：按 typography.md 进入「字体提案」。官网是商业字体（Söhne、Canela、GT 系列、方正 / 汉仪、苹方）时不要用系统里的副本，`python3 scripts/fonts.py similar "<字体名>"` 找开源平替；官网字体本身平庸时，用它当第 4 组对照，再按调性给 3 组更有设计感的配对。
- 中文字体动辄 10–25 MB，每个渲染标签页都要加载，会拖慢出片。写完文案后收集 `src/` 里用到的字，用 fonttools 做子集：`python3 -m fontTools.subset Font.ttf --text-file=chars.txt --flavor=woff2 --layout-features='*' --output-file=Font.woff2`（需 `pip install --user fonttools brotli`），通常只剩 100–300 KB；改文案加了新字就重新做一次。Google Fonts 的完整文件可从 GitHub `google/fonts` 仓库下载。
- 产品图：收集页面中 `img/source/video` 的 `src`、`srcset`，通常是官网的高清宣传图（界面截图、插画、角色头像）。它们比截屏清晰，优先使用。
- 用 `curl -L -o` 下载；宿主的命令沙箱拦了网络时，按宿主的方式对这条命令放开（见 SKILL.md「渲染约束」）。webp 用系统 ffmpeg 转换：`ffmpeg -i in.webp out.png`（Remotion 自带的 ffmpeg 不含 webp 解码器；Chrome 渲染时可直接用 webp）。

## 4. 官网的视频与交互演示

- `<video>`：在页面里执行脚本收集 `currentSrc` 与 `poster` 直接下载；长的产品演示视频先用 `rn sheet demo.mp4 --fps 1` 看时间线（`rn cuts demo.mp4 --sheet cuts.jpg` 直接列出镜头边界），再用 `rn sheet demo.mp4 --seconds 12.4,31` 精确核对每个选中的镜头；演示里的文字用 `rn text demo.mp4` 读出时间和位置。演示画面自带说明文字时，按像素测出产品窗口区域，裁切后放进卡片，避免和片中标题重复。
- 内嵌交互演示（`iframe srcdoc`，常见于首屏「产品界面演示」）：把 `srcdoc` 存成本地 HTML，起本地静态服务（`python3 -m http.server <端口>` 放到后台跑，见 SKILL.md「渲染约束」；前台跑的命令结束时会把服务一起关掉），在浏览器里打开，点击侧栏、输入框切换状态，逐个截图。截图是 2 倍分辨率，足够做产品窗口。
- 要改演示页的尺寸或样式时，直接改本地那份 HTML，不要往页面里注入脚本改界面（执行脚本只用于读取和检查）。点击坐标用截图上的坐标。
- 演示里的打字、发送、思考中、结果页都是现成的真实状态：空白首页上自己叠一层逐字打字动画，比截整段录屏更可控。

## 5. 仍需向用户确认

- 官网图是示意图还是真实产品界面；真实截图或录屏效果更好
- 可引用的数据与模型名等事实
- 是否有品牌规范文档（精确色值、Logo 使用规则）
- 是否已有品牌固定配乐或片尾
