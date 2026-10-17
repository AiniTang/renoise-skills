import React from "react";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { AbsoluteFill, Img, random, staticFile, useCurrentFrame } from "remotion";
import { E, clamp01, mix, seg, track, typed, typingSchedule } from "./cinematic/motion";
import { V } from "./cinematic/brand";

const SANS = V.body;
const SERIF = V.display;
const ORANGE = V.accent;
const BG = "#F3F3F3";

export const PROMPT = "Create a quarterly business review deck for Northline Home.";
export const PROMPT_T = typingSchedule(PROMPT, 14, 0.95, (i) => random(`key${i}`));
const REPLY = "Reviewing your data, then building the deck.";
const REPLY_T = typingSchedule(REPLY, 108, 0.32, () => 0.5);
const HEADLINE = "Growth is up.\nClarity comes next.";
const HEADLINE_T = typingSchedule(HEADLINE, 186, 0.85, (i) => random(`h${i}`));

export const AGENTS = [
  { img: "images/head-3.png", name: "Project Manager", status: "Plan and checklist ready" },
  { img: "images/head-7.png", name: "Researcher", status: "12 sources verified" },
  { img: "images/head-2.png", name: "Data Analyst", status: "Charts built, work shown" },
  { img: "images/head-4.png", name: "Writer & Designer", status: "8 slides laid out" },
  { img: "images/head-1.png", name: "Reviewer", status: "2 items flagged for you" },
];
export const agentStart = (i: number) => 118 + i * 11;
export const agentDone = (i: number) => agentStart(i) + 16;
export const CHIP_AT = [62, 68];
export const CLICK_AT = 88;
export const TOAST_AT = 232;
export const UI_FRAMES = 260;

const CARD_A = { x: 510, y: 420, w: 900, h: 230 };
const CARD_B = { x: 180, y: 890, w: 440, h: 84 };
const WIN = { x: 160, y: 80, w: 1600, h: 920 };
const SLIDE = { x: 810, y: 240, w: 930, h: 523 };

const camera = (f: number) =>
  track(f, [
    { f: 0, x: 960, y: 560, s: 2.3, rx: 24, ry: 0 },
    { f: 16, x: 960, y: 560, s: 1.5, rx: 12, ry: 0, ease: E.out },
    { f: 60, x: 930, y: 555, s: 1.38, rx: 0, ry: 0 },
    { f: 84, x: 1120, y: 590, s: 1.5, rx: 0, ry: 0 },
    { f: 94, x: 1120, y: 590, s: 1.52, rx: 0, ry: 0 },
    { f: 124, x: 960, y: 540, s: 0.97, rx: 7, ry: -10 },
    { f: 150, x: 760, y: 600, s: 1.25, rx: 2, ry: -3, ease: E.sine },
    { f: 176, x: 720, y: 640, s: 1.3, rx: 0, ry: 0, ease: E.sine },
    { f: 205, x: 1275, y: 500, s: 1.5, rx: 0, ry: 0 },
    { f: 246, x: 1275, y: 500, s: 1.62, rx: 0, ry: 0, ease: E.sine },
    { f: 260, x: 1110, y: 395, s: 4.4, rx: 0, ry: 0, ease: E.in },
  ]);

const Caret: React.FC<{ f: number; typing: boolean; color?: string }> = ({ f, typing, color = "#111" }) => (
  <span
    style={{
      display: "inline-block",
      width: "0.08em",
      height: "1.05em",
      marginLeft: 2,
      verticalAlign: "-0.15em",
      background: color,
      opacity: typing || Math.floor(f / 15) % 2 === 0 ? 1 : 0,
    }}
  />
);

const FileIcon: React.FC<{ kind: "xlsx" | "docx" }> = ({ kind }) => (
  <div
    style={{
      width: 34,
      height: 34,
      borderRadius: 8,
      background: kind === "xlsx" ? "#E4F1E4" : "#E4ECF8",
      color: kind === "xlsx" ? "#1D7A3E" : "#2C5BB5",
      fontFamily: SANS,
      fontSize: 11,
      fontWeight: 700,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    {kind.toUpperCase()}
  </div>
);

const CHIPS = [
  { kind: "xlsx" as const, name: "Q2 Sales.xlsx", meta: "XLSX · Sales data" },
  { kind: "docx" as const, name: "Customer interviews.docx", meta: "DOCX · 12 interviews" },
];

const Chip: React.FC<{ i: number; f: number; morph: number }> = ({ i, f, morph }) => {
  const c = CHIPS[i];
  const appear = seg(f, CHIP_AT[i], 14, E.back);
  const from = { x: CARD_A.x + 28 + i * 300, y: CARD_A.y + 100, w: 284 };
  const to = { x: 196, y: 348 + i * 64, w: 400 };
  const x = mix(from.x, to.x, morph);
  const y = mix(from.y, to.y, morph);
  const w = mix(from.w, to.w, morph);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: 54,
        borderRadius: 14,
        background: "#fff",
        border: "1px solid rgba(0,0,0,0.08)",
        boxShadow: "0 6px 18px rgba(0,0,0,0.06)",
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "0 12px",
        opacity: clamp01(appear * 1.4),
        transform: `scale(${mix(0.6, 1, appear)}) translateY(${(1 - appear) * 20}px)`,
        transformOrigin: "left center",
      }}
    >
      <FileIcon kind={c.kind} />
      <div style={{ fontFamily: SANS, lineHeight: 1.25 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "#111" }}>{c.name}</div>
        <div style={{ fontSize: 12, color: "rgba(0,0,0,0.5)" }}>{c.meta}</div>
      </div>
    </div>
  );
};

const Composer: React.FC<{ f: number; morph: number }> = ({ f, morph }) => {
  const r = {
    x: mix(CARD_A.x, CARD_B.x, morph),
    y: mix(CARD_A.y, CARD_B.y, morph),
    w: mix(CARD_A.w, CARD_B.w, morph),
    h: mix(CARD_A.h, CARD_B.h, morph),
  };
  const text = typed(PROMPT, PROMPT_T.times, f);
  const typing = f >= PROMPT_T.times[0] && f < PROMPT_T.end + 2;
  const press = f >= CLICK_AT && f < CLICK_AT + 8 ? 1 - Math.sin(((f - CLICK_AT) / 8) * Math.PI) * 0.08 : 1;
  const aOpacity = clamp01(1 - morph * 3);
  const bOpacity = clamp01((morph - 0.6) / 0.4);
  const ripple = seg(f, CLICK_AT, 18, E.out);
  return (
    <div
      style={{
        position: "absolute",
        left: r.x,
        top: r.y,
        width: r.w,
        height: r.h,
        borderRadius: mix(28, 20, morph),
        background: "#fff",
        boxShadow: `0 ${mix(30, 8, morph)}px ${mix(80, 24, morph)}px rgba(0,0,0,${mix(0.1, 0.06, morph)})`,
        border: "1px solid rgba(0,0,0,0.06)",
      }}
    >
      <div style={{ position: "absolute", inset: 0, padding: "26px 28px", opacity: aOpacity }}>
        <div style={{ fontFamily: SANS, fontSize: 28, color: "#111", lineHeight: 1.35 }}>
          {text}
          <Caret f={f} typing={typing} />
        </div>
        <div style={{ position: "absolute", left: 28, bottom: 28, display: "flex", gap: 10, alignItems: "center" }}>
          {["#34A853", "#EA4335", "#107C41", "#A259FF", "#111"].map((c) => (
            <div key={c} style={{ width: 16, height: 16, borderRadius: 4, background: c, opacity: 0.85 }} />
          ))}
          <span style={{ fontFamily: SANS, fontSize: 18, color: "rgba(0,0,0,0.45)", marginLeft: 6 }}>Connectors</span>
        </div>
        <div
          style={{
            position: "absolute",
            right: 28,
            bottom: 24,
            height: 52,
            padding: "0 26px",
            borderRadius: 999,
            background: "#111",
            color: "#fff",
            fontFamily: SANS,
            fontWeight: 600,
            fontSize: 20,
            display: "flex",
            alignItems: "center",
            transform: `scale(${press})`,
          }}
        >
          Try for free →
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              width: 240,
              height: 240,
              marginLeft: -120,
              marginTop: -120,
              borderRadius: "50%",
              border: `3px solid ${ORANGE}`,
              transform: `scale(${mix(0.2, 1, ripple)})`,
              opacity: f >= CLICK_AT ? (1 - ripple) * 0.9 : 0,
            }}
          />
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          inset: 0,
          padding: "0 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          opacity: bOpacity,
          fontFamily: SANS,
          fontSize: 17,
          color: "rgba(0,0,0,0.4)",
        }}
      >
        Chat with YouWare
        <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#D6D6D6", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>
          ↑
        </div>
      </div>
    </div>
  );
};

const Spinner: React.FC<{ f: number }> = ({ f }) => (
  <svg width={26} height={26} viewBox="0 0 26 26" style={{ transform: `rotate(${f * 18}deg)` }}>
    <circle cx={13} cy={13} r={10} fill="none" stroke="rgba(0,0,0,0.12)" strokeWidth={3} />
    <path d="M13 3 a10 10 0 0 1 10 10" fill="none" style={{ stroke: ORANGE }} strokeWidth={3} strokeLinecap="round" />
  </svg>
);

const Check: React.FC<{ p: number }> = ({ p }) => (
  <div
    style={{
      width: 26,
      height: 26,
      borderRadius: "50%",
      background: ORANGE,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transform: `scale(${mix(0.3, 1, p)})`,
    }}
  >
    <svg width={14} height={14} viewBox="0 0 14 14">
      <path d="M2.5 7.5 L5.5 10.5 L11.5 3.5" fill="none" stroke="#fff" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  </div>
);

const LeftPanel: React.FC<{ f: number; blur: number }> = ({ f, blur }) => {
  const bubble = seg(f, 100, 14);
  const progress = seg(f, 118, 80, E.inOut);
  return (
    <div style={{ position: "absolute", left: WIN.x, top: WIN.y + 46, width: 480, height: WIN.h - 46, filter: `blur(${blur}px)` }}>
      <div style={{ position: "absolute", left: 24, top: 18, fontFamily: SANS, fontSize: 19, fontWeight: 500, color: "#111" }}>
        Quarterly Business Review
      </div>
      <div
        style={{
          position: "absolute",
          left: 24,
          top: 62,
          width: 432,
          padding: "14px 18px",
          borderRadius: 16,
          background: "#EEF0E6",
          fontFamily: SANS,
          fontSize: 17,
          lineHeight: 1.45,
          color: "#222",
          opacity: bubble,
          transform: `translateY(${(1 - bubble) * 18}px)`,
        }}
      >
        {PROMPT} Include key metrics, customer insights and next steps.
      </div>
      <div style={{ position: "absolute", left: 24, top: 170, width: 432, fontFamily: SANS, fontSize: 17, lineHeight: 1.45, color: "#333" }}>
        {typed(REPLY, REPLY_T.times, f)}
      </div>
      <div style={{ position: "absolute", left: 24, top: 392, width: 432, opacity: seg(f, 114, 10) }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: SANS, fontSize: 14, color: "rgba(0,0,0,0.5)" }}>
          <span>{progress < 1 ? "Your AI team is working" : "All steps complete"}</span>
          <span>{Math.round(progress * 100)}%</span>
        </div>
        <div style={{ marginTop: 8, height: 4, borderRadius: 2, background: "rgba(0,0,0,0.08)" }}>
          <div style={{ width: `${progress * 100}%`, height: "100%", borderRadius: 2, background: ORANGE }} />
        </div>
      </div>
      {AGENTS.map((a, i) => {
        const inP = seg(f, agentStart(i), 12, E.out);
        const doneP = seg(f, agentDone(i), 10, E.back);
        const done = f >= agentDone(i);
        const statusChars = Math.floor(clamp01((f - agentStart(i) - 4) / 14) * a.status.length);
        return (
          <div
            key={a.name}
            style={{
              position: "absolute",
              left: 24,
              top: 440 + i * 66,
              width: 432,
              height: 56,
              display: "flex",
              alignItems: "center",
              gap: 14,
              opacity: inP,
              transform: `translateX(${(1 - inP) * -30}px)`,
            }}
          >
            <Img src={staticFile(a.img)} style={{ width: 44, height: 44, objectFit: "contain" }} />
            <div style={{ flex: 1, fontFamily: SANS, lineHeight: 1.3 }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#111" }}>{a.name}</div>
              <div style={{ fontSize: 14, color: "rgba(0,0,0,0.5)" }}>{a.status.slice(0, statusChars)}</div>
            </div>
            {done ? <Check p={doneP} /> : <Spinner f={f} />}
          </div>
        );
      })}
    </div>
  );
};

const Thumb: React.FC<{ i: number; f: number; blur: number }> = ({ i, f, blur }) => {
  const p = seg(f, 168 + i * 6, 14, E.back);
  const dark = i % 3 === 0;
  return (
    <div
      style={{
        position: "absolute",
        left: 668,
        top: 184 + i * 86,
        width: 118,
        height: 66,
        borderRadius: 6,
        background: dark ? "#3B3A33" : "#F1EEE6",
        border: i === 0 ? `2px solid ${ORANGE}` : "1px solid rgba(0,0,0,0.08)",
        opacity: clamp01(p * 1.5),
        transform: `scale(${mix(0.5, 1, p)})`,
        filter: `blur(${blur}px)`,
        padding: 8,
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div style={{ width: "60%", height: 6, borderRadius: 2, background: dark ? "#CDE8A0" : "#3B3A33" }} />
      <div style={{ width: "40%", height: 4, borderRadius: 2, background: dark ? "#8a877d" : "#bdbab0" }} />
      <div style={{ marginTop: "auto", display: "flex", gap: 3, alignItems: "flex-end", height: 18 }}>
        {[0.5, 0.8, 0.6, 1].map((h, k) => (
          <div key={k} style={{ flex: 1, height: `${h * 100}%`, background: k === 3 ? ORANGE : dark ? "#6b6a60" : "#d8d3c6" }} />
        ))}
      </div>
    </div>
  );
};

const Slide: React.FC<{ f: number }> = ({ f }) => {
  const wipe = seg(f, 168, 18, E.inOut);
  const headline = typed(HEADLINE, HEADLINE_T.times, f);
  const bars = [0.42, 0.55, 0.5, 0.72, 0.95];
  const growth = seg(f, 216, 22, E.out);
  const sweep = seg(f, 226, 18, E.inOut);
  const tile = (start: number) => seg(f, start, 16, E.back);
  return (
    <div
      style={{
        position: "absolute",
        left: SLIDE.x,
        top: SLIDE.y,
        width: SLIDE.w,
        height: SLIDE.h,
        background: "#3B3A33",
        clipPath: `inset(0 ${(1 - wipe) * 100}% 0 0 round 4px)`,
        overflow: "hidden",
        boxShadow: "0 30px 60px rgba(0,0,0,0.18)",
      }}
    >
      <div style={{ position: "absolute", left: 40, top: 34, fontFamily: SANS, fontSize: 13, letterSpacing: "0.1em", color: "#BDBAB0", opacity: seg(f, 178, 10) }}>
        NORTHLINE HOME &nbsp;/&nbsp; Q2 2026 &nbsp;/&nbsp; 01
      </div>
      <div style={{ position: "absolute", left: 40, top: 110, width: 520, fontFamily: SANS, fontWeight: 300, fontSize: 56, lineHeight: 1.08, color: "#CDE8A0", whiteSpace: "pre-wrap" }}>
        {headline}
        {f >= HEADLINE_T.times[0] && f < HEADLINE_T.end + 12 ? <Caret f={f} typing={f < HEADLINE_T.end} color="#CDE8A0" /> : null}
      </div>
      <div style={{ position: "absolute", left: 40, top: 262, fontFamily: SANS, fontSize: 24, color: "#fff", opacity: seg(f, 212, 12), transform: `translateY(${(1 - seg(f, 212, 16)) * 14}px)` }}>
        Quarterly business review
      </div>
      <div style={{ position: "absolute", left: 40, top: 304, width: 440, fontFamily: SANS, fontSize: 15, lineHeight: 1.5, color: "#BDBAB0", opacity: seg(f, 218, 12) }}>
        Revenue performance, customer signals and Q3 priorities.
      </div>
      <div style={{ position: "absolute", left: 40, bottom: 30, fontFamily: SANS, fontSize: 10, letterSpacing: "0.1em", color: "#8a877d", opacity: seg(f, 220, 10) }}>
        ILLUSTRATIVE CASE · NOT CUSTOMER RESULTS
      </div>
      <div style={{ position: "absolute", left: 560, top: 36, width: 160, height: 170, background: "#D9D2C3", padding: 16, fontFamily: SANS, fontSize: 21, lineHeight: 1.2, color: "#3B3A33", opacity: clamp01(tile(200) * 1.5), transform: `scale(${mix(0.6, 1, tile(200))})`, transformOrigin: "top left" }}>
        Customer confidence.
      </div>
      <div style={{ position: "absolute", left: 560, top: 220, width: 160, height: 150, background: "#CDE8A0", padding: 16, fontFamily: SANS, fontSize: 21, lineHeight: 1.2, color: "#3B3A33", opacity: clamp01(tile(208) * 1.5), transform: `scale(${mix(0.6, 1, tile(208))})`, transformOrigin: "top left" }}>
        Listen.
        <br />
        Then act.
      </div>
      <div style={{ position: "absolute", left: 735, top: 36, width: 160, height: 334, background: "#4A4940", padding: 16, opacity: clamp01(tile(212) * 1.5), transform: `scale(${mix(0.6, 1, tile(212))})`, transformOrigin: "top left" }}>
        <div style={{ fontFamily: SANS, fontSize: 12, letterSpacing: "0.08em", color: "#BDBAB0" }}>Q2 REVENUE</div>
        <div style={{ fontFamily: SANS, fontSize: 34, fontWeight: 300, color: "#CDE8A0", marginTop: 6 }}>+{Math.round(18 * growth)}%</div>
        <div style={{ position: "absolute", left: 16, right: 16, bottom: 16, height: 190, display: "flex", alignItems: "flex-end", gap: 8 }}>
          {bars.map((h, k) => (
            <div
              key={k}
              style={{
                flex: 1,
                height: `${h * 100 * seg(f, 216 + k * 3, 18, E.out)}%`,
                background: k === bars.length - 1 ? ORANGE : "#8a877d",
                borderRadius: "3px 3px 0 0",
              }}
            />
          ))}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(105deg, transparent 35%, rgba(255,255,255,0.22) 50%, transparent 65%)",
          transform: `translateX(${mix(-100, 100, sweep)}%)`,
          opacity: f >= 226 && f <= 244 ? 1 : 0,
        }}
      />
    </div>
  );
};

const Workspace: React.FC<{ f: number; s: number; x: number }> = ({ f, s, x }) => {
  const open = seg(f, 92, 30, E.inOut);
  const blur = clamp01((s - 1.08) / 0.35) * clamp01((x - 900) / 300) * 6;
  return (
    <div
      style={{
        position: "absolute",
        left: WIN.x,
        top: WIN.y,
        width: WIN.w,
        height: WIN.h,
        borderRadius: 18,
        background: "#FCFCFC",
        boxShadow: "0 40px 120px rgba(0,0,0,0.14)",
        border: "1px solid rgba(0,0,0,0.06)",
        opacity: open,
        transform: `scale(${mix(1.08, 1, open)})`,
      }}
    >
      <div style={{ height: 46, borderBottom: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 8, padding: "0 18px" }}>
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
          <div key={c} style={{ width: 12, height: 12, borderRadius: "50%", background: c }} />
        ))}
        <div style={{ marginLeft: 20, padding: "5px 16px", borderRadius: 8, background: "#F0F0F0", fontFamily: SANS, fontSize: 13, color: "rgba(0,0,0,0.5)" }}>
          youware.com/chat
        </div>
      </div>
      <div style={{ position: "absolute", left: 480, top: 46, bottom: 0, width: 1, background: "rgba(0,0,0,0.06)" }} />
      <div style={{ position: "absolute", left: 504, top: 64, fontFamily: SANS, fontSize: 19, fontWeight: 500, color: "#111", filter: `blur(${blur * 0.5}px)`, opacity: seg(f, 160, 10) }}>
        Quarterly business review.pptx
      </div>
      <div style={{ position: "absolute", inset: 0, left: -WIN.x, top: -WIN.y, width: 1920, height: 1080 }}>
        <LeftPanel f={f} blur={blur} />
        {Array.from({ length: 6 }).map((_, i) => (
          <Thumb key={i} i={i} f={f} blur={blur * 0.6} />
        ))}
        <Slide f={f} />
      </div>
    </div>
  );
};

const Cursor: React.FC<{ f: number }> = ({ f }) => {
  const move = seg(f, 56, 28, E.inOut);
  const leave = seg(f, CLICK_AT + 6, 14, E.in);
  const p0 = { x: 1500, y: 880 };
  const c = { x: 1440, y: 700 };
  const p1 = { x: 1290, y: 606 };
  const bx = (1 - move) ** 2 * p0.x + 2 * (1 - move) * move * c.x + move ** 2 * p1.x;
  const by = (1 - move) ** 2 * p0.y + 2 * (1 - move) * move * c.y + move ** 2 * p1.y;
  const press = f >= CLICK_AT && f < CLICK_AT + 6 ? 0.82 : 1;
  const visible = seg(f, 54, 6, E.linear) * (1 - leave);
  return (
    <svg
      width={36}
      height={36}
      viewBox="0 0 24 24"
      style={{
        position: "absolute",
        left: bx + leave * 120,
        top: by + leave * 90,
        opacity: visible,
        transform: `scale(${press})`,
        transformOrigin: "top left",
        filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.25))",
      }}
    >
      <path d="M4 2 L20 12 L12.5 13.5 L9 21 Z" fill="#111" stroke="#fff" strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
};

const Pills: React.FC<{ f: number }> = ({ f }) => {
  const out = seg(f, 90, 10, E.inOut);
  return (
    <div style={{ position: "absolute", left: 0, width: 1920, top: 690, display: "flex", justifyContent: "center", gap: 12, opacity: seg(f, 4, 12) * (1 - out) }}>
      {["Presentations", "Reports", "Analysis", "Data", "Websites"].map((p, i) => (
        <div
          key={p}
          style={{
            padding: "10px 20px",
            borderRadius: 999,
            fontFamily: SANS,
            fontSize: 17,
            color: "rgba(0,0,0,0.7)",
            background: i === 0 ? "rgba(0,0,0,0.07)" : "transparent",
            border: "1px solid rgba(0,0,0,0.08)",
          }}
        >
          {p}
        </div>
      ))}
    </div>
  );
};

const Stage: React.FC = () => {
  const f = useCurrentFrame();
  const cam = camera(f);
  const morph = seg(f, 92, 30, E.inOut);
  const flat = Math.abs(cam.rx) < 0.01 && Math.abs(cam.ry) < 0.01;
  const rot = flat ? "" : ` rotateX(${cam.rx}deg) rotateY(${cam.ry}deg)`;
  const fadeIn = seg(f, 0, 10, E.linear);
  return (
    <AbsoluteFill style={{ background: BG, perspective: flat ? undefined : 2200, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          width: 1920,
          height: 1080,
          transformOrigin: "0 0",
          transform: `translate(960px, 540px)${rot} scale(${cam.s}) translate(${-cam.x}px, ${-cam.y}px)`,
          opacity: fadeIn,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: -400,
            background: `radial-gradient(ellipse 60% 50% at 50% 45%, #FFFFFF 0%, ${BG} 60%)`,
          }}
        />
        <Pills f={f} />
        <Workspace f={f} s={cam.s} x={cam.x} />
        <Composer f={f} morph={morph} />
        {CHIPS.map((_, i) => (
          <Chip key={i} i={i} f={f} morph={morph} />
        ))}
        <Cursor f={f} />
      </div>
      <Toast f={f} />
    </AbsoluteFill>
  );
};

const Toast: React.FC<{ f: number }> = ({ f }) => {
  const inP = seg(f, TOAST_AT, 14, E.back);
  const outP = seg(f, 250, 8, E.in);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 70 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "16px 28px",
          borderRadius: 999,
          background: "#111",
          color: "#fff",
          fontFamily: SANS,
          fontSize: 22,
          opacity: clamp01(inP * 1.5) * (1 - outP),
          transform: `translateY(${(1 - inP) * 60}px) scale(${mix(0.8, 1, inP)})`,
          boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
        }}
      >
        <Check p={inP} />
        Quarterly business review.pptx · 8 slides · Ready
      </div>
    </AbsoluteFill>
  );
};

/** ~242 frames. Fast camera moves get real motion blur. */
export const ProductUI: React.FC = () => {
  const f = useCurrentFrame();
  const fast = (f >= 92 && f <= 126) || f >= 246;
  return fast ? (
    <CameraMotionBlur samples={6} shutterAngle={160}>
      <Stage />
    </CameraMotionBlur>
  ) : (
    <Stage />
  );
};
