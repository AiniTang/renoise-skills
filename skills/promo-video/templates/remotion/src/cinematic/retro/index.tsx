import React from "react";
import { random, staticFile } from "remotion";

/*
 * Retro synthwave kit (复古 Synthwave): sky + striped sun (optional brand mark cut into it), perspective neon grid that
 * scrolls toward camera, wireframe mountains, palm silhouettes, roadside signs flying past, chrome + neon type and a
 * VHS overlay (scanlines, tracking band, colour fringing, OSD). Everything is 2D (SVG/CSS) and a pure function of `t`.
 */

export const SYN = { night: "#12051F", violet: "#2A0B45", magenta: "#FF2BD6", pink: "#FF5FA8", orange: "#FF8A3D", yellow: "#FFE14D", cyan: "#29F0FF", grid: "#FF3DDB" };
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

export const HORIZON = 600;
const F = 900; // focal length (px)
const CAM_H = 1.6; // camera height (world units)

/** Project a ground point (x across, z forward) to the screen. */
export const project = (x: number, z: number, y = 0) => ({ sx: 960 + (x * F) / z, sy: HORIZON + ((CAM_H - y) * F) / z, k: F / z });

export const SynthSky: React.FC<{ t: number }> = ({ t }) => (
  <div style={{ position: "absolute", inset: 0 }}>
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: HORIZON, background: `linear-gradient(180deg, ${SYN.night} 0%, ${SYN.violet} 42%, #6A1470 72%, #C22E7A 92%, ${SYN.orange} 100%)` }} />
    <svg width={1920} height={HORIZON} style={{ position: "absolute", inset: 0 }}>
      {Array.from({ length: 90 }, (_, i) => {
        const x = random(`st${i}`) * 1920;
        const y = random(`sy${i}`) * HORIZON * 0.62;
        const tw = 0.4 + 0.6 * Math.abs(Math.sin(t * 0.08 + i));
        return <circle key={i} cx={x} cy={y} r={random(`sr${i}`) * 1.6 + 0.4} fill="#FFFFFF" opacity={tw * 0.8} />;
      })}
    </svg>
  </div>
);

/** Sun with horizontal slits that widen toward the bottom; `mark` cuts the brand mark out of its centre. */
export const StripedSun: React.FC<{ t: number; r?: number; mark?: string; rise?: number }> = ({ t, r = 250, mark, rise = 1 }) => {
  const cy = HORIZON - r * 0.55 + (1 - rise) * r;
  const slits = Array.from({ length: 9 }, (_, i) => {
    const y = 0.48 + i * 0.058 + ((t * 0.002) % 0.058);
    return `transparent ${y * 100}%, transparent ${(y + 0.006 + i * 0.0042) * 100}%, #000 ${(y + 0.006 + i * 0.0042) * 100}%`;
  });
  const maskGrad = `linear-gradient(180deg, #000 0%, #000 48%, ${slits.join(", ")})`;
  return (
    <div style={{ position: "absolute", left: 960 - r, top: cy - r, width: r * 2, height: r * 2, filter: `drop-shadow(0 0 40px ${SYN.pink})` }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: `linear-gradient(180deg, ${SYN.yellow} 0%, ${SYN.orange} 48%, ${SYN.magenta} 100%)`,
          WebkitMaskImage: mark ? `${maskGrad}, url(${staticFile(mark)})` : maskGrad,
          WebkitMaskSize: mark ? `100% 100%, 38% 38%` : "100% 100%",
          WebkitMaskPosition: mark ? "0 0, 50% 34%" : "0 0",
          WebkitMaskRepeat: "no-repeat",
          WebkitMaskComposite: mark ? "source-out" : undefined,
        }}
      />
    </div>
  );
};

/** Perspective neon grid scrolling toward camera. `speed` in world units / frame. */
export const NeonGrid: React.FC<{ t: number; speed?: number; lanes?: number; color?: string }> = ({ t, speed = 0.12, lanes = 14, color = SYN.grid }) => {
  const off = (t * speed) % 1;
  const rows = Array.from({ length: 40 }, (_, i) => i + 1 - off).filter((z) => z > 0.35);
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0, filter: `drop-shadow(0 0 6px ${color})` }}>
      <defs>
        <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1A0630" />
          <stop offset="1" stopColor="#07010F" />
        </linearGradient>
      </defs>
      <rect x={0} y={HORIZON} width={1920} height={1080 - HORIZON} fill="url(#floor)" />
      {rows.map((z, i) => {
        const y = project(0, z).sy;
        return <line key={`h${i}`} x1={0} x2={1920} y1={y} y2={y} stroke={color} strokeWidth={Math.min(3, 1 + 6 / z)} opacity={Math.min(1, 0.25 + 2 / z)} />;
      })}
      {Array.from({ length: lanes * 2 + 1 }, (_, i) => {
        const x = (i - lanes) * 1.2;
        const near = project(x, 0.35);
        return <line key={`v${i}`} x1={960} y1={HORIZON} x2={near.sx} y2={near.sy} stroke={color} strokeWidth={1.6} opacity={0.8} />;
      })}
      <line x1={0} x2={1920} y1={HORIZON} y2={HORIZON} stroke={SYN.cyan} strokeWidth={2} opacity={0.9} />
    </svg>
  );
};

/** Wireframe mountain range sitting on the horizon. */
export const WireMountains: React.FC<{ seed?: string; color?: string; height?: number }> = ({ seed = "mt", color = SYN.cyan, height = 170 }) => {
  const n = 26;
  const pts = Array.from({ length: n + 1 }, (_, i) => {
    const x = (i / n) * 1920;
    const mid = Math.abs(i / n - 0.5) * 2; // lower in the middle (behind the sun)
    const h = height * (0.25 + 0.75 * random(`${seed}${i}`)) * (0.45 + 0.55 * mid);
    return [x, HORIZON - h] as [number, number];
  });
  const outline = `M 0 ${HORIZON} ` + pts.map(([x, y]) => `L ${x} ${y}`).join(" ") + ` L 1920 ${HORIZON} Z`;
  return (
    <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
      <path d={outline} fill="#1A0630" stroke={color} strokeWidth={2} style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
      {pts.map(([x, y], i) => (i % 2 === 0 ? <line key={i} x1={x} y1={y} x2={(pts[Math.min(n, i + 1)][0] + x) / 2} y2={HORIZON} stroke={color} strokeOpacity={0.35} /> : null))}
    </svg>
  );
};

/** Palm silhouette (anchor = trunk base). */
export const Palm: React.FC<{ x: number; y: number; s?: number; flip?: boolean; sway?: number }> = ({ x, y, s = 1, flip, sway = 0 }) => (
  <svg width={400 * s} height={600 * s} viewBox="0 0 400 600" style={{ position: "absolute", left: x - 200 * s, top: y - 600 * s, transform: flip ? "scaleX(-1)" : undefined, overflow: "visible" }}>
    <path d="M 196 600 C 204 480 214 330 236 210 L 250 212 C 230 330 222 480 216 600 Z" fill="#07010F" />
    <g transform={`translate(243 208) rotate(${sway})`}>
      {[-150, -120, -80, -40, -10, 25, 60].map((a, i) => (
        <path key={i} d="M 0 0 C 50 -30 120 -20 170 30 C 120 0 60 -4 0 12 Z" fill="#07010F" transform={`rotate(${a})`} />
      ))}
    </g>
  </svg>
);

/** Roadside sign that rushes from the horizon past the camera. `at` = frame it appears, `side` = -1 left / 1 right. */
export const RoadSign: React.FC<{ t: number; at: number; side: -1 | 1; title: string; sub: string; family: string; mono: string; color?: string; dur?: number }> = ({
  t,
  at,
  side,
  title,
  sub,
  family,
  mono,
  color = SYN.cyan,
  dur = 48,
}) => {
  const u = (t - at) / dur;
  if (u < 0 || u > 1) return null;
  const z = 40 * Math.pow(1 - u, 2.2) + 0.9;
  const base = project(side * 3.2, z);
  const k = base.k / 100;
  const w = 320 * k;
  const h = 150 * k;
  return (
    <div style={{ position: "absolute", left: base.sx - w / 2, top: base.sy - h - 220 * k, width: w, height: h, opacity: clamp01(u * 6) }}>
      <div style={{ position: "absolute", left: w / 2 - 4 * k, top: h, width: 8 * k, height: 220 * k, background: "#2A1640" }} />
      <div style={{ position: "absolute", inset: 0, borderRadius: 10 * k, border: `${4 * k}px solid ${color}`, background: "rgba(8,2,20,0.85)", boxShadow: `0 0 ${24 * k}px ${color}`, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div style={{ fontFamily: family, fontWeight: 800, fontSize: 52 * k, color: "#FFFFFF", textShadow: `0 0 ${12 * k}px ${color}` }}>{title}</div>
          <div style={{ fontFamily: mono, fontSize: 20 * k, letterSpacing: "0.2em", color }}>{sub}</div>
        </div>
      </div>
    </div>
  );
};

/** Chrome letters with a horizon line reflection and a neon rim. */
export const ChromeText: React.FC<{ text: string; family: string; size: number; x?: number; y: number; t: number; at: number; italic?: boolean }> = ({ text, family, size, x = 960, y, t, at, italic = true }) => {
  const lt = t - at;
  if (lt < 0) return null;
  const k = clamp01(lt / 10);
  const e = 1 - Math.pow(1 - k, 3);
  const s = 2.4 - 1.4 * e + (k >= 1 ? 0.02 * Math.exp(-(lt - 10) / 5) : 0);
  const base: React.CSSProperties = { fontFamily: family, fontWeight: 800, fontSize: size, lineHeight: 1, fontStyle: italic ? "italic" : undefined, letterSpacing: "0.02em", whiteSpace: "nowrap", fontSynthesis: "none" };
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) scale(${s}) skewX(${italic ? -8 : 0}deg)`, opacity: e }}>
      <div style={{ ...base, position: "absolute", left: 0, top: 0, color: "transparent", WebkitTextStroke: `10px ${SYN.magenta}`, filter: `blur(8px)`, opacity: 0.9 }}>{text}</div>
      <div style={{ ...base, position: "absolute", left: 0, top: 0, color: "transparent", WebkitTextStroke: `6px #2B0B3F` }}>{text}</div>
      <div
        style={{
          ...base,
          position: "relative",
          backgroundImage: "linear-gradient(180deg, #FFFFFF 0%, #C9E8FF 38%, #2B1B6A 50%, #FFB6F0 51%, #FFFFFF 78%, #7C4BD6 100%)",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          color: "transparent",
          textShadow: "none",
        }}
      >
        {text}
      </div>
    </div>
  );
};

/** VHS: scanlines, a rolling tracking band, colour fringing on everything under `children`, and an OSD. */
export const VhsOverlay: React.FC<{ t: number; mono: string; osd?: string }> = ({ t, mono, osd = "PLAY ▶" }) => {
  const bandY = ((t * 9) % 1400) - 200;
  const sec = Math.floor(t / 30);
  return (
    <>
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none", background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.28) 0 1px, transparent 1px 3px)", mixBlendMode: "multiply" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: bandY, height: 70, pointerEvents: "none", background: "linear-gradient(180deg, transparent, rgba(255,255,255,0.08), transparent)", mixBlendMode: "screen" }} />
      <div style={{ position: "absolute", left: 70, top: 56, fontFamily: mono, fontSize: 34, color: "#FFFFFF", textShadow: "2px 0 #FF2B6A, -2px 0 #29F0FF", opacity: Math.floor(t / 15) % 2 === 0 || t > 60 ? 1 : 0.4 }}>{osd}</div>
      <div style={{ position: "absolute", right: 70, bottom: 56, fontFamily: mono, fontSize: 28, color: "#FFFFFF", textShadow: "2px 0 #FF2B6A, -2px 0 #29F0FF" }}>
        SP 0:{String(Math.floor(sec / 60)).padStart(2, "0")}:{String(sec % 60).padStart(2, "0")}
      </div>
    </>
  );
};
