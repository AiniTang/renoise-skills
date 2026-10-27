# Episode guide: `episode.js`

`episode.js` is one JSON object assigned to `window.EP` (`window.EP = { ... };`). The Python tools read it too, so it must be
strict JSON: double quotes, no comments, no trailing commas. The engine reads it, the timeline (`timeline.js`, written by
`layout.py`) and the media, and builds every frame from them.

## Top-level keys

| Key | Meaning |
| --- | --- |
| `title` | page title (not shown) |
| `lang` | BCP-47 language of the voice and subtitles, e.g. `en`, `zh-CN`, `ja` (also the transcription language) |
| `script` | array of narration lines, exactly as they will be spoken |
| `anchors` | `{ "name": [line, "word", occurrence?] }`: the time the word starts being spoken; `occurrence` counts from 0 |
| `keywords` | `{ "line": ["phrase", ...] }`: subtitle phrases drawn in orange, hopping when spoken |
| `pacing` | `{ "line": seconds }`: silence placed before that line (default `gap`, 0.3 s); give 0.4–1.2 s before title, chat, outro |
| `gap`, `tail` | default gap before lines (0.3) and the hold after the last line (2.6) |
| `asrHint`, `asrMap` | optional: a vocabulary hint for transcription, and character replacements for common mishearings |
| `media` | `{ "key": "media/enc/key.mp4" }`: every clip the scenes use (all-intra, see SKILL.md) |
| `images` | `{ "key": "assets/file.png" }`: extra stills for `media` items with `image` |
| `host` | `{ "image": "assets/host.png" }` (480×270 pixel portrait) or `null` |
| `brand` | `{ "name": "...", "logo": "assets/logo.png", "tint": "#000000" }`, every field optional; `tint` recolours the logo |
| `accent` | main highlight colour (default `#e0702b`) |
| `steps` | optional step badges: `[{ "at": "L6-0.1", "big": "Step 1", "label": "Drop the clip", "short": "Drop" }]` |
| `stepsUntil` | time the step tracker (top right) disappears |
| `music` | `{ "file": "audio/music.wav", "offset": 14.5, "gain": -13, "sections": [[0, 14.5], [33.2, 16.5]], "fade": 1.4 }` |
| `subtitles`, `subtitleScale` | `false` hides subtitles; scale of the subtitle font (default 3) |
| `shakes`, `cues` | extra camera shakes `[[at, dur, px]]` and extra sound cues `[{ "at": ..., "type": "pop" }]` |
| `scenes` | the edit: list of scenes, each starting at `at` (see below) |
| `cover` | the 3:4 cover (see the end) |

## Time expressions

Any `at`, `until`, `from`, `to`, `sendAt` … accepts: a number of seconds; `"L4"` (line 4 starts); `"L4e"` (line 4 ends);
`"@name"` (an anchor); and any of these with an offset: `"@hit-0.2"`, `"L9e+0.05"`. Put events slightly before the word
(−0.1 to −0.3 s) so they land with it.

## Canvas, colours, safe areas

- Pixel coordinates are on the 480×270 grid (x right, y down). Footage boxes are given in the same units.
- Subtitles occupy the band below y ≈ 228: keep important things above it. The step tracker sits top right (y < 18).
- In the chat's split screen the recording window is at x 8–188 and the right panel area is x 196–472, y 20–228.
- Colours: any `#rrggbb`, or a palette name: `ink`, `ink2`, `paper`, `white`, `black`, `accent`, `accent2`, `red`, `red2`, `green`,
  `green2`, `yellow`, `blue`, `sky`, `dark`, `dark2`, `dim`, `mint`, `muted`, `soft`, `cream`, `sub` (subtitle orange).
- Icons (`icon` names): `camera video phone person lock swap check cross heart star eye ear film image note clock coin bolt chat
  building fan paw sparkle gear`.

## Media clocks

Wherever a clip plays, `clock` says which moment of it is on screen:

- a number: the clip time at the scene start, then real speed (`2.5`);
- `{ "at": "@sweep", "media": 6.2 }`: the clip shows 6.2 s exactly when the anchor is spoken, real speed around it — use this to make
  a measured moment of the clip (a cut, a wipe) land on a word;
- `{ "at": ..., "media": ..., "speed": 0.7 }`: same, at another speed;
- `{ "loop": [3.9, 6.8] }`: loop a range (shots, thumbnails);
- `{ "hold": 4.2 }`: a still frame.

## Scenes

Every scene has `type`, `at`, and optionally `tr` (transition into it: `whip`, `blocks`, or `pblocks` between canvas and chat) and
`d` (its length). A scene lasts until the next scene starts.

### `compare`: two clips side by side, in sync (the hook)

```json
{"type": "compare", "at": 0, "crt": true, "orient": "portrait",
 "left": {"media": "source", "label": "Original", "clock": {"at": "@sweep", "media": 6.2}},
 "right": {"media": "remake", "label": "AI remake", "labelAt": "@right-0.2", "clock": {"at": "@sweep", "media": 6.2}},
 "vs": "@right+0.3",
 "items": [{"kind": "chip", "at": "@swap", "x": 60, "y": 146, "text": "One sweep = one outfit"},
           {"kind": "stamp", "at": "@whole", "text": "Whole new cast", "x": 240, "y": 184}]}
```

`orient: "landscape"` lays out two 16:9 screens instead of phones. Side columns (x < 110 and x > 370 for portrait) take items.
`crt: true` opens with a CRT switch-on (first scene only).

### `row`: one clip splits into many (batch remakes, a results wall)

```json
{"type": "row", "at": 0, "crt": true, "source": {"media": "source", "label": "Original", "short": "Original"},
 "splitAt": "@nine", "clock": {"at": "@same", "media": 6.9}, "cutFlash": [3.6, 6.9],
 "items": [{"media": "v1", "label": "Parrot", "at": "@parrot"}, {"media": "v2", "label": "Otter", "at": "@otter"}],
 "groups": [{"from": 0, "to": 1, "label": "Two animals", "at": "@two"}],
 "highlight": {"index": 1, "at": "@hot", "label": "This one"}, "tag": "illustration",
 "extras": [{"kind": "stamp", "at": "@nine2", "text": "Nine stars", "x": 240, "y": 204}]}
```

Without `source` the row starts directly. `cutFlash` (clip times) flashes every tile at once on shared cuts. `highlight` dims the
others. `tag` prints a small label top right (use `"illustration"` for hypothetical shots).

### `title`: title card over the host portrait

```json
{"type": "title", "at": "L4-0.2", "tr": "whip", "lines": [["Remake", "accent", 3], ["any viral clip", "ink", 2]],
 "sub": "Episode 2", "stamp": {"at": "@again", "text": "Again!", "color": "red"}}
```

Lines are `[text, colour, scale]` (scale shrinks automatically to fit). The brand (logo or name) sits on top of the card. Without
a host the card is centred on paper.

### `board`: a free board with an optional phone

```json
{"type": "board", "at": "L5-0.2", "tr": "blocks", "bg": "paper",
 "phone": {"media": "source", "pos": "right", "clock": {"at": "@block", "media": 6.45},
           "boxes": [{"at": "@people", "until": "@low", "box": [0.58, 0.66, 0.97, 0.84], "label": "people"}],
           "chips": [{"at": "@why", "text": "Original", "pos": "top"}]},
 "items": [ ... ]}
```

`bg`: `paper` (light grid), `dark` (dark grid) or `black`. `pos`: `left`, `center`, `right`, or `box: {x, y, w, h}`. `boxes`
highlight a region of the clip given as fractions `[x0, y0, x1, y1]` of the screen.

### `chat`: the simulated agent chat (one per episode)

```json
{"type": "chat", "at": "L9-0.2", "tr": "pblocks",
 "app": {"name": "Agent", "model": "Opus 5.5", "tool": "Renoise", "title": "Fan-wipe remake", "sidebar": ["Earlier project"],
         "greeting": "What are we making today?", "placeholder": "Describe the video", "replyHint": "Reply…", "recLabel": "REC"},
 "messages": [ ... ], "callouts": [ ... ], "split": [ ... ]}
```

`app` labels the interface; keep it neutral or use the user's real tool names. The address bar is always mosaicked.

Messages (each has a unique `id`; times are when it appears):

| `role` | Fields |
| --- | --- |
| `user` | `text`, `attachments` `[{thumb, name}]` (first message), `dropAt` (files fly in), `typeAt`, `sendAt`, `cps` (typing speed) |
| `assistant` | `text`, `at` (typed in) |
| `tool` | `name`, `detail`, `at`, `doneAt` (spinner → `doneLabel`), or `status` |
| `list` | `title`, `items` (strings), `at`, `step` (delay between items) |
| `table` | `title`, `text`, `head` `[a, b]`, `rows` `[[a, b, thumb?]]` (a cell starting `{{` is shown as code), `at`, `step` |
| `images` | `text`, `images` (paths), `size` (px width), `at` |
| `quote` | `title`, `rows` `[[label, value]]`, `costRow` (row index shown large), `note`, `at`, `step` |
| `progress` | `name`, `items` `[{label, minutes, done}]` (bars fill by real run time), `at`, `skipAt`, `skipLabel` ("17 min later"), `doneAt`, `doneLabel` |
| `result` | `name`, `video` or `videos` (media keys), `landscape`, `caption`, `download`, `at`, `mt` (clip start), `loop`, `zoom` |

`callouts`: `[{ "target": "m5.r2", "label": "Price first", "from": "@quote+0.6", "to": "@confirm-0.5" }]` draws a blinking pixel
frame around a message (`m5`), a table or quote row (`m5.r2`), a table value (`m5.v2`), a list item (`m4.i1`) or a user bubble
(`m1.b`). Labels are hidden inside the split screen.

`split`: `[{ "from": "L10-0.15", "to": "L13-0.3", "panels": [{ "from": ..., "to": ..., "title": "analyze_media · breakdown",
"window": true, "items": [ ... ] }] }]` shrinks the recording into a window on the left and shows panels of items on the right
(x 196–472). Panels follow each other; `window: true` draws a dark pixel window with the title. Items use absolute coordinates.

### `outro`

```json
{"type": "outro", "at": "L15-0.15", "tr": "blocks",
 "chips": [{"at": "@bone", "text": "Copy the skeleton"}, {"at": "@skin", "text": "Swap the skin", "color": "accent"}],
 "follow": {"at": "@follow", "label": "+ Follow", "done": "♥ Following"}, "endAt": "L15e+0.3", "endText": "See you next time"}
```

From `endAt` the end card shows the brand large and fades to black at the end.

## Items (boards, side columns, split panels)

Every item has `kind`, `at` (pops in with a small bounce), optional `until`, `x`, `y`, and `sound: false` to silence its cue.

| `kind` | Fields |
| --- | --- |
| `chip` | `text`, `color`, `fg`, `align` (`center` default) |
| `text` | `text`, `color`, `scale`, `align` |
| `stamp` | `text`, `color`, `x`, `y` (centre); slams in with cracks and a camera shake (`shake: false` to skip) |
| `cross` | big red X at `x`, `y`, `size` |
| `icon` | `name`, `scale`, `label` (x, y = centre) |
| `arrow` | `len`, `dir` (1 or −1), `color` (grows in) |
| `bullets` | `w`, `title`, `titleColor`, `lines` (strings or `{text, icon, at, color}`), `icon` (`dot` or an icon for every line), `fill`, `color`, `gap` |
| `card` | `w`, `h`, `title`, `titleScale`, `icon`, `chip`, `media`/`image` + `mediaH` + `clock`, `lines`, `note`, `hot` (highlight while popping), `fill`, `edge` |
| `timeline` | `w`, `duration`, `title`, `segments` `[[t0, t1, colour, label?]]`, `markers` `[{t, label, icon, at}]`, `thumbs` `[{media, mt, t}]`, `ticks`, `tickStep` |
| `slot` | `w`, `h`, `title` (`{{animal}}`), `spinAt`, `spin` `[{media, mt, label}]` (slot-machine through clips) |
| `phones` | `items` `[{media, loop, label, sub, at, hot}]`, `w`, `h`, `gapX`, `y`, `rise`, `arrows` (mini phones, e.g. "three shots") |
| `grid` | `items` `[{media or image, mt, label, at, hot, fx, fy}]`, `cols`, `cell`, `cellH`, `gap`, `square` (square crops), `dimAt` |
| `media` | `media` + `clock`, or `image`; `w`, `h`, `phone` (phone frame) or a white frame; `ax`, `ay` (crop anchor); `dimAt` |
| `boxes` | highlight regions of a footage box: `x, y, w, h` of the box, `boxes` `[{at, until, box: [x0,y0,x1,y1], label}]` |

## Cover

```json
"cover": {"bg": "purple", "lines": [["Remake", "#fff8ec", 5], ["any viral", "#ffd23f", 4]], "badge": "Ep 3",
          "focus": {"kind": "pair", "left": {"media": "source", "t": 4.5, "tag": "Original"}, "right": {"media": "remake", "t": 4.5, "tag": "AI remake"}}}
```

`bg`: `orange blue teal purple red ink` (do not put an orange `badge` on `orange`). Lines: at most about five CJK characters or
ten Latin letters each at scale 5; the scale shrinks to fit. The badge line under the title shows the logo (or brand name) and
the episode label in orange. `focus.kind`: `pair` (original → remake, tags, arrow), `grid` (`items` `[{media, t, fx, fy}]`, square
crops), or a single `{media | image, t}`. Add `"pixel": true` to a focus item to turn a real photo into pixel art (use it when the
user does not want real faces on the cover). `zoom`, `fx`, `fy` frame the crop.

## A compact example

```json
window.EP = {
  "lang": "en", "brand": {"name": "My Channel"}, "host": null,
  "media": {"source": "media/enc/source.mp4", "remake": "media/enc/remake.mp4"},
  "script": ["Left is the viral clip, right is my AI remake.", "Same cuts, same timing, a brand new star.",
             "Here is exactly how it was made.", "Follow for the next one!"],
  "anchors": {"right": [1, "right"], "star": [2, "star"], "follow": [4, "follow"]},
  "keywords": {"1": ["AI remake"], "2": ["brand new star"]},
  "pacing": {"3": 0.5, "4": 0.8},
  "scenes": [
    {"type": "compare", "at": 0, "crt": true, "left": {"media": "source", "label": "Original"}, "right": {"media": "remake", "label": "AI remake", "labelAt": "@right-0.2"}, "vs": "@right+0.3",
     "items": [{"kind": "stamp", "at": "@star-0.1", "text": "New star", "x": 240, "y": 196}]},
    {"type": "title", "at": "L3-0.2", "tr": "whip", "lines": [["How it was made", "accent", 3]]},
    {"type": "outro", "at": "L4-0.15", "tr": "blocks", "follow": {"at": "@follow"}, "endAt": "L4e+0.3", "endText": "See you soon"}
  ],
  "cover": {"bg": "blue", "lines": [["Remake", "#fff8ec", 5], ["it", "#ffd23f", 5]], "badge": "Ep 1", "focus": {"kind": "pair", "left": {"media": "source", "t": 2, "tag": "Original"}, "right": {"media": "remake", "t": 2, "tag": "AI remake"}}}
};
```
