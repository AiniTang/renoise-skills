import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { dropAt, GlossyDefs, Reflect } from "../cinematic/glossy";
import { fam } from "../cinematic/type";

/**
 * 14 · 液态流动 — "One pour": four glossy brand-colour drops (websites / slides / sheets / reports) fall, merge into
 * one marbled blob, spread into a puddle and rise as the liquid YouWare wordmark. 330 frames.
 */
export const LIQUID_LEN = 330;
const DISPLAY = fam("Bricolage Grotesque");
const SANS = fam("Manrope");
const SLAB = fam("Hepta Slab");

const FLOOR = 700;
const R = 76;
const INK = "#1D1A24";
const DROPS = [
  { x: 600, at: 40, color: "#F36440", label: "Websites" },
  { x: 840, at: 52, color: "#FFC94A", label: "Slides" },
  { x: 1080, at: 64, color: "#7D6BC1", label: "Sheets" },
  { x: 1320, at: 76, color: "#2F6BD8", label: "Reports" },
];
const PROMPT = "Plan my café launch";
const MERGE = [130, 172];
const SPREAD = [206, 236];
const RISE = [226, 262];
const BASE = 672; // wordmark baseline

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const ease = (v: number) => {
  const k = clamp01(v);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
const out3 = (v: number) => 1 - Math.pow(1 - clamp01(v), 3);

type El = { x: number; y: number; rx: number; ry: number; color: string };

const shapes = (t: number): El[] => {
  const m = ease((t - MERGE[0]) / (MERGE[1] - MERGE[0]));
  const bigR = R * 2;
  const spread = ease((t - SPREAD[0]) / (SPREAD[1] - SPREAD[0]));
  const rise = ease((t - RISE[0]) / (RISE[1] - RISE[0]));
  const els: El[] = [];
  DROPS.forEach((d, i) => {
    const p = dropAt(t, d.at, d.x, R, FLOOR, 196, 960 + (i - 1.5) * 36);
    if (!p) return;
    if (m <= 0) {
      els.push({ ...p, color: d.color });
      return;
    }
    // slide toward the centre, stretching into the neighbour; grow so the area is conserved
    const x = p.x + (960 - p.x) * m;
    const stretch = Math.sin(m * Math.PI) * 0.35;
    const r = R + (bigR * 0.62 - R) * m;
    // inside the merged blob the colours keep swirling (marbling)
    const swirl = clamp01((t - MERGE[1] + 16) / 30);
    const ang = i * (Math.PI / 2) + (t - MERGE[1]) * 0.05 * swirl;
    const orbit = bigR * 0.42 * swirl;
    const cx = x + Math.cos(ang) * orbit;
    const cy = p.y + (FLOOR - bigR - p.y) * m + Math.sin(ang) * orbit * 0.8;
    // spread: each colour flows to its own stretch of the puddle, in the wordmark's gradient order
    const px = 960 + (i - 1.5) * 280;
    const gone = 1 - rise;
    els.push({
      x: cx + (px - cx) * spread,
      y: cy + (FLOOR - 34 - cy) * spread,
      rx: (r * (1 + stretch) + (230 - r * (1 + stretch)) * spread) * (0.25 + 0.75 * gone),
      ry: (r * (1 - stretch * 0.4) + (36 - r * (1 - stretch * 0.4)) * spread) * gone,
      color: d.color,
    });
  });
  if (m > 0 && spread < 1) {
    // the body that holds the marbled colours; it thins out as the colours spread
    const breathe = 1 + Math.sin((t - MERGE[1]) * 0.12) * 0.025 * clamp01((t - MERGE[1]) / 10);
    const body = bigR * m * breathe * (1 - spread);
    els.unshift({ x: 960, y: FLOOR - body * 0.98, rx: body, ry: body, color: "#9A6FC4" });
  }
  return els;
};

const LiquidLayer: React.FC<{ t: number; lightX: number }> = ({ t, lightX }) => {
  const els = shapes(t);
  const rise = ease((t - RISE[0]) / (RISE[1] - RISE[0]));
  const wob = t > RISE[1] ? Math.sin((t - RISE[1]) * 0.5) * Math.exp(-(t - RISE[1]) / 9) * 0.05 : 0;
  const k = clamp01((t - SPREAD[0]) / (RISE[1] - SPREAD[0]));
  const blur = 15 - 6 * k;
  const dome = 30 - 19 * k;
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <defs>
        <linearGradient id="lq-word" x1={430} y1={0} x2={1490} y2={0} gradientUnits="userSpaceOnUse">
          <stop offset={0} stopColor="#F36440" />
          <stop offset={0.34} stopColor="#FFB23F" />
          <stop offset={0.66} stopColor="#8B6FD6" />
          <stop offset={1} stopColor="#2F6BD8" />
        </linearGradient>
        <clipPath id="lq-floor">
          <rect x={0} y={0} width={1920} height={FLOOR - 4} />
        </clipPath>
      </defs>
      <GlossyDefs id="lq" blur={blur} dome={dome} light={[lightX, 150, 380]} spec={1.3} shine={38} />
      <g filter="url(#lq)">
        {els.map((e, i) => (
          <ellipse key={i} cx={e.x} cy={e.y} rx={Math.max(0, e.rx)} ry={Math.max(0, e.ry)} fill={e.color} />
        ))}
        {rise > 0 && (
          <g clipPath="url(#lq-floor)">
            <text
              x={960}
              y={BASE + (1 - rise) * 250}
              textAnchor="middle"
              fontFamily={DISPLAY}
              fontWeight={800}
              fontSize={272}
              letterSpacing="-0.02em"
              fill="url(#lq-word)"
              transform={`translate(960 ${BASE}) scale(${1 + (1 - rise) * 0.18 - wob} ${1 - (1 - rise) * 0.25 + wob}) translate(-960 ${-BASE})`}
            >
              YouWare
            </text>
          </g>
        )}
      </g>
    </svg>
  );
};

const Shadows: React.FC<{ t: number }> = ({ t }) => {
  const m = ease((t - MERGE[0]) / (MERGE[1] - MERGE[0]));
  const spread = ease((t - SPREAD[0]) / (SPREAD[1] - SPREAD[0]));
  const rise = ease((t - RISE[0]) / (RISE[1] - RISE[0]));
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, filter: "blur(14px)" }}>
      {DROPS.map((d, i) => {
        const p = dropAt(t, d.at, d.x, R, FLOOR, 196, 960 + (i - 1.5) * 36);
        if (!p) return null;
        const h = clamp01(1 - (FLOOR - p.y - p.ry) / 260);
        const x = p.x + (960 - p.x) * m;
        return <ellipse key={i} cx={x} cy={FLOOR + 6} rx={p.rx * (0.6 + 0.4 * h) * (1 - m)} ry={14 * h} fill="rgba(40,20,50,0.28)" opacity={h} />;
      })}
      {m > 0 && <ellipse cx={960} cy={FLOOR + 8} rx={(R * 2 * 0.95 + 560 * spread) * m * (1 - rise * 0.2)} ry={20} fill="rgba(40,20,50,0.26)" />}
    </svg>
  );
};

export const LiquidDemo: React.FC = () => {
  const t = useCurrentFrame();
  const fadeIn = clamp01(t / 10);
  const typed = PROMPT.slice(0, Math.floor(clamp01((t - 8) / 26) * PROMPT.length));
  const pill = clamp01((t - 2) / 8) * (1 - clamp01((t - 120) / 12));
  const lightX = 960 - 340 * ease((t - 200) / 50) + 760 * ease((t - 262) / 60);
  const sub = out3((t - 266) / 18);
  return (
    <AbsoluteFill style={{ background: "#EFE8DF", overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 50% 30%, #FBF7F2 0%, #F1EAE1 55%, #E6DCD0 100%)` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: FLOOR, bottom: 0, background: "linear-gradient(180deg, #E3D8CB 0%, #EFE8DF 60%)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: FLOOR - 1, height: 2, background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent)" }} />
      <Shadows t={t} />
      <Reflect floorY={FLOOR} opacity={0.26} depth={150}>
        <LiquidLayer t={t} lightX={lightX} />
      </Reflect>
      {/* prompt pill */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center", opacity: pill }}>
        <div style={{ padding: "22px 34px", borderRadius: 999, background: "rgba(255,255,255,0.78)", boxShadow: "0 14px 40px rgba(60,40,70,0.12)", fontFamily: SANS, fontWeight: 600, fontSize: 38, color: INK, display: "flex", alignItems: "center", gap: 18 }}>
          <span style={{ width: 14, height: 14, borderRadius: 7, background: "#F36440" }} />
          <span>{typed}</span>
          <span style={{ width: 3, height: 40, background: INK, opacity: Math.floor(t / 8) % 2 === 0 && t < 60 ? 1 : 0 }} />
        </div>
      </div>
      {/* labels over the landed drops */}
      {DROPS.map((d) => {
        const on = out3((t - d.at - 38) / 12) * (1 - clamp01((t - MERGE[0]) / 10));
        return (
          <div key={d.label} style={{ position: "absolute", left: d.x - 120, width: 240, top: FLOOR - 2 * R - 74 + (1 - on) * 14, textAlign: "center", opacity: on, fontFamily: SANS, fontWeight: 700, fontSize: 30, color: INK, letterSpacing: "0.01em" }}>
            {d.label}
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 0, right: 0, top: 872 + (1 - sub) * 16, textAlign: "center", opacity: sub, fontFamily: SLAB, fontWeight: 500, fontSize: 50, color: INK, letterSpacing: "-0.01em" }}>
        From answers to outcomes.
      </div>
      <AbsoluteFill style={{ background: "#EFE8DF", opacity: 1 - fadeIn, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
