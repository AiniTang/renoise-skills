---
name: pixel-breakdown
description: >
  Make a 16:9 pixel-art breakdown video (60–90 s, 1920×1080, 30 fps) that explains a reference clip the user is authorized to use and the AI remake made from it: a hook that plays the original and the remake side by side, a pixel diagram of why the original works (measured cuts, transitions, timing), the remake recipe, a simulated agent chat that shows the workflow with a quote card and live progress, the finished result, and an outro. Code-built: pixel canvas animation with real footage composited at full resolution, conversational voiceover generated on Renoise, word-timed subtitles with highlighted keywords, chiptune sound design and a 3:4 cover. All content, host, brand, voice and language come from the user. Use when the user wants a pixel-style tutorial, explainer or breakdown of a viral video and its remake, a 像素风拆解 / 像素教程 / 爆款复刻讲解 video, or a series episode in that format. Not for live-action or AI drama shorts themselves.
license: MIT
compatibility: Any agent client that reads Agent Skills and can run a shell — the Renoise sandbox, or macOS / Linux / Windows — with Python 3.8+ (numpy, scipy, pillow, playwright with Chromium, faster-whisper) and ffmpeg. scripts/doctor.py checks them; the Renoise sandbox has them preinstalled. Generation (voice, music, host portrait, remake) needs a Renoise connection (MCP).
---

# Pixel Breakdown

> Paths: `<skill>` is the folder of this SKILL.md; `scripts/`, `engine/`, `references/` and `assets/` are inside it. Replace
> `<skill>` with its absolute path in commands. On Windows call `python` where this file says `python3`.

One run makes one episode: a 1920×1080, 30 fps MP4 of about 60–90 seconds and a 3:4 cover (1080×1440). Every frame is drawn by
code on a 480×270 pixel grid and scaled up 4×; the user's footage is composited at full resolution inside pixel phone frames; the
tutorial part is a simulated agent chat (HTML) captured together with the canvas. Each frame is a pure function of time, so a new
voice take re-times the whole picture automatically.

The engine is `engine/`; `setup_project.py` copies it into each project. You describe the episode as data in `episode.js`; you
do not write animation code per episode. The data format is in [references/episode-guide.md](references/episode-guide.md);
writing rules for the script, voice and music are in [references/script-and-voice.md](references/script-and-voice.md). Read both
before planning.

## Where it runs

- **Renoise sandbox** (when the `sandbox` tool is there): a remote Linux machine with everything preinstalled. It is a Director
  Mode (subscription) feature: `get_account` must show `commerce.sandbox: true`, otherwise sandbox calls fail with
  `SUBSCRIPTION_REQUIRED`. Without it, use the client's own shell if it has one; if not, tell the user the episode needs Director
  Mode or a client that can run commands, and stop before any paid step. Read `~/TOOLBOX.md` before the first piece of work
  there (model paths, fonts, pitfalls). Run anything longer than about 45 seconds (frames, alignment, encodes) in the background
  and poll its log with short commands. You cannot see the screen: look at contact sheets and stills as images.
- **Local shell** (macOS, Linux, Windows): run `python3 <skill>/scripts/doctor.py` first and install what it marks ✗.
  `python3 <skill>/scripts/demo.py <tmp-folder>` builds a credit-free demo episode if you want to prove the toolchain end to end.
- Work only in a project folder of its own: `~/projects/<yyyy-mm-dd>-pixel-breakdown-<slug>/` in the sandbox, or a folder the
  user names locally. Never work in `~` itself or inside another project.
- Renoise tools: `get_account`, `analyze_media`, `estimate_cost`, `create_tasks`, `wait_tasks`, `download_results`,
  `upload_files`, `show_result`; choose models with `load_skill model-routing` and check their limits with `list_models`. Never
  ask the user for local paths in the sandbox or to run anything themselves.

## Ground rules

- Everything that appears in the video comes from the user or from measurement: their reference clip, their remake, their host
  image, their brand, their language. Do not add any other creator's characters, logos, channel names or footage.
- The user must be authorized to use the reference clip. If they are not, or say they are not sure, stop and explain why.
- Numbers on screen are real: model names, durations, resolutions, credits, run times and timestamps come from the actual task
  records or from your own measurements. Text you compose to show the workflow (the agent's analysis lines, tables, plans) is an
  illustration; say so in your delivery note. A hypothetical strategy shot (for example "post them all and follow the winner")
  carries an on-screen "illustration" tag (`tag` on a row scene) and never shows invented view counts or other metrics.
- URLs are never readable on screen: the chat's address bar is pixel-mosaicked by the engine. The voiceover never reads a URL and
  never tells viewers to "open a website". If the user names products or words they do not want shown or said (some platforms
  limit reach for them), keep them out of the script, subtitles and pixel text, and refer to models by their model name.
- The brand appears only on the title card, the end card and the cover: no persistent watermark. Do not give the series an
  AI-sounding generated name; use the user's own series name, or the topic itself.
- All text inside the pixel picture is drawn by the engine in the pixel font. Never ask an image model to write words.
- Spending credits: see Phase 4. Generation prompts are written in English; talk to the user in their language.

## Phase 0 — Intake (one message)

Call `get_account` first (balance, and whether the sandbox is available). Then ask for everything still missing in a single
message, with the host's question tool when it has one, else as a numbered list. Required items block; optional items have
defaults, so never hold the run for them.

| Item | Required | Default |
| --- | --- | --- |
| Reference clip (upload or existing material) and confirmation they may use it | yes | — |
| The AI remake: an existing result (task or material), or "make one first" | yes | — |
| What the episode should teach (the angle) | no | you propose one from the analysis |
| Host character image (shown as a pixel portrait on the title and outro) | no | no host: paper studio cards |
| Voice: a voice sample, "infer it from the host image", or a short description | no | inferred from the host image, else a described voice |
| Brand name and/or logo image | no | none |
| Language of voiceover and subtitles | no | the conversation's language |
| Episode number or series name | no | none |
| Music: generate one, use an upload, or none | no | generate one chiptune bed |
| Target length | no | 70–80 seconds |

If the remake does not exist yet, make it first with Renoise's reference-video remake workflow (`load_skill video-remake`; the
source clip stays attached as the reference video, replacement images come from the user, quote and approval before
generation), then continue here.

## Phase 1 — Project and engine

1. `python3 <skill>/scripts/setup_project.py <project> --lang <lang>` makes `media/enc/`, `assets/`, `audio/`, `fonts/`, `qa/`,
   copies the engine into the project root and downloads the Fusion Pixel font (once, size- and sha256-checked, SIL OFL 1.1)
   into `fonts/` with its licence. It prints the BDF to use. A checksum failure means the download failed: rerun; never
   substitute another font. Do not edit, reformat or "improve" the engine files in the project.
2. Every other command below runs inside `<project>`. `align.py` uses the faster-whisper model `small` unless you pass
   `--model <name-or-path>` (in the sandbox use the path `~/TOOLBOX.md` lists). `render.py` uses Playwright's Chromium, or the
   browser in `CHROME=/path/to/chrome`.

## Phase 2 — Sources, measurements and facts

`M` below stands for `python3 <skill>/scripts/media.py`.

1. Bring the reference clip and the remake (and any variants) into `media/`: `download_results` returns a download command;
   run it in the shell you work in.
2. Watch and listen with `analyze_media` on both. Then measure: `M probe media/<clip>` (duration, frame rate, orientation) and
   `M cuts media/<clip>` (hard cuts by scene score, plus labelled contact sheets at four frames per second in
   `qa/cuts_<clip>/`). Look at the sheets and find the moments that make the clip work: occlusion or wipe transitions, outfit
   or subject swaps, beat hits. Write the measured times down; diagram scenes use them.
3. Read the remake's task record when the host exposes it: model, mode (generate or edit), duration, resolution, audio on or off,
   materials and their roles, estimated credits, created, started and completed times. Use only what you can read; when a number
   is unknown, leave it out of the script.
4. `M intra media/<clip> media/enc/<key>.mp4` for every clip the episode will show: all-intra H.264, 30 fps, no audio, 432×768
   for vertical clips and 768×432 for horizontal ones. All-intra is what makes per-frame seeking exact.
5. `M thumb media/<clip> assets/thumb_<key>.jpg` for the chat attachments, and copy the logo (PNG with transparency) to
   `assets/logo.png` if there is one.

## Phase 3 — Script, storyboard and `episode.js`

1. Write the script (12–16 lines, 280–400 characters for Chinese or about 150–210 words for English) following the script
   guide: hook in the first three seconds, why it works, the recipe, the workflow in the chat, the result, an outro. One line =
   one beat; every line gets a new on-screen action.
2. Write the storyboard as a table (line → scene → what moves) and show it to the user with the script. Do not wait for the
   storyboard to be approved before preparing the paid-step quote; do wait for approval before spending.
3. Write `episode.js` (a JSON object assigned to `window.EP`, see the episode guide): `script`, `lang`, `anchors` (named words
   the picture hangs on), `keywords`, `pacing`, `media`, `brand`, `host`, `music`, optional `steps`, the `scenes` list and `cover`.
   Use anchors for every on-screen event that belongs to a spoken word.

## Phase 4 — Paid steps (one quote, explicit approval)

Collect every paid step in one quote: the voice takes (default 3), the music track (unless uploaded or none), the host portrait
(1–2 images, only when a host image was given), and the remake if it still has to be made. For each show the model chosen with
model-routing, the full prompt, the materials and their roles, the count, and the `estimate_cost` total, plus the account
balance. Then stop and wait for the user's explicit approval in the chat; a host's tool-approval dialog is not approval. Submit
exactly what was quoted with `create_tasks`; any change needs a new quote.

- **Voice:** a speech model that accepts a reference voice. Attach the user's voice sample as the reference audio when there is
  one, else the host image as the reference image when the model supports it, else describe the voice in the prompt. Build the
  prompt from the template in the script guide. The total duration you write is a hard cap: write at least 20% more than the
  script needs.
- **Music:** a music model, instrumental chiptune bed (prompt in the script guide), about 110 seconds.
- **Host portrait:** an image model with the user's host image as the reference: a 16:9 pixel-art medium shot of the character
  in a cosy room, facing the viewer, centred, no text. Turn it into the 480×270 grid with
  `python3 pixelize.py <image> assets/host.png`.

Record every task ID as soon as it is returned, and wait with `wait_tasks`. After an interruption, read the existing task's
status instead of submitting again.

## Phase 5 — Voice to timeline

1. Download the takes, convert each with `M wav <take> audio/vo_<id>.wav` and run `python3 align.py audio/vo_<id>.wav` for each
   (in the background in the sandbox). Compare each transcript with the script: dropped, added or repeated words, misread names,
   and the "NO tail silence" warning (cut off mid-word). Pick the take with the fewest problems and the most natural pace.
   Extra words that sit between lines in their own pause are cut out automatically by the layout; words lost inside a line are
   not: regenerate that take instead (with a new quote if it costs credits).
2. `python3 layout.py audio/vo_<id>.wav audio/vo_<id>_align.json` writes `timeline.js` and `audio/vo_track.wav` and prints each
   line's phrases and the anchor times. Every anchor must resolve; fix `episode.js` until it does.
3. `python3 font.py fonts/<bdf>` builds `font.js` from the characters in `episode.js`. Rerun it whenever on-screen text changes.

## Phase 6 — Build and check the picture

1. Render check frames: `python3 render.py stills 0.5,2.1,...` (a frame before and after every beat), then look at
   `qa/st/sheet.jpg`. Check every section; do not skip this.
2. Look for: text or chips off the frame or overlapping each other, subtitles covering the subject, a step badge covering a stamp,
   footage missing (striped MISSING cards), anchors firing on the wrong word, empty seconds with no new motion, unreadable chat text,
   and a split screen whose right panel is empty. Fix `episode.js`, rerender those times, repeat.
3. A final pass covers the whole video at one still every 2–3 seconds.

## Phase 7 — Sound, frames and delivery

1. Convert the music with `M wav <music> audio/music.wav --stereo` and set `music.file`; choose `music.offset` or
   `music.sections` at bar lines (measure the tempo). `python3 render.py cues` writes `audio/events.json`; `python3 mix.py`
   writes `audio/mix.wav` (voice at about −17 dBFS speech level, chiptune effects, the music bed ducked under the voice).
2. `python3 render.py frames --workers 6` (background in the sandbox; fewer workers on a small machine) writes
   `frames/f_00000.jpg` …; it reports slow frames. Expect about 20 frames per second per worker.
3. `M final frames audio/mix.wav out/<slug>.mp4`: H.264 yuv420p CRF 18, AAC 192 kbps, fast start, loudness normalised to
   −16 LUFS integrated with a −1.5 dBTP ceiling.
4. `M qa out/<slug>.mp4 --expect <timeline duration>`: one video and one audio stream, duration, loudness, true peak below
   −1 dBTP, no silent seconds; look at `qa/final/sheet.jpg`. Fix anything it reports as FAIL.
5. Cover: set `cover` in `episode.js`, run `python3 font.py fonts/<bdf>` and `python3 render.py cover cover.png`, look at
   `cover.png` and at `cover_grid.png` (profile-grid size): the two big lines must read at that size.
6. Deliver. In the sandbox register the MP4 and the cover with `upload_files` and show them with `show_result`; locally give the
   paths (and upload them too if the user wants them in Renoise). Report: duration, what was measured versus illustrated, the
   task IDs used, credits spent, and anything to check by ear (you cannot hear the audio: name the lines to listen to).

## Quality bar

- First three seconds: the result and a conflict (original versus remake in sync, or one clip splitting into many) plus a stamp.
- Every line brings a new action: a stamp, a pop-in, a highlight frame, a whip or block transition, a counter. No static slides.
- The voice is a quick, conversational creator talking to a friend, with clear emotional turns; if a take sounds read aloud,
  regenerate it with a sharper prompt.
- Subtitles: large pixel text, outline and shadow, no box, keywords highlighted and hopping when spoken (the engine does this).
- Pacing: give the picture room before the title, the chat and the outro with `pacing`; never let the narration run over a
  transition without something to look at.
- The tutorial part looks like a real interface (the simulated chat) and the explanations are pixel diagrams beside it (the split
  screen). Do not replace the chat with pixel drawings and do not run the whole tutorial as a screen recording.

## Troubleshooting

- `render.py` stops with "page error": the message names the problem (usually a bad time expression or an unknown anchor in
  `episode.js`). Fix the data, rerun.
- An anchor is "not in line N": the word must appear in that line's script text (case and punctuation are ignored).
- The chat is cut off or tiny: shorten long messages, lower `step` delays, or start the split screen later.
- Subtitles wrap into three rows: split the line with punctuation into shorter phrases.
- A clip shows as MISSING: its `media` path in `episode.js` does not match a file in `media/enc/`.
- Frames render slowly: check the log for slow frames and late seeks; re-encode the clip with `M intra`.
- Chromium does not start: run `doctor.py`; it prints the install command, or set `CHROME` to an installed Chrome.
- A paid task fails or its state is unknown: read the existing task's status; do not submit it again without a known result.
