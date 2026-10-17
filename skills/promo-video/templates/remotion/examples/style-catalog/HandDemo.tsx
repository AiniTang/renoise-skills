import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { BoilDefs, Hatch, onTwos, Rough, Smear, Sparkle } from "../cinematic/handdrawn";
import { warpPath } from "@remotion/paths";
import { fam } from "../cinematic/type";
import { headPath, HEADS } from "../youware-ladder/YouWareChain";

/**
 * 01 · 逐帧手绘 — "Doodle day": on a notebook page, a boiling-line YouWare head pops up (key poses on twos), gets an
 * idea, doodles a website / deck / sheet / report around itself with crayon fills, swallows them with a hop, and hands
 * over to the crayon mark + handwritten slogan. 330 frames, everything on twos.
 */
export const HAND_LEN = 330;
const HAND = fam("Caveat");
const INK = "#2A2140";

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const rr = (x: number, y: number, w: number, h: number, r = 14) => `M ${x + r} ${y} L ${x + w - r} ${y} Q ${x + w} ${y} ${x + w} ${y + r} L ${x + w} ${y + h - r} Q ${x + w} ${y + h} ${x + w - r} ${y + h} L ${x + r} ${y + h} Q ${x} ${y + h} ${x} ${y + h - r} L ${x} ${y + r} Q ${x} ${y} ${x + r} ${y} Z`;
const circ = (x: number, y: number, r: number) => `M ${x - r} ${y} a ${r} ${r} 0 1 0 ${2 * r} 0 a ${r} ${r} 0 1 0 ${-2 * r} 0`;

/* ---------- key poses for the head (substituted on twos) ---------- */
type Pose = { dy: number; sx: number; sy: number; rot: number };
const P = (dy: number, sx: number, sy: number, rot = 0): Pose => ({ dy, sx, sy, rot });
const POP: [number, Pose][] = [
  [10, P(520, 1, 1)],
  [12, P(300, 0.8, 1.3, -4)],
  [14, P(60, 0.86, 1.22, -2)],
  [16, P(-40, 0.95, 1.08)],
  [18, P(0, 1.18, 0.8, 2)],
  [20, P(-12, 0.96, 1.06)],
  [22, P(0, 1.02, 0.98)],
  [24, P(0, 1, 1)],
];
const HOP: [number, Pose][] = [
  [212, P(0, 1.14, 0.84)],
  [214, P(-80, 0.88, 1.18, -3)],
  [216, P(-130, 0.94, 1.08, -5)],
  [218, P(-120, 1, 1, -4)],
  [220, P(-60, 0.95, 1.08)],
  [222, P(0, 1.2, 0.78, 2)],
  [224, P(-10, 0.96, 1.05)],
  [226, P(0, 1, 1)],
];
const poseAt = (t: number): Pose => {
  const tt = onTwos(t);
  let p = P(560, 1, 1);
  for (const [at, q] of [...POP, ...HOP]) if (tt >= at) p = q;
  // idle breathing between the big moves, still on twos
  if (tt > 24 && tt < 212) p = { ...p, sy: 1 + Math.sin(tt * 0.18) * 0.015, sx: 1 - Math.sin(tt * 0.18) * 0.01 };
  return p;
};

/* ---------- the four doodles ---------- */
type Doodle = { at: number; cx: number; cy: number; lines: string[]; fill: { d: string; box: [number, number, number, number]; color: string }[]; face: "left" | "right" };
const D1 = { x: 270, y: 150 };
const D2 = { x: 1350, y: 150 };
const D3 = { x: 1350, y: 690 };
const D4 = { x: 270, y: 690 };
const DOODLES: Doodle[] = [
  {
    at: 84, cx: D1.x + 150, cy: D1.y + 100, face: "left",
    lines: [rr(D1.x, D1.y, 300, 200), `M ${D1.x} ${D1.y + 40} L ${D1.x + 300} ${D1.y + 40}`, `${circ(D1.x + 22, D1.y + 20, 6)} ${circ(D1.x + 42, D1.y + 20, 6)}`, rr(D1.x + 24, D1.y + 60, 252, 80, 8), `M ${D1.x + 24} ${D1.y + 164} L ${D1.x + 200} ${D1.y + 164}`],
    fill: [{ d: rr(D1.x + 24, D1.y + 60, 252, 80, 8), box: [D1.x + 24, D1.y + 60, 252, 80], color: HEADS.coral }],
  },
  {
    at: 110, cx: D2.x + 150, cy: D2.y + 110, face: "right",
    lines: [rr(D2.x, D2.y, 300, 190), `M ${D2.x + 90} ${D2.y + 190} L ${D2.x + 60} ${D2.y + 260} M ${D2.x + 210} ${D2.y + 190} L ${D2.x + 240} ${D2.y + 260}`, `M ${D2.x + 40} ${D2.y + 160} L ${D2.x + 40} ${D2.y + 110} L ${D2.x + 90} ${D2.y + 110} L ${D2.x + 90} ${D2.y + 160} M ${D2.x + 120} ${D2.y + 160} L ${D2.x + 120} ${D2.y + 80} L ${D2.x + 170} ${D2.y + 80} L ${D2.x + 170} ${D2.y + 160} M ${D2.x + 200} ${D2.y + 160} L ${D2.x + 200} ${D2.y + 50} L ${D2.x + 250} ${D2.y + 50} L ${D2.x + 250} ${D2.y + 160}`],
    fill: [
      { d: `M ${D2.x + 120} ${D2.y + 160} L ${D2.x + 120} ${D2.y + 80} L ${D2.x + 170} ${D2.y + 80} L ${D2.x + 170} ${D2.y + 160} Z`, box: [D2.x + 120, D2.y + 80, 50, 80], color: HEADS.lavender },
      { d: `M ${D2.x + 200} ${D2.y + 160} L ${D2.x + 200} ${D2.y + 50} L ${D2.x + 250} ${D2.y + 50} L ${D2.x + 250} ${D2.y + 160} Z`, box: [D2.x + 200, D2.y + 50, 50, 110], color: HEADS.coral },
    ],
  },
  {
    at: 136, cx: D3.x + 150, cy: D3.y + 100, face: "right",
    lines: [rr(D3.x, D3.y, 300, 200, 8), `M ${D3.x} ${D3.y + 50} L ${D3.x + 300} ${D3.y + 50} M ${D3.x} ${D3.y + 100} L ${D3.x + 300} ${D3.y + 100} M ${D3.x} ${D3.y + 150} L ${D3.x + 300} ${D3.y + 150}`, `M ${D3.x + 100} ${D3.y} L ${D3.x + 100} ${D3.y + 200} M ${D3.x + 200} ${D3.y} L ${D3.x + 200} ${D3.y + 200}`],
    fill: [{ d: rr(D3.x, D3.y, 300, 50, 8), box: [D3.x, D3.y, 300, 50], color: HEADS.sage }],
  },
  {
    at: 162, cx: D4.x + 130, cy: D4.y + 110, face: "left",
    lines: [`M ${D4.x} ${D4.y} L ${D4.x + 200} ${D4.y} L ${D4.x + 260} ${D4.y + 60} L ${D4.x + 260} ${D4.y + 230} L ${D4.x} ${D4.y + 230} Z`, `M ${D4.x + 200} ${D4.y} L ${D4.x + 200} ${D4.y + 60} L ${D4.x + 260} ${D4.y + 60}`, `M ${D4.x + 30} ${D4.y + 40} L ${D4.x + 150} ${D4.y + 40} M ${D4.x + 30} ${D4.y + 70} L ${D4.x + 120} ${D4.y + 70}`, circ(D4.x + 110, D4.y + 150, 50)],
    fill: [{ d: `M ${D4.x + 110} ${D4.y + 150} L ${D4.x + 110} ${D4.y + 100} A 50 50 0 0 1 ${D4.x + 158} ${D4.y + 165} Z`, box: [D4.x + 60, D4.y + 100, 100, 100], color: HEADS.yellow }],
  },
];
const SWALLOW = 196;

const HEAD = { x: 960, y: 560, w: 250 };

/** Filters use user-space regions, so the head is warped into world coordinates instead of being transformed. */
const Head: React.FC<{ t: number; face: "left" | "right"; x: number; y: number; s: number }> = ({ t, face, x, y, s }) => {
  const p = poseAt(t);
  const H = (124 * HEAD.w) / 106;
  const cos = Math.cos((p.rot * Math.PI) / 180);
  const sin = Math.sin((p.rot * Math.PI) / 180);
  const ox = x;
  const oy = y + p.dy * s;
  const pt = (px: number, py: number) => {
    const a = px * p.sx * s;
    const b = py * p.sy * s;
    return { x: ox + a * cos - b * sin, y: oy + a * sin + b * cos };
  };
  const xf = (d: string) => warpPath(d, ({ x: px, y: py }) => pt(px, py));
  const d = xf(headPath(-HEAD.w / 2, -H, HEAD.w, face));
  const blink = [36, 38, 138, 140].includes(onTwos(t));
  const ex = face === "right" ? 44 : -44;
  const eye = pt(ex, -H + 78);
  const top = pt(-HEAD.w / 2 - 60, -H - 10);
  const bot = pt(HEAD.w / 2 + 60, 10);
  const box: [number, number, number, number] = [Math.min(top.x, bot.x), Math.min(top.y, bot.y), Math.abs(bot.x - top.x), Math.abs(bot.y - top.y)];
  return (
    <g>
      <Hatch clip={d} box={box} u={1} color={HEADS.coral} id="head-h" gap={11} width={10} />
      <Rough d={d} width={6} />
      {blink ? <Rough d={xf(`M ${ex - 14} ${-H + 78} L ${ex + 14} ${-H + 78}`)} width={5} /> : <circle cx={eye.x} cy={eye.y} r={9 * s} fill={INK} filter="url(#boil-a)" />}
      <Rough d={xf(face === "right" ? `M ${ex - 30} ${-H + 122} Q ${ex - 8} ${-H + 146} ${ex + 18} ${-H + 118}` : `M ${ex + 30} ${-H + 122} Q ${ex + 8} ${-H + 146} ${ex - 18} ${-H + 118}`)} width={5} />
    </g>
  );
};

const Thought: React.FC<{ t: number }> = ({ t }) => {
  const tt = onTwos(t);
  if (tt < 44 || tt > 92) return null;
  const k = clamp01((tt - 44) / 10);
  const out = tt > 84;
  const bx = 1170;
  const by = 250;
  const idea = tt >= 66;
  return (
    <g opacity={out ? 0.3 : 1}>
      <Rough d={circ(1060, 420, 10)} u={k * 3} />
      <Rough d={circ(1095, 370, 16)} u={k * 3 - 0.6} />
      <Rough d={`M ${bx - 90} ${by + 40} Q ${bx - 120} ${by - 20} ${bx - 60} ${by - 40} Q ${bx - 30} ${by - 90} ${bx + 30} ${by - 60} Q ${bx + 100} ${by - 80} ${bx + 110} ${by - 10} Q ${bx + 150} ${by + 40} ${bx + 90} ${by + 70} Q ${bx + 40} ${by + 110} ${bx - 20} ${by + 80} Q ${bx - 90} ${by + 100} ${bx - 90} ${by + 40} Z`} u={(tt - 50) / 10} />
      {!idea && tt >= 58 && <text x={bx + 6} y={by + 36} textAnchor="middle" fontFamily={HAND} fontWeight={700} fontSize={110} fill={INK} filter="url(#boil-a)">?</text>}
      {idea && (
        <g filter="url(#boil-a)">
          <Hatch clip={circ(bx + 8, by - 2, 38)} box={[bx - 32, by - 42, 80, 80]} u={clamp01((tt - 66) / 6)} color={HEADS.yellow} id="bulb-h" gap={9} width={8} />
          <Rough d={`${circ(bx + 8, by - 2, 40)} M ${bx - 8} ${by + 40} L ${bx + 24} ${by + 40} M ${bx - 4} ${by + 54} L ${bx + 20} ${by + 54}`} u={(tt - 66) / 6} />
          {[0, 1, 2, 3, 4].map((i) => {
            const a = (-150 + i * 30) * (Math.PI / 180);
            return <Rough key={i} d={`M ${bx + 8 + Math.cos(a) * 58} ${by - 2 + Math.sin(a) * 58} L ${bx + 8 + Math.cos(a) * 80} ${by - 2 + Math.sin(a) * 80}`} u={(tt - 70) / 4} />;
          })}
        </g>
      )}
    </g>
  );
};

const DoodleArt: React.FC<{ d: Doodle; t: number; i: number }> = ({ d, t, i }) => {
  const tt = onTwos(t);
  if (tt < d.at) return null;
  const sw = clamp01((tt - SWALLOW - i * 3) / 12);
  if (sw >= 1) return null;
  // swallowed: jump in 3 drawn steps toward the head
  const steps = [0, 0.18, 0.55, 1];
  const s = steps[Math.min(3, Math.floor(sw * 4))];
  const tx = (HEAD.x - d.cx) * s;
  const ty = (HEAD.y - 150 - d.cy) * s;
  const sc = 1 - 0.8 * s;
  const lines = d.lines.map((l, j) => clamp01((tt - d.at - j * 3) / 10));
  const fillU = clamp01((tt - d.at - 14) / 10);
  return (
    <g transform={`translate(${d.cx + tx} ${d.cy + ty}) scale(${sc}) translate(${-d.cx} ${-d.cy})`}>
      {d.fill.map((f, j) => (
        <Hatch key={j} clip={f.d} box={f.box} u={fillU} color={f.color} id={`dh${i}${j}`} />
      ))}
      {d.lines.map((l, j) => (
        <Rough key={j} d={l} u={lines[j]} width={5} />
      ))}
      {s > 0 && s < 1 && <Smear x={d.cx} y={d.cy} angle={Math.atan2(d.cy - HEAD.y, d.cx - HEAD.x) * (180 / Math.PI)} len={160} seed={`sm${i}`} />}
    </g>
  );
};

const Notebook: React.FC = () => (
  <>
    <AbsoluteFill style={{ background: "#FBF8F0" }} />
    <AbsoluteFill style={{ backgroundImage: "linear-gradient(transparent 46px, #CFE0F2 46px, #CFE0F2 48px)", backgroundSize: "100% 48px", backgroundPosition: "0 20px" }} />
    <div style={{ position: "absolute", left: 170, top: 0, bottom: 0, width: 3, background: "#F2A9A0" }} />
  </>
);

export const HandDemo: React.FC = () => {
  const t = useCurrentFrame();
  const tt = onTwos(t);
  // the head faces whichever doodle it is drawing
  let face: "left" | "right" = "right";
  for (const d of DOODLES) if (tt >= d.at - 4) face = d.face;
  if (tt >= SWALLOW) face = "right";
  // hand-over: the head steps aside (three drawn positions) for the crayon mark + words
  const aside = [0, 0.3, 0.75, 1][Math.min(3, Math.max(0, Math.floor((tt - 236) / 3) + 1))] * (tt >= 236 ? 1 : 0);
  const hx = HEAD.x + (1560 - HEAD.x) * aside;
  const hy = HEAD.y + (720 - HEAD.y) * aside;
  const hs = 1 - 0.3 * aside;
  const mark = clamp01((tt - 244) / 14);
  const word = clamp01((tt - 256) / 16);
  const sub = clamp01((tt - 272) / 16);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Notebook />
      <BoilDefs t={t} hold={2} scale={3} />
      {/* crayon mark revealed by a scribble wipe */}
      {mark > 0 && (
        <div style={{ position: "absolute", left: 250, top: 250, width: 440, height: 440, clipPath: `inset(0 ${100 - mark * 100}% 0 0)`, filter: "url(#boil-a)" }}>
          <Img src={staticFile("brand/mark-crayon.png")} style={{ width: 440, height: 440 }} />
        </div>
      )}
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {DOODLES.map((d, i) => (
          <DoodleArt key={i} d={d} t={t} i={i} />
        ))}
        <Thought t={t} />
        {tt >= 10 && <Head t={t} face={face} x={hx} y={hy} s={hs} />}
        <Sparkle x={1180} y={180} r={34} t={t} at={70} />
        <Sparkle x={HEAD.x + 170} y={HEAD.y - 330} r={40} t={t} at={216} />
        <Sparkle x={HEAD.x - 190} y={HEAD.y - 250} r={30} t={t} at={220} color={HEADS.sky} />
        <Sparkle x={1640} y={380} r={36} t={t} at={286} />
        {word > 0 && <Rough d="M 760 530 Q 960 552 1300 526" u={(tt - 266) / 10} color={HEADS.coral} width={8} />}
      </svg>
      {word > 0 && (
        <div style={{ position: "absolute", left: 740, top: 330, fontFamily: HAND, fontWeight: 700, fontSize: 200, color: INK, clipPath: `inset(-20% ${100 - word * 100}% -20% 0)`, filter: "url(#boil-a)", lineHeight: 1 }}>YouWare</div>
      )}
      {sub > 0 && (
        <div style={{ position: "absolute", left: 770, top: 572, fontFamily: HAND, fontWeight: 600, fontSize: 70, color: INK, clipPath: `inset(-20% ${100 - sub * 100}% -20% 0)`, filter: "url(#boil-a)" }}>from answers to outcomes</div>
      )}
      <AbsoluteFill style={{ background: "#FBF8F0", opacity: 1 - clamp01(t / 8), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
