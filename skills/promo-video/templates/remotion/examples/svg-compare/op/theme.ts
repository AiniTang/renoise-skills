import { E } from "../cinematic/motion";

/* ── timing: Deep Urban, 124.05 BPM; beat 0 lands on 2.5 s (the prompt starts) ── */
export const FPS = 30;
export const BEAT = 60 / 124.05;
export const b = (n: number) => 2.5 + n * BEAT;
export const T = {
  hookPill: 0.35,
  dock: 2.05, // the pill travels into the input box
  typing0: b(1),
  typing1: b(7.4),
  open: b(8), // click "Auto ⌄" → the model menu opens
  pick: b(10.4), // click "Claude Opus 5.5" → the chip switches
  send: b(13),
  work0: b(14),
  list0: b(14.6),
  listStep: BEAT * 0.9,
  worked: b(24.4),
  reveal: b(26),
  push: b(29),
  pull: b(51.5),
  reelEnd: b(26) + 14.0,
  dl: b(58),
  chips: b(59),
  end: b(64),
  total: 37.6,
};
export const FRAMES = Math.round(T.total * FPS);

/* ── YouWare (colours sampled from the recording + brand identity 2.0) ── */
export const C = {
  yellow: "#FFD05F",
  banner: "#FFCF5A",
  ivory: "#FBF6EC",
  ink: "#151513",
  text: "#1F1F1F",
  body: "#2E2E2E",
  grey: "#8E8E8E",
  line: "#E7E7E7",
  win: "#FBFBFB",
  panel: "#F3F3F3",
  bubble: "#EDF0E5",
  sage: "#BBC98D",
  blush: "#FDE3DE",
  coral: "#F26B3A",
};
export const UI = '"DM Sans", -apple-system, "Helvetica Neue", sans-serif';
export const SERIF = '"Hepta Slab", Georgia, serif';
export const SANS = '"Manrope", -apple-system, sans-serif';

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
export const mix = (a: number, b2: number, t: number) => a + (b2 - a) * t;
export const sg = (t: number, a: number, d: number, e: (x: number) => number = E.inOut) => e(clamp01((t - a) / d));

/* window in world space (world = stage at zoom 1) */
export const WIN = { x: 90, y: 60, w: 1740, h: 905, chat: 600 }; // bottom at 965: captions sit in the band below
export const INPUT = { x: WIN.x + 24, y: WIN.y + WIN.h - 24 - 118, w: 552, h: 118 };
export const PLAYER = { x: WIN.x + WIN.chat + 40, y: WIN.y + 150, w: 1060, h: 596 };
export const CHIP = { x: INPUT.x + INPUT.w - 58 - 128, y: INPUT.y + INPUT.h - 44, w: 128, h: 30 };
export const SEND = { x: INPUT.x + INPUT.w - 48, y: INPUT.y + INPUT.h - 46, w: 34, h: 34 };
export const DL = { x: WIN.x + WIN.w - 102, y: WIN.y + 84, w: 30, h: 30 };
export const CHIP_AUTO_W = 64; // the chip while it reads "Auto" (right edge stays put)
/* YouWare's model menu, rebuilt from the user's screenshot: opens above the chip, right edges aligned */
export const MENU = { w: 228, h: 350, x: CHIP.x + CHIP.w - 228, y: CHIP.y - 8 - 350, row0: 53, rowH: 38 };
export const MODELS: [string, string][] = [
  ["GPT-6 Astra", "openai"],
  ["GPT-6 Sol", "openai"],
  ["Claude Opus 5.5", "claude"],
  ["Claude Sonnet 5", "claude"],
  ["GLM-5.3-FlashX", "zai"],
  ["DeepSeek-V4.1-Flash", "deepseek"],
  ["Gemini 3.8 Flash", "gemini"],
  ["MiMo-V2.6-Pro", "mimo"],
];
export const OPUS_ROW = 2;

/* the reel's own arrangement, from the agent's message in the recording */
export const SECTIONS = [
  { name: "Form", t0: 0, t1: 2, line: "A white dot pops in, squashes and stretches into a line." },
  { name: "Type", t0: 2, t1: 4.5, line: "“MOTION” rises letter by letter; a coral “E” makes it “EMOTION”." },
  { name: "Rhythm", t0: 4.5, t1: 7, line: "A grid of colored dots ripples in waves." },
  { name: "Morph", t0: 7, t1: 9.5, line: "One shape morphs through circle, triangle, square and star." },
  { name: "Craft", t0: 9.5, t1: 12, line: "An animated easing-curve graph and spacing chart." },
  { name: "Speed", t0: 12, t1: 13.5, line: "A tunnel of spinning squares with words flashing past." },
  { name: "Intent", t0: 13.5, t1: 15, line: "An end card reading “EVERY FRAME INTENTIONAL”." },
];
export const SEC_COLORS = ["#F4F2EC", "#F26B3A", "#6E7BFF", "#FF8A3D", "#D8F33A", "#5CD1FF", "#F26B3A"];
export const PROMPT = "Make a dynamic 15-second motion graphics video that shows what an incredible motion designer you are.";
