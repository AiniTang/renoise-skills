import React, { useEffect, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, Img, staticFile } from "remotion";

/*
 * Mesh-gradient + glassmorphism kit (弥散渐变·玻璃拟态).
 * - `Aurora`: drifting radial blooms on a dark base, blended with `screen`, plus film grain so the gradient never bands
 *   in H.264. Pure function of `t`.
 * - `Glass`: a frosted panel — real `backdrop-filter` blur + saturation over whatever is behind it, a bright top rim,
 *   a faint frost grain and an optional diagonal sheen (`sheen` 0→1 sweeps it across).
 * - `GlassMark`: the same frosting clipped to an SVG silhouette (mask-image), for a glass logo.
 * - `Thumb`: crop a region of a screenshot into a fixed box (cover).
 * Pitfalls: keep glass out of preserve-3d / 3D transforms (backdrop-filter is flaky there); Three.js behind glass is
 * fine only in a pre-rendered video; blur ≥ 24px or the aurora shows through as blobs instead of frost.
 */

export type Bloom = { color: string; x: number; y: number; r: number; ax?: number; ay?: number; speed?: number; phase?: number };

export const Aurora: React.FC<{ t: number; blooms: Bloom[]; base?: string; grain?: number; w?: number; h?: number }> = ({ t, blooms, base = "#150F2E", grain = 0.07, w = 1920, h = 1080 }) => (
  <AbsoluteFill style={{ background: base, overflow: "hidden" }}>
    {blooms.map((b, i) => {
      const sp = b.speed ?? 0.012;
      const ph = b.phase ?? i * 1.7;
      const x = b.x + Math.sin(t * sp + ph) * (b.ax ?? 160);
      const y = b.y + Math.cos(t * sp * 0.8 + ph * 1.3) * (b.ay ?? 110);
      const r = b.r * (1 + Math.sin(t * sp * 1.3 + ph) * 0.08);
      return (
        <div
          key={i}
          style={{
            position: "absolute",
            left: x - r,
            top: y - r,
            width: r * 2,
            height: r * 2,
            borderRadius: "50%",
            background: `radial-gradient(circle at 50% 50%, ${b.color} 0%, ${b.color}B3 24%, ${b.color}00 70%)`,
            mixBlendMode: "screen",
          }}
        />
      );
    })}
    <Grain t={t} opacity={grain} w={w} h={h} />
  </AbsoluteFill>
);

/** Animated film grain (changes every 2 frames). */
export const Grain: React.FC<{ t: number; opacity?: number; w?: number; h?: number; id?: string }> = ({ t, opacity = 0.07, w = 1920, h = 1080, id = "grain" }) => {
  const seed = Math.floor(t / 2) % 50;
  return (
    <svg width={w} height={h} style={{ position: "absolute", inset: 0, opacity, mixBlendMode: "overlay", pointerEvents: "none" }}>
      <filter id={`${id}-${seed}`}>
        <feTurbulence type="fractalNoise" baseFrequency={0.9} numOctaves={2} seed={seed} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width={w} height={h} filter={`url(#${id}-${seed})`} />
    </svg>
  );
};

export const Glass: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  radius?: number;
  blur?: number;
  tint?: string;
  sheen?: number;
  opacity?: number;
  transform?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ x, y, w, h, radius = 36, blur = 32, tint = "rgba(255,255,255,0.12)", sheen, opacity = 1, transform, style, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      height: h,
      borderRadius: radius,
      overflow: "hidden",
      opacity,
      transform,
      backdropFilter: `blur(${blur}px) saturate(175%) brightness(1.06)`,
      WebkitBackdropFilter: `blur(${blur}px) saturate(175%) brightness(1.06)`,
      background: `linear-gradient(145deg, rgba(255,255,255,0.24) 0%, ${tint} 45%, rgba(255,255,255,0.05) 100%)`,
      boxShadow: "inset 0 1.5px 0 rgba(255,255,255,0.6), inset 0 0 0 1.5px rgba(255,255,255,0.22), inset 0 -18px 40px rgba(255,255,255,0.05), 0 40px 80px rgba(8,4,30,0.35)",
      ...style,
    }}
  >
    {sheen !== undefined && sheen > 0 && sheen < 1 && (
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(115deg, transparent 38%, rgba(255,255,255,0.28) 48%, rgba(255,255,255,0.06) 54%, transparent 62%)",
          backgroundSize: "300% 100%",
          backgroundPosition: `${100 - sheen * 100}% 0`,
          mixBlendMode: "screen",
        }}
      />
    )}
    {children}
  </div>
);

/** Frosted glass in the shape of an SVG silhouette (e.g. the brand mark). */
export const GlassMark: React.FC<{ src: string; x: number; y: number; size: number; blur?: number; opacity?: number; transform?: string }> = ({ src, x, y, size, blur = 22, opacity = 1, transform }) => {
  const url = staticFile(src);
  useMaskReady(url);
  const mask = `url(${url}) center / contain no-repeat`;
  return (
    <div style={{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size, opacity, transform }}>
      {/* soft drop shadow */}
      <div style={{ position: "absolute", inset: 0, WebkitMask: mask, mask, background: "rgba(8,4,30,0.35)", transform: "translate(0, 24px)", filter: "blur(18px)" }} />
      <div
        style={{
          position: "absolute",
          inset: 0,
          WebkitMask: mask,
          mask,
          backdropFilter: `blur(${blur}px) saturate(180%) brightness(1.15)`,
          WebkitBackdropFilter: `blur(${blur}px) saturate(180%) brightness(1.15)`,
          background: "linear-gradient(150deg, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0.18) 40%, rgba(255,255,255,0.08) 100%)",
        }}
      />
    </div>
  );
};

/** CSS masks load lazily; hold the render until the image is decoded so the first frames aren't blank. */
const useMaskReady = (url: string) => {
  const [handle] = useState(() => delayRender(`mask ${url}`));
  useEffect(() => {
    const im = new Image();
    im.onload = () => im.decode().then(() => continueRender(handle), () => continueRender(handle));
    im.onerror = () => continueRender(handle);
    im.src = url;
  }, [url, handle]);
};

/** A crop [x0,y0,x1,y1] (fractions) of an image of natural size `nat`, covering a w×h box. */
export const Thumb: React.FC<{ src: string; nat: [number, number]; crop: [number, number, number, number]; w: number; h: number; radius?: number; style?: React.CSSProperties }> = ({ src, nat, crop, w, h, radius = 14, style }) => {
  const [x0, y0, x1, y1] = crop;
  const cw = (x1 - x0) * nat[0];
  const ch = (y1 - y0) * nat[1];
  const s = Math.max(w / cw, h / ch);
  const offX = (w - cw * s) / 2 - x0 * nat[0] * s;
  const offY = (h - ch * s) / 2 - y0 * nat[1] * s;
  return (
    <div style={{ width: w, height: h, borderRadius: radius, overflow: "hidden", position: "relative", ...style }}>
      <Img src={staticFile(src)} style={{ position: "absolute", left: offX, top: offY, width: nat[0] * s, height: nat[1] * s, maxWidth: "none" }} />
    </div>
  );
};
