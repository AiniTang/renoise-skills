# SFX kit

Copied into every new project as `public/sfx/` by `setup_project.sh`. Every file is free for commercial use without attribution (CC0 or generated). All are 48 kHz stereo WAV. Schedule a cue on the frame the action happens (the contact frame): most hits peak within 7 ms of the start, and `SoundCues` shifts the few that build up first (`swish`, `whoosh`, `cut`, `paper-place`, `riser`, `key-8`) by their measured peak (`SFX_PEAK` in `sfx.tsx`). Re-measure with numpy (`argmax(abs(x)) / sr`) when adding a sound.

`preview.wav` plays the whole kit in the order below (start time in the first column) for auditioning.

| Preview | File | Use for | Source |
|---|---|---|---|
| 0.0 s | `key-1..8`, `key-space` | Typing, one per character via `keyCues` | Real Cherry KC 1000 keypresses, "Keyboard Sounds" by unicaegames ([OpenGameArt](https://opengameart.org/content/keyboard-sounds)) |
| 2.8 s | `click` | Mouse click on a button (press + release) | Kenney UI Audio `mouseclick1` + `mouserelease1` |
| 3.9 s | `tap` | Light tap: chips, tabs, menu items | Kenney UI Audio `click3` |
| 4.9 s | `pop` | Element appears: toast, card, bubble | Kenney Interface Sounds `drop_001` |
| 6.0 s | `done` | Check mark, step finished | Kenney Interface Sounds `select_001` |
| 7.0 s | `ding` | Final success only (pitched; use once) | Kenney Interface Sounds `glass_002` |
| 8.0 s | `slam-1..3` | On-beat cuts: kinetic type, list items. Rotate variants | Kenney Impact Sounds `impactSoft_medium_001–003` + Interface `tick_002` |
| 10.3 s | `swish-1..3` | Soft moves: paper sliding, panels, light camera moves | Kenney RPG Audio `cloth2–4` |
| 13.1 s | `page-1..3` | Report/document pages turning or scrolling | Kenney RPG Audio `bookFlip1–3` |
| 15.5 s | `paper-place-1..2` | Paper layer or card landing | Kenney RPG Audio `bookPlace1–2` |
| 17.4 s | `cut` | Paper-cut reveal, blade wipe | Kenney RPG Audio `knifeSlice` |
| 18.9 s | `whoosh` | Fast camera move, scene transition | `scripts/synth_sfx.py` |
| 20.4 s | `impact` | Opening hit, end-card landing | `scripts/synth_sfx.py` |
| 22.7 s | `riser` | 1.2 s build before a reveal | `scripts/synth_sfx.py` |
| 24.9 s | `processing` | 5 s bed under "AI is working" shots, volume ≤ 0.15 | Kenney Sci-Fi Sounds `computerNoise_002` |

Kenney packs: https://kenney.nl/assets (CC0). Avoid pitched electronic blips for repeated cues; they read as cheap. Add new sounds only from CC0 / public-domain sources and record them here.
