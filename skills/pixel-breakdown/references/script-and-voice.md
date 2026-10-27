# Script, voice and music

## 1. Choosing the angle

A breakdown episode answers two questions: why did the original work, and how was the remake made. Pick one angle that the
footage and the measurements support, and let every line serve it. Angles that have worked:

- **Swap the star:** same moves, timing and camera, a new protagonist (the user's character).
- **Swap the theme:** keep the skeleton (camera, transitions, rhythm), change the skin (characters, outfits, setting).
- **One clip, many variants:** turn the original into a template with one open slot and generate a batch in parallel.
- **The hidden transition:** an occlusion wipe, a match cut or a beat-locked cut that hides every change.
- **Design first:** a look board or reference sheet approved before the paid video run.

If a series already exists, do not repeat the previous episode's angle.

## 2. Structure (12–16 lines)

| Part | Length | Purpose |
| --- | --- | --- |
| Hook | 0–4 s, 1–2 lines | the result and a conflict: original versus remake in sync, or one clip splitting into many |
| Proof / promise | 4–9 s | one more striking fact ("I didn't shoot a single second"), then what today's episode teaches |
| Title | ~1 s | brand + title card (give 0.4–0.6 s of `pacing` before it) |
| Why it works | 2–3 lines | measured: the cuts, the transition, the timing, the composition trick; end with a stamped term |
| The recipe | 1–2 lines | what stays locked to the original, what becomes a slot |
| The workflow | 4–6 lines | in the chat: drop the clip, the analysis, the slots or look board, the plan, the quote, the confirmation, the progress |
| Result | 1 line | the finished remake plays; real run time and cost if known |
| Outro | 1–2 lines | one memorable sentence, a follow call |

Rules:

- One line = one beat = one new on-screen action. Write the storyboard next to the script.
- Conversational, short, opinionated: a quick creator talking to a friend. No "firstly / secondly", no essay sentences.
- Write numbers the way they are spoken ("four hundred eighty credits", "十五秒"), so the voice reads them right and the alignment
  holds; the subtitles show what you wrote.
- Facts only from task records and measurements. Strategy advice can be said, but anything hypothetical on screen is tagged.
- Never read a URL aloud, never say "open the website", and keep any words or brand names the user asked to avoid out of the
  script; call models by their model name.
- Proper nouns go into `asrHint` so the transcription recognises them.

## 3. Hooks that work

- **Side by side, in sync:** both clips play with the same clock, and a measured moment (a cut, a wipe) lands on a spoken word;
  a VS badge, then a stamp ("whole new cast").
- **One into many:** the original shrinks to a small tile and a row of variants fans out from it; each is named as it is spoken;
  all tiles cut at the same instant; a stamp ("nine stars").
- **The impossible claim:** "I didn't shoot a single second": a camera icon crossed out with a big X.

## 4. Voice prompt template

Generate three takes in one batch. The model returns the duration you write as a hard cap: estimate the length (characters ÷ 5
or words ÷ 2.6, plus 0.4 s per line) and write at least 20% more. Shorter takes simply end in silence that the layout removes.

```text
This is a short-video knowledge voiceover, not a reading, not an announcement, not a dubbing script.
The speaker: <who, from the host image or the user's description: age, vibe, attitude>. They talk to the camera like a quick,
confident creator explaining a trick to a friend, a little proud, a little cheeky.

Most important:
1. Fast: about <6 characters / 3 words> per second, one breath flowing into the next. Barely any pause between sentences
   (about 0.2 s) and about 0.3 s between lines. Do not stop at every comma, do not drag syllables.
2. Conversational: relaxed articulation, natural stress and linking, as if said off the cuff. No reading voice, no announcer,
   no recital, no advert voice.
3. Pronunciation: <how to say every product, model and English term, e.g. "Opus 5.5" as "Opus five point five">.
4. Big emotional range, line by line:
- "<line 1 fragment>": <grab attention, a little mysterious or provocative>.
- "<key reveal>": <proud reveal, smiling>.
- "<the term>": <stressed, like announcing the answer>.
- "<the workflow request>": <casual, like typing a message>.
- "<the price line>": <reassuring>.
- "<the result>": <delighted>.
- "<the last line>": <cool closing, then a relaxed smiling follow call>.

Audio: clean voice only, no music, no sound effects, no reverb. Total length within <N> seconds.
Say the lines below word for word, adding and dropping nothing, and do not read these instructions:

<the script, one line per line>
```

Choosing a take (`align.py` prints the transcript of each):

1. Reject takes that drop, add or repeat words inside a line, misread names, or end without tail silence (cut off).
2. Extra words that stand alone between two lines, in their own pause, are fine: the layout cuts each line out of the take.
3. Among good takes prefer the faster, livelier one. If none is good, sharpen the prompt and generate again (new approval).

## 5. Music prompt

```text
Instrumental chiptune background music for a cute pixel-art tutorial video. 16-bit SNES / Game Boy Advance style: square and
pulse wave lead, soft triangle bass, light noise-channel drums, a few arpeggios. Mood: playful, curious, upbeat but relaxed, a
little cheeky, like a cozy indie game's town theme. Around 105-115 BPM, steady groove. Simple, sparse melody with room for a
narrator; no vocals, no lyrics, no spoken words. Structure: short intro, loopable A section, a quieter B section, the A section
returns brighter, clean ending. About 1 minute 50 seconds.
```

Measure the tempo and the bar lines (librosa beat tracking) and use them: start the bed on a bar line after the intro
(`music.offset`), and when the chat or the outro starts, jump back to an earlier bar line with `music.sections` so the loud part
covers the whole video.

## 6. Sound

`render.py cues` derives the effects from the scenes: pops for chips and cards, stamps, whooshes on transitions, typing, clicks,
dings when a tool finishes, a counter on the price, a chime on the result, steps on the end card. Add a cue with `cues` in
`episode.js` for a moment the scenes do not cover. Available types: `tick pop blip click type chime ding swish whoosh whip blocks
crt stamp sparkle count step` (`soft: 1` makes a stamp quieter, `gain` adds dB).
