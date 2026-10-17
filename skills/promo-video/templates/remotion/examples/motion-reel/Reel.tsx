import React from "react";
import gsap from "gsap";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { AbsoluteFill, Audio, interpolate, random, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { E, clamp01, mix, seg } from "../cinematic/motion";
import { SoundCues, type Cue } from "../cinematic/sfx";
import { Cubes } from "./Cubes";
import { Particles2D } from "./Particles2D";

type Ease = (t: number) => number;
const ELASTIC = gsap.parseEase("elastic.out(1, 0.35)") as Ease;

const INK = "#0A0A0B";
const PAPER = "#F3F1EC";
const RED = "#FF3B2F";
const BLUE = "#2B59FF";
const LIME = "#D7FF3B";
const DISPLAY = '"SF Pro Display", -apple-system, "Helvetica Neue", sans-serif';
const MONO = '"SF Mono", Menlo, monospace';

const T = { intro: 0, type: 60, morph: 120, depth: 195, parts: 270, slats: 345, end: 405 };
export const REEL_FRAMES = 450;
const FLOOR = 700;

/* ── 00 · the dot ── */
const dotY = (t: number) => {
  const c = [12, 22, 28];
  const y0 = -80;
  if (t < c[0]) return y0 + (FLOOR - y0) * Math.pow(t / c[0], 2);
  if (t < c[1]) {
    const u = (t - c[0]) / (c[1] - c[0]);
    return FLOOR - 4 * 170 * u * (1 - u);
  }
  if (t < c[2]) {
    const u = (t - c[1]) / (c[2] - c[1]);
    return FLOOR - 4 * 55 * u * (1 - u);
  }
  return FLOOR;
};

const Intro: React.FC = () => {
  const f = useCurrentFrame();
  const squash = [12, 22, 28].reduce((a, c) => a + Math.exp(-Math.abs(f - c) / 1.4) * (c === 12 ? 1 : c === 22 ? 0.7 : 0.45), 0);
  const antic = seg(f, 29, 5, E.out) * (1 - seg(f, 34, 3, E.linear));
  const shoot = seg(f, 34, 11, E.out);
  const size = 64;
  const w = mix(size * (1 + 0.55 * squash + 0.3 * antic), 2200, shoot);
  const h = mix(size * (1 - 0.42 * squash - 0.35 * antic), 10, shoot);
  const settle = seg(f, 50, 10, E.inOut);
  const lineW = mix(w, 1180, settle);
  const letters = "MOTION".split("");
  return (
    <AbsoluteFill style={{ background: INK }}>
      <div style={{ position: "absolute", left: 960 - lineW / 2, top: dotY(f) - h, width: lineW, height: h, borderRadius: shoot > 0.2 ? 4 : 999, background: LIME, boxShadow: `0 0 40px rgba(215,255,59,0.35)` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: FLOOR - 300, height: 300, overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "flex-end" }}>
        {letters.map((ch, i) => {
          const e = seg(f, 42 + i * 2, 14, E.back);
          return (
            <span key={i} style={{ display: "inline-block", fontFamily: DISPLAY, fontWeight: 900, fontSize: 300, lineHeight: 0.8, letterSpacing: "-0.03em", color: PAPER, transform: `translateY(${(1 - e) * 110}%) skewY(${(1 - e) * 12}deg)` }}>
              {ch}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/* ── 01 · kinetic type ── */
const Wipe: React.FC<{ color: string; at?: number }> = ({ color, at = 0 }) => {
  const f = useCurrentFrame();
  const r = mix(0, 1250, seg(f, at, 9, E.out));
  return <div style={{ position: "absolute", left: 960 - r, top: 540 - r, width: r * 2, height: r * 2, borderRadius: "50%", background: color }} />;
};

const BIG: React.CSSProperties = { fontFamily: DISPLAY, fontWeight: 900, fontSize: 280, letterSpacing: "-0.035em", lineHeight: 1 };

const Timing: React.FC = () => {
  const f = useCurrentFrame();
  const word = "TIMING.";
  const n = Math.min(word.length, Math.floor(f / 2) + 1);
  return (
    <AbsoluteFill>
      <Wipe color={RED} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ ...BIG, color: INK }}>{word.slice(0, n)}<span style={{ opacity: 0 }}>{word.slice(n)}</span></div>
        <div style={{ marginTop: 20, display: "flex", gap: 22, fontFamily: MONO, fontSize: 22, color: INK }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, opacity: i <= f ? 1 : 0.25 }}>
              <div style={{ width: 3, height: i % 4 === 0 ? 34 : 18, background: INK }} />
              {i % 4 === 0 ? String(i).padStart(2, "0") : ""}
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Easing: React.FC = () => {
  const f = useCurrentFrame();
  const letters = "EASING.".split("");
  const p = clamp01(f / 14);
  const curve = Array.from({ length: 60 }, (_, i) => {
    const t = i / 59;
    return `${i ? "L" : "M"}${t * 520} ${120 - ELASTIC(t) * 100}`;
  }).join(" ");
  return (
    <AbsoluteFill>
      <Wipe color={BLUE} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex" }}>
          {letters.map((ch, i) => {
            const e = ELASTIC(clamp01((f - i * 1.2) / 12));
            return (
              <span key={i} style={{ ...BIG, color: PAPER, display: "inline-block", transform: `scaleX(${e}) scaleY(${mix(1.4, 1, e)})`, transformOrigin: "0% 100%" }}>
                {ch}
              </span>
            );
          })}
        </div>
        <svg width={560} height={150} style={{ marginTop: 10, overflow: "visible" }}>
          <path d={curve} fill="none" stroke="rgba(243,241,236,0.35)" strokeWidth={3} />
          <path d={curve} fill="none" stroke={PAPER} strokeWidth={4} strokeDasharray={1400} strokeDashoffset={1400 * (1 - p)} />
          <circle cx={p * 520} cy={120 - ELASTIC(p) * 100} r={10} fill={LIME} />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Rhythm: React.FC = () => {
  const f = useCurrentFrame();
  const letters = "RHYTHM.".split("");
  return (
    <AbsoluteFill>
      <Wipe color={PAPER} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex" }}>
          {letters.map((ch, i) => {
            const y = Math.max(0, Math.sin((f - i * 1.6) * 0.55)) * -60 * clamp01(f / 3);
            return (
              <span key={i} style={{ ...BIG, color: INK, display: "inline-block", transform: `translateY(${y}px)` }}>
                {ch}
              </span>
            );
          })}
        </div>
        <div style={{ marginTop: 26, display: "flex", alignItems: "flex-end", gap: 8, height: 90 }}>
          {Array.from({ length: 32 }).map((_, i) => {
            const v = 0.2 + 0.8 * Math.abs(Math.sin(i * 0.9 + f * 0.7)) * (0.6 + 0.4 * random(`eq${i}-${Math.floor(f / 2)}`));
            return <div key={i} style={{ width: 12, height: 90 * v, background: i % 5 === 0 ? RED : INK, borderRadius: 3 }} />;
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Craft: React.FC = () => {
  const f = useCurrentFrame();
  const STRIPS = 6;
  return (
    <AbsoluteFill>
      <Wipe color={INK} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative", width: 1100, height: 280 }}>
          {Array.from({ length: STRIPS }).map((_, i) => {
            const e = seg(f, i * 1.2, 10, E.out);
            const dir = i % 2 ? 1 : -1;
            return (
              <div key={i} style={{ position: "absolute", inset: 0, clipPath: `inset(${(i / STRIPS) * 100}% 0 ${100 - ((i + 1) / STRIPS) * 100}% 0)`, transform: `translateX(${(1 - e) * dir * 900}px)` }}>
                <div style={{ ...BIG, color: LIME, textAlign: "center" }}>CRAFT.</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const TypeScene: React.FC = () => (
  <AbsoluteFill style={{ background: INK }}>
    <Sequence durationInFrames={15} layout="none"><Timing /></Sequence>
    <Sequence from={15} durationInFrames={15} layout="none"><AbsoluteFill style={{ background: RED }}><Easing /></AbsoluteFill></Sequence>
    <Sequence from={30} durationInFrames={15} layout="none"><AbsoluteFill style={{ background: BLUE }}><Rhythm /></AbsoluteFill></Sequence>
    <Sequence from={45} durationInFrames={15} layout="none"><AbsoluteFill style={{ background: PAPER }}><Craft /></AbsoluteFill></Sequence>
  </AbsoluteFill>
);

/* ── 02 · morph ── */
const polyR = (verts: [number, number][]) => (th: number) => {
  const dx = Math.cos(th);
  const dy = Math.sin(th);
  let best = 1;
  let found = false;
  for (let i = 0; i < verts.length; i++) {
    const a = verts[i];
    const b = verts[(i + 1) % verts.length];
    const ex = b[0] - a[0];
    const ey = b[1] - a[1];
    const det = -dx * ey + ex * dy;
    if (Math.abs(det) < 1e-9) continue;
    const t = (-a[0] * ey + ex * a[1]) / det;
    const s = (dx * a[1] - dy * a[0]) / det;
    if (t > 0 && s >= -1e-6 && s <= 1 + 1e-6 && (!found || t < best)) {
      best = t;
      found = true;
    }
  }
  return best;
};
const ngon = (n: number, r: number, rot = -Math.PI / 2, inner?: number): [number, number][] =>
  Array.from({ length: inner ? n * 2 : n }, (_, i) => {
    const rr = inner && i % 2 ? inner : r;
    const a = rot + (i / (inner ? n * 2 : n)) * Math.PI * 2;
    return [Math.cos(a) * rr, Math.sin(a) * rr];
  });

const SHAPES: ((th: number) => number)[] = [
  () => 1,
  polyR(ngon(4, 1.12, Math.PI / 4)),
  polyR(ngon(3, 1.2)),
  polyR(ngon(5, 1.2, -Math.PI / 2, 0.52)),
  (th) => 0.92 + 0.12 * Math.sin(3 * th + 0.5) + 0.08 * Math.sin(5 * th - 1) + 0.05 * Math.sin(7 * th),
  () => 1,
];
const SHAPE_COL = [RED, BLUE, INK, RED, BLUE, INK];
const NAMES = ["CIRCLE", "SQUARE", "TRIANGLE", "STAR", "BLOB"];

const shapePath = (f: number, R: number) => {
  const k = Math.min(SHAPES.length - 2, Math.max(0, Math.floor(f / 15)));
  const e = E.inOut(clamp01((f - k * 15 - 3) / 10));
  const pts = Array.from({ length: 240 }, (_, i) => {
    const th = (i / 240) * Math.PI * 2;
    const r = mix(SHAPES[k](th), SHAPES[k + 1](th), e) * R;
    return `${i ? "L" : "M"}${(Math.cos(th) * r).toFixed(1)} ${(Math.sin(th) * r).toFixed(1)}`;
  });
  return { d: pts.join(" ") + "Z", k, e };
};

const Morph: React.FC = () => {
  const f = useCurrentFrame();
  const shrink = seg(f, 62, 12, E.in2);
  const R = mix(300, 22, shrink) * mix(0.3, 1, seg(f, 0, 10, E.back));
  const rotAt = (t: number) => Math.floor(t / 15) * 90 + E.inOut(clamp01(((t % 15) - 3) / 10)) * 90;
  const { d, k, e } = shapePath(f, R);
  const color = e > 0.5 ? SHAPE_COL[k + 1] : SHAPE_COL[k];
  return (
    <AbsoluteFill style={{ background: PAPER }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {[5, 4, 3, 2, 1].map((g) => {
          const t = Math.max(0, f - g * 2);
          const gp = shapePath(t, mix(300, 22, seg(t, 62, 12, E.in2)) * mix(0.3, 1, seg(t, 0, 10, E.back)));
          return <path key={g} d={gp.d} transform={`translate(960 540) rotate(${rotAt(t)})`} fill="none" stroke={INK} strokeOpacity={0.14 - g * 0.02} strokeWidth={3} />;
        })}
        <path d={d} transform={`translate(960 540) rotate(${rotAt(f)})`} fill={color} />
      </svg>
      <div style={{ position: "absolute", left: 120, bottom: 110, fontFamily: MONO, fontSize: 26, letterSpacing: "0.2em", color: INK, opacity: 1 - shrink }}>
        {NAMES[Math.min(4, k + (e > 0.5 ? 1 : 0))]} <span style={{ opacity: 0.4 }}>→ {NAMES[Math.min(4, k + 1)]}</span>
      </div>
    </AbsoluteFill>
  );
};

/* ── 05 · slats ── */
const PANELS = [
  { word: "DESIGN", bg: BLUE, fg: PAPER },
  { word: "ANIMATE", bg: LIME, fg: INK },
  { word: "SOUND", bg: RED, fg: INK },
  { word: "DELIVER", bg: PAPER, fg: INK },
];
const SLATS = 8;

const Panel: React.FC<{ word: string; bg: string; fg: string; idx: number }> = ({ word, bg, fg, idx }) => (
  <AbsoluteFill style={{ background: bg, alignItems: "center", justifyContent: "center" }}>
    <div style={{ ...BIG, fontSize: 300, color: fg }}>{word}</div>
    <div style={{ position: "absolute", left: 120, bottom: 110, fontFamily: MONO, fontSize: 26, letterSpacing: "0.2em", color: fg }}>{String(idx + 1).padStart(2, "0")} / 04</div>
  </AbsoluteFill>
);

const Slats: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: INK }}>
      {PANELS.map((p, idx) => {
        const at = idx * 15;
        if (f < at) return null;
        return (
          <AbsoluteFill key={p.word}>
            {Array.from({ length: SLATS }).map((_, i) => {
              const e = seg(f, at + i * 0.6, 9, E.out);
              const dir = i % 2 ? 1 : -1;
              const w = 1920 / SLATS;
              return (
                <div key={i} style={{ position: "absolute", left: i * w, top: 0, width: w + 1, height: 1080, overflow: "hidden", transform: `translateY(${(1 - e) * dir * 1080}px)` }}>
                  <div style={{ position: "absolute", left: -i * w, top: 0, width: 1920, height: 1080 }}>
                    <Panel {...p} idx={idx} />
                  </div>
                </div>
              );
            })}
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

/* ── 06 · end ── */
const End: React.FC = () => {
  const f = useCurrentFrame();
  const pop = ELASTIC(clamp01(f / 14));
  const stretch = seg(f, 12, 10, E.out);
  const out = seg(f, 36, 8, E.in2);
  const w = mix(64 * pop, 900, stretch) * (1 - out) + 14 * out;
  const h = mix(64 * pop, 8, stretch) * (1 - out) + 14 * out;
  const blink = f >= 44 ? 0 : 1;
  return (
    <AbsoluteFill style={{ background: INK }}>
      <div style={{ position: "absolute", left: 960 - w / 2, top: 640 - h / 2, width: w, height: h, borderRadius: 999, background: LIME, opacity: blink, boxShadow: "0 0 40px rgba(215,255,59,0.4)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 380, height: 240, overflow: "hidden", display: "flex", justifyContent: "center", alignItems: "flex-end", opacity: 1 - out }}>
        <div style={{ ...BIG, fontSize: 210, color: PAPER, transform: `translateY(${(1 - seg(f, 16, 14, E.out)) * 110}%)` }}>
          SHOWREEL <span style={{ color: LIME }}>’26</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 680, textAlign: "center", fontFamily: MONO, fontSize: 30, letterSpacing: "0.25em", color: "rgba(243,241,236,0.7)", opacity: seg(f, 24, 10) * (1 - out) }}>
        EVERY FRAME, WRITTEN IN CODE.
      </div>
    </AbsoluteFill>
  );
};

/* ── HUD & grain ── */
const LABELS: [number, string][] = [
  [T.intro, "00 · INTRO"],
  [T.type, "01 · TYPE"],
  [T.morph, "02 · MORPH"],
  [T.depth, "03 · DEPTH"],
  [T.parts, "04 · PARTICLES"],
  [T.slats, "05 · RHYTHM"],
  [T.end, "06 · FIN"],
];

const Hud: React.FC = () => {
  const f = useCurrentFrame();
  const label = [...LABELS].reverse().find(([at]) => f >= at)![1];
  const tc = `00:00:${String(Math.floor(f / 30)).padStart(2, "0")}:${String(f % 30).padStart(2, "0")}`;
  const mark = (s: React.CSSProperties) => <div style={{ position: "absolute", width: 34, height: 34, ...s }} />;
  const c = "2px solid #fff";
  return (
    <AbsoluteFill style={{ mixBlendMode: "difference", color: "#fff", fontFamily: MONO, fontSize: 20, letterSpacing: "0.18em", pointerEvents: "none" }}>
      {mark({ left: 48, top: 48, borderLeft: c, borderTop: c })}
      {mark({ right: 48, top: 48, borderRight: c, borderTop: c })}
      {mark({ left: 48, bottom: 48, borderLeft: c, borderBottom: c })}
      {mark({ right: 48, bottom: 48, borderRight: c, borderBottom: c })}
      <div style={{ position: "absolute", left: 100, top: 58 }}>{label}</div>
      <div style={{ position: "absolute", right: 100, top: 58 }}>{tc}</div>
      <div style={{ position: "absolute", right: 100, bottom: 58 }}>SHOWREEL ’26</div>
      <div style={{ position: "absolute", left: 100, bottom: 64, width: 360, height: 2, background: "rgba(255,255,255,0.3)" }}>
        <div style={{ width: `${(f / REEL_FRAMES) * 100}%`, height: 2, background: "#fff" }} />
      </div>
    </AbsoluteFill>
  );
};

const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.09, mixBlendMode: "overlay" }}>
      <svg width={1920} height={1080}>
        <filter id="g">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={f % 24} />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width={1920} height={1080} filter="url(#g)" />
      </svg>
    </AbsoluteFill>
  );
};

const Blur: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <CameraMotionBlur shutterAngle={200} samples={6}>
    {children}
  </CameraMotionBlur>
);

const cues = (): Cue[] => [
  { at: 12, name: "tap", volume: 0.6 },
  { at: 22, name: "tap", volume: 0.4 },
  { at: 28, name: "tap", volume: 0.25 },
  { at: 34, name: "whoosh", volume: 0.45 },
  { at: 44, name: "slam-1", volume: 0.4 },
  { at: T.type, name: "slam-2", volume: 0.45 },
  ...[0, 2, 4, 6, 8, 10, 12].map((d) => ({ at: T.type + d, name: `key-${(d / 2) % 8 + 1}`, volume: 0.35 })),
  { at: T.type + 15, name: "swish-1", volume: 0.35 },
  { at: T.type + 30, name: "pop", volume: 0.45 },
  { at: T.type + 45, name: "swish-3", volume: 0.4 },
  ...[0, 15, 30, 45].map((d, i) => ({ at: T.morph + d + 3, name: `swish-${(i % 3) + 1}`, volume: 0.28 })),
  { at: T.morph + 62, name: "pop", volume: 0.3 },
  { at: T.depth, name: "whoosh", volume: 0.4 },
  { at: T.depth + 20, name: "riser", volume: 0.25 },
  { at: T.depth + 58, name: "swish-2", volume: 0.3 },
  { at: T.parts, name: "riser", volume: 0.3 },
  { at: T.parts + 30, name: "slam-3", volume: 0.4 },
  { at: T.parts + 60, name: "impact", volume: 0.55 },
  ...[0, 15, 30, 45].map((d) => ({ at: T.slats + d, name: "cut", volume: 0.45 })),
  ...[0, 15, 30, 45].map((d, i) => ({ at: T.slats + d + 1, name: `swish-${(i % 3) + 1}`, volume: 0.25 })),
  { at: T.end, name: "pop", volume: 0.45 },
  { at: T.end + 16, name: "ding", volume: 0.3 },
  { at: T.end + 44, name: "click", volume: 0.5 },
];

export const Reel: React.FC = () => {
  const { fps, durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Sequence durationInFrames={T.type}><Blur><Intro /></Blur></Sequence>
      <Sequence from={T.type} durationInFrames={T.morph - T.type}><Blur><TypeScene /></Blur></Sequence>
      <Sequence from={T.morph} durationInFrames={T.depth - T.morph}><Blur><Morph /></Blur></Sequence>
      <Sequence from={T.depth} durationInFrames={T.parts - T.depth}><Cubes /></Sequence>
      <Sequence from={T.parts} durationInFrames={T.slats - T.parts}><Particles2D text="EVERY FRAME" /></Sequence>
      <Sequence from={T.slats} durationInFrames={T.end - T.slats}><Blur><Slats /></Blur></Sequence>
      <Sequence from={T.end}><Blur><End /></Blur></Sequence>
      <Grain />
      <Hud />
      <Audio src={staticFile("music/bgm.wav")} volume={(f) => interpolate(f, [0, 2, durationInFrames - fps * 0.6, durationInFrames - 1], [0, 0.8, 0.8, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      <SoundCues cues={cues()} />
    </AbsoluteFill>
  );
};
