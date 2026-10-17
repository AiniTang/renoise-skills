import React from "react";
import { Img, random, staticFile } from "remotion";

/*
 * Collage / scrapbook kit (拼贴风).
 * - `tornPath`: a rectangle with hand-torn edges (seeded), as an SVG path string usable in CSS `clip-path: path()`.
 * - `Torn`: a paper scrap — white fibrous rim + inner content clipped by a second, slightly inset tear.
 * - `Halftone`: a real halftone print of an image. Luminance (×0.5) + a radial dot screen (×0.5) are summed with
 *   `plus-lighter`, then `contrast()` thresholds the sum at 0.5, so dark areas get big dots and light areas small ones;
 *   `ink` recolours the dots (screen), and the paper shows through (multiply).
 * - `Ransom`: letters cut from different "magazines" (mixed fonts, papers, angles, scissor-cut corners).
 * - `jitter`: stop-motion wobble that changes on twos.
 */

export const tornPath = (w: number, h: number, seed: string, amp = 5, stepPx = 9, inset = 0) => {
  const pts: [number, number][] = [];
  const edge = (x0: number, y0: number, x1: number, y1: number, k: number) => {
    const len = Math.hypot(x1 - x0, y1 - y0);
    const n = Math.max(2, Math.round(len / stepPx));
    const nx = -(y1 - y0) / len;
    const ny = (x1 - x0) / len;
    for (let i = 0; i < n; i++) {
      const u = i / n;
      const r = (random(`${seed}-${k}-${i}`) - 0.5) * 2 * amp + (random(`${seed}-${k}-${i}-b`) > 0.85 ? amp * 0.9 : 0);
      pts.push([x0 + (x1 - x0) * u + nx * r, y0 + (y1 - y0) * u + ny * r]);
    }
  };
  const a = inset;
  edge(a, a, w - a, a, 0);
  edge(w - a, a, w - a, h - a, 1);
  edge(w - a, h - a, a, h - a, 2);
  edge(a, h - a, a, a, 3);
  return `M ${pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L ")} Z`;
};

/** Stop-motion wobble: small offset + rotation that changes every `hold` frames. */
export const jitter = (t: number, seed: string, px = 2, deg = 0.4, hold = 2) => {
  const k = Math.floor(t / hold);
  return { x: (random(`${seed}x${k}`) - 0.5) * 2 * px, y: (random(`${seed}y${k}`) - 0.5) * 2 * px, r: (random(`${seed}r${k}`) - 0.5) * 2 * deg };
};

export const Torn: React.FC<{ w: number; h: number; seed: string; rim?: string; amp?: number; children?: React.ReactNode; style?: React.CSSProperties; shadow?: boolean }> = ({ w, h, seed, rim = "#FBF8F1", amp = 5, children, style, shadow = true }) => (
  <div style={{ width: w, height: h, position: "relative", filter: shadow ? "drop-shadow(3px 6px 5px rgba(40,25,10,0.35))" : undefined, ...style }}>
    <div style={{ position: "absolute", inset: 0, background: rim, clipPath: `path('${tornPath(w, h, seed, amp)}')` }} />
    <div style={{ position: "absolute", inset: 0, clipPath: `path('${tornPath(w, h, `${seed}-in`, amp * 0.8, 7, amp + 5)}')`, overflow: "hidden" }}>{children}</div>
  </div>
);

export const Halftone: React.FC<{ src: string; w: number; h: number; cell?: number; ink?: string; paper?: string; fit?: { left: number; top: number; width: number } ; gain?: number }> = ({ src, w, h, cell = 7, ink = "#1D1A24", paper = "#F3E9D6", fit, gain = 1 }) => (
  <div style={{ width: w, height: h, position: "relative", background: paper, overflow: "hidden" }}>
    <div style={{ position: "absolute", inset: 0, mixBlendMode: "multiply" }}>
      <div style={{ position: "absolute", inset: 0, isolation: "isolate", filter: "contrast(40)", background: "#000" }}>
        <Img src={staticFile(src)} style={{ position: "absolute", left: fit?.left ?? 0, top: fit?.top ?? 0, width: fit?.width ?? w, filter: `grayscale(1) brightness(${0.5 * gain})` }} />
        <div style={{ position: "absolute", inset: 0, mixBlendMode: "plus-lighter", backgroundImage: "radial-gradient(circle at center, #000 0%, #808080 100%)", backgroundSize: `${cell}px ${cell}px` }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: ink, mixBlendMode: "screen" }} />
    </div>
  </div>
);

const RANSOM_FONTS = [
  { f: '"Anton", Impact, sans-serif', w: 400 },
  { f: '"DM Serif Display", Georgia, serif', w: 400 },
  { f: '"Bricolage Grotesque", sans-serif', w: 800 },
  { f: '"Hepta Slab", serif', w: 700 },
  { f: '"Unbounded", sans-serif', w: 900 },
  { f: '"Geist Mono", monospace', w: 700 },
  { f: '"Fredoka", sans-serif', w: 700 },
];
const PAPERS = [
  ["#FFFFFF", "#1D1A24"],
  ["#1D1A24", "#FFFFFF"],
  ["#F36440", "#FFFFFF"],
  ["#FFD15C", "#1D1A24"],
  ["#ADC8E6", "#1D1A24"],
  ["#7D6BC1", "#FFFFFF"],
  ["#F2E6CF", "#C94A2C"],
];

/** Ransom-note word. Letters land one by one from `at` (every `gap` frames), each with a slap. */
export const Ransom: React.FC<{ text: string; t: number; at: number; size: number; seed: string; gap?: number }> = ({ text, t, at, size, seed, gap = 5 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.06 }}>
    {Array.from(text).map((ch, i) => {
      const lt = t - at - i * gap;
      if (lt < 0) return <span key={i} style={{ width: size * 0.7 }} />;
      const f = RANSOM_FONTS[Math.floor(random(`${seed}f${i}`) * RANSOM_FONTS.length)];
      const [bg, fg] = PAPERS[Math.floor(random(`${seed}p${i}`) * PAPERS.length)];
      const rot = (random(`${seed}r${i}`) - 0.5) * 16;
      const dy = (random(`${seed}y${i}`) - 0.5) * size * 0.18;
      const sc = 0.85 + random(`${seed}s${i}`) * 0.35;
      const slap = lt < 4 ? 1.35 - lt * 0.09 : 1;
      const j = jitter(t, `${seed}${i}`, 1.2, 0.5);
      const c = (k: number) => `${(random(`${seed}c${i}${k}`) * 12).toFixed(0)}%`;
      return (
        <span
          key={i}
          style={{
            display: "inline-block",
            fontFamily: f.f,
            fontWeight: f.w,
            fontSize: size * sc,
            lineHeight: 1,
            color: fg,
            background: bg,
            padding: `${size * 0.08}px ${size * 0.12}px`,
            transform: `translate(${j.x}px, ${dy + j.y}px) rotate(${rot + j.r}deg) scale(${slap})`,
            clipPath: `polygon(${c(0)} ${c(1)}, calc(100% - ${c(2)}) ${c(3)}, 100% calc(100% - ${c(4)}), ${c(5)} 100%)`,
            filter: "drop-shadow(2px 4px 3px rgba(40,25,10,0.35))",
          }}
        >
          {ch}
        </span>
      );
    })}
  </div>
);

/** Semi-transparent masking tape with torn ends. */
export const Tape: React.FC<{ x: number; y: number; w?: number; rot?: number; seed: string; color?: string }> = ({ x, y, w = 150, rot = 0, seed, color = "rgba(245,236,200,0.78)" }) => (
  <div style={{ position: "absolute", left: x - w / 2, top: y - 20, width: w, height: 40, transform: `rotate(${rot}deg)`, background: color, clipPath: `path('${tornPath(w, 40, seed, 3, 6)}')`, boxShadow: "0 1px 2px rgba(0,0,0,0.1)" }} />
);

/** Kraft / cardboard background with fibres and a coffee ring. */
export const Kraft: React.FC<{ color?: string }> = ({ color = "#CDB38D" }) => (
  <>
    <div style={{ position: "absolute", inset: 0, background: color }} />
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: 0.55 }}>
      <filter id="kraft-n">
        <feTurbulence type="fractalNoise" baseFrequency="0.012 0.6" numOctaves={3} seed={3} />
        <feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.42  0 0 0 0 0.28  0 0 0 0.9 -0.2" />
      </filter>
      <rect width="100%" height="100%" filter="url(#kraft-n)" />
    </svg>
  </>
);
