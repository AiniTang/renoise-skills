# Renoise Skills

[English](README.md) · **简体中文**

用 AI agent 做视频的生产级 skill，遵循开放的 [Agent Skills](https://agentskills.io) 标准。每个 skill 是一个文件夹，里面有 `SKILL.md`，以及它用到的参考文档、脚本和模板。同一个 skill 在 Claude Code、Codex、Cursor、Gemini CLI，以及任何支持 Agent Skills 的 agent 里都能用。

| Skill | 能做什么 |
|---|---|
| [`promo-video`](skills/promo-video/SKILL.md) | 用 Remotion 渲染产品片、品牌片和发布片。模板片由分镜驱动；电影级片子加上 3D、真实产品界面演示、动效设计和卡拍配乐。也能做作品合集和单形状 UI 动效循环片。交给客户前，会先过一遍细节审片和交付检查。 |

## 安装

[`skills`](https://github.com/vercel-labs/skills) 安装器会把 skill 放到每个 agent 读取的位置：本体只在标准目录 `.agents/skills/` 里放一份，对于读取自己专属目录的 agent（Claude Code 读 `.claude/skills/`），再建一个链接指过去。

```sh
npx skills add renoise-ai/renoise-skills                                   # 交互式选择 skill 和 agent
npx skills add renoise-ai/renoise-skills -s promo-video -a claude-code -a codex -y
npx skills add renoise-ai/renoise-skills -s promo-video -g -y              # 装到用户级，而不是当前项目
```

也可以手动安装，把 `skills/promo-video/` 复制到 agent 的 skill 目录：

- Codex 等遵循标准的 agent：项目里的 `.agents/skills/`，或 `~/.agents/skills/`。
- Claude Code：项目里的 `.claude/skills/`，或 `~/.claude/skills/`。

## promo-video 的运行依赖

- **Node.js 18+**：Remotion 负责渲染画面和混音。找不到 Node 时，`setup_project.sh` 会下载一个便携版。
- **ffmpeg 7+**（需要带 libass）：
  - macOS：`brew install ffmpeg-full && export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"`
  - Debian / Ubuntu：`apt install ffmpeg`
- **[`rn`](https://github.com/renoise-ai/renoise-kit)**：负责每次渲染之后的编码收尾、交付检查和审计。用 `uv tool install 'renoise-kit[all]'` 或 `pipx install 'renoise-kit[all]'` 安装。
- **Python 3 和 numpy**：skill 自带的脚本要用。
- **可选：生成 AI 素材**。生成关键帧和图生视频需要接入 [Renoise](https://renoise.ai)，各 agent 的接入方式见 [renoise-plugins-official](https://github.com/renoise-ai/renoise-plugins-official)。

音乐文件不随仓库分发。skill 里的曲库目录记录了每首 Mixkit 曲子的下载地址和校验值，`pick_music.py` 第一次用到某首时再下载；字体也是同样的处理方式。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 目录结构

```text
skills/
  promo-video/
    SKILL.md         agent 加载的主说明
    references/      按需阅读的参考：风格、运镜、字体、配乐、细节审片……
    scripts/         建工程、渲染、选曲、字体、文字检查、旁白
    templates/       Remotion 工程模板和示例片
    assets/          音效，以及曲库目录和字体目录
```

## 许可

[MIT](LICENSE)。第三方内容，以及哪些内容是按需下载、不随仓库分发的，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
