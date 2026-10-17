# 配乐

优先级：用户提供 > 内置曲库（`assets/music/`，默认）> 在线开源曲库补充 > `synth_bgm.py` 合成（兜底）。同一用户连续几支片不要用同一首歌、同一种曲风。

## 1. 内置曲库（默认）

`assets/music/` 有 27 首可免费商用、免署名的曲子（Mixkit Free License），按情绪分 10 组，`catalog.json` 记录每首的曲风、BPM、时长、能量档、**能量到达点**（音乐从铺垫进入主段落的秒数）和授权。

```bash
python3 <skill>/scripts/pick_music.py --list --style 暗场科技      # 按风格或 --mood 浏览
python3 <skill>/scripts/pick_music.py <项目>/public/music/bgm.wav \
  --mood tech-drive --seconds 45 --hit-at 3.9                                         # 自动选曲、裁剪、对齐
```

- 自动选最久没用过的一首（记录在 `~/.cache/promo-video/music-usage.json`）；想指定时用 `--track <文件名>`。
- `--hit-at`：主段落要落在成片的第几秒，通常是 Logo 出现或第一个大转场的时刻。脚本在能量到达点前后 0.5 秒找最强起音、吸附到那一帧，再反推切入点；给了 `--hit-at` 时优先挑真有前奏铺垫的曲子。
- 输出 48 kHz 立体声 WAV，自带淡入淡出，并在同目录写 `credit.txt`（曲名、作者、来源、授权），交付说明照抄即可。
- 精测结果在整数附近（如 119.3、127.8）时，按 6–10 秒分窗比较各候选速度的底鼓相位：相位最稳的那个就是真实速度，多半是整数；用 `--bpm 120` 强制，脚本只找拍头。
- **时间轴按曲子的 BPM 重排**：`BEAT = 30 * 60 / bpm`（123 BPM ≈ 14.63 帧），段落边界用 `Math.round(拍数 * BEAT)`。不要沿用 120 BPM 的 15 帧网格，一支 45 秒的片子会漂移一秒多。BPM 标 `~` 的可能是真实速度的两倍或一半，按听感取 80–160 之间的值。

| mood | 适合风格 | 代表曲 |
|---|---|---|
| `tech-drive` | 暗场科技、产品发布、动效作品集 | Techno Fest Vibes、Deep Urban（15 秒处进入主段落，长曲可切多段）、Minimal Techno 02 |
| `tech-dark` | 安全、硬核、悬念开场 | Cyberpunk City、Trap Electro Vibes、Sci-Fi Score |
| `corporate` | 浅色编辑、企业服务、讲解 | Motivating Mornings、Better Times are Coming、Close Up |
| `cinematic` | 品牌片、硬件发布、预告片 | Epical Drums 02、Driving Ambition、Discover（前奏极安静，13 秒爆发）|
| `calm` | 温馨暖色、东方星图、慢节奏回顾 | Vastness、Relaxation 05、Sleepy Cat |
| `upbeat` | 社媒广告、消费品、年轻品牌 | Gimme that Groove!、Midnight Funk、Take this Higher |
| `warm` | 生活方式、个人品牌 | Magical moment、Tears of Joy、Upbeat Jazz |
| `urban` | 社媒快剪、潮流 | Need for speed、Young Trizzy |
| `sports` / `world` | 运动集锦 / 文旅 | Sports Highlights / Games Worldbeat |

Mixkit 授权限制：可用于网络视频、社媒、线上广告；**不能**用于电视/电台广播、游戏，也不能把音乐单独再分发。交付广播用途的片子时改用 CC0 曲目或用户授权音乐。

## 2. 扩充曲库

内置曲库不够或需要特定曲风时，从这些来源补充，只选授权明确可商用的：

| 来源 | 授权 | 取法 |
|---|---|---|
| [Mixkit](https://mixkit.co/free-stock-music/) | Free License，免署名 | 分类页 `/free-stock-music/tag/<tag>/` 内嵌 JSON-LD（`MusicRecording`：曲名、作者、曲风、时长、`license`），mp3 在 `assets.mixkit.co/music/<id>/<id>.mp3`；只取 `license` 以 `#musicFree` 结尾的 |
| Free Music Archive 的 CC0 音乐人 | CC0 公有领域 | HoliznaCC0（lo-fi、合成器、游戏配乐）、Komiku（冒险、民谣感配乐）、Loyalty Freak Music（电子、放克）；逐首核对页面上的授权 |
| [Pixabay Music](https://pixabay.com/music/) | Pixabay License，免署名 | 需用户在浏览器下载 |
| [OpenGameArt](https://opengameart.org/) | 只选标注 CC0 的 | 循环乐段多，适合短片 |

新曲入库流程：下载到临时目录 → `rn listen <曲子> --json` 读 BPM（含半 / 倍速候选）、起音、响度曲线，`rn signal <曲子> --json` 读逐帧低 / 中 / 高频段与起音强度，由此算频谱重心、低频占比、起音密度、前 4 秒相对响度、能量到达点 → 按这些数字归到上表的 mood → 复制进 `assets/music/` 并追加到 `catalog.json`（字段与现有条目一致，`license` 与 `source` 必填）。我听不到声音，分类只能靠这些特征和曲名、曲风标签，入库后在交付说明里提醒用户试听。

## 3. 用户提供音乐

```bash
npx remotion ffmpeg -y -i /path/to/song.mp3 -ar 48000 -ac 2 public/music/bgm.wav
rn listen public/music/bgm.wav --json out/music.json                 # BPM（含半 / 倍速候选与强度）、拍点时间、响度
```

把检测到的 BPM 写入 `music.bpm`（模板片）或 Film 的 `BEAT`。前奏太长用 `music.startOffset` 或 `pick_music.py --track` 的同样思路手动切。

## 4. 合成（兜底）

没有网络、或用户要求零授权风险且曲库都不合适时才用：

```bash
python3 <skill>/scripts/synth_bgm.py <项目目录>/public/music/bgm.wav --seconds <秒数> --bpm 120 --mood tech [--intro-beats 8]
```

mood 有 `tech`、`upbeat`、`calm`、`cinematic`、`eastern`（五声音阶拨弦，国风品牌）。合成音色单一，连续多支片都用它会听起来雷同。

## 混音规则

- 剪辑点对齐到曲子的节拍；主段落落在 Logo 或第一个大转场上。
- 音乐淡入约 0.4 秒、淡出 1.2–1.5 秒；音效密集处 BGM 音量 0.3–0.5，其余 0.8 左右。
- 母带由 `render.sh` 里的 `rn finish` 统一做：−14 LUFS，**编码后**测 true peak ≤ −1 dBTP（AAC 会把峰值抬高 1–2 dB，超了自动降限幅重编音频）。要更响或更轻用 `LUFS=-13 render.sh …`；成片已出、只改响度时不重渲画面：`rn finish out/film.mp4 -o out/film-loud.mp4 --copy-video --lufs -12`。
- 有旁白时 BGM 压到约 0.22，旁白间隙回到 0.4。
- **转折处不落数字静音**：重排曲子时，硬停处不要直接把采样归零（会被听成故障）。做法：末尾 1.4 秒低通扫频 + 淡出，最后半秒送进暗房混响（`fft_conv`，RT ≈ 3.4 秒）做尾音，合成的低频床从尾音里 1.8 秒渐入，第一下心跳落在画面转折帧。不要取下一小节续尾（下一小节的第一拍常是满幅重击）。成片后看 `rn qa` 的 `dead_air` 是 PASS（`render.sh` 自动跑）。
