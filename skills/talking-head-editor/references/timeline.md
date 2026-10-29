# timeline.json 格式

一份时间线同时喂给 `render.py`（出成片）和 `build_draft.py`（出剪映草稿）。所有时间都是**粗剪后的成片时间**（秒），所有位置都是**相对画面的比例**（0~1，左上角为原点，x 向右、y 向下）。相对路径以 timeline.json 所在目录为准。

先用 `init_timeline.py` 生成骨架（画布、口播、自动断好的字幕），再按剪辑方案往里填。

## 画幅与尺寸

`canvas` 是画幅的唯一声明，横屏写 `{"w": 1920, "h": 1080, "fps": 30}`；没有声明的旧时间线仍按 1080×1920 渲染。
`auto_edl.py`、`rough_cut.py`、`init_timeline.py` 和 `preview_library.py` 都接受 `--canvas WxH`。不指定时按素材方向选横屏或竖屏 1080P；
粗剪优先沿用 EDL 的 canvas，并把实际画布写进输出目录的 `canvas.json`，初始化时间线会接着用它。显式 `--canvas` 优先。
多段素材方向不同时，默认以第一段保留素材为准；要转画幅就显式指定，铺满时会裁切。

字号、描边、圆角等像素尺寸统一乘 `kvlib.unit(W, H)`，即短边 / 1080；横向位置仍乘 W，纵向位置仍乘 H。
横屏默认字幕居中在 0.88H，行宽约 0.70W；PIP 默认右上角，内容直径约 0.26H。
`pip.d` 仍表示画布宽度比例，手写的 `pip` 和字幕 y、style_overrides 优先于默认值；crop 的 x、y、s 仍相对画布宽度，超界会收回画内。
横屏 card、contain、tilt、double、band 内容框上限约 0.62W × 0.72H（投影和装饰边框另计）。
叠加物 w、定格头像 d 沿用旧数字，但尺寸基准改为短边；x、y 的含义不变。

代码背景、信息图和素材检索也可传 `--canvas`；信息图可在 spec.canvas 声明 w、h，没有画布时仍用旧的 960×720。
横屏时所有手法自动按横屏排版：人在画面中间，大字、标签、卡片放左右两侧，整屏版式改成横向分栏，字幕在底部中间。素材带、铺满版式用横版截图和录屏效果最好，竖版截图放进横屏会左右留边，`fit: cover` 会切掉上下。

## 完整示例

```json
{
  "canvas": {"w": 1080, "h": 1920, "fps": 30},
  "style": "premium",
  "aroll": "aroll.mp4",
  "duration": 61.2,
  "fonts": {"title": "/path/to/品牌标题字体.ttf"},
  "tail": 1.5,
  "zoom_anchor_y": 0.38,

  "zoom": [
    {"t0": 8.18, "t1": 12.45, "to": 1.10},
    {"t0": 16.5, "t1": 20.9, "to": 1.08, "ease": 4.0}
  ],

  "layout": [
    {"t0": 12.5, "t1": 16.5, "mode": "aside"},
    {"t0": 21.0, "t1": 26.2, "mode": "pip", "pip": {"x": 0.78, "y": 0.84, "d": 0.32}, "crop": {"x": 0.0, "y": 0.08, "s": 1.0}},
    {"t0": 30.0, "t1": 33.0, "mode": "hidden"}
  ],

  "broll": [
    {"t0": 12.5, "t1": 16.5, "src": "broll/git树.png", "fit": "card", "w": 0.84, "y": 0.42, "enter": "slide_up", "motion": "rise"},
    {"t0": 21.0, "t1": 26.2, "src": "broll/演示.mov", "fit": "double", "ratio": "4:3", "y": 0.40},
    {"t0": 30.0, "t1": 33.0, "src": "broll/rocket.mp4", "fit": "cover", "src_in": 2.0, "speed": 1.0, "motion": "push"},
    {"t0": 40.0, "t1": 44.0, "src": "broll/录屏.mp4", "fit": "cover", "speed": 4.0,
     "focus": {"t": 1.5, "dur": 0.5, "scale": 2.4, "cx": 0.8, "cy": 0.6}}
  ],

  "subs": [
    {"t0": 0.06, "t1": 1.20, "text": "Vibe coding 一年半以来", "level": "base"},
    {"t0": 10.8, "t1": 12.5, "text": "还把之前的功能改坏了", "level": "key", "hl": ["改坏了"], "anim": "pop", "jy_flower": "黄色条纹花字"}
  ],

  "titles": [
    {"t0": 0.3, "t1": 2.4, "text": "踩坑", "y": 0.21, "behind": true},
    {"t0": 7.9, "t1": 9.4, "layout": "chapter", "number": "01", "text": "版本管理", "en": "Point one · Version control", "sub": "改坏了也能一秒回退"},
    {"t0": 10.6, "t1": 12.3, "layout": "side", "lead": "它不仅没写对", "text": "还把功能\\N改坏了", "hl": ["改坏了"]},
    {"t0": 18.9, "t1": 20.6, "layout": "quote", "text": "不能依靠\\NAI 的记忆\\N来撤回", "hl": ["记忆"], "en": "never trust its memory", "ghost": {"text": "MEMORY", "y": 0.14}},
    {"t0": 28.4, "t1": 30.4, "layout": "split", "left": "越聊", "right": "越蠢", "left_en": "more talk", "right_en": "less smart", "hl": ["蠢"]}
  ],

  "overlays": [
    {"t0": 5.0, "t1": 6.5, "src": "assets/arrow.png", "x": 0.7, "y": 0.35, "w": 0.18}
  ],

  "effects": [{"t0": 8.2, "t1": 9.4, "name": "大头"}],
  "stickers": [{"t0": 16.6, "t1": 18.0, "name": "红圈 圈重点", "x": 0.8, "y": 0.3, "scale": 0.4}],

  "audio": {
    "voice": {"lufs": -16, "denoise": true},
    "bgm": [{"src": "bgm/calm.mp3", "t0": 0, "t1": 30, "src_in": 0, "db": -24, "fade_in": 0.5, "fade_out": 1.0, "duck": true}],
    "sfx": [{"src": "sfx/pop.wav", "t": 8.18, "db": -10}]
  },

  "style_overrides": {"sub": {"hl_color": "#FF6B35"}}
}
```

## 字段说明

### 顶层

| 字段 | 说明 |
|---|---|
| canvas | 画布宽高帧率，竖屏默认 1080×1920 30fps |
| style | `premium` 高级感 / `variety` 综艺感，决定字幕、卡片、小窗、配乐音量等默认值（见 `scripts/kvlib.py` 的 STYLES） |
| aroll | 粗剪后的口播文件，成片时间 = 这个文件的时间 |
| fonts | 按角色覆盖字体，一般不用写。角色有 `sub` 字幕、`title` 大字、`serif` 金句、`en` 英文小标和数字、`body` 说明小字、`hand` 手写感；值可以是字体族名加字重（如 `Source Han Sans CN Heavy`）或字体文件路径。剪映草稿用 `jy_<角色>` 指定剪映字体名（如 `"jy_title": "得意黑"`）。默认字体见 `style-premium.md` 的字体一节 |
| sub_scrim | `true` 时在字幕区垫一条很柔的底部渐暗，用于衣服印字、杂乱背景抢字幕的素材；`sub_scrim_alpha` 调浓淡（默认 0x70，数值越小越暗） |
| tail | 口播说完后再留几秒，画面定格在最后一帧，用来放片尾大字、让配乐收尾；默认 0 |
| zoom_anchor_y | 推近时以画面多高处为中心，人脸一般在 0.35~0.4 |
| tone | 高级感的强度档：`web` 网感档（默认）/ `calm` 克制档，见 `styles.md` |
| sub_look | 常驻字幕的样子（`rolling` 双行滚动：左下角两行，上一句变灰退上去、当前句在下，换句整体上滚，只适合无人出镜的解说测评；浅色纸页底用 `rolling_ink`）：`box` 半透明黑底条（高级感默认）/ `shadow` 无底柔阴影白字 / `serif` 胸口粗宋白字（杂志感）/ `low` 小号压底（大字多的片子）/ `bar` 不透明黑条访谈字幕 / `outline` 白色粗黑体细黑边（抖音最常见）/ `chest` 胸口高度深蓝圆体白边 / `huazi` 整句蓝边黄字垫黑底（综艺感最强） |
| cover | 首帧封面图：`{"text", "text2", "frame_at": 抠哪一秒的人, "bg", "bg2", "dur": 0.15}`，片头 0.15 秒铺一张封面（抠像人带白贴纸描边、上下两行倾斜彩色标题），随后硬切进第一句，平台自动截的首帧就是它；标题要和第一句呼应 |
| points | 角落要点编号：`{"variant": "glow" / "film" / "brush", "items": [{"t0", "t1", "n", "text"}], "until": 最后一点到几秒}`。glow 左上黄色斜体编号加本节名、换项时黄光扫过；film 右上胶片框小卡、换项故障闪；brush 左上斜切白编号。不写 items 就按章节页自动排（章节页和白场接力页结束起到下一章）。压在字幕下面，剪映草稿里没有 |
| hud | 常驻栏目信息层：`{"variant": "watermark", "text": 系列名}` 顶部一行灰色系列名 / `{"variant": "progress", "y": 0.24, "mascot": "Person walking"}` 黄色进度条按成片时长走完，前端小人跟着走 |
| montage_cuts | 一词一镜快剪：`[{"t0", "t1", "srcs": [素材...], "pip": true 或 {"pip": {x, y, d}}, "subs": true, "broll": {"fit": "band", "crop": [...]}}]`，这段话按短语一个镜头换一个素材（轮着用，视频从不同时刻截），头像小窗不动，字幕一个镜头一个短语 |
| section_ends | 段落收尾推高收束：`[{"t0", "t1": 快剪段, "srcs", "talk": [问题句起, 止], "silence": 1.2}]`，快剪推情绪、问题句跳到 115%、下一个章节页那一下配乐停 1.2 秒 |
| phrase_subs | 快剪一词一镜字幕：`[{"t0", "t1", "cut": true}]`，这几段里的跟读字幕按逐字时间拆成 2~6 字一个的短语（分词不拆词，标点必断，停顿长处优先断，一个短语至少停 0.4 秒），起止吸附到 0.2 秒内的素材、版式、粗剪刀口；`cut` 为 true 时每个短语换一档景别（100% / 118% / 132% / 110% 硬切），一个机位也像在快剪。放在口播全屏、信息密的一两句上 |
| badge_bar | 口播上移底部留黑：`{"text": 角标文字, "h": 0.82, "sub_y": 0.70, "ranges": [[t0, t1]]}`。口播全屏时段底部 18% 盖纯黑、交界线正中骑一枚米白描边角标，B-roll 和整屏版式时段恢复全屏；字幕整片挪到人物胸前。适合底部有平台标题和按钮遮挡的抖音、视频号。剪映草稿里没有 |
| stings | 梗句幽默短乐句：`[{"t": 梗句开始, "src": 用户准备的喜剧短乐句, "in": 从第几秒截, "dur": 2~4, "db": -2}]`，渲染前剪成短片段放进音效，这几秒主配乐让开。没有短乐句就别写，改用梗音效；一期三四次就够 |
| sub_key_look | 字幕里强调词的样子：`weight` 换粗一档不变色（高级感默认）/ `red` 同号深红 / `yellow` 亮黄放大 1.2 倍 / `bracket` 加【】（教程类）/ `stripe` 黄字放大弹一下（综艺感）。一行只强调第一个 hl |
| font_palette | 全片字体基调：`sans` 干货黑体（默认）/ `serif` 标题和字幕都换思源宋体 / `heavy` 标题换得意黑 / `hand` 标题换毛笔字 |
| beats | 按内容自动搭配的大字，见下面「beats」一节 |
| sections | 段落表（先按结构切段再包装）：`[{"t0": 0, "name": "开场", "mood": "hype"}, {"t0": 7.9, "name": "第一点 版本管理", "mood": "calm"}, ...]`，每段到下一段开始为止。`mood` 是这段配乐的情绪：`calm` 舒缓 / `dense` 信息密、快剪 / `happy` 欢快 / `hype` 提气，不写按画面密度判。可写 `seam` 指定和上一段配乐怎么接（见 audio 的「段落换曲」）、`shout: true` 换曲时叠一声欢呼、`gap` 留白秒数。配乐换曲、留白、声音先入都按段落走；不写就按章节页切。3 段以上或 3 分钟以上的口播要写，rhythm_check 会查；写 `"climax": true`（或秒数）把这一段最后约 4 小节换成同一首里最有劲的 4 小节、切点落在重拍上，推到段落结束再回原位（截高潮段） |
| jcut | 声音先入：铺满画面的素材、遮住人的版式、章节页在下一句开口前后结束时，延长到开口后 0.35 秒，观众先听到下一句、画面再切回口播。默认开；写数字改提前量（0.3~1），写 `false` 关掉 |
| auto_zoom | 口播景别怎么自动做，见下面「zoom」一节：`jump` / `snap` / `mixed` / `false` |
| auto_link | `false` 时相接的两张卡片不自动做同向移出移入（见 broll 的 `link`） |
| opening | 开场第一秒入场冲击，配一声音效：`zoom` 画面先以 45% 大小出现在黑底中间，0.4 秒放大铺满，配点击（网感档默认）/ `spotlight` 第一句四周压成椭圆暗角只有人亮，同时整句缓推到 112%（克制档默认）/ `flash` 过曝白光加竖向动态模糊闪入，配铃声（综艺感默认）/ `iris` 黑底上一个小圆从人脸处张开 / `boom` 放射速度线冲一下配「咚」/ `false` 关掉。开头就是铺满素材或别的版式时不自动加 |
| voice_fx | 人声变声段：`[{"t0", "t1", "type": "megaphone" / "bleep", "label"}]`。megaphone 扩音器念原话（这几秒人声只留中频再轻微失真，画面叠四角取景框和闪烁 REC），bleep 哔声消音（原声换成 1000 Hz 的哔，嘴边贴黄底标签，label 默认「消音」）。剪映草稿里变声要在剪映里手动加 |
| style_overrides | 覆盖风格预设，任意层级只改写到的键，比如 `{"sub": {"base": {"y": 0.74}}}` 只挪字幕位置、字号颜色不变 |

### zoom：口播推近

| 字段 | 说明 |
|---|---|
| t0, t1 | 生效区间，区间结束时恢复原大小（通常对齐一刀的边界，所以看不出跳回） |
| to | 推到多大，快推 1.08~1.18，缓推 1.05~1.15 |
| from | 起始大小，默认 1 |
| ease | 推近用时，默认 0.12 秒（快推）；缓推就设成整段时长 |
| push | 缓推预设：`suspense` 开场铺悬念，1.5 秒推到 115%；`settle` 段落结论或片尾，整段慢推到 112%。写了 push 就不用写 from、to、ease |
| dx | 推近时同时横向漂移，占画面宽的比例（0.02~0.04，正数往右） |

口播景别自动做，`auto_zoom` 选做法：
- `jump` 跳切三档（克制档默认）：每次回到口播全屏，人物大小在 100% / 115% / 125%（综艺感到 130%）里换一档，相邻两段不同；单段超过 4 秒就在句子停顿处再跳一档，跳档点优先放在粗剪的接缝上，看起来像换了机位。
- `snap` 再加句首快推：粗剪接缝或重点句（`level: key` 的字幕）开口那一刀，0.15 秒推进 7%，遮住跳剪也给重音加力；每 3 刀最多一次。
- `mixed` 跳档 + 句首快推 + 一句两推（网感档和综艺感默认）：超过 2.5 秒的重点句先推 5%，说到第二个强调词再推 5%。
- `false` 关掉。

手写的 zoom 和字在人后（mattes）的时段不动。zoom 只用来写特殊推近（情绪推、冲焦、缓推）。

### layout：口播画面怎么摆

没写的时间段都是口播全屏。

| mode | 效果 | 搭配的 B-roll |
|---|---|---|
| aside | 人移出画面，背景是口播的虚化压暗画面 | card / contain 的截图卡片浮在上面 |
| pip | 人缩成圆形小窗，压在 B-roll 上面 | cover / double 铺满的录屏或素材 |
| hidden | 口播画面完全不显示（声音还在） | cover 的全屏素材 |
| bg | 代码画的背景盖住口播：`"bg": "grid"` 网格（`variant`：`white` 黑底白网格 / `rainbow` 灰细网格透彩虹光晕，高级感用这个 / `neon` 彩虹细线 / `plaid` 卡其波浪格纹）、`"dots"` 点阵（`static` 静止 / `rainbow` 缓慢漂移带彩虹光晕）、`"metal"` 拉丝金属 | 和 pip 同时用，人放在背景上 |
| inset | 口播缩成圆角卡片，可以缩放：`anim` 为 `static` 0.79 宽静止卡片 / `expand` 在 `at` 秒 0.25 秒撑满全屏讲重点 / `shrink` 在 `at` 秒缩到 0.67 宽讲负面（`gray: true` 同时变黑白）/ `badge` 缩到 0.85 并在右上弹编号圆章（`badge` 写编号）；`to` 改目标大小（积极句推到 1.15、消极句缩到 0.8）；`bg` 四周的底，默认 `dots`，也可以 `black`、`blur`、`grid:rainbow` | 不配，或配小卡片 |
| circle | 口播被圆形蒙版收成一个圆：`anim` 为 `to_corner` 先缩到头像大小再滑进小窗位置（后面接一段同位置的 pip）/ `quick` 0.2 秒猛收成居中的圆 / `center_ring` 0.5 秒收成 0.68 宽的居中大圆加环；`ring`：`gold` / `white` / `pink_dash` / `cream` / `none`；`bg` 圆外：`blur`（口播虚化）/ `black` / `grid:rainbow` / `dots` / `none`（透明，露出底下的 B-roll） | bg 为 none 时配 cover 素材 |
| mockup | 手机样机（代码画的）放录屏或成片：`variant` 为 `screen` 深蓝渐变点阵底、样机居中，顶部超粗英文大标题 `title` 和中文副标 `sub` / `steps` 网格底、样机在右，左边黄色「方法：」下的 `steps` 按 `at`（每步出现的相对秒数）一条条出现 / `stack` 两台叠放，第二台 `src2` 在 `at2` 秒从右侧压上来，`labels` 给两个黄色标签；`src` 是样机里放的素材，竖屏素材最合适；横版录屏会按宽度放进屏幕、上下留黑，字小就写 `crop`（`crop2` 给第二台）先裁出要看的那块 | 不配 |
| combo | 圆头像图文版：口播裁成圆形头像（`crop` 同 pip）固定在一角，其余放标题和图片卡：`variant` 为 `band` 素材 `bg` 铺底、左上头像、右边标题 `title` 和黄色副标题 `sub`、下方一张横图 / `head_top` 牛皮纸底、顶部大头像、下面一张满宽横图 / `corner` 口播虚化底、两张卡依次上浮、左下头像压住第二张 / `tutorial` 教程截图版，加一行说明 `note`（`hl` 的词黄色）；`cards` 是图片列表，`at` 每张出现的相对秒数 | 不配 |
| overview | 要点目录与回顾：`variant` 为 `grid` 口播虚化、2×2 编号卡一张张弹出（每张是该章节的画面定格）/ `toc` 方格纸底、竖排红色主题加四张彩色斜标签卡 / `list` 暖色渐变底、两列「01·标题」逐条闪现 / `tilted_collage` 前面的画面缩成斜放卡片缓慢漂移；`items`：`[{"num", "text", "src"}]`，不写就从时间线的章节页自动取（编号、章节名、这一章第一张图片，没有就截口播）；`title`、`en` 给 toc 和 list 的标题，`every` 卡片间隔 | 片尾回顾或开场目录 |
| endcard | 头像关注尾帧（1.5~2 秒，不超过 3 秒）：`variant` 为 `follow` 黑网格底中央白边圆头像，红色加号一翻变成红勾，头像上方弧形黄字账号名 `name`，下面一行 `text`（默认「感谢关注」）/ `name` 黑底「@账号」放大滚入配「叮」；`avatar` 头像图片，不给就用口播画面里的人脸 | 不配 |
| matte | 抠像换底，人原地不动：`bg` 为 `blur` 背景轻度虚化（默认，`blur` 改虚化程度，默认 12）/ `keep` 原背景 / `grid:rainbow` 这类代码画的底；写了 `src`（话题截图、录屏、图片，`src_in` 起点）就是换话题背景，压到八成亮（`dim` 可改），`title` 在顶部弹出一行话题标题；`outline` 描边：`solid_white` 白色实线 / `color_thin` 黄色细边（`outline_color`: `green` 换绿色）/ `dashed` 白色虚线（背景自动压到六成亮）/ `torn_edge` 撕纸毛边 | 不配 |
| corner | 抠出来的人缩到角落给内容让位，开头 0.4 秒从原位缩过去：`variant` 为 `over_recording` 人叠录屏（`src` 录屏，竖屏铺满、横屏放上半屏，人在右下）/ `point_cards` 背景虚化、人带虚线描边在左下，右上三张深橄榄色观点卡 / `glass_cards` 深色网格底、右侧三张半透明蓝玻璃卡带透视浮着 / `tilted_cards` 以图片为底的斜卡从左滑入、沿对角线排开；`items`：`[文字 或 {"text", "en", "src"}]` 最多 3 张，`at` 每张出现的相对秒数；`side`（left / right）、`scale`、`outline` 可改 | 不配 |
| breakout | 人物出框：口播放进一个窗口照常显示，窗口外只露出抠出来的头或手：`variant` 为 `head_over_frame` 牛皮纸底上的拍立得相框，头顶探出相框上沿，`title` 写在相框下沿（英文用手写体）/ `band_pop` 上下两张图（`src`、`src2`），中间口播横条，头伸出横条压在上方大标题 `title` 前面 / `corner_over_card` 深色网格底上一张白色圆角画框装标题 `title` 和素材 `src`，人缩小站在左下压住画框角 / `hands_below_card` 口播装进圆角卡片、下沿裁到腰部（`waist`，默认 0.70），手越过卡片底边伸到黑底上；要人在腰部附近、手势伸到身体外面的素材，近景口播手一直在胸前时卡片下面露出的是整片身体，渲染会提醒；`overflow` 头出框多少（占画面高，默认 0.09） | 不配 |
| split | 分屏对比：`variant` 为 `torn` 撕纸竖条（各带竖排红字）/ `diagonal` 15° 斜线上下分割（蓝色倾斜标签）/ `focus` 两个圆角窗并排，`focus_at` 列出切焦点的相对秒数，没在讲的一边压暗 / `triptych` 三屏并排；`panels`：`[{"src": 路径或 "aroll", "label": "以前", "src_in": 0}]` | 不配 |

pip 的 `pip`：`x, y` 小窗中心位置，`d` 直径占画面宽度比例；`crop`：从口播画面取哪块正方形当头像（相对画面宽度，默认从顶部 8% 处取整宽），人脸偏的话调 x、y。小窗落在画面下部（会挡字幕）时，这段字幕自动上移到 `pip_y`；小窗放在上半部就不动字幕。
- `pos` 位置预设：`top_right`、`top_left`、`bottom_left`、`bottom_right`、`center`（定格强调时放大到正中）。画面右上有内容时用 top_left，引文段用 bottom_left；换位直接切，不做位移动画。
- `look` 样子：`ring` 细环硬边（默认）/ `feather` 羽化虚边，适合纸页和例子页 / `shadow` 白描边加投影，压在长录屏上。
- 整屏大字、章节页、巨数字出现时和章节转场前后，小窗自动消失再回来；`"hide_on_peak": false` 关掉。

mockup、combo、overview、endcard、corner、breakout 和换话题背景都自带声音（唰、啵、叮）；overview 和 endcard 在画面上时常驻字幕自动让开。

matte、corner、breakout 的人像不用自己准备：渲染时按这一段的时间自动抠（RVM 模型，头发丝能抠出来），抠过的段落有缓存，改了别的再渲不会重抠。第一次抠像会下载 15MB 的模型。人原地不动的版式里口播不自动推近。

aside 的 `stack`：`[截图路径, ...]` 或 `[{"src", "at"}]`，人移出画面后两三张截图居中依次进场、错位叠放（左滑、右滑、上滑轮换），`interval` 是进场间隔，默认 0.5 秒。

### broll

按数组顺序叠加，后面的盖在前面上。

- **透明底素材**（PNG 抠图、`make_graphic.py` 和别人做好的带透明通道的 .mov，`check_media.py --broll` 会标出来）只能用 `contain` 或 `card`，并配 `aside` 或 `hidden` 版式；用 `cover` 时透明的地方会直接露出底下的口播画面。
- **视频比区间短**时会定格在最后一帧。想让动作正好铺满区间，用 `speed = 素材可用时长 ÷ 区间时长` 调速；想让素材里某个画面对上某句话，用 `src_in` 和 `speed` 一起算。

| 字段 | 说明 |
|---|---|
| src | 图片或视频路径（HEIC 会自动转 PNG） |
| fit | `cover` 铺满裁切；`contain` 按宽度缩放保持比例；`card` 圆角加投影的卡片（截图最常用）；`double` 双层构图（下层铺满虚化、上层裁成 `ratio` 比例放在 `y` 处）；`band` 横版素材带（上层裁成 4:3 横条放在 0.45 高处，下层默认同素材压暗加网点颗粒、不虚化，财经知识口播约六成时长是这个版式；`bg` 换 `blur` 虚化或 `metal` 拉丝金属加白边）；`tilt` 透视斜置卡（截图斜放像桌上的纸，从下方升入再缓缓上升 5%；`tilt` 写 `left` / `right`，没写的连续几张自动左右交替；`pair` 用 `srcs` 给三张做镜像三联，两侧压暗退后）；`pages` 报告纸页飞入堆叠（`srcs` 给一张或几张报告截图，带投影旋转飞入，`variant`：`cascade` 白粉黄蓝四张从右上依次飞入错落 / `scatter` 十张从四面八方散落成一桌 / `stack` 一页带三道拖影斜飞进来叠成一摞 / `curl` 右下卷角的单页从上方滑下；自带翻页声） |
| w, x, y | contain / card 的宽度比例和中心位置；`max_h` 限制卡片最大高度比例 |
| src_in, speed | 视频从第几秒开始用、播放倍速。录屏写 `"speed": "auto"`：1 秒以上画面不动的等待段自动加速 2~10 倍正好塞进这段（加速处右上角标「快进 ×N」，`"speed_badge": false` 不标），录屏比这段短时整体放慢（最慢 0.36 倍）；`src_out` 限定只用到素材第几秒 |
| enter | `none` 硬切 / `fade` 渐显 / `slide_up` 上滑 / `slide_left` 左滑 / `slide_right` 右滑 / `rise_in` 从下方升入；铺满类默认硬切，卡片默认渐显，透视卡默认升入 |
| exit | `none` / `fade` |
| link | 同向运动衔接：写在后一张上，`left` / `right` / `up`，前一张往这个方向加速移出、这一张从反方向以同样速度移入，像一个连续动作。两张卡片首尾相接、都没写进出场时自动用 `left` |
| dim | 背景压暗突出主体：`sync` 卡片入场同一刻，背景 0.3 秒压到六成亮（高级感里卡片浮在口播全屏上时默认）/ `pre` 提前 0.4 秒压到四成亮，像灯光暗下来，用在数字、数据卡 / `false` 不压。相接的几张卡片共用一层 |
| motion | `push` 缓推、`pull` 缓拉（cover 图片，默认缓推 4%）；`drift` 缓推到 108% 同时横向漂移（cover），或卡片往右下漂（卡片）；`rise` 缓慢上升（卡片和 contain 素材默认上浮画面高度的 3%）；`none` 不动。画面一直在极慢地动，观众才不觉得是静止的 PPT |
| mosaic | 截图隐私打码：`[[x, y, 宽, 高], ...]`（相对素材画面的比例），渲染前把素材打成大颗粒马赛克副本，`mosaic_block` 改颗粒大小（默认 24，按 1080 宽）。框的位置先跑 `detect_sensitive.py` 找手机号、邮箱、人名、二维码，确认后抄进来；大字的 `src` 也能写 |
| bg / bg_src | double、band 的底：`blur` 同素材虚化（double 默认）/ `dim` 压暗加网点（band 默认）/ `metal` 拉丝金属 / `video` 主题视频压暗做底，`bg_src` 写一段话题视频（星空、数据流、会议），循环铺满、压暗三成、轻虚化 |
| crop | `[x, y, 宽, 高]`，只用素材的这一块（相对素材的比例）。横版录屏、带小字的截图放进竖屏前先裁出要看的区域，否则字小得看不清 |
| frame | 素材卡装饰边框（card / contain）：`glow` 边缘一圈柔和淡黄光 / `viewfinder` 叠相机取景框（四角直角标、REC、ISO 和快门、曝光刻度），像在回看素材。写了 frame 默认宽 0.68、中心在 0.57 高、从下往上滑入，放在胸口到腰之间 |
| marks | 截图划重点（card / contain 的图片）：`{"boxes": [[x, y, 宽, 高], ...], "look": "yellow", "at": [0.6, 1.6], "wipe": 0.4}`，boxes 按截图比例框出要划的行，一道道从左往右划出；`look` 为 `yellow` 黄色荧光笔（正片叠底，黑字透出来）或 `inverse` 黑色反白（被划到的字变白字黑底，比黄色更重，同一段已经用过黄色时换这个；只对黑白文字截图用）。每道自带一声上滑音 |
| focus | 局部放大：从 `t` 秒起用 `dur` 秒平滑放大到 `scale` 倍（录屏 2.4~3.3），聚焦在 `cx, cy`；写 `hold` 就停 hold 秒再平滑缩回全景。cover、card、contain 都能用 |

### subs：跟读字幕

| 字段 | 说明 |
|---|---|
| text | 显示的文字，去掉句末标点，句中逗号换成空格 |
| level | `base` 口播底字 / `key` 重点句（更大、带弹出动画） |
| hl | 要变色强调的词，全片只用一个强调色 |
| anim | key 级别的入场动画：`pop` / `slide_up` / `fade` |
| y | 单条覆盖纵向位置；小窗在画面下部时会自动上移 |
| jy_flower | 只在剪映草稿里生效的花字名，见 `assets/jianying_resources.json` |

### beats：按内容自动搭配大字

每条是一段话：标内容类型、给出要上屏的字，渲染时由 `scripts/library.py` 从手法库挑手法、算出现时刻，展开成 titles（timeline 文件不变）。

```json
{"t0": 36.4, "t1": 38.9, "beat": "list", "items": ["一个功能一个会话", "剩 20% 写交接", "新会话先读交接"], "items_en": ["one task one session", "handoff at 20%", "read before you start"]}
{"t0": 9.5, "t1": 12.2, "beat": "topic", "text": "它不仅没写对", "text2": "还把功能改坏了", "hl": ["改坏了"]}
{"t0": 28.4, "t1": 29.5, "beat": "compare", "left": "越聊", "right": "越蠢", "items_en": ["more talk", "less smart"]}
```

| 字段 | 说明 |
|---|---|
| beat | 内容类型：`hook` 开场钩子 / `topic` 点题 / `chapter` 章节 / `list` 并列 / `number` 数字 / `compare` 对比 / `steps` 步骤 / `quote` 金句 / `concept` 新概念 / `evidence` 证据 / `emphasis` 重点词 / `negative` 负面 / `question` 提问 / `emotion` 情绪 / `demo` 演示 / `story` 故事 / `transition_talk` 过渡 / `cta` 结尾互动 |
| 上屏的字 | 按内容给，给得越全可选的手法越多：`text`、`text2`（后半句）、`lead`（引子）、`left` / `right`、`items`、`items_en`、`en`、`chunks`（`[{"text", "w": 1~3}]`，w 是重要程度）、`number`（巨数字）、`value`（"58%" 这种结论数字）或 `from` / `to` / `suffix`（滚动数字）、`conclude`（列举后的结论）、`hl`。数据卡再给 `label`（数字后面的说明）、`value2` / `label2`（第二行，说到时才出现）；占比给 `pct`（0~100）或 `pcts`（和 `items` 一一对应的几个占比），圆形图上长扇形再给 `src`（logo、地球这类圆形图）；章节给 `number`、`sub`（小标题）、`items`（雾面上的三个并列词）、`preview`（预告窗素材）、`main`（总标题，原位换分标题用）；并列词配图标再给 `icons`（和 `items` 一一对应的 Fluent Emoji 英文名，如 Laptop、Rocket、Light bulb、Money bag，全表见 github.com/microsoft/fluentui-emoji 的 assets 目录，MIT 授权；图标要和词义对得上，对不上就别用这个手法）；主词裂开、呐喊声波给 `sub`（插进缝里或压在下面的副句）；表情包吐槽字给 `src`（用户自己的表情图）或 `emoji`（Fluent Emoji 英文名，如 Face with tears of joy、Face screaming in fear）；对话气泡给 `text`（头顶气泡里的问句）或 `items`（散在两侧的几种情况）；引导词换重点词给 `lead`（引导词）和 `text`（重点词） |
| note、note_look | 主标题旁小补充：`note` 一行俏皮话或标签，`note_look` 为 `tag` 便利贴 / `arc` 弧形；主标题出来 0.3 秒后弹到它右上角 |
| sting、ambience | 梗音效和氛围铺垫音：`sting` 写声音名（punch、boing、dizzy、honk、rimshot、sad_trombone、fail_piano、dun_dun_duun…）、true 按轮换配、false 关（情绪句默认配，负面句默认不配）；`ambience` 写 suspense / calm / false（提问句默认铺悬念小鼓） |
| use / variant | 指定手法和变体（id 见 `library.md`）；不写由代码挑 |
| side、y、sfx | 同 titles |

代码挑手法的规则：内容类型匹配、字数够用、风格和强度档允许；章节页全片只用一种载体（第一次按强度档挑：网感档白雾镂空序号、克制档经典章节页、综艺感章节标题页），数据卡、章节页全片沿用第一次的样子只换内容；同一手法 30 秒内不重复，和挨着的大字换版式，重手法之间隔 20 秒，变体轮着用；这段话四成以上时间有素材卡片在画面上时不自动加大字（同一时刻一个视觉焦点）。字出现的时刻按 lines.json 的逐字时间对到口播说出那个词的瞬间。

### titles：关键词大字、章节标题、金句

排版由 `scripts/typeset.py` 算位置，成片和剪映草稿用同一套结果。高级感参考大字报式字幕教程：字放在人的一侧、不对称；一组字里大小差 3 倍以上；关键词用压窄的特粗黑体、红白两色；书法或手写字点缀；背后可以叠半透明巨字。整组字会自动避开字幕区（底边不超过画面 75% 高处）。

| layout | 长什么样 | 写哪些字段 | 适合 |
|---|---|---|---|
| side（高级感默认） | 人的一侧：一行小字引子 → 压窄特粗大字（可多行）→ 一行英文斜体衬线 | `lead`、`text`（`\\N` 换行，每行 2~4 字）、`hl`、`en`、`side`（left / right）、`y`（字块上沿，默认 0.5） | 关键词、观点、结论 |
| split | 两个词分在头的左右两侧，各带一行拼音或英文小标 | `left`、`right`（各 2~3 字）、`left_en`、`right_en`、`hl`、`y`（默认 0.27，头部高度） | 对比、两个关键词、「来点 / 干货」 |
| quote | 左对齐的宋体金句，含强调词的那行放大 1.4 倍，下面一行英文斜体 | `text`、`hl`、`en`、`y` | 金句，配 `aside` 虚化背景 |
| chapter | 镂空的超大章节号 → 压窄特粗章节名 → 红色英文小标 → 一行说明，左下对齐，整屏压暗 | `number`、`text`、`en`、`sub`、`y` | 章节开头，配 `aside` 或 `hidden` |
| mix | 自己逐行指定的字块 | `lines`：`[{"text", "size", "role", "color", "spacing"}]`、`x`、`y`、`side` | 角标章节标签、特殊组合 |
| plain（综艺感默认） | 居中一行大字，可带描边、底板和一行说明 | `text`、`sub`、`outline`、`box`、`align` | 综艺感大字 |
| stack | 编号卡逐条出现：标题 + 01、02、03 一条条累加，前面的留着 | `text`（标题）、`items`、`every`（每条间隔秒）、`side`、`y` | 「三步走」「几个原因」这类并列要点，常配 paper 纸页底 |
| count | 数字滚动大字：数字从 from 滚到 value，上面一行引子、下面一行说明 | `from`、`value`、`decimals`、`prefix`、`suffix`、`lead`、`text`、`roll`（滚动秒数） | 关键数字；配 sound tick |
| statcard | 深色描边数据卡（压暗背景上浮出）：`variant` 为 `ornate` 暗金角花 / `lime` 黄绿发光加上下金色小花纹 / `rows` 简洁黑卡，第二行前先亮绿勾 | `title`、`en`、`rows`：`[{"value": "580", "label": "完成发射次数"}, {"value": "534", "label": "成功着陆次数", "at": 1.6}]`（第二行在 at 秒出现，数字尾巴的「+」做上标）、`x`、`y`（默认 0.60）、`w` | 关键数据、对比数据 |
| ring | 占比环形图（压暗背景，放在胸口）：`variant` 为 `donut` 细圆环顺时针填到比例，中心百分比同步滚动 / `pie` 饼图扇区长出后略张开，两边弹出渐变虚线标签 / `slice` 圆形图（`src`）上一块色块从 12 点长到占比 | `pct`、`items`（pie：`[["美国", 55, "USA"], ...]`）、`src`、`text`、`lead`、`color` | 占比、份额 |
| fog | 白雾镂空大序号（章节）：`variant` 为 `panel` 下方一半蒙七成白雾，巨大斜体序号镂空透出后面的人，像便利贴从左下翻进来，雾上压章节名、英文和三个并列词 / `window` 整屏白雾，只有占画面七成高的序号是清晰窗口。背景很亮（白墙）时自动换深色雾 | `number`、`text`、`en`、`items` | 清单式的「第 N 点」 |
| chapter_page | 章节标题页（口播虚化做底）：`variant` 为 `hand` 斜放毛笔大标题、白色小标题、拉开字距的英文、蓝色签名体斜穿、右边缘竖排灰字出血 / `preview` 暖橙到灰蓝渐变底，左上衬线编号和标题，右下圆角竖屏小窗播 `preview` / `swap` 中间先出白色总标题 `main`，`swap_at` 秒（默认 1 秒）同一位置换成蓝色块反白的本节名 | `number`、`text`、`en`、`sub`、`sign`、`preview`、`main` | 章节开头 |
| word | 整屏单字页：一两个字撑满画面，下面一行红色英文 | `text`、`en`；配 `hidden` 黑底 | 强动作词、段落冲击页 |
| flank | 人两侧对称短语：一句话拆两段放人的左右空位，先后出现；`variant` 为 `white_red` 左白右红 / `stagger` 错落双字 / `pop` 双词弹出 | `left`、`right`、`left_en`、`right_en`、`right_at`（右边出现的秒数）、`y`（默认 0.40） | 对比、两个关键词 |
| yield | 前句让位后句重点：前半句先出，后半句出现时前半句缩小挪开；`variant` 为 `push_up` / `diagonal` / `gray_down` / `squeeze` | `text`、`text2`、`hl2`、`switch_at`、`y`（默认 0.60） | 「铺垫 + 重点」句 |
| chunks | 说一块出一块：3~5 块按口播出现，越重要越大 | `chunks`、`chunk_at`、`side`、`y`（默认 0.50） | 金句、概念解释 |
| list | 并列项逐条出现；`variant` 为 `conclude` 列举后收拢出结论 / `bullets` 侧边方块要点配英文 / `grid` 编号淡成底纹网格 / `one` 一屏一个三连击 | `items`、`items_en`、`conclude`、`item_at`、`y` | 并列、步骤 |
| chips | 标签卡逐个点出；`variant` 为 `bilingual` 胸前中英卡 / `red_bar` 红条擦入 / `gold` 暗红金字 / `capsule` 彩色胶囊 / `stack3` 浅底竖排 | `items`、`items_en`、`item_at`、`chip_color` | 并列短语、概念标签 |
| concept | 发光概念词：压暗后两三个字带柔光、字距拉开，下面灰色英文 | `text`、`en`、`y` | 新概念第一次出现 |
| bignum | 巨数字点题：一侧立起占画面高七成的灰白数字，旁边星光 | `number`、`text`、`side` | 「这 4 个方法」 |
| number | 大数字浮现：先压暗，窄体大数字带柔光从模糊变清楚，上面金色小标题，下面灰色说明 | `value`、`lead`、`text` | 结论数字、金额 |
| mixline | 一行大小字混排：一行里只有关键词放大，其余小字同一条底边；`variant` 为 `static` 关键词放大 2.7 倍变金（默认靠左）/ `focus` 整句同样大溶解飘下，`focus_at` 秒关键词放大到 150% 变金、其余缩到 80% | `text`、`key`、`focus_at`、`ratio`、`align`（left / center）、`y`（底边，默认 0.66） | 重点词、数字、短金句 |
| （behind） | 写 `"behind": true` 就是字在人后，人像自动抠；`variant` 为 `brand_head` 2~3 个字撑满画面宽度、放在头部高度（默认，浅色墙面自动换深色字）/ `top_keyword` 4 个字以内的橙黄关键词压在头顶，头发盖住字的下沿，位置按头顶自动算 / `hollow_sandwich` 两行英文巨字（用 `en`），实心字在人后、同一行只剩描边的字在人前，人像嵌在字中间 | `text`、`en`、`y`（brand_head 默认 0.21，hollow_sandwich 默认 0.22） | 点题、开场关键词 |

所有 layout 都能加三种点缀：
- `block`：色块衬底关键词，先刷块再出字，如 `{"color": "#1C46B8", "style": "solid"}`；style 为 `solid` 紧贴实心块 / `offset` 错位刷块 / `skew` 斜切渐隐条 / `grow` 方块拉长成条；默认垫在第一个 hl 词背后，块上的字自动反白或反黑。
- `ghost`：半透明超大英文底纹，如 `{"text": "MEMORY", "y": 0.14, "alpha": 0.4}`，用 Anton，自动撑满宽度。
- `note`：手写批注，如 `{"text": "划重点", "x": 0.62, "y": 0.6, "rot": -7}`，用志莽行书、强调色。

通用字段：`t0`、`t1`；`sfx`（`false` 不配音效，`"chapter"` 换成章节音效）；`size` 大字基准字号（高级感 200，按 1080 宽画布）；`color`、`hl_color`（高级感暖白和红 #D7262D）；`anim`（`blur_in` 模糊渐清并从侧边滑入，高级感默认；`pop` 弹出，综艺感默认；`flash` 先亮白闪一下再定住；`type` 打字机光标逐字打出；`zoom_in`、`drop`、`blur_still`、`fade`、`slide_up`、`none`；克制入场：`fall` 从上方一成画面高处落下模糊变清、`graypop` 灰色半透明小字放大成白字、`flip` 像卡片一样绕竖轴翻进来）；`dim_after`（读完压暗留底：从出现算起几秒后 2.5 秒慢慢暗到三成多，留在画面上；beats 上也能写 `anim`、`dim_after`）；`font` 主标题字体角色；`condense` 横向压缩百分比（高级感 82）；`max_bottom` 字块底边上限。

字号单位是 ASS 字号（行高），中文字宽约为字号的 0.69；脚本会自动缩小字号，保证一行不超出画面。

同一时刻只放一个视觉焦点：用了 behind 大字，就别在同一秒再放别的大字。

statcard、ring、fog、chapter_page 是逐帧合成的画面（`scripts/cards.py`），第 6~9 批的重点字、贴纸、特效大字和大字排版（keytext.py、annot.py、effects.py、bigtype.py）也是，写法见 `library.md` 各条；剪映草稿里这些段落铺成片画面。章节页（chapter、fog、chapter_page，第 9 批加了 topcard 顶部整句卡、vflank 竖排双列页）在画面上时常驻字幕自动让开，小窗也让开；章节页开头自动加效果转场、配乐留白和换段。

第 10 批开场与结构（structure.py）：`montage` 开场快闪蒙太奇（`macro` / `chaos`，`srcs` 素材池、`text` 落定的大标题）、`collage` 卡片拼贴预告（`fan` / `scatter` / `wall` / `paper`，`srcs`、`text`、`text2`、`big`、`numbers`）、`textfirst` 黑底文字先行（`stack` / `meme` / `warning`，`lines`、`hl`、`line_at`）、`qframe` 反问钩子画框问号（`text`）、`poster` 整屏海报标题页（`cinema` / `film` / `grid` / `popart` / `magazine`，`text`、`en`、`sub`、`issue`、`lines`、`badge`）、`askpage` 求赞收藏提醒页（`flank` 写 `left`、`right`、`left_en`、`right_en`、`arc` / `lines`）、`inkecho` 结尾回扣开场大字（`text`、`color`、`y`）、`actionrow` 点赞转发评论条（`items`、`name`）、`slogan` 固定口号收尾（`text`、`text2` 两个字）；章节载体加了 `gesture` 圆头像手势卡（`number`、`unit`、`src` 比手势的镜头）和 `cutnum` 剪纸大数字页。

第 11 批信息卡片（infocard.py）：`callout` 界面截图圈注卡（`src`、`crop`、`mark` 圈哪一点（截图里的比例）、`label`、`side`）、`widget` 仿界面小组件（`search` 写 `text` 关键词、`title` / `sfx` 写 `items` 音效名卡）、`flow` 流程节点逐级点亮（`items` 最多 5 个、`item_at`、`title`）、`axis` 时间轴区间示意（`two_point` 两个 `items` / `events` 事件 `items` / `year` 年份 `items`、`target` / `wave` 波形切点卡，`src`、`wave_t`、`cut_at`）、`stepwall` 暗色拼格步骤墙（`items` 3~8 个步骤名）、`reslist` 资源清单页（`paper` / `poster`，`items` 最多 7 条、`title`、`category`、`note`）、`typerow` 竖卡一排类型展示（`screenshot` 写 `srcs`、`items`、`pinyin` / `wireframe` 写 `kinds` 构图名、`focus` 放大第几张、`giant` 两侧巨字、`note`）、`photostack` 并列图片卡错落（`tab` / `tilted`，三张 `srcs` 配三个 `items`）、`comments` 评论气泡堆（`behind` 人身后的评论卡 / `pileup` 气泡堆满，`items` 写文字或 `{text, likes, name}`；示意评论别做得像真实截图）、`fanwin` 头后三窗口扇形展开（`srcs`）、`ticker` 黑底发光播报框（`title`、`hl`、`src` 截图反色上滚或 `lines`）、`quotetype` 压暗底引文逐行打出（`lines` 最多 5 行、`by`）、`labelcol` 纸页左标签右内容卡（`items`: `[{label, en, src}]`）、`person` 人物信息卡（`profile` 写 `name`、`fans`、`avatar` / `nameplate` 写 `name`、`titles`）、`products` 压暗叠商品卡（`items`: `[{name, price, src 或 icon, button}]`）、`translate` 外文原文配中文翻译条（`src`、`line` 那一句的框、`text` 意译、`hl`）。

第 12 批版式与镜头（scene.py）：`splitwin` 同画面拆窗看细节（上窗自动框脸，`hands` 下窗框手的位置）、`window` 素材窗口嵌入（`thin` / `glow` 写 `label`、`sub` / `shadow` 写 `title`，`src`、`src_in`、`crop`）、`bands` 并列词素材条堆叠（`push` / `drop` / `gray`，`items` 2~3 个配同样多的 `srcs`）、`matteband` 抠像人站素材带（`three` / `tech` 写 `tag`，`srcs`、`text`、`sub`）、`papercollage` 纸张分层拼贴（`srcs`、`text`、`stickers` 3D 图标名）、`figure` 话题人物压暗剪影（`src` 那个人的照片，自动抠像；`text`、`sub`）、`moodword` 情绪图配一个字（`src` 意象图、`text` 一个字、`color`）、`parallax` 多层视差缓动（`ambient` / `shift`，`text`、`lines` 两列竖排小字、`icon` 主体物、`bg_src`、`shift_at`）。定格暂停是顶层 `freezes`（见「版式 paper / frame、冲焦、定格」）。

第 13~15 批（一星）文字、特效与贴纸：`grid2x2` 田字格方块字（四字 `text`、`pair` 竖排对比词）、`persp3d` 透视立体大字（`text` 或 `left`、`right`）、`stairs` 阶梯斜排字（`text` 最多 5 字）、`overlapframe` 字跨框边混搭（`items` 最多 5 组）、`orbit` 字环绕人旋转（`text` 最多 6 字）、`wordwall` 字墙与字云（`wall` 一个字 / `cloud` 写 `items` 和红色关键词 `text`）、`pinyin` 拼音谐音注释（`above` / `pun` 写 `text`，拼音自动出、多音字写 `pinyin` 校对 / `list` 写 `items`: `[{text, pun}]`）、`credits` 双语制作团队（`items`: `[{role, en, name}]`、`src` 空镜）、`readygo` 开讲前暗角收黑（两字 `text`、`en`、`iris_at`）、`darkenword` 手写字变暗混合（`text`、`y`）、`tape` 斜向警戒带（`text`、`text2` 英文）、`searchhook` 模糊搜索结果钩子（`src` 搜索录屏、`clear` 清晰的那块、`text`、`items`、`number`）；`shapecut` 相似形状快切（`srcs`、`circles` 每张的圆心半径、`every`）、`radial` 径向模糊失焦（`lines`）、`whitefade` 底部白色渐隐、`particles` 粒子飘落（`starfield` 写 `text` / `money` 写金额 `text`）、`extend` 取色画布羽化延伸（`text`、`sub`、`shift`）、`idwall` 斜排 ID 水印底纹（`text`）、`panels` 半透明 PPT 面板比喻（`text` 红色巨字、`items` 面板标题）、`screenblend` 灰度绿幕去饱和叠加（`src` 光效烟雾素材）、`swatch` 磨砂色卡（`colors`、`text`、`note`）、`diagram` 示意图分级发光标注（`src`、`stages`: `[{poly: [[x, y], ...], label}]`）；`trail` 头像轨迹残影（`path`）、`spinring` 主体物缓转加虚线环（`src` 抠好的 PNG 或 `icon`）、`gesturetext` 文字跟手势（`keys`: `[[秒, 缩放, 横移, 竖移, 横向挤压]]`）、`paperpanels` 透视纸板（`items`: `[{text, note}]`）、`orbitcover` 地球轨道覆盖、`armwipe` 手臂抹字（`text`、`wipe_at`、`reverse`）、`mics` 话筒围采（`text`）、`framesticker` 边框贴纸（`polaroid` / `film` / `cartoon`）、`painpoint` 痛点词接怎么办（`text`、两个 `items`、`ask`）、`jytpl` 剪映综艺文字模板近似（`energy` / `warn` / `out` / `aaa`，剪映草稿里换真模板）。

第 9 批大字排版（bigtype.py）：`giant` 巨字压画面（`metal` / `red_bleed` / `collage`，`trad` 写繁体先繁后简）、`ghostword` 巨字底纹装饰（`hollow` / `emboss` / `edge` / `grunge`，主标题 `text`、`lead` 一起画）、`boxed` 方框单字标题（`tag` 黄色小字、`sub` 一行说明、`behind` 让人挡住几个框）、`corners` 四角分字围人（`four` / `shrink` / `flank`）、`circletext` 圆形头像配环绕字（`arc` 写 `text`、`text2` / `tangent` 写三个 `items` / `sandwich` 写 `text`、`text2`）、`splitswap` 分屏圆头像巨字轮换（`src` 上半屏素材、`crop`、`items`、`item_at`）、`typepanel` 打字机长文面板（`accumulate` / `top_card`，`lines` 每句、`line_at` 每句开打的时刻、`cps` 每秒几个字）。这些版式直接读口播画面或抠像，这段时间不自动推近；铺满整屏的（circletext、splitswap、topcard、vflank，以及 red_bleed、collage、emboss、grunge、shrink、top_card 变体）算盖住口播。

### 版式 paper / frame、冲焦、定格、配乐换段

- layout 的 `mode` 还有 `paper`（代码生成的纸页底，`"paper": "kraft"` 牛皮纸或 `"cream"` 米白纸，盖住口播、声音还在；米白纸上的大字自动换深色）和 `frame`（画框底：口播缩进带白边的画框，后面是虚化口播，用在「第一招」这类小节编号点）。单机位视频每 10 到 30 秒换一次底。
- broll 的 `punch`：冲焦，`{"t": 0.5, "dur": 2.0, "scale": 2.3, "cx": 0.5, "cy": 0.3}`，硬切放大到截图里关键数字的位置（cx, cy 按截图比例），停一会儿硬切回全图，自动配快门声。只给关键数字用，每分钟最多一次。
- 顶层 `freezes`：定格暂停，`[{"t0": 22.4, "t1": 23.8}]`，画面停在这一帧并压暗，头像从角落放大到画面中间说这一句（`d` 头像大小、`y` 位置），画暂停图标、配快门声，配乐静音。用在长段 B-roll 中间那句带情绪的话。
- 配乐换段：只有一首配乐、没写 sections 时，每个章节页处自动跳到同一首曲子里能量最高的另一段，重拍对准章节页，换段前配乐轻停一下。需要节拍文件（beat_sync 生成）；`"music_sections": false` 关掉。写了 sections 或给了几首曲子，按 audio 的「段落换曲」走。

### transitions：章节转场

默认不用写：每个章节页开始处自动加一个效果转场，按风格轮换（高级感网感档：甩切、漏光、光圈、撕纸、闪白；克制档：闪白、模糊扫屏、漏光、压黑；综艺感：闪白、故障、甩切、撕纸、模糊扫屏），相邻不同、30 秒内最多一个，其余都是硬切（财经知识口播原片九成以上是硬切）。要自己指定就写 `"transitions": [{"t": 25.9, "type": "light_leak"}]`（写了就只用写的），写 `"auto_transitions": false` 关掉。

每个效果转场自带一声过渡音，起音对准转场开始那一帧；想换声音写 `"sound"`（如 `whoosh_big`），不要声音写 `"sfx": false`。硬切不配声音。有变体的写 `"variant"`。

| type | 用在哪 | 变体 | 自带声音 | 剪映里对应 |
|---|---|---|---|---|
| `flash` | 闪白：换小节、换话题 | | 唰 `whoosh` | 闪白 |
| `dip_black` | 压黑：段落收尾、情绪沉下来 | | 旋风 `whoosh_big` | 闪黑 |
| `blur_swipe` | 竖向动态模糊扫屏：节奏快的段落切换 | | 唰 `whoosh` | 竖向模糊 |
| `whip` | 动态模糊甩切：整屏往一边甩走，下一段同方向甩进来；`dir` 写 left / right / up / down | | 唰 `whoosh` | 横向模糊 |
| `light_leak` | 漏光闪过：橙黄暖光从一侧扫过，几乎铺满时换段 | `flash`、`zoom_reveal` 光退时下一段从六成大小放大回来 | 穿梭 `shuttle` | 复古漏光 |
| `glitch` | RGB 故障闪切：红青错开、几条横切片左右错位 | | 电流 `glitch` | 信号故障 |
| `iris` | 圆形光圈：收成中下部一个圆，圆里换段再放大；`x`、`y` 是圆心，要对准脸 | `swap`、`open` 黑底小圆张开成圆头像再打开 | 唰 `whoosh` | 圆形遮罩 |
| `tear` | 撕纸揭开：上一画面被带白纸芯的撕边撕掉 | `diagonal` 斜向、`split` 中间上下撕开 | 揉纸 `crumple` | 撕纸 |
| `blocks` | 色块碎片擦屏：橙红、深色矩形碎块几帧内铺满，切点后散开露出下一段；`colors` 换颜色 | `random`、`bars` 黑色竖条随机升起擦屏 | 电流 `glitch` | 色块故障 |
| `tunnel` | 隧道穿梭：中心青色放射光柱冲出来，下一段从画面中心 20% 冲到满屏，开场第一下或章节页进正片；`color` 换光柱颜色 | | 穿梭 `shuttle` | 穿越 |
| `occlude` | 主题物遮挡扫屏：主题物带纵向模糊从下往上冲过，盖满那一帧换段；`src` 写主题物图（透明底最好），或 `emoji` 写 3D 表情英文名 | | 大段唰 `whoosh_big` | 竖向模糊 |

白场载体接力（只配白雾章节页 fog 的 window）：`"enter": "cover"` 开头 0.3 秒白雾从下半屏往上铺满，紧跟在底部面板后面时面板不淡出、直接接力；`"exit": "door"` 最后 0.5 秒整屏白雾像门一样以左边为轴转开，配开门声；`"shapes": ["2", "?"]` 加 `"shape_at"` 镂空数字逆时针转一下换成问号。

### fx：整屏特效

顶层 `fx` 写在某一段时间上的整屏特效，`[{"t0": 52.0, "t1": 54.2, "type": "crack"}]`。调色、暗角、扫描线、网点、放大镜、模糊、压暗聚光框、人脸特效压在常驻字幕下面；震动、裂屏、宽银幕黑边、全剧终连字幕一起。每种自带声音，写 `"sound"` 换、`"sfx": false` 关。剪映草稿里剪映有对应特效的放真特效，没有的那几秒铺成片画面。

| type | 效果 | 字段 |
|---|---|---|
| `bw` | 变黑白：失落、听不懂 | |
| `shake` | 震动：冲击、惊讶，约 12 Hz 越抖越轻 | `amp` 幅度 |
| `crack` | 裂开了：崩溃，屏幕从一点裂开、跟着抖一下 | `at` 裂开的点，默认右上角避开脸 |
| `magnifier` | 放大镜：把一点放大两倍；`reach` 变体手柄从画外伸进来，镜片 0.5 秒滑到 at、停住、最后 0.5 秒移走（默认 1.5 倍） | `at` 要放大的点、`zoom`、`r` 镜片半径；reach 加 `from` 画外起点、`move` |
| `tilt` | 画面歪头倾斜：0.3 秒整屏（连字幕）转到 -10 度并放大 1.1 倍，高级感慎用 | `angle`、`back` 最后 0.3 秒转回来 |
| `the_end` | 全剧终：片尾整屏压暗，毛笔大字 | `text`、`en` |
| `blur` | 模糊遮挡：遮隐私 | `box` [x, y, w, h] |
| `spotlight` | 聚光灯暗角，只用在开头或重大转折 | `variant`：`push` 同时缓推到 112%、`drama` 加荧幕噪点配重音 |
| `crt` | 扫描线老电视，别全片一直开 | `variant`：`emphasis` 一句话强调、`section` 段落收尾加桶形弯曲和推近 |
| `halftone` | 网点丝印质感 | `variant`：`screenprint` 扣掉人像只在背景、`bg_grain` 叠在 aside、hidden 的暗底上 |
| `grade` | 调色变化 | `variant`：`desat_cool` 降饱和偏冷灰、`band` 先变黑白再让红绿橙色块扫过（`colors`） |
| `letterbox` | 宽银幕黑边，1~3 秒，常配一行引用大字 | `text` 下黑边里滚动的小字 |
| `dimbox` | 压暗聚光框游走：整屏压暗，虚线框在脸、胸口之间移动 | `boxes` [{at, box, shape: rect / circle}]，不写就自动框脸再移到胸口 |
| `face` | 人脸情绪特效：剪映人物特效名，常叠两个；成片里放大头、头边贴 3D 表情和手写问号近似，脸用 OpenCV 检测 | `names`：大头、红温大头、一脸问号、懵、迷茫、惊讶、中刀、打击、石化了、宕机中、尴尬住了、灵机一动、真的会谢、秘密 |

代码画的背景（`backgrounds.py`）都能写在纸页底 `{"mode": "bg", "bg": ...}` 和抠像换底 `{"mode": "matte", "bg": ...}` 里：`grain` 深灰纸纹暗角底（纯文字页）、`waves` 黑底动态波浪线（缓慢流动）、`floor` 3D 透视空间底（`variant` 或 `floor:<变体>`：`floor` 透视地面 / `tunnel` 上下隧道 / `corner` 斜角走廊 / `color` 青色发光格）。

波普网点底写在版式里：抠像换底 `{"mode": "matte", "bg": "popart:pink"}`（或 `popart:red`），纸页底 `{"mode": "bg", "bg": "popart"}`。窗口按节拍变形是版式 `{"mode": "morph", "at": [每次变形的秒数]}`：人在小窗里，背后是同画面虚化，窗口小圆、大圆、圆角方、竖长圆角、接近满屏一下下变。

### inserts：插入影视梗片段

顶层 `inserts`：`[{"t": 132.0, "src": "meme/片段.mp4", "in": 3.2, "dur": 1.2, "text": "嘿嘿"}]`（`text` 叠一行荧光绿花字，插入反应镜头用）。成片渲完后在 t 秒处硬切进用户给的片段：横版居中黑底，不带字幕和头像，用片段自己的声音（统一响度），配乐在这一段留空，再硬切回口播；片子变长 dur 秒。插在抖完包袱后的停顿处，全片 1~2 次，超过 1.5 秒拖节奏。只用用户自己提供的片段（版权）。剪映草稿里不插，要在剪映里手动放。

### doodles：手绘贴纸

圈注（`circle`，多圈涂鸦圈 `multicircle`、螺旋圈 `spiral`）、下划线、箭头、闪光、三短线放射（`exclaim`）、打勾、打叉，一笔笔画出来（`scripts/doodle.py`）。要指着截图上的按钮、数字，用 titles 的 `arrow` 箭头和 `focus` 聚焦框（坐标按画面比例，截图里的位置要按卡片的摆放换算）：

```json
"doodles": [{"t0": 10.9, "t1": 12.2, "type": "circle", "target": {"text": "改坏了"}, "rot": -3},
            {"t0": 30.1, "t1": 31.4, "type": "arrow", "x": 0.7, "y": 0.45, "w": 0.25, "h": 0.12}]
```

`target` 写要圈的字，自动找这一刻画面上含这几个字的大字（beats 自动展开的也算），位置按排版结果自动算；同一时刻有两条大字都含这几个字时加 `"title": 第几条`；指向画面上别的东西时用 `x, y, w, h`（中心和大小，按画面比例）。可选 `color`（默认强调色）、`width`、`rot`。每个贴纸对着一个具体的词，停 1 到 2 秒；高级感每分钟最多 1 个，综艺感最多 4 个。只在成片里有，剪映草稿里用剪映自带贴纸代替。

### music_breaks：配乐留白

只有一首配乐、没写 sections 时，默认在每个章节页出现前 0.7 秒把配乐压下去（-16 dB），章节页那一下再回来，相隔至少 30 秒（财经知识口播原片约 46 秒一次留白，停完接大变化）。自己指定写 `"music_breaks": [[44.2, 45.0]]`，写 `false` 关掉。写了 sections 时用段落的 `"seam": "gap"` 做完全停下的留白，重音收住用 audio 的 `stops`。目前只在成片里生效，剪映草稿要在剪映里给配乐打音量关键帧。

### mattes：现成的人像片段（一般不用写）

字在人后的人像渲染时自动抠，不用写这个字段。只有想用别处抠好的人像（比如剪映导出的透明视频）时写 `[{"t0", "t1", "src": "mattes/m1.mov"}]`（画布尺寸、透明底、从 0 秒开始），覆盖到的 behind 大字就用它。渲染顺序：画面 → behind 大字 → 人像 → 人前的字（hollow_sandwich 的描边字）和其余字幕。字被人挡住超过四成时渲染会提醒。

### overlays：叠加的图片和透明视频

箭头、手绘圈、代码生成的信息图（`make_graphic.py` 输出的 .mov）都放这里或放 broll。字段：`src, t0, t1, x, y, w`。

### effects / stickers：剪映专属

只在剪映草稿里生效，成片渲染会忽略。`effects` 的 name 是剪映特效名（人物特效如「大头」「真的会谢」「灵机一动」，画面特效如「聚光灯」「暗角」「模糊」「马赛克」）；`stickers` 的 name 见 `assets/jianying_resources.json`。纯代码成片要表达同样的情绪，用 overlays 放表情图或用 titles 放字。

### audio

| 字段 | 说明 |
|---|---|
| voice | 人声处理：`lufs` 目标响度，默认 -16（高级感）/ -15（综艺感）；`denoise` 降噪、`deess` 去齿音、`compress` 轻压缩，默认都开（降噪强度按实测底噪自动定）；`cleanup: false` 只做响度。处理结果缓存在项目的 `.cache/` |
| bgm[] | 配乐片段：`src, t0, t1, src_in, db, fade_in, fade_out, duck`（duck 表示有人声时自动压低，默认开）；配乐不够长会自动循环。只写一首时按段落自动跳段；手写好几段时照写的铺 |
| tracks[] | 段落换曲用的几首曲子：`[{"src": "bgm/慢.mp3", "mood": "calm"}, {"src": "bgm/快.mp3", "mood": "dense"}]`，按 sections 的情绪分配，见下面「段落换曲」。写了 tracks 就不用写 bgm。某首写 `"loop": true`（或 `{"bars": 4}`）就挑它能量平稳的整数小节按重拍首尾相接反复放（节奏段无缝循环），用在大段画中画讲解 |
| bed | 开头高一档、正文压低：`{"open": 13, "lift": 5, "fade": 0.9}`，开头 13 秒配乐比正文高 5 dB，0.9 秒过渡。默认开，`false` 关掉 |
| open_boost | 开场提气曲：`{"src": "bgm/提气.mp3", "len": 7}`，开头 7 秒放这首，0.34 秒淡出接主曲（主曲 0.33 秒淡入）；不写 src 用主曲里最有劲的一段 |
| stops[] | 重音收住再硬切：`[{"t": 5.15, "gap": 1.0}]`，t 是数字放大那一帧，那一帧一声重音鼓，鼓尾配乐跟着收，空 gap 秒后硬切进下一段配乐。全片一两次，后面要紧跟一个大变化 |
| sfx_density | 音效密度：`sparse` 稀疏（每分钟最多 12 个）/ `dense` 密集（每分钟最多 30 个）。不写按风格和强度档：克制档 8 个、网感档 14 个、综艺感 25 个 |
| sfx[] | 手写的音效文件：`src, t（起始秒）, db`。一般用不到，按画面和口播挂声音用 `sound` 和 `sounds` |
| auto_sfx | 默认 `true`；`false` 时不自动配音效 |
| sfx_engine | `earshot`（默认，装了 earshot 时）/ `mixkit` 只用 Mixkit 音效 |

顶层 `sounds`：按口播的词或时间点挂声音，`[{"word": "清空", "sound": "trash"}]`；broll、overlays、titles、layout、transitions 上的 `sound`：这个画面出现时响什么声音。sound 可以写声音清单里的名字、组合名（`swing` 挥动落定、`shuttle` 穿梭、`rising_ui` 升调串，升调串写 `step` 0、1、2… 一个比一个高），也可以直接写剪映音效原名（「综艺叮」「唰」「挥动声」），按手法库的对照表换算。声音清单和用法见 `audio.md`「音效怎么配」。

#### 段落换曲

配乐按 sections 的段落排：每段按 `mood` 挑 tracks 里情绪对上的曲子（曲子没写 mood 按速度判，108 BPM 以上算快），和上一段同一首就接着放；换到没放过的曲子从它第一个有劲的重拍起播，再放到用过的曲子从上次停的地方接着，剩下的不够这一段用就从头一个有劲的重拍再起。3 分钟以上的片子防听感疲劳：同一首连着放满 75 秒，到下一个段落就换一首；一首快放完、又没有别的曲子情绪对得上时，同一首从头再起。只给一首曲子时，在同一首里按段落跳到能量高的另一段。

两段配乐怎么接，段落写 `seam`，不写按情绪变化自动选：

| seam | 怎么接 | 自动用在 |
|---|---|---|
| `xfade` | 交叉淡化 0.4 秒，后一首比画面早 0.3 秒进来（声音先入） | 情绪一样的两段 |
| `whoosh` | 嗖一声盖住接缝：嗖起来时前一首 0.2 秒淡出，后一首在嗖最响处起播，听着是有意换挡 | 舒缓切到快、欢快、提气 |
| `gap` | 前一首先停，留白 `gap` 秒（默认 0.8）再进下一段 | 快切到舒缓 |
| `cut` | 画面切的那一帧直接换，情绪反转用；段落写 `"shout": true` 再叠一声欢呼 | 不自动用 |
