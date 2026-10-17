import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { step as stepS } from "../cinematic/spring";
import { fam } from "../cinematic/type";
import { MARK_SIDES, MARK_VB } from "./markPath";

/**
 * 11 · 包豪斯动态海报 — "YouWare, in primary geometry": circle / square / triangle choreograph a YOU·WARE poster,
 * split into a 2×2 grid of the four kinds of work, then rebuild the mark from eight primary-colour arches. 330 frames.
 */
export const BAUHAUS_LEN = 330;
const GEO = fam("Unbounded");
const SANS = fam("Manrope");
const C = { paper: "#EDE6D6", red: "#D93A2B", blue: "#1E4FA3", yellow: "#F2B705", black: "#161616" };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const out3 = (v: number) => 1 - Math.pow(1 - clamp01(v), 3);
const inOut = (v: number) => {
  const k = clamp01(v);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
const sp = (f: number, w = 3, z = 0.55) => stepS(f / 30, { w: 2 * Math.PI * w, z });

/* ---------- act 1: the poster ---------- */
const Poster: React.FC<{ t: number }> = ({ t }) => {
  const gone = inOut((t - 78) / 16);
  if (gone >= 1) return null;
  const roll = out3((t - 6) / 30);
  const cx = 2250 + (700 - 2250) * roll;
  const rot = ((cx - 700) / 250) * (180 / Math.PI) * -1 + t * 0.4;
  const sq = sp(t - 14, 2.6, 0.5);
  const tri = sp(t - 20, 2.4, 0.6);
  const bar = out3((t - 2) / 12);
  const line = out3((t - 44) / 16);
  const shrink = 1 - gone;
  const g = (x: number, y: number) => `translate(${x} ${y}) scale(${shrink}) translate(${-x} ${-y})`;
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <rect x={140} y={-1080 + 1080 * bar} width={46} height={1080} fill={C.black} transform={`translate(0 ${-gone * 1100})`} />
      <line x1={260} y1={980} x2={260 + 1400 * line} y2={980 - 700 * line} stroke={C.black} strokeWidth={6} opacity={shrink} />
      <g transform={g(700, 560)}>
        <g transform={`translate(${cx} 560) rotate(${rot})`}>
          <circle r={250} fill={C.red} />
          <path d="M 0 -250 A 250 250 0 0 1 250 0 L 0 0 Z" fill={C.black} />
          <circle cx={-110} cy={90} r={34} fill={C.paper} />
        </g>
      </g>
      <g transform={g(1360, 330)}>
        <rect x={1180} y={-420 + 570 * sq} width={360} height={360} fill={C.blue} transform={`rotate(${(1 - sq) * 20} 1360 ${-240 + 570 * sq})`} />
      </g>
      <g transform={g(1440, 760)}>
        <polygon points="1440,560 1670,960 1210,960" fill={C.yellow} transform={`translate(0 ${(1 - tri) * 600}) rotate(${(1 - tri) * -30} 1440 820)`} style={{ mixBlendMode: "multiply" }} />
      </g>
    </svg>
  );
};

const Word: React.FC<{ text: string; t: number; at: number; x: number; y: number; size: number; align?: "left" | "right"; color?: string; gone?: number }> = ({ text, t, at, x, y, size, align = "left", color = C.black, gone = 0 }) => (
  <div style={{ position: "absolute", left: align === "left" ? x : undefined, right: align === "right" ? 1920 - x : undefined, top: y, display: "flex", fontFamily: GEO, fontWeight: 900, fontSize: size, lineHeight: 0.9, color, letterSpacing: "-0.03em", overflow: "hidden", paddingBottom: 8 }}>
    {Array.from(text).map((ch, i) => {
      const k = sp(t - at - i * 3, 2.8, 0.7);
      const out = inOut((gone - i * 0.08) / 0.7);
      return (
        <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - k) * 110 + out * -120}%)`, whiteSpace: "pre" }}>
          {ch}
        </span>
      );
    })}
  </div>
);

/* ---------- act 2: the grid ---------- */
const PANELS = [
  { bg: C.blue, ink: C.paper, no: "01", name: "WEBSITES", from: "left" },
  { bg: C.yellow, ink: C.black, no: "02", name: "SLIDES", from: "top" },
  { bg: C.paper, ink: C.black, no: "03", name: "SHEETS", from: "bottom" },
  { bg: C.red, ink: C.paper, no: "04", name: "REPORTS", from: "right" },
];
const PW = 955;
const PH = 535;
const GRID_IN = 86;
const GRID_OUT = 192;

const PanelArt: React.FC<{ i: number; t: number }> = ({ i, t }) => {
  const k = (d: number) => sp(t - GRID_IN - i * 12 - d, 2.6, 0.6);
  if (i === 0)
    return (
      <g>
        <rect x={250} y={110 + (1 - k(8)) * 60} width={460} height={290} fill={C.paper} opacity={clamp01(k(8) * 2)} />
        <rect x={250} y={110 + (1 - k(8)) * 60} width={460} height={44} fill={C.black} opacity={clamp01(k(8) * 2)} />
        <circle cx={600} cy={290} r={80 * k(14)} fill={C.red} />
        <rect x={290} y={220} width={180 * k(18)} height={26} fill={C.blue} />
        <rect x={290} y={270} width={120 * k(20)} height={26} fill={C.black} />
      </g>
    );
  if (i === 1) {
    const a = k(12);
    return (
      <g>
        <line x1={400} y1={400} x2={340} y2={400 + 110 * k(6)} stroke={C.black} strokeWidth={14} />
        <line x1={560} y1={400} x2={620} y2={400 + 110 * k(6)} stroke={C.black} strokeWidth={14} />
        <rect x={250} y={100} width={460} height={300 * k(4)} fill={C.paper} />
        <path d={`M 330 360 A 110 110 0 0 1 ${330 + 220 * a} 360 Z`} fill={C.blue} opacity={a > 0.02 ? 1 : 0} />
        <polygon points={`560,${360 - 200 * k(16)} 660,360 560,360`} fill={C.red} />
      </g>
    );
  }
  if (i === 2)
    return (
      <g>
        {Array.from({ length: 12 }, (_, j) => {
          const col = j % 4;
          const row = Math.floor(j / 4);
          const s = k(4 + j * 2);
          const fill = [C.black, C.blue, C.red, C.yellow][(col + row) % 4];
          return <rect key={j} x={260 + col * 112 + 48 * (1 - s)} y={110 + row * 100 + 44 * (1 - s)} width={96 * s} height={88 * s} fill={fill} />;
        })}
      </g>
    );
  return (
    <g>
      {[260, 190, 120].map((r, j) => {
        const a = k(6 + j * 6) * (Math.PI / 2) * (0.55 + j * 0.2);
        const x0 = 290;
        const y0 = 420;
        return <path key={j} d={`M ${x0} ${y0 - r} A ${r} ${r} 0 0 1 ${x0 + Math.sin(a) * r} ${y0 - Math.cos(a) * r}`} fill="none" stroke={[C.paper, C.black, C.yellow][j]} strokeWidth={46} />;
      })}
      <rect x={290} y={420} width={420 * k(20)} height={14} fill={C.black} />
    </g>
  );
};

const Grid: React.FC<{ t: number }> = ({ t }) => {
  if (t < GRID_IN - 4) return null;
  const lines = out3((t - GRID_IN + 4) / 12);
  const collapse = inOut((t - GRID_OUT) / 22);
  if (collapse >= 1) return null;
  return (
    <AbsoluteFill style={{ transform: `scale(${1 - collapse * 0.55}) rotate(${collapse * 18}deg)`, opacity: 1 - clamp01((collapse - 0.5) * 2) }}>
      {PANELS.map((p, i) => {
        const x = (i % 2) * (PW + 10);
        const y = Math.floor(i / 2) * (PH + 10);
        const w = out3((t - GRID_IN - i * 12) / 14);
        const clip = p.from === "left" ? `inset(0 ${100 - w * 100}% 0 0)` : p.from === "right" ? `inset(0 0 0 ${100 - w * 100}%)` : p.from === "top" ? `inset(0 0 ${100 - w * 100}% 0)` : `inset(${100 - w * 100}% 0 0 0)`;
        const lab = out3((t - GRID_IN - i * 12 - 18) / 14);
        return (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: PW, height: PH, background: p.bg, clipPath: clip, overflow: "hidden" }}>
            <svg width={PW} height={PH} style={{ position: "absolute", inset: 0 }}>
              <PanelArt i={i} t={t} />
            </svg>
            <div style={{ position: "absolute", left: 52, top: 40, fontFamily: GEO, fontWeight: 800, fontSize: 64, color: p.ink, transform: `translateX(${(1 - lab) * -40}px)`, opacity: lab }}>{p.no}</div>
            <div style={{ position: "absolute", right: 52, bottom: 40, fontFamily: GEO, fontWeight: 800, fontSize: 52, color: p.ink, letterSpacing: "-0.01em", transform: `translateX(${(1 - lab) * 40}px)`, opacity: lab }}>{p.name}</div>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 955, top: 0, width: 10, height: 1080 * lines, background: C.black }} />
      <div style={{ position: "absolute", left: 0, top: 535, height: 10, width: 1920 * lines, background: C.black }} />
    </AbsoluteFill>
  );
};

/* ---------- act 3: the mark, rebuilt from four primary-colour sides ---------- */
// Each side of the mark flies home from the grid panel of the same colour.
const SIDES: { k: "N" | "E" | "S" | "W"; color: string; from: [number, number]; spin: number }[] = [
  { k: "W", color: C.blue, from: [-760, -520], spin: -140 },
  { k: "N", color: C.yellow, from: [760, -520], spin: 120 },
  { k: "E", color: C.red, from: [760, 520], spin: -110 },
  { k: "S", color: C.black, from: [-760, 520], spin: 150 },
];
const MARK_AT = 206;
const MARK_PX = 440;
const Arches: React.FC<{ t: number }> = ({ t }) => {
  if (t < MARK_AT - 2) return null;
  const spin = Math.max(0, t - MARK_AT - 34) * 0.12;
  const ring = out3((t - MARK_AT - 16) / 30);
  const s = MARK_PX / MARK_VB;
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <circle cx={960} cy={500} r={320} fill="none" stroke={C.black} strokeWidth={4} strokeDasharray={`${2011 * ring} 2100`} transform="rotate(-90 960 500)" />
      <g transform={`translate(960 500) rotate(${spin})`}>
        {SIDES.map((d, i) => {
          const k = sp(t - MARK_AT - i * 4, 2.1, 0.66);
          return (
            <g key={d.k} transform={`translate(${d.from[0] * (1 - k)} ${d.from[1] * (1 - k)}) rotate(${d.spin * (1 - k)}) scale(${s}) translate(${-MARK_VB / 2} ${-MARK_VB / 2})`}>
              <path d={MARK_SIDES[d.k]} fill={d.color} fillRule="evenodd" />
            </g>
          );
        })}
      </g>
      <circle cx={960 + 300 * Math.cos(-0.9)} cy={500 + 300 * Math.sin(-0.9)} r={22 * out3((t - MARK_AT - 40) / 10)} fill={C.red} />
    </svg>
  );
};

export const BauhausDemo: React.FC = () => {
  const t = useCurrentFrame();
  const posterGone = clamp01((t - 76) / 14);
  const tail = out3((t - 250) / 14);
  return (
    <AbsoluteFill style={{ background: C.paper, overflow: "hidden" }}>
      <Poster t={t} />
      {t < 96 && (
        <>
          <Word text="YOU" t={t} at={28} x={240} y={70} size={300} gone={posterGone} />
          <Word text="WARE" t={t} at={36} x={1850} y={770} size={300} align="right" gone={posterGone} />
        </>
      )}
      <Grid t={t} />
      <Arches t={t} />
      {t >= 236 && (
        <>
          <Word text="FROM ANSWERS" t={t} at={236} x={100} y={880} size={84} />
          <Word text="TO OUTCOMES" t={t} at={246} x={1820} y={966} size={84} align="right" color={C.red} />
        </>
      )}
      <div style={{ position: "absolute", left: 100, top: 90, opacity: tail, transform: `translateY(${(1 - tail) * -12}px)` }}>
        <Img src={staticFile("brand/lockup.svg")} style={{ height: 70 }} />
      </div>
      <div style={{ position: "absolute", right: 100, top: 108, opacity: tail, fontFamily: SANS, fontWeight: 700, fontSize: 26, letterSpacing: "0.2em", color: C.black }}>FOUR KINDS OF WORK · ONE MARK</div>
    </AbsoluteFill>
  );
};
