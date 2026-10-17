import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { chainPen, Oneline, Paper, Seg, SketchDefs, Stroke } from "../cinematic/lineart";
import { fam } from "../cinematic/type";
import { MARK_D, MARK_VB } from "./markPath";

/**
 * 04 · 线条艺术 — "One line": a single ink line runs along the page and lifts into a question bubble, a website,
 * a slide deck and a report; colour arrives only when a drawing is done (line = answer, fill = outcome); it ends in
 * the YouWare mark. 330 frames.
 */
export const LINE_LEN = 330;
const HAND = fam("Caveat");
const SLAB = fam("Hepta Slab");
const INK = "#1D1A24";
const B = 800;

const MAIN: Seg[] = [
  { d: `M -420 ${B} L 500 ${B}`, a: 4, b: 18 },
  { d: `M 500 ${B} Q 560 700 640 600 L 604 600 Q 560 600 560 556 L 560 344 Q 560 300 604 300 L 1076 300 Q 1120 300 1120 344 L 1120 556 Q 1120 600 1076 600 L 700 600 Q 690 700 740 ${B}`, a: 18, b: 48 },
  { d: `M 740 ${B} L 1640 ${B}`, a: 58, b: 72 },
  { d: `M 1640 ${B} L 1700 740 L 1700 380 Q 1700 360 1720 360 L 2280 360 Q 2300 360 2300 380 L 2300 740 L 2360 ${B}`, a: 72, b: 100 },
  { d: `M 2360 ${B} L 2860 ${B}`, a: 114, b: 126 },
  { d: `M 2860 ${B} L 2940 680 L 2940 330 L 3480 330 L 3480 680 L 3560 ${B}`, a: 126, b: 152 },
  { d: `M 3560 ${B} L 4060 ${B}`, a: 166, b: 178 },
  { d: `M 4060 ${B} L 4140 ${B} L 4140 300 L 4420 300 L 4500 380 L 4500 ${B} L 4560 ${B}`, a: 178, b: 202 },
  { d: `M 4560 ${B} L 5900 ${B}`, a: 212, b: 236 },
];
const circ = (x: number, y: number, r: number) => `M ${x - r} ${y} a ${r} ${r} 0 1 0 ${2 * r} 0 a ${r} ${r} 0 1 0 ${-2 * r} 0`;
type Detail = { d: string; a: number; b: number; w?: number };
const DETAILS: Detail[] = [
  // website
  { d: `M 1700 740 L 2300 740`, a: 92, b: 104 },
  { d: `M 1700 410 L 2300 410`, a: 94, b: 106 },
  { d: `${circ(1728, 385, 7)} ${circ(1752, 385, 7)} ${circ(1776, 385, 7)}`, a: 98, b: 108, w: 4 },
  { d: `M 1740 450 L 2260 450 L 2260 600 L 1740 600 Z`, a: 98, b: 112 },
  { d: `M 1760 598 L 1850 520 L 1910 570 L 1980 490 L 2080 598`, a: 104, b: 116 },
  { d: circ(2180, 505, 26), a: 106, b: 116, w: 4 },
  { d: `M 1740 646 L 2060 646`, a: 108, b: 116 },
  { d: `M 1740 690 L 1960 690`, a: 110, b: 118 },
  // deck
  { d: `M 2940 680 L 3480 680`, a: 146, b: 156 },
  { d: `M 3210 680 L 3210 ${B}`, a: 148, b: 158 },
  { d: `M 3000 392 L 3260 392`, a: 148, b: 158, w: 7 },
  { d: `M 3000 434 L 3160 434`, a: 150, b: 160 },
  { d: `M 3020 640 L 3020 560 L 3090 560 L 3090 640`, a: 152, b: 162 },
  { d: `M 3120 640 L 3120 510 L 3190 510 L 3190 640`, a: 155, b: 165 },
  { d: `M 3220 640 L 3220 468 L 3290 468 L 3290 640`, a: 158, b: 168 },
  { d: `M 3000 640 L 3440 640`, a: 152, b: 164 },
  { d: `M 3330 620 Q 3390 560 3430 474 M 3408 478 L 3432 470 L 3440 494`, a: 160, b: 172 },
  // report
  { d: `M 4420 300 L 4420 380 L 4500 380`, a: 196, b: 204 },
  { d: `M 4190 360 L 4360 360`, a: 196, b: 206, w: 7 },
  { d: `M 4190 420 L 4450 420 L 4450 560 L 4190 560 Z`, a: 198, b: 210 },
  { d: `M 4190 466 L 4450 466 M 4190 512 L 4450 512 M 4280 420 L 4280 560 M 4366 420 L 4366 560`, a: 204, b: 214, w: 3.5 },
  { d: `M 4190 604 L 4190 752 L 4450 752`, a: 204, b: 214 },
  { d: `M 4196 736 L 4262 690 L 4326 708 L 4396 632 L 4450 650`, a: 208, b: 220 },
];
type Fill = { d: string; at: number; color: string };
const FILLS: Fill[] = [
  { d: `M 564 344 Q 564 304 604 304 L 1076 304 Q 1116 304 1116 344 L 1116 556 Q 1116 596 1076 596 L 604 596 Q 564 596 564 556 Z`, at: 50, color: "#FFE3A8" },
  { d: `M 1740 450 L 2260 450 L 2260 600 L 1740 600 Z`, at: 112, color: "#F36440" },
  { d: circ(2180, 505, 26), at: 116, color: "#FFC94A" },
  { d: `M 3020 640 L 3020 560 L 3090 560 L 3090 640 Z`, at: 164, color: "#FFC94A" },
  { d: `M 3120 640 L 3120 510 L 3190 510 L 3190 640 Z`, at: 167, color: "#F36440" },
  { d: `M 3220 640 L 3220 468 L 3290 468 L 3290 640 Z`, at: 170, color: "#9B8AE0" },
  { d: `M 4190 420 L 4450 420 L 4450 466 L 4190 466 Z`, at: 214, color: "#8FB3EA" },
  { d: `M 4196 752 L 4196 736 L 4262 690 L 4326 708 L 4396 632 L 4450 650 L 4450 752 Z`, at: 220, color: "#9B8AE0" },
];
const LABELS = [
  { text: "a website", x: 2000, at: 116 },
  { text: "a deck", x: 3210, at: 170 },
  { text: "a report", x: 4320, at: 220 },
];
const MARK_C = { x: 5400, y: 530, s: 460 };
const MARK_DRAW = [226, 262];
const MARK_FILL = 256;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const ease = (v: number) => {
  const k = clamp01(v);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
/** Camera centre: holds on each drawing, eases between them. */
const CAM: [number, number, number][] = [
  [0, 56, 840],
  [84, 112, 2000],
  [136, 164, 3210],
  [188, 210, 4320],
  [238, 999, MARK_C.x],
];
const camAt = (t: number) => {
  for (let i = 0; i < CAM.length; i++) {
    const [a, b, x] = CAM[i];
    if (t <= b) {
      if (t >= a || i === 0) return x;
      const [, pb, px] = CAM[i - 1];
      return px + (x - px) * ease((t - pb) / (a - pb));
    }
  }
  return CAM[CAM.length - 1][2];
};

export const LineDemo: React.FC = () => {
  const t = useCurrentFrame();
  const cx = camAt(t);
  const pen = chainPen(MAIN, t);
  const drawing = t >= 4 && t < 238;
  const bubbleText = "Plan my café launch";
  const typed = bubbleText.slice(0, Math.floor(clamp01((t - 40) / 20) * bubbleText.length));
  const ms = MARK_C.s / MARK_VB;
  const markU = clamp01((t - MARK_DRAW[0]) / (MARK_DRAW[1] - MARK_DRAW[0]));
  const markFill = ease((t - MARK_FILL) / 16);
  const slogan = ease((t - 266) / 18);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Paper />
      <SketchDefs id="ln-boil" t={t} hold={3} scale={2.4} freq={0.03} region={[0, 0, 1920, 1080]} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <g filter="url(#ln-boil)">
          <g transform={`translate(${960 - cx} 0)`}>
            {/* colour arrives after the line: slightly off-register, like a print */}
            {FILLS.map((f, i) => {
              const k = ease((t - f.at) / 12);
              return k > 0 ? <path key={i} d={f.d} fill={f.color} opacity={0.9 * k} transform={`translate(${9 * k} ${9 * k})`} /> : null;
            })}
            <path d={MARK_D} fill="#F36440" opacity={markFill} transform={`translate(${MARK_C.x - MARK_C.s / 2 + 12 * markFill} ${MARK_C.y - MARK_C.s / 2 + 12 * markFill}) scale(${ms})`} />
            <Oneline segs={MAIN} t={t} width={5} color={INK} />
            {DETAILS.map((d, i) => (
              <Stroke key={i} d={d.d} u={ease((t - d.a) / (d.b - d.a))} width={d.w ?? 5} color={INK} />
            ))}
            <Stroke d={MARK_D} u={markU} width={4.5} color={INK} nonScaling transform={`translate(${MARK_C.x - MARK_C.s / 2} ${MARK_C.y - MARK_C.s / 2}) scale(${ms})`} />
            {drawing && <circle cx={pen.x} cy={pen.y} r={8} fill={INK} />}
          </g>
        </g>
      </svg>
      {/* hand-lettered words sit on the paper, outside the boil so they stay readable */}
      <div style={{ position: "absolute", left: 560 + 960 - cx, width: 560, top: 404, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 70, color: INK, lineHeight: 1 }}>{typed}</div>
      {LABELS.map((l) => {
        const k = ease((t - l.at) / 14);
        return (
          <div key={l.text} style={{ position: "absolute", left: l.x - 200 + 960 - cx, width: 400, top: B + 26 + (1 - k) * 10, textAlign: "center", opacity: k, fontFamily: HAND, fontWeight: 600, fontSize: 52, color: INK }}>
            {l.text}
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: B + 44 + (1 - slogan) * 12, textAlign: "center", opacity: slogan, fontFamily: SLAB, fontWeight: 500, fontSize: 56, color: INK, letterSpacing: "-0.01em" }}>
        From answers to outcomes.
      </div>
      <AbsoluteFill style={{ background: "#F6F1E7", opacity: 1 - clamp01(t / 8), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

