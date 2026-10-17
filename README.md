# Renoise Skills

**English** · [简体中文](README.zh-CN.md)

Production-grade skills for making videos with an AI agent, written to the open
[Agent Skills](https://agentskills.io) standard. Each skill is a folder with a `SKILL.md`, its references, scripts and
templates. The same skill works in Claude Code, Codex, Cursor, Gemini CLI and any other agent that reads Agent Skills.

| Skill | What it makes |
|---|---|
| [`promo-video`](skills/promo-video/SKILL.md) | Product, brand and launch films rendered with Remotion: the template mode is driven by a storyboard, the cinematic mode adds 3D, real product UI demos, motion design and beat-matched music. It also makes showreels and one-shape UI loops. A detail pass and delivery checks run before anything goes to the client. |

## Install

The [`skills`](https://github.com/vercel-labs/skills) installer puts a skill where each agent looks for it. It keeps one
copy in the standard `.agents/skills/` folder and links it for agents that read their own folder (Claude Code reads
`.claude/skills/`).

```sh
npx skills add renoise-ai/renoise-skills                                   # pick skills and agents interactively
npx skills add renoise-ai/renoise-skills -s promo-video -a claude-code -a codex -y
npx skills add renoise-ai/renoise-skills -s promo-video -g -y              # user-level instead of this project
```

To install by hand, copy `skills/promo-video/` into your agent's skills folder:

- Codex and other agents that follow the standard: `.agents/skills/` in the project, or `~/.agents/skills/`.
- Claude Code: `.claude/skills/` in the project, or `~/.claude/skills/`.

## What promo-video needs

- **Node.js 18+**: Remotion draws the picture and the mix. `setup_project.sh` downloads a portable Node when none is
  found.
- **ffmpeg 7+** with libass:
  - macOS: `brew install ffmpeg-full && export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"`
  - Debian/Ubuntu: `apt install ffmpeg`
- **[`rn`](https://github.com/renoise-ai/renoise-kit)**: finishes, checks and audits every render.
  Install it with `uv tool install 'renoise-kit[all]'` or `pipx install 'renoise-kit[all]'`.
- **Python 3 with numpy**, for the skill's own scripts.
- **Optional, AI footage**: a [Renoise](https://renoise.ai) connection for keyframes and image-to-video. See
  [renoise-plugins-official](https://github.com/renoise-ai/renoise-plugins-official) for how each agent connects.

Music is not shipped. The skill's catalogue lists Mixkit tracks with their URL and checksum, and `pick_music.py`
downloads a track on first use. Fonts are fetched the same way. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Layout

```text
skills/
  promo-video/
    SKILL.md         instructions the agent loads
    references/      read on demand: styles, camera, typography, music, detail pass, ...
    scripts/         setup, render, music, fonts, text checks, narration
    templates/       the Remotion project and example films
    assets/          sound effects, music and font catalogues
```

## License

[MIT](LICENSE). Third-party content and what is fetched instead of shipped:
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
