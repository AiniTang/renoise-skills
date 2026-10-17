import React, { useEffect, useMemo, useState } from "react";
import { AbsoluteFill, Audio, cancelRender, continueRender, delayRender, interpolate, staticFile, useCurrentFrame } from "remotion";
import { keyCues, SoundCues, type Cue } from "../cinematic/sfx";
import { CH, CHAIN_LEN, PROMPT, typeAt, YouWareChain } from "./YouWareChain";
import {
  BounceGraph,
  CubeStage,
  drawHalftone,
  drawMarquee,
  drawPalette,
  drawRidges,
  drawStrings,
  drawTruchet,
  drawVoice,
  icoFaces,
  MARK_PATHS,
  MARK_WIDTH,
  ParticleField,
  penAt,
  SpecimenCanvas,
  SpecimenHud,
  StrokeDraw,
  VIBE_DOT,
  VIBE_PATH,
  VolumeScene,
  clamp01,
  easeBack,
  easeInOut,
  easeOut,
  mix,
  rgba,
  win,
  type BounceSpec,
  type CubeFace,
  type SpecimenTheme,
} from "../cinematic/specimen";

/*
 * YouWare brand film, 60 s cut (style-pack-03). Slow piano (Silent Descent, 71.8 BPM half-time):
 * every shot sits on the beat grid and the piano's burst (track 69.8 s) lands on the particle cut.
 * Each geometric chapter carries one human value: small → big, inclusion, listening, craft, experience,
 * innovation, together.
 */
const FPS = 30;
const BPM = 71.8;
const BEAT = (FPS * 60) / BPM; // 25.07 frames ≈ 0.836 s
const at = (b: number) => Math.round(b * BEAT);
const B = { point: 4, line: 16, plane: 29, volume: 45, field: 59, outro: 67.5, end: 77.5 };
export const FILM60_FRAMES = at(B.end) + 1;
const sec = (f: number, from: number) => (f - at(from)) / FPS;

const TH: SpecimenTheme = {
  ink: "#151513",
  paper: "#F5F0E6",
  paper2: "#ECE5D6",
  cream: "#F4EEE2",
  accent: "#CFE3A0",
  accent2: "#EE8C6C",
  palette: [
    { name: "IVORY", hex: "#F5F0E6" },
    { name: "PISTACHIO", hex: "#CFE3A0" },
    { name: "SAGE", hex: "#BBC98D" },
    { name: "MOSS", hex: "#7D8F57" },
    { name: "TEAL", hex: "#4FA597" },
    { name: "LAVENDER", hex: "#B4A5E4" },
    { name: "CORAL", hex: "#EE8C6C" },
    { name: "INK", hex: "#151513" },
  ],
  sprinkle: ["#B4A5E4", "#CFE3A0", "#EE8C6C", "#4FA597", "#86A8DA", "#BBC98D"],
  serif: '"Hepta Slab", Georgia, serif',
  sans: '"DM Sans", -apple-system, sans-serif',
  mono: '"SF Mono", Menlo, monospace',
};
const MOSS = "#7D8F57";
const WORDS = ["WEBSITES", "SLIDES", "SHEETS", "REPORTS"];

const useBrandFonts = () => {
  const [handle] = useState(() => delayRender("brand fonts"));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const faces: [string, string, FontFaceDescriptors][] = [
      ["DM Sans", "DMSans-300.woff2", { weight: "300" }],
      ["DM Sans", "DMSans-400.woff2", { weight: "400" }],
      ["DM Sans", "DMSans-500.woff2", { weight: "500" }],
      ["DM Sans", "DMSans-700.woff2", { weight: "600 700" }],
      ["DM Sans", "DMSans-900.woff2", { weight: "800 900" }],
      ["Hepta Slab", "HeptaSlab.woff2", { weight: "1 900" }],
    ];
    Promise.all(faces.map(([fam, file, d]) => new FontFace(fam, `url(${staticFile(`fonts/${file}`)})`, d).load().then((ff) => document.fonts.add(ff))))
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [handle]);
  return ready;
};

/** One line of manifesto copy; beats in, beats out. */
const Line: React.FC<{ f: number; from: number; to: number; children: React.ReactNode; y?: number; color?: string; size?: number; halo?: string; weight?: number }> = ({
  f,
  from,
  to,
  children,
  y = 800,
  color = TH.cream,
  size = 40,
  halo,
  weight = 300,
}) => {
  const a = win(f, at(from), 14, easeOut) * (1 - win(f, at(to) - 10, 10));
  if (a <= 0) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: y,
        textAlign: "center",
        fontFamily: TH.serif,
        fontWeight: weight,
        fontSize: size,
        color,
        opacity: a,
        transform: `translateY(${(1 - a) * 14}px)`,
        textShadow: halo ? `0 0 10px ${halo}, 0 0 24px ${halo}, 0 0 40px ${halo}` : undefined,
      }}
    >
      {children}
    </div>
  );
};

/* ── prologue + 01 POINT ───────────────────────────────────────────────────────── */
const WORD = "idea";
const WORD_SIZE = 190;
const BASELINE = 600;
const DOT = 26;
const TYPE_AT = [4.45, 4.75, 5.05, 5.35].map(at);
const BOUNCE = { at: at(7.5), contacts: [22, 40, 54], heights: [270, 140, 60] };
const LAND = { x: 700, y: BASELINE };

const useWordWidths = () =>
  useMemo(() => {
    const g = document.createElement("canvas").getContext("2d")!;
    g.font = `400 ${WORD_SIZE}px ${TH.serif}`;
    return Array.from(WORD).map((c) => g.measureText(c).width);
  }, []);

const Point: React.FC<{ f: number }> = ({ f }) => {
  const widths = useWordWidths();
  const typedE = TYPE_AT.map((a) => easeOut(clamp01((f - a) / 6)));
  const W = widths.reduce((s, w, i) => s + w * typedE[i], 0) + DOT + 8;
  const left = 960 - W / 2;
  const dotX0 = left + widths.reduce((s, w, i) => s + w * typedE[i], 0) + 8 + DOT / 2;
  const tb = f - BOUNCE.at;
  const bounce: BounceSpec = { x0: dotX0, x1: LAND.x, floor: BASELINE, contacts: BOUNCE.contacts, heights: BOUNCE.heights, r: DOT / 2 };
  const phase = (f - at(0.5)) / (BEAT * 0.9);
  const blinkOn = f >= at(0.5) && (f >= at(3.8) || phase % 1 < 0.55);
  const m = easeInOut(clamp01((f - at(4)) / 8));
  const cw = mix(5, DOT, m);
  const ch = mix(150, DOT, m);
  const cy = mix(BASELINE - 140, BASELINE - DOT, m);
  const htSpawn = (f - at(11)) * 50;
  const collapse = win(f, at(15), at(16) - at(15) - 2);
  const guides = win(f, BOUNCE.at + 2, 6) * (1 - win(f, at(11), 10));
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {f >= at(11) && <SpecimenCanvas t={f - at(11)} draw={drawHalftone(TH, { ox: LAND.x, oy: LAND.y - DOT / 2, spawn: htSpawn, collapse, diverse: 1 })} />}
      {f < BOUNCE.at + 40 &&
        Array.from(WORD).map((c, i) => {
          if (typedE[i] <= 0) return null;
          const x = left + widths.slice(0, i).reduce((s, w, j) => s + w * typedE[j], 0);
          const tf = Math.max(0, tb - i * 2.5);
          const fall = tb > 0 ? { y: -9 * tf + 0.9 * tf * tf, r: tf * (i % 2 ? 2.4 : -2.1), o: 1 - clamp01((tf - 14) / 10) } : { y: 0, r: 0, o: 1 };
          return (
            <span
              key={i}
              style={{
                position: "absolute",
                left: x,
                top: BASELINE - WORD_SIZE * 0.97,
                fontFamily: TH.serif,
                fontSize: WORD_SIZE,
                lineHeight: 1,
                color: TH.cream,
                opacity: typedE[i] * fall.o,
                transform: `translateY(${(1 - typedE[i]) * 24 + fall.y}px) rotate(${fall.r}deg)`,
                transformOrigin: "50% 80%",
              }}
            >
              {c}
            </span>
          );
        })}
      {tb < 0 && blinkOn && <div style={{ position: "absolute", left: dotX0 - cw / 2, top: cy, width: cw, height: ch, borderRadius: m > 0.5 ? "50%" : 3 * m + 1, background: TH.cream }} />}
      {tb >= 0 && f < at(11) + 18 && <BounceGraph th={TH} b={bounce} t={tb} frameOffset={BOUNCE.at} guides={guides} ballAlpha={1 - clamp01((htSpawn - 60) / 80)} />}
      <Line f={f} from={0.9} to={3.9} y={720}>
        Everything big starts small.
      </Line>
      {f >= at(11.6) && f < at(15.5) && (
        <div style={{ position: "absolute", left: 560, right: 560, top: 860, height: 130, borderRadius: 65, background: `radial-gradient(ellipse at 50% 50%, ${rgba(TH.ink, 0.92 * win(f, at(11.6), 12) * (1 - win(f, at(15.1), 10)))} 45%, transparent 72%)` }} />
      )}
      <Line f={f} from={11.8} to={15.4} y={900} halo={TH.ink}>
        No two people are alike.
      </Line>
    </AbsoluteFill>
  );
};

/* ── 02 LINE: listen → voices → connections → vibe coding ──────────────────── */
const VS = 1.15;
const VX = 960 - 315 * VS;
const VY = 470 - 221 * VS;
const vibePt = (p: { x: number; y: number }) => ({ x: VX + p.x * VS, y: VY + p.y * VS });

const LineCh: React.FC<{ f: number }> = ({ f }) => {
  const voice = f < at(20.2);
  const ridges = f >= at(19.5) && f < at(22.7);
  const strings = f >= at(22.7) && f < at(26);
  const k = mix(2, 3.4, win(f, at(22.7), at(25) - at(22.7)));
  // strings squash into a 600 px line, the line retracts into a dot at its left end, the dot writes "vibe"
  const retract = win(f, at(25.9), at(26.3) - at(25.9));
  const start = vibePt({ x: 40, y: 262 });
  const write = win(f, at(26.3), at(28.5) - at(26.3), (x) => x);
  const end = vibePt(penAt([VIBE_PATH], 1));
  const hop = win(f, at(28.5), at(28.9) - at(28.5));
  const tit = vibePt(VIBE_DOT);
  const toLine = win(f, at(28.95), at(29.3) - at(28.95));
  let dot = { x: mix(660, start.x, retract), y: mix(540, start.y, retract) };
  if (write > 0 && write < 1) dot = vibePt(penAt([VIBE_PATH], write));
  if (write >= 1) dot = { x: mix(end.x, tit.x, hop), y: mix(end.y, tit.y, hop) - Math.sin(hop * Math.PI) * 120 };
  if (toLine > 0) dot = { x: mix(tit.x, 960, toLine), y: mix(tit.y, 540, toLine) };
  const fadeWord = win(f, at(28.8), 10);
  const lineW = mix(DOT, 600, easeInOut(clamp01((f - at(29.1)) / 6)));
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {voice && (
        <SpecimenCanvas
          t={f - at(16)}
          draw={drawVoice(TH, { grow: win(f, at(16), at(16.8) - at(16)), amp: win(f, at(16.6), at(17.4) - at(16.6)) * (1 - win(f, at(19.3), at(20) - at(19.3))) })}
        />
      )}
      {ridges && (
        <SpecimenCanvas
          t={f - at(19.5)}
          style={{ position: "absolute", inset: 0, opacity: win(f, at(19.5), 8) }}
          draw={drawRidges(TH, { spread: win(f, at(19.5), at(20.5) - at(19.5)), reveal: 1, amp: win(f, at(20), at(21.2) - at(20)), chord: win(f, at(22), at(22.7) - at(22)) })}
        />
      )}
      {strings && (
        <SpecimenCanvas
          t={f - at(22.7)}
          draw={drawStrings(TH, { k, enter: win(f, at(22.7), at(23.6) - at(22.7)), extra: win(f, at(23.1), at(24) - at(23.1)), squash: win(f, at(25.2), at(25.9) - at(25.2)) })}
        />
      )}
      {f >= at(25.9) && f < at(26.3) && <div style={{ position: "absolute", left: 660, top: 539, width: mix(600, 2, retract), height: 2.2, background: TH.cream }} />}
      {f >= at(25.9) && f < at(29.4) && (
        <div style={{ position: "absolute", inset: 0 }}>
          <div style={{ position: "absolute", inset: 0, opacity: 1 - fadeWord }}>
            <StrokeDraw paths={[VIBE_PATH]} p={write} color={TH.cream} width={5.2 / VS} transform={`translate(${VX} ${VY}) scale(${VS})`} nib={0} />
          </div>
          {f < at(29.1) ? (
            <div
              style={{
                position: "absolute",
                left: dot.x - DOT / 2,
                top: dot.y - DOT / 2,
                width: DOT,
                height: DOT,
                borderRadius: "50%",
                background: TH.cream,
                boxShadow: write > 0 && write < 1 ? `0 0 26px ${rgba(TH.cream, 0.8)}` : undefined,
                transform: `scale(${write > 0 && write < 1 ? 0.55 : write >= 1 && toLine <= 0 ? mix(0.55, 0.62, hop) : 1})`,
              }}
            />
          ) : (
            <div style={{ position: "absolute", left: 960 - lineW / 2, top: 539, width: lineW, height: 2.2, background: TH.cream }} />
          )}
        </div>
      )}
      <Line f={f} from={16.8} to={20.2} y={820}>
        So we listen first.
      </Line>
      <Line f={f} from={26.4} to={29.3} y={780}>
        Vibe coding — an idea that went for a walk.
      </Line>
    </AbsoluteFill>
  );
};

/* ── 03 PLANE: palette (taste) → one thing at a time (YouWare's own details) → for everyone ── */
const CHAIN_AT = 32.4; // beats; the chain lasts CHAIN_LEN frames, then the Truchet opens from its last dot
const TRU = CHAIN_AT + CHAIN_LEN / BEAT; // ≈ 42.2

const Plane: React.FC<{ f: number }> = ({ f }) => {
  const c0 = at(CHAIN_AT);
  const tIris = win(f, at(TRU), 10, easeOut) * 1250;
  const hole = win(f, at(TRU + 0.5), 12) * 215 * (1 - win(f, at(45), 8));
  const textA = win(f, at(TRU + 0.6), 12, easeOut) * (1 - win(f, at(44.5), 10));
  return (
    <AbsoluteFill style={{ background: TH.paper }}>
      {f >= c0 && f < at(TRU) + 12 && <YouWareChain th={TH} t={f - c0} />}
      {f < at(32.6) && (
        <AbsoluteFill>
          <SpecimenCanvas
            t={f - at(29)}
            draw={drawPalette(TH, {
              grow: win(f, at(29.3), at(30.3) - at(29.3)),
              split: win(f, at(30.3), at(31.3) - at(30.3)),
              labels: win(f, at(30.8), at(31.8) - at(30.8), (x) => x),
              exit: win(f, at(32), at(32.6) - at(32), (x) => x),
              under: "none",
            })}
          />
        </AbsoluteFill>
      )}
      {f >= at(TRU) && (
        <AbsoluteFill style={{ clipPath: `circle(${tIris}px at 50% 48%)` }}>
          <SpecimenCanvas t={f - at(TRU)} draw={drawTruchet(TH, { assemble: win(f, at(TRU), at(TRU + 1) - at(TRU), (x) => x), hole })} />
          <div style={{ position: "absolute", left: 0, right: 0, top: 470, textAlign: "center", fontFamily: TH.serif, fontWeight: 500, fontSize: 64, lineHeight: 1.12, color: TH.ink, opacity: textA }}>
            <div style={{ transform: `translateY(${(1 - textA) * 16}px)` }}>From vibe coding</div>
            <div style={{ transform: `translateY(${(1 - win(f, at(TRU + 1.1), 12, easeOut)) * 16}px)`, opacity: win(f, at(TRU + 1.1), 12) }}>
              to work, for <span style={{ color: MOSS }}>everyone.</span>
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/* ── the collect beat + cube ─────────────────────────────────────────────────── */
const cubeFaces = (f: number): CubeFace[] => {
  const t = f - at(TRU);
  return [
    { draw: drawTruchet(TH, { hole: 215 * (1 - win(f, at(45), 8)) }), t },
    { draw: drawStrings(TH, { k: 3.4 + t * 0.002 }), t },
    { draw: drawMarquee(TH, { words: WORDS }), t: t + 60 },
    { draw: drawRidges(TH, {}), t },
    { draw: drawPalette(TH, { split: 1, labels: 1 }), t },
    { draw: drawHalftone(TH, { diverse: 1 }), t },
  ];
};

const Collect: React.FC<{ f: number }> = ({ f }) => {
  const spin = win(f, at(48.2), at(49.6) - at(48.2));
  const turn = Math.max(0, f - at(49.6)) * 0.45;
  return (
    <CubeStage
      th={TH}
      faces={cubeFaces(f)}
      gridOrder={[3, 4, 1, 5, 0, 2]}
      heroCell={4}
      S={300}
      st={{
        grid: win(f, at(45), at(46) - at(45)),
        net: win(f, at(46.4), at(47.4) - at(46.4)),
        fold: win(f, at(47.6), at(48.6) - at(47.6)),
        rx: -24 * spin,
        ry: 38 * spin + turn,
        lift: 70 * win(f, at(48.4), at(49.6) - at(48.4)),
        scale: mix(1, 1.32, spin),
        rubik: win(f, at(49.8), at(50.3) - at(49.8)),
        twists: [win(f, at(50.5), at(51.3) - at(50.5), (x) => x), win(f, at(51.6), at(52.4) - at(51.6), (x) => x)],
        explode: win(f, at(52.8), at(53.5) - at(52.8), (x) => x),
      }}
    />
  );
};

/* ── 04 VOLUME (three.js) ────────────────────────────────────────────────────── */
const DETAILS = [0, 1, 2, 3, 5, 7];
const detailAt = (f: number) => {
  if (f >= at(57)) return 99;
  const i = Math.floor((f - at(56.1)) / (0.15 * BEAT));
  return DETAILS[Math.max(0, Math.min(DETAILS.length - 1, i))];
};
const volumeState = (f: number) => {
  const v = f - at(53.5);
  const toBlob = win(f, at(55), at(56.2) - at(55));
  return {
    wave: v + 40,
    drop: win(f, at(53.5), at(54.5) - at(53.5), (x) => x),
    sink: win(f, at(55), at(55.6) - at(55)),
    field: 1 - win(f, at(58.4), at(59) - at(58.4)),
    flat: toBlob,
    rise: win(f, at(55.6), at(56.1) - at(55.6), (x) => easeBack(x, 1.2)),
    detail: detailAt(f),
    wire: 1,
    amp: 0.3 * win(f, at(57), at(57.6) - at(57)) * (1 - win(f, at(57.9), at(58.4) - at(57.9))),
    dark: win(f, at(58.4), at(59) - at(58.4)),
    cam: { ang: 0.7 + v * 0.0045, dist: mix(27, 12.55, toBlob), height: mix(18, 1.2, toBlob), target: [0, mix(0, 2.75, toBlob), 0] as [number, number, number] },
  };
};

/* ── 05 FIELD (seconds from the burst) ───────────────────────────────────────── */
const fieldState = (f: number) => {
  const u = sec(f, B.field);
  const seg = (a: number, b: number) => easeInOut(clamp01((u - a) / (b - a)));
  const hold = (u > 2.5 && u < 3.6) || (u > 4.4 && u < 6.4);
  return {
    stage: seg(0.5, 1.6) + seg(1.7, 2.5) + seg(3.6, 4.4) + seg(6.4, 6.8),
    burst: 1.1 * easeOut(clamp01(u / 0.45)) * (1 - seg(0.45, 1.6)),
    noise: hold ? 5 : u < 1.6 ? 46 : 22,
    spin: 1.6 * Math.min(u, 2.5),
    point: seg(6.8, 7.05),
    t: f - at(B.field),
    alpha: clamp01((f - at(B.field) + 1) / 5),
    rotY: 0.18 * Math.sin(u * 0.8) * (1 - seg(1.7, 2.5)),
  };
};

/* ── OUTRO (seconds from its start) ──────────────────────────────────────────── */
const MS = 520 / 1200;
const MX = 960 - 600 * MS;
const MY = 560 - 600 * MS;
const markPt = (p: { x: number; y: number }) => ({ x: MX + p.x * MS, y: MY + p.y * MS });

const Outro: React.FC<{ f: number }> = ({ f }) => {
  const u = sec(f, B.outro);
  const w = (a: number, b: number, e: (x: number) => number = easeInOut) => e(clamp01((u - a) / (b - a)));
  const glide = w(0.1, 0.5);
  const draw = w(0.5, 3.3, (x) => x);
  const s0 = markPt({ x: 267, y: 155 });
  const endP = markPt(penAt(MARK_PATHS, 1));
  const flash = w(3.3, 3.5, easeOut) * (1 - w(3.55, 3.85));
  const irisA = w(3.6, 4.2, easeOut);
  const thick = w(3.7, 4.5);
  const rot = 90 * w(3.7, 4.8);
  const official = w(4.5, 4.8);
  const lock = w(4.8, 5.7);
  const wordA = w(5.1, 5.9);
  const tag = w(5.9, 6.4, easeOut);
  const period = w(6.55, 6.8, (x) => easeBack(x, 2.2));
  const label = w(0.2, 0.6) * (1 - w(3.1, 3.4));
  const size = mix(520, 190, lock);
  const cx = mix(960, 765.2, lock);
  const cy = mix(560, 520, lock);
  const k = size / 520;
  const nib = draw <= 0 ? { x: mix(960, s0.x, glide), y: mix(540, s0.y, glide) } : markPt(penAt(MARK_PATHS, draw));
  const maskSvg = (file: string): React.CSSProperties => ({
    WebkitMaskImage: `url(${staticFile(`brand/${file}`)})`,
    WebkitMaskSize: "100% 100%",
    maskImage: `url(${staticFile(`brand/${file}`)})`,
    maskSize: "100% 100%",
    background: TH.ink,
  });
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      <AbsoluteFill style={{ background: TH.paper, clipPath: `circle(${irisA * 2300}px at ${endP.x}px ${endP.y}px)` }}>
        <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 48%, transparent 45%, ${rgba("#8A7D60", 0.16)} 100%)` }} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 0, right: 0, top: 232, textAlign: "center", fontFamily: TH.mono, fontSize: 15, letterSpacing: "0.34em", color: rgba(TH.cream, 0.7), opacity: label }}>
        A BRAND FILM BY
      </div>
      <div style={{ position: "absolute", inset: 0, transform: `translate(${cx - 960}px, ${cy - 560}px) scale(${k})`, transformOrigin: "960px 560px" }}>
        <div style={{ position: "absolute", inset: 0, transform: `rotate(${rot}deg)`, transformOrigin: "960px 560px", opacity: 1 - official }}>
          <StrokeDraw
            paths={MARK_PATHS}
            p={draw}
            color={irisA > 0.5 ? TH.ink : TH.cream}
            width={mix(7.5, MARK_WIDTH, thick)}
            transform={`translate(${MX} ${MY}) scale(${MS})`}
            nib={0}
            glow={irisA > 0.5 ? 0 : 7}
            lineCap={thick > 0.5 ? "butt" : "round"}
          />
        </div>
        {official > 0 && <div style={{ position: "absolute", left: 700, top: 300, width: 520, height: 520, opacity: official, ...maskSvg("logo-mark.svg") }} />}
      </div>
      {draw > 0 && draw < 1 && <div style={{ position: "absolute", left: nib.x - 7, top: nib.y - 7, width: 14, height: 14, borderRadius: "50%", background: "#fff", boxShadow: `0 0 18px 6px ${rgba(TH.cream, 0.7)}` }} />}
      {draw <= 0 && <div style={{ position: "absolute", left: nib.x - 8, top: nib.y - 8, width: 16, height: 16, borderRadius: "50%", background: "#fff", boxShadow: `0 0 24px 8px ${rgba(TH.cream, 0.6)}` }} />}
      {flash > 0 && (
        <div style={{ position: "absolute", left: endP.x - 90, top: endP.y - 90, width: 180, height: 180, borderRadius: "50%", background: `radial-gradient(circle, #fff 0%, ${rgba(TH.cream, 0.5)} 30%, transparent 70%)`, opacity: flash, transform: `scale(${0.4 + flash})` }} />
      )}
      {wordA > 0 && <div style={{ position: "absolute", left: 900.2, top: 486, width: 349.7, height: 68, clipPath: `inset(0 ${(1 - wordA) * 100}% 0 0)`, transform: `translateX(${(1 - wordA) * -30}px)`, ...maskSvg("logo-wordmark.svg") }} />}
      {tag > 0 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 648, textAlign: "center", fontFamily: TH.serif, fontWeight: 300, fontSize: 42, color: rgba(TH.ink, 0.78), opacity: tag, transform: `translateY(${(1 - tag) * 12}px)` }}>
          From answers to outcomes
          <span style={{ display: "inline-block", width: 11, height: 11, marginLeft: 5, borderRadius: "50%", background: MOSS, transform: `scale(${period})` }} />
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ── sound (soft: the piano carries the film) ─────────────────────────────── */
const o = (b: number, s: number) => at(b) + Math.round(s * FPS);
const CUES: Cue[] = [
  ...TYPE_AT.map((a, i) => ({ at: a, name: `key-${i + 2}`, volume: 0.42 })),
  ...BOUNCE.contacts.map((c, i) => ({ at: BOUNCE.at + c, name: "tap", volume: [0.45, 0.3, 0.18][i] })),
  { at: at(11), name: "swish-1", volume: 0.18 },
  { at: at(22.7), name: "swish-3", volume: 0.14 },
  { at: at(26.3), name: "swish-2", volume: 0.12 },
  ...Array.from({ length: 8 }, (_, i) => ({ at: at(30.3) + Math.round(i * 2.6), name: "tap", volume: 0.08 })),
  ...keyCues(PROMPT, Array.from(PROMPT, (_, i) => typeAt(i)), at(CHAIN_AT), 0.32, 2),
  { at: at(CHAIN_AT) + CH.send, name: "click", volume: 0.3 },
  { at: at(CHAIN_AT) + CH.site, name: "swish-1", volume: 0.16 },
  { at: at(CHAIN_AT) + CH.slide + 16, name: "page-2", volume: 0.22 },
  { at: at(CHAIN_AT) + CH.sheet + 20, name: "tap", volume: 0.12 },
  { at: at(CHAIN_AT) + CH.report + 8, name: "paper-place-2", volume: 0.2 },
  { at: at(CHAIN_AT) + CH.pair, name: "pop", volume: 0.18 },
  { at: at(CHAIN_AT) + CH.team, name: "pop", volume: 0.14 },
  { at: at(TRU), name: "swish-2", volume: 0.18 },
  { at: at(45), name: "swish-1", volume: 0.18 },
  { at: at(46.4), name: "paper-place-1", volume: 0.3 },
  { at: at(47.7), name: "page-1", volume: 0.34 },
  { at: at(51.3), name: "click", volume: 0.26 },
  { at: at(52.4), name: "click", volume: 0.26 },
  { at: at(52.8), name: "whoosh", volume: 0.22 },
  { at: at(53.7), name: "paper-place-2", volume: 0.28 },
  ...DETAILS.slice(1).map((_, i) => ({ at: at(56.1) + Math.round((i + 1) * 0.15 * BEAT), name: "pop", volume: 0.1 })),
  { at: at(B.field), name: "impact", volume: 0.35 },
  { at: o(B.outro, 3.35), name: "ding", volume: 0.14 },
  { at: o(B.outro, 3.6), name: "whoosh", volume: 0.24 },
  { at: o(B.outro, 4.8), name: "impact", volume: 0.2 },
  { at: o(B.outro, 6.55), name: "pop", volume: 0.22 },
];
const musicVolume = (f: number) => interpolate(f, [0, 20, FILM60_FRAMES - 60, FILM60_FRAMES], [0, 0.95, 0.95, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const CAPTIONS = [
  { from: BOUNCE.at + 6, to: at(11), text: "BOUNCE · 3 CONTACTS · SQUASH 0.55" },
  { from: at(11.4), to: at(15.6), text: "48 × 27 DOTS · 7 COLOURS · 4 SHAPES" },
  { from: at(20), to: at(22.6), text: "48 VOICES · ONE SIGNAL" },
  { from: at(22.9), to: at(25.9), text: (f: number) => `I → ${mix(2, 3.4, win(f, at(22.7), at(25) - at(22.7))).toFixed(2)} · I  (MOD 200)` },
  { from: at(30.4), to: at(32.6), text: "BRAND PALETTE · 8 COLOURS" },
  ...(
    [
      [CH.type, CH.site, "PROMPT"],
      [CH.site + 6, CH.slide, "WEBSITES"],
      [CH.slide + 6, CH.sheet, "SLIDES"],
      [CH.sheet + 6, CH.report, "SHEETS"],
      [CH.report + 6, CH.head, "REPORTS"],
      [CH.pair, CH.team, "YOU + YOUR AI EXPERT"],
      [CH.team, CHAIN_LEN, "YOUR AI EXPERT TEAM"],
    ] as [number, number, string][]
  ).map(([a, b, text]) => ({ from: at(CHAIN_AT) + a, to: at(CHAIN_AT) + b, text })),
  { from: at(TRU) + 8, to: at(44.8), text: "16 × 9 TILES · 2 STATES" },
  { from: at(45.6), to: at(48.4), text: "6 PLANES → 1 VOLUME" },
  { from: at(49.9), to: at(52.8), text: "3 × 3 × 3 · 27 CUBELETS" },
  { from: at(53.8), to: at(55.8), text: "24 × 24 VOXELS · ONE WAVE" },
  { from: at(56.1), to: at(58.6), text: (f: number) => (f >= at(57) ? "SUBDIVISION · 20 → 1,280 FACES" : `SUBDIVISION · ${icoFaces(detailAt(f)).toLocaleString("en-US")} FACES`) },
  { from: at(B.field) + 8, to: o(B.field, 3.5), text: "60,000 PARTICLES · ONE SHADER" },
  { from: o(B.field, 3.8), to: o(B.field, 6.4), text: "4 LOOPS · 1 MARK" },
];

export const Film60: React.FC = () => {
  const ready = useBrandFonts();
  const f = useCurrentFrame();
  if (!ready) return <AbsoluteFill style={{ background: TH.ink }} />;
  const vol = volumeState(f);
  const fld = fieldState(f);
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {f < at(B.line) && <Point f={f} />}
      {f >= at(B.line) && f < at(B.plane) + 10 && <LineCh f={f} />}
      {f >= at(29.3) && f < at(45) + 1 && <Plane f={f} />}
      {f >= at(45) && f < at(53.5) + 3 && <Collect f={f} />}
      {f >= at(53.5) && f < at(B.field) + 5 && (
        <AbsoluteFill style={{ opacity: 1 - clamp01((f - at(B.field)) / 5) }}>
          <VolumeScene th={TH} s={vol} clay="#A7BD72" />
          <Line f={f} from={56.6} to={58.9} y={900} color={TH.ink} size={42} halo={TH.paper2}>
            Refined, then reinvented.
          </Line>
        </AbsoluteFill>
      )}
      {f >= at(45) && f < at(53.5) && (
        <Line f={f} from={50} to={52.8} y={900} color={TH.ink} size={42} halo={TH.paper2}>
          Every detail, considered.
        </Line>
      )}
      {f >= at(B.field) && f < at(B.outro) + 2 && (
        <AbsoluteFill>
          <ParticleField th={TH} s={fld} text={{ value: "together.", font: `600 240px ${TH.serif}` }} image={staticFile("brand/logo-mark.svg")} imageSize={600} R={330} />
          {(() => {
            const u = sec(f, B.field);
            const a = clamp01((u - 4.4) / 0.4) * (1 - clamp01((u - 6.1) / 0.3));
            return a > 0 ? (
              <div style={{ position: "absolute", left: 0, right: 0, top: 890, textAlign: "center", fontFamily: TH.serif, fontWeight: 300, fontSize: 40, color: TH.cream, opacity: a }}>
                Made with people, for people.
              </div>
            ) : null;
          })()}
        </AbsoluteFill>
      )}
      {f >= at(B.outro) && <Outro f={f} />}
      <SpecimenHud
        th={TH}
        title="YOUWARE  —  BRAND FILM"
        spec={(k) => `2026  ·  ${1920 * k}×${1080 * k}  ·  30P`}
        total={FILM60_FRAMES}
        fps={FPS}
        light={[[at(29.8), at(58.8)]]}
        hideAt={at(B.outro) - 12}
        chapters={[
          { at: at(B.point), no: "01", name: "POINT", dim: "0D" },
          { at: at(B.line), no: "02", name: "LINE", dim: "1D" },
          { at: at(B.plane), no: "03", name: "PLANE", dim: "2D" },
          { at: at(B.volume), no: "04", name: "VOLUME", dim: "3D" },
          { at: at(B.field), no: "05", name: "FIELD", dim: "∞" },
        ]}
        captions={CAPTIONS}
      />
      <Audio src={staticFile("music/bgm60.wav")} volume={musicVolume} />
      <SoundCues cues={CUES} />
    </AbsoluteFill>
  );
};
