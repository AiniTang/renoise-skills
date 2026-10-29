# 手法库

本文件由 `scripts/library.py docs` 从手法登记表生成，不要手改。
手法库共 212 条手法（17 类），来自 26 个抖音口播剪辑教程和 10 个剪映草稿；已全部实现（120 条按内容搭配、7 组全片一次选定、93 条写在 timeline 字段里，有几条是同一手法的不同写法）。

## 怎么用

在 timeline.json 里写 `beats`：每段话标一个内容类型、给出要上屏的字，渲染时代码自动挑手法和变体、对齐口播时刻。
想指定手法写 `"use": "<id>"`，指定变体写 `"variant"`。挑的结果用 `python scripts/library.py arrange timeline.json` 查看。

| 内容类型 beat | 意思 |
|---|---|
| `hook` | 开场钩子 |
| `topic` | 点题 |
| `chapter` | 章节切换 |
| `list` | 并列列举 |
| `number` | 数字数据 |
| `compare` | 对比 |
| `steps` | 步骤流程 |
| `quote` | 金句结论 |
| `concept` | 新概念 |
| `evidence` | 事实证据 |
| `emphasis` | 重点词 |
| `negative` | 负面警告 |
| `question` | 提问悬念 |
| `emotion` | 情绪吐槽 |
| `demo` | 操作演示 |
| `story` | 讲故事 |
| `transition_talk` | 过渡句 |
| `cta` | 结尾互动 |

## 已实现：按内容搭配的手法

### `flank_pair` 人两侧对称短语

人站中间，一句话拆成两段分放左右空位，先后出现，左白右红或左右对比，像海报两栏。

- 适合：`compare`、`quote`、`list`；风格：premium、web、variety；轻重：2
- 变体：`white_red` 左白右红（premium、web）；`stagger` 错落双字（premium）；`pop` 双词弹出（variety、web）
- 示例：`{"beat": "compare", "left": "会剪", "right": "会想", "items_en": ["EDIT", "THINK"]}`

### `line_yield_shift` 前句让位后句重点

一句话拆成两段：第二段要出现时，第一段缩小、变淡并挪开让位，第二段的重点更大、换色进场，主次一下分清。

- 适合：`topic`、`hook`、`question`、`compare`、`emphasis`；风格：premium、web；轻重：2
- 变体：`push_up` 上移让位（premium、web）；`diagonal` 对角错位（premium、web）；`gray_down` 变灰下沉（premium）；`squeeze` 缩小挤入（web）
- 示例：`{"beat": "topic", "text": "你剪的口播没人看", "text2": "问题出在字幕", "hl": ["字幕"]}`

### `staged_chunk_reveal` 说一块出一块

一句话按口播节奏一块一块出现在人旁边，越重要的块越大，先出的不消失，整句说完一起消失。

- 适合：`quote`、`concept`、`steps`；风格：premium、web；轻重：2
- 示例：`{"beat": "quote", "chunks": [{"text": "好的剪辑", "w": 1}, {"text": "不是加特效", "w": 2}, {"text": "是做减法", "w": 3}]}`

### `list_accumulate` 并列项逐条出现

并列的几点按口播节奏一条一条出来，先出的不消失；可以在最后收拢让位给结论，或做成编号网格、侧边速记清单。

- 适合：`list`、`steps`、`question`；风格：premium、web、variety；轻重：2
- 变体：`conclude` 列举后收拢出结论（premium、web、variety）；`bullets` 侧边要点配英文（premium、web）；`grid` 编号淡成底纹网格（premium、web）；`one` 一屏一个三连击（web、variety）
- 示例：`{"beat": "list", "items": ["没存档", "乱改代码", "不做测试"], "items_en": ["NO BACKUP", "RANDOM EDITS", "NO TESTS"], "conclude": "怎么避开？"}`

### `label_chips_sequence` 标签卡逐个点出

口播连续说出几个并列短语时，人物旁边按说话节奏一张一张弹出小标签卡，切镜时一起消失。

- 适合：`list`、`concept`、`topic`、`hook`、`evidence`；风格：premium、web、variety；轻重：2
- 变体：`bilingual` 胸前中英标签卡（premium、web）；`red_bar` 红条擦入标签（premium、web）；`gold` 暗红金字错落（premium）；`capsule` 彩色胶囊（web、variety）；`stack3` 浅底竖排要点（premium、web）
- 示例：`{"beat": "list", "items": ["选题", "脚本", "剪辑"], "items_en": ["TOPIC", "SCRIPT", "EDIT"]}`

### `cn_en_tracked` 中文大字配宽字距英文

中文关键词大字下面或中间压一行细小的全大写英文，字距拉得很开，颜色比中文淡，是高级感版式的主要来源之一。

- 适合：`concept`、`topic`；风格：premium；轻重：2
- 示例：`{"beat": "concept", "text": "上下文", "en": "Context window"}`

### `giant_number_hook` 巨数字点题

说到「这 4 个方法」时，画面一侧立起一个占画面高约 70% 的灰白数字，部分出血到画外，旁边星光闪烁，人在另一侧比同样的手势。

- 适合：`hook`、`topic`、`list`、`number`；风格：premium、web；轻重：3
- 示例：`{"beat": "hook", "number": 4, "text": "4 个方法"}`

### `number_reveal` 大数字浮现

没有卡框，一个窄体大数字直接浮在压暗画面上，0.2~0.3 秒从模糊变清晰或从 0 滚到结果，上方一行小号标题，下方灰色说明或一行绿色等宽日志作为证据。

- 适合：`number`、`evidence`；风格：premium、web；轻重：3
- 变体：`glow` 柔光模糊渐显（premium、web）；`roll` 数字滚动加日志（premium、web）
- 示例：`{"beat": "number", "value": "$1,000,000", "lead": "Annual revenue", "text": "一个人做到的年收入"}`

### `text_typewriter` 打字机光标逐字出

文字一个字一个字打出来，末尾跟着一个闪烁光标，像有人正在输入。

- 适合：`question`、`quote`、`topic`、`hook`；风格：premium、web；轻重：2
- 示例：`{"beat": "question", "text": "为什么你的视频没人看完？", "hl": ["没人看完"]}`

### `kw_color_block` 色块衬底关键词

关键词背后刷出一块纯色矩形，像荧光笔整块涂过，字和底形成强反差。

- 适合：`emphasis`、`negative`、`concept`、`quote`；风格：premium、web；轻重：2
- 变体：`solid` 实心反白块（premium、web）；`offset` 错位刷块（web）；`skew` 斜切渐隐条（premium、web）；`grow` 方块拉长成条（premium、web）
- 示例：`{"beat": "emphasis", "lead": "真正拉开差距的是", "text": "信息密度", "hl": ["信息密度"], "en": "information density"}`

### `info_stat_card` 深色描边数据卡

压暗的素材上浮出一张深色圆角卡，细描边（黄绿发光或暗金）带角饰，卡内是主体名标题 + 英文小字 + 一个关键数字或环形图；第二个数字或第二行跟着口播再出现。

- 适合：`evidence`、`number`、`compare`；风格：premium；轻重：2
- 变体：`ornate` 暗金角花卡（premium）；`lime` 黄绿发光卡（web）；`rows` 分行跟读卡（premium）
- 示例：`{"beat": "evidence", "text": "SpaceX 发射记录", "en": "Launch record", "value": "580", "label": "完成发射次数", "value2": "534", "label2": "成功着陆次数"}`

### `share_ring_pie` 占比环形扇形生长

一个圆环或扇形从 12 点方向顺时针长到对应比例，中心或旁边写出百分比，直观表示占比、份额、被谁拿走多少。

- 适合：`number`、`compare`、`evidence`；风格：premium、web；轻重：2
- 变体：`donut` 细圆环填充（premium、web）；`pie` 饼图加标签（premium、web）；`slice` 圆形图上扇形长出（premium、web）
- 示例：`{"beat": "number", "pct": 60, "lead": "新手里", "text": "第一周就放弃了"}`

### `chapter_fog_numeral` 白雾镂空大序号

讲第 N 点时画面下半部升起一片 70% 白雾（上缘羽化），雾里镂空一个巨大的粗斜体数字，数字笔画里透出后面的画面；全屏版是整屏白雾只留数字窗口，人脸从数字笔画里露出来。

- 适合：`chapter`；风格：premium；轻重：3
- 变体：`panel` 底部雾面板（premium）；`window` 整屏数字窗（premium）
- 示例：`{"beat": "chapter", "number": "02", "text": "上下文管理", "en": "Context", "items": ["一事一会话", "留两成交接", "先读再动手"]}`

### `chapter_title_page` 虚化底章节标题页

口播画面整体虚化或换成渐变底，压一组章节标题（编号、标题、英文副标），停 1~3 秒再进入下一节。

- 适合：`chapter`；风格：premium、web、variety；轻重：3
- 变体：`hand` 毛笔手写体（premium、web）；`preview` 衬线标题加预告窗（premium、web）；`swap` 总标题原位换分标题（web、variety）
- 示例：`{"beat": "chapter", "number": "02", "text": "做减法", "en": "Less is more", "sub": "给字幕加戏", "main": "剪辑三板斧"}`

### `side` 人一侧不对称大字

（已有版式，见 timeline.md 的 titles）

- 适合：`concept`、`topic`、`emphasis`、`quote`、`negative`；风格：premium；轻重：2
- 示例：`{"beat": "concept", "lead": "这一步叫", "text": "版本管理", "hl": ["版本"], "en": "Version control"}`

### `quote` 金句引号

（已有版式，见 timeline.md 的 titles）

- 适合：`quote`、`concept`；风格：premium；轻重：2
- 示例：`{"beat": "quote", "text": "不要依赖 AI 的记忆\\N来撤回", "hl": ["记忆"]}`

### `chapter` 章节页

（已有版式，见 timeline.md 的 titles）

- 适合：`chapter`；风格：premium、web；轻重：3
- 示例：`{"beat": "chapter", "number": "02", "text": "上下文管理", "en": "Context", "sub": "别让 AI 失忆"}`

### `stack` 编号卡逐条累加

（已有版式，见 timeline.md 的 titles）

- 适合：`steps`、`list`；风格：premium、web；轻重：2
- 示例：`{"beat": "steps", "text": "三步走", "items": ["git init 初始化", "git commit 存档", "git revert 回退"]}`

### `count` 数字滚动

（已有版式，见 timeline.md 的 titles）

- 适合：`number`；风格：premium、web、variety；轻重：2
- 示例：`{"beat": "number", "from": 100, "to": 20, "suffix": "%", "text": "上下文只剩两成"}`

### `behind_text` 人压字

大字放在人物身后，头发和肩膀挡住字的一部分，形成背景、字、人三层的空间感。

- 适合：`topic`、`hook`、`emphasis`；风格：premium、web；轻重：3
- 变体：`brand_head` 头部高度点题大字（premium、web）；`top_keyword` 头顶要点关键词（web）；`hollow_sandwich` 实心镂空夹人（premium、web）
- 示例：`{"beat": "topic", "text": "剪辑", "en": "Cut it right"}`

### `word` 整屏单字页

（已有版式，见 timeline.md 的 titles）

- 适合：`negative`、`emotion`、`emphasis`；风格：premium、web、variety；轻重：3
- 变体：`blur` 模糊渐显（premium）；`flash` 闪现（web、variety）
- 示例：`{"beat": "negative", "text": "失忆", "en": "Amnesia"}`

### `split` 左右分列

（已有版式，见 timeline.md 的 titles）

- 适合：`compare`；风格：premium；轻重：2
- 示例：`{"beat": "compare", "left": "以前", "right": "现在", "items_en": ["BEFORE", "NOW"]}`

### `plain` 居中大字

（已有版式，见 timeline.md 的 titles）

- 适合：`emotion`、`emphasis`、`topic`、`quote`；风格：variety；轻重：2
- 示例：`{"beat": "emotion", "text": "这谁顶得住", "hl": ["顶不住"]}`

### `kw_slam_stamp` 巨字砸屏盖章

红色毛笔或书法大字从超大尺寸一下砸进画面再缩回，斜着盖在画面上，底下的东西被虚化，冲击感很强。

- 适合：`negative`、`emotion`、`hook`、`emphasis`；风格：web、variety；轻重：3
- 变体：`stamp` 痛点词盖章（web、variety）；`char` 单个巨字（web、variety）
- 示例：`{"beat": "negative", "text": "别这样做"}`

### `kw_speedline_burst` 速度线爆发重点字

画面四周突然炸出一圈抖动的漫画集中线，中间一行巨大的重点字，像敲黑板。

- 适合：`emphasis`、`hook`、`quote`；风格：web、variety；轻重：3
- 示例：`{"beat": "emphasis", "text": "信息密度"}`

### `kw_crash_knockout` 后词撞飞前词

新词从一侧滑进来，刚碰到旧词就把旧词撞出画面，像被一拳打飞。

- 适合：`compare`、`negative`、`emotion`；风格：web、variety；轻重：2
- 示例：`{"beat": "compare", "left": "加功能", "right": "做减法"}`

### `kw_split_insert` 主词裂开插入副句

一个主词从中间被切开，两半向两边分开，缝里插进一行追问或补充，或者干脆把「裂开」演出来。

- 适合：`question`、`emphasis`、`emotion`、`negative`、`concept`；风格：premium、web；轻重：2
- 变体：`gap` 巨字横缝嵌字（premium、web）；`shift` 三层错位（web）
- 示例：`{"beat": "question", "text": "上下文", "sub": "到底满没满？"}`

### `kw_word_replace` 引导词换成重点词

先出现一个引导词，接着在同一位置被一个更大、换色的重点词替换掉，替换动作本身就是看点。

- 适合：`transition_talk`、`emphasis`、`question`、`compare`；风格：web；轻重：2
- 变体：`fold` 折叠弹入（web）；`ghost` 引导词放大成底纹（web）；`vblur` 竖向模糊换字（web）
- 示例：`{"beat": "transition_talk", "lead": "其实只要", "text": "一个命令"}`

### `text_finish_fx` 花字质感渲染

同一个大字换一种质感：横纹拖影立体、网点投影、霓虹空心、渐变填充或故障网点填充，让重点字更有设计感。

- 适合：`emphasis`、`emotion`、`hook`、`transition_talk`；风格：web；轻重：2
- 变体：`striped` 横纹拖影立体（web）；`halftone` 网点投影（web）；`neon` 霓虹空心（web）；`gradient` 渐变填充（web）；`glitch` 故障错位（web）
- 示例：`{"beat": "emphasis", "text": "上下文"}`

### `paper_patch_text` 纸片垫底字

关键词写在一片撕边纸、牛皮纸胶带或一块块彩纸上，像剪下来贴上去的手作拼贴。

- 适合：`topic`、`concept`、`emotion`；风格：web、variety；轻重：2
- 变体：`kraft` 牛皮纸胶带标题（web、variety）；`torn` 撕纸片（web、variety）；`chips` 每字彩纸（web、variety）
- 示例：`{"beat": "topic", "text": "Claude Code 七个命令"}`

### `concept_quote_marks` 引号括号框概念词

术语第一次出现时，外面加上比字还大的引号或括号，像在给概念下定义。

- 适合：`concept`、`quote`；风格：web；轻重：2
- 变体：`bracket` 方括号（web）；`curly` 弯引号（web）
- 示例：`{"beat": "concept", "text": "上下文", "en": "context"}`

### `handwritten_note` 红色手写数字批注

截图或画面上直接写一个红色手写数字，像拿笔圈注出数据结论。

- 适合：`evidence`、`number`；风格：premium、web；轻重：2
- 示例：`{"beat": "evidence", "value": "80%"}`

### `icon_keyword_list` 图标配并列词

说到几个具体名词时，每个词配一个图标或小图依次弹进画面，让并列项变得看得见。

- 适合：`list`、`steps`、`concept`；风格：web、variety；轻重：2
- 变体：`unfold` 关键词展开配图标（web、variety）；`row` 图标横排随读高亮（web、variety）；`dashbox` 虚线框逐个累加（web、variety）
- 示例：`{"beat": "list", "items": ["看额度", "看日志", "算钱"], "icons": ["Battery", "Memo", "Money bag"]}`

### `kw_question_mark` 问号点缀

问句出现时，旁边立起一个大问号或蹦出几个手绘问号，把「疑问」画出来。

- 适合：`question`、`hook`；风格：web、variety；轻重：2
- 变体：`stand` 半透明大问号站起（web、variety）；`hop` 手绘问号连蹦（web、variety）
- 示例：`{"beat": "question", "text": "到底满没满？"}`

### `speech_bubble_text` 对话气泡文字

文字装进漫画对话气泡里，模拟提问或列出一类问题的几种表现。

- 适合：`question`、`hook`、`list`、`negative`；风格：web；轻重：2
- 变体：`comic` 头顶漫画气泡（web）；`tags` 黄色气泡散布（web）
- 示例：`{"beat": "question", "text": "它是不是又忘了？", "items": ["忘了前面", "答非所问", "越改越乱"]}`

### `meme_reaction_caption` 表情包倾斜吐槽字

黑底中央一张反应表情图，下边骑缝压一行倾斜的白色立体大字，像综艺吐槽。

- 适合：`emotion`、`question`、`negative`；风格：web、variety；轻重：3
- 示例：`{"beat": "emotion", "text": "这谁顶得住", "emoji": "Face with tears of joy"}`

### `anim_shout_wave` 呐喊声波残影

大字带着三四层放大的残影像声波一样冲出来，再收回成一个字，有喊出来的力量感。

- 适合：`emotion`、`question`、`emphasis`、`hook`；风格：web、premium；轻重：3
- 示例：`{"beat": "emphasis", "text": "先规划", "sub": "再动手"}`

### `text_cross_slide` 左右滑入交错

引导词从一侧滑进来，重点词从另一侧滑进来，两行错开成对角或交叉压在一起。

- 适合：`emphasis`、`topic`、`compare`、`list`；风格：web；轻重：2
- 变体：`diagonal` 对角错位（web）；`cross` 横穿压中（web）
- 示例：`{"beat": "compare", "lead": "不是写得慢", "text": "是没想清楚"}`

### `text_wipe_reveal` 擦除显字

字不是淡入，而是被一道看不见的刷子或光点刷出来：从上往下、从中间往两边，或被发光点刻出来。

- 适合：`topic`、`concept`、`quote`、`emphasis`；风格：premium、web；轻重：2
- 变体：`vwipe` 竖向擦除（premium、web）；`center` 中间左右展开（premium、web）；`laser` 激光雕刻（web）
- 示例：`{"beat": "topic", "text": "上下文窗口"}`

### `anim_per_char` 逐字入场

一行标题一个字一个字出现：要么依次从小放大弹出，要么每个字从不同高度随机升起。

- 适合：`topic`、`story`、`chapter`；风格：premium、web；轻重：2
- 变体：`zoom` 逐字缩放（web）；`rise` 随机上升（premium、web）
- 示例：`{"beat": "topic", "text": "找回会话", "hl": ["会话"]}`

### `cursor_click` 鼠标指针点击

关键词旁出现一个白色鼠标箭头，点一下带一圈波纹，关键词同时弹跳或变色。

- 适合：`cta`、`demo`、`emphasis`；风格：web；轻重：2
- 示例：`{"beat": "cta", "text": "点这里"}`

### `radial_burst_bg` 放射爆炸底

说到冲突或强动作词时，人物身后或整屏瞬间变成红粉色放射锯齿爆炸图，0.3 秒到 2 秒后恢复。

- 适合：`emotion`、`negative`、`emphasis`；风格：web、variety；轻重：3
- 变体：`behind` 身后爆闪（web、variety）；`cartoon` 卡通爆炸炸成单字页（web、variety）
- 示例：`{"beat": "emotion", "text": "炸了"}`

### `text_persist_bg_swap` 字不动底在换

一组大字排好后位置完全不动，下面的底连续换（人物、黑场、动态模糊、白底），换完字再慢慢变暗。

- 适合：`quote`、`transition_talk`、`emphasis`；风格：premium、web；轻重：2
- 示例：`{"beat": "quote", "text": "慢就是快"}`

### `giant_word_page` 巨字压画面

一句话的结论只剩一两个字时，把它做成压在画面上的巨字：金属浮雕、半透明出血红字，或拼贴纸底上的毛笔字。

- 适合：`quote`、`emotion`、`concept`；风格：premium、web；轻重：3
- 变体：`metal` 金属浮雕单字（premium、web）；`red_bleed` 半透明红字出血（premium、web）；`collage` 拼贴底毛笔字（premium）
- 示例：`{"beat": "quote", "text": "稳", "en": "Steady"}`

### `ghost_bg_word` 巨字底纹装饰

主标题背后垫一层不抢戏的巨大底纹字：空心英文、同色系浮雕中文、贴边竖排英文或两侧做旧灰字，让版面像海报。

- 适合：`topic`、`question`、`quote`；风格：premium、web；轻重：2
- 变体：`hollow` 空心描边英文（premium、web）；`edge` 贴边竖排英文（premium、web）；`emboss` 同色系浮雕中文（premium、web）；`grunge` 两侧做旧灰字（premium、web）
- 示例：`{"beat": "topic", "text": "先想清楚", "lead": "动手之前", "en": "Think", "ghost": "想"}`

### `boxed_char_title` 方框单字标题

标题每个字单独套一个白色细线方框，字是带立体阴影的白色粗宋，有仪式感。

- 适合：`topic`、`quote`；风格：premium；轻重：2
- 示例：`{"beat": "topic", "text": "上下文", "tag": "Context", "sub": "AI 一次能记住的全部内容"}`

### `mix_size_line` 一行大小字混排

一行字里只有关键词放大两三倍，其余小字同一底边对齐；也可以先整句出现，再让重点词放大变金、其余缩小。

- 适合：`emphasis`、`number`、`quote`；风格：premium、web；轻重：1
- 变体：`static` 静态混排（premium、web）；`focus` 出现后突出（premium、web）
- 示例：`{"beat": "emphasis", "text": "3秒 决定观众走不走", "key": "3秒"}`

### `corner_chars_frame` 四角分字围人

一个四字词拆开放在人物四角，或两个字左右夹住头部，把一句话变成包住人的画框。

- 适合：`cta`、`topic`、`hook`、`quote`；风格：web；轻重：2
- 变体：`four` 四字四角（web）；`shrink` 画面缩到中间（web）；`flank` 两字夹头（web）
- 示例：`{"beat": "cta", "text": "一键三连"}`

### `circle_pip_text` 圆形头像配环绕字

人物缩成一个圆形头像，文字顺着圆弧弯成徽章，或几个并列词贴着圆周排开，或大字上下夹住圆头像。

- 适合：`hook`、`topic`、`list`、`cta`；风格：web；轻重：3
- 变体：`arc` 弧形徽章字（web）；`tangent` 并列词贴圆周（web）；`sandwich` 大字上下夹头像（web）
- 示例：`{"beat": "hook", "text": "剪辑技巧", "text2": "新手必看", "hl": ["技巧"], "items": ["快", "准", "稳"]}`

### `split_pip_word_swap` 分屏圆头像巨字轮换

上半屏是素材，下半屏黑底，交界处一个白边圆形头像，下半屏两个超大字一词一换，像在念排比。

- 适合：`list`、`quote`；风格：web、premium；轻重：3
- 示例：`{"beat": "list", "items": ["看", "想", "做"]}`

### `typewriter_panel` 打字机长文面板

一个面板里逐字打出一整段原文，上一句一直保留、逐行累加，观众可以对照着读完。

- 适合：`evidence`、`story`、`steps`、`quote`；风格：web、premium；轻重：2
- 变体：`accumulate` 面板逐行累加（web、premium）；`top_card` 顶部长文卡（web）
- 示例：`{"beat": "evidence", "lines": ["第一步：需求写成文档", "第二步：拆成小任务", "第三步：做完一步提交一次", "第四步：跑测试再继续", "第五步：每天收尾写交接", "第六步：卡住就换个会话", "第七步：别一次改太多"]}`

### `chapter_sentence_card_top` 顶部整句章节标题卡

清单类视频每个「第 N 点」开头，把整句标题放在画面上部垫圆角色块，逐字弹出，人缩小放下方、背景虚化。

- 适合：`chapter`；风格：web、variety；轻重：3
- 示例：`{"beat": "chapter", "number": "02", "text": "上下文满了怎么办"}`

### `chapter_vertical_flank` 竖排双列夹主体章节页

全屏主题背景中间立着一个抠出来的主体物，左右两列银色竖排大字一高一低夹住它，各层缓慢浮动。

- 适合：`chapter`；风格：premium；轻重：3
- 示例：`{"beat": "chapter", "number": "03", "text": "先规划再动手", "en": "Plan first"}`

### `montage_flash_open` 开场快闪蒙太奇

开场 1.5~4 秒内一串截图或主题镜头快速闪过，最后落在一张主题大标题上。

- 适合：`hook`、`topic`；风格：web；轻重：3
- 变体：`macro` 卡点接标题（web）；`chaos` 乱闪拼凑（web）
- 示例：`{"beat": "hook", "srcs": ["@shot", "@photo", "@rec", "@rec2"], "text": "剪辑三板斧"}`

### `collage_cards_title` 卡片拼贴预告

一组截图、logo 或成片缩略卡依次飞入，带旋转错落地堆在画面上，配一行大标题，用来预告「N 种方法」或展示战绩背书。

- 适合：`evidence`、`hook`、`topic`、`list`；风格：web、premium；轻重：3
- 变体：`fan` 扇形铺开（web、premium）；`scatter` 散点快闪（web）；`wall` 曲面视频墙（web）；`paper` 纸页战绩拼贴（web、premium）
- 示例：`{"beat": "evidence", "srcs": ["@shot", "@photo", "@rec", "@rec2"], "text": "这期讲 7 个场景", "text2": "每个都能直接用", "big": "七种", "numbers": ["103.6W", "2.4W"]}`

### `opening_text_first` 黑底文字先行开场

开头先不露脸，黑底上一行行打出干货结论或反差需求（关键词变色），文字说完才让人物以圆头像滑入或切进口播。

- 适合：`hook`；风格：web；轻重：3
- 变体：`stack` 逐行累加再露脸（web）；`meme` 逐句替换配表情包（web）；`warning` 警告式内容预告（web）
- 示例：`{"beat": "hook", "lines": ["剪了三个月口播", "播放量还是两位数", "问题不在内容", "在包装"], "hl": ["包装", "两位数"], "title": "警告"}`

### `opening_question_frame` 反问钩子画框问号

开场第一秒人物缩进一个手机比例的圆角白边框，背景换成暗色立体网格空间，四周散落半虚化的红色立体问号，胸前一行手写字「留不住人?」逐字出现。

- 适合：`question`、`hook`；风格：web；轻重：3
- 示例：`{"beat": "question", "text": "留不住人？"}`

### `poster_title_page` 整屏海报标题页

整屏切到一张设计好的海报式标题页，停 1~3 秒交代本期主题或栏目名：电影片名式黑底红字、胶片齿孔做旧纸、石膏像网格、波普网点或杂志封面。

- 适合：`topic`、`hook`、`concept`；风格：premium、web；轻重：3
- 变体：`cinema` 黑底红字片名（premium、web）；`film` 胶片齿孔做旧页（premium、web）；`grid` 编号淡成底纹网格（premium、web）；`popart` 波普网点（web）；`magazine` 杂志封面（premium、web）
- 示例：`{"beat": "topic", "text": "高级感", "en": "Editing Lab", "sub": "口播剪辑", "issue": "第三期", "lines": ["口播剪辑", "第三期：高级感"], "hl": ["高级感"], "badge": "NEW"}`

### `engagement_ask_page` 求赞收藏提醒页

开场钩子说完后插一页 1.5~2.5 秒的求赞或求收藏页：黑底只留人物中间一个羽化椭圆窗口，左右各一个大字，或者三行竖排大字「视频很长 / 干货很多 / 记得收藏」。

- 适合：`cta`、`transition_talk`；风格：premium、web；轻重：3
- 变体：`flank` 两字夹头（premium、web）；`lines` 竖排收藏提醒（premium、web）
- 示例：`{"beat": "cta", "left": "上点", "right": "干货", "left_en": "like", "right_en": "dry goods", "arc": "先赞后看~", "lines": ["视频很长", "干货很多", "记得收藏"]}`

### `chapter_avatar_gesture` 圆头像手势章节卡

进入每一招前插约 1 秒章节卡：上一画面虚化做底，中间一个白边圆形头像，里面是作者比数字手势的画面，头像从画外弹入，下方「第 N 招」白字黑描边，数字换黄色。

- 适合：`chapter`；风格：web；轻重：3
- 示例：`{"beat": "chapter", "number": "2", "text": "上下文满了"}`

### `chapter_cutout_numeral` 抠像剪纸大数字章节页

章节页上手势抠像带白描边站在黑网格底上，旁边一个巨大的剪纸风彩色数字（错位浅色描边、纸纹），身后垫爆炸闪电贴纸；随后数字后退虚化、红色网点底浮现，白色手写粗体章节标题带网点投影压上来。

- 适合：`chapter`；风格：web、variety；轻重：3
- 示例：`{"beat": "chapter", "number": "3", "text": "先规划再动手"}`

### `ending_echo_keyword` 结尾回扣开场大字

最后一句时，开场那个品牌色大字再次出现在头部后方，用水墨晕染方式铺开、60% 不透明，首尾呼应。

- 适合：`cta`、`quote`；风格：premium；轻重：2
- 示例：`{"beat": "cta", "text": "新手崩溃", "color": "#F5D547"}`

### `cta_action_row` 点赞转发评论条

片尾人在中间挥手，下方一行白色粗字「点赞 — 转发 — 评论」三个词依次出现，词之间是薄荷绿短横，左上一个黑色圆角小名片（头像 + 账号名 + 黄点）。

- 适合：`cta`；风格：web、premium；轻重：2
- 示例：`{"beat": "cta", "name": "@口播剪辑课"}`

### `signature_outro` 固定口号收尾

最后一句固定口号（学会了，去练）：画面先缩成圆角卡片或圆形头像露出黑网格底，「学会了」故障闪入，下一拍「去」「练」两个黄色大字分列人物左右。

- 适合：`cta`、`quote`；风格：web；轻重：3
- 示例：`{"beat": "cta", "text": "学会了", "text2": "去练"}`

### `ui_callout_card` 界面截图圈注卡

讲操作时人旁边浮出一张深色圆角的软件界面截图，关键菜单项被白色虚线圆圈住，旁边一个黄色手绘弧形箭头指过去，再加一个黄底黑字小标签解释。

- 适合：`demo`、`steps`；风格：web；轻重：2
- 示例：`{"beat": "demo", "src": "@shot", "mark": [0.3, 0.3], "label": "点这里切模型"}`

### `ui_widget_mock` 仿界面小组件

把信息包装成观众熟悉的界面小部件：一个搜索框里逐字打出关键词，或一张剪映音效列表项小卡随音效弹出。

- 适合：`concept`、`demo`；风格：web；轻重：2
- 变体：`search` 搜索框打字（web）；`sfx` 音效名卡片（web）
- 示例：`{"beat": "concept", "key": "口播剪辑 网感", "title": "去哪找灵感", "items": [{"name": "综艺 叮", "author": "剪映音效", "dur": "00:01"}, {"name": "嗖 转场", "author": "音效库", "dur": "00:02"}]}`

### `flowchart_nodes` 流程节点逐级点亮

讲因果链时画面上几张黑底金边小卡排成流程，用金色双箭头连接，讲到哪一张就变成浅黄高亮、字变深色，其余保持黑底；口播在后面压暗，右下圆形头像。

- 适合：`steps`、`concept`；风格：premium；轻重：2
- 示例：`{"beat": "steps", "items": ["写需求", "拆任务", "跑测试", "提交"], "title": "一次改动的流程"}`

### `timeline_axis` 时间轴区间示意

画一条横轴，用刻度、标记点和游标解释「从 A 到 B」、事件先后或年份回溯：关键帧两点、音效切点、年份刻度尺、波形切点。

- 适合：`story`、`steps`、`concept`；风格：premium、web；轻重：2
- 变体：`two_point` 两点加游标（premium、web）；`events` 事件标点逐个点亮（premium、web）；`year` 年份刻度尺滚动（premium、web）；`wave` 波形切点卡（premium、web）
- 示例：`{"beat": "story", "items": ["开头", "结尾"], "title": "从第一帧到最后一帧", "target": 2025}`

### `step_mosaic_wall` 暗色拼格步骤墙

整屏一面深色拼贴墙：6~8 个大小不一的暗色格子，格子里是卡其和白色大字（STEP 01 表达先行、02 提取文字…），像杂志内页，整体缓慢推近。

- 适合：`steps`；风格：premium；轻重：3
- 示例：`{"beat": "steps", "items": ["表达先行", "提取文字", "找素材", "粗剪", "包装", "复盘"]}`

### `resource_list_page` 资源清单页

把要推荐的字体、BGM、工具做成一页清单：整屏牛皮纸上竖排金黄色斜体条目，或左侧一张半透明白色规格海报、右侧大字跟着口播逐个点名。

- 适合：`list`、`evidence`；风格：web、premium；轻重：2
- 变体：`paper` 整屏牛皮纸清单（web、premium）；`poster` 侧栏规格海报（web、premium）
- 示例：`{"beat": "list", "items": ["思源黑体", "得意黑", "霞鹜文楷", "站酷快乐体", "抖音美好体"], "title": "免费可商用字体", "category": "中文无衬线", "note_line": "均可免费商用"}`

### `type_card_row` 竖卡一排类型展示

分类讲 3~5 种类型时，一排竖版卡片从左到右一张张出现，标签上下交错写类型名和拼音；需要细讲某一种时放大成单张示意页。

- 适合：`list`、`compare`、`concept`；风格：premium、web；轻重：3
- 变体：`screenshot` 截图竖卡排开（premium、web）；`wireframe` 构图线框卡（premium、web）
- 示例：`{"beat": "list", "srcs": ["@shot", "@photo", "@rec", "@rec2"], "items": ["截图", "照片", "录屏", "素材"], "pinyin": ["jie tu", "zhao pian", "lu ping", "su cai"], "kinds": ["topbottom", "corners", "center", "leftright", "diagonal"], "focus": 2, "giant": "居中", "note_line": "人在中间，字压上下"}`

### `photo_card_stack` 并列图片卡错落

说到三个并列项时，三张带图的圆角卡片依次滑入、上下错落排列，每张卡上压白色描边粗字。

- 适合：`list`；风格：web；轻重：2
- 变体：`tab` 彩色折角阶梯卡（web）；`tilted` 倾斜白边照片卡（web）
- 示例：`{"beat": "list", "srcs": ["@shot", "@photo", "@rec"], "items": ["看截图", "拍照片", "录屏幕"]}`

### `comment_bubbles` 评论气泡堆

人物周围浮出一堆白色圆角评论卡或聊天气泡（卡通头像 + 网友问题或差评 + 点赞数），制造「大家都在问、都这么说」的感觉。

- 适合：`question`、`negative`、`evidence`、`emotion`；风格：web；轻重：2
- 变体：`behind` 身后评论墙（web）；`pileup` 差评气泡堆满（web）
- 示例：`{"beat": "question", "items": [{"text": "剪辑软件用哪个？", "likes": "1.2w"}, {"text": "字幕怎么做得这么好看", "likes": "3896"}, {"text": "音效从哪找的？", "likes": "826"}, {"text": "求出教程！", "likes": "2.4w"}]}`

### `fan_window_cards` 头后三窗口扇形展开

人物头顶后方先出一张竖版圆角展示窗，随后左右两张从它后面向两侧滑出、略小略靠后，形成扇形；人物抠出压在卡片前，头发挡住卡片底边。

- 适合：`list`、`demo`、`evidence`；风格：premium；轻重：2
- 示例：`{"beat": "demo", "srcs": ["@rec", "@shot", "@photo"]}`

### `news_ticker_box` 黑底发光播报框

画面中部一个黑色播报框，四边白色柔光描边像发光屏幕，框里是反色成黑底白字的新闻正文从下往上缓慢滚动，标题里的高亮词用白底黑字反白块；人物和主体在框下层。

- 适合：`evidence`；风格：premium；轻重：2
- 示例：`{"beat": "evidence", "title": "剪辑软件全面接入 AI 自动包装", "hl": ["AI 自动包装"], "src": "@shot"}`

### `quote_typewriter_dim` 压暗底引文逐行打出

引用名人原话或书籍原文时，底图整体压暗，上方一行一行打出白色引文（带中文引号），约 1.5 秒一行，头像移到左下角。

- 适合：`quote`、`evidence`；风格：premium；轻重：2
- 示例：`{"beat": "quote", "lines": ["好的剪辑", "是让观众忘了剪辑的存在"], "by": "沃尔特·默奇"}`

### `paper_label_column` 纸页左标签右内容卡

牛皮纸底，左侧一列红色粗体标签（补充背景、解释潜台词、强化情绪）各带一行小英文，右侧一张大圆角卡放对应例子；换标签时版式不动只换内容。

- 适合：`list`、`concept`；风格：premium；轻重：2
- 示例：`{"beat": "list", "items": [{"label": "补充背景", "en": "Background", "src": "@shot"}, {"label": "解释潜台词", "en": "Subtext", "src": "@photo"}, {"label": "强化情绪", "en": "Emotion", "src": "@rec"}]}`

### `person_info_card` 人物信息卡

提到某个人时下方弹出一张人物信息卡，让观众马上知道是谁：仿抖音主页的博主信息条，或开场自我介绍的金色名字名片。

- 适合：`story`、`hook`、`concept`、`evidence`；风格：web、variety；轻重：1
- 变体：`profile` 博主主页信息条（web、variety）；`nameplate` 自我介绍名片（web、variety）
- 示例：`{"beat": "story", "name": "口播剪辑研究所", "fans": "粉丝 128.6w", "titles": ["十年剪辑师", "带过 300 个口播账号"]}`

### `product_cards_dim` 压暗叠商品卡

人物画面整体压暗并覆盖一层斜条纹，像被推到后台；三张白色圆角商品卡（左边产品图，右边型号 + 价格，蓝色按钮）从下往上依次弹出堆叠。

- 适合：`compare`、`number`、`list`；风格：web；轻重：2
- 示例：`{"beat": "compare", "items": [{"name": "基础版 · 月付", "price": "¥29", "icon": "Package"}, {"name": "专业版 · 月付", "price": "¥69", "icon": "Gem stone"}, {"name": "团队版 · 年付", "price": "¥599", "icon": "Trophy"}]}`

### `doc_translation_bar` 外文原文配中文翻译条

英文专利或外媒放大到正文，相关的一句被反白划出，约 1 秒后下方弹出一条黑色圆角长条写中文意译，关键词黄色，四周灰色暗角。

- 适合：`evidence`、`concept`；风格：premium；轻重：2
- 示例：`{"beat": "evidence", "src": "@shot", "line": [0.04, 0.42, 0.92, 0.08], "text": "这里写的是：上下文满了会自动压缩", "hl": ["自动压缩"]}`

### `detail_split_windows` 同画面拆窗看细节

同一个口播画面被拆成上下两个错开的窗口，上窗露脸，下窗只露双手或手里的东西，把视线分到表情和手势。

- 适合：`demo`、`emphasis`；风格：web；轻重：2
- 示例：`{"beat": "demo"}`

### `example_window` 素材窗口嵌入

别人的视频、案例或成品缩成画面中间的一个窗口，带细描边、外发光或投影，窗口外是深色动态底或虚化底，和自己的口播区分开。

- 适合：`demo`、`evidence`、`compare`；风格：premium、web；轻重：2
- 变体：`thin` 细蓝框示例窗（premium、web）；`glow` 发光框加分段标签（premium、web）；`shadow` 投影卡加金属标题（premium、web）
- 示例：`{"beat": "demo", "src": "@rec", "label": "第1段", "sub": "开头三秒抓人", "title": "案例拆解"}`

### `keyword_band_stack` 并列词素材条堆叠

说到两三个并列词时，每个词配一条横向素材条依次进画面、上下排开，人物缩成小窗留在画面里。

- 适合：`list`、`compare`；风格：web；轻重：3
- 变体：`push` 顶部压入下推（web）；`drop` 卡片下落堆叠（web）；`gray` 黑白转彩跟读（web）
- 示例：`{"beat": "list", "items": ["截图", "照片", "录屏"], "srcs": ["@shot", "@photo", "@rec"]}`

### `matte_band_stack` 抠像人站素材带

画面横向分成两三段素材，人物抠像带白描边站在中间段，头部略溢出到上段，大标题压在人头附近。

- 适合：`topic`、`evidence`；风格：web；轻重：3
- 变体：`three` 三段式（web）；`tech` 科技上下两段（web）
- 示例：`{"beat": "topic", "srcs": ["@photo", "@rec", "@shot"], "text": "信息差", "tag": "效率工具"}`

### `paper_layer_collage` 纸张分层拼贴

抠像人物放在揉皱白纸底上，身后铺扇形演示素材，前景再叠撕边色纸和贴纸，层层叠出手作拼贴的空间感。

- 适合：`demo`、`concept`、`story`、`chapter`；风格：web；轻重：3
- 示例：`{"beat": "story", "srcs": ["@shot", "@photo", "@rec"], "text": "手作拼贴感"}`

### `topic_figure_dim_cutout` 话题人物压暗剪影

讲到某个具体人物时，把他的照片抠出来变成近乎黑白的压暗胸像，从下方升到画面下半部，给上方文字留空间。

- 适合：`story`、`concept`、`hook`；风格：premium；轻重：2
- 示例：`{"beat": "story", "figure": null, "text": "他是谁？", "sub": "一个改变剪辑行业的人"}`

### `mood_image_word` 情绪图配一个字

插入一两秒和情绪意象直接对应的画面（观众席、灯泡、胶片放映机），上面只放一个关键词大字。

- 适合：`emotion`、`concept`、`emphasis`；风格：premium；轻重：2
- 示例：`{"beat": "emotion", "mood": "@photo", "word": "静"}`

### `layer_parallax_drift` 多层视差缓动

静态页面拆成多层，每层以不同速度和方向缓慢移动或缩放，画面一直活着，换句时还能做出镜头在动的视差。

- 适合：`transition_talk`、`chapter`、`number`；风格：premium；轻重：2
- 变体：`ambient` 多层各自缓动（premium）；`shift` 换句视差位移（premium）
- 示例：`{"beat": "transition_talk", "text": "慢下来", "lines": ["少即是多", "留白有力"]}`

### `grid_2x2_title` 田字格方块字

四字词拆成两行两列的方块大字，旁边可以再竖排一个两字词形成对比。

- 适合：`topic`、`compare`、`quote`；风格：premium；轻重：2
- 示例：`{"beat": "topic", "text": "信息密度", "pair": "取舍"}`

### `perspective_text_3d` 透视立体大字

白色厚重的立体字在人两侧沿透视方向伸向画面深处，像立在地上的大招牌。

- 适合：`topic`、`chapter`；风格：premium；轻重：3
- 示例：`{"beat": "topic", "text": "先想后做"}`

### `staircase_text` 阶梯斜排字

短句每个字沿斜线从左上往右下排，后一个字比前一个低半行，字号可以逐个变大。

- 适合：`emotion`、`question`、`transition_talk`；风格：web；轻重：2
- 示例：`{"beat": "emotion", "text": "简单吗？"}`

### `text_depth_overlap_frame` 字跨框边混搭

画面缩成中间一个窄框，几组不同字体颜色的大字一半在框内一半伸出框外，制造前后层次。

- 适合：`concept`、`emphasis`；风格：web；轻重：3
- 示例：`{"beat": "concept", "items": ["网感", "高级感", "节奏", "留白"]}`

### `text_orbit_3d` 字环绕人旋转

关键词拆成单字，像一圈立体字环绕着人头转：转到身后的字被人挡住，转到胸前的字压在人前面。

- 适合：`concept`、`emotion`；风格：web；轻重：3
- 示例：`{"beat": "concept", "text": "关键信息"}`

### `word_wall_cloud` 字墙与字云

人身后铺满文字：同一个字重复成墙表达「碎碎念、太多太吵」，或多层远近不同的字漂浮表达「信息很多很乱」。

- 适合：`emotion`、`negative`、`concept`；风格：premium、web；轻重：2
- 变体：`wall` 重复字墙（premium、web）；`cloud` 多层景深字云（premium、web）
- 示例：`{"beat": "emotion", "text": "吵"}`

### `pinyin_note` 拼音谐音注释

关键词上方或下方标一行拼音或谐音梗，读到哪个字那个音节放大，增加网感和俏皮感。

- 适合：`concept`、`emotion`、`list`、`topic`；风格：web；轻重：1
- 变体：`above` 上方拼音跟读（web）；`pun` 下方谐音梗（web）；`list` 头像列表注释（web）
- 示例：`{"beat": "concept", "text": "上盘硬菜", "items": [{"text": "油条", "pun": "oil tiao"}, {"text": "豆汁", "pun": "dou juice"}, {"text": "煎饼", "pun": "jian bing"}]}`

### `credits_bilingual` 双语制作团队字幕

最后一镜是压暗的空镜，左上「制作团队 PRODUCTION TEAM」，下面几列中文职位 + 英文小字 + 细斜线连着人名，白色衬线小字，像电影片尾。

- 适合：`cta`；风格：premium；轻重：2
- 示例：`{"beat": "cta", "items": [{"role": "出品", "en": "Producer", "name": "阿木"}, {"role": "剪辑", "en": "Editor", "name": "AI Agent"}, {"role": "配乐", "en": "Music", "name": "Mixkit"}]}`

### `ready_go_iris_out` 开讲前暗角收黑

说「现在开始」那一句，人两侧摆好错位白色大字和空心描边的 READY GO→，随后四周暗角 0.5 秒向内收，画面压成黑底只剩人和字，下一镜硬切进第一招。

- 适合：`transition_talk`、`chapter`；风格：premium；轻重：3
- 示例：`{"beat": "transition_talk", "text": "开始", "en": "READY GO→"}`

### `darken_blend_text` 手写字变暗混合

手写体白字带深阴影放在人物身后，用变暗混合只留下暗色笔迹，像印在墙上的氛围字。

- 适合：`story`、`topic`；风格：premium；轻重：1
- 示例：`{"beat": "story", "wall": "十年剪辑 只做口播"}`

### `hazard_tape_strips` 斜向警戒带英文条

画面一角两条交叉的斜向色带（黄底黑字、蓝底白字），印着重复英文，像警戒胶带。

- 适合：`hook`、`topic`、`negative`；风格：web；轻重：2
- 示例：`{"beat": "hook", "en": "Warning", "en2": "Do not skip"}`

### `search_proof_hook` 模糊搜索结果钩子

画面是一页整体虚化的搜索结果录屏，中间留一块清晰的结果卡，前景压粗黑大字「不会告诉你的」，右侧卡其色竖排关键词滑入，背后一个巨大的灰色「90%」底纹。

- 适合：`hook`、`evidence`；风格：web；轻重：3
- 示例：`{"beat": "hook", "src": "@rec", "text": "不会告诉你的", "items": ["流量", "算法"], "number": "90%"}`

### `match_shape_cut` 相似形状快切

几个外形相似的物体（杯口、碗、唱片）缩放到同样大小、同一圆心，以零点几秒一下的节奏连续硬切，形状不变内容在变。

- 适合：`list`、`hook`；风格：web；轻重：3
- 示例：`{"beat": "list", "srcs": ["@photo", "@shot", "@rec", "@rec2"], "text": "形状不变 内容在变"}`

### `radial_blur_feel` 径向模糊失焦感

画面被径向或旋转模糊成一片旋涡，中间两行极小、字距拉得极开的白字，把「看不清、难受」的感受做出来。

- 适合：`negative`、`emotion`；风格：premium；轻重：3
- 示例：`{"beat": "negative", "lines": ["看 不 清", "好 难 受"]}`

### `edge_white_fade` 底部白色渐隐

画面最底部约四分之一由下往上从亮白渐隐到透明，压在人物身后，像海报底部打光。

- 适合：`hook`、`topic`；风格：premium；轻重：1
- 示例：`{"beat": "topic"}`

### `particle_overlay` 粒子飘落层

一层飘动的粒子（星光颗粒、纸币金币）叠在画面上或只在卡片框内飘，给结尾或金额加氛围。

- 适合：`cta`、`number`；风格：variety、premium、web；轻重：2
- 变体：`starfield` 星河粒子（variety、premium、web）；`money` 卡内撒钱（variety、web）
- 示例：`{"beat": "cta", "text": "我们下期见"}`

### `canvas_feather_extend` 取色画布羽化延伸

原画面不够铺满时，在后面垫一块取自墙面颜色的画布并大羽化融合，画面像向上延伸出一大片干净留白。

- 适合：`topic`、`concept`；风格：premium；轻重：2
- 示例：`{"beat": "topic", "text": "上方留白放标题", "sub": "画面往下挪，墙面颜色补上去"}`

### `id_watermark_bg` 斜排 ID 水印底纹

整屏铺满斜排的博主 ID 小字，白色行和暗橙行交错并朝相反方向缓慢平移，像钞票防伪底纹。

- 适合：`hook`、`cta`、`chapter`；风格：web、premium；轻重：1
- 示例：`{"beat": "cta", "id": "@口播剪辑研究所"}`

### `ui_panel_metaphor_bg` 半透明 PPT 面板比喻

人身后的画面上铺几块半透明灰白矩形面板，像 PPT 或官网页面，配一个红色半透明巨字压在人后面，比喻「模板化」。

- 适合：`negative`、`concept`；风格：premium；轻重：2
- 示例：`{"beat": "negative", "giant": "模板"}`

### `greenscreen_desaturate` 灰度绿幕去饱和叠加

玻璃、烟雾、光效这类只有黑白灰的绿幕素材抠不干净时，直接把饱和度拉到最低，绿色变成深灰，滤色叠在深色背景上看起来像透明叠加。

- 适合：`emotion`；风格：premium；轻重：1
- 示例：`{"beat": "emotion", "overlay": "@rec2"}`

### `color_swatch_card` 磨砂色卡

人旁边浮出一张半透明磨砂玻璃圆角卡，里面几根竖着的胶囊色条和圆点，下方黄色大字「≤3 种颜色」，旁边一行弧形小字配黄色放射短线。

- 适合：`concept`、`number`；风格：premium、web；轻重：2
- 示例：`{"beat": "concept", "colors": ["#F2E9B8", "#F0A21A", "#BFE3F0"], "text": "≤3 种颜色", "note_line": "配色越少越高级"}`

### `diagram_glow_callout` 示意图分级发光标注

一张示意图（火箭、产品架构、漏斗）背景先压暗、主体加白色发光；说到哪一级，那一段覆盖一层半透明色块并拉出一道梯形光束连到旁边的彩色标签，逐级点亮。

- 适合：`concept`、`steps`；风格：premium；轻重：2
- 示例：`{"beat": "concept", "src": "@shot", "stages": [{"poly": [[0.05, 0.05], [0.95, 0.05], [0.95, 0.4], [0.05, 0.4]], "label": "第一层：占用比例"}, {"poly": [[0.05, 0.45], [0.95, 0.45], [0.95, 0.85], [0.05, 0.85]], "label": "第二层：自动压缩"}]}`

### `avatar_motion_trail` 头像轨迹残影

圆形头像沿一条路径移动，每隔一段留下一个静止复制体，路径上配箭头，像画出动态轨迹。

- 适合：`steps`、`story`；风格：web；轻重：2
- 示例：`{"beat": "steps"}`

### `subject_spin_ring` 主体物缓转加虚线环

画面中上部一个抠出来的主体物（星球、产品、硬币）缓慢自转，边缘带柔光，外圈一个白色细虚线环反向慢转。

- 适合：`topic`、`chapter`；风格：premium；轻重：2
- 示例：`{"beat": "topic", "icon": "Globe showing asia-australia", "text": "一个产品 三种卖法"}`

### `text_follow_gesture` 文字跟手势运动

字随人的手势动：双手张开字放大、合拢缩小，手一推字横拉过去，双手一压字被挤扁。

- 适合：`emphasis`、`emotion`、`demo`；风格：web、premium；轻重：2
- 示例：`{"beat": "emphasis", "text": "放大", "keys": null}`

### `perspective_paper_panels` 透视纸板立在人旁

人在场景里说话，旁边像立着几块带透视角度的白色纸板，纸板上是竖排彩色关键词和小字段落，随着说话一块块滑入。

- 适合：`list`；风格：premium；轻重：2
- 示例：`{"beat": "list", "items": [{"text": "表达", "note": "先把一句话说清楚"}, {"text": "节奏", "note": "每两秒有变化"}, {"text": "包装", "note": "重点才加字"}]}`

### `orbit_coverage` 地球轨道覆盖动画

黑色全屏，地球居中，外面一圈细灰轨道环，一个卫星亮点沿轨道移动，地球表面逐块亮起淡黄色覆盖区，从卫星位置往下投一道光。

- 适合：`concept`；风格：premium；轻重：3
- 示例：`{"beat": "concept", "orbit": true, "text": "全球覆盖"}`

### `hand_mask_text_wipe` 手臂抹字

人旁边一块竖排文字，手臂一挥文字像被抹掉一样从上到下消失，反过来就是字从手里拉出来。

- 适合：`emotion`、`emphasis`；风格：web、premium；轻重：2
- 示例：`{"beat": "emotion", "text": "抹掉焦虑", "wipe_at": 1.6}`

### `mic_cluster_announce` 话筒围采宣布

头像下方一排复古话筒从两侧冲进来像发布会围采，同时金色闪光扫过留下金边花字。

- 适合：`topic`、`hook`；风格：variety；轻重：3
- 示例：`{"beat": "topic", "text": "重磅宣布"}`

### `frame_stickers` 边框贴纸

拍立得框、胶片框、卡通手绘框套住人物，人物头部超出框外，做出照片或作品展示感。

- 适合：`story`、`evidence`；风格：web、variety；轻重：2
- 变体：`polaroid` 拍立得框（web、variety）；`film` 胶片框（web、variety）；`cartoon` 卡通手绘框（variety、web）
- 示例：`{"beat": "story", "caption": "2026 夏"}`

### `pain_point_opening` 痛点词贴纸接怎么办

黄色主题词打出后，两个彩色痛点词（没排版~、没思路~）歪斜弹出、各挂一个走路小人贴纸，接一下故障抖动，换成黄色「怎么办?」配哭脸和大问号。

- 适合：`hook`、`question`；风格：web、variety；轻重：3
- 示例：`{"beat": "hook", "text": "剪口播", "items": ["没排版~", "没思路~"]}`

### `jy_text_template_variety` 剪映综艺文字模板

直接调用剪映自带的综艺文字模板（前方高能、注意、警告、OUT、情绪词啊啊啊），自带循环动画。

- 适合：`emotion`、`negative`、`hook`；风格：variety；轻重：2
- 变体：`energy` 前方高能（variety）；`warn` 警告（variety）；`out` OUT（variety）；`aaa` 情绪词（variety）
- 示例：`{"beat": "emotion"}`

## 已实现：全片一次选定

- `sub_look`（无底柔阴影字幕）：`box` 半透明黑底条（高级感默认）；`shadow` 无底柔阴影白字；`serif` 胸口粗宋白字（杂志感）；`low` 小号压底（大字多的片子）
- `sub_key_look`（字幕关键词强调）：`weight` 换粗一档不变色（高级感默认）；`red` 同号深红；`yellow` 亮黄放大 1.2 倍（网感）；`bracket` 加【】（教程类）；`stripe` 黄字放大弹一下（综艺感）
- `font_palette`（全片字体基调表）：`sans` 干货黑体（默认）；`serif` 杂志宋体：标题和字幕都换思源宋体；`heavy` 网感粗斜黑：标题换得意黑；`hand` 标题换毛笔字
- `titles[].anim`（闪现入场）：`flash` 先亮白闪一下再定住，任何大字都能用，网感档的整屏单字页默认
- `sub_look`（黑底条访谈字幕）：`bar` 不透明黑条访谈字幕：任何背景上都能读
- `sub_look`（描边综艺字幕）：`outline` 白字黑边（综艺感默认）；`chest` 胸口深蓝圆体白边；`huazi` 整句蓝边黄字垫黑底
- `sub_look`（双行滚动字幕）：`rolling` 双行滚动字幕：左下角两行，上一句变灰退上去（无人出镜的解说）；`rolling_ink` 双行滚动字幕深色版：浅色纸页底上用

## 已实现：写在 timeline 字段里的手法

版式、背景、镜头运动、素材卡样式、开场这类手法不跟一段话的内容走，由 Agent 按画面节奏写进 layout、broll、zoom 或顶层字段；字段细节见 `timeline.md`。每条的示例是样本册用的时间线片段（0~3.6 秒，`A[...]` 是素材路径）。

### `bg_dim_focus` 背景压暗突出主体

前景卡片、截图或数字出现时，后面的背景整体暗下去一截，主体立刻跳出来；也可以全片给背景统一压暗。

- 怎么写：broll 的 "dim"：sync / pre / false
- 风格：premium
- 自动：高级感里卡片、截图、透视卡浮在口播全屏上时默认 sync；相接的几张共用一层
- 变体：`sync` 同帧压暗：卡片入场同一刻，背景 0.3 秒压到六成亮（premium、web）；`pre` 先暗后出：提前 0.4 秒压到四成亮，像灯光暗下来，卡片才浮上来（premium、web）
- 示例：`{"broll": [{"t0": 0.7, "t1": 3.5, "src": "A['shot']", "fit": "card", "w": 0.82, "y": 0.46, "dim": "sync"}]}`

### `talk_zoom_punch` 口播景别推近

同一机位口播，在停顿或重点词处画面猛地推近一档，遮住跳剪接缝也给重音加力。

- 怎么写：顶层 "auto_zoom"：jump / snap / mixed / false
- 风格：premium、web、variety
- 自动：网感档和综艺感默认 mixed，克制档 jump
- 变体：`jump` 跳切三档：停顿处硬切 100% / 115% / 125%（premium）；`snap` 句首快推：粗剪接缝或重点句开口 0.15 秒推进 7%，遮跳剪（premium、web、variety）；`two_step` 一句两推：重点句先推 5%，说到第二个强调词再推 5%（mixed 里自动用）（web、variety）
- 示例：`{"auto_zoom": false, "zoom": [{"t0": 1.4, "t1": 3.6, "from": 1.15, "to": 1.15, "ease": 0.01}]}`

### `frame_card_scale` 画框缩放

口播画面在全屏和缩进的圆角卡片之间快速缩放：讲重点时从卡片撑满全屏，讲负面或第 N 点时从全屏缩小露出四周黑底。

- 怎么写：layout 的 inset 版式：{"mode": "inset", "anim": ..., "at": 相对秒, "to": 目标大小, "bg": "dots", "gray": true}
- 风格：web、premium
- 变体：`expand` 卡片撑满讲重点（web、premium）；`shrink` 缩小压抑讲负面（可加 gray 变黑白）（web）；`badge` 章节编号缩框，右上弹编号圆章（web）；`static` 点阵底上的静止人物卡（premium、web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "inset", "anim": "expand", "at": 1.2, "bg": "dots", "gray": false}]}`

### `punch_zoom_detail` 局部放大看细节

截图或录屏先给全景，然后放大到关键数字或按钮处停一下，再回到全景。

- 怎么写：broll 的 "punch"（截图硬切放大）或 "focus"（平滑放大，card / contain / cover 都能用，写 hold 停一下再缩回）
- 风格：premium、web
- 变体：`screenshot_punch` 截图硬切放大 2.2 倍对准关键数字，停一下硬切回（premium、web）；`recording_zoom` 平滑放大：0.5 秒推到 2.4 倍，停 1 秒再缩回全景（premium、web）
- 示例：`{"broll": [{"t0": 0.3, "t1": 3.6, "src": "A['shot']", "fit": "card", "w": 0.82, "y": 0.46, "punch": {"t": 1.0, "dur": 1.6, "scale": 2.2, "cx": 0.3, "cy": 0.35}}]}`

### `slow_push_drift` 缓推运镜

整段画面在几秒内持续慢慢推近或带一点漂移，画面一直在动但不晃眼。

- 怎么写：zoom 的 "push"：suspense / settle（可加 dx 横向漂移）；broll 的 "motion": "drift"
- 风格：premium、web
- 变体：`suspense` 慢推做悬疑：1.5 秒推到 115%（premium、web）；`segment_end` 段尾整段慢推到 112%（premium、web）；`drift` 素材缓推加横向漂移（premium、web）；`card_drift` 卡片往右下漂（premium、web）
- 示例：`{"auto_zoom": false, "zoom": [{"t0": 0.3, "t1": 3.6, "push": "suspense"}]}`

### `broll_band_layout` 横版素材带构图

横版素材裁成 4:3 横条放在画面中上部，上下用同一素材放大压暗或纹理底填满；需要强视觉时改为全屏铺满再叠包装。

- 怎么写：broll 的 "fit": "band"，"bg"：dim / blur / metal；"ratio" 默认 4:3，"y" 默认 0.45
- 风格：premium
- 变体：`dim_copy` 同素材压暗加网点颗粒做底（财经知识口播常用的版式）（premium）；`blur` 同素材虚化压暗做底（premium、web）；`metal` 拉丝金属底，横条加白边（premium）
- 示例：`{"broll": [{"t0": 0.3, "t1": 3.6, "src": "A['rec']", "fit": "band", "bg": "dim"}], "layout": [{"t0": 0.3, "t1": 3.6, "mode": "pip", "pos": "bottom_right"}]}`

### `aside_blur_stack` 虚化底叠截图

讲截图时人整个移出画面，背景只剩口播的虚化，两三张截图居中依次进场、上下叠放。

- 怎么写：aside 版式的 "stack": [截图, ...]，"interval" 进场间隔（默认 0.5 秒），每张可写 at
- 风格：web、premium
- 示例：`{"layout": [{"t0": 0.3, "t1": 3.6, "mode": "aside", "stack": ["A['shot']", "A['photo']", "A['shot']"]}]}`

### `pip_circle_avatar` 圆形头像小窗

B-roll、录屏、资料页期间，人物缩成角落里的圆形头像继续说话，观众一直看得到人。

- 怎么写：pip 版式的 "look"：ring / feather / shadow；"pos"：top_right / top_left / bottom_left / bottom_right / center
- 风格：premium、web
- 自动：整屏大字、章节页、巨数字、章节转场时小窗自动让开（"hide_on_peak": false 关掉）
- 变体：`ring` 细环硬边，右上（premium、web）；`feather` 羽化虚边，左下（premium、web）；`stroke_shadow` 白描边加投影，右下（premium、web）
- 示例：`{"layout": [{"t0": 0.3, "t1": 3.6, "mode": "hidden"}, {"t0": 0.3, "t1": 3.6, "mode": "pip", "look": "ring", "pos": "top_right"}], "broll": [{"t0": 0.3, "t1": 3.6, "src": "A['rec']", "fit": "cover"}]}`

### `pip_shrink_circle` 圆形蒙版收缩

全屏口播被圆形蒙版快速收成一个圆，或停在画面中间做大圆特写，或再滑到角落变成头像。

- 怎么写：layout 的 circle 版式：{"mode": "circle", "anim": ..., "bg": "blur|black|grid|dots|none", "ring": "gold|white|pink_dash|none"}；to_corner 后面接同位置的 pip
- 风格：premium、web
- 变体：`to_corner` 先缩后移进角落变头像（premium、web）；`quick` 0.2 秒猛收成圆（web）；`center_ring` 居中大圆加环，圆外网格底（web、premium）
- 示例：`{"layout": [{"t0": 0.3, "t1": 3.6, "mode": "circle", "anim": "to_corner"}]}`

### `compare_split_panels` 分屏对比

画面切成两到三块并排放不同素材，用撕纸边、斜线或圆角窗口分开，形成前后、左右、好坏的对照。

- 怎么写：layout 的 split 版式：{"mode": "split", "variant": ..., "panels": [{"src", "label"}], "focus_at": [相对秒]}；src 写 aroll 用口播
- 风格：web、premium
- 变体：`torn` 撕纸竖条（web）；`diagonal` 15° 斜线上下分割（web）；`focus` 圆角双窗切焦点（web、premium）；`triptych` 三屏并排（web、premium）
- 示例：`{"layout": [{"t0": 0.3, "t1": 3.6, "mode": "split", "variant": "torn", "focus_at": [0, 1.6], "panels": [{"src": "A['shot']", "label": "以前"}, {"src": "A['photo']", "label": "现在"}]}]}`

### `perspective_card` 透视斜置卡

口播画面或截图被拉成斜放的透视四边形，像斜摆的照片或立在桌上的纸，可以单张、左右镜像成对，或者一边斜着一边缓慢上升。

- 怎么写：broll 的 "fit": "tilt"，"tilt"：left / right / pair（pair 用 "srcs" 给三张）；默认从下方升入再缓缓上升
- 风格：premium、web
- 自动：连续几张没写方向的透视卡左右交替
- 变体：`tilt_rise` 斜放缓升，相邻页左右交替（premium、web）；`mirror_pair` 镜像三联（premium、web）
- 示例：`{"broll": [{"t0": 0.3, "t1": 1.9, "src": "A['shot']", "fit": "tilt"}, {"t0": 1.9, "t1": 3.6, "src": "A['photo']", "fit": "tilt"}]}`

### `grid_bg` 网格底

黑底或纯色底上铺一层细方格网，人物抠像或小窗放在上面，脱离实拍环境，可做成系列统一底。

- 怎么写：layout 的 bg 版式：{"mode": "bg", "bg": "grid", "variant": ...}，人用 pip、inset 或抠像放上面；inset / circle / split 的 "bg" 也能写 "grid:rainbow"
- 风格：web、premium
- 变体：`white` 黑底白网格（web）；`rainbow` 灰细网格透彩虹光晕（premium、web）；`neon` 彩虹细线网格（web）；`plaid` 卡其底波浪格纹（web）
- 示例：`{"layout": [{"t0": 0.3, "t1": 3.6, "mode": "bg", "bg": "grid", "variant": "white"}, {"t0": 0.3, "t1": 3.6, "mode": "pip", "pos": "center", "hide_on_peak": false}]}`

### `dot_matrix_bg` 黑底点阵底

纯黑底上铺一层很淡的细点阵，可以静止当卡片底，也可以缓慢漂移并透出淡淡的彩虹光晕。

- 怎么写：layout 的 bg 版式 {"mode": "bg", "bg": "dots", "variant": ...}，或 inset 的 "bg": "dots"
- 风格：premium、web
- 变体：`static_card` 静态点阵配人物卡（premium、web）；`scroll_rainbow` 炫彩波点漂移（web、premium）
- 示例：`{"layout": [{"t0": 0.3, "t1": 3.6, "mode": "inset", "bg": "dots:static"}]}`

### `match_motion_cut` 同向运动衔接

前一镜头的主体朝一个方向移动，切到下一镜头时新主体从同一方向、同样速度继续移动，观众视线跟着走，感觉不到切点。

- 怎么写：broll 的 "link": "left|right|up"（写在后一张上）
- 风格：premium、web
- 自动：两张卡片首尾相接、都没写进出场时，前一张往左加速移出、后一张从右减速移入（"auto_link": false 关掉）
- 示例：`{"broll": [{"t0": 0.3, "t1": 1.9, "src": "A['shot']", "fit": "card", "w": 0.82, "y": 0.46}, {"t0": 1.9, "t1": 3.6, "src": "A['photo']", "fit": "card", "w": 0.82, "y": 0.46}]}`

### `screenshot_highlight` 截图划重点

新闻、公告截图上的关键句被一条色块从左往右划出来：黄色荧光笔（字仍是黑的），或黑色反白（被划到的字变成白字黑底）。

- 怎么写：broll（card / contain 的图片）的 "marks"：{"boxes": [[x, y, w, h], ...]（相对截图）, "look": "yellow|inverse", "at": [每道开始的相对秒], "wipe": 0.4}
- 风格：premium、web
- 自动：每划一道自带一声上滑音
- 变体：`yellow` 黄色荧光笔：亮黄色块从左往右扫过，正片叠底，黑字透出来（premium、web）；`inverse` 黑色反白：被划到的字变成白字黑底，比黄色更重更正式（premium、web）
- 示例：`{"broll": [{"t0": 0.3, "t1": 3.6, "src": "A['shot']", "fit": "card", "w": 0.82, "y": 0.46, "marks": {"boxes": [[0.13, 0.405, 0.72, 0.115], [0.1, 0.615, 0.77, 0.115]], "look": "yellow", "at": [0.6, 1.6]}}]}`

### `clip_card_frame` 装饰边框素材卡

人物胸前或画面中部出现一张横版圆角素材卡（B-roll 或自己另一场景的片段），边缘加发光描边或相机取景框，从下往上滑入。

- 怎么写：broll（card / contain）的 "frame"：glow / viewfinder；写了 frame 默认宽 0.68、中心在 0.57 高、从下往上滑入
- 风格：premium、web
- 变体：`glow` 发光描边：卡片边缘一圈柔和淡黄光（premium、web）；`viewfinder` 取景器：四角白色直角标、右上 REC、左下 ISO 和快门、底部曝光刻度，像在回看素材（web、premium）
- 示例：`{"broll": [{"t0": 0.3, "t1": 3.6, "src": "A['photo']", "fit": "card", "frame": "glow"}]}`

### `doc_pages_fly_in` 报告纸页飞入堆叠

引用报告、论文、财报时，一页页带投影的纸页旋转着飞进画面、落定后叠成一摞，像真的把文件扔在桌上，底层是压暗的画面。

- 怎么写：broll 的 "fit": "pages"，"srcs": [报告截图, ...]（不够就轮着用），"variant"：cascade / scatter / stack / curl
- 风格：premium、web
- 自动：自带翻页声；浮在口播全屏上时背景跟卡片一样压暗
- 变体：`cascade` 彩色纸页错落：白、粉、黄、蓝四张纸页从右上依次飞入，各自略倾斜上下错落（web、premium）；`scatter` 四面八方散落：十张纸页从四面八方旋转飞入，带拖影，散落堆成一桌文件（web）；`stack` 一沓拖影落定：一页纸从右下斜飞进来，后面拖着三张错开 1 帧的副本，落定后叠成一摞再轻微放大（premium、web）；`curl` 卷角单页滑入：报告右下角卷起白色卷角，整页从上方滑下来定位（premium、web）
- 示例：`{"broll": [{"t0": 0.2, "t1": 3.6, "fit": "pages", "variant": "cascade", "src": "A['shot']", "srcs": ["A['shot']", "A['photo']"]}]}`

### `device_mockup` 设备样机展示

把录屏、成片或示例视频装进手机、显示器或电视样机里展示，配步骤清单或逐字文稿，让演示显得规整。

- 怎么写：layout 的 mockup 版式：{"mode": "mockup", "variant": ..., "src": 录屏或成片, "title", "sub", "steps": [...], "at": [每步出现秒], "src2", "at2", "labels": [两个标签]}
- 风格：web、premium
- 自动：样机入场自带唰声
- 变体：`steps` 样机配步骤：深色网格底，样机在右，左边黄色「方法：」下的步骤跟着口播一条条出现，顶部白色粗斜体标题（web、premium）；`screen` 渐变底样机录屏：深蓝到灰蓝渐变带细点阵，样机居中占画宽六成放录屏，顶部白色超粗英文大标题加中文副标（web、premium）；`stack` 两台叠放：示例装进样机，第二台从右侧压上来叠在前面，各带一个黄色标签（web、premium）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "mockup", "variant": "steps", "src": "A['rec']", "title": "第 1 种：问答结构", "steps": ["先抛一个问题", "马上给答案", "再举一个例子"], "at": [0.5, 1.3, 2.1]}]}`

### `avatar_content_combo` 圆头像图文组合版

人物缩成圆形头像固定在一角，其余画面整齐摆放标题、横图卡片或软件截图，像一页带主持人的图文版面。

- 怎么写：layout 的 combo 版式：{"mode": "combo", "variant": ..., "cards": [图片], "at": [每张出现秒], "title", "sub", "note", "hl", "bg"（band 的底素材）, "crop"（头像取口播哪块，同 pip）}
- 风格：web、premium
- 自动：每张卡出现自带啵一声
- 变体：`band` 头像领标题：素材铺底，左上白边圆头像，右边白色粗斜体标题和黄色副标题，下方一张横图卡片（web、premium）；`head_top` 顶部大头像配横图：牛皮纸底，顶部居中大圆头像，下方一张满宽白描边横图（web、premium）；`corner` 角落头像压叠卡：口播虚化底，两张横图卡依次上浮叠放，左下圆头像压住第二张卡的一角（web、premium）；`tutorial` 教程截图版：暗色虚化底，左上圆头像配步骤名，中间界面截图卡，下方参数截图，一行小字说明（关键词黄色）（web、premium）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "combo", "variant": "band", "bg": "A['rec']", "title": "为什么新手总踩坑", "sub": "三个原因", "cards": ["A['photo']"]}]}`

### `points_overview` 要点目录与回顾

把本期 N 个要点做成一页目录或片尾回顾，逐张累加出现：彩色斜标签卡层叠、两列编号目录、2×2 截图编号卡或倾斜的作品墙。

- 怎么写：layout 的 overview 版式：{"mode": "overview", "variant": ..., "items": [{"num", "text", "src"}], "title", "en", "every"}；不写 items 就从时间线的章节页自动取（编号、章节名、这一章第一张图片，没有就截口播）
- 风格：premium、web
- 自动：目录在画面上时常驻字幕让开；卡片一张张出现自带啵一声
- 变体：`grid` 2×2 编号卡回顾：口播虚化，四张圆角卡一张张弹出，每张是该章节的画面定格，上面 POINT、空心大序号和章节名（premium、web）；`toc` 彩色斜标签目录：方格纸底，左边半透明红色竖排大字主题加手写英文，右边紫橙绿白四张斜标签卡依次上滑，各带描边大序号（web）；`list` 两列编号目录：暖色渐变底，「01·标题」白色宋体两列逐条快速闪现（premium、web）；`tilted_collage` 倾斜作品墙：前面讲过的画面缩成 3~5 张白边卡片，斜着叠成一堆缓慢漂移，暗红色调底（premium、web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "overview", "variant": "grid", "title": "新手三个坑", "en": "Three traps", "items": [{"num": "01", "text": "不存档", "src": "A['shot']"}, {"num": "02", "text": "乱改代码", "src": "A['photo']"}, {"num": "03", "text": "不做测试"}, {"num": "04", "text": "不写交接", "src": "A['shot']"}]}]}`

### `follow_endcard` 头像关注尾帧

片尾 1.5~2 秒黑底（或黑网格底）中央一个白边圆形账号头像，下方红色加号一点就翻成白底红勾，下面「感谢关注」或一句自我介绍；也可以只是账号名 @xxx 放大滚入配一声收银机「叮」。

- 怎么写：layout 的 endcard 版式：{"mode": "endcard", "variant": "follow|name", "avatar": 头像图片, "name": "@账号", "text": "感谢关注"}；不给头像就用口播画面里的人脸
- 风格：web、variety
- 自动：尾帧在画面上时常驻字幕让开；头像弹出和加号翻勾自带声音
- 变体：`follow` 加号翻勾：黑网格底中央白边圆头像弹出，下面红色加号一翻变成白底红勾，头像上方弧形黄字账号名，下面一行「感谢关注」（web、variety）；`name` 账号名放大滚入：黑底中央「@账号」带回弹地放大滚入，配一声「叮」（web、variety）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "endcard", "variant": "follow", "name": "@口播剪辑课", "text": "学会了，去练"}]}`

### `opening_entry_hit` 开场第一秒入场冲击

视频第一帧画面带一个入场动作（闪白、从小放大、光圈打开、聚光推近或速度线冲刺），同时响一声铃、点击或重音，把观众一下拽进第一句话。

- 怎么写：顶层 "opening"：flash / zoom / boom / iris / spotlight / false
- 风格：premium、web、variety
- 自动：不写就按强度档自动加：网感档 zoom、克制档 spotlight、综艺感 flash；开头就是铺满素材或别的版式时不加
- 变体：`zoom` 从小放大：画面先以 45% 大小出现在黑底中间，0.4 秒放大铺满（web、premium）；`spotlight` 聚光推近：第一句四周压成椭圆暗角只有人亮，同时整句缓推到 112%（premium）；`flash` 闪白响铃：过曝白光加竖向动态模糊 0.2 秒闪入，落定时略放大（web、variety）；`iris` 光圈打开：黑底上一个小圆从人脸处张开到 60% 宽，再打开到全屏（web）；`boom` 综艺咚加冲刺：放射速度线冲 0.6 秒，画面从 115% 弹回（variety）
- 示例：`{"opening": "zoom"}`

### `matte_bg_blur` 抠像背景虚化

人物始终清晰，身后背景整体轻度虚化，像大光圈拍摄，文字可以夹在背景和人物之间。

- 怎么写：layout 的 matte 版式：{"mode": "matte", "bg": "blur", "blur": 12}；想整片用就写一段从头到尾
- 风格：premium
- 自动：背景虚化前先把人挖掉，人身边不会糊出一圈人的颜色；这几秒不自动推近
- 变体：`blur` 背景虚化：人始终清楚，身后整体轻度虚化，像大光圈拍的（premium、web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "matte", "bg": "blur"}]}`

### `matte_bg_swap` 抠像换话题背景

人物原地不动，身后的实拍背景瞬间换成和话题相关的画面，交代「我们在聊什么」。

- 怎么写：layout 的 matte 版式：{"mode": "matte", "src": 话题画面, "title": "话题标题", "outline": "solid_white"}；切换点对齐口播关键词
- 风格：web
- 自动：背景压到八成亮（dim 可改）；硬切那一下自带啵一声
- 变体：`swap` 换话题背景：人原地不动，身后的实拍背景硬切成话题相关的截图、录屏或图片，压到八成亮，顶部可压一行话题标题（web、premium）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "matte", "src": "A['photo']", "title": "上下文管理", "outline": "solid_white"}]}`

### `matte_outline` 抠像描边

抠出的人像外围加一圈描边，像贴纸一样从背景上跳出来，同时遮住抠像毛边。

- 怎么写：matte、corner 版式的 "outline"：solid_white / color_thin / dashed / torn_edge（color_thin 可配 "outline_color": "green"）
- 风格：web
- 自动：描边前先把飘起来的头发丝收掉，不会描成一坨白；虚线背景自动压暗
- 变体：`solid_white` 白色实线：人像外一圈约 9 像素纯白实心描边，像贴纸，最常用（web）；`color_thin` 彩色细描边：约 5 像素黄色细边（outline_color 写 green 换绿色），配干净背景（web、premium）；`dashed` 白色虚线：沿轮廓外扩一圈白色短划虚线，背景压到六成亮，像剪纸（web）；`torn_edge` 撕纸毛边：约 15 像素不规则白纸边带一点投影，像从杂志上撕下来贴上去（web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "matte", "bg": "keep", "outline": "solid_white"}]}`

### `matte_corner_person` 抠像人缩角让位

人物抠像带描边缩到一角，腾出大片空间给录屏、观点卡或立体关键词卡，人和信息同屏。

- 怎么写：layout 的 corner 版式：{"mode": "corner", "variant": 变体, "items": [文字 或 {text, en, src}], "src": 录屏}；人默认站的一边录屏右下有关键内容时写 "side": "left"
- 风格：web、premium
- 自动：开头 0.4 秒人从原位缩进角落，卡片之后每 0.3 秒弹一张，各带一声
- 变体：`over_recording` 人叠录屏：录屏铺满（横屏录屏放在上半屏），人带白描边缩到六成放右下，整段不切（web、premium）；`point_cards` 观点卡竖排：背景虚化，人带白色虚线描边缩到左下，右上依次弹出三张深橄榄色圆角观点卡，带浅色错位投影（web、premium）；`glass_cards` 立体玻璃卡：深色网格底，人带白描边站左下，右侧三张半透明蓝玻璃卡带透视，上下错开浮着（web）；`tilted_cards` 倾斜图片卡：背景虚化，以素材为底的圆角卡斜着从左滑入，沿对角线错开排，卡上超粗白字配小号英文（web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "corner", "variant": "over_recording", "src": "A['rec']", "items": [{"text": "一事一会话", "en": "one task", "src": "A['photo']"}, {"text": "留两成交接", "en": "handoff", "src": "A['shot']"}, {"text": "先读再动手", "en": "read first", "src": "A['photo']"}]}]}`

### `matte_frame_breakout` 人物出框

人物被装进相框、卡片或横条里，但头或双手越过边框伸出来，像从画里探出来。

- 怎么写：layout 的 breakout 版式：{"mode": "breakout", "variant": 变体, "title": 标题或相框手写字, "src": 素材, "src2": 横条下方的图}
- 风格：web
- 自动：头出框多少按头顶位置自动算（overflow 可改）；进来那一下 0.15 秒叠化，自带啵一声
- 变体：`head_over_frame` 相框出头：拍立得相框装着口播，人的头顶越过相框上沿探出来，相框下沿写一行手写字（web）；`band_pop` 横条探头：上下两张图，中间一条口播横条，人头伸出横条压在上方大标题前面（web）；`corner_over_card` 压住画框角：深色网格底上一张白色圆角画框装标题和素材，人缩小站在左下压住画框角，带投影（web）；`hands_below_card` 手伸出卡片：口播装进圆角卡片、下沿裁到腰部，手越过卡片底边伸到黑底上（要手势伸出身体外的素材，近景口播做不出）（web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "breakout", "variant": "head_over_frame", "src": "A['shot']", "src2": "A['shot']", "title": "Day 1"}]}`

### `sfx_event_engine` 音效自动挂点

观众听到的是：画面每发生一个事件（元素弹出、卡片滑入、大字砸下、转场、定格），那一帧就响一个对应的短音效，动作越大声音越重，纯口播段保持安静。

- 怎么写：自动：画面上每个事件（大字、素材、版式、转场、定格）开始那一帧按事件类型配声音；手写在素材、大字、版式的 "sound" 或顶层 "sounds"。sound 可以写声音清单里的名字、组合名（swing 挥动落定、shuttle 穿梭、rising_ui 升调串），也可以直接写剪映音效原名（「综艺叮」「唰」），按对照表换算。密度写 audio.sfx_density：sparse / dense
- 风格：premium、web、variety
- 自动：起音对准画面事件开始那一帧（蓄力类反向镲、上升音是最响处对准）；同一时刻最多叠两个；重音类每种全片两次；一句话里提示音最多 3 个；纯口播段不加。渲染加 --stems 后用 audio_check.py 出频谱检查图和逐个音效差几帧
- 变体：`premium_sparse` 高级感稀疏：每分钟最多 12 个，只挂画面事件（premium、web）；`variety_dense` 综艺感密集：每分钟最多 30 个，每个花字、每次弹出都配一声（variety、web）；`new_sounds` 新增声音试听：开门、机械开合、机器启动、上发条、推近、拉远、悬念、戏剧重音、欢呼、贝斯单音、利刃（premium、web、variety）
- 示例：`{"audio": {"sfx_density": "sparse"}, "titles": [{"t0": 0.4, "t1": 2.6, "layout": "side", "lead": "真正拉开差距的是", "text": "信息密度", "hl": ["密度"]}], "broll": [{"t0": 3.0, "t1": 5.4, "src": "A['shot']", "fit": "card", "enter": "slide_up"}], "transitions": [{"t": 5.9, "type": "flash"}]}`

### `sfx_impact` 冲击重音

信息爆点时一声重击：大字砸下、数据炸出、人物冲出、结论定格，或一声低沉的综艺「咚」把观众摁住。

- 怎么写：大字、素材、sounds 写 "sound"：swing（挥动落定）/ hit（击中）/ thump（综艺咚）
- 风格：web、variety
- 自动：重音前 0.2 秒配乐自动压低 6 dB 让出位置；hit 这类重音每种全片最多两次
- 变体：`swing` 挥动落定：人物冲出来、元素甩进来，嗖一声再落定（web、variety）；`hit` 击中：标题砸下、数据炸出（web、variety）；`dong` 综艺咚：低沉一声把观众摁住（thump）（web、variety）
- 示例：`{"audio": {"bgm": [{"src": "A['bgm']", "t0": 0, "t1": 4.0}], "bed": false}, "titles": [{"t0": 0.6, "t1": 3.8, "layout": "word", "text": "暴涨 3 倍", "anim": "drop", "sound": "swing"}]}`

### `sfx_ui_pop` 元素出现提示音

关键词、标签、卡片、图标每次冒出来都配一个短促的点击、叮或啵，同一组并列词用同一个声音，网感主要靠这类声音堆出来。

- 怎么写：大字、素材、sounds 写 "sound"：click / ding / pop / rising_ui（写 step 0、1、2…一个比一个高）/ zip_up（电子滑音）
- 风格：web、variety
- 自动：提示音一句话里最多 3 个，多了自动去掉或压低；同一组并列词用同一个声音
- 变体：`click` 点击：标签、按钮、卡片弹出（web、variety）；`ding` 叮：花字关键词弹出（web、variety）；`pop` 啵：图片、气泡冒出（web、variety）；`rising_ui` 升调 UI 串：重点词一个个蹦出，每个高一个音（写 step 0、1、2…）（web、variety）；`slide_ui` 电子滑音：图标、贴纸飞入（zip_up）（web、variety）
- 示例：`{"titles": [{"t0": 0.2, "t1": 3.5, "layout": "list", "variant": "bullets", "items": ["选题", "脚本", "剪辑", "复盘"], "item_at": [0.3, 0.9, 1.5, 2.1], "sfx": false, "sound": [{"type": "click", "at": 0.3}, {"type": "click", "at": 0.9}, {"type": "click", "at": 1.5}, {"type": "click", "at": 2.1}]}]}`

### `sfx_whoosh` 转场滑动音

画面切换、甩切、冲屏、章节进出时配一声过渡音：短促的「唰」表现速度，更厚更长的风声表现呼啸，高音闪光扫过表现穿梭。

- 怎么写：transitions 写 "sound"：whoosh（唰）/ whoosh_big（旋风）/ shuttle（穿梭）；不写按转场种类自动配
- 风格：web、premium
- 自动：效果转场自带：闪白、模糊扫屏配唰，压黑配旋风，漏光配穿梭，故障配电流；起音对准转场开始那一帧；硬切不配
- 变体：`speed` 速度感：短促的唰，配动态模糊甩切（web、premium）；`gust` 呼啸感：更长更厚的风声（web、premium）；`shuttle` 穿梭感：嗖一声叠高音闪光（web、premium）
- 示例：`{"broll": [{"t0": 1.6, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.6, "type": "blur_swipe", "sound": "whoosh"}]}`

### `music_bed_levels` 配乐两档音量加闪避

同一首用户给的配乐，开头 12~15 秒音量高一点带气氛，进入正文压低，人一说话配乐再自动让开，人声始终在前。

- 怎么写：audio.bed：{"open": 13, "lift": 5, "fade": 0.9}（默认就开，写 false 关掉）
- 风格：premium、web、variety
- 自动：开头 13 秒配乐比正文高 5 dB，0.9 秒过渡到正文；人一说话配乐自动让开（阈值 -30 dB、压缩比 6），说话时配乐比人声低约 18~22 dB
- 变体：`bed` 开头高一档、正文压低（样片把开头缩成 4 秒）（premium、web、variety）
- 示例：`{"audio": {"bgm": [{"src": "A['bgm']", "t0": 0, "t1": 9.0}], "bed": {"open": 4.0}}}`

### `music_hit_stop_gap` 音乐留白与重音收住

段落之间配乐完全停下 0.5~2 秒，只剩人声甚至全静，然后下一段带着新配乐或大画面变化进来；开场钩子数字放大那一帧一声重音鼓，鼓尾配乐一起收掉，空约 1 秒后硬切进下一段。

- 怎么写：段落留白：sections 的段落写 "seam": "gap"（"gap": 秒）；重音收住：audio.stops [{"t": 数字放大那一帧, "gap": 1.0}]
- 风格：premium、web
- 自动：留白和重音收住后面必须跟一个大变化（换段、章节页、硬切画面）；只有一首配乐、没写段落时，章节页前自动压低一下
- 变体：`plain_gap` 段落留白：配乐停 0.8 秒，再带新一段进来（premium、web）；`hit_stop` 重音收住再硬切：数字放大那一帧一声重音鼓，配乐跟着收，空 1 秒硬切进下一段（premium、web）
- 示例：`{"audio": {"bgm": [{"src": "A['bgm']", "t0": 0, "t1": 7.0}], "bed": false}, "sections": [{"t0": 0, "name": "前一段"}, {"t0": 3.6, "name": "后一段", "seam": "gap", "gap": 0.8}], "titles": [], "broll": [{"t0": 3.6, "t1": 7.0, "src": "A['photo']", "fit": "cover", "sfx": false}]}`

### `music_section_switch` 按段落换曲

配乐跟着段落走：开场用一段激昂节奏提气，7 秒处淡进主曲；信息密的快剪段换快歌、舒缓段换慢歌；情绪突变处直接换曲当转场；换曲接缝用一声嗖盖住。

- 怎么写：顶层 sections 分段（写 mood：calm / dense / happy / hype，可写 seam、shout），audio.tracks 给几首曲子 [{"src", "mood"}]；开场提气写 audio.open_boost {"src", "len": 7}
- 风格：premium、web、variety
- 自动：段落没写情绪按画面密度判（每 10 秒 3.5 个以上画面事件算快剪段），曲子没写情绪按速度判（108 BPM 以上算快）；换到没放过的曲子从它第一个有劲的重拍起播；舒缓切快节奏默认嗖一声盖接缝，快切慢默认留白，同情绪交叉淡化且早 0.3 秒进来；只给一首曲子时在同一首里按段落跳到能量高的一段；不生成任何音乐
- 变体：`open_boost` 开场提气再切主曲：提气曲 0.34 秒淡出，主曲 0.33 秒淡入（premium、web、variety）；`density_bpm` 按信息密度换快慢：快剪段自动换快歌（premium、web）；`chapter_switch` 大章节换曲：交叉淡化，声音比画面早 0.3 秒（premium、web）；`mood_switch` 情绪突变换曲：画面切的那一帧直接换，叠一声欢呼（web、variety）；`sfx_seam` 音效盖接缝：嗖起来时前一首淡出，后一首在嗖最响处起播（premium、web）；`silence_gap` 音乐留白：前一首先停 1 秒，再进下一首（premium、web）
- 示例：`{"audio": {"bgm": [{"src": "A['bgm']", "t0": 0, "t1": 7.0}], "open_boost": {"src": "A['hype']", "len": 3.5}, "bed": false}}`

### `jcut_audio_lead` 声音先入

上一个画面还没切，下一段的人声和配乐已经先响起来，画面随后才切过去。

- 怎么写：自动（timeline 写 "jcut": false 关掉，写数字改提前量 0.3~1 秒）
- 风格：premium、web
- 自动：铺满画面的素材、遮住人的版式、章节页在下一句开口前后结束时，延长到开口后 0.35 秒：先听到下一句，画面再切回口播。画面盖住了嘴，口型不会对不上；单机位口播之间不做（声音先进来时人嘴没动，口型会穿帮）。配乐换曲的交叉淡化也早 0.3 秒进来
- 变体：`off` 对比：素材在开口前就切回口播（premium、web）；`audio_lead_jcut` 声音先入：开口 0.35 秒后画面才切回（premium、web）
- 示例：`{"jcut": false, "broll": [{"t0": 0.3, "t1": 2.1, "src": "A['photo']", "fit": "cover", "sfx": false}]}`

### `rough_cut_breath_trim` 去气口粗剪

口播主轨按句硬切，句间停顿、口误、重录都剪掉；网感版平均 2 秒一刀，高级感版保留一点呼吸和段落留白。

- 怎么写：粗剪：auto_edl.py 从转写起草 edl.json（重录留最后一遍、半句和语气词删掉），edl 写 "breath": web_tight / premium_breath，段落结尾那句写 "para": true；rough_cut.py 照着剪
- 风格：premium、web、variety
- 自动：网感紧剪句间只留 0.08 秒、一句里超过 0.15 秒的停顿也收短；高级感句间留 0.3 秒、段落结尾多留 1 秒；句中收短留下的刀口写进 lines.json，渲染时在那里跳景别遮跳剪
- 变体：`raw` 原始素材（口播 02 前 20 秒，没剪）（premium、web、variety）；`web_tight` 网感紧剪：41.7 秒原片剪成 18.2 秒，平均 2.6 秒一刀（web、variety）；`premium_breath` 高级感留气口：剪成 20.6 秒，段落处多留一口气（premium、web）
- 示例：`{}`

### `speed_adjust` 整体与录屏变速

整条口播比原速快一点点，语速更紧凑但听不出变调；录屏里等待、加载的段落加速，录屏比讲解短时放慢让画面和讲解一起结束。

- 怎么写：口播整体：edl.json 的 "speed"（真人 1.05~1.09，AI 配音写 "ai_voice": true 可到 1.2）；录屏：broll 写 "speed": "auto"
- 风格：web、premium
- 自动：录屏里 1 秒以上画面不动的等待段加速 2~10 倍正好塞进这段，加速处右上角标「快进 ×N」；录屏比这段短时整体放慢（最慢 0.36 倍）
- 变体：`voice_1x` 对比：口播原速（web、premium）；`voice_global` 口播整体提速 1.07 倍，听不出变调（web、premium）；`screenrec_1x` 对比：6 秒录屏原速放进 3.3 秒，后半截看不到（web、premium）；`screenrec_ramp` 录屏等待段加速：三段等待加速，整段操作都看得到（web、premium）
- 示例：`{}`

### `voice_cleanup_loudness` 原声降噪统一响度

无线麦收的原声统一放大、降噪，响度拉到平台标准，手机外放也听得清。

- 怎么写：audio.voice：{"lufs": -16, "denoise": true, "deess": true, "compress": true}（默认全开；"cleanup": false 只做响度）
- 风格：premium、web、variety
- 自动：先量素材底噪定降噪强度，再高通去嗡声、去齿音、轻压缩，最后两遍法把响度拉到 -16 LUFS（综艺感 -15），峰值不超过 -1.5 dBFS；结果按素材缓存
- 变体：`raw` 对比：原声没处理（premium、web、variety）；`clean` 降噪、去齿音、压缩、响度 -16 LUFS（premium、web、variety）
- 示例：`{"audio": {"voice": {"raw": true}}}`

### `script_segment_plan` 先按结构切段再包装

不产生画面：拿到口播先识别字幕，按「开场 / 第一点 / 第二点 / … / 结束语」切段，给每段起小标题、标起止时间和情绪，同一段共享一套包装参数，再开始逐句包装。

- 怎么写：顶层 sections：[{"t0", "name", "mood"}]，开场、第一点…结束语各一段；plan.md 先写段落表再逐句包装
- 风格：premium、web
- 自动：3 段以上或 3 分钟以上没写 sections，rhythm_check 会提醒；配乐换曲、留白、声音先入都按段落走；没写就按章节页切

### `title_aside_note` 主标题旁小补充

主标题出来后，旁边补一行很小的俏皮话或便利贴小标签，给版面加一点人味。

- 怎么写：beats 的一条写 "note": "小补充"、"note_look": arc / tag；主标题出来 0.3 秒后弹到它右上角
- 风格：web
- 自动：位置按主标题排好的外框算；每个画面最多一个
- 变体：`tag` 便利贴标签：橙底黑字小色块歪 5 度（web）；`arc` 弧形语气词：一行黄色小字沿弧线斜排（web）
- 示例：`{"beats": [{"t0": 0.3, "t1": 3.5, "beat": "concept", "use": "side", "lead": "这一步叫", "text": "版本管理", "note": "亲测好用", "note_look": "tag", "sfx": false}]}`

### `sfx_comic_sting` 综艺梗音效

反转、吐槽、打脸、翻车的笑点上配一个综艺梗音：经典戏剧三连「DUN DUN DUUUUN!!」、拳击重击、放屁声、心碎，常和人脸特效同一帧。

- 怎么写：自动：beats 里 emotion（情绪、吐槽）句的句末；negative（负面）句写 "sting": true 或声音名才配（提醒类的负面句配梗会错位）；写 false 关；audio.stings false 全关
- 风格：web、variety
- 自动：负面句轮换失落类（悲伤长号、失败钢琴、答错；放屁声只在综艺感），情绪句轮换滑稽类（打脸、弹簧、被打懵、小丑喇叭、梗鼓点）；两个梗音效至少隔 12 秒；戏剧三连（dun_dun_duun）只能手写，全片一次；克制档不加
- 变体：`drama` 戏剧三连：反转、真相揭晓（web、variety）；`slap` 打脸重击：被怼、被驳回、想法撞墙（web、variety）；`fail` 翻车滑稽：白忙一场、失落（web、variety）
- 示例：`{"beats": [{"t0": 0.4, "t1": 2.6, "beat": "emotion", "use": "word", "text": "真相", "sting": "dun_dun_duun", "sfx": false}]}`

### `sfx_mechanical` 机械结构音

画面做结构变化（推拉、窗口变形、分屏拼接、版式切换）时配机械声：推拉配机器开门的气压声，形变配机器人启动声，分屏配上发条的咔哒声。

- 怎么写：自动：版式 inset、split、frame 出现或变化那一刻；手写 sound 写 mech_door / mech_robot / mech_wind
- 风格：web
- 自动：口播卡片放大或缩小（推拉）配气压开门，画框形变配机器人启动，分屏拼接配上发条；柔和治愈的片子写 sfx: false 关
- 变体：`door` 气压开门：口播卡片推拉（web）；`robot` 机器人启动：画框形变（web）；`wind` 上发条：分屏拼接（web）
- 示例：`{"layout": [{"t0": 0.4, "t1": 3.4, "mode": "inset", "anim": "expand", "at": 0.6, "bg": "dots"}]}`

### `bass_pre_entry` 包装前垫低音

数据卡、关键词页、章节页这类重包装出现前半拍到一拍，先响一个低沉的贝斯单音，让情绪先进场，画面包装再出来，比直接加音效更顺。

- 怎么写：自动（audio.bass_pre 写 false 关）
- 风格：premium、web
- 自动：数据卡、数字、整屏单字、章节页出现前 0.4 秒先响一个贝斯单音，让情绪先进场；综艺感不加；不和砸屏的重击叠
- 变体：`bass` 包装前垫低音（premium、web）
- 示例：`{"audio": {"bgm": [{"src": "A['bgm']", "t0": 0, "t1": 4.0}], "bed": false}, "titles": [{"t0": 1.2, "t1": 3.8, "layout": "word", "text": "暴涨 3 倍", "anim": "drop"}]}`

### `sfx_ambience` 氛围铺垫音

铺垫情绪的环境声：故弄玄虚时一段上升或紧张的悬疑声配画面压暗红字，温柔治愈时一段发光闪亮声加平静氛围音配光斑暖色。

- 怎么写：自动：beats 里 question（提问）句底下铺悬念小鼓；beat 写 "ambience": suspense / calm / false
- 风格：web、premium
- 自动：悬念最多铺 4 秒，比配乐低一档；calm 是闪亮一声加平静氛围底，用在温柔、治愈的段落
- 变体：`suspense` 悬疑紧张：抛出问题等答案（web、premium）；`calm` 温柔治愈：闪亮一声加平静氛围（web、premium）
- 示例：`{"beats": [{"t0": 0.3, "t1": 3.8, "beat": "question", "use": "side", "text": "到底满没满？", "ambience": "suspense", "sfx": false}]}`

### `voice_fx_swap` 人声变声段

某几秒的人声被换个质感制造笑点或区分角色：念别人原话时变成扩音器声并叠录制边框，内心 OS 换成加速的 TTS 角色音，不能说的词被一声「哔」盖住并贴「秘密」。

- 怎么写：顶层 voice_fx：[{"t0", "t1", "type": megaphone / bleep, "label"}]
- 风格：web、variety
- 自动：扩音器：这几秒人声只留中频再轻微失真，画面叠四角取景框和闪烁的 REC；哔声：原声静音换成 1000 Hz 的哔，嘴边贴黄底「消音」（label 可改）。AI 配音的内心独白要接语音合成，还没做；剪映草稿里变声要在剪映里手动加
- 变体：`megaphone` 扩音器念原话（web、variety）；`bleep` 哔声消音（web、variety）
- 示例：`{"voice_fx": [{"t0": 0.6, "t1": 2.8, "type": "megaphone"}]}`

### `music_beat_loop` 节奏段无缝循环

大段画中画讲解时，背景是一段约 10 秒的固定节奏，反复接很多次听不出接缝。

- 怎么写：audio.tracks 里那首写 "loop": true（或 {"bars": 4}）
- 风格：premium、web
- 自动：挑这首里能量平稳的 4 小节（短于 8 秒的拍子取 8 小节），首尾按重拍对齐反复接、接缝 10 毫秒交叉淡化，铺满它负责的段落；循环 2 分钟以上会腻，中间用段落换曲打断
- 变体：`loop` 节奏段无缝循环（样片用 2 小节，5.3 秒处接回开头）（premium、web）
- 示例：`{"audio": {"tracks": [{"src": "A['bgm']", "mood": "calm", "loop": {"bars": 2}}], "bed": false}}`

### `music_climax_splice` 截高潮段接尾音

段落收尾时，把同一首配乐最燃的收尾部分截出来，对齐节拍无缝接在主旋律后面，把情绪提前推到顶；推完再接一个 1~2 秒的收尾音，进入章节页留白。

- 怎么写：sections 的段落写 "climax": true（或秒数）
- 风格：premium、web
- 自动：这一段最后约 4 小节（6~10 秒）换成同一首里能量最高的 4 小节，切点落在重拍上听不出接缝，推到段落结束；后面接段落留白或换曲
- 变体：`climax` 截高潮段推到段落末尾（样片 3 秒处切进高潮）（premium、web）
- 示例：`{"sections": [{"t0": 0, "name": "前一段", "mood": "calm", "climax": 6.0}, {"t0": 8.0, "name": "后一段", "mood": "calm", "seam": "gap"}], "audio": {"tracks": [{"src": "A['bgm']", "mood": "calm"}], "bed": false}}`

### `arrow_stickers` 箭头标注

用箭头把视线拉到目标上：指向重点、表示涨跌、画出运动路线，或四个箭头从四角指向主体。

- 怎么写：titles 写 {"layout": "arrow", "variant": point / up / corners, "from": [x, y], "to": [x, y], "color", "dir": "down"}，坐标按画面比例，to 是箭头要指的那一点（截图上的按钮、数字），一定要对准真实目标
- 风格：web、variety
- 自动：0.2 秒从尾巴长到箭头，到了沿方向轻轻弹；同屏箭头风格不超过 2 种
- 变体：`point` 粗箭头指向目标：带白边的黄色粗箭头（web、variety）；`up` 3D 上升箭头：绿色立体箭头往右上冲，dir 写 down 是红色下跌（web、variety）；`corners` 四角视线引导：四个箭头从画面四角指向主体（web、variety）
- 示例：`{"titles": [{"t0": 0.4, "t1": 3.4, "layout": "arrow", "variant": "point", "from": [0.85, 0.78], "to": [0.62, 0.6]}]}`

### `focus_box` 聚焦框标注

在要观众看的地方套一个框：相机对焦角标收紧、黄色细圆角框圈出，或发光框把一句话从截图里拎出来重写。

- 怎么写：titles 写 {"layout": "focus", "variant": brackets / callout / glow, "box": [x, y, w, h], "text"}，box 按画面比例圈出要看的地方
- 风格：web、premium
- 自动：同屏只一个焦点；glow 写了 text 就在框里重写那句话（字少于两行）
- 变体：`brackets` 对焦角标：四个白色角标从大一圈收紧（web、premium）；`callout` 黄色细框：框外压暗两成（web、premium）；`glow` 发光框重写重点句：黄绿发光框里重写那句话（web）
- 示例：`{"broll": [{"t0": 0.2, "t1": 3.5, "src": "A['shot']", "fit": "card", "w": 0.86, "y": 0.45, "sfx": false}], "titles": [{"t0": 0.8, "t1": 3.4, "layout": "focus", "variant": "brackets", "box": [0.12, 0.4, 0.76, 0.1]}]}`

### `card_slide_pair` 双卡同步左移让位

第一张卡居中一会儿后向左平移约半张卡（部分出画），同时第二张卡从右侧滑入，两卡并排。

- 怎么写：titles 写 {"layout": "cardpair", "src": 第一张, "src2": 第二张, "at": 第二张进场秒数, "y", "w"}
- 风格：premium、web
- 自动：第一张居中出现，到 at 秒 0.5 秒缓入缓出往左让到画面左边（露出约半张），第二张从右边滑到右半边，两张并排；底下口播压暗
- 变体：`pair` 先说 A 再说 B 的并列截图（premium、web）
- 示例：`{"titles": [{"t0": 0.3, "t1": 3.5, "layout": "cardpair", "src": "A['shot']", "src2": "A['photo']", "at": 1.4}]}`

### `divider_line_reveal` 金色细分割线展开

人物肩膀高度一条很细的金色渐变长线从中心向两边展开，两端渐隐，把标题区和人物区分开。

- 怎么写：titles 写 {"layout": "divider", "y": 0.42, "w": 0.8}
- 风格：premium
- 自动：0.6 秒从中间往两边展开，两端渐隐，1080 宽画布上 3 像素，压一层淡投影浅色墙上也看得见
- 变体：`line` 肩膀高度金色细线，把标题区和人分开（premium）
- 示例：`{"titles": [{"t0": 0.3, "t1": 3.5, "layout": "divider", "y": 0.42}, {"t0": 0.6, "t1": 3.5, "layout": "side", "text": "版本管理", "y": 0.3, "sfx": false}]}`

### `doodle_marks` 手绘点缀标记

少量手绘小元素点缀重点：涂鸦圈、头像涂鸦边框、三条放射短线、星光、墨镜表情、彩纸屑。

- 怎么写：doodles 写 {"type": multicircle / spiral / exclaim / sparkle / circle, "x", "y", "w", "h"} 或 "target": {"text": 大字里的词}
- 风格：web、variety
- 自动：逐笔画出 0.4 秒；同一画面涂鸦圈不超过 3 个、放射线一个，每分钟贴纸点缀不超过 4 个，不压脸不压大字
- 变体：`multicircle` 多圈涂鸦圈：一笔绕两圈半（web、variety）；`spiral` 螺旋圈：从外往里收（web、variety）；`exclaim` 三短线放射：情绪点上冒三道短线（web、variety）；`sparkle` 星光：亮点、灵感（web、variety）
- 示例：`{"titles": [{"t0": 0.3, "t1": 3.5, "layout": "side", "text": "改坏了", "y": 0.56, "sfx": false}], "doodles": [{"t0": 0.7, "t1": 3.4, "type": "multicircle", "target": {"text": "改坏了"}}]}`

### `entry_preset_extra` 克制入场预设

几种不回弹、很干净的入场：从上方落下、从灰色小字放大成白字、像卡片一样镜面翻进来。

- 怎么写：titles 写 "anim"：fall（上方落下）/ graypop（灰变白放大）/ flip（镜面翻转）
- 风格：premium
- 自动：都不回弹、干净利落，克制档用；flip 适合面板、章节名
- 变体：`fall` 上方落下：从一成画面高处落下，模糊变清（premium）；`graypop` 灰变白放大：灰色半透明小字放大成白字（premium）；`flip` 镜面翻转：像卡片一样绕竖轴翻进来（premium）
- 示例：`{"titles": [{"t0": 0.3, "t1": 3.5, "layout": "side", "lead": "这一步叫", "text": "版本管理", "anim": "fall", "sfx": false}]}`

### `read_then_dim` 读完压暗留底

一组关键大字说完后不立刻消失，而是在两三秒里慢慢变暗到约三分之一亮度，作为背景继续留着。

- 怎么写：titles 写 "dim_after": 秒（从出现算起，说完的时刻）
- 风格：premium
- 自动：说完后 2.5 秒慢慢暗到三成多亮度，留在画面上可以回看，下一个版式硬切掉
- 变体：`dim` 读完压暗留底（样片 1.2 秒后开始暗）（premium）
- 示例：`{"titles": [{"t0": 0.3, "t1": 3.6, "layout": "quote", "text": "不要依赖 AI 的记忆\\N来撤回", "hl": ["记忆"], "dim_after": 1.2, "sfx": false}]}`

### `screen_reaction_fx` 整屏反应特效

用整屏画面特效配情绪：变黑白表示失落，震动表示综艺冲击，裂开表示崩溃，模糊遮隐私，全剧终收片尾。

- 怎么写：顶层 fx 写 {"t0", "t1", "type": bw / shake / crack / magnifier / the_end / blur}；crack 的 "at": [x, y] 是裂开的点，magnifier 的 "at" 是要放大的点（"zoom" 倍数、"r" 镜片半径占画面宽），blur 的 "box": [x, y, w, h]
- 风格：web、variety
- 自动：每种自带声音（变黑白低音下沉、震动落地、裂开重击、放大镜推近、全剧终反向镲片）；剪映草稿里变黑白、震动、裂开了、全剧终放剪映真特效，放大镜和模糊遮挡那几秒铺成片画面
- 变体：`bw` 变黑白：失落、听不懂，整屏去色，前后 0.15 秒渐变（web、variety）；`shake` 震动：冲击、惊讶，整屏约 12 Hz 抖动、越抖越轻（amp 改幅度）（web、variety）；`crack` 裂开了：崩溃，屏幕从 at 那一点（默认右上角，避开脸）裂开，跟着抖一下（web、variety）；`magnifier` 放大镜：at 那一点放大 zoom 倍（默认 2），带镜框手柄，0.15 秒弹出；variant reach 手柄从画外 from 伸进来、镜片滑到 at 再移走（默认 1.5 倍）（web、variety）；`the_end` 全剧终：片尾整屏压暗，毛笔「全剧终」大字加 THE END（web、variety）；`blur` 模糊遮挡：box 框里强模糊遮隐私，优先于马赛克（web、variety）
- 示例：`{"fx": [{"t0": 0.6, "t1": 3.4, "type": "bw"}]}`

### `spotlight_vignette` 聚光灯暗角

画面四周压成黑色椭圆暗角，只有人物身上亮，像舞台聚光灯，常配合缓推或综艺重音。

- 怎么写：fx 写 {"type": "spotlight", "variant": push / drama, "y": 亮区中心高}；只用在开头或重大转折，一期一两次
- 风格：premium、web、variety
- 自动：push 同时整句缓推到 112%（"push": false 不推）；drama 加荧幕噪点、配重音；剪映草稿放「聚光灯」
- 变体：`push` 聚光加推近：四周压成椭圆暗角只有人亮，同时缓推到 112%（premium、web、variety）；`drama` 戏剧聚焦：聚光加荧幕噪点，关键反转词处配重音（web、variety）
- 示例：`{"fx": [{"t0": 0.3, "t1": 3.4, "type": "spotlight", "variant": "push"}]}`

### `dim_spotlight_box` 压暗聚光框游走

画面整体压暗，只有一个虚线框区域保持原亮度，这个框在脸、手、衣服之间移动变形，引导观众看哪里。

- 怎么写：fx 写 {"type": "dimbox", "boxes": [{"at": 秒, "box": [x, y, w, h], "shape": rect / circle}]}，at 相对特效开始；不写 boxes 就先框脸、一半时移到胸口
- 风格：web
- 自动：每个框至少停 0.6 秒；移动 0.4 秒缓入缓出，每移一次滴答一声
- 变体：`walk` 压暗聚光框游走：整屏压到四成亮，白色虚线框里保持原亮度，在脸、胸口之间移动变形（web）
- 示例：`{"fx": [{"t0": 0.3, "t1": 3.5, "type": "dimbox"}]}`

### `crt_scanline` 扫描线老电视

画面叠一层细横向扫描线和暗角，像老电视显像管，可只给一句话做强调，也可给段落收尾加质感。

- 怎么写：fx 写 {"type": "crt", "variant": emphasis / section}；emphasis 只铺说到节目名、栏目名那 1.5 秒，section 铺段落收尾的总结句
- 风格：web
- 自动：前后 0.1 秒渐入渐出，起头一声故障音；section 加桶形弯曲、强暗角和轻推近；全片别一直开，会发灰累眼
- 变体：`emphasis` 一句话强调：细横向扫描线加暗角（web）；`section` 段落质感：扫描线、强暗角、桶形弯曲，配推近（web）
- 示例：`{"fx": [{"t0": 0.5, "t1": 3.4, "type": "crt", "variant": "emphasis"}]}`

### `halftone_texture` 网点丝印质感

一层规则的印刷网点颗粒，轻叠在画面或暗背景上做杂志、海报质感，加重了就是波普网点背景。

- 怎么写：fx 写 {"type": "halftone", "variant": screenprint / bg_grain}；波普底写在版式里：抠像换底 {"mode": "matte", "bg": "popart:pink"}（或 popart:red），纸页底 {"mode": "bg", "bg": "popart", "variant": "pink"}
- 风格：premium、web
- 自动：screenprint 扣掉人像，网点只在背景上；bg_grain 只叠在压暗的背景层（aside、hidden）上；红色波普底刺眼，别超过 2 秒
- 变体：`screenprint` 整体丝印叠加：细密网点略偏蓝，只在亮部和背景看得出来（premium、web）；`bg_grain` 暗背景颗粒：压暗的背景上一层网点，大片暗底不空不廉价（premium、web）；`popart` 波普网点底：粉紫底上从大到小的网点，人抠出来站在上面（web）
- 示例：`{"fx": [{"t0": 0.3, "t1": 3.5, "type": "halftone", "variant": "screenprint"}]}`

### `color_grade_shift` 调色变化

给某个段落换影调：整段降饱和偏冷灰显得沉稳，或先整体变黑白再让彩色色块扫过某个区域。

- 怎么写：fx 写 {"type": "grade", "variant": desat_cool / band}；band 可写 "colors" 三个色块颜色
- 风格：premium、web
- 自动：desat_cool 整段换影调（降饱和、偏冷灰、暗角两成），人和红字反而跳出来；band 只在讲「颜色」「变化」时偶尔用一次，每条色块扫过一声
- 变体：`desat_cool` 去色冷灰：整段降饱和、偏冷、压暗部（premium、web）；`band` 黑白加色块扫：先变黑白，红绿橙横色块依次从脸部扫过，色块里恢复颜色（web）
- 示例：`{"fx": [{"t0": 0.3, "t1": 3.5, "type": "grade", "variant": "desat_cool"}]}`

### `letterbox_bars` 宽银幕黑边

画面上下突然滑入两条黑边变成宽银幕比例，配一行大字，持续一到三秒后撤掉。

- 怎么写：fx 写 {"type": "letterbox", "text": 下黑边里滚动的小字（可不写）}，持续 1~3 秒；常配一行引用大字
- 风格：premium
- 自动：上下各 0.11 画面高，进出各 0.2 秒；常驻字幕在 0.8 画面高，不会被黑边压住
- 变体：`bars` 宽银幕黑边：上下黑边滑进来变成电影比例（premium、web）
- 示例：`{"fx": [{"t0": 0.3, "t1": 3.4, "type": "letterbox", "text": "EP.06  Claude Code 常用命令"}], "titles": [{"t0": 0.6, "t1": 3.3, "layout": "quote", "text": "慢就是快", "sfx": false}]}`

### `window_shape_morph` 窗口按节拍变形

人物装在小窗口里，背景是同画面的放大虚化版，窗口形状随口播节拍一下一下变：小圆、大圆、圆角方、竖长矩形，最后接近满屏。

- 怎么写：layout 写 {"mode": "morph", "at": [每次变形的秒数], "steps": [[宽, 高, 圆角, 中心高], ...]}；at 对准口播的节拍，不写就均匀排开
- 风格：web
- 自动：默认五步：小圆、大圆、圆角方、竖长圆角、接近满屏；背后是同画面放大 1.2 倍虚化压暗，每变一次啵一声；没有节拍感的平稳口播别用
- 变体：`steps` 窗口按节拍变形：人在小窗里，窗口形状一下一下变大变形（web）
- 示例：`{"layout": [{"t0": 0.2, "t1": 3.6, "mode": "morph", "at": [0.0, 0.6, 1.2, 1.8, 2.5]}]}`

### `face_effect_emotion` 人脸情绪特效

在吐槽、反转、自嘲的情绪点给人脸贴剪映人物特效，常两个叠用，如一脸问号、大头、中刀、石化。

- 怎么写：fx 写 {"type": "face", "names": [剪映人物特效名，常叠两个]}，0.6~3 秒；可用：大头、红温大头、一脸问号、懵、迷茫、惊讶、中刀、打击、石化了、宕机中、尴尬住了、灵机一动、真的会谢、秘密
- 风格：variety、web
- 自动：剪映草稿里放剪映真的人物特效（剪映里没有的名字那几秒铺成片画面）；成片里用抠像放大头、头边贴 3D 表情和手写问号近似；中刀、打击自带整屏震一下
- 变体：`bighead` 大头、懵（variety、web）；`hot` 红温大头（variety、web）；`stab` 中刀（variety、web）；`stone` 石化了（variety、web）；`idea` 灵机一动（variety、web）；`crash` 宕机中、尴尬住了（variety、web）
- 示例：`{"fx": [{"t0": 0.5, "t1": 3.4, "type": "face", "names": ["大头", "懵"]}]}`

### `rgb_glitch` RGB 故障闪切

切点前后约 0.2~0.3 秒画面或文字出现红青通道错位和横向切片偏移，然后切走或换字。

- 怎么写：transitions 写 {"t", "type": "glitch"} 整屏故障（综艺感章节页会自动轮到）；文字故障换字 titles 写 {"layout": "glitchswap", "text", "text2", "swap_at"}
- 风格：web
- 自动：整屏 0.3 秒红青错开加横切片跳动，配故障音；高级感片子只在片头用一次
- 变体：`frame` RGB 故障闪切：红青通道错开、几条横切片左右错位（web）；`text_swap` 文字故障换字：一句大字被红青错位撕开，故障中间换成下一句（web）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "glitch"}]}`

### `whip_blur` 动态模糊甩切

画面在两三帧内被强烈方向性运动模糊甩走，下一镜头同方向甩入后清晰；也可以只甩底层、上面文字不动。

- 怎么写：transitions 写 {"t", "type": "whip", "dir": left / right / up / down} 整屏甩切；只甩底在字不动底在换的 bgs 里写 "whip"
- 风格：web、premium
- 自动：网感档章节页自动轮到；配唰一声；只甩底常和字不动底在换一起用
- 变体：`whip` 整屏甩切：往一边甩走，下一段同方向甩进来（web、premium）；`bg_only` 只甩底：底层横向拉丝扫过，上面的字不动（web、premium）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "whip"}]}`

### `iris_circle` 圆形光圈转场

画面从一个小圆打开，或先收成一个圆、圆里换成下一个镜头再放大到满屏，像相机光圈。

- 怎么写：transitions 写 {"t", "type": "iris", "variant": swap / open, "x", "y": 圆心}；圆心要对准脸
- 风格：web、premium
- 自动：网感档章节页自动轮到；swap 0.3 秒收成中下部 0.6 宽的圆，圆里换段，0.4 秒放大；open 从黑底小圆张开到圆头像再打开
- 变体：`swap` 收圆换镜：画面收成一个圆，圆里换成下一段再放大到满屏（web、premium）；`open` 小圆打开：黑底上人从很小的圆张开成圆头像，再打开到满屏（web、premium）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "iris", "variant": "swap"}]}`

### `light_leak` 漏光闪过

切换处一大片橙黄暖光从画面一侧扫过、短暂几乎铺满再退去，光退后画面换成下一段。

- 怎么写：transitions 写 {"t", "type": "light_leak", "variant": flash / zoom_reveal}
- 风格：premium、web
- 自动：高级感两档章节页都会轮到；30 秒内最多一次；配一声穿梭声
- 变体：`flash` 光斑扫过：橙黄暖光从左边扫过，几乎铺满时换段（premium、web）；`zoom_reveal` 漏光后放大出成片：光退去时下一段从六成大小放大回满屏（premium、web）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "light_leak", "variant": "flash"}]}`

### `occlusion_wipe` 主题物遮挡扫屏

一个和本期主题相关的大物体（火星、产品、logo）带强烈动态模糊从画面一端冲到另一端，某一帧完全盖住画面，下一帧已经换成新版式。

- 怎么写：transitions 写 {"t", "type": "occlude", "src": 主题物图（透明底最好）}，或 "emoji": 3D 表情英文名；只在章节点用
- 风格：premium、web
- 自动：主题物放大到 1.7 倍画面宽，纵向强模糊从下往上冲过 0.4 秒，切点前后各一帧整屏盖满；配大段唰声
- 变体：`object` 主题物遮挡扫屏：火箭、产品、logo 从下往上冲过，盖满那一帧换段（premium、web）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "occlude", "emoji": "Rocket"}]}`

### `panel_carrier_transition` 白场载体接力转场

章节之间同一块白雾面板接力：面板放大盖满屏变成下一页，或镂空形状旋转换形，或像一扇门透视转开露出下一段。

- 怎么写：白雾章节页 fog 上写，后一页 window 写 "enter": "cover"（前一页底部面板放大盖屏）；"shapes": ["2", "?"] 加 "shape_at"（镂空换形）；"exit": "door"（最后 0.5 秒像门一样转开）
- 风格：premium
- 自动：只在要点切换处用，和白雾镂空序号配套；开门配开门声，换形配唰声；人一直在雾上面，两段人物位置要接近
- 变体：`zoom_cover` 放大盖屏：底部白雾面板往上急速放大盖满，变成整屏白雾数字页（premium、web）；`shape_rotate` 镂空换形旋转：白雾里的镂空数字逆时针转一下换成问号（premium、web）；`door_open` 透视开门：整屏白雾带着镂空数字以左边为轴转开，露出下一段（premium、web）
- 示例：`{"auto_transitions": false, "titles": [{"layout": "fog", "number": 1, "text": "先存档", "en": "plan first", "sfx": false, "t0": 0.2, "t1": 1.6, "variant": "panel"}, {"layout": "fog", "number": 2, "text": "先规划再动手", "en": "plan first", "sfx": false, "t0": 1.6, "t1": 3.6, "variant": "window", "enter": "cover"}]}`

### `paper_tear_reveal` 撕纸揭开

上一画面像纸一样被撕开或从纸团里展开，不规则白色纸边划过后露出下一画面。

- 怎么写：transitions 写 {"t", "type": "tear", "variant": diagonal / split, "angle": 撕边角度}
- 风格：web、variety
- 自动：网感档章节页自动轮到；切点前最后一帧定格被撕掉，白纸芯撕边程序画；配揉纸声；效果转场 30 秒内最多一个。揉纸展开要素材，没做
- 变体：`diagonal` 斜向撕开：一条带白纸芯的不规则撕边斜着划过，露出下一段（web、variety）；`split` 中间撕开：从中间撕开，上下两半往外退（web、variety）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "tear", "variant": "diagonal"}]}`

### `meme_clip_insert` 插入影视梗片段

抖完一个包袱后硬切插入一段约 1.2 秒大众熟悉的影视梗片段，横版居中黑底，不放头像和自己的字幕，然后硬切回口播。

- 怎么写：顶层 inserts 写 [{"t": 插入点, "src": 用户给的片段, "in": 从片段第几秒起, "dur": 1~1.5}]；插在抖完包袱之后的停顿处
- 风格：web、variety
- 自动：成片渲完后在 t 秒硬切插入：横版居中黑底，不带字幕和头像，用片段自己的声音（统一响度），配乐在这一段留空；片子变长 dur 秒；剪映草稿里不插，要在剪映里手动放；只用用户自己提供的片段（版权）
- 变体：`insert` 插入影视梗片段：硬切进一段 1.2 秒左右的梗，再硬切回口播（web、variety）
- 示例：`{"inserts": [{"t": 1.6, "src": "A['meme']", "dur": 1.2}]}`

### `sub_phrase_per_cut` 快剪一词一镜字幕

快剪段每个镜头只配一个 2~6 字短语，字幕和镜头同时切换，像词卡在跳。

- 怎么写：顶层 "phrase_subs": [{"t0", "t1", "cut": true}]，这段里的跟读字幕按逐字时间拆成 2~6 字一个的短语
- 风格：web、premium
- 自动：短语按分词断、不拆词，标点处必断、停顿长的地方优先断；起止吸附到 0.2 秒内的素材、版式、粗剪刀口；cut 为 true 时每个短语换一档景别（100% / 118% / 132% / 110% 硬切），一个机位也像在快剪
- 变体：`cut` 一词一镜：每个短语换一档景别，字幕和镜头同一帧切（web、premium）；`plain` 只拆短语不换景别：配真的快剪素材时用（web、premium）
- 示例：`{"auto_zoom": false, "phrase_subs": [{"t0": 0, "t1": 3.6, "cut": true}]}`

### `cover_first_frame` 首帧封面图

视频第 1 帧是一张只停 0.15 秒的封面图：抠像人物带白色贴纸描边、手指镜头，周围是倾斜的彩色标题，随后硬切进第一句口播，保证平台自动截的首帧就是包装好的封面。

- 怎么写：顶层 "cover": {"text", "text2", "frame_at": 抠哪一秒的人, "bg", "bg2", "dur": 0.15}；标题要和第一句口播呼应
- 风格：web
- 自动：片头 0.15 秒（3~6 帧）铺一张封面：抠像人带白贴纸描边，上下两行倾斜彩色标题，随后硬切进第一句；有封面时不再自动加开场冲击
- 变体：`cover` 首帧封面图：平台自动截的第一帧就是包装好的封面（样本册放慢到 0.8 秒好看清）（web）
- 示例：`{"cover": {"text": "剪辑三板斧", "text2": "新手直接抄", "frame_at": 0.5, "dur": 0.8}}`

### `point_index_marker` 角落要点编号

不离开口播画面，在角落常驻一个要点编号（01→02→03），每换一点用光扫或故障闪刷新数字，让观众知道讲到第几点。

- 怎么写：顶层 "points": {"variant": glow / film / brush, "items": [{"t0", "t1", "n", "text"}]}；不写 items 就按章节页自动排：每个章节页结束起到下一章开始，编号是章节号、旁边是章节名
- 风格：web、premium
- 自动：换一点的 0.4 秒做光扫、故障闪或斜切弹入，之后静止常驻；压在常驻字幕下面
- 变体：`glow` 顶部光扫编号：左上黄色粗斜体编号和本节名，换一点时一道黄色光团从左扫过把数字刷新（web、premium）；`film` 胶片框小窗编号：右上角胶片齿孔小卡，里面字距拉开的 POINT 和白色做旧大数字，换项处故障闪 0.15 秒（web）；`brush` 斜刃编号：左上白色粗斜体编号被一刀斜切出缺口，旁边一行本节名（web、premium）
- 示例：`{"points": {"variant": "glow", "items": [{"t0": 0.3, "t1": 1.9, "n": "1", "text": "找回会话"}, {"t0": 1.9, "t1": 3.6, "n": "2", "text": "上下文满了"}]}}`

### `persistent_hud` 常驻栏目信息层

全片常驻一层低调的信息：顶部一行灰色系列名水印，或一根随时间走完的黄色进度条（前端可挂一个卡通小人往前走）。

- 怎么写：顶层 "hud": {"variant": "watermark", "text": 系列名, "y": 0.04} 或 {"variant": "progress", "y": 0.24, "mascot": Fluent Emoji 名}
- 风格：premium、web
- 自动：水印整片不动、灰色低亮度；进度条从 0 走到 100%（按成片时长），前端小人跟着走；进度条默认放 24% 高，避开平台顶部按钮
- 变体：`watermark` 系列名水印：最上方一行灰色斜体系列名，整片不动（premium、web）；`progress` 进度条小人：上方一根黄色进度条随播放走完，前端一个小人跟着走（premium、web）
- 示例：`{"hud": {"variant": "watermark", "text": "vibe coding 从 0 到实战"}}`

### `fast_cut_word_montage` 一词一镜快剪

同一句话拆成 6~9 个短语，每个短语换一个不同的 B-roll 镜头，头像小窗不动，节奏像卡点，制造「大家都在冲」的热闹感。

- 怎么写：顶层 "montage_cuts": [{"t0", "t1", "srcs": [素材，或 {"src", "crop"} 同一段录屏裁不同地方当不同景别], "pip": true 或 {"pip": {x, y, d}}, "pos": 小窗位置, "subs": true, "broll": {"fit": "band", "crop": [...]}}]
- 风格：web、premium
- 自动：这段话按逐字时间拆成短语（同一词一镜字幕），每个短语换一个素材铺满（素材轮着用，视频从不同位置截），头像小窗不动，字幕一个镜头一个短语；没有逐字时间就 0.75 秒一镜
- 变体：`montage` 一词一镜快剪：一句话拆成六到九个短语，每个短语换一个镜头（web、premium）
- 示例：`{"montage_cuts": [{"t0": 0.2, "t1": 3.6, "srcs": ["A['shot']", "A['photo']", "A['rec']", "A['rec2']"]}]}`

### `section_end_climax` 段落收尾推高收束

大段落结尾先用一串 0.5~1 秒一镜的快剪把情绪推上去，回到口播跳切放大一档说出引出下一段的问题句，然后硬切整屏章节页，配乐戛然而止约 1.2 秒再进入下一部分。

- 怎么写：顶层 "section_ends": [{"t0", "t1": 快剪段, "srcs", "talk": [问题句起, 止], "silence": 1.2}]，接在下一个章节页前
- 风格：premium、web
- 自动：t0~t1 按短语快剪（同一词一镜快剪）；talk 那句跳到 115% 一档；下一个章节页那一下配乐停 1.2 秒再进下一部分；配乐高潮段用 sections 的 climax 接在快剪下面
- 变体：`climax` 段落收尾推高收束：快剪推情绪，跳一档说出问题句，硬切章节页、配乐戛然而止（premium、web）
- 示例：`{"section_ends": [{"t0": 0.2, "t1": 1.8, "srcs": ["A['shot']", "A['photo']", "A['rec']"], "talk": [1.8, 2.4]}], "titles": [{"t0": 2.4, "t1": 3.6, "layout": "chapter", "number": "03", "text": "先规划再动手", "en": "Plan first"}]}`

### `reaction_cutaway` 插入反应镜头

说完一个梗或一句夸赞后，硬切插入约 1 秒的反应镜头：博主本人在另一个场景鼓掌大笑，或一段影视梗片段，然后硬切回口播。

- 怎么写：顶层 inserts 写 [{"t": 插入点, "src": 用户给的反应镜头, "in", "dur": 1~1.5, "text": "嘿嘿"}]；text 是叠在镜头上的荧光绿花字
- 风格：web、variety
- 自动：同插入影视梗片段：横版居中黑底、不带字幕和头像、片子变长 dur 秒；一期最多两次；只用用户自己提供的镜头
- 变体：`host_cam` 博主另一机位：自己在别处鼓掌大笑 1 秒，加荧光绿「嘿嘿」（web、variety）；`meme_clip` 影视梗片段：一段 1.2 秒左右的梗，原片字幕留着（web、variety）
- 示例：`{"inserts": [{"t": 1.6, "src": "A['meme']", "dur": 1.2, "text": "嘿嘿"}]}`

### `privacy_mosaic` 截图隐私打码

真实手机截图（聊天、订单、账户）里的头像、名字、内容打成大颗粒马赛克，只留需要佐证的那一条可读。

- 怎么写：broll 或带 src 的大字写 "mosaic": [[x, y, 宽, 高], ...]（相对素材画面的比例），"mosaic_block" 改颗粒大小（默认 24，按素材宽 1080 算）；框的位置先跑 detect_sensitive.py 找手机号、邮箱、人名、二维码，确认后抄进来
- 风格：premium、web
- 自动：渲染前把素材打成马赛克副本（缓存在 ~/.cache/koubo/mosaic）：框里缩到 1/24 再按最近邻放大回去，认不出字；视频每帧同样位置打码
- 变体：`mosaic` 截图隐私打码：头像、名字、内容打成大颗粒马赛克，只留要佐证的那一条可读（premium、web）
- 示例：`{"broll": [{"t0": 0.3, "t1": 3.5, "src": "A['shot']", "fit": "card", "mosaic": [[0.0, 0.0, 1.0, 0.35], [0.0, 0.62, 1.0, 0.38]]}]}`

### `freeze_pause` 定格暂停

长段画中画中间说到有情绪的一句，画面定格压暗，出现暂停图标，头像跳到正中放大，配快门声并让配乐停一下。

- 怎么写：顶层 "freezes": [{"t0", "t1", "d": 头像大小, "y": 位置}]（1~1.9 秒，全片一次）
- 风格：premium、web
- 自动：画面停在这一帧并压暗，头像从角落放大到画面中间、带浅金圆环，右侧画暂停图标；配快门声，这几秒配乐静音
- 变体：`freeze` 定格暂停：长段画中画中间说到有情绪的一句，画面定格、头像跳到正中（premium、web）
- 示例：`{"freezes": [{"t0": 1.2, "t1": 2.8}]}`

### `bottom_black_badge` 口播上移底部留黑

口播段人物画面只占竖屏上方约八成，下方一条纯黑，交界线正中压一枚小品牌角标；B-roll 段恢复全屏。

- 怎么写：顶层 "badge_bar": {"text": 角标文字, "h": 0.82, "sub_y": 0.70, "ranges": [[t0, t1], ...]}；不写 ranges 就是所有口播全屏的时段
- 风格：premium
- 自动：口播全屏时段画面底部 18% 盖纯黑，交界线正中骑一枚米白描边小角标；B-roll 和整屏版式时段恢复全屏；字幕整片挪到人物胸前（不放进黑边）
- 变体：`badge` 口播上移底部留黑：人物只占上方八成，下面一条黑，交界线压品牌角标（premium）
- 示例：`{"badge_bar": {"text": "口播剪辑研究所"}}`

### `grain_vignette_bg` 深灰纸纹暗角底

中灰偏暗带细颗粒纸纹的平面，四周很重的黑色暗角，中心偏上最亮，用作纯文字页底。

- 怎么写：layout 写 {"mode": "bg", "bg": "grain"}（纯文字页底），或抠像换底 {"mode": "matte", "bg": "grain"}
- 风格：premium
- 自动：代码画：#4A4A4A 底加细颗粒纸纹，四周重暗角压到约 15% 亮度，最亮在 0.4 高
- 变体：`grain` 深灰纸纹暗角底：纯文字页用，比纯黑有质感（premium）
- 示例：`{"layout": [{"t0": 0.0, "t1": 3.6, "mode": "bg", "bg": "grain"}], "titles": [{"t0": 0.3, "t1": 3.5, "layout": "quote", "text": "慢一点，才能看清", "sfx": false}]}`

### `wave_lines_bg` 黑底动态波浪线

纯黑底铺满极细的深灰横向波浪线，像等高线一样缓慢流动，几乎察觉不到但让黑底不死板。

- 怎么写：layout 写 {"mode": "bg", "bg": "waves"}，或抠像换底、素材窗口（example_window 的 thin）的窗外
- 风格：premium
- 自动：黑底上 1 像素深灰正弦波浪线，行距 1.2% 画面高，整体每秒上移约 9 像素，像等高线慢慢流动
- 变体：`waves` 黑底动态波浪线：几乎察觉不到地流动，黑底不死板（premium）
- 示例：`{"layout": [{"t0": 0.0, "t1": 3.6, "mode": "matte", "bg": "waves"}]}`

### `perspective_floor_bg` 3D 透视空间底

点阵或网格平面被透视成向远处收窄的地面、上下对称的隧道或斜角走廊，营造科技空间纵深。

- 怎么写：layout 写 {"mode": "matte", "bg": "floor:<变体>"} 抠像人站在透视空间里，或 {"mode": "bg", "bg": "floor", "variant": ...}
- 风格：premium
- 自动：代码画网格平面，透视成往远处收窄的地面，远端渐隐到黑；地平线在画面中线，字放中间黑带
- 变体：`floor` 透视地面：下半屏白网格地面（premium）；`tunnel` 上下隧道：上下两片对称、中间留黑带（premium）；`corner` 斜角走廊：两片斜向楔形对称（premium）；`color` 彩色网格纹理：青色发光方格地面（premium）
- 示例：`{"layout": [{"t0": 0.0, "t1": 3.6, "mode": "bg", "bg": "floor", "variant": "floor"}], "titles": [{"t0": 0.3, "t1": 3.5, "layout": "quote", "text": "走进三维空间", "sfx": false}]}`

### `theme_video_dim_bg` 主题视频压暗做底

卡片和截图后面垫一段和话题相关的视频（会议、数据流、星空），压暗加虚化，一直在微动但不抢戏。

- 怎么写：broll 的 fit 为 double 或 band 时写 "bg": "video", "bg_src": 话题视频（星空、数据流、会议）
- 风格：premium
- 自动：话题视频循环铺满做底，压暗约三成、轻虚化、降饱和，一直在微动但不抢卡片
- 变体：`video` 主题视频压暗做底：卡片和截图后面垫一段相关视频（premium）
- 示例：`{"broll": [{"t0": 0.2, "t1": 3.5, "src": "A['shot']", "fit": "band", "bg": "video", "bg_src": "A['rec']"}]}`

### `block_wipe` 色块碎片擦屏

画面上随机冒出大小不一的矩形色块或碎片，几帧内铺满整屏，再从色块里露出下一画面或归位成新画面。

- 怎么写：transitions 写 {"t", "type": "blocks", "variant": random / bars, "colors": [...]}
- 风格：web
- 自动：random 橙红、深色矩形碎块 0.2 秒内随机铺满，切点后按随机顺序散掉露出下一段；bars 黑色竖条随机升起盖满再落下；配故障声
- 变体：`random` 随机色块铺满：矩形碎块铺满整屏，再散开露出下一画面（web）；`bars` 黑色竖条擦屏：竖条随机升起擦掉上一画面（web）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "blocks", "variant": "random"}]}`

### `tunnel_zoom` 隧道穿梭

画面中心出现放射状隧道或光柱，小窗画面从中心向镜头冲出来放大到满屏。

- 怎么写：transitions 写 {"t", "type": "tunnel", "color": "#1E6E8C"}；30 秒内最多一个，适合开场第一下或章节页进正片
- 风格：web
- 自动：切点前后中心放射青色光柱往外冲，下一段从画面中心 20% 冲到满屏；配穿梭声
- 变体：`tunnel` 隧道穿梭：光柱冲出来，小窗从中心向镜头冲到满屏（web）
- 示例：`{"broll": [{"t0": 1.8, "t1": 3.6, "src": "A['photo']", "fit": "cover", "sfx": false}], "transitions": [{"t": 1.8, "type": "tunnel"}]}`

### `frame_tilt` 画面歪头倾斜

整段口播画面 0.3 秒内旋转约 -10° 并略放大，像镜头歪头，讲完转回或直接切走。

- 怎么写：顶层 fx 写 {"t0", "t1", "type": "tilt", "angle": -10, "back": true}
- 风格：web、variety
- 自动：0.3 秒整屏（连字幕）转到 -10 度并放大到 1.1 倍免得露黑角，back 写了最后 0.3 秒转回来；配一声嗖
- 变体：`tilt` 画面歪头倾斜：像镜头歪一下头，讲完转回或直接切走（web、variety）
- 示例：`{"fx": [{"t0": 1.0, "t1": 2.6, "type": "tilt", "back": true}]}`

### `magnifier_zoom` 放大镜局部放大

一只手拿着放大镜从画面外伸进来，镜片里的画面（脸或关键词）放大约 1.5 倍，随后移开。

- 怎么写：顶层 fx 写 {"t0", "t1", "type": "magnifier", "variant": "reach", "at": [x, y], "from": [画外起点], "zoom": 1.5, "r": 0.2}
- 风格：web、variety
- 自动：镜片 0.5 秒从画外沿手柄方向滑到 at，镜片里放大 1.5 倍（裁切位置跟着镜片走、对得齐），长手柄一直伸到画外，最后 0.5 秒移走；配推近声
- 变体：`reach` 放大镜从画外伸进来：镜片里的脸或关键词放大，随后移开（web、variety）
- 示例：`{"fx": [{"t0": 0.4, "t1": 3.4, "type": "magnifier", "variant": "reach", "at": [0.5, 0.3]}]}`

### `music_humor_sting` 梗句幽默短乐句

说到调侃、反转的梗句时，配乐临时换成 2~4 秒俏皮的喜剧乐句，再回到主循环，替代一声「叮」。

- 怎么写：顶层 "stings": [{"t": 梗句开始, "src": 用户准备的喜剧短乐句, "in": 从第几秒截, "dur": 2~4}]；没有短乐句就别写，改用梗音效
- 风格：web、premium
- 自动：渲染前剪成短片段（前后 0.1 秒淡变）放进音效，这几秒主配乐让开；五分半的片子三四次就够，不是每个梗都要
- 变体：`sting` 梗句幽默短乐句：调侃、反转那句配乐临时换成两三秒俏皮乐句再回主循环（web、premium）
- 示例：`{"audio": {"voice": {"lufs": -16}, "bgm": [{"src": "A['bgm']", "t0": 0, "t1": 3.6}]}, "stings": [{"t": 1.0, "src": "A['hype']", "in": 20, "dur": 2.4}]}`

### `ai_micro_animation` AI 补一两秒小动画

原本需要 AE 才能做的一两秒小动画（爆炸、变形、转场插画），取一帧静态图交给图生视频模型生成 1~2 秒片段，当 B-roll 剪进去。

- 怎么写：broll 写生成好的片段 {"src": "ai/xxx.mp4", "ai": {"frame_at": 截帧秒数, "prompt": "…"}}；ai 只是记录来源，渲染照普通 B-roll 放
- 风格：web
- 自动：流程：截出关键帧 → 用 Renoise 的图生视频生成 2 秒（消耗额度，先给用户看预估花费，用户同意才生成）→ 截 1~1.5 秒当 B-roll；只补画面小片段，配乐不用 AI 生成
- 变体：`ai` AI 补一两秒小动画：原本要 AE 做的爆炸、变形、转场插画（web）

### `jianying_layer_tips` 剪映图层组织技巧

导出剪映草稿时的工程组织方法：每个包装打包成复合片段放在同一条包装轨；文字转复合片段后才能加视频特效、滤镜和蒙版；开自由层级把抠像层叠在文字上做人压字。

- 怎么写：build_draft.py 生成剪映草稿时按这个结构摆轨道，不用手写
- 风格：premium、web
- 自动：轨道从下到上：主轨口播 → B-roll → 调整图层 → 网点丝印 → 素材带 → 包装（复合片段）→ 头像 → 字幕；剪映里要人压字就开自由层级、口播复制一层做智能抠像、文字放两层之间；文字转复合片段后才能加特效滤镜蒙版，先定稿再打包
- 变体：`layers` 剪映图层组织：包装放同一条轨、文字转复合片段、自由层级夹字（premium、web）

### `teardown_audit` 拉片量化复盘

学习别人成片或自检自己成片时的量化方法：先在时间线上给每处包装打标记数数量，再按轨道统计口播、画中画、留白的时长占比，最后把人声分离掉单听配乐和音效找换段与留白。

- 怎么写：python scripts/teardown.py 成片.mp4 [--timeline timeline.json] [--music 配乐分轨.wav] [--separate]
- 风格：premium
- 自动：场景检测数包装点、给平均间隔；按 timeline 算口播全屏 / 画中画和整屏包装 / 气口留白的占比；配乐每 0.5 秒算响度找停顿和换段（装了 demucs 可先分离人声）
- 变体：`audit` 拉片量化复盘：标记包装点、镜头类型占比、分离人声单听配乐（premium）

## 还没实现

按落地批次陆续补齐；没实现的手法不要在 timeline 里写，也不要用别的手法冒充。

