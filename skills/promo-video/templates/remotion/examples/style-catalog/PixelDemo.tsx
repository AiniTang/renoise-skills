import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { cycle, pixText, px, PixelStage, ridge, sprite } from "../cinematic/pixel";

/** 13 · 像素风 — "YOUWARE QUEST": the YouWare head runs, bumps four ? blocks (site / slides / sheet / report), reaches the flag. 330 frames, 320×180 canvas. */
export const PIXEL_LEN = 330;
const W = 320;
const H = 180;
const GROUND = 148;
const SPEED = 1.5;
const START = 10;
const BLOCKS = [110, 175, 240, 305];
const GOAL = 400;
const JUMP = 22;

const P: Record<string, string> = {
  C: "#F36440", c: "#C94A2C", W: "#FFFFFF", K: "#1A1208", D: "#2A2140", L: "#7D6BC1",
  Y: "#FFD15C", y: "#D99A2B", B: "#2556B6", G: "#7D8F57", g: "#BAC78D", R: "#EE8C6C", S: "#ADC8E6", P: "#B4A5E4",
};
const SKY = ["#2B1B4A", "#3B2663", "#4B2E7A", "#6A4F9E", "#7D6BC1", "#B4A5E4", "#F3B9A8", "#FFD15C"];
const LAKE = ["#2556B6", "#3E6FC9", "#5C8BD8", "#ADC8E6", "#5C8BD8", "#3E6FC9"];

const HERO_HEAD = ["...CCCCC....", "..CCCCCCC...", ".CCCCCCCCC..", ".CCCCCCCCC..", "CCCCCCCCCC..", "CCCCCCCWKC..", "CCCCCCCCCCC.", "CCCCCCCCCCCC", "CCCCCCCCCc..", "CCCCCCCCCc..", "cCCCCCCCcc.."];
const LEGS = [
  [".DD....DD...", ".DD....DD..."],
  ["..DD..DD....", "...DD.DD...."],
];
const ITEMS: string[][] = [
  ["KKKKKKKK", "KRYgWWWK", "KKKKKKKK", "KWWWWWWK", "KWBBWRRK", "KWBBWRRK", "KWWWWWWK", "KKKKKKKK"], // website
  ["KKKKKKKK", "KWWWWWWK", "KWKKWWLK", "KWWWWLLK", "KWKKWLLK", "KKKKKKKK", "...KK...", "..K..K.."], // slides on an easel
  ["KKKKKKKK", "KggggggK", "KWKWKWKK", "KKKKKKKK", "KWKWKWKK", "KKKKKKKK", "KWKWKWKK", "KKKKKKKK"], // sheet
  [".KKKKKK.", ".KRRRRK.", ".KWWWWK.", ".KWKKWK.", ".KWWWWK.", ".KWKKWK.", ".KWWWWK.", ".KKKKKK."], // report
];
const Q_BLOCK = ["KKKKKKKKKKKKKKKK", "KYYYYYYYYYYYYYYK", "KYyYYYYYYYYYYyYK", "KYYYYYKKKKYYYYYK", "KYYYYKKYYKKYYYYK", "KYYYYYYYYKKYYYYK", "KYYYYYYYKKYYYYYK", "KYYYYYYKKYYYYYYK", "KYYYYYYKKYYYYYYK", "KYYYYYYYYYYYYYYK", "KYYYYYYKKYYYYYYK", "KYYYYYYKKYYYYYYK", "KYyYYYYYYYYYYyYK", "KYYYYYYYYYYYYYYK", "KyyyyyyyyyyyyyyK", "KKKKKKKKKKKKKKKK"];
const USED = Q_BLOCK.map((r) => r.replace(/Y|y/g, "c").replace(/c(?=c)/g, "c"));
const FLAG_MARK = ["..L.L...", ".LL.LL..", "L......L", "........", "L......L", ".LL.LL..", "..L.L...", "........"];

const heroX = (t: number) => Math.min(GOAL, 30 + SPEED * Math.max(0, t - START));
const jumpAt = (bx: number) => START + (bx - 14 - 30) / SPEED;
const heroY = (t: number) => {
  for (const bx of BLOCKS) {
    const u = (t - jumpAt(bx)) / JUMP;
    if (u >= 0 && u <= 1) return -4 * 42 * u * (1 - u);
  }
  return 0;
};
const hitT = (i: number) => jumpAt(BLOCKS[i]) + JUMP / 2;

const draw = (g: CanvasRenderingContext2D, t: number) => {
  const hx = heroX(t);
  const cam = Math.min(GOAL - 200, Math.max(0, hx - 70));
  // sky with palette cycling
  for (let b = 0; b < 9; b++) px(g, 0, b * 12, W, 12, cycle(SKY, b, t, 0.06));
  // sun + clouds
  px(g, 250 - cam * 0.05, 30, 22, 22, "#FFE9A8");
  for (let i = 0; i < 5; i++) {
    const cx = ((i * 97 + 20 - t * 0.2 - cam * 0.1) % 420 + 420) % 420 - 50;
    const cy = 18 + (i % 3) * 14;
    px(g, cx, cy, 26, 5, "#FFFFFF");
    px(g, cx + 5, cy - 4, 14, 4, "#FFFFFF");
  }
  // far mountains (parallax 0.2)
  for (let x = 0; x < W; x++) {
    const wx = x + cam * 0.2;
    const hgt = 38 + ridge(wx / 26, 3) * 34;
    px(g, x, 128 - hgt, 1, hgt, "#5554AE");
    if (ridge(wx / 26, 3) > 0.78) px(g, x, 128 - hgt, 1, 3, "#E9E4F5");
  }
  // lake with shimmer (palette cycling)
  for (let r = 0; r < 4; r++) px(g, 0, 128 + r * 5, W, 5, cycle(LAKE, r, t, 0.2));
  for (let i = 0; i < 18; i++) {
    const sx = ((i * 41 - cam * 0.35) % W + W) % W;
    if ((Math.floor(t / 6) + i) % 3 === 0) px(g, sx, 131 + (i % 3) * 5, 6, 1, "#FFFFFF");
  }
  // near hills + pines (parallax 0.5)
  for (let x = 0; x < W; x++) {
    const wx = x + cam * 0.5;
    const hgt = 10 + ridge(wx / 18, 9) * 16;
    px(g, x, GROUND - hgt, 1, hgt, "#3E7A6A");
  }
  for (let i = 0; i < 14; i++) {
    const wx = i * 58 + 20;
    const sx = wx - cam * 0.5;
    if (sx < -10 || sx > W + 10) continue;
    px(g, sx + 3, GROUND - 26, 2, 6, "#6B4029");
    for (let k = 0; k < 4; k++) px(g, sx + 4 - (k + 1), GROUND - 34 + k * 3, (k + 1) * 2, 3, "#2F6552");
  }
  // ground tiles
  for (let x = -((cam % 16) + 16); x < W + 16; x += 16) {
    px(g, x, GROUND, 16, 4, "#BAC78D");
    px(g, x, GROUND + 4, 16, H - GROUND - 4, "#8B5A3C");
    px(g, x + 3, GROUND + 9, 2, 2, "#6B4029");
    px(g, x + 10, GROUND + 16, 2, 2, "#6B4029");
    px(g, x, GROUND, 1, 4, "#7D8F57");
  }
  // blocks + items
  BLOCKS.forEach((bx, i) => {
    const ht = hitT(i);
    const bump = t >= ht && t < ht + 6 ? -Math.sin(((t - ht) / 6) * Math.PI) * 4 : 0;
    sprite(g, t >= ht ? USED : Q_BLOCK, bx - cam - 8, 90 + bump, P);
    if (t >= ht) {
      const u = (t - ht) / 12;
      const fly = Math.min(1, Math.max(0, (t - ht - 14) / 16));
      const ix0 = bx - cam - 4;
      const iy0 = 90 - 4 - Math.min(1, u) * 16;
      const tx = 12 + i * 11;
      const ty = 16;
      const ease = fly * fly * (3 - 2 * fly);
      const ix = ix0 + (tx - ix0) * ease;
      const iy = iy0 + (ty - iy0) * ease - Math.sin(ease * Math.PI) * 20;
      sprite(g, ITEMS[i], ix, iy, P);
    }
  });
  // goal flag with the mark
  const fx = GOAL + 34 - cam;
  px(g, fx, GROUND - 60, 2, 60, "#E9E4F5");
  const raise = Math.min(1, Math.max(0, (t - 258) / 20));
  const fy = GROUND - 14 - raise * 42;
  px(g, fx + 2, fy, 14, 10, "#FFFFFF");
  sprite(g, FLAG_MARK, fx + 5, fy + 1, P);
  // hero
  const frame = Math.floor(t / 4) % 2;
  const air = heroY(t) < 0;
  const moving = heroX(t) < GOAL;
  const hy = GROUND - 13 + heroY(t);
  sprite(g, HERO_HEAD, hx - cam - 6, hy, P);
  sprite(g, moving && !air ? LEGS[frame] : LEGS[0], hx - cam - 6, hy + 11, P);
  // HUD
  const score = BLOCKS.filter((_, i) => t >= hitT(i) + 30).length;
  pixText(g, `SCORE ${score}/4`, 8, 6, "#FFFFFF", 1, "#1A1208");
  pixText(g, "WORLD 1-1", W / 2, 6, "#FFFFFF", 1, "#1A1208", "center");
  pixText(g, `TIME ${String(Math.max(0, 99 - Math.floor(t / 30))).padStart(3, "0")}`, W - 62, 6, "#FFFFFF", 1, "#1A1208");
  // title
  if (t >= 262) {
    const k = Math.min(1, (t - 262) / 10);
    const drop = (1 - k) * -60 + (k >= 1 ? Math.max(0, Math.sin(((t - 272) / 8) * Math.PI)) * -3 * Math.exp(-(t - 272) / 10) : 0);
    pixText(g, "YOUWARE", W / 2, 44 + drop, "#FFD15C", 3, "#1A1208", "center");
    pixText(g, "QUEST", W / 2, 70 + drop, "#F36440", 3, "#1A1208", "center");
    if (t >= 280) pixText(g, "4/4 WORK DONE", W / 2, 98, "#FFFFFF", 1, "#1A1208", "center");
    if (t >= 292 && Math.floor(t / 8) % 2 === 0) pixText(g, "PRESS START", W / 2, 112, "#FFFFFF", 1, "#1A1208", "center");
  }
  // pixel fade-in (dither)
  if (t < 12) {
    const k = t / 12;
    const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
    for (let y = 0; y < H; y += 4) for (let x = 0; x < W; x += 4) if (BAYER[((y / 4) % 4) * 4 + ((x / 4) % 4)] / 16 >= k) px(g, x, y, 4, 4, "#0B0716");
  }
};

export const PixelDemo: React.FC = () => {
  const t = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "#0B0716" }}>
      <PixelStage t={t} draw={draw} />
      <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.16) 0 2px, transparent 2px 6px)", pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

/** Frames where the hero jumps / hits / the flag rises — for chiptune SFX cues. */
export const PIXEL_CUES = { jumps: BLOCKS.map((b) => Math.round(jumpAt(b))), hits: BLOCKS.map((_, i) => Math.round(hitT(i))), coins: BLOCKS.map((_, i) => Math.round(hitT(i) + 30)), flag: 258, title: 262 };
