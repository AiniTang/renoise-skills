/*
 * Timeline, authored in beats of the music (Mixkit "Tears of Joy", measured 124.05 BPM, its first downbeat trimmed to
 * frame 0 by tools/build_music.py). bf(n) = frame of beat n. Bars (4 beats) carry the big sync points:
 * bar 2 send · bar 3 question · bar 4 zoom-out + music splice · bar 5 end headline on the track's own final chord.
 */
export const FPS = 30;
export const BPM = 124.05;
export const BEAT = (60 / BPM) * FPS; // 14.509 frames
export const bf = (beats: number) => beats * BEAT;
export const TOTAL = 360; // 12 s

/** SVG clock = film clock + offset (s): puts GPT-6 Sol Max's own 3.4 s blink inside the head-zoom hold. */
export const SVG_OFFSET = 2.49;

export const K = {
  handoff: bf(2.6), // comparison recedes, the empty YouWare box rises ("Chat with YouWare")
  boxLand: bf(3.6), // lands empty: "Chat with YouWare" reads for ~6 frames
  type0: bf(4.25), // the prompt types in… (placeholder settled ~10 frames first)
  typeEnd: bf(5.5), // …and holds, complete, until the duplicate
  dup0: bf(6.0), // one chat becomes two
  dup1: bf(7.0),
  cur0: bf(6.4), // cursor sends the left chat (GPT-6 Sol)…
  curL: bf(7.0),
  pressL: bf(7.05),
  cam0: bf(7.05), // camera pushes in on the right chat so the model menu reads on a phone
  cam1: bf(7.72),
  curChip: bf(7.5), // …then opens the right chat's model menu…
  press: bf(7.55),
  menu0: bf(7.55),
  menu1: bf(7.9),
  curRow: bf(8.25), // …and picks GPT-6.1 Sol
  pick: bf(8.3),
  menuClose: bf(8.35),
  roll0: bf(8.4),
  roll1: bf(8.85),
  cam2: bf(8.7), // camera pulls back (11 frames, sine) while the cursor heads for send
  cam3: bf(9.45),
  curSend0: bf(8.9),
  curSend1: bf(9.35),
  sendR: bf(9.45),
  dock0: bf(9.55), // each ask docks into its result window
  dock1: bf(10.75),
  rev0: bf(10.75), // the scan line reveals both results
  rev1: bf(11.95),
  q0: bf(12), // bar 3: "Which one would you pick?"
  zin0: bf(14.4), // matched head zoom
  zin1: bf(15.1),
  zout0: bf(16), // bar 4 (music splice under the whoosh)
  zout1: bf(16.8),
  fold0: bf(18), // results fold back into one YouWare box → CTA
  endHead: bf(20), // bar 5: end headline + final chord
};

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
export const mix = (a: number, b: number, t: number) => a + (b - a) * t;
