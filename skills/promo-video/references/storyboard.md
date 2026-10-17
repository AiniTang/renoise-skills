# 分镜与 storyboard.json

## 时长档位

| 档位 | 场景数 | 适用 |
|------|--------|------|
| 15 秒 | 3–4 | 社媒信息流广告、开屏：钩子 → 1 个卖点 → 品牌 |
| 30 秒 | 5–7 | 产品发布首选：钩子 → 主视觉 → 卖点 → 数据/界面 → 品牌 |
| 60 秒 | 8–12 | 产品介绍：问题 → 方案 → 3 个卖点逐一展开 → 证明 → 行动号召 |
| 90–120 秒 | 12–20 | 讲解视频、融资路演：需要分章节，考虑后续加配音 |
| 15 秒（动效作品集） | 6–7 种手艺 | 每 2–2.5 秒一种手艺，首尾呼应（motion-craft.md） |
| ≤ 60 秒（作品合集） | 每作品 4–5 秒 | 开场 4 秒 + 作品轮播 + 署名 + 收尾墙（recap.md） |

推荐时说明：时长越短，每屏文字越少；超过 60 秒没有配音时观众容易流失。

## 叙事结构（问题 → 方案 → 证明 → 行动）

1. **钩子 / 痛点**（`statement`）：一句戳中受众的话，前 3 秒决定是否继续看。
2. **方案亮相**（`hero3d` 或 `statement`）：产品名 + 价值主张。
3. **卖点**（`features`，或多个 `statement`/`showcase`）：3 个为宜。
4. **证明**（`stats`、`showcase`）：数据、界面、客户背书。
5. **行动**（`outro`）：品牌、口号、CTA、网址。

## 文案规则

- 标题：中文 ≤ 14 字，英文 ≤ 7 词；可用 `\n` 手动断行。
- 卡片正文：中文 ≤ 12 字；卡片 3 个最佳，最多 6 个。
- 屏幕阅读速度按中文约 7 字/秒、英文约 3.3 词/秒估算，外加 0.5 秒反应时间；`check_storyboard.py` 会提示超时的场景。
- 数据必须来自用户素材；没有真实数据时要么不用 `stats`，要么在 `brand.disclaimer` 注明「数据为示例」。

## storyboard.json 字段

```json
{
  "meta": { "title": "", "language": "zh|en|ja", "industry": "", "audience": "", "purpose": "" },
  "format": { "aspect": "16:9|9:16|1:1|4:5", "fps": 30, "resolution": "720p|1080p|4k" },
  "style": "keynote|kinetic|aurora|editorial",
  "brand": {
    "name": "品牌名",
    "logo": "brand/logo-mark.svg",
    "wordmark": "brand/logo-wordmark.svg",
    "fonts": {
      "display": { "family": "Hepta Slab", "file": "brand/Display.woff2" },
      "body": { "family": "DM Sans", "file": "brand/Body.woff2" }
    },
    "displayWeight": 500,
    "colors": {
      "primary": "#hex", "accent": "#hex", "background": "#hex", "text": "#hex",
      "muted": "rgba(0,0,0,0.6)", "button": "#hex", "dark": "#hex", "light": "#hex"
    },
    "disclaimer": "示例品牌与数据，仅用于演示"
  },
  "music": { "file": "music/bgm.wav", "bpm": 120, "volume": 0.8, "startOffset": 0 },
  "captions": false,
  "scenes": []
}
```

除 `name` 外均可省略。`logo` 是图形标志，`wordmark` 是字标，两者都有时片尾并排显示；深色场景会自动反色。`fonts` 只给 `display` 或 `body` 之一时两者共用。`colors.button` 是 CTA 按钮色（文字色按亮度自动选黑或白），`colors.dark` / `colors.light` 是场景切换色调时使用的底色。

## 场景类型

每个场景都有 `seconds`（必填），以及可选的：

- `camera`、`transition`
- `tone`: `light` / `dark`：单独把这个场景切到浅色或深色，用于模仿官网明暗区块交替
- `caption`：`captions: true` 时显示为底部字幕，并导出到 SRT

| type | 专有字段 | 画面 |
|------|----------|------|
| `statement` | `text`、`eyebrow?`、`highlight?`（text 中要高亮的子串） | 居中大字，逐字/逐词出现 |
| `hero3d` | `title`、`subtitle?`、`shape?`: `knot`/`orbs`/`cubes` | Three.js 3D 物体 + 标题 |
| `features` | `title?`、`items[]`: `{icon?, image?, title, body?}`、`imageStyle?`: `icon`/`cover`、`imageAspect?` | 卡片网格。无图时图标线条描绘；`icon` 模式图片当图标；`cover` 模式图片铺满卡片上半部（成品截图、角色头像） |
| `stats` | `title?`、`items[]`: `{value, prefix?, suffix?, decimals?, label}` | 数字滚动计数 |
| `showcase` | `title`、`body?`、`image?`、`frame?`: `browser`/`phone`/`none` | 设备外框中的截图；无截图时画示意界面。图片自带窗口外框（官网宣传图常见）时用 `none`，原样显示 |
| `outro` | `tagline?`、`cta?`、`url?` | Logo / 文字标、口号、按钮、网址、声明 |

`icon` 可选：`spark bolt shield chart globe chat clock heart cube check search lock users book factory wallet layers rocket`。

竖屏（9:16）会自动改为纵向排版：卡片单列、showcase 默认手机外框、3D 物体在上文字在下。

## 按信息密度定时长

用户让你判断时长时，先数官网里可以上屏的独立事实块（主张、功能/栏目、人物、数据、案例、渠道）：4–5 块约 30 秒，6–8 块约 45 秒，更多再到 60 秒；每块 4–8 秒，读得完为准。信息不够就保持短片，不靠延长镜头凑时长。
