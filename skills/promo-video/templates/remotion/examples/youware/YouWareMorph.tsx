import React from "react";
import { Check, CornerDownLeft, FileSpreadsheet, FileText } from "lucide-react";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { V } from "./cinematic/brand";
import { E, clamp01, mix } from "./cinematic/motion";
import { CAM, CURSOR, LEAD, PRESS, TRAIL, UI, step, track, trackCfg, trackColor } from "./cinematic/spring";

export const BPM = 122.3;
const B = 60 / BPM;
export const MORPH_BEATS = 28;
export const morphSeconds = MORPH_BEATS * B;
const K = (n: number, o = 0) => (n - 1) * B + o;

const CANVAS = "#F3F3F3";
const INK = "#111111";
const WHITE = "#FFFFFF";
const GRAY = "#8A8680";
const LINE = "#E6E3DE";
const ACC = "#F36440";
const OFF = "#D6D2CC";
const DISPLAY = V.display;
const SANS = V.body;

const CX = 1420;
const CY = 540;

const SHAPE: [number, number, number, number][] = [
  [0, 480, 132, 66],
  [K(4), 1040, 156, 78],
  [K(9), 1040, 280, 36],
  [K(13), 1000, 156, 78],
  [K(17), 160, 160, 80],
  [K(20), 860, 168, 84],
  [K(21), 1040, 580, 36],
  [K(25), 980, 520, 36],
  [K(27), 880, 168, 84],
];
const BG: [number, string][] = [
  [0, INK],
  [K(4), WHITE],
  [K(17), INK],
  [K(20), INK],
  [K(21), WHITE],
  [K(27), INK],
];
const fill = (w: number, h: number) => Math.min(880 / w, 780 / h, 1.85);
const MAX_W = 920;
const CAMK: [number, number][] = SHAPE.map(([t, w, h]) => [t, fill(w, h)]);
const PRESSK: [number, number][] = [
  [0, 1],
  [K(3), 0.94],
  [K(3, 0.1), 1],
  [K(8), 0.97],
  [K(8, 0.1), 1],
];

const P0: [number, number] = [280, 180];
const CUR: [number, number, number][] = [
  [0, ...P0],
  [K(1, 0.05), 80, 16],
  [K(4, 0.1), 360, 160],
  [K(7), 430, 0],
  [K(8, 0.15), 430, 80],
  [K(9, 0.1), -220, 40],
  [K(11), 40, 70],
  [K(13), -200, 140],
  [K(14, -0.28), -320, 4],
  [K(15, -0.28), 0, 4],
  [K(16, -0.28), 320, 4],
  [K(16, 0.3), 200, 150],
  [K(18), 80, 80],
  [K(21, 0.15), -360, -160],
  [K(23), 360, 160],
  [K(25, 0.1), -360, -80],
  [K(26), -360, 80],
  [K(27, 0.2), 400, 140],
];
const PRESSES: [number, number][] = [
  [K(3), K(3, 0.1)],
  [K(8), K(8, 0.1)],
  [K(14), K(14, 0.08)],
  [K(15), K(15, 0.08)],
  [K(16), K(16, 0.08)],
];
const cursorAt = (t: number): [number, number] => [
  track(t, CUR.map(([tt, x]) => [tt, x] as [number, number]), CURSOR),
  track(t, CUR.map(([tt, , y]) => [tt, y] as [number, number]), CURSOR),
];

const PROMPT = "Create a quarterly business review deck for Northline Home.";
const PROMPT_T0 = K(5, 0.04);
const PROMPT_CPS = 16;
const TABS = ["Gemini 3 Pro", "Claude Sonnet", "GPT-5-Codex"];
const FILES = [
  { name: "Q2 Sales.xlsx", meta: "XLSX · Sales data", kind: "xlsx" as const },
  { name: "Customer interviews.docx", meta: "DOCX · 12 interviews", kind: "docx" as const },
];
const AGENTS = [
  { img: "images/head-3.png", name: "Project Manager", status: "Plan ready" },
  { img: "images/head-7.png", name: "Researcher", status: "12 sources" },
  { img: "images/head-2.png", name: "Data Analyst", status: "Work shown" },
  { img: "images/head-4.png", name: "Writer & Designer", status: "15 pages" },
  { img: "images/head-1.png", name: "Reviewer", status: "2 flagged" },
];
const CHECKS = ["Market sizing · Industry report 2026", "Revenue table · Q2 filing", "Survey panel · 1,200 respondents"];

type Head = { tin: number; cap: string; l1: string; l2: string };
const HEADS: Head[] = [
  { tin: -1, cap: "YOUWARE", l1: "Ask once.", l2: "Get {finished work}." },
  { tin: K(4), cap: "01  BRIEF", l1: "You type.", l2: "It {starts}." },
  { tin: K(9), cap: "02  FILES", l1: "Bring your", l2: "{files}." },
  { tin: K(13), cap: "03  MODEL", l1: "Pick any", l2: "{model}." },
  { tin: K(17), cap: "04  TEAM", l1: "A specialist", l2: "for {every step}." },
  { tin: K(25), cap: "05  CHECK", l1: "Nothing ships", l2: "{unchecked}." },
];

const swap = (t: number, tin: number, tout: number, rise = 0) => {
  const i = E.out(clamp01((t - tin) / 0.2));
  const o = clamp01((t - tout) / 0.1);
  return {
    opacity: i * (1 - o),
    filter: `blur(${(1 - i) * 10 + o * 8}px)`,
    transform: `translateY(${(1 - i) * rise - o * rise * 0.4}px) scale(${mix(0.96, 1, i) * mix(1, 0.98, o)})`,
  };
};
const visible = (t: number, tin: number, tout: number) => t >= tin - 0.02 && t <= tout + 0.12;

const At: React.FC<{ x: number; y: number; children: React.ReactNode; style?: React.CSSProperties; anchor?: "center" | "left" | "right" }> = ({
  x,
  y,
  children,
  style,
  anchor = "center",
}) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      transform: anchor === "center" ? "translate(-50%, -50%)" : anchor === "left" ? "translate(0, -50%)" : "translate(-100%, -50%)",
      whiteSpace: "nowrap",
    }}
  >
    <div style={style}>{children}</div>
  </div>
);

const Layer: React.FC<{ t: number; tin: number; tout: number; children: React.ReactNode }> = ({ t, tin, tout, children }) =>
  visible(t, tin, tout) ? <div style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, ...swap(t, tin, tout) }}>{children}</div> : null;

const txt = (size: number, weight: number, color: string, font: string = SANS): React.CSSProperties => ({
  fontFamily: font,
  fontSize: size,
  fontWeight: weight,
  color,
  letterSpacing: "-0.015em",
  lineHeight: 1.15,
});

const Accented: React.FC<{ s: string }> = ({ s }) => (
  <>
    {s.split(/(\{[^}]+\})/).map((p, i) =>
      p.startsWith("{") ? (
        <span key={i} style={{ color: ACC }}>
          {p.slice(1, -1)}
        </span>
      ) : (
        <span key={i}>{p}</span>
      ),
    )}
  </>
);

export const YouWareMorph: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  const [cx, cy] = cursorAt(t);
  const w = trackCfg(t, SHAPE.map(([tt, ww]) => [tt, ww]));
  const h = trackCfg(t, SHAPE.map(([tt, , hh]) => [tt, hh]));
  const r = trackCfg(t, SHAPE.map(([tt, , , rr]) => [tt, rr]));
  const bg = trackColor(t, BG);
  const cam = Math.min(track(t, CAMK, CAM), MAX_W / w);
  const press = track(t, PRESSK, PRESS);
  const indL = trackCfg(t, [
    [0, -360],
    [K(13), -480, LEAD],
    [K(14), -160, TRAIL],
    [K(15), 160, TRAIL],
  ]);
  const indR = trackCfg(t, [
    [0, -330],
    [K(13), -160, TRAIL],
    [K(14), 160, LEAD],
    [K(15), 480, LEAD],
  ]);
  const tabActive = t < K(14) ? 0 : t < K(15) ? 1 : 2;
  const typed = Math.max(0, Math.floor((t - PROMPT_T0) * PROMPT_CPS));
  const sx = CX + cx * cam;
  const sy = CY + cy * cam;
  const isDown = PRESSES.some(([a, b]) => t >= a && t <= b);

  return (
    <AbsoluteFill style={{ background: CANVAS }}>
      <CameraMotionBlur shutterAngle={180} samples={4}>
        <AbsoluteFill style={{ background: CANVAS }}>
          {HEADS.map((hd, i) => {
            const tout = HEADS[i + 1]?.tin ?? 99;
            if (!visible(t, hd.tin, tout)) return null;
            return (
              <div key={i} style={{ position: "absolute", left: 88, top: 340 }}>
                <div style={{ ...txt(22, 600, GRAY), letterSpacing: "0.16em", whiteSpace: "nowrap", ...swap(t, hd.tin, tout, 16) }}>{hd.cap}</div>
                <div style={{ ...txt(68, 500, INK, DISPLAY), marginTop: 22, letterSpacing: "-0.03em", whiteSpace: "nowrap", ...swap(t, hd.tin, tout, 36) }}>{hd.l1}</div>
                <div style={{ ...txt(68, 500, INK, DISPLAY), marginTop: 6, letterSpacing: "-0.03em", whiteSpace: "nowrap", ...swap(t, hd.tin < 0 ? hd.tin : hd.tin + B / 2, tout, 36) }}>
                  <Accented s={hd.l2} />
                </div>
              </div>
            );
          })}

          <div style={{ position: "absolute", left: CX, top: CY, transform: `scale(${cam})` }}>
            <div
              style={{
                position: "absolute",
                left: -w / 2,
                top: -h / 2,
                width: w,
                height: h,
                borderRadius: r,
                background: bg,
                overflow: "hidden",
                transform: `scale(${press})`,
                boxShadow: "0 24px 60px rgba(17,17,17,0.12), 0 2px 6px rgba(17,17,17,0.08)",
              }}
            >
              <div style={{ position: "absolute", left: w / 2, top: h / 2 }}>
                <Layer t={t} tin={-1} tout={K(4)}>
                  <At x={0} y={0} style={{ ...txt(42, 600, WHITE), display: "flex", alignItems: "center", gap: 12 }}>
                    New task <span style={{ display: "inline-block", transform: `translateX(${8 * step(t - K(2), UI)}px)` }}>→</span>
                  </At>
                </Layer>

                <Layer t={t} tin={K(4, 0.08)} tout={K(9)}>
                  <At x={-460} y={0} anchor="left" style={txt(32, 500, INK)}>
                    {Array.from(PROMPT).slice(0, typed).join("")}
                    <span
                      style={{
                        display: "inline-block",
                        width: 3,
                        height: 34,
                        marginLeft: 4,
                        verticalAlign: "-6px",
                        background: ACC,
                        opacity: Math.floor(t * 3) % 2 === 0 ? 1 : 0,
                      }}
                    />
                  </At>
                  <At
                    x={460}
                    y={0}
                    anchor="right"
                    style={{
                      padding: "10px 14px",
                      borderRadius: 14,
                      background: t >= K(8) ? ACC : "#F1EFEB",
                      display: "flex",
                    }}
                  >
                    <CornerDownLeft size={28} strokeWidth={2} color={t >= K(8) ? WHITE : INK} />
                  </At>
                </Layer>

                <Layer t={t} tin={K(9, 0.06)} tout={K(13)}>
                  {FILES.map((file, i) => {
                    const e = step(t - K(9, 0.12 + i * 0.35), UI);
                    const Icon = file.kind === "xlsx" ? FileSpreadsheet : FileText;
                    return (
                      <div
                        key={file.name}
                        style={{
                          position: "absolute",
                          left: -460,
                          top: -90 + i * 88,
                          width: 920,
                          height: 76,
                          borderRadius: 18,
                          background: "#F7F6F3",
                          border: "1px solid rgba(0,0,0,0.06)",
                          display: "flex",
                          alignItems: "center",
                          gap: 16,
                          padding: "0 22px",
                          boxSizing: "border-box",
                          opacity: clamp01(e * 1.4),
                          transform: `translateY(${(1 - e) * 24}px)`,
                        }}
                      >
                        <div
                          style={{
                            width: 44,
                            height: 44,
                            borderRadius: 12,
                            background: file.kind === "xlsx" ? "#E4F1E4" : "#E4ECF8",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <Icon size={22} strokeWidth={1.75} color={file.kind === "xlsx" ? "#1D7A3E" : "#2C5BB5"} />
                        </div>
                        <div>
                          <div style={txt(26, 600, INK)}>{file.name}</div>
                          <div style={txt(16, 400, GRAY)}>{file.meta}</div>
                        </div>
                      </div>
                    );
                  })}
                </Layer>

                {t >= K(13) && t <= K(17, 0.12) && (
                  <div
                    style={{
                      position: "absolute",
                      left: indL,
                      top: -58,
                      width: Math.max(0, indR - indL),
                      height: 116,
                      borderRadius: 58,
                      background: ACC,
                      ...swap(t, K(13), K(17)),
                    }}
                  />
                )}
                <Layer t={t} tin={K(13, 0.08)} tout={K(17)}>
                  {TABS.map((tab, i) => (
                    <At key={tab} x={-320 + i * 320} y={0} style={txt(28, 600, i === tabActive ? WHITE : INK)}>
                      {tab}
                    </At>
                  ))}
                </Layer>

                <Layer t={t} tin={K(17, 0.04)} tout={K(20)}>
                  <svg width={150} height={150} style={{ position: "absolute", left: -75, top: -75, transform: `rotate(${t * 480}deg)` }}>
                    <circle cx={75} cy={75} r={40} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={10} />
                    <circle
                      cx={75}
                      cy={75}
                      r={40}
                      fill="none"
                      stroke={WHITE}
                      strokeWidth={10}
                      strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 40 * mix(0.18, 1, step(t - K(18), UI) * 0.45 + step(t - K(19), UI) * 0.55)} 400`}
                    />
                  </svg>
                </Layer>

                <Layer t={t} tin={K(20, 0.04)} tout={K(21)}>
                  <At x={-300} y={0} anchor="left" style={txt(34, 600, WHITE)}>
                    5 specialists
                  </At>
                  <At x={340} y={0} anchor="right" style={txt(24, 500, "rgba(255,255,255,0.55)")}>
                    on your task
                  </At>
                </Layer>

                <Layer t={t} tin={K(21, 0.08)} tout={K(25)}>
                  {AGENTS.map((ag, i) => {
                    const e = step(t - K(21, 0.12 + i * 0.28), UI);
                    return (
                      <div
                        key={ag.name}
                        style={{
                          position: "absolute",
                          left: -460,
                          top: -230 + i * 88,
                          width: 920,
                          height: 76,
                          borderRadius: 16,
                          background: i === 4 && t >= K(24) ? "#F8EEEA" : "#F7F6F3",
                          display: "flex",
                          alignItems: "center",
                          gap: 16,
                          padding: "0 18px",
                          boxSizing: "border-box",
                          opacity: clamp01(e * 1.5),
                          transform: `translateX(${(1 - e) * -40}px)`,
                        }}
                      >
                        <div style={{ width: 52, height: 52, borderRadius: 26, overflow: "hidden", flexShrink: 0 }}>
                          <Img src={staticFile(ag.img)} style={{ width: 52, height: 52 }} />
                        </div>
                        <div style={txt(26, 600, INK)}>{ag.name}</div>
                        <div style={{ ...txt(20, 500, i === 4 && t >= K(24) ? ACC : GRAY), marginLeft: "auto" }}>{ag.status}</div>
                      </div>
                    );
                  })}
                </Layer>

                <Layer t={t} tin={K(25, 0.06)} tout={K(27)}>
                  {CHECKS.map((c, i) => {
                    const e = step(t - K(25, 0.15 + i * 0.32), UI);
                    return (
                      <div
                        key={c}
                        style={{
                          position: "absolute",
                          left: -430,
                          top: -140 + i * 92,
                          width: 860,
                          display: "flex",
                          alignItems: "center",
                          gap: 18,
                          opacity: clamp01(e * 1.5),
                        }}
                      >
                        <div
                          style={{
                            width: 40,
                            height: 40,
                            borderRadius: 12,
                            background: e > 0.55 ? ACC : OFF,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <Check size={22} strokeWidth={2.4} color={WHITE} />
                        </div>
                        <div style={txt(26, 500, INK)}>{c}</div>
                      </div>
                    );
                  })}
                </Layer>

                <Layer t={t} tin={K(27, 0.06)} tout={99}>
                  <div
                    style={{
                      position: "absolute",
                      left: -380,
                      top: -36,
                      width: 72,
                      height: 72,
                      borderRadius: 36,
                      background: ACC,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transform: `scale(${step(t - K(27, 0.06), UI)})`,
                    }}
                  >
                    <Check size={38} strokeWidth={2.6} color={WHITE} />
                  </div>
                  <div style={{ position: "absolute", left: -284, top: -40, whiteSpace: "nowrap" }}>
                    <div style={txt(32, 600, WHITE)}>Your market report is ready.</div>
                    <div style={{ ...txt(20, 400, "rgba(255,255,255,0.6)"), marginTop: 4 }}>Open the finished deck.</div>
                  </div>
                </Layer>
              </div>
            </div>
          </div>

          <svg
            width={44}
            height={44}
            viewBox="0 0 24 24"
            style={{
              position: "absolute",
              left: sx - 5,
              top: sy - 3,
              transform: `scale(${isDown ? 0.88 : 1})`,
              transformOrigin: "5px 3px",
              filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.25))",
            }}
          >
            <path d="M5 3 L5 19 L9.5 14.8 L12.6 21 L15.2 19.8 L12.2 13.7 L18.5 13.4 Z" fill={INK} stroke={WHITE} strokeWidth={1.4} strokeLinejoin="round" />
          </svg>
        </AbsoluteFill>
      </CameraMotionBlur>
    </AbsoluteFill>
  );
};

export const morphCues = (from: number) => {
  const at = (s: number) => Math.round(from + s * 30);
  const keys = Array.from(PROMPT).map((_, i) => ({
    at: at(PROMPT_T0 + i / PROMPT_CPS),
    name: `key-${(i % 7) + 1}`,
    volume: 0.38,
  }));
  return [
    { at: at(K(3)), name: "click", volume: 0.8 },
    { at: at(K(4)), name: "swish-1", volume: 0.14 },
    ...keys.filter((_, i) => i % 2 === 0),
    { at: at(K(8)), name: "click", volume: 0.6 },
    { at: at(K(9)), name: "paper-place-1", volume: 0.35 },
    { at: at(K(10)), name: "paper-place-2", volume: 0.3 },
    ...[14, 15, 16].map((b) => ({ at: at(K(b)), name: "tap", volume: 0.45 })),
    { at: at(K(17)), name: "swish-2", volume: 0.12 },
    { at: at(K(20)), name: "pop", volume: 0.35 },
    ...AGENTS.map((_, i) => ({ at: at(K(21, 0.12 + i * 0.28)), name: "tap", volume: 0.22 })),
    ...CHECKS.map((_, i) => ({ at: at(K(25, 0.15 + i * 0.32)), name: "done", volume: 0.28 })),
    { at: at(K(27)), name: "ding", volume: 0.32 },
  ];
};
