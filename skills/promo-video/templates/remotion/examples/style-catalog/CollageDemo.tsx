import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { Halftone, jitter, Kraft, Ransom, Tape, Torn } from "../cinematic/collage";
import { fam } from "../cinematic/type";

/**
 * 09 · 拼贴风 — "YouWare scrapbook": on kraft board, a typed prompt slip, then four halftone cut-outs of real YouWare
 * work (website / deck / sheet / report) are taped down on twos, each stamped DONE, and a ransom-note YOUWARE lands
 * over it all with the slogan on a torn strip. 330 frames.
 */
export const COLLAGE_LEN = 330;
const MONO = fam("Geist Mono");
const HAND = fam("Caveat");
const SERIF = fam("DM Serif Display");
const RED = "#D93A2B";

type Cut = { src: string; nat: [number, number]; crop: [number, number, number, number]; x: number; y: number; w: number; h: number; rot: number; at: number; ink: string; paper: string; label: string; note: string };
const CUTS: Cut[] = [
  { src: "site/capability-websites.png", nat: [2246, 1424], crop: [0.3, 0.19, 0.98, 0.95], x: 120, y: 250, w: 560, h: 340, rot: -4, at: 40, ink: "#2556B6", paper: "#F4E6D4", label: "WEBSITE", note: "live!" },
  { src: "site/capability-slide-decks.png", nat: [2534, 1600], crop: [0.42, 0.32, 0.94, 0.8], x: 1230, y: 150, w: 540, h: 330, rot: 5, at: 70, ink: "#7D2F7D", paper: "#F6DCD6", label: "SLIDES", note: "pitch-ready" },
  { src: "site/capability-spreadsheets.png", nat: [2246, 1424], crop: [0.3, 0.22, 0.96, 0.8], x: 230, y: 650, w: 540, h: 320, rot: 3, at: 100, ink: "#1F5A3A", paper: "#E4EAD2", label: "SHEETS", note: "3 scenarios" },
  { src: "site/capability-research-reports.png", nat: [2246, 1424], crop: [0.5, 0.2, 0.87, 0.72], x: 1240, y: 600, w: 520, h: 360, rot: -6, at: 130, ink: "#9C2F1E", paper: "#F7E3C4", label: "REPORT", note: "ready to share" },
];
const STAMP0 = 178;
const TITLE = 222;
const STRIP = 262;

/** Stop-motion timing: animate on twos. */
const two = (t: number) => Math.floor(t / 2) * 2;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const out3 = (v: number) => 1 - Math.pow(1 - clamp01(v), 3);

const CutOut: React.FC<{ c: Cut; i: number; t: number }> = ({ c, i, t }) => {
  const lt = two(t) - c.at;
  if (lt < 0) return null;
  // placed by hand: comes in from off-board in 3 steps, lands with a small overshoot
  const k = out3(lt / 10);
  const from = [
    [-700, -200],
    [700, -300],
    [-600, 400],
    [700, 400],
  ][i];
  const j = jitter(t, `cut${i}`, 1.5, 0.35);
  const x = c.x + from[0] * (1 - k) + j.x;
  const y = c.y + from[1] * (1 - k) + j.y;
  const rot = c.rot + (1 - k) * (i % 2 ? 18 : -18) + j.r;
  const [x0, y0, x1, y1] = c.crop;
  const cw = (x1 - x0) * c.nat[0];
  const s = (c.w - 24) / cw;
  const fit = { left: -x0 * c.nat[0] * s, top: -y0 * c.nat[1] * s, width: c.nat[0] * s };
  const tape = lt >= 12;
  const label = lt >= 16;
  const note = out3((lt - 20) / 8);
  const stampT = two(t) - (STAMP0 + i * 8);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: c.w, height: c.h, transform: `rotate(${rot}deg)` }}>
      <Torn w={c.w} h={c.h} seed={`c${i}`} amp={5}>
        <div style={{ position: "absolute", left: 12, top: 12 }}>
          <Halftone src={c.src} w={c.w - 24} h={c.h - 24} cell={6} ink={c.ink} paper={c.paper} fit={fit} gain={1.05} />
        </div>
      </Torn>
      {tape && (
        <>
          <Tape x={30} y={10} rot={-38} seed={`t${i}a`} w={140} />
          <Tape x={c.w - 30} y={10} rot={36} seed={`t${i}b`} w={140} />
        </>
      )}
      {label && (
        <div style={{ position: "absolute", left: -18, bottom: -34, transform: "rotate(-3deg)" }}>
          <Ransom text={c.label} t={t} at={c.at + 16} size={46} seed={`lab${i}`} gap={2} />
        </div>
      )}
      {note > 0 && (
        <div style={{ position: "absolute", right: -10, bottom: -58, fontFamily: HAND, fontWeight: 700, fontSize: 50, color: RED, transform: `rotate(-6deg)`, opacity: note, clipPath: `inset(0 ${(1 - note) * 100}% 0 0)` }}>
          {c.note}
        </div>
      )}
      {stampT >= 0 && <Stamp t={stampT} seed={`st${i}`} />}
    </div>
  );
};

const Stamp: React.FC<{ t: number; seed: string }> = ({ t, seed }) => {
  const slam = t < 4 ? 1.6 - t * 0.15 : 1;
  const op = t < 2 ? 0.5 : 0.88;
  const rot = -14 + (random(seed) - 0.5) * 10;
  return (
    <div style={{ position: "absolute", right: 36, top: 30, transform: `rotate(${rot}deg) scale(${slam})`, opacity: op, mixBlendMode: "multiply" }}>
      <div
        style={{
          fontFamily: '"Anton", Impact, sans-serif',
          fontSize: 64,
          letterSpacing: "0.08em",
          color: RED,
          border: `6px solid ${RED}`,
          borderRadius: 12,
          padding: "0 18px",
          lineHeight: 1.15,
          WebkitMaskImage: GRUNGE,
          maskImage: GRUNGE,
          WebkitMaskSize: "300px 200px",
        }}
      >
        DONE ✓
      </div>
    </div>
  );
};
const GRUNGE = `url("data:image/svg+xml;utf8,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.4 2.1"/></filter><rect width="300" height="200" filter="url(#g)"/></svg>',
)}")`;

const PromptSlip: React.FC<{ t: number }> = ({ t }) => {
  const lt = two(t) - 8;
  if (lt < 0) return null;
  const k = out3(lt / 8);
  const j = jitter(t, "slip", 1, 0.25);
  const text = "PLAN MY CAFÉ LAUNCH";
  const n = Math.floor(clamp01((lt - 8) / 20) * text.length);
  return (
    <div style={{ position: "absolute", left: 640 + j.x, top: 60 + (1 - k) * -200 + j.y, transform: `rotate(${-2 + j.r}deg)` }}>
      <Torn w={640} h={110} seed="slip" rim="#FFFFFF" amp={4}>
        <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", display: "flex", alignItems: "center", paddingLeft: 36, fontFamily: MONO, fontWeight: 600, fontSize: 40, color: "#1D1A24", letterSpacing: "0.04em" }}>
          {text.slice(0, n)}
          <span style={{ opacity: Math.floor(t / 6) % 2 && n < text.length ? 1 : 0 }}>_</span>
        </div>
      </Torn>
      <Tape x={4} y={54} rot={80} seed="slipt" w={110} />
    </div>
  );
};

const Decor: React.FC = () => (
  <>
    {/* grid-paper scrap + coffee ring, already on the board */}
    <div style={{ position: "absolute", left: 60, top: 40, transform: "rotate(-7deg)" }}>
      <Torn w={380} h={200} seed="grid" rim="#F4F1E8" shadow>
        <div style={{ position: "absolute", inset: 0, background: "#F4F1E8", backgroundImage: "linear-gradient(#B9D0E6 1.5px, transparent 1.5px), linear-gradient(90deg, #B9D0E6 1.5px, transparent 1.5px)", backgroundSize: "22px 22px" }} />
        <div style={{ position: "absolute", left: 36, top: 44, fontFamily: HAND, fontWeight: 700, fontSize: 46, color: "#2556B6", transform: "rotate(-3deg)" }}>café launch ☕</div>
      </Torn>
    </div>
    <div style={{ position: "absolute", left: 1560, top: 470, width: 210, height: 210, borderRadius: "50%", border: "10px solid rgba(110,70,30,0.22)", filter: "blur(1.5px)", clipPath: "polygon(0 0, 100% 0, 100% 78%, 0 100%)" }} />
  </>
);

export const CollageDemo: React.FC = () => {
  const t = useCurrentFrame();
  const strip = out3((two(t) - STRIP) / 8);
  const dim = clamp01((two(t) - TITLE + 6) / 10) * 0.22;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Kraft />
      <Decor />
      <PromptSlip t={t} />
      {CUTS.map((c, i) => (
        <CutOut key={i} c={c} i={i} t={t} />
      ))}
      <AbsoluteFill style={{ background: "#3A2A18", opacity: dim }} />
      {two(t) >= TITLE && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 360, display: "flex", justifyContent: "center" }}>
          <Ransom text="YOUWARE" t={t} at={TITLE} size={168} seed="title" gap={4} />
        </div>
      )}
      {strip > 0 && (
        <div style={{ position: "absolute", left: 960 - 460, top: 610 + (1 - strip) * 240, transform: `rotate(${1.5 + jitter(t, "strip", 0, 0.3).r}deg)` }}>
          <Torn w={920} h={120} seed="strip" rim="#FFFDF6" amp={5}>
            <div style={{ position: "absolute", inset: 0, background: "#FFFDF6", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: SERIF, fontStyle: "italic", fontSize: 62, color: "#1D1A24" }}>From answers to outcomes.</div>
          </Torn>
          <Tape x={10} y={60} rot={84} seed="st-a" w={120} />
          <Tape x={910} y={60} rot={-80} seed="st-b" w={120} />
        </div>
      )}
      <AbsoluteFill style={{ background: "#CDB38D", opacity: 1 - clamp01(t / 8), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
