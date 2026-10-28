# 08 · 两档制作：基础档（画面 0 积分）/ 增强档（按镜头挑）

原则：**能用代码做的都用代码做，Renoise 只补代码做不好的镜头**。两档的配音都在 Renoise 生成（15-voice.md；用户有自己的 MiMo 密钥时也可以走 MiMo）。
每期在确认 1（选题）时就问清楚做哪一档；增强档在确认 2 之前列出「增强镜头清单 + estimate_cost 报价」。

## 基础档 · 画面 0 积分

| 层 | 用什么 |
|---|---|
| 旁白 | Renoise 语音模型（用户本人或授权的音色参照，或按描述配）+ 可选 voice_post.py 人声后期（15-voice.md） |
| 画面主体 | **Opus 直接写 SVG 插画**（扁平矢量人物 / 建筑 / 器物 / 地图轮廓），用 `layers` 分远中近三层做视差推移；cine 的粒子、3D 镜头、着色器（Particles、Tunnel、Liquid…）做抽象概念 |
| 数据与信息 | know.js：counter、bars、spread、trail、vquote、keyword、chapter、foot |
| 配乐 | **默认 BGM**（工作区 `cine/music/vibe-bgm.m4a`，两档通用）：`python3 cine/tools/fit_bgm.py lessons/<期号>/assets/audio/bgm.wav --lesson lessons/<期号>` 按片长按小节裁剪；film.js 不放也会自动补，音量按人声校准（下面「默认 BGM」）。换曲：用户给的曲子写成 `bgm: true` 的 music 条目；或 cine 的 bed.py 按 sections 合成 |
| 音效 | cine 内置（slam whoosh riser impact chime tick shutter card …，写进 sfx） |
| 素材 | 公有领域 / CC 素材（Wikimedia Commons 古画、古籍书影、NASA 图）可以用，署名写进片尾和 facts.md；不用来路不明的图 |

**基础档怎么做到精品**：
- 每个场景至少三层 SVG（远景剪影、中景主体、前景遮挡物），推移时有景深。
- 人物用「几何化无五官」造型，画得稳、整期统一，也没有肖像风险。
- 每章一个「代码王炸」镜头：粒子聚字、光点变形、地图扩散、3D 镜头穿梭，代替增强档的动态镜头。
- 色板严格按视觉系统（03-visual-systems.md），颗粒和暗角统一由 `bg()` 控制。

## 增强档 · 按镜头挑，花费可控

**判断哪些镜头值得用 Renoise**（满足任意一条）：
1. 写实场景代码画不出来：历史现场、自然现象（雷暴、洪水、星云）、真实材质（青铜、丝绸、古籍纸纹）。
2. 全片最需要被记住的 1–3 个时刻：冷开场、反转、高潮。
3. 需要真实运动：人群、水流、火、机械运转。

其余镜头（数据、地图、文字、图表、抽象概念、示意动画）**仍用代码**。

| 增强等级 | 内容 |
|---|---|
| 轻 | 3–8 张关键配图（MJ）+ 2–5 个音效（配乐用默认 BGM，不再生成） |
| 标准 | 6–10 张配图 + 2 个动态镜头（720p 8s，首帧用配图）+ 6 个音效 |
| 旗舰 | 10–14 张配图 + 3 个动态镜头 + 1 个高难动态镜头（高潮）+ 8 个音效 |

每一档的价格按当期清单用 estimate_cost 实时报（模型和价格会变，不要凭记忆报）。
每次生成前照常报价、等用户确认；生成的图和视频优先放在已经用代码搭好的镜头里「替换底图」，不改镜头结构，这样增强档和基础档可以共用同一份 film.js（`const ENH = true` 时用 plate/vclip，否则用 layers）。

## 一份 film.js 两档通用的写法

```js
const ENH = false;   // 增强档改成 true（assets/ 里有对应文件）
const scene01 = (s) => ENH
  ? plate(s, { src: A("img/a01.jpg") })                                   // Renoise 配图
  : layers(s, [{ svg: SVG_SKY, depth: 0.15 }, { svg: SVG_PALACE, depth: 0.5 }, { svg: SVG_FG, depth: 1 }]);   // Opus 手画三层
// render 里两者的 update 签名一样：x.update(t, t0, t1, { … })
```

## 默认 BGM

工作区的 `vk.json` 管 BGM：`{"bgm": "cine/music/vibe-bgm.m4a", "force_bgm": true, "voice_gap_db": 10}`。
- 默认每期都有这首 BGM（112.9 BPM，160 秒，节拍网格在同名 .json）。film.js 没放，finish 时按片长自动补上；其他 ≥20 秒的整段配乐停用（每期只留一首）。
- 音量统一：说话时 BGM 比人声低 `voice_gap_db` dB，停顿处自动抬起约 3–7 dB；film.js 里 gain_curve 只管起伏形状。
- 想卡点：`fit_bgm.py` 同时写 `bgm.beats.json`（成片里每一拍 / 每一小节的秒数），film.js 读它。
- 换曲：用户给的曲子在 film.js 里写 `music.push({ src: P("audio/xxx.wav"), …, bgm: true })`，这期的 BGM 就是它（同目录有节拍 .json 时按小节裁，没有就整首截取 / 循环）。
- 不要 BGM：这一期 `export const meta = { …, bgm: false }`；整个工作区 `vk.json` 写 `"force_bgm": false`。
