import React from "react";
import { random } from "remotion";
import { step, type SpringCfg } from "../spring";

/*
 * Variety-show captions (综艺花字 / テロップ): layered-outline type that pops in per character on a bouncy spring,
 * reaction marks (burst, speed lines, sweat, sparkles, ?!, confetti), a TV lower-third bar and a zoom punch.
 * Every value is a pure function of the local frame `t` (30 fps unless `fps` is passed).
 */

const hz = (f: number) => 2 * Math.PI * f;
/** Bouncy pop (≈35 % overshoot) for 花字. */
export const POP: SpringCfg = { w: hz(3.6), z: 0.36 };
/** Harder landing for slams. */
export const SLAM: SpringCfg = { w: hz(5.2), z: 0.5 };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const sec = (t: number, fps = 30) => t / fps;

export type Layer = { color: string; width: number };
export type Fill = string | string[]; // solid or vertical gradient stops

export type HuaZiPreset = { fill: Fill; layers: Layer[]; shadow?: { dx: number; dy: number; color: string } };

/** Colour recipes that read as variety captions. Layers go outer → inner (outer is widest). */
export const HUAZI: Record<string, HuaZiPreset> = {
  shock: { fill: ["#FFF36A", "#FFB01F"], layers: [{ color: "#1A1208", width: 16 }, { color: "#E8332B", width: 10 }, { color: "#FFFFFF", width: 4 }], shadow: { dx: 0, dy: 8, color: "#1A1208" } },
  cute: { fill: ["#FFFFFF", "#FFE3F1"], layers: [{ color: "#3A1030", width: 14 }, { color: "#FF5FA8", width: 8 }], shadow: { dx: 0, dy: 6, color: "#3A1030" } },
  cool: { fill: ["#FFFFFF", "#C9F1FF"], layers: [{ color: "#0B1D3A", width: 14 }, { color: "#2A7DFF", width: 8 }], shadow: { dx: 0, dy: 6, color: "#0B1D3A" } },
  fresh: { fill: ["#F7FFE0", "#CFE3A0"], layers: [{ color: "#1E2A12", width: 14 }, { color: "#7D8F57", width: 8 }], shadow: { dx: 0, dy: 6, color: "#1E2A12" } },
  note: { fill: "#1A1208", layers: [{ color: "#FFFFFF", width: 10 }], shadow: { dx: 0, dy: 4, color: "rgba(0,0,0,0.25)" } },
};

export type PopKind = "spring" | "slam" | "drop" | "wave";

/**
 * Layered-outline caption. Each character is stacked: widest outline at the back, fill on top, so variable-font
 * overlaps and stroke insides are always covered by the layer above.
 */
export const HuaZi: React.FC<{
  text: string;
  t: number;
  at?: number;
  x: number;
  y: number;
  size: number;
  family: string;
  weight?: number;
  preset?: HuaZiPreset;
  rotate?: number;
  pop?: PopKind;
  stagger?: number; // frames between characters
  tracking?: number; // em
  out?: number; // frame the caption leaves (scale down + fade)
  wobble?: number; // deg of idle wobble
  fps?: number;
  stretch?: number; // font-stretch % for variable-width faces
}> = ({ text, t, at = 0, x, y, size, family, weight = 800, preset = HUAZI.shock, rotate = 0, pop = "spring", stagger = 1.6, tracking = -0.01, out, wobble = 1.5, fps = 30, stretch }) => {
  const lines = text.split("\n").map((l) => Array.from(l));
  const lt = t - at;
  if (lt < 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 6) : 0;
  if (leave >= 1) return null;
  const fills = Array.isArray(preset.fill) ? preset.fill : [preset.fill, preset.fill];
  const grad = `linear-gradient(180deg, ${fills.map((c, i) => `${c} ${Math.round((i / Math.max(1, fills.length - 1)) * 100)}%`).join(", ")})`;
  const base: React.CSSProperties = {
    fontFamily: family,
    fontWeight: weight,
    fontSize: size,
    lineHeight: 1,
    letterSpacing: `${tracking}em`,
    whiteSpace: "pre",
    fontStretch: stretch ? `${stretch}%` : undefined,
    fontSynthesis: "none",
  };
  const outer = preset.layers[0]?.width ?? 0;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) rotate(${rotate + wobble * Math.sin(sec(lt, fps) * 5.2)}deg) scale(${1 - 0.35 * leave})`,
        opacity: 1 - leave,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: outer,
      }}
    >
      {lines.map((chars, li) => (
        <div key={li} style={{ display: "flex" }}>
      {chars.map((ch, ci) => {
        const i = lines.slice(0, li).reduce((n, l) => n + l.length, 0) + ci;
        const ct = sec(lt - i * stagger, fps);
        if (ct <= 0) return <span key={i} style={{ ...base, visibility: "hidden" }}>{ch}</span>;
        let s = 1;
        let dy = 0;
        let r = 0;
        if (pop === "spring") s = step(ct, POP);
        else if (pop === "slam") s = 1 + 0.9 * (1 - step(ct, SLAM));
        else if (pop === "drop") {
          const k = step(ct, POP);
          dy = (1 - k) * -size * 0.9;
          s = 0.6 + 0.4 * k;
        } else {
          s = step(ct, POP);
          dy = Math.sin(sec(lt, fps) * 9 - i * 0.7) * size * 0.05;
        }
        r = (1 - clamp01(ct * 4)) * (i % 2 ? 10 : -10);
        const o = pop === "slam" ? clamp01(ct * 10) : 1;
        return (
          <span key={i} style={{ position: "relative", display: "inline-block", transform: `translateY(${dy}px) scale(${Math.max(0, s)}) rotate(${r}deg)`, opacity: o, transformOrigin: "50% 80%" }}>
            <span style={{ ...base, visibility: "hidden" }}>{ch}</span>
            {preset.shadow && (
              <span aria-hidden style={{ ...base, position: "absolute", left: preset.shadow.dx, top: preset.shadow.dy, color: preset.shadow.color, WebkitTextStroke: `${outer * 2}px ${preset.shadow.color}` }}>
                {ch}
              </span>
            )}
            {preset.layers.map((l, k) => (
              <span key={k} aria-hidden style={{ ...base, position: "absolute", left: 0, top: 0, color: l.color, WebkitTextStroke: `${l.width * 2}px ${l.color}` }}>
                {ch}
              </span>
            ))}
            <span aria-hidden style={{ ...base, position: "absolute", left: 0, top: 0, backgroundImage: grad, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>
              {ch}
            </span>
          </span>
        );
      })}
        </div>
      ))}
    </div>
  );
};

/** Spiky starburst sticker behind a reaction word; spins a little and pulses. */
export const Burst: React.FC<{ t: number; at?: number; x: number; y: number; r: number; spikes?: number; fill?: string; stroke?: string; rotate?: number; out?: number; children?: React.ReactNode }> = ({
  t,
  at = 0,
  x,
  y,
  r,
  spikes = 14,
  fill = "#E8332B",
  stroke = "#1A1208",
  rotate = -8,
  out,
  children,
}) => {
  const lt = sec(t - at);
  if (lt < 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 6) : 0;
  if (leave >= 1) return null;
  const s = step(lt, POP) * (1 + 0.03 * Math.sin(lt * 18)) * (1 - 0.4 * leave);
  const pts = Array.from({ length: spikes * 2 }, (_, i) => {
    const a = (i / (spikes * 2)) * Math.PI * 2;
    const rr = i % 2 ? r * (0.62 + 0.06 * random(`b${i}`)) : r * (0.96 + 0.08 * random(`c${i}`));
    return `${(Math.cos(a) * rr).toFixed(1)},${(Math.sin(a) * rr).toFixed(1)}`;
  }).join(" ");
  return (
    <div style={{ position: "absolute", left: x, top: y, width: 0, height: 0, opacity: 1 - leave }}>
      <svg width={r * 2.4} height={r * 2.4} viewBox={`${-r * 1.2} ${-r * 1.2} ${r * 2.4} ${r * 2.4}`} style={{ position: "absolute", left: -r * 1.2, top: -r * 1.2, transform: `rotate(${rotate + lt * 12}deg) scale(${s})`, overflow: "visible" }}>
        <polygon points={pts} fill={stroke} transform="translate(0 10)" />
        <polygon points={pts} fill={fill} stroke={stroke} strokeWidth={8} strokeLinejoin="round" />
      </svg>
      <div style={{ position: "absolute", left: 0, top: 0, transform: `scale(${s})` }}>{children}</div>
    </div>
  );
};

/** Manga speed lines rushing to a focus point; they re-seed every other frame so they flicker like hand-drawn. */
export const SpeedLines: React.FC<{ t: number; at?: number; dur?: number; cx?: number; cy?: number; color?: string; count?: number; inner?: number; w?: number; h?: number }> = ({
  t,
  at = 0,
  dur = 60,
  cx = 960,
  cy = 540,
  color = "rgba(20,14,8,0.85)",
  count = 64,
  inner = 360,
  w = 1920,
  h = 1080,
}) => {
  const lt = t - at;
  if (lt < 0 || lt > dur) return null;
  const a = clamp01(lt / 4) * clamp01((dur - lt) / 6);
  const seed = Math.floor(t / 2);
  const R = Math.hypot(w, h);
  return (
    <svg width={w} height={h} style={{ position: "absolute", inset: 0, opacity: a }}>
      {Array.from({ length: count }, (_, i) => {
        const ang = (i / count) * Math.PI * 2 + (random(`sl${seed}-${i}`) - 0.5) * 0.08;
        const r0 = inner * (0.9 + 0.5 * random(`sr${seed}-${i}`));
        const width = 2 + 9 * random(`sw${seed}-${i}`);
        const x0 = cx + Math.cos(ang) * r0;
        const y0 = cy + Math.sin(ang) * r0;
        const x1 = cx + Math.cos(ang) * R;
        const y1 = cy + Math.sin(ang) * R;
        const nx = -Math.sin(ang) * width;
        const ny = Math.cos(ang) * width;
        return <polygon key={i} points={`${x0},${y0} ${x1 + nx},${y1 + ny} ${x1 - nx},${y1 - ny}`} fill={color} />;
      })}
    </svg>
  );
};

/** Little reaction marks: sweat drop, sparkle, "!!", "?", heart. Bounce in and idle. */
export type MarkKind = "sweat" | "sparkle" | "bang" | "question" | "heart";
export const Mark: React.FC<{ kind: MarkKind; t: number; at?: number; x: number; y: number; size?: number; color?: string; stroke?: string; rotate?: number; out?: number }> = ({
  kind,
  t,
  at = 0,
  x,
  y,
  size = 80,
  color,
  stroke = "#1A1208",
  rotate = 0,
  out,
}) => {
  const lt = sec(t - at);
  if (lt < 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 5) : 0;
  if (leave >= 1) return null;
  const s = step(lt, POP) * (1 - 0.4 * leave);
  const bob = Math.sin(lt * 6 + x) * size * 0.05;
  const sw = size * 0.08;
  let shape: React.ReactNode;
  if (kind === "sweat") {
    const drop = kind === "sweat" ? Math.min(1, lt * 0.6) * size * 0.3 : 0;
    shape = <path d="M0,-50 C 18,-20 34,0 34,18 A 34 34 0 1 1 -34,18 C -34,0 -18,-20 0,-50 Z" transform={`translate(0 ${drop})`} fill={color ?? "#7FD3FF"} stroke={stroke} strokeWidth={sw * (100 / size)} />;
  } else if (kind === "sparkle") {
    const tw = 0.8 + 0.25 * Math.sin(lt * 14);
    shape = <path d="M0,-50 C 6,-10 10,-6 50,0 C 10,6 6,10 0,50 C -6,10 -10,6 -50,0 C -10,-6 -6,-10 0,-50 Z" transform={`scale(${tw})`} fill={color ?? "#FFE14D"} stroke={stroke} strokeWidth={sw * (100 / size)} />;
  } else if (kind === "heart") {
    shape = <path d="M0,40 C -60,0 -50,-50 -18,-44 C -6,-42 0,-30 0,-24 C 0,-30 6,-42 18,-44 C 50,-50 60,0 0,40 Z" fill={color ?? "#FF5FA8"} stroke={stroke} strokeWidth={sw * (100 / size)} />;
  } else {
    const ch = kind === "bang" ? "!!" : "?";
    shape = (
      <text x={0} y={30} textAnchor="middle" fontFamily='"Bricolage Grotesque", sans-serif' fontWeight={800} fontSize={96} fill={color ?? (kind === "bang" ? "#E8332B" : "#2A7DFF")} stroke={stroke} strokeWidth={10} paintOrder="stroke" style={{ fontSynthesis: "none" }}>
        {ch}
      </text>
    );
  }
  return (
    <svg width={size * 1.6} height={size * 1.6} viewBox="-80 -80 160 160" style={{ position: "absolute", left: x - size * 0.8, top: y - size * 0.8 + bob, transform: `rotate(${rotate}deg) scale(${s})`, overflow: "visible", opacity: 1 - leave }}>
      {shape}
    </svg>
  );
};

/** Paper confetti burst with gravity and flutter. */
export const Confetti: React.FC<{ t: number; at?: number; x: number; y: number; count?: number; colors?: string[]; power?: number; w?: number; h?: number }> = ({
  t,
  at = 0,
  x,
  y,
  count = 90,
  colors = ["#FFE14D", "#FF5FA8", "#2A7DFF", "#7DDB6A", "#FF8A3D", "#FFFFFF"],
  power = 900,
  w = 1920,
  h = 1080,
}) => {
  const lt = sec(t - at);
  if (lt < 0 || lt > 3) return null;
  return (
    <svg width={w} height={h} style={{ position: "absolute", inset: 0, overflow: "visible", opacity: clamp01((3 - lt) / 0.6) }}>
      {Array.from({ length: count }, (_, i) => {
        const a = -Math.PI / 2 + (random(`ca${i}`) - 0.5) * 2.4;
        const v = power * (0.4 + 0.6 * random(`cv${i}`));
        const px = x + Math.cos(a) * v * lt * (1 - 0.25 * lt);
        const py = y + Math.sin(a) * v * lt + 900 * lt * lt;
        const rot = lt * 720 * (random(`cr${i}`) - 0.5);
        const flutter = Math.abs(Math.cos(lt * 12 + i));
        const c = colors[i % colors.length];
        return <rect key={i} x={-9} y={-5} width={18} height={10 * flutter + 1} rx={2} fill={c} transform={`translate(${px} ${py}) rotate(${rot})`} />;
      })}
    </svg>
  );
};

/** TV lower-third caption bar (テロップ): a rounded bar slides in with an icon chip, text types on. */
export const Telop: React.FC<{ t: number; at?: number; out?: number; x: number; y: number; text: string; family: string; size?: number; bar?: string; ink?: string; chip?: string; chipText?: string }> = ({
  t,
  at = 0,
  out,
  x,
  y,
  text,
  family,
  size = 40,
  bar = "#FFFFFF",
  ink = "#1A1208",
  chip = "#E8332B",
  chipText,
}) => {
  const lt = sec(t - at);
  if (lt < 0) return null;
  const leave = out !== undefined ? clamp01((t - out) / 6) : 0;
  if (leave >= 1) return null;
  const k = step(lt, { w: hz(3), z: 0.7 });
  const shown = Math.floor(clamp01((lt - 0.12) * 3) * Array.from(text).length);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translateX(${(1 - k) * -80}px) scale(${1 - 0.1 * leave})`, opacity: Math.min(1, k * 1.5) * (1 - leave), display: "flex", alignItems: "center", gap: 14 }}>
      {chipText && (
        <div style={{ background: chip, color: "#fff", fontFamily: family, fontWeight: 800, fontSize: size * 0.62, padding: `${size * 0.18}px ${size * 0.4}px`, borderRadius: 999, border: `4px solid ${ink}`, boxShadow: `0 5px 0 ${ink}` }}>{chipText}</div>
      )}
      <div style={{ background: bar, color: ink, fontFamily: family, fontWeight: 800, fontSize: size, padding: `${size * 0.22}px ${size * 0.6}px`, borderRadius: size * 0.5, border: `5px solid ${ink}`, boxShadow: `0 6px 0 ${ink}`, whiteSpace: "pre" }}>
        {Array.from(text).slice(0, shown).join("")}
        <span style={{ opacity: 0 }}>{Array.from(text).slice(shown).join("")}</span>
      </div>
    </div>
  );
};

/** Punch-in on emphasis frames: returns a scale factor for the footage underneath. */
export const zoomPunch = (t: number, hits: number[], amount = 0.09, fps = 30) =>
  1 + hits.reduce((acc, h) => {
    const lt = (t - h) / fps;
    if (lt < 0) return acc;
    return acc + amount * (1 - step(lt, { w: hz(4), z: 0.55 })) * (lt < 0.03 ? lt / 0.03 : 1);
  }, 0);

/** Screen shake offset (px) after hits, decays fast. */
export const shake = (t: number, hits: number[], amp = 10) => {
  let dx = 0;
  let dy = 0;
  for (const h of hits) {
    const lt = t - h;
    if (lt < 0 || lt > 12) continue;
    const d = Math.exp(-lt / 3.5) * amp;
    dx += (random(`sx${h}-${Math.floor(t)}`) - 0.5) * 2 * d;
    dy += (random(`sy${h}-${Math.floor(t)}`) - 0.5) * 2 * d;
  }
  return { dx, dy };
};
