import React from "react";
import { Check, CornerDownLeft, Music2, Sparkles } from "lucide-react";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { AbsoluteFill, Audio, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { E, clamp01, mix } from "../cinematic/motion";
import { SoundCues, keyCues, type Cue } from "../cinematic/sfx";
import { FONT, useGeist } from "./geist";
import { CAM, CURSOR, LEAD, PRESS, TRAIL, UI, dragged, step, track, trackCfg, trackColor, type SpringCfg } from "./spring";
import WAVE from "./wave.json";

const FPS = 60;
const BPM = 124;
const B = 60 / BPM;
export const PROMO_FRAMES = Math.round(40 * B * FPS);
const K = (n: number, o = 0) => (n - 1) * B + o;

const CANVAS = "#ECEAE6";
const INK = "#111111";
const INK2 = "#2E2E2E";
const WHITE = "#FFFFFF";
const GRAY = "#8A8680";
const LINE = "#E6E3DE";
const ACC = "#FF5A1F";
const OFF = "#D6D2CC";

/** Shape centre on screen; the headline column owns x < 700. */
const CX = 1300;
const CY = 540;

/* ── the one shape: [time, w, h, r] and colour ── */

const SHAPE: [number, number, number, number][] = [
  [0, 520, 140, 70],
  [K(4), 1000, 150, 75],
  [K(8), 150, 150, 75],
  [K(12), 820, 160, 80],
  [K(13), 960, 160, 80],
  [K(17), 1000, 300, 48],
  [K(21), 1000, 220, 110],
  [K(25), 260, 820, 130],
  [K(29), 340, 180, 90],
  [K(33), 1060, 560, 40],
  [K(36), 900, 150, 75],
  [K(37), 860, 160, 80],
  [K(39), 520, 140, 70],
];
const BG: [number, string][] = [[0, INK], [K(2), INK2], [K(3), INK], [K(4), WHITE], [K(8), INK], [K(11), ACC], [K(12), INK], [K(13), WHITE], [K(29), OFF], [K(31), ACC], [K(33), WHITE], [K(36), INK]];
const fill = (w: number, h: number) => Math.min(1040 / w, 860 / h, 2.3);
/** Widest the shape may get on screen without crossing the headline column or the right edge. */
const MAX_W = 1100;
/** The last change rides the faster UI spring so the camera has fully settled when the loop wraps. */
const CAMK: [number, number, SpringCfg?][] = SHAPE.map(([t, w, h], i) => [t, fill(w, h), i === SHAPE.length - 1 ? UI : CAM]);
const PRESSK: [number, number][] = [[0, 1], [K(3), 0.94], [K(3, 0.1), 1], [K(7), 0.97], [K(7, 0.1), 1], [K(31), 0.96], [K(31, 0.1), 1]];
/** Push-in while the cursor works: camera leans toward the pointer and tightens 10%. */
const PUSH: [number, number][] = [[0, 0], [K(3, -0.25), 1], [K(4), 0], [K(21), 1], [K(24, 0.1), 0], [K(26), 1], [K(28, 0.1), 0], [K(30, 0.2), 1], [K(31, 0.25), 0], [K(35, -0.3), 1], [K(36), 0]];

/* ── cursor (world, shape centre = origin) ── */

const P0: [number, number] = [330, 190];
const WAVE_X = (i: number) => -480 + (i + 0.5) * (960 / WAVE.length);
const WAVE_Y = 40;
const WAVE_H = 170;
const MARKERS = [
  { i: 8, n: "click" },
  { i: 20, n: "tap" },
  { i: 34, n: "pop" },
  { i: 48, n: "done" },
  { i: 61, n: "ding" },
];
const markerTop = (m: (typeof MARKERS)[number]) => WAVE_Y - WAVE[m.i] * WAVE_H;

const CUR: [number, number, number][] = [
  [0, ...P0],
  [K(1, 0.05), 90, 20],
  [K(4, 0.1), 320, 170],
  [K(6), 380, 200],
  [K(9), 200, 170],
  [K(13), -200, 150],
  [K(14, -0.3), 0, 6],
  [K(15, -0.3), 320, 6],
  [K(16, -0.3), 0, 6],
  [K(16, 0.25), 200, 170],
  [K(17, 0.15), 400, -20],
  [K(18, 0.3), 300, 150],
  [K(20, 0.25), -350, 26],
  [K(22), -60, 30],
  [K(23), 300, 26],
  [K(23, 0.3), 560, 26],
  [K(24, 0.2), 0, 169],
  [K(27), 0, -120],
  [K(27, 0.3), 0, -440],
  [K(28, 0.15), 170, -260],
  [K(29, 0.3), -80, 8],
  [K(31, 0.3), 130, 140],
  [K(34, 0.2), 300, 330],
  [K(35, -0.2), WAVE_X(MARKERS[1].i), markerTop(MARKERS[1]) + 6],
  [K(36), 420, 300],
  [K(36, 0.25), 400, 170],
  [K(39, 0.1), ...P0],
];
const PRESSES: [number, number][] = [[K(3), K(3, 0.1)], [K(14), K(14, 0.08)], [K(15), K(15, 0.08)], [K(16), K(16, 0.08)], [K(18), K(18, 0.1)], [K(21, 0.25), K(24)], [K(26), K(28)], [K(31), K(31, 0.1)]];
const cursorAt = (t: number): [number, number] => [track(t, CUR.map(([tt, x]) => [tt, x] as [number, number]), CURSOR), track(t, CUR.map(([tt, , y]) => [tt, y] as [number, number]), CURSOR)];

/* ── drags ── */

const SCRUB_HOLD: [number, number] = [K(21, 0.25), K(24)];
const playerP = (t: number) => 0.02 + Math.max(0, t - K(18)) * 0.05;
const scrubAt = (t: number) => dragged(t, SCRUB_HOLD, (tt) => clamp01((cursorAt(tt)[0] + 440) / 880), playerP(K(21)), 1);
const SLIDE_HOLD: [number, number] = [K(26), K(28)];
const rubber = (px: number) => 260 * (1 - Math.exp(-Math.max(0, px) / 260));

/** Beat ticks crossed while scrubbing, found by sampling the pointer-driven value. */
const tickCrossings = (() => {
  const out: number[] = [];
  let last = Math.floor(scrubAt(SCRUB_HOLD[0]) * 16 - 0.5);
  for (let tt = SCRUB_HOLD[0]; tt <= SCRUB_HOLD[1]; tt += 1 / 240) {
    const k = Math.floor(scrubAt(tt) * 16 - 0.5);
    if (k > last) out.push(tt);
    last = Math.max(last, k);
  }
  return out;
})();

/* ── copy ── */

type Head = { tin: number; cap: string; l1: string; l2: string };
const HEADS: Head[] = [
  { tin: -1, cap: "PROMO-VIDEO SKILL", l1: "一句话，", l2: "做一条{宣传片}。" },
  { tin: K(4), cap: "01  需求", l1: "你只管", l2: "{说需求}。" },
  { tin: K(8), cap: "02  分析", l1: "它判断", l2: "{行业}和{风格}。" },
  { tin: K(13), cap: "03  风格", l1: "三种档位，", l2: "{随你挑}。" },
  { tin: K(17), cap: "04  选曲", l1: "开源曲库，", l2: "{自动选曲}。" },
  { tin: K(21), cap: "05  对拍", l1: "每个动作，", l2: "{卡在拍上}。" },
  { tin: K(25), cap: "06  动效", l1: "弹簧驱动，", l2: "不是{缓动}。" },
  { tin: K(29), cap: "07  质感", l1: "运动模糊，", l2: "{电影}质感。" },
  { tin: K(33), cap: "08  音效", l1: "音效对齐", l2: "{波形峰值}。" },
  { tin: K(37), cap: "09  出片", l1: "promo-video", l2: "{一句话出片}。" },
  { tin: K(39), cap: "PROMO-VIDEO SKILL", l1: "一句话，", l2: "做一条{宣传片}。" },
];

const PROMPT = "给我的 App 做 20 秒宣传片";
const PROMPT_T0 = K(5, 0.05);
const PROMPT_CPS = 14;
const TABS = ["克制", "表现", "精密 UI"];

/* ── helpers ── */

const swap = (t: number, tin: number, tout: number, rise = 0) => {
  const i = E.out(clamp01((t - tin) / 0.2));
  const o = clamp01((t - tout) / 0.1);
  return { opacity: i * (1 - o), filter: `blur(${(1 - i) * 10 + o * 8}px)`, transform: `translateY(${(1 - i) * rise - o * rise * 0.4}px) scale(${mix(0.96, 1, i) * mix(1, 0.98, o)})` };
};
const visible = (t: number, tin: number, tout: number) => t >= tin - 0.02 && t <= tout + 0.12;

const At: React.FC<{ x: number; y: number; children: React.ReactNode; style?: React.CSSProperties; anchor?: "center" | "left" | "right" }> = ({ x, y, children, style, anchor = "center" }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: anchor === "center" ? "translate(-50%, -50%)" : anchor === "left" ? "translate(0, -50%)" : "translate(-100%, -50%)", whiteSpace: "nowrap" }}>
    <div style={style}>{children}</div>
  </div>
);

const Layer: React.FC<{ t: number; tin: number; tout: number; children: React.ReactNode }> = ({ t, tin, tout, children }) =>
  visible(t, tin, tout) ? <div style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, ...swap(t, tin, tout) }}>{children}</div> : null;

const txt = (size: number, weight: number, color: string): React.CSSProperties => ({ fontFamily: FONT, fontSize: size, fontWeight: weight, color, letterSpacing: "-0.01em", lineHeight: 1.2 });

const Accented: React.FC<{ s: string }> = ({ s }) => (
  <>
    {s.split(/(\{[^}]+\})/).map((p, i) => (p.startsWith("{") ? <span key={i} style={{ color: ACC }}>{p.slice(1, -1)}</span> : <span key={i}>{p}</span>))}
  </>
);

const lerpPts = (a: number[][], b: number[][], m: number) => a.map(([x, y], i) => `${mix(x, b[i][0], m)},${mix(y, b[i][1], m)}`).join(" ");
const PLAY = [[[11, 6], [23, 13], [23, 27], [11, 34]], [[23, 13], [35, 20], [35, 20], [23, 27]]];
const PAUSE = [[[9, 7], [17, 7], [17, 33], [9, 33]], [[23, 7], [31, 7], [31, 33], [23, 33]]];

/* ── scene ── */

export const SkillPromo: React.FC = () => {
  useGeist();
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = f / FPS;
  const [cx, cy] = cursorAt(t);

  const scrub = scrubAt(t);
  const vol = dragged(t, SLIDE_HOLD, (tt) => clamp01((340 - cursorAt(tt)[1]) / 570), 0.3, 1);
  const over = dragged(t, SLIDE_HOLD, (tt) => rubber(-220 - cursorAt(tt)[1]), 0, 0);

  const w = trackCfg(t, SHAPE.map(([tt, ww]) => [tt, ww]));
  const h = trackCfg(t, SHAPE.map(([tt, , hh]) => [tt, hh])) + over * 0.6;
  const r = trackCfg(t, SHAPE.map(([tt, , , rr]) => [tt, rr]));
  const bg = trackColor(t, BG);
  const push = track(t, PUSH, CAM);
  const cam = Math.min(trackCfg(t, CAMK) * (1 + 0.1 * push), MAX_W / w);
  const press = track(t, PRESSK, PRESS);
  const lift = -over * 0.3;
  const whip = 120 * (step(t - K(32), PRESS) - step(t - K(32, 0.13), UI));
  const fx = cx * 0.15 * push + whip / track(t, CAMK.map(([tt, v]) => [tt, v] as [number, number]), CAM);
  const fy = cy * 0.15 * push;

  const indL = trackCfg(t, [[0, -352], [K(13), -470, LEAD], [K(14), -150, TRAIL], [K(15), 170, TRAIL], [K(16), -150, LEAD]]);
  const indR = trackCfg(t, [[0, -328], [K(13), -170, TRAIL], [K(14), 150, LEAD], [K(15), 470, LEAD], [K(16), 150, TRAIL]]);
  const indH = track(t, [[0, 24], [K(13), 120]]);
  const tabActive = t < K(14) ? 0 : t < K(15) ? 1 : t < K(16) ? 2 : 1;
  const knobL = trackCfg(t, [[0, -154], [K(31), 6, TRAIL]]);
  const knobR = trackCfg(t, [[0, -6], [K(31), 154, LEAD]]);
  const playM = step(t - K(18), UI);

  const sx = CX + (cx - fx) * cam;
  const sy = CY + (cy - fy) * cam;
  const isDown = PRESSES.some(([a, b]) => t >= a && t <= b);
  const hoverTip = t >= K(35, -0.05) && t < K(36);

  return (
    <AbsoluteFill style={{ background: CANVAS }}>
      <CameraMotionBlur shutterAngle={180} samples={4}>
        <AbsoluteFill style={{ background: CANVAS }}>
          {/* headline column */}
          {HEADS.map((hd, i) => {
            const tout = HEADS[i + 1]?.tin ?? 99;
            if (!visible(t, hd.tin, tout)) return null;
            return (
              <div key={i} style={{ position: "absolute", left: 120, top: 360 }}>
                <div style={{ ...txt(24, 600, GRAY), letterSpacing: "0.14em", ...swap(t, hd.tin, tout, 20) }}>{hd.cap}</div>
                <div style={{ ...txt(92, 700, INK), marginTop: 26, letterSpacing: "-0.03em", ...swap(t, hd.tin, tout, 40) }}>{hd.l1}</div>
                <div style={{ ...txt(92, 700, INK), marginTop: 8, letterSpacing: "-0.03em", ...swap(t, hd.tin < 0 ? hd.tin : hd.tin + B / 2, tout, 40) }}>
                  <Accented s={hd.l2} />
                </div>
              </div>
            );
          })}

          <div style={{ position: "absolute", left: CX, top: CY, transform: `scale(${cam}) translate(${-fx}px, ${-fy}px)` }}>
            {/* captions outside the clipped shape */}
            <Layer t={t} tin={K(8, 0.1)} tout={K(11)}>
              <At x={0} y={130} style={txt(28, 500, GRAY)}>分析素材 · 判断行业</At>
            </Layer>
            <Layer t={t} tin={K(29, 0.1)} tout={K(33)}>
              <At x={0} y={-160}>
                <span style={txt(36, 600, INK)}>运动模糊 </span>
                <span style={txt(36, 600, t >= K(31) ? ACC : GRAY)}>{t >= K(31) ? "ON" : "OFF"}</span>
              </At>
            </Layer>

            <div style={{ position: "absolute", left: -w / 2, top: -h / 2 + lift, width: w, height: h, borderRadius: r, background: bg, overflow: "hidden", transform: `scale(${press})`, boxShadow: "0 24px 60px rgba(17,17,17,0.12), 0 2px 6px rgba(17,17,17,0.08)" }}>
              <div style={{ position: "absolute", left: w / 2, top: h / 2 - lift }}>
                {/* button */}
                <Layer t={t} tin={-1} tout={K(4)}>
                  <At x={0} y={0} style={{ ...txt(48, 600, WHITE), display: "flex", alignItems: "center", gap: 14 }}>
                    做宣传片 <span style={{ display: "inline-block", transform: `translateX(${8 * (step(t - K(2), UI) - step(t - K(3), UI))}px)` }}>→</span>
                  </At>
                </Layer>
                {/* prompt input */}
                <Layer t={t} tin={K(4, 0.1)} tout={K(8)}>
                  <Sparkles size={40} strokeWidth={1.75} color={ACC} style={{ position: "absolute", left: -450, top: -20 }} />
                  <At x={-388} y={0} anchor="left" style={txt(42, 500, INK)}>
                    {Array.from(PROMPT).slice(0, Math.max(0, Math.floor((t - PROMPT_T0) * PROMPT_CPS))).join("")}
                    <span style={{ display: "inline-block", width: 3, height: 44, marginLeft: 4, verticalAlign: "-8px", background: ACC, opacity: Math.floor(t * 3) % 2 === 0 ? 1 : 0 }} />
                  </At>
                  <At x={450} y={0} anchor="right" style={{ padding: "10px 14px", borderRadius: 14, background: t >= K(7) ? ACC : "#F1EFEB", display: "flex", transform: `scale(${1 - 0.08 * (step(t - K(7), PRESS) - step(t - K(7, 0.1), UI))})` }}>
                    <CornerDownLeft size={32} strokeWidth={2} color={t >= K(7) ? WHITE : INK} />
                  </At>
                </Layer>
                {/* loader */}
                <Layer t={t} tin={K(8, 0.05)} tout={K(11)}>
                  <svg width={150} height={150} style={{ position: "absolute", left: -75, top: -75, transform: `rotate(${t * 540}deg)` }}>
                    <circle cx={75} cy={75} r={40} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={10} />
                    <circle cx={75} cy={75} r={40} fill="none" stroke={WHITE} strokeWidth={10} strokeLinecap="round" strokeDasharray={`${2 * Math.PI * 40 * mix(0.2, 1, step(t - K(9), UI) * 0.4 + step(t - K(10), UI) * 0.6)} 400`} />
                  </svg>
                </Layer>
                {/* check */}
                <Layer t={t} tin={K(11)} tout={K(12)}>
                  <svg width={90} height={90} style={{ position: "absolute", left: -45, top: -45 }}>
                    <path d="M20 46 L38 64 L72 28" fill="none" stroke={WHITE} strokeWidth={11} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={80} strokeDashoffset={80 * (1 - E.out(clamp01((t - K(11)) / 0.25)))} />
                  </svg>
                </Layer>
                {/* dynamic island */}
                <Layer t={t} tin={K(12, 0.06)} tout={K(13)}>
                  <At x={-300} y={0} anchor="left" style={txt(40, 600, WHITE)}>表现档</At>
                  <At x={360} y={0} anchor="right" style={{ ...txt(30, 500, "rgba(255,255,255,0.6)"), display: "flex", gap: 28 }}>
                    <span>20s</span>
                    <span>16:9</span>
                    <span>124 BPM</span>
                  </At>
                </Layer>
                {/* liquid indicator: starts as the island's dot */}
                {t >= K(12, 0.06) && t <= K(17, 0.12) && (
                  <div style={{ position: "absolute", left: indL, top: -indH / 2, width: Math.max(0, indR - indL), height: indH, borderRadius: indH / 2, background: ACC, ...swap(t, K(12, 0.06), K(17)) }} />
                )}
                <Layer t={t} tin={K(13, 0.1)} tout={K(17)}>
                  {TABS.map((tab, i) => (
                    <At key={tab} x={-320 + i * 320} y={0} style={txt(38, 600, i === tabActive ? WHITE : INK)}>{tab}</At>
                  ))}
                </Layer>
                {/* music player */}
                <Layer t={t} tin={K(17, 0.08)} tout={K(21)}>
                  <div style={{ position: "absolute", left: -460, top: -110, width: 170, height: 170, borderRadius: 28, background: INK, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Music2 size={64} strokeWidth={1.75} color={ACC} />
                  </div>
                  <div style={{ position: "absolute", left: -250, top: -104, whiteSpace: "nowrap" }}>
                    <div style={txt(42, 600, INK)}>Techno Fest Vibes</div>
                    <div style={{ ...txt(26, 400, GRAY), marginTop: 6 }}>Mixkit · 124 BPM · 可商用</div>
                  </div>
                  <div style={{ position: "absolute", left: 345, top: -80, width: 110, height: 110, borderRadius: 55, background: INK, transform: `scale(${1 - 0.08 * (step(t - K(18), PRESS) - step(t - K(18, 0.1), UI))})` }}>
                    <svg width={110} height={110} viewBox="-15 -15 70 70">
                      {PLAY.map((pts, i) => <polygon key={i} points={lerpPts(pts, PAUSE[i], clamp01(playM))} fill={WHITE} />)}
                    </svg>
                  </div>
                  {Array.from({ length: 16 }, (_, i) => {
                    const d = step(t - K(20, i * 0.02), UI);
                    return <div key={i} style={{ position: "absolute", left: -250 + (i + 0.5) * (710 / 16) - 1.5, top: mix(40, 70, d), width: 3, height: 14, borderRadius: 2, background: GRAY, opacity: clamp01(d) }} />;
                  })}
                  <div style={{ position: "absolute", left: -250, top: 95, width: 710, height: 10, borderRadius: 5, background: LINE }}>
                    <div style={{ width: `${playerP(t) * 100}%`, height: "100%", borderRadius: 5, background: t >= K(19) ? ACC : GRAY }} />
                  </div>
                  <At x={-250} y={132} anchor="left" style={{ ...txt(20, 500, GRAY), fontVariantNumeric: "tabular-nums" }}>0:0{Math.floor(playerP(t) * 19)}</At>
                  <At x={460} y={132} anchor="right" style={txt(20, 500, GRAY)}>0:19</At>
                </Layer>
                {/* scrub the beat grid */}
                <Layer t={t} tin={K(21, 0.06)} tout={K(25)}>
                  <At x={-440} y={-62} anchor="left" style={txt(28, 500, GRAY)}>节拍网格</At>
                  <At x={440} y={-62} anchor="right" style={{ ...txt(36, 700, INK), fontVariantNumeric: "tabular-nums" }}>
                    拍 <span style={{ color: ACC }}>{String(Math.max(1, Math.min(16, Math.floor(scrub * 16 + 0.5)))).padStart(2, "0")}</span> / 16
                  </At>
                  {Array.from({ length: 16 }, (_, i) => {
                    const lit = scrub * 16 > i + 0.5;
                    return <div key={i} style={{ position: "absolute", left: -440 + (i + 0.5) * 55 - 2, top: lit ? -22 : -14, width: 4, height: lit ? 28 : 18, borderRadius: 2, background: lit ? ACC : OFF }} />;
                  })}
                  <div style={{ position: "absolute", left: -440, top: 20, width: 880, height: 12, borderRadius: 6, background: LINE }}>
                    <div style={{ width: `${scrub * 100}%`, height: "100%", borderRadius: 6, background: ACC }} />
                  </div>
                  <div style={{ position: "absolute", left: -440 + scrub * 880 - 24, top: 2, width: 48, height: 48, borderRadius: 24, background: WHITE, boxShadow: "0 2px 10px rgba(0,0,0,0.2)", transform: `scale(${t >= SCRUB_HOLD[0] && t <= SCRUB_HOLD[1] ? 1.12 : 1})` }} />
                </Layer>
                {/* density slider */}
                <Layer t={t} tin={K(25, 0.06)} tout={K(29)}>
                  <At x={0} y={-350 - over * 0.3} style={{ ...txt(54, 700, INK), fontVariantNumeric: "tabular-nums" }}>{Math.round(vol * 100)}%</At>
                  <At x={0} y={-296 - over * 0.3} style={txt(24, 500, GRAY)}>动作密度</At>
                  <div style={{ position: "absolute", left: -65, top: -230 - over * 0.6, width: 130, height: 570 + over * 0.6, borderRadius: 65, background: LINE, overflow: "hidden" }}>
                    <div style={{ position: "absolute", left: 0, bottom: 0, width: "100%", height: `${vol * 100}%`, borderRadius: 65, background: ACC }}>
                      <div style={{ position: "absolute", left: 35, top: 24, width: 60, height: 8, borderRadius: 4, background: "rgba(255,255,255,0.85)" }} />
                    </div>
                  </div>
                </Layer>
                {/* toggle knob */}
                <Layer t={t} tin={K(29, 0.06)} tout={K(33)}>
                  <div style={{ position: "absolute", left: knobL, top: -74, width: Math.max(0, knobR - knobL), height: 148, borderRadius: 74, background: WHITE, boxShadow: "0 3px 10px rgba(0,0,0,0.18)" }} />
                </Layer>
                {/* waveform */}
                <Layer t={t} tin={K(33, 0.08)} tout={K(36)}>
                  <At x={-480} y={-230} anchor="left" style={txt(32, 600, INK)}>bgm.wav</At>
                  <At x={480} y={-230} anchor="right" style={txt(24, 500, GRAY)}>124 BPM · 4/4</At>
                  {Array.from({ length: 17 }, (_, i) => (
                    <div key={i} style={{ position: "absolute", left: -480 + i * 60 - 1, top: -170, width: 2, height: 400, background: i % 4 === 0 ? LINE : "#F2F0EC" }} />
                  ))}
                  {WAVE.map((a, i) => {
                    const g = step(t - K(33, 0.1 + (i / WAVE.length) * 0.9), UI);
                    const hh = a * WAVE_H * 2 * g;
                    return <div key={i} style={{ position: "absolute", left: WAVE_X(i) - 3.5, top: WAVE_Y - hh / 2, width: 7, height: hh, borderRadius: 3.5, background: INK }} />;
                  })}
                  {MARKERS.map((m, j) => {
                    const d = step(t - K(34, j * 0.08), UI);
                    const top = markerTop(m);
                    return (
                      <React.Fragment key={m.n}>
                        <div style={{ position: "absolute", left: WAVE_X(m.i) - 1.5, top: -150, width: 3, height: Math.max(0, (top + 150) * d), background: ACC }} />
                        <div style={{ position: "absolute", left: WAVE_X(m.i) - 9, top: mix(-150, top, d) - 9, width: 18, height: 18, borderRadius: 9, background: ACC, opacity: clamp01(d * 3) }} />
                        <At x={WAVE_X(m.i)} y={-176} style={{ ...txt(20, 600, ACC), opacity: clamp01(d * 2) }}>{m.n}</At>
                      </React.Fragment>
                    );
                  })}
                </Layer>
                {/* render progress */}
                <Layer t={t} tin={K(36, 0.08)} tout={K(37)}>
                  <At x={-380} y={-14} anchor="left" style={txt(34, 600, WHITE)}>渲染中</At>
                  <At x={380} y={-14} anchor="right" style={txt(24, 500, "rgba(255,255,255,0.6)")}>60fps · 4× 运动模糊</At>
                  <div style={{ position: "absolute", left: -380, top: 30, width: 760, height: 8, borderRadius: 4, background: "rgba(255,255,255,0.15)" }}>
                    <div style={{ width: `${E.inOut(clamp01((t - K(36, 0.08)) / (B * 0.8))) * 100}%`, height: "100%", borderRadius: 4, background: ACC }} />
                  </div>
                </Layer>
                {/* toast */}
                <Layer t={t} tin={K(37, 0.06)} tout={K(39)}>
                  <div style={{ position: "absolute", left: -370, top: -36, width: 72, height: 72, borderRadius: 36, background: ACC, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${step(t - K(37, 0.06), UI)})` }}>
                    <Check size={40} strokeWidth={2.6} color={WHITE} />
                  </div>
                  <div style={{ position: "absolute", left: -276, top: -48, whiteSpace: "nowrap" }}>
                    <div style={txt(38, 600, WHITE)}>已导出 promo.mp4</div>
                    <div style={{ ...txt(24, 400, "rgba(255,255,255,0.6)"), marginTop: 4 }}>1920×1080 · 60fps · 19 秒</div>
                  </div>
                </Layer>
                {/* back to the button */}
                <Layer t={t} tin={K(39, 0.1)} tout={99}>
                  <At x={0} y={0} style={{ ...txt(48, 600, WHITE), display: "flex", alignItems: "center", gap: 14 }}>
                    做宣传片 <span>→</span>
                  </At>
                </Layer>
              </div>
            </div>

            {/* waveform tooltip */}
            {hoverTip && (
              <div style={{ position: "absolute", left: cx + 30, top: cy - 96, padding: "14px 20px", borderRadius: 16, background: INK, boxShadow: "0 12px 30px rgba(0,0,0,0.2)", whiteSpace: "nowrap", ...swap(t, K(35, -0.05), K(36, -0.1)) }}>
                <div style={txt(24, 600, WHITE)}>tap · 峰值 +4ms</div>
                <div style={{ ...txt(18, 400, "rgba(255,255,255,0.6)"), marginTop: 2 }}>音效按实测峰值对齐</div>
              </div>
            )}
          </div>

          {/* cursor */}
          <svg width={48} height={48} viewBox="0 0 24 24" style={{ position: "absolute", left: sx - 5, top: sy - 3, transform: `scale(${isDown ? 0.88 : 1})`, transformOrigin: "5px 3px", filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.25))" }}>
            <path d="M5 3 L5 19 L9.5 14.8 L12.6 21 L15.2 19.8 L12.2 13.7 L18.5 13.4 Z" fill={INK} stroke={WHITE} strokeWidth={1.4} strokeLinejoin="round" />
          </svg>
        </AbsoluteFill>
      </CameraMotionBlur>
      <Audio src={staticFile("music/bgm124.wav")} volume={(fr) => interpolate(fr, [0, 3, durationInFrames - 14, durationInFrames - 1], [0.35, 0.65, 0.65, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      <SoundCues cues={cues()} />
    </AbsoluteFill>
  );
};

const at = (s: number) => Math.round(s * FPS);

const cues = (): Cue[] => [
  { at: at(K(3)), name: "click", volume: 0.8 },
  { at: at(K(4)), name: "swish-1", volume: 0.15 },
  ...keyCues(PROMPT, Array.from(PROMPT).map((_, i) => (i / PROMPT_CPS) * FPS), at(PROMPT_T0), 0.4, 4),
  { at: at(K(7)), name: "click", volume: 0.55 },
  { at: at(K(8)), name: "swish-2", volume: 0.12 },
  { at: at(K(11)), name: "done", volume: 0.45 },
  { at: at(K(12)), name: "pop", volume: 0.35 },
  ...[14, 15, 16].map((b) => ({ at: at(K(b)), name: "tap", volume: 0.45 })),
  { at: at(K(17)), name: "swish-3", volume: 0.12 },
  { at: at(K(18)), name: "click", volume: 0.7 },
  { at: at(SCRUB_HOLD[0]), name: "click", volume: 0.55 },
  ...tickCrossings.map((tt) => ({ at: at(tt), name: "tap", volume: 0.16 })),
  { at: at(K(24)), name: "tap", volume: 0.4 },
  { at: at(K(26)), name: "click", volume: 0.55 },
  { at: at(K(28)), name: "tap", volume: 0.4 },
  { at: at(K(31)), name: "click", volume: 0.7 },
  { at: at(K(32)), name: "whoosh", volume: 0.25 },
  { at: at(K(33)), name: "swish-1", volume: 0.12 },
  ...MARKERS.map((_, j) => ({ at: at(K(34, j * 0.08)), name: "tap", volume: 0.18 })),
  { at: at(K(36)), name: "swish-2", volume: 0.12 },
  { at: at(K(37)), name: "ding", volume: 0.3 },
  { at: at(K(39)), name: "swish-3", volume: 0.12 },
];
