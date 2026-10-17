import React, { useMemo } from "react";
import { getLength, getPointAtLength } from "@remotion/paths";
import { clamp01 } from "./theme";

/** Where the pen tip is when `p` (0..1) of the total length of `paths` has been drawn in order. */
export const penAt = (paths: string[], p: number) => {
  const lens = paths.map((d) => getLength(d));
  const total = lens.reduce((a, b) => a + b, 0);
  let left = clamp01(p) * total;
  for (let i = 0; i < paths.length; i++) {
    if (left <= lens[i] || i === paths.length - 1) return getPointAtLength(paths[i], Math.min(lens[i], left));
    left -= lens[i];
  }
  return { x: 0, y: 0 };
};

/**
 * Draws SVG paths in sequence like a pen (signature, monoline script, logo strokes) with a glowing nib.
 * `erase` (0..1) removes the stroke from its start, so the line can be pulled back into the nib.
 * Coordinates are in `viewBox` units; `transform` places the drawing on the 1920×1080 frame.
 */
export const StrokeDraw: React.FC<{
  paths: string[];
  p: number;
  erase?: number;
  color: string;
  width: number; // in viewBox units
  viewBox?: string;
  transform?: string;
  nib?: number; // 0..1 nib glow strength
  nibColor?: string;
  nibR?: number; // nib radius in viewBox units
  glow?: number; // px of soft glow around the stroke
  lineCap?: "round" | "butt";
}> = ({ paths, p, erase = 0, color, width, viewBox = "0 0 1920 1080", transform, nib = 1, nibColor = "#fff", nibR = 6, glow = 0, lineCap = "round" }) => {
  const lens = useMemo(() => paths.map((d) => getLength(d)), [paths]);
  const total = lens.reduce((a, b) => a + b, 0);
  const drawn = clamp01(p) * total;
  const gone = clamp01(erase) * total;
  let acc = 0;
  const head = penAt(paths, erase > 0 && p >= 1 ? erase : p);
  return (
    <svg viewBox={viewBox} width={1920} height={1080} style={{ position: "absolute", inset: 0, overflow: "visible", filter: glow ? `drop-shadow(0 0 ${glow}px ${color})` : undefined }}>
      <g transform={transform}>
        {paths.map((d, i) => {
          const L = lens[i];
          const a = Math.min(L, Math.max(0, gone - acc));
          const b = Math.min(L, Math.max(0, drawn - acc));
          acc += L;
          if (b - a <= 0.01) return null;
          return <path key={i} d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap={lineCap} strokeLinejoin="round" strokeDasharray={`0 ${a} ${b - a} ${L + 1}`} />;
        })}
        {nib > 0 && (p < 1 || (erase > 0 && erase < 1)) && (
          <g opacity={nib}>
            <circle cx={head.x} cy={head.y} r={nibR * 4} fill={nibColor} opacity={0.12} />
            <circle cx={head.x} cy={head.y} r={nibR * 2} fill={nibColor} opacity={0.25} />
            <circle cx={head.x} cy={head.y} r={nibR} fill={nibColor} />
          </g>
        )}
      </g>
    </svg>
  );
};

/** The YouWare mark as four identical loop strokes (centre-lines traced from the official SVG, 1200-unit box). */
const MARK_STROKE =
  "M 267 155 L 406 299 C 450 344 480 350 505 350 C 540 350 575 330 600 300 C 640 250 665 190 665 130 C 665 76 638 44 602 44 C 566 44 539 76 539 130 C 539 190 562 250 600 300 C 625 330 660 350 695 350 C 720 350 750 344 794 299 L 933 155";
const rotD = (d: string, k: number) => {
  const a = (k * Math.PI) / 2;
  const c = Math.cos(a);
  const s = Math.sin(a);
  const nums = d.match(/-?\d+\.?\d*/g)!.map(Number);
  let i = 0;
  return d.replace(/-?\d+\.?\d*\s+-?\d+\.?\d*/g, () => {
    const x = nums[i++] - 600;
    const y = nums[i++] - 600;
    return `${(600 + x * c - y * s).toFixed(2)} ${(600 + x * s + y * c).toFixed(2)}`;
  });
};
export const MARK_PATHS = [0, 1, 2, 3].map((k) => rotD(MARK_STROKE, k));
/** Stroke width of the official mark in the same 1200-unit box. */
export const MARK_WIDTH = 96;

/** Monoline cursive "vibe" (one continuous stroke) + where its i-dot sits, in a 640×460 box. */
export const VIBE_PATH =
  "M 40 262 C 62 232 100 226 110 256 C 118 290 132 348 148 378 C 164 342 186 288 204 246 C 210 230 196 222 190 234 C 186 246 208 250 230 242 C 246 236 258 232 266 232 C 262 278 256 336 260 364 C 264 390 290 382 306 356 C 334 306 364 204 372 124 C 378 72 346 50 336 96 C 326 156 326 290 332 378 C 342 326 380 244 420 250 C 456 256 448 334 404 362 C 386 374 360 372 352 360 C 390 370 432 352 462 330 C 492 312 526 290 528 262 C 530 238 502 232 488 252 C 466 282 470 344 492 370 C 514 394 556 380 590 348";
export const VIBE_DOT = { x: 262, y: 186 };
