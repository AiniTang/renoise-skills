# 版本说明

## rn 版（2026-10-17）

画面和混音仍由 Remotion 渲染；所有机械、易错的环节改由 [renoise-kit](https://github.com/renoise-ai/renoise-kit) 的 `rn` 命令完成，skill 本身只保留流程、判断和内容（风格包、组件、曲库、字体、文案检查、旁白、生图）。

### 换成 rn 的部分

| 原来 | 现在 | 变化 |
|---|---|---|
| `contact_sheet.py` | `rn sheet`（视频或静帧文件夹） | 按解码帧号取帧，不再按 `-ss` 时间戳；`--around 秒,... --span 4` 看切换点，`--diff` 看闪烁和跳帧 |
| `audit_av.py` | `rn qa` + `rn cuts --sheet` + `rn signal` | 数字静音、电平跳变、爆音阈值相同；黑帧 / 冻帧用 ffmpeg 检测；硬切用场景分数并列出待确认的 suspects |
| `deliver.py` | `rn finish` + `rn qa` | 同样修好 Remotion 直出的半时长、色彩范围、moov 位置；AAC 延迟改为从根上避开（画面 `--muted` 渲染 + 混音另渲 WAV + `rn finish --audio`）；4K 自动附 1080p（`--height 1080`） |
| `master_audio.py`、`check_audio.py` | `rn finish` / `rn qa` | 响度标准从 RMS −17 dBFS 改为 **−14 LUFS**，true peak 在 AAC **编码后**测（≤ −1 dBTP）；`LUFS=-16 render.sh …` 可改 |
| `detect_bpm.py` | `rn listen` | 给出 BPM 的半 / 倍速候选与强度、拍点时间、响度 |

### 新增

- **`qa-accept.txt`**（工程根目录）：审片后判断为有意为之的 WARN 写在这里（`检查项` 或 `检查项@秒`），之后的审计不再重复报；FAIL 不能豁免。
- **预览也是交付规格**：`preview` / `film-preview` 同样经过 `rn finish`，发给用户的预览不会再出现「只有一半时长」。
- `stills` / `film-stills` 自动拼出 `out/stills-sheet.jpg`。
- 审计结果统一在 `out/audit/`：`qa.json`、`cuts.json`、`cuts.jpg`。
- 可选：`rn compare` 对比新旧两版，`rn text` 读画面文字，`rn signal` 看逐帧亮度 / 频段 / 鼓点曲线。

### 依赖变化

- 新增：系统 ffmpeg（macOS 用 `ffmpeg-full`）和 `rn`（`uv tool install 'renoise-kit[all]'`）。`setup_project.sh` 缺了会提示，`render.sh` 缺 `rn` 时直接报错。
- 不再需要：`npx remotion ffmpeg` 兜底、numpy 版的审计 / 母带脚本。

### 已验证

在模板工程上实际跑过 `preview`、`final`、`film-stills`、`film-preview`、`film`。成片和 Remotion 单独渲出的 WAV 混音逐样本对齐（`rn align` 偏移 0.0000 s）；预览用 `--audio-offset -0.0437` 补偿后偏移 1 ms；成片 `fixed_frame_rate_flag=1`，`rn qa` 无 FAIL。

### 原样保留

`audio_features.py`（输出格式是 `AudioReactive.tsx` 的数据契约）、`pick_music.py` 与曲库、`fonts.py` / `font_check.py` / `typo_lint.py`、`check_storyboard.py`、旁白与生图脚本、全部 Remotion 模板与示例、全部参考文档的创作内容。
