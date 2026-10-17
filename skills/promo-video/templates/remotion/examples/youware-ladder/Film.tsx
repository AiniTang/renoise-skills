import React, { useEffect, useMemo, useState } from "react";
import { AbsoluteFill, Audio, cancelRender, continueRender, delayRender, interpolate, staticFile, useCurrentFrame } from "remotion";
import { SoundCues, type Cue } from "../cinematic/sfx";
import {
  BounceGraph,
  CubeStage,
  drawHalftone,
  drawMarquee,
  drawPalette,
  drawRidges,
  drawStrings,
  drawTruchet,
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

/* ── timing: 128 BPM, every cut on the beat grid ─────────────────────────────── */
const FPS = 30;
const BPM = 128;
const BEAT = (FPS * 60) / BPM; // 14.0625 frames
const at = (b: number) => Math.round(b * BEAT);
const B = { point: 0, line: 12, plane: 24, volume: 40, field: 60, outro: 72, end: 86 };
export const FILM_FRAMES = at(B.end) + 1;

/* ── YouWare brand (colour upgrade from the collaboration film style guide) ───── */
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
      ["DM Sans", "DMSans-400i.woff2", { weight: "400", style: "italic" }],
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

/* ── shared bits ──────────────────────────────────────────────────────────────── */
const Sub: React.FC<{ f: number; from: number; to: number; text: React.ReactNode; y?: number; color?: string; size?: number; halo?: string }> = ({ f, from, to, text, y = 800, color = TH.cream, size = 38, halo }) => {
  const a = win(f, from, 10, easeOut) * (1 - win(f, to - 8, 8));
  if (a <= 0) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: y, textAlign: "center", fontFamily: TH.serif, fontWeight: 300, fontSize: size, letterSpacing: "0.005em", color, opacity: a, textShadow: halo ? `0 0 10px ${halo}, 0 0 24px ${halo}, 0 0 40px ${halo}` : undefined, transform: `translateY(${(1 - a) * 14}px)` }}>
      {text}
    </div>
  );
};

/* ── 01 POINT ─────────────────────────────────────────────────────────────────── */
const WORD = "idea";
const WORD_SIZE = 190;
const BASELINE = 600;
const DOT = 26;
const TYPE_AT = [30, 34, 38, 42];
const BOUNCE_AT = at(4);
const LAND = { x: 700, y: BASELINE };

const useWordWidths = () =>
  useMemo(() => {
    const g = document.createElement("canvas").getContext("2d")!;
    g.font = `400 ${WORD_SIZE}px ${TH.serif}`;
    return Array.from(WORD).map((c) => g.measureText(c).width);
  }, []);

const Point: React.FC<{ f: number }> = ({ f }) => {
  const widths = useWordWidths();
  const typedE = TYPE_AT.map((a) => easeOut(clamp01((f - a) / 5)));
  const W = widths.reduce((s, w, i) => s + w * typedE[i], 0) + DOT + 8;
  const left = 960 - W / 2;
  const dotX0 = left + widths.reduce((s, w, i) => s + w * typedE[i], 0) + 8 + DOT / 2;
  const tb = f - BOUNCE_AT;
  const bounce: BounceSpec = { x0: dotX0, x1: LAND.x, floor: BASELINE, contacts: [18, 33, 44], heights: [270, 140, 60], r: DOT / 2 };

  // caret → dot
  const blinkOn = f < 8 || (f >= 14 && f < 21) || f >= 21;
  const m = easeInOut(clamp01((f - 21) / 7));
  const cw = mix(5, DOT, m);
  const ch = mix(150, DOT, m);
  const cy = mix(BASELINE - 140, BASELINE - DOT, m);

  const htSpawn = (f - at(8)) * 58;
  const collapse = win(f, at(11), at(12) - at(11) - 2);
  const guides = win(f, BOUNCE_AT + 2, 6) * (1 - win(f, at(8), 10));
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {f >= at(8) && <SpecimenCanvas t={f - at(8)} draw={drawHalftone(TH, { ox: LAND.x, oy: LAND.y - DOT / 2, spawn: htSpawn, collapse })} />}
      {f < BOUNCE_AT + 40 &&
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
                fontWeight: 400,
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
      {tb < 0 && blinkOn && (
        <div style={{ position: "absolute", left: dotX0 - cw / 2, top: cy, width: cw, height: ch, borderRadius: m > 0.5 ? "50%" : 3 * m + 1, background: TH.cream }} />
      )}
      {tb >= 0 && f < at(8) + 18 && <BounceGraph th={TH} b={bounce} t={tb} frameOffset={BOUNCE_AT} guides={guides} ballAlpha={1 - clamp01((htSpawn - 60) / 80)} />}
    </AbsoluteFill>
  );
};

/* ── 02 LINE ──────────────────────────────────────────────────────────────────── */
const VS = 1.15;
const VX = 960 - 315 * VS;
const VY = 470 - 221 * VS;
const vibePt = (p: { x: number; y: number }) => ({ x: VX + p.x * VS, y: VY + p.y * VS });

const Line: React.FC<{ f: number }> = ({ f }) => {
  const start = vibePt({ x: 40, y: 262 });
  const glide = win(f, at(12), at(12.6) - at(12));
  const write = win(f, at(12.6), at(15.2) - at(12.6), (x) => x);
  const end = vibePt(penAt([VIBE_PATH], 1));
  const hop = win(f, at(15.2), at(15.7) - at(15.2));
  const tit = vibePt(VIBE_DOT);
  const fadeWord = win(f, at(16), 12);
  let dot = { x: mix(960, start.x, glide), y: mix(540, start.y, glide) - Math.sin(glide * Math.PI) * 60 };
  if (write > 0 && write < 1) dot = vibePt(penAt([VIBE_PATH], write));
  if (write >= 1) dot = { x: mix(end.x, tit.x, hop), y: mix(end.y, tit.y, hop) - Math.sin(hop * Math.PI) * 120 };
  const ridges = f >= at(16) && f < at(21);
  const strings = f >= at(21);
  const chord = win(f, at(20), at(21) - at(20));
  const k = mix(2, 3.4, win(f, at(21), at(23.3) - at(21)));
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {ridges && (
        <SpecimenCanvas
          t={f - at(16)}
          draw={drawRidges(TH, { spread: win(f, at(16), at(17) - at(16)), reveal: win(f, at(16), at(16.8) - at(16)), amp: win(f, at(16.5), at(18) - at(16.5)), chord })}
        />
      )}
      {strings && (
        <SpecimenCanvas
          t={f - at(21)}
          draw={drawStrings(TH, {
            k,
            enter: win(f, at(21), at(22) - at(21)),
            extra: win(f, at(21.5), at(22.5) - at(21.5)),
            squash: win(f, at(23.2), at(24) - at(23.2) - 1),
          })}
        />
      )}
      {f < at(16) + 14 && (
        <div style={{ position: "absolute", inset: 0, opacity: 1 - fadeWord, transform: `translateY(${-24 * fadeWord}px)` }}>
          <StrokeDraw paths={[VIBE_PATH]} p={write} color={TH.cream} width={5.2 / VS} transform={`translate(${VX} ${VY}) scale(${VS})`} nib={1} nibColor={TH.cream} nibR={0} />
          <div style={{ position: "absolute", left: dot.x - DOT / 2, top: dot.y - DOT / 2, width: DOT, height: DOT, borderRadius: "50%", background: TH.cream, boxShadow: write > 0 && write < 1 ? `0 0 26px ${rgba(TH.cream, 0.8)}` : undefined, transform: `scale(${write > 0 && write < 1 ? 0.55 : write >= 1 ? mix(0.55, 0.62, hop) : 1})` }} />
        </div>
      )}
      <Sub f={f} from={at(13.4)} to={at(17.2)} y={780} text={<>Vibe coding — an idea that went for a walk.</>} />
    </AbsoluteFill>
  );
};

/* ── 03 PLANE ─────────────────────────────────────────────────────────────────── */
const Plane: React.FC<{ f: number }> = ({ f }) => {
  const iris = win(f, at(32), 10, easeOut) * 1250;
  const hole = win(f, at(32.8), 10) * 215 * (1 - win(f, at(36), 8));
  const textA = win(f, at(33.1), 10, easeOut) * (1 - win(f, at(35.2), 8));
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {f < at(28) && (
        <SpecimenCanvas
          t={f - at(24)}
          draw={drawPalette(TH, {
            grow: win(f, at(24), at(25.2) - at(24)),
            split: win(f, at(25.2), at(26.6) - at(25.2)),
            labels: win(f, at(25.8), at(27) - at(25.8), (x) => x),
            exit: win(f, at(27.4), at(28) - at(27.4), (x) => x),
          })}
        />
      )}
      {f >= at(28) && f < at(32) + 12 && (
        <SpecimenCanvas t={f - at(28)} draw={drawMarquee(TH, { words: WORDS, enter: win(f, at(28), at(29) - at(28), (x) => x), exit: win(f, at(31.3), at(32) - at(31.3), (x) => x) })} />
      )}
      {f >= at(32) && (
        <AbsoluteFill style={{ clipPath: `circle(${iris}px at 50% 50%)` }}>
          <SpecimenCanvas t={f - at(32)} draw={drawTruchet(TH, { assemble: win(f, at(32), at(33.4) - at(32), (x) => x), hole })} />
          <div style={{ position: "absolute", left: 0, right: 0, top: 470, textAlign: "center", fontFamily: TH.serif, fontWeight: 500, fontSize: 64, lineHeight: 1.12, color: TH.ink, opacity: textA }}>
            <div style={{ transform: `translateY(${(1 - textA) * 16}px)` }}>From vibe coding</div>
            <div style={{ transform: `translateY(${(1 - win(f, at(33.6), 10, easeOut)) * 16}px)`, opacity: win(f, at(33.6), 10) }}>
              to work, for <span style={{ color: MOSS }}>everyone.</span>
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/* ── the collect beat + cube (end of PLANE, start of VOLUME) ─────────────────── */
const cubeFaces = (f: number): CubeFace[] => {
  const t = f - at(32);
  return [
    { draw: drawTruchet(TH, { hole: 215 * (1 - win(f, at(36), 8)) }), t },
    { draw: drawStrings(TH, { k: 3.4 + t * 0.002 }), t },
    { draw: drawMarquee(TH, { words: WORDS }), t: t + 60 },
    { draw: drawRidges(TH, {}), t },
    { draw: drawPalette(TH, { split: 1, labels: 1 }), t },
    { draw: drawHalftone(TH, {}), t },
  ];
};

const Collect: React.FC<{ f: number }> = ({ f }) => {
  const spin = win(f, at(40.6), at(42.6) - at(40.6));
  const turn = Math.max(0, f - at(42.6)) * 0.55;
  return (
    <CubeStage
      th={TH}
      faces={cubeFaces(f)}
      gridOrder={[3, 4, 1, 5, 0, 2]}
      heroCell={4}
      S={300}
      st={{
        grid: win(f, at(36), at(37.3) - at(36)),
        net: win(f, at(38), at(39.6) - at(38)),
        fold: win(f, at(40), at(41.4) - at(40)),
        rx: -24 * spin,
        ry: 38 * spin + turn,
        lift: 70 * win(f, at(41), at(42.6) - at(41)),
        scale: mix(1, 1.32, spin),
        rubik: win(f, at(44), at(44.7) - at(44)),
        twists: [win(f, at(45), at(46) - at(45), (x) => x), win(f, at(46.4), at(47.4) - at(46.4), (x) => x)],
        explode: win(f, at(48), at(49) - at(48), (x) => x),
      }}
    />
  );
};

/* ── 04 VOLUME (three.js) ─────────────────────────────────────────────────────── */
const DETAILS = [0, 1, 2, 3, 5, 7];
const detailAt = (f: number) => {
  const i = Math.floor((f - at(54.6)) / (0.35 * BEAT));
  if (f >= at(56.7)) return 99;
  return DETAILS[Math.max(0, Math.min(DETAILS.length - 1, i))];
};
const volumeState = (f: number) => {
  const v = f - at(49);
  const toBlob = win(f, at(53.6), at(55.2) - at(53.6));
  const amp = 0.3 * win(f, at(56.7), at(57.6) - at(56.7)) * (1 - win(f, at(58.4), at(59.2) - at(58.4)));
  return {
    wave: v + 40,
    drop: win(f, at(49), at(50.6) - at(49), (x) => x),
    sink: win(f, at(53.4), at(54.2) - at(53.4)),
    field: 1 - win(f, at(59), at(59.8) - at(59)),
    flat: toBlob,
    rise: win(f, at(54), at(54.8) - at(54), (x) => easeBack(x, 1.2)),
    detail: detailAt(f),
    wire: 1,
    amp,
    dark: win(f, at(59), at(59.9) - at(59)),
    cam: { ang: 0.7 + v * 0.0045, dist: mix(27, 12.55, toBlob), height: mix(18, 1.2, toBlob), target: [0, mix(0, 2.75, toBlob), 0] as [number, number, number] },
  };
};

/* ── 05 FIELD ─────────────────────────────────────────────────────────────────── */
const fieldState = (f: number) => {
  const u = (f - at(60)) / BEAT;
  const seg = (a: number, b: number) => easeInOut(clamp01((u - a) / (b - a)));
  const stage = seg(0.6, 2.6) + seg(3.2, 4.4) + seg(6, 7.3) + seg(9.8, 10.8);
  const hold = (u > 4.4 && u < 6) || (u > 7.3 && u < 9.8);
  return {
    stage,
    burst: 1.1 * easeOut(clamp01(u / 0.7)) * (1 - seg(0.7, 2.6)),
    noise: hold ? 5 : u < 2.6 ? 46 : 22,
    spin: 0.95 * Math.min(u, 4.4),
    point: seg(11, 11.9),
    t: f - at(60),
    alpha: clamp01((f - at(60) + 1) / 5),
    rotY: 0.18 * Math.sin(u * 0.4) * (1 - seg(3.2, 4.4)),
  };
};

/* ── OUTRO: the dot signs the mark, then the lockup ──────────────────────────── */
const MS = 520 / 1200;
const MX = 960 - 600 * MS;
const MY = 560 - 600 * MS;
const markPt = (p: { x: number; y: number }) => ({ x: MX + p.x * MS, y: MY + p.y * MS });

const Outro: React.FC<{ f: number }> = ({ f }) => {
  const glide = win(f, at(72.15), at(72.7) - at(72.15));
  const draw = win(f, at(72.7), at(77.4) - at(72.7), (x) => x);
  const s0 = markPt({ x: 267, y: 155 });
  const endP = markPt(penAt(MARK_PATHS, 1));
  const flash = win(f, at(77.4), 6, easeOut) * (1 - win(f, at(78), 8));
  const irisA = win(f, at(78), at(78.8) - at(78), easeOut);
  const thick = win(f, at(78.2), at(79.2) - at(78.2));
  const rot = 90 * win(f, at(78.2), at(79.6) - at(78.2));
  const official = win(f, at(79.3), 8);
  const lock = win(f, at(79.6), at(80.9) - at(79.6));
  const wordA = win(f, at(80), at(81.1) - at(80));
  const tag = win(f, at(81.2), 14, easeOut);
  const period = win(f, at(82.4), 8, (x) => easeBack(x, 2.2));
  const label = win(f, at(72.3), 12) * (1 - win(f, at(77.6), 8));

  const size = mix(520, 190, lock);
  const cx = mix(960, 765.2, lock);
  const cy = mix(560, 520, lock);
  const k = size / 520;
  const nib = draw <= 0 ? { x: mix(960, s0.x, glide), y: mix(540, s0.y, glide) } : markPt(penAt(MARK_PATHS, draw));
  const strokeCol = irisA > 0.5 ? TH.ink : TH.cream;
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
            color={strokeCol}
            width={mix(7.5, MARK_WIDTH, thick)}
            transform={`translate(${MX} ${MY}) scale(${MS})`}
            nib={0}
            glow={irisA > 0.5 ? 0 : 7}
            lineCap={thick > 0.5 ? "butt" : "round"}
          />
        </div>
        {official > 0 && <div style={{ position: "absolute", left: 960 - 260, top: 560 - 260, width: 520, height: 520, opacity: official, ...maskSvg("logo-mark.svg") }} />}
      </div>
      {draw > 0 && draw < 1 && <div style={{ position: "absolute", left: nib.x - 7, top: nib.y - 7, width: 14, height: 14, borderRadius: "50%", background: "#fff", boxShadow: `0 0 18px 6px ${rgba(TH.cream, 0.7)}` }} />}
      {draw <= 0 && f >= at(72) && (
        <div style={{ position: "absolute", left: nib.x - 8, top: nib.y - 8, width: 16, height: 16, borderRadius: "50%", background: "#fff", boxShadow: `0 0 24px 8px ${rgba(TH.cream, 0.6)}` }} />
      )}
      {flash > 0 && <div style={{ position: "absolute", left: endP.x - 90, top: endP.y - 90, width: 180, height: 180, borderRadius: "50%", background: `radial-gradient(circle, #fff 0%, ${rgba(TH.cream, 0.5)} 30%, transparent 70%)`, opacity: flash, transform: `scale(${0.4 + flash})` }} />}
      {wordA > 0 && (
        <div style={{ position: "absolute", left: 900.2, top: 520 - 34, width: 349.7, height: 68, clipPath: `inset(0 ${(1 - wordA) * 100}% 0 0)`, transform: `translateX(${(1 - wordA) * -30}px)`, ...maskSvg("logo-wordmark.svg") }} />
      )}
      {tag > 0 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 648, textAlign: "center", fontFamily: TH.serif, fontWeight: 300, fontSize: 42, color: rgba(TH.ink, 0.78), opacity: tag, transform: `translateY(${(1 - tag) * 12}px)` }}>
          From answers to outcomes
          <span style={{ display: "inline-block", width: 11, height: 11, marginLeft: 5, borderRadius: "50%", background: MOSS, transform: `scale(${period})` }} />
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ── sound ───────────────────────────────────────────────────────────────────── */
const CUES: Cue[] = [
  ...TYPE_AT.map((a, i) => ({ at: a, name: `key-${i + 2}`, volume: 0.5 })),
  ...[18, 33, 44].map((c, i) => ({ at: BOUNCE_AT + c, name: "tap", volume: [0.55, 0.38, 0.24][i] })),
  { at: at(8), name: "swish-1", volume: 0.3 },
  { at: at(11.2), name: "swish-3", volume: 0.25 },
  { at: at(12.6), name: "swish-2", volume: 0.18 },
  { at: at(21), name: "swish-1", volume: 0.25 },
  { at: at(23.4), name: "whoosh", volume: 0.3 },
  { at: at(24), name: "impact", volume: 0.55 },
  ...Array.from({ length: 8 }, (_, i) => ({ at: at(25.2) + Math.round(i * 0.1 * (at(26.6) - at(25.2)) * 1.0), name: "tap", volume: 0.14 })),
  { at: at(28), name: "whoosh", volume: 0.42 },
  { at: at(31.4), name: "swish-3", volume: 0.3 },
  { at: at(32), name: "swish-2", volume: 0.3 },
  { at: at(36), name: "swish-1", volume: 0.3 },
  { at: at(38), name: "paper-place-1", volume: 0.45 },
  { at: at(40), name: "impact", volume: 0.45 },
  { at: at(40.3), name: "page-1", volume: 0.5 },
  { at: at(44), name: "click", volume: 0.35 },
  { at: at(46), name: "click", volume: 0.45 },
  { at: at(47.4), name: "click", volume: 0.45 },
  { at: at(48), name: "whoosh", volume: 0.4 },
  { at: at(49.3), name: "impact", volume: 0.5 },
  { at: at(54.1), name: "swish-1", volume: 0.3 },
  ...DETAILS.slice(1).map((_, i) => ({ at: at(54.6) + Math.round((i + 1) * 0.35 * BEAT), name: "pop", volume: 0.16 })),
  { at: at(60) - 36, name: "riser", volume: 0.4 },
  { at: at(60), name: "impact", volume: 0.8 },
  { at: at(63.2), name: "swish-2", volume: 0.3 },
  { at: at(66), name: "swish-3", volume: 0.3 },
  { at: at(72.7), name: "swish-2", volume: 0.16 },
  { at: at(77.5), name: "ding", volume: 0.22 },
  { at: at(78), name: "whoosh", volume: 0.4 },
  { at: at(79.6), name: "impact", volume: 0.4 },
  { at: at(82.4), name: "pop", volume: 0.3 },
];

const musicVolume = (f: number) =>
  interpolate(f, [0, 12, at(23), at(24), at(24) + 4, at(39), at(40), at(40) + 4, FILM_FRAMES - 40, FILM_FRAMES], [0, 0.8, 0.8, 0.5, 0.8, 0.8, 0.52, 0.8, 0.8, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/* ── captions (all real numbers of what is on screen) ─────────────────────────── */
const CAPTIONS = [
  { from: BOUNCE_AT + 6, to: at(8), text: "BOUNCE · 3 CONTACTS · SQUASH 0.55" },
  { from: at(8) + 4, to: at(11.5), text: "48 × 27 DOTS · ONE WAVE" },
  { from: at(16) + 8, to: at(20.6), text: "48 LINES · ONE SIGNAL" },
  { from: at(21) + 4, to: at(24), text: (f: number) => `I → ${mix(2, 3.4, win(f, at(21), at(23.3) - at(21))).toFixed(2)} · I  (MOD 200)` },
  { from: at(25.4), to: at(28), text: "BRAND PALETTE · 8 COLOURS" },
  { from: at(32) + 8, to: at(36), text: "16 × 9 TILES · 2 STATES" },
  { from: at(37.4), to: at(40.5), text: "6 PLANES → 1 VOLUME" },
  { from: at(44) + 4, to: at(48.2), text: "3 × 3 × 3 · 27 CUBELETS" },
  { from: at(49.6), to: at(54), text: "24 × 24 VOXELS · ONE WAVE" },
  { from: at(54.6), to: at(59.4), text: (f: number) => (f >= at(56.7) ? "SUBDIVISION · 20 → 1,280 FACES" : `SUBDIVISION · ${icoFaces(detailAt(f)).toLocaleString("en-US")} FACES`) },
  { from: at(60) + 8, to: at(66), text: "60,000 PARTICLES · ONE SHADER" },
  { from: at(67.4), to: at(71.6), text: "4 LOOPS · 1 MARK" },
];

export const Film: React.FC = () => {
  const ready = useBrandFonts();
  const f = useCurrentFrame();
  const vol = volumeState(f);
  const fld = fieldState(f);
  const light: [number, number][] = [[at(24.6), at(59.4)]];
  if (!ready) return <AbsoluteFill style={{ background: TH.ink }} />;
  return (
    <AbsoluteFill style={{ background: TH.ink }}>
      {f < at(12) && <Point f={f} />}
      {f >= at(12) && f < at(24) && <Line f={f} />}
      {f >= at(24) && f < at(36) + 1 && <Plane f={f} />}
      {f >= at(36) && f < at(49) + 3 && <Collect f={f} />}
      {f >= at(49) && f < at(60) + 5 && (
        <AbsoluteFill style={{ opacity: 1 - clamp01((f - at(60)) / 5) }}>
          <VolumeScene th={TH} s={vol} clay="#A7BD72" />
          <Sub f={f} from={at(50.2)} to={at(53.4)} y={900} color={TH.ink} size={42} halo={TH.paper2} text="Every detail, considered." />
          <Sub f={f} from={at(56.8)} to={at(59.5)} y={900} color={TH.ink} size={42} halo={TH.paper2} text="Refined, then reinvented." />
        </AbsoluteFill>
      )}
      {f >= at(60) && f < at(72) + 2 && (
        <AbsoluteFill>
          <ParticleField th={TH} s={fld} text={{ value: "together.", font: `600 240px ${TH.serif}` }} image={staticFile("brand/logo-mark.svg")} imageSize={600} R={330} />
          <Sub f={f} from={at(67.6)} to={at(69.9)} y={880} text="Your AI expert team." />
        </AbsoluteFill>
      )}
      {f >= at(72) && <Outro f={f} />}
      <SpecimenHud
        th={TH}
        title="YOUWARE  —  BRAND FILM"
        spec={(k) => `2026  ·  ${1920 * k}×${1080 * k}  ·  30P`}
        total={FILM_FRAMES}
        fps={FPS}
        light={light}
        hideAt={at(71.4)}
        chapters={[
          { at: at(B.point), no: "01", name: "POINT", dim: "0D" },
          { at: at(B.line), no: "02", name: "LINE", dim: "1D" },
          { at: at(B.plane), no: "03", name: "PLANE", dim: "2D" },
          { at: at(B.volume), no: "04", name: "VOLUME", dim: "3D" },
          { at: at(B.field), no: "05", name: "FIELD", dim: "∞" },
        ]}
        captions={CAPTIONS}
      />
      <Audio src={staticFile("music/bgm.wav")} volume={musicVolume} />
      <SoundCues cues={CUES} />
    </AbsoluteFill>
  );
};
