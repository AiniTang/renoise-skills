Brand film for an AI video platform (~28.5 s) built from the product's own footage: chrome logo fly-through, beat-cut model montage, prompt → model picker → generate → result demo, template coverflow with upload, editing tools on footage, end card with accent CTA.

Assets in `public/`: `video/*.mp4` downloaded from the site's `<video>` sources, poster JPGs cut with `npx remotion ffmpeg -ss <t> -i in.mp4 -frames:v 1`, `brand/logo-glyph.svg` (white glyph only, for extrusion), `brand/logo-mark.svg`, `brand/wordmark-black.svg`, `music/bgm.wav` (synth_bgm.py --bpm 120 --mood tech).
