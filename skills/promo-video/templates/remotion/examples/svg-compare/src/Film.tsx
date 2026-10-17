import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ArrowRight } from "lucide-react";
import { E } from "../cinematic/motion";
import { keyCues, SoundCues, type Cue } from "../cinematic/sfx";
import { Cursor } from "../op/ui";
import { chipBox, Composer, INK, measureChip, NATIVE, SEND_C } from "./Composer";
import { MENU_N, ModelMenu } from "./Menu";
import { SvgPlayer, type Box4 } from "./SvgPlayer";
import { SVG_G61, SVG_SOL } from "./svgs";
import { bf, clamp01, K, mix, SVG_OFFSET, TOTAL } from "./timeline";

/**
 * YouWare · "Two pelicans, one box" — a 12 s paid-social cut comparing two OpenAI models' animated-SVG answers to one
 * prompt (GPT-6 Sol vs GPT-6.1 Sol, both at reasoning effort Extra High — zh-CN 「极高」, API `xhigh`), shown unaltered
 * and frame-deterministic, then a YouWare hook.
 * Storyboard: 3 concepts × 3 judges → director (2026-09-30); v2 fixes: 4-lens review (craft / motion / brand / phone).
 */
export const FILM_LEN = TOTAL;

const SERIF = '"Hepta Slab", Georgia, serif';
const SANS = '"Manrope", -apple-system, sans-serif';
const IVORY = "#FBF6EC";
const YELLOW = "#FFD05F";
const BANNER = "#FFCF5A";
const PAPER = "#FFFDF5"; // the GPT-6.1 Sol file's own --paper fallback

const MODEL_A = "GPT-6 Sol";
const MODEL_B = "GPT-6.1 Sol";
const EFFORT = "Extra High";
const chipOf = (m: string) => `${m} · ${EFFORT}`;
const PROMPT = "Draw a pelican riding a bicycle as an animated SVG."; // paraphrase — replace with the real prompt

/* ---------- layout ---------- */
const PANE = { w: 880, h: 552, y: 270, xs: [64, 976], banner: 20 };
const CONTENT = { h: 532 };
const LABEL = { y: 886, xs: [504, 1416], size: 72 };
const HEAD_TOP = 102;
const VB_SOL: Box4 = [0, 0, 960, 580];
const VB_G61: Box4 = [-50, 0, 860, 520]; // widened in prep_svgs.py to the card's 1.654 aspect (paper margins)
const ZOOM_SOL: Box4 = [480, 65, 480, 290]; // 2×: crest, eye, beak, pouch + fish
const ZOOM_G61: Box4 = [265, 60, 430, 260]; // 2×: hat, eye, beak, scarf
const BIG = { x: 65, y: 540, w: 1790 };
const COL = (i: number) => ({ x: PANE.xs[i], y: 540, w: PANE.w });
const sOf = (w: number) => w / NATIVE.w;
const S1 = sOf(PANE.w);
/* end card */
const END = { lockTop: 250, lockW: 440, headTop: 440, headSize: 108 };
const SEED: number[] = [360, 640, 1200, 257, 43]; // one YouWare box, centred (960, 768.5)
const PILL: number[] = [380, 690.5, 1160, 156, 78];
const U0: number[] = [414.4, 597.4, 1091.2, 342.2, 40]; // the two folded cards, touching
const FOLD_C = { y: 768.5, xs: [687.2, 1232.8] };

const inOut = E.inOut;
const out = E.out;
const sine = E.sine;
const seg = (f: number, a: number, d: number, e: (x: number) => number = inOut) => e(clamp01((f - a) / d));
const bump = (f: number, at: number, len = 4) => (f >= at && f < at + len ? Math.sin(((f - at) / len) * Math.PI) : 0);

/** Geometric zoom from `base` to `win` about their fixed point (constant perceived speed). */
const zoomWin = (base: Box4, win: Box4, t: number): Box4 => {
  const r = win[2] / base[2];
  if (t <= 0 || Math.abs(1 - r) < 1e-6) return base;
  const fx = (win[0] - r * base[0]) / (1 - r);
  const fy = (win[1] - r * base[1]) / (1 - r);
  const rt = Math.pow(r, t);
  return [fx - (fx - base[0]) * rt, fy - (fy - base[1]) * rt, base[2] * rt, base[3] * rt];
};

/* ---------- the pane group: recedes to a soft ghost and comes back ---------- */
const gState = (f: number) => {
  const rec = seg(f, K.handoff, 18);
  const back = seg(f, K.dock0, K.dock1 - K.dock0);
  const k = rec * (1 - back);
  return { s: mix(1, 0.62, k), ty: -120 * k, k };
};
const gPt = (x: number, y: number, g: { s: number; ty: number }) => ({ x: 960 + (x - 960) * g.s, y: PANE.y + (y - PANE.y) * g.s + g.ty });

/* ---------- camera: a breath on the poster, a push into the model menu ---------- */
const camState = (f: number) => {
  const pp = f < K.handoff ? 0.02 * sine(f / K.handoff) : 0.02 * (1 - seg(f, K.handoff, 18));
  const k = seg(f, K.cam0, K.cam1 - K.cam0, sine) * (1 - seg(f, K.cam2, K.cam3 - K.cam2, sine));
  const S = (1 + pp) * mix(1, 1.6, k);
  const P = { x: mix(960, 1590, k), y: mix(546, 500, k) }; // world point…
  const Q = { x: mix(960, 1040, k), y: mix(546, 540, k) }; // …held at this screen point
  return { S, tx: Q.x - S * P.x, ty: Q.y - S * P.y };
};

const Stage: React.FC = () => (
  <AbsoluteFill style={{ background: IVORY }}>
    <AbsoluteFill style={{ background: `radial-gradient(1100px 760px at 8% -6%, rgba(255,208,95,0.34), rgba(255,208,95,0) 70%)` }} />
    <AbsoluteFill style={{ background: `radial-gradient(1000px 700px at 96% 108%, rgba(253,227,222,0.7), rgba(253,227,222,0) 70%)` }} />
  </AbsoluteFill>
);

/** One result window: white card, YouWare banner, the live SVG, the ghost fog and the scan line. */
const Pane: React.FC<{ i: number; f: number }> = ({ i, f }) => {
  const x0 = PANE.xs[i];
  // ghost: the card shell stays at 60 % so the ghosts still read as the same two windows
  const shell = f < K.dock0 ? 1 - 0.4 * seg(f, K.handoff, 10) : mix(0.6, 1, seg(f, K.dock0 + 8, K.dock1 - K.dock0 - 8));
  const bannerOn = f < K.dock1 ? 1 - seg(f, K.handoff, 8) : 1;
  // fold: shrink toward the centre, outer radius grows toward the box, pictures fade to white
  const fo = seg(f, K.fold0, 12);
  const cx = x0 + PANE.w / 2;
  const tx = (FOLD_C.xs[i] - cx) * fo;
  const ty = (FOLD_C.y - (PANE.y + PANE.h / 2)) * fo;
  const sc = mix(1, 0.62, fo);
  const pic = 1 - seg(f, K.fold0 + 3, 9, sine);
  const banner2 = 1 - seg(f, K.fold0, 7);
  const outer = mix(22, 64, fo);
  const inner = 22 * (1 - seg(f, K.fold0 + 6, 6));
  // CSS order: top-left, top-right, bottom-right, bottom-left (left pane: outer corners on the left)
  const cardR = i === 0 ? `${outer}px ${inner}px ${inner}px ${outer}px` : `${inner}px ${outer}px ${outer}px ${inner}px`;
  const shadowA = 1 - seg(f, K.fold0, 8);
  const topShown = clamp01(bannerOn * banner2); // with no banner above it, the picture takes the card's top radii
  const tl = mix(i === 0 ? outer : inner, 0, topShown);
  const tr = mix(i === 0 ? inner : outer, 0, topShown);
  const picR = i === 0 ? `${tl}px ${tr}px ${inner}px ${outer}px` : `${tl}px ${tr}px ${outer}px ${inner}px`;
  // fog (ghost) and the reveal
  const fog = seg(f, K.handoff, 12) * (f < K.rev1 + 2 ? 1 : 0);
  const p = clamp01((f - K.rev0) / (K.rev1 - K.rev0)); // linear: even speed through the art
  const lineY = CONTENT.h * p;
  const scanA = f >= K.rev0 && f < K.rev1 ? clamp01((f - K.rev0) / 3) * (1 - clamp01((p - 0.8) / 0.2)) : 0;
  // matched head zoom
  const z = seg(f, K.zin0, K.zin1 - K.zin0, sine) * (1 - seg(f, K.zout0, K.zout1 - K.zout0, sine));
  const t = f / 30 + SVG_OFFSET;
  if (f >= K.fold0 + 12) return null;
  return (
    <div style={{ position: "absolute", left: x0, top: PANE.y, width: PANE.w, height: PANE.h, transform: `translate(${tx}px, ${ty}px) scale(${sc})`, transformOrigin: "50% 50%" }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: cardR, background: "#FFFFFF", boxShadow: `0 0 0 1px rgba(231,231,231,${shadowA}), 0 30px 80px rgba(60,40,0,${0.14 * shadowA})`, opacity: shell }} />
      <div style={{ position: "absolute", left: 0, top: 0, width: PANE.w, height: PANE.banner, borderRadius: i === 0 ? `${outer}px ${inner}px 0 0` : `${inner}px ${outer}px 0 0`, background: BANNER, opacity: bannerOn * banner2 }} />
      <div style={{ position: "absolute", left: 0, top: PANE.banner, width: PANE.w, height: CONTENT.h, overflow: "hidden", borderRadius: picR, background: i === 1 ? PAPER : "#FFFFFF", opacity: pic }}>
        <SvgPlayer markup={i === 0 ? SVG_SOL : SVG_G61} prefix={i === 0 ? "sol" : "g61"} time={t} base={i === 0 ? VB_SOL : VB_G61} win={zoomWin(i === 0 ? VB_SOL : VB_G61, i === 0 ? ZOOM_SOL : ZOOM_G61, z)} />
        {fog > 0.001 && lineY < CONTENT.h && (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: lineY - 12,
              bottom: 0,
              backdropFilter: "blur(5px)",
              WebkitBackdropFilter: "blur(5px)",
              background: `rgba(255,255,255,${0.5 * fog})`,
              WebkitMaskImage: "linear-gradient(to bottom, transparent 0, #000 24px)",
              maskImage: "linear-gradient(to bottom, transparent 0, #000 24px)",
              opacity: fog,
            }}
          />
        )}
        {scanA > 0.001 && (
          <>
            <div style={{ position: "absolute", left: 0, right: 0, top: lineY - 20, height: 40, background: "linear-gradient(to bottom, rgba(255,208,95,0), rgba(255,208,95,0.55), rgba(255,208,95,0))", opacity: scanA }} />
            <div style={{ position: "absolute", left: 0, right: 0, top: lineY - 2, height: 4, background: YELLOW, opacity: scanA, boxShadow: "0 0 18px rgba(255,208,95,0.9)" }} />
          </>
        )}
      </div>
    </div>
  );
};

const Headline: React.FC<{ text: string; a: number; dy: number; top?: number; size?: number }> = ({ text, a, dy, top = HEAD_TOP, size = 88 }) =>
  a > 0.001 ? (
    <div style={{ position: "absolute", left: 0, right: 0, top: top + dy, textAlign: "center", fontFamily: SERIF, fontWeight: 500, fontSize: size, lineHeight: 1.05, letterSpacing: "-0.02em", color: INK, opacity: a, fontSynthesis: "none", whiteSpace: "nowrap" }}>{text}</div>
  ) : null;

/** Model label: the name, and the reasoning-effort tag beside it. */
const ModelLabel: React.FC<{ name: string; x: number; y: number; size: number; a: number; tag: number }> = ({ name, x, y, size, a, tag }) =>
  a > 0.001 ? (
    <div style={{ position: "absolute", left: x - 700, width: 1400, top: y - size * 0.62, height: size * 1.24, display: "flex", alignItems: "center", justifyContent: "center", gap: size * 0.28 * tag, opacity: a, whiteSpace: "nowrap" }}>
      <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: size, letterSpacing: "-0.015em", color: INK, fontSynthesis: "none", lineHeight: 1 }}>{name}</span>
      {tag > 0.001 && (
        <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: size * 0.46, letterSpacing: "0.01em", color: INK, background: YELLOW, borderRadius: 999, padding: `${size * 0.1}px ${size * 0.22}px`, opacity: tag, transform: `translateY(${(1 - tag) * 6}px) scale(${mix(0.9, 1, tag)})`, lineHeight: 1.1 }}>{EFFORT}</span>
      )}
    </div>
  ) : null;

export const Film: React.FC = () => {
  const f = useCurrentFrame();
  const g = gState(f);
  const cam = camState(f);

  /* headlines: out first on the handoff; in with a sine opacity + expo translate */
  const h1 = f < K.handoff + 6 ? 1 - seg(f, K.handoff - 3, 7, E.in2) : 0;
  const h2a = seg(f, K.q0, 10, sine) * (1 - seg(f, K.fold0, 8));
  const h2dy = f < K.fold0 ? 20 * (1 - seg(f, K.q0, 14, out)) : -20 * seg(f, K.fold0, 8);

  /* typing: the empty box arrives ("Chat with YouWare"), then the prompt types in and holds */
  const times = Array.from(PROMPT, (_, i) => K.type0 + (i / PROMPT.length) * (K.typeEnd - K.type0 - 1) + (i % 3 === 1 ? 0.5 : 0));
  const nTyped = times.filter((tt) => tt <= f).length;
  const text = PROMPT.slice(0, nTyped);
  const caret = f < K.dup1 && Math.floor(f / 8) % 2 === 0;

  /* the big box rises from below the frame (opaque, trailing the recede), then becomes two chats */
  const rise = seg(f, K.handoff + 2, K.boxLand - K.handoff - 2);
  const d = seg(f, K.dup0, K.dup1 - K.dup0);
  const L = { x: mix(BIG.x, COL(0).x, d), y: mix(BIG.y, COL(0).y, d), w: mix(BIG.w, COL(0).w, d) };
  const R = { x: mix(BIG.x, COL(1).x, d), y: L.y, w: L.w };
  const copyFace = seg(f, K.dup0 + 7, 5);
  const fontSize = mix(18, 15, d);

  /* the switch: send left, open the right chat's menu, pick GPT-6.1 Sol */
  const pressL = bump(f, K.pressL, 5);
  const workingL = seg(f, K.pressL + 2, 4);
  const chipPressed = f >= K.press && f < K.menuClose + 4 ? 1 - seg(f, K.menuClose, 4) : 0;
  const menuA = f < K.menuClose ? seg(f, K.menu0, K.menu1 - K.menu0, out) : 1 - seg(f, K.menuClose, 5);
  const hoverA = seg(f, K.curRow - 3, 3) * (1 - seg(f, K.pick + 2, 3));
  const roll = seg(f, K.roll0, K.roll1 - K.roll0);
  const hot = seg(f, K.roll0 + 1, 5) * (1 - seg(f, K.roll1 + 6, 8));
  const pressR = bump(f, K.sendR, 5);

  /* dock: each box becomes its window's banner; the model names fly down into the labels */
  const dk = seg(f, K.dock0, K.dock1 - K.dock0);
  const faceOut = 1 - seg(f, K.dock0 + 1, 6);
  const dockBox = (i: number) => {
    const c = COL(i);
    const a = gPt(PANE.xs[i], PANE.y, g);
    const b = gPt(PANE.xs[i] + PANE.w, PANE.y + PANE.banner, g);
    const r0 = 20 * S1;
    const rt = mix(r0, 22 * g.s, dk);
    const rb = mix(r0, 0, dk);
    return {
      x: mix(c.x, a.x, dk),
      y: mix(c.y, a.y, dk),
      w: mix(c.w, b.x - a.x, dk),
      h: mix(NATIVE.h * S1, b.y - a.y, dk),
      r: `${rt}px ${rt}px ${rb}px ${rb}px`,
      bg: `rgb(255,${Math.round(mix(255, 207, dk))},${Math.round(mix(255, 90, dk))})`,
    };
  };
  /** Where the model name sits inside a chat's chip (world coords, native font 13.5 px). */
  const chipName = (i: number) => {
    const name = i === 0 ? MODEL_A : MODEL_B;
    const label = chipOf(name);
    const cb = chipBox(label, measureChip);
    const textLeft = cb.x + cb.w - 25 - measureChip(label);
    const c = COL(i);
    return { x: c.x + (textLeft + measureChip(name) / 2) * S1, y: c.y + (cb.y + 15) * S1, size: 13.5 * S1 };
  };

  /* cursor (world coords, inside the camera) */
  const cbR = chipBox(chipOf(MODEL_A), measureChip);
  const chevron = { x: COL(1).x + (cbR.x + cbR.w - 14) * S1, y: COL(1).y + (cbR.y + 22) * S1 };
  const sendLc = { x: COL(0).x + SEND_C.x * S1, y: COL(0).y + SEND_C.y * S1 };
  const sendRc = { x: COL(1).x + SEND_C.x * S1, y: COL(1).y + SEND_C.y * S1 };
  const menuPos = { x: COL(1).x + (NATIVE.w - 58 - MENU_N.w) * S1, y: COL(1).y + (NATIVE.h - 44 - 8 - MENU_N.h) * S1 };
  const row0 = { x: menuPos.x + 118 * S1, y: menuPos.y + (MENU_N.row0 + 19) * S1 };
  const path: [number, { x: number; y: number }][] = [
    [K.cur0, { x: 760, y: 1160 }],
    [K.curL, sendLc],
    [K.pressL + 2, sendLc],
    [K.curChip, chevron],
    [K.menu1, chevron],
    [K.curRow, row0],
    [K.pick + 3, row0],
    [K.curSend1, sendRc],
  ];
  let cur = path[0][1];
  for (let k = 1; k < path.length; k++) {
    const [a, pa] = path[k - 1];
    const [b, pb] = path[k];
    if (f >= a) {
      const u = seg(f, a, b - a);
      cur = { x: mix(pa.x, pb.x, u), y: mix(pa.y, pb.y, u) };
    }
  }
  const curA = seg(f, K.cur0, 5) * (1 - seg(f, K.sendR + 2, 4));
  const curPress = Math.max(pressL, bump(f, K.press, 5), bump(f, K.pick, 5), pressR);

  /* labels (static in the comparison states) */
  const labA = f < K.dock0 ? 1 - seg(f, K.handoff - 3, 6) : f >= K.dock1 ? 1 - seg(f, K.fold0, 8) : 0;
  const tagA = f < K.dock0 ? 1 : seg(f, K.dock1 - 3, 8, out);

  /* end card */
  const bloom = 1300 * seg(f, K.fold0 + 3, 33, sine);
  const union = f >= K.fold0 + 12;
  const um = seg(f, K.fold0 + 12, 8); // folded cards → one YouWare box
  const pm = seg(f, K.fold0 + 25, 12); // box → CTA pill
  const ub = U0.map((v, i) => mix(mix(v, SEED[i], um), PILL[i], pm));
  const seedS = ub[2] / NATIVE.w;
  const seedFace = seg(f, K.fold0 + 12, 5, sine) * (1 - seg(f, K.fold0 + 26, 3));
  const seedSendOn = f >= K.fold0 + 21 ? 1 : 0;
  const seedPress = bump(f, K.fold0 + 23, 4);
  const inkR = f < K.fold0 + 24 ? 0 : mix(17 * seedS, 1400, seg(f, K.fold0 + 24, 8, E.in2));
  const inkC = { x: ub[2] - 31 * seedS, y: ub[3] - 29 * seedS };
  const lockY = seg(f, K.fold0 + 16, 16, out);
  const lockA = seg(f, K.fold0 + 16, 4, sine);
  const endA = seg(f, K.endHead - 10, 7, sine);
  const endY = seg(f, K.endHead - 10, 10, out);
  const cta = seg(f, K.fold0 + 28, 8, out); // white on the white box: the ink disc reveals it
  const nudge = 6 * bump(f, K.endHead + 32, 9);
  const watermark = 1 - seg(f, K.fold0, 8);

  /* sound */
  const cues: Cue[] = [
    { at: K.handoff + 8, name: "whoosh", volume: 0.22 },
    ...keyCues(PROMPT, times, 0, 0.3, 2),
    { at: K.dup0 + 1, name: "swish-2", volume: 0.2 },
    { at: K.dup1, name: "pop", volume: 0.26 },
    { at: K.pressL, name: "click", volume: 0.45 },
    { at: K.press, name: "tap", volume: 0.4 },
    { at: K.menu0, name: "swish-1", volume: 0.14 },
    { at: K.pick, name: "click", volume: 0.5 },
    { at: K.roll0 + 3, name: "click", volume: 0.16 },
    { at: K.sendR, name: "click", volume: 0.6 },
    { at: K.sendR + 1, name: "swish-1", volume: 0.2 },
    { at: K.dock0 + 1, name: "swish-3", volume: 0.2 },
    { at: bf(11.35), name: "ding", volume: 0.2 },
    { at: K.q0, name: "tap", volume: 0.2 },
    { at: K.zin0, name: "swish-2", volume: 0.16 },
    { at: K.zout0, name: "whoosh", volume: 0.2 },
    { at: K.fold0 + 1, name: "whoosh", volume: 0.26 },
    { at: K.fold0 + 23, name: "click", volume: 0.4 },
    { at: K.endHead, name: "impact", volume: 0.34 },
    { at: K.endHead + 32, name: "tap", volume: 0.14 },
  ];
  const musicVol = (fr: number) => interpolate(fr, [0, 2, K.type0 - 2, K.type0 + 2, K.typeEnd, K.typeEnd + 4], [0, 0.55, 0.55, 0.39, 0.39, 0.55], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Stage />
      {bloom > 1 && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(900px 620px at 50% 42%, rgba(255,255,255,0.35), rgba(255,255,255,0) 70%), ${YELLOW}`,
            WebkitMaskImage: `radial-gradient(circle at 960px ${FOLD_C.y}px, #000 ${Math.max(0, bloom - 90)}px, transparent ${bloom}px)`,
            maskImage: `radial-gradient(circle at 960px ${FOLD_C.y}px, #000 ${Math.max(0, bloom - 90)}px, transparent ${bloom}px)`,
          }}
        />
      )}

      {/* camera: everything that belongs to the story */}
      <AbsoluteFill style={{ transform: `translate(${cam.tx}px, ${cam.ty}px) scale(${cam.S})`, transformOrigin: "0 0" }}>
        <Headline text="Same prompt. Two models." a={h1} dy={-20 * seg(f, K.handoff - 3, 7, E.in2)} />
        <Headline text="Which one would you pick?" a={h2a} dy={h2dy} />

        <div style={{ position: "absolute", inset: 0, transform: `translate(0px, ${g.ty}px) scale(${g.s})`, transformOrigin: `960px ${PANE.y}px`, opacity: mix(1, 0.85, g.k) }}>
          <Pane i={0} f={f} />
          <Pane i={1} f={f} />
        </div>

        {[MODEL_A, MODEL_B].map((m, i) => (
          <ModelLabel key={m} name={m} x={LABEL.xs[i]} y={LABEL.y} size={LABEL.size} a={labA} tag={tagA} />
        ))}

        {/* the ask */}
        {f >= K.handoff + 4 && f < K.dock1 && (
          <>
            {f >= K.dup0 &&
              (f < K.dock0 ? (
                <Composer x={R.x} y={R.y} w={R.w} scale={mix(0.985, 1, d)} faceOpacity={copyFace} face={{ text, fontSize, chip: { from: chipOf(MODEL_A), to: chipOf(MODEL_B), roll, hot, pressed: chipPressed }, press: pressR }} />
              ) : (
                <Composer {...dockBox(1)} faceOpacity={faceOut} border={1 - dk} face={{ text, chip: { from: chipOf(MODEL_B), textOpacity: 0 } }} />
              ))}
            {f < K.dock0 ? (
              <Composer
                x={f < K.dup0 ? BIG.x : L.x}
                y={f < K.dup0 ? BIG.y + 600 * (1 - rise) : L.y}
                w={f < K.dup0 ? BIG.w : L.w}
                face={{ text, caret, fontSize, placeholderColor: "#9A9A9A", chip: { from: chipOf(MODEL_A) }, press: pressL, working: workingL }}
              />
            ) : (
              <Composer {...dockBox(0)} faceOpacity={faceOut} border={1 - dk} face={{ text, chip: { from: chipOf(MODEL_A), textOpacity: 0 }, working: 1 }} />
            )}
            {menuA > 0.001 && (
              <div style={{ position: "absolute", left: menuPos.x, top: menuPos.y, width: MENU_N.w, height: MENU_N.h, transform: `scale(${S1})`, transformOrigin: "0 0" }}>
                <ModelMenu a={menuA} hoverRow={0} hover={hoverA} />
              </div>
            )}
          </>
        )}

        {/* model names fly from the chips into the labels (Manrope from the first frame: at chip size the switch is invisible) */}
        {f >= K.dock0 && f < K.dock1 &&
          [MODEL_A, MODEL_B].map((m, i) => {
            const st = chipName(i);
            const u = seg(f, K.dock0, K.dock1 - K.dock0 - 2);
            const x = mix(st.x, LABEL.xs[i], u);
            const y = mix(st.y, LABEL.y, u) - Math.sin(u * Math.PI) * 24;
            return <ModelLabel key={m} name={m} x={x} y={y} size={mix(st.size, LABEL.size, u)} a={1} tag={0} />;
          })}

        <Cursor x={cur.x} y={cur.y} press={curPress} a={curA} scale={1.5} />
      </AbsoluteFill>

      {/* fixed brand bug, above the camera layer */}
      <Img src={staticFile("brand/lockup.svg")} style={{ position: "absolute", left: 64, top: 38, height: 56, opacity: watermark }} />
      {/* the fold: one YouWare box, the send button's ink fills it, it settles into the CTA pill */}
      {union && (
        <div
          style={{
            position: "absolute",
            left: ub[0],
            top: ub[1],
            width: ub[2],
            height: ub[3],
            borderRadius: ub[4],
            background: "#FFFFFF",
            boxShadow: `0 0 0 1px rgba(231,231,231,${1 - pm}), 0 ${mix(18, 20, pm)}px ${mix(50, 44, pm)}px rgba(60,40,0,${mix(0.16, 0.22, pm)})`,
            overflow: "hidden",
          }}
        >
          {seedFace > 0.001 && (
            <div style={{ position: "absolute", left: 0, top: 0, width: ub[2], height: ub[3] }}>
              <Composer x={0} y={0} w={ub[2]} h={ub[3]} r="0" bg="transparent" border={0} shadow={0} face={{ text: "", caret: Math.floor(f / 8) % 2 === 0, fontSize: 18, placeholderColor: "#9A9A9A", chip: { from: chipOf(MODEL_B) }, sendOn: seedSendOn, press: seedPress }} faceOpacity={seedFace} />
            </div>
          )}
          {inkR > 0 && <div style={{ position: "absolute", left: inkC.x - inkR, top: inkC.y - inkR, width: inkR * 2, height: inkR * 2, borderRadius: "50%", background: INK }} />}
          {cta > 0.001 && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 20, fontFamily: SANS, fontWeight: 700, fontSize: 62, letterSpacing: "-0.01em", color: "#FFFFFF", opacity: cta, transform: `translateY(${(1 - cta) * 8}px)` }}>
              Try it at youware.com
              <ArrowRight size={54} strokeWidth={3.4} color="#FFFFFF" style={{ transform: `translateX(${nudge}px)` }} />
            </div>
          )}
        </div>
      )}
      {lockA > 0.001 && <Img src={staticFile("brand/lockup.svg")} style={{ position: "absolute", left: 960 - END.lockW / 2, top: END.lockTop + 16 * (1 - lockY), width: END.lockW, opacity: lockA }} />}
      <Headline text={`Can’t wait to try ${MODEL_B}?`} a={endA} dy={20 * (1 - endY)} top={END.headTop} size={END.headSize} />

      <Audio src={staticFile("music/bgm.wav")} volume={musicVol} />
      <SoundCues cues={cues} />
    </AbsoluteFill>
  );
};
