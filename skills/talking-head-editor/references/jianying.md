# 剪映草稿路线

```bash
pip install pyJianYingDraft    # 0.3 以上
python scripts/build_draft.py timeline.json --name "草稿名" [--draft-root 剪映草稿目录]
```

## 什么时候走这条路

- 用户想自己在剪映里微调；
- 综艺感风格（人脸特效、花字、综艺文字模板、剪映音效库都只在剪映里有）；
- 用户习惯用剪映导出、发布。

## 草稿目录

| 系统 | 默认位置 |
|---|---|
| macOS 剪映专业版 | `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft` |
| Windows 剪映专业版 | `C:/Users/<用户名>/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft` |

不确定时让用户在剪映「全局设置 → 草稿位置」里看。生成后在剪映首页找到草稿打开，看不到就重启剪映。

## 草稿里哪些能改，哪些是成片画面

剪映能原样搭出来的用剪映自己的轨道：口播（含推近）、口播全屏、圆形小窗、截图卡片（aside 单张）、B-roll、普通大字、字幕、配乐、音效，打开就能改。

剪映做不出来的段落，草稿最上面一条视频轨「成片画面」铺的是成片切下来的画面：抠像换背景、纸页、目录、画框、圆形缩放、四角卡片、网格底、截图叠放、尾帧这些版式，带色块、手绘、压暗或人压字的大字，数字滚动，开场冲击。和这些段落重叠的大字整条一起算进成片画面，不再另放剪映文字，免得叠两层。这一版成片不压字幕（`render.py --no-subs`，build_draft 自动渲到 `out/draft_assets/clean.mp4`），字幕在这些段落照样是剪映文字，能改错字。用户想自己重做某段，删掉那段成片画面，底下的口播和素材还在。

时间线改过之后重新跑 build_draft，会自动重渲这版成片；也可以用 `--film` 指定一份已经渲好的不压字幕成片。

## 版本差异与已知坑

- **剪映 Mac 11.x 读 `draft_info.json`**，pyJianYingDraft 写的是 `draft_content.json`，build_draft.py 已经自动复制一份。
- **草稿引用素材的绝对路径**：素材都放在项目目录（build_draft 会把预处理过的 B-roll、小窗复制到 `out/draft_assets/`），之后不要挪动项目目录。
- **剪映 7 及以上（含 Mac 版）不能自动导出成片**：告诉用户打开草稿后自己点「导出」。需要成片就同时用 render.py 出一份。
- **新版剪映自己存的草稿往往是加密的**，pyJianYingDraft 读不了；但同一个草稿文件夹下 `Timelines/<id>/template.json` 或 `template.json.bak` 常常是明文，可以从里面查到用户常用的花字、贴纸、特效的编号。
- 剪映打开草稿时会自动下载没缓存的特效、动画、花字，网络不好会显示「加载失败」，让用户重开一次。

## 坐标和尺寸换算

build_draft.py 已经处理好，自己改草稿时参考：

| timeline | 剪映 |
|---|---|
| 位置 x（0~1，左到右） | transform_x = (x - 0.5) × 2 |
| 位置 y（0~1，上到下） | transform_y = (0.5 - y) × 2（向上为正，单位是半个画布高） |
| 字号（1080 宽画布上的像素字高） | 剪映字号 ≈ 像素 ÷ 6.1 |
| 素材缩放 | 剪映默认把素材完整放进画布，再乘 scale |

## 时间线字段在草稿里怎么落

| timeline | 草稿里 |
|---|---|
| zoom | 口播片段的缩放和位置关键帧（以人脸为中心放大） |
| layout aside | 口播片段移出画面 + 背景填充「模糊」 |
| layout hidden | 口播片段移出画面 + 背景填充黑色 |
| layout pip | 预先导出的圆形小窗视频（带透明通道），放在「人像小窗」轨 |
| broll | 与成片同一批预处理素材，入场动画映射为剪映的渐显、向上滑动、向左滑动 |
| subs | 字幕轨，关键词分段上色；key 级别加「弹入」动画；`jy_flower` 加花字 |
| titles | 大字轨（重叠的自动分轨）。排版模板拆成几段文字：章节号、英文小标、主标题、说明、引号；字体按角色换成剪映自带的相近字体（关键词大字用优设标题黑，书法用毛笔行楷，手写批注用飞扬行书，金句用思源粗宋，英文用 Anton、Playfair Display 斜体）；动画映射为弹入、渐显、向上滑动、打字机。章节页的整屏压暗不进草稿，需要时在剪映里加一层黑色背景调透明度 |
| effects | 剪映特效轨（人物特效、画面特效） |
| stickers | 剪映贴纸 |
| overlays | 视频轨叠加 |
| audio | 口播音量按目标响度换算（降噪、去齿音、压缩只在成片里有，剪映里用「降噪」「人声美化」）；配乐按段落排好的段放进 BGM 轨，换曲交叉淡化重叠时分两条轨，配乐自动循环；音效分轨。开头高一档、留白、重音前压低这几样音量变化只在成片里有，草稿里要在剪映给配乐打音量关键帧；升调串的音高要在剪映里手调变调 |
| behind 大字和抠像版式 | 大字照常生成，抠像不进草稿：在剪映里把口播这一段复制一层放上面、开「智能抠像」，大字放在两层之间（开启自由层级）；matte、corner、breakout 版式这几秒是原口播画面，按 references/library.md 里各手法的剪映做法补 |

## 剪映素材编号

`assets/jianying_resources.json` 里有常用花字（黄色条纹花字、立体渐变浅黄花字、红色渐变裂痕综艺花字等）和贴纸的编号；人物特效、画面特效、文字动画、视频动画、转场、字体用 pyJianYingDraft 自带的枚举（`VideoCharacterEffectType`、`VideoSceneEffectType`、`TextIntro`、`IntroType`、`TransitionType`、`FontType`），名字就是剪映界面上的中文名。

想用用户自己常用的花字或贴纸：让用户在剪映里随便建个草稿用上它，然后从草稿的明文 JSON 里取 `resource_id`（`pyJianYingDraft.DraftFolder(...).inspect_material(草稿名)` 也能列出来）。

这些剪映素材只在剪映里生效，也只适合用户自己用；分享给别人的成片，用代码路线的样式近似。
