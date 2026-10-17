import React from "react";
import { random } from "remotion";
import { getLength } from "@remotion/paths";
import { step, type SpringCfg } from "../spring";

/*
 * Sticker explainer kit (贴纸风): a die-cut white outline around any content (PNG with alpha, SVG, DOM, a screenshot),
 * a "slap" landing (big → overshoot → settle, shadow tightening as it touches down), washi tape, hand-drawn doodles and
 * label stickers. Mount <StickerDefs /> once per composition. Frames are local (30 fps).
 */

const hz = (f: number) => 2 * Math.PI * f;
export const SLAP: SpringCfg = { w: hz(4.2), z: 0.45 };
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** SVG filters for die-cut outlines of a few thicknesses: `url(#stk-8)`, `url(#stk-12)`, `url(#stk-18)`. */
export const StickerDefs: React.FC<{ sizes?: number[]; color?: string }> = ({ sizes = [6, 8, 12, 18], color = "#FFFFFF" }) => (
  <svg width={0} height={0} style={{ position: "absolute" }}>
    <defs>
      {sizes.map((r) => (
        <filter key={r} id={`stk-${r}`} x="-30%" y="-30%" width="160%" height="160%" colorInterpolationFilters="sRGB">
          <feMorphology in="SourceAlpha" operator="dilate" radius={r} result="grow" />
          <feGaussianBlur in="grow" stdDeviation={Math.max(1, r * 0.35)} result="soft" />
          <feComponentTransfer in="soft" result="cut">
            <feFuncA type="table" tableValues="0 0 0.6 1 1" />
          </feComponentTransfer>
          <feFlood floodColor={color} result="paper" />
          <feComposite in="paper" in2="cut" operator="in" result="outline" />
          <feMerge>
            <feMergeNode in="outline" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      ))}
    </defs>
  </svg>
);

/**
 * One sticker. `x, y` = centre. Lands at `at` with a slap; idles with a tiny breath; `out` peels it away.
 * The die-cut follows the content's alpha, so transparent PNGs get a contour cut and rounded boxes a rounded one.
 */
export const Sticker: React.FC<{
  t: number;
  at: number;
  x: number;
  y: number;
  rotate?: number;
  border?: 6 | 8 | 12 | 18;
  out?: number;
  from?: "above" | "left" | "right";
  children: React.ReactNode;
  lift?: number; // resting shadow offset
}> = ({ t, at, x, y, rotate = 0, border = 12, out, from = "above", children, lift = 10 }) => {
  const lt = (t - at) / 30;
  if (lt < 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 8) : 0;
  if (leave >= 1) return null;
  const k = step(lt, SLAP);
  const inAir = 1 - clamp01(lt * 5);
  const scale = 1 + 0.35 * (1 - k);
  const dx = from === "left" ? -(1 - k) * 260 : from === "right" ? (1 - k) * 260 : 0;
  const dy = from === "above" ? -(1 - k) * 60 : 0;
  const rot = rotate + (1 - k) * (random(`r${at}`) > 0.5 ? 14 : -14);
  const sh = lift + 36 * inAir;
  const blur = 8 + 30 * inAir;
  const breath = 1 + 0.004 * Math.sin((t - at) / 30 * 2.2 + at);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) translate(${dx}px, ${dy - leave * 40}px) rotate(${rot + leave * 8}deg) scale(${scale * breath * (1 - 0.1 * leave)})`,
        opacity: clamp01(lt * 8) * (1 - leave),
        filter: `url(#stk-${border}) drop-shadow(0 ${sh}px ${blur}px rgba(40,30,10,${0.18 + 0.1 * inAir}))`,
      }}
    >
      {children}
    </div>
  );
};

/** A strip of washi tape with torn ends. */
export const Tape: React.FC<{ t: number; at: number; x: number; y: number; w?: number; h?: number; rotate?: number; color?: string; out?: number }> = ({
  t,
  at,
  x,
  y,
  w = 170,
  h = 44,
  rotate = -12,
  color = "rgba(238,140,108,0.72)",
  out,
}) => {
  const lt = (t - at) / 30;
  if (lt < 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 8) : 0;
  if (leave >= 1) return null;
  const k = step(lt, SLAP);
  const teeth = 7;
  const edge = (side: number) =>
    Array.from({ length: teeth + 1 }, (_, i) => {
      const yy = (i / teeth) * 100;
      const xx = side === 0 ? (i % 2 ? 5 : 0) : i % 2 ? 95 : 100;
      return `${xx}% ${yy}%`;
    });
  const clip = `polygon(${[...edge(0), ...edge(1).reverse()].join(", ")})`;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        transform: `translate(-50%, -50%) rotate(${rotate}deg) scaleX(${k})`,
        transformOrigin: "0% 50%",
        background: `repeating-linear-gradient(90deg, ${color} 0 14px, rgba(255,255,255,0.12) 14px 16px)`,
        clipPath: clip,
        opacity: 1 - leave,
        boxShadow: "0 2px 4px rgba(0,0,0,0.08)",
      }}
    />
  );
};

/** A label sticker: bold word on a coloured pill, die-cut white. */
export const Label: React.FC<{ text: string; family: string; size?: number; bg?: string; ink?: string; weight?: number }> = ({ text, family, size = 34, bg = "#151513", ink = "#FFFFFF", weight = 800 }) => (
  <div style={{ background: bg, color: ink, fontFamily: family, fontWeight: weight, fontSize: size, lineHeight: 1, padding: `${size * 0.32}px ${size * 0.62}px`, borderRadius: 999, letterSpacing: "0.02em", whiteSpace: "nowrap", fontSynthesis: "none" }}>
    {text}
  </div>
);

/** Hand-drawn doodle: a wobbly path drawn on like a marker stroke (arrows, circles, underlines). */
export const Doodle: React.FC<{ t: number; at: number; dur?: number; d: string; color?: string; width?: number; head?: boolean; out?: number }> = ({
  t,
  at,
  dur = 14,
  d,
  color = "#151513",
  width = 7,
  head = false,
  out,
}) => {
  const p = clamp01((t - at) / dur);
  if (p <= 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 6) : 0;
  if (leave >= 1) return null;
  const L = getLength(d);
  const e = 1 - Math.pow(1 - p, 2.2);
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, overflow: "visible", opacity: 1 - leave }}>
      <path d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${L * e} ${L + 1}`} />
      {head && e > 0.98 && <DoodleHead d={d} color={color} width={width} />}
    </svg>
  );
};

const DoodleHead: React.FC<{ d: string; color: string; width: number }> = ({ d, color, width }) => {
  // arrow head from the last two numbers pairs of the path
  const nums = d.match(/-?\d+\.?\d*/g)!.map(Number);
  const [x1, y1, x2, y2] = nums.slice(-4);
  const a = Math.atan2(y2 - y1, x2 - x1);
  const L = 26;
  const p = (da: number) => `${x2 - Math.cos(a + da) * L},${y2 - Math.sin(a + da) * L}`;
  return <polyline points={`${p(0.5)} ${x2},${y2} ${p(-0.5)}`} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" />;
};

/** Dotted cutting-mat / notebook board behind stickers. */
export const StickerBoard: React.FC<{ bg?: string; dot?: string; gap?: number }> = ({ bg = "#DCE7B8", dot = "rgba(21,21,19,0.16)", gap = 40 }) => (
  <div style={{ position: "absolute", inset: 0, background: bg, backgroundImage: `radial-gradient(${dot} 2px, transparent 2.5px)`, backgroundSize: `${gap}px ${gap}px`, backgroundPosition: `${gap / 2}px ${gap / 2}px` }}>
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.16, mixBlendMode: "multiply" }}>
      <filter id="board-grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={7} />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#board-grain)" />
    </svg>
  </div>
);
