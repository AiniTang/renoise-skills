# 登记主播

主播形象不随 skill 分发。每个工程的主播登记在 `brief.json` 的 `hosts` 里，build_tasks.py 按它写提示词：

```json
"hosts": {
  "a": { "ref": "material:<id>", "who": "young woman", "framing": "selfie", "ratio": "9:16",
         "voice": "young friendly female voice, clear and patient but lively, natural pace" },
  "b": { "ref": "task:<id>", "who": "man", "framing": "studio", "ratio": "16:9",
         "voice": "warm, steady, confident male voice around 35 years old, natural pace" }
}
```
- `framing`：`selfie`（手机前置自拍感，适合竖屏口播）/ `studio`（固定机位棚拍，适合横屏讲解），对应 persona.json 的两套提示词。
- `who` 写进提示词，动物主播写清物种（见 persona.json 的 animal_note）。
- 同一个用户换了对话还想用同一个主播：问他上次的 material id，或用 search_media 找。

## 用户本人（或明确同意的人）的照片
1. 只用本人或明确同意的人的照片，不用公众人物和名人。
2. 照片要求：正脸、光线均匀、头发不挡脸、嘴闭着；竖屏照出竖屏口播，横屏照出横屏口播（不用再裁）。从视频里取帧时挑嘴闭着的一帧。
3. 上传：request_upload（或在 shell 里 upload_files）→ 拿到 `material:<id>`，写进 hosts。

## AI 生成的主播
1. 按 model-routing 选图片模型，先报价再生成：描述人物外形、服装、背景和构图（竖屏自拍 / 横屏棚拍），正脸、闭嘴、头发不挡脸，不出现任何文字；不要像任何真实存在的人。
2. 出 2–4 张给用户挑，选中的那张的 `task:<id>` 写进 hosts。
3. 想让后面换场景、换角度时形象更稳：再做一张四视图（同一个人、同一套衣服发型，正面 / 左侧 / 右侧 / 背面并排，浅灰无缝背景），放进 hosts 的备注。

## 先试拍再批量
同一句 8 秒台词先拍一段（报价、确认后）给用户看：脸像不像、口型对不对、动作自不自然、声音喜不喜欢。用户想比较模型时，可以同一张图、同一句台词再拍一个首帧模式更便宜的模型（按 model-routing 选），两版并排看。满意了再按 SKILL.md 第 2 步批量。
