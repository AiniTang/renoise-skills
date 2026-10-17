# AI 素材补充：用 Renoise 生成关键帧与视频

客户拍不到、官网也没有的画面——人、场景、生活——用生成素材补。**注意**：在图形化的品牌片里硬插一段生成的人物视频会显得突兀（YouWare 品牌片 60s v2 的反馈）；这类片子优先用品牌自己的图形语言讲「人」，生成素材更适合整片都是实景 / 三渲二叙事的片子，或做背景、材质、空镜。典型用途：品牌调性片里某段抽象动效「跳戏」「像别人家的片子」时，换成客户品牌画风里的真实人物（YouWare 品牌片 60s：字形解剖 + 引语一段被用户指出像别家，换成「手绘贝塞尔曲线 → 设计师倾听用户」两镜）。

生成走 **Renoise**：需要接入 Renoise 并登录（各 agent 的接入方式见 [renoise-plugins-official](https://github.com/renoise-ai/renoise-plugins-official) 的 README）。对话里所有生成都用 Renoise 的工具，**不要**在对话里用 `renoise task create` 等命令行路径提交付费任务（会绕过确认）。

## 流程

1. **画风来自客户自己的设计规范**：客户有画风 skill / 风格指南就把它的视觉支点写成英文风格块，所有镜头共用；没有就先按品牌色和 design-principles.md 写一版给用户确认。风格块和主体 / 动作 / 镜头分开写。
2. **选模型**：按 Renoise 的 model-routing skill 选图像和视频模型、写对应的提示词；可用模型和参数以 `list_models` 的实时结果为准，不要凭记忆写死。
3. **关键帧**：16:9、2K 左右。一次出 4–6 张给用户看，**先看图再花视频的钱**。
4. **动起来**：图生视频，以选中的关键帧为首帧（`save_result_as_material` 把结果存成素材后引用），1080p、5 s、关掉模型自带音频（配乐另有）。每镜 2 个运镜版本挑一个。需要落到指定画面（例如收成一个圆、对上粒子球）时再给尾帧。
5. **花钱前确认**：每一批先 `estimate_cost`，把数量、模型和估价一次说清，用户同意后才 `create_tasks`；`wait_tasks` 等结果，`download_results` 下载到工程的 `public/ai/`。任务 ID 记进 `gen/tasks.md`（镜头 → 模型 → 提示词 → 任务 ID），方便复用和追溯；中断后只重查任务，不重复提交。
6. **进片**：`<OffthreadVideo muted startFrom>` 放进 `<Sequence>`，剪辑点落在节拍上，外面加 1.02→1.055 的缓推；上一段用遮罩 / 色板滑走 / 圆形揭示露出视频（`drawPalette({ under: "none" })` 让色板滑走时透明）。字幕用品牌衬线字，亮画面上 ink + 纸色光晕。进片前用 `rn probe` / `rn sheet --fps 4` 看清帧数和可用段落，用 `{"frame": n}` 精确取入点。

## 提示词规则

- 每条都以风格块开头，结尾写死：**no text, letters, numbers, logos or readable UI; screens show only soft abstract colour cards**（生成模型写不好字，也不能伪造客户界面）。
- 人物多样：年龄、族裔、体型、轮椅使用者……每镜主色分给不同人，不要所有人穿品牌色。
- 视频提示词只写运动和镜头（slow push-in / lateral dolly / slow orbit + 人物的一个动作），并加「keep the exact look of the first frame, no cuts, no new objects」。
- 情绪：温暖、专注、被倾听；避免摆拍笑脸墙和「科技蓝」。

## 底线

- 生成的人物是示意角色，不是真实客户，不配真实姓名、数据或评价；交付说明里写明「部分画面由 AI 生成」。
- 不生成真人名人、竞品界面或他人商标。
- 生成是付费任务：先报数量和估价，用户同意再提交。内容审核拒绝时如实告诉用户并停下，不重试、不改写绕过。
