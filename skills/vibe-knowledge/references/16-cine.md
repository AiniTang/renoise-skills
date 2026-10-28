# 16 · 代码成片引擎（cine）

每一帧都是代码算出来的（DOM 大字、SVG 插画、Three.js / GLSL、粒子、镜头运动）：一期片子就是一个 `seek(t)`，同一个 t 渲两次 0 像素差。引擎在 skill 的 `engine/`，`new_film.py` 把它拷进工作区的 `cine/`（每次都同步到 skill 当前版本，不要在工作区里改引擎）。

## 目录

```
<工作区>/
  vk.json                 设置：默认 BGM、是否强制、人声比（bgm_mix.py 读）、系列名
  cine/
    index.html            ?lesson=<期号> 打开一期；&capture 是录制模式
    engine/               core.js（时间轴、镜头调度、__film 接口）narr.js（旁白时间、字幕）ui.js util.js post.js glsl.js
                          know.js（知识片组件，07-kit.md）
    engine/scenes/        particles clock bars showroom liquid tunnel
    tools/                stills record finish clips retail（render.py 调用）browser.py bgm_mix.py fit_bgm.py earshot_render.py
    audio/tools/          bed.py（合成背景乐 + 音效）score.py（合成和 DSP 库）
    audio/sfx/            CC0 真实按键录音（key 音效）
    music/                默认 BGM vibe-bgm.m4a + 节拍数据 vibe-bgm.json
    fonts/ vendor/        字体（scripts/fonts.py 下载）、three.js
  lessons/<期号>/          narration.json film.js facts.md assets.json assets/ build/ stills/
  styles/                 用户自己的风格（09-style-studio.md）
  out/                    交付：<期号>_<片名>.mp4 / .jpg
```

## 环境

- Python 3.8+，装 `numpy scipy pillow playwright`（`python -m playwright install chromium`），ffmpeg、ffprobe。配音对齐要 `faster-whisper`。`scripts/doctor.py` 逐项查。
- 无头浏览器：macOS 走 Metal；Linux / Windows 没有 GPU 时走 SwiftShader 软件渲染（结果一样，慢几倍）。`CINE_CHROME` 可以指定浏览器。
- 页面要用 HTTP 打开（ES module 不能 file://）：`render.py` 每次自己起一个本地服务器，用完就关。

## film.js 契约

```js
import { clamp, lerp, eOutCubic, spring, el, css } from "../../cine/engine/util.js";
import { C, appear, slam, typeText, codeCard, sourceTag, pauseCard, recapMap, clipBox } from "../../cine/engine/ui.js";
import { TH, bg, layers, plate, keyword, counter } from "../../cine/engine/know.js";

export const COLD = 0;                           // 片头冷开场长度（旁白整体往后挪这么多秒）
export const TAIL = 2.5;                         // 旁白结束后停几秒（尾卡）
export const meta = { title: "本福特定律", n: "05" };   // meta.bgm = false：这一期不要 BGM
export let hits = [], blur = [], clips = [], music = [];
export const sfx = [], sections = [];

export async function build(ctx) {
  const T = (s) => ctx.narr.t(s);                // "B07" "B07.ring" "B03@三千" "B07.end" "B05+1.2"
  return [{ from: 0, to: T("B03"), build(root) { … }, render(t, u) { … } }, …];
}
```

- 镜头 `{ from, to, build(root), render(t, u) }`：build 只建一次 DOM / 场景，render 按绝对时间 t 摆状态，**不能依赖上一帧**（录制会跳着 seek）。
- `hits`：镜头冲击（曝光提升 + 极短闪白 + 位移），全片 ≤3 个；有片段在画面里时不用。
- `blur`：`[起, 止]` 秒段，录制时 4 个子帧平均做运动模糊。
- `sfx`：引擎合成音效 `{ t, type }`，类型 slam whoosh whoosh-through riser(t_to) impact blip click tick shutter snap chime error card rewind key。用了 earshot 就别再写同一角色的 sfx（10-earshot.md）。
- `sections`：合成背景乐段落 `{ t, t_to, level }`；有默认 BGM 时写一段 level 0。
- `clips`：真片段 `{ id, src, from, at, dur, x, y, w, h, audio: mute|duck|full, gain, fade }`，clips.py 裁好，finish.py 叠在框上。
- `music`：`{ src, from, at, dur, gain | gain_curve: [[t, dB]…], fade_in, fade_out, duck }`。src 写相对工作区的路径（`P("audio/bgm.wav")`）或 `earshot:<编号>`；BGM 条目的音量由 bgm_mix.py 按人声校准，曲线只管起伏；写 `bgm: true` 的条目是这期换的曲。
- 组件：know.js（07-kit.md）；ui.js 的 appear slam typeText codeCard quoteCard sourceTag pauseCard recapMap clipBox；scenes/ 的 Particles Clock Bars Showroom Liquid Tunnel（参数见各文件末尾注释）。

## 流水线

```bash
python3 scripts/render.py stills <期号> lessons/<期号>/stills/sheet.png 1 B01+1 B02.title B05.count+0.5   # 接触表，逐张看
python3 scripts/render.py film <期号> --title 片名 --poster 12    # clips → record → finish → deliver，串行
python3 scripts/render.py audio <期号>                           # 只改了音效 / BGM：只重做混音
python3 scripts/render.py retail <期号> B18                      # 只改了结尾几拍：从 B18 起重录，接回 picture.mp4
```

- record：1920×1080 60fps 逐帧 seek + 截图，管道给 ffmpeg（CRF 18）→ `build/picture.mp4`。
- finish：读 `__film` → bed.py 合成音效 → earshot 音效 → 默认 BGM（bgm_mix.py）→ 旁白压低背景乐 → 叠片段 → 限幅（留 1.5 dB）→ `build/lesson<期号>.mp4`。
- deliver：`out/<期号>_<片名>.mp4`（CRF 23、码率封顶 6M）+ 封面帧。之后按 05-publish.md 用 cover_first.py 把封面接成开头帧。
- 同一工作区同一时间只能有一个 film 渲染（锁文件 `cine/.render.lock`）。

## 坑

- `[[cue]]` 只用小写字母、数字、下划线；不能叫 `end`（`B06.end` 是保留写法）。
- 旁白里的英文名别带连字符（「promo-video」会让逐字对齐从那里断），写「promo video」；配音后跑 `check_timings.py`。
- `appear()` 不能改 display（会冲掉 flex 居中），用 visibility；字幕别在「5.5」小数点处断句。
- 片段永远在最上层、不跟 hits 抖；字、箭头不能压在片段框上；框不能进 y>920（字幕区）；w、h 用偶数。
- 粒子：curl 噪声频率太低整团会漂成怪圈；闪白压在暗画面上发灰，冲击用曝光提升 + 极短闪白。
- 60fps + 粒子 / 颗粒码率很高：交付封顶码率，母版别用 CRF 16。
- 接触表要看动画**中途**的帧，静止帧会漏掉重影、残留。
