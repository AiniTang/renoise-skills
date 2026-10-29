# 15 · 配音

节奏是硬要求（02-premium.md）：成片 5.5–6 字/秒，句间停顿 ≤0.35 秒，拍间 0.2 秒。先出开场试听让用户定音色和语速，再配全片。

## 默认：Renoise 语音模型

1. **音色**：narration.json 的 `voice`：
   - `speaker`：说话人（年龄、气质、口吻），没有音色参照时按它配。
   - `ref`：音色参照，只用用户本人或明确授权的声音。用户给录音时：12–20 秒干净朗读（安静房间、离嘴 20 厘米），用 request_upload / upload_files 传成 Renoise 素材，写 `material:<id>`。不模仿任何真实博主、名人的声音。
   - `style`：语气（科技博主快节奏、悬念感、不要播音腔……），会写进提示词。
   - `lexicon`：专名读音（「AI」→「A I」），只在回读真读错了时加。
2. **切 take**：`python3 scripts/voice.py plan <期号>`。按拍切成几条 take（每条 ≤100 秒，切在拍与拍之间），写 `build/voice_plan.json`，打印每条的提示词、预估时长和时长上限（多留 25%，念完剩下的是静音，对齐时会裁掉）。
3. **试听**：先只生成第一条 take 的前两三拍（或整条第一条，做 2 版）给用户听，定音色和语速；语速不对就调 `style` 或 `--cps` 重出。
4. **报价、确认、生成**：模型用 `seed-audio-1.0`（限制以 list_models 为准）：plan 写的提示词是它的写法，按 speaker 描述设计音色、用说明控制语速停顿，也能吃 `ref` 克隆。model-routing 把纯念稿交给 TTS 模型，但那类模型只有预设音色、提示词里的说明可能被念出来，这里不换。每条 take 一个任务：提示词用 plan 打印的原文，有 `ref` 时作为 reference_audio。全部列进报价（提示词、模型、参照、数量、estimate_cost 总价、余额），用户在对话里明确同意才 create_tasks；wait_tasks → download_results。
5. **对齐**：`python3 scripts/voice.py align <期号> <take1> [<take2> …]`（按 plan 的顺序）。faster-whisper 逐块转写 → 按字和旁白对齐 → 切出每拍 → `build/audio/<拍>.wav`、`build/narration.wav`、`build/timings.json`。打印每拍的语速、对齐率和听写稿。
6. **挑 take / 重配**：
   - 读听写稿对原文：漏字、多字、重复、读错专名、念了提示词 → 这条重新生成（新报价）。
   - 对齐率 <85% 先听：古文、专名多的拍，听写稿会把「凌人」写成「零人」，但录音本身没错——没念错就不用重配，对不上的字按前后已知字的时间插值。
   - 整条对齐率 <60%：多半念串了段落或语言不对，重新生成。
7. **收尾**：`check_timings.py <期号>`（对齐有没有断）→ 需要时 `speed.py <期号> 1.1`（音调不变，目标 5.5–6 字/秒）→ 可选 `voice_post.py <期号>`（人声后期：加厚、去闷、压缩）。

## 可选：小米 MiMo

用户自己有 MiMo 密钥、想用 MiMo 时：`voice.engine` 写 `"mimo"`，密钥只放环境变量（`MIMO_API_KEY`、可选 `MIMO_BASE_URL`），不写进任何文件；`voice.ref` 写本地参照 wav 路径（相对期目录）就走克隆，否则用预设音色 `voice.mimo_voice`（默认「茉莉」）。

```bash
python3 scripts/voice.py mimo <期号> --jobs 2      # 每拍单独合成，再用同样的 faster-whisper 对齐，产物和 Renoise 路线一样
```

MiMo 不走 Renoise，不花 Renoise 积分；用量和费用以用户自己的 MiMo 账号为准。

## 写稿时就避开的对齐坑

- 同一拍里重复出现的短语（「二之日 / 三之日」各两次）会让对齐跳到错的那一处：改写成不重复的说法。
- 英文名不带连字符；数字写成要念的样子（「三百七十」而不是「370」，除非就是要念「三七零」）。
- `[[cue]]` 放在要落点的字前面；不能叫 `end`。
