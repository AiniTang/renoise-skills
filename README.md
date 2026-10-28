# Renoise Skills

**English** · [简体中文](README.zh-CN.md)

Production-grade skills for making videos with an AI agent, written to the open
[Agent Skills](https://agentskills.io) standard. Each skill is a folder with a `SKILL.md`, its references, scripts and
templates. The same skill works in Claude Code, Codex, Cursor, Gemini CLI and any other agent that reads Agent Skills.

| Skill | What it makes |
|---|---|
| [`promo-video`](skills/promo-video/SKILL.md) | Product, brand and launch films rendered with Remotion: the template mode is driven by a storyboard, the cinematic mode adds 3D, real product UI demos, motion design and beat-matched music. It also makes showreels and one-shape UI loops. A detail pass and delivery checks run before anything goes to the client. |
| [`digital-human-koubo`](skills/digital-human-koubo/SKILL.md) | Talking-head videos with a digital presenter: the user's own photo or an AI-generated host speaks a script cut into 15-second takes generated on Renoise (quoted and confirmed first), checked by ear with faster-whisper, aligned word by word and edited with Remotion in one of four styles (vertical caption-heavy, launch explainer, step-by-step tutorial, multi-host multilingual) with 47 packaging components. Adapted from [andyhuo520/digital-human-koubo](https://github.com/andyhuo520/digital-human-koubo) (MIT). |
| [`pixel-breakdown`](skills/pixel-breakdown/SKILL.md) | Pixel-art breakdown episodes (16:9, 60–90 s) of a viral clip and its AI remake: the two side by side in sync, a pixel diagram of measured cuts and transitions, a simulated agent chat with a quote card and live progress, the result and an outro. Voice takes and music are generated on Renoise (quoted and confirmed first), aligned word by word with faster-whisper; every frame is drawn by a deterministic canvas engine in headless Chromium, with chiptune sound design and a 3:4 cover. |
| [`vibe-knowledge`](skills/vibe-knowledge/SKILL.md) | Narrated knowledge shorts (45 s – 5 min, 16:9) where every claim on screen has a source: six script templates reverse-engineered from viral explainers, a fact sheet, a voiceover generated on Renoise (quoted and confirmed first) and aligned word by word with faster-whisper, then 44 visual styles in eight families drawn frame by frame by a code engine in headless Chromium (hand-written SVG layers, particles, data widgets, a default music bed and code-generated sound effects). An enhanced tier adds Renoise stills, image-to-video shots and sound effects only where code falls short. OCR read-back checks the text against the fact sheet. |

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

It runs on macOS, Linux and Windows: the skill's scripts are Python, with no bash needed. On Windows, call `python`
(or `py -3`) where the skill says `python3`.

- **Node.js 18+**: Remotion draws the picture and the mix. `setup_project.py` downloads a portable Node when none is
  found.
- **ffmpeg 7+** with libass:
  - macOS: `brew install ffmpeg-full && export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"`
  - Debian/Ubuntu: `apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` (the full build), then open a new terminal
- **[`rn`](https://github.com/renoise-ai/renoise-kit)**: finishes, checks and audits every render.
  Install it with `uv tool install "renoise-kit[all]"` or `pipx install "renoise-kit[all]"`.
- **Python 3.8+ with numpy**, for the skill's own scripts.
- **Optional, AI footage**: a [Renoise](https://renoise.ai) connection for keyframes and image-to-video. See
  [renoise-plugins-official](https://github.com/renoise-ai/renoise-plugins-official) for how each agent connects.

Music is not shipped. The skill's catalogue lists Mixkit tracks with their URL and checksum, and `pick_music.py`
downloads a track on first use. Fonts are fetched the same way. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## What digital-human-koubo needs

A shell: the Renoise sandbox (everything below is preinstalled there) or macOS, Linux or Windows. Its scripts are
Python; `scripts/doctor.py` checks what is missing.

- **A Renoise connection** (MCP) to generate the presenter takes.
- **Node.js 18+** for Remotion, and **ffmpeg**.
- **Python 3.8+** with `numpy`, `pillow`, `faster-whisper`, and `rembg` (only for text-behind-the-presenter shots).

No presenter images or voices ship with the skill: each project registers its own host in `brief.json`.

## What pixel-breakdown needs

A shell: the Renoise sandbox (everything below is preinstalled there) or macOS, Linux or Windows. Its scripts are Python;
`scripts/doctor.py` checks what is missing and `scripts/demo.py` renders a credit-free demo episode.

- **A Renoise connection** (MCP) for the voice takes, the music bed and an optional host portrait.
- **ffmpeg** for probing, re-encoding and the final encode.
- **Python 3.8+** with `numpy`, `scipy`, `pillow`, `playwright` (plus its Chromium: `python -m playwright install chromium`)
  and `faster-whisper`.

No footage, host, voice or brand ships with the skill: each episode uses the user's own. The pixel font (Fusion Pixel, SIL OFL
1.1) is downloaded on first use and checked against its sha256.

## What vibe-knowledge needs

A shell: the Renoise sandbox or macOS, Linux or Windows. Its scripts are Python; `scripts/doctor.py` checks what is missing and
`scripts/demo.py` builds a credit-free 10-second demo episode.

- **A Renoise connection** (MCP) for the voiceover and, in the enhanced tier, stills, video shots and sound effects.
- **ffmpeg** for probing, mixing and the final encode.
- **Python 3.8+** with `numpy`, `scipy`, `pillow`, `playwright` (plus its Chromium: `python -m playwright install chromium`) and
  `faster-whisper`. Optional: `rapidocr_onnxruntime` (reads the text on screen back for fact checks) and `rembg` (splits a generated
  still into layers).

The engine's fonts (SIL OFL 1.1) are downloaded on first use and checked against their sha256; the earshot sound bank (MIT) is installed
on request into its own environment. The default music bed ships with the skill. No voice, presenter or footage ships with it.

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
