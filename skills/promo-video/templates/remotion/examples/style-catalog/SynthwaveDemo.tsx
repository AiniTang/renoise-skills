import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ChromeText, HORIZON, NeonGrid, Palm, project, RoadSign, StripedSun, SYN, SynthSky, VhsOverlay, WireMountains } from "../cinematic/retro";
import { fam } from "../cinematic/type";

/** 12 · 复古 Synthwave — "YouWare Drive": a night drive toward a sun with the mark, four exits rush past, chrome title. 330 frames. */
export const SYNTH_LEN = 330;
const DISPLAY = fam("Bricolage Grotesque");
const SANS = fam("Manrope");
const MONO = fam("Geist Mono");
const HAND = fam("Caveat");

const SIGNS = [
  { at: 50, side: -1 as const, title: "WEBSITES", sub: "EXIT 1" },
  { at: 95, side: 1 as const, title: "SLIDES", sub: "EXIT 2" },
  { at: 140, side: -1 as const, title: "SHEETS", sub: "EXIT 3" },
  { at: 185, side: 1 as const, title: "REPORTS", sub: "EXIT 4" },
];

const Road: React.FC<{ t: number }> = ({ t }) => {
  const a = project(-1.7, 0.35);
  const b = project(1.7, 0.35);
  const dash = Array.from({ length: 18 }, (_, i) => i * 1.4 + 0.5 - ((t * 0.12) % 1.4)).filter((z) => z > 0.4);
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <polygon points={`960,${HORIZON} ${a.sx},${a.sy} ${b.sx},${b.sy}`} fill="rgba(10,2,24,0.85)" />
      <line x1={960} y1={HORIZON} x2={a.sx} y2={a.sy} stroke={SYN.cyan} strokeWidth={3} style={{ filter: `drop-shadow(0 0 6px ${SYN.cyan})` }} />
      <line x1={960} y1={HORIZON} x2={b.sx} y2={b.sy} stroke={SYN.cyan} strokeWidth={3} style={{ filter: `drop-shadow(0 0 6px ${SYN.cyan})` }} />
      {dash.map((z, i) => {
        const p0 = project(0, z + 0.5);
        const p1 = project(0, z);
        return <line key={i} x1={p0.sx} y1={p0.sy} x2={p1.sx} y2={p1.sy} stroke={SYN.yellow} strokeWidth={Math.max(1.5, 14 / z)} opacity={0.9} />;
      })}
    </svg>
  );
};

const Car: React.FC<{ t: number }> = ({ t }) => {
  const k = Math.min(1, Math.max(0, (t - 8) / 22));
  const e = 1 - Math.pow(1 - k, 3);
  const sway = Math.sin(t * 0.07) * 8;
  const glow = 0.8 + 0.2 * Math.sin(t * 0.9);
  return (
    <svg width={560} height={260} viewBox="0 0 560 260" style={{ position: "absolute", left: 960 - 280 + sway, top: 790 + (1 - e) * 300, overflow: "visible" }}>
      <ellipse cx={280} cy={236} rx={250} ry={18} fill="rgba(0,0,0,0.55)" />
      <path d="M 70 150 L 120 70 Q 130 56 150 56 L 410 56 Q 430 56 440 70 L 490 150 Z" fill="#1B0A30" stroke={SYN.magenta} strokeWidth={3} />
      <path d="M 140 70 L 420 70 L 452 142 L 108 142 Z" fill="#0C0418" stroke="#6A2FA0" strokeWidth={2} />
      <rect x={40} y={140} width={480} height={80} rx={14} fill="#241040" stroke={SYN.magenta} strokeWidth={3} />
      <rect x={60} y={158} width={440} height={16} rx={6} fill="#FF2B55" opacity={glow} style={{ filter: "drop-shadow(0 0 14px #FF2B55)" }} />
      <rect x={220} y={184} width={120} height={26} rx={4} fill="#EDE6FF" />
      <text x={280} y={204} textAnchor="middle" fontFamily={MONO} fontSize={17} fontWeight={600} fill="#241040" letterSpacing="0.12em">
        YOUWARE
      </text>
      <rect x={52} y={216} width={80} height={22} rx={6} fill="#0C0418" />
      <rect x={428} y={216} width={80} height={22} rx={6} fill="#0C0418" />
    </svg>
  );
};

export const SynthwaveDemo: React.FC = () => {
  const t = useCurrentFrame();
  const rise = Math.min(1, t / 40);
  const scriptOn = t >= 248 && (t > 262 || Math.floor(t / 3) % 2 === 0);
  return (
    <AbsoluteFill style={{ background: SYN.night, overflow: "hidden" }}>
      <SynthSky t={t} />
      <StripedSun t={t} r={260} mark="brand/mark.svg" rise={1 - Math.pow(1 - rise, 3)} />
      <WireMountains />
      <NeonGrid t={t} />
      <Road t={t} />
      <Palm x={150} y={HORIZON + 40} s={1.05} sway={Math.sin(t * 0.05) * 3} />
      <Palm x={330} y={HORIZON + 10} s={0.7} sway={Math.sin(t * 0.05 + 1) * 3} />
      <Palm x={1770} y={HORIZON + 40} s={1.05} flip sway={Math.sin(t * 0.05 + 2) * 3} />
      <Palm x={1590} y={HORIZON + 10} s={0.7} flip sway={Math.sin(t * 0.05 + 3) * 3} />
      {SIGNS.map((s) => (
        <RoadSign key={s.title} t={t} at={s.at} side={s.side} title={s.title} sub={s.sub} family={SANS} mono={MONO} color={s.side < 0 ? SYN.cyan : SYN.pink} />
      ))}
      <Car t={t} />
      <ChromeText text="YOUWARE" family={DISPLAY} size={190} y={300} t={t} at={228} />
      {scriptOn && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 404, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 84, color: "#FFE6F7", textShadow: `0 0 10px ${SYN.pink}, 0 0 26px ${SYN.magenta}, 0 0 52px ${SYN.magenta}`, transform: "rotate(-4deg)" }}>
          from answers to outcomes
        </div>
      )}
      <VhsOverlay t={t} mono={MONO} osd={t < 150 ? "PLAY ▶" : "YOUWARE · SIDE A"} />
    </AbsoluteFill>
  );
};
