import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { Doodle, Label, Sticker, StickerBoard, StickerDefs, Tape } from "../cinematic/sticker";
import { fam } from "../cinematic/type";
import { step } from "../cinematic/spring";

/** 02 · 贴纸风科普 — "One YouWare. Four kinds of work." built from die-cut stickers of the official site art. 300 frames. */
export const STICKER_LEN = 330;
const SLAB = fam("Hepta Slab");
const SANS = fam("Manrope");
const HAND = fam("Caveat");
const INK = "#151513";

const SHOTS = [
  { src: "site/capability-websites.png", label: "WEBSITES", bg: "#EE8C6C", x: 1150, y: 390, r: -4, at: 44 },
  { src: "site/capability-slide-decks.png", label: "SLIDES", bg: "#7D6BC1", x: 1640, y: 410, r: 3, at: 70 },
  { src: "site/capability-spreadsheets.png", label: "SHEETS", bg: "#7D8F57", x: 1160, y: 790, r: 2, at: 96 },
  { src: "site/capability-research-reports.png", label: "REPORTS", bg: "#2556B6", x: 1650, y: 810, r: -3, at: 122 },
];
/** label at each screenshot's outer corner, tape across the seams, so the centre stays free for the count */
const LABEL: [number, number][] = [[-80, -175], [150, -170], [-150, 170], [150, 170]];
const TAPE: [number, number, number][] = [[215, -150, 24], [-215, -150, -22], [-215, -150, -26], [215, -150, 22]];
const HEADS = ["site/hero-team.png", "site/agent-data-analytics.png", "site/agent-market-research.png", "site/agent-product-strategy.png", "site/agent-competitive-analysis.png"];

const Word: React.FC<{ t: number; at: number; children: React.ReactNode }> = ({ t, at, children }) => {
  const k = step(Math.max(0, (t - at) / 30), { w: 2 * Math.PI * 2.6, z: 0.7 });
  return <span style={{ display: "inline-block", transform: `translateY(${(1 - k) * 60}px)`, opacity: Math.min(1, k * 1.4) }}>{children}</span>;
};

export const StickerDemo: React.FC<{ t?: number }> = ({ t: tProp }) => {
  const frame = useCurrentFrame();
  const t = tProp ?? frame;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <StickerDefs />
      <StickerBoard />
      <div style={{ position: "absolute", left: 120, top: 84, fontFamily: SLAB, fontWeight: 700, fontSize: 72, lineHeight: 1.05, color: INK, letterSpacing: "-0.02em", fontSynthesis: "none" }}>
        <div>
          <Word t={t} at={2}>One&nbsp;</Word>
          <Word t={t} at={6}>YouWare.</Word>
        </div>
        <div>
          <Word t={t} at={12}>Four&nbsp;</Word>
          <Word t={t} at={16}>kinds&nbsp;</Word>
          <Word t={t} at={20}>of&nbsp;</Word>
          <Word t={t} at={24}>work.</Word>
        </div>
      </div>

      {/* the prompt */}
      <Sticker t={t} at={30} x={440} y={520} rotate={-2}>
        <div style={{ width: 560, height: 116, background: "#FFFFFF", borderRadius: 58, display: "flex", alignItems: "center", gap: 18, padding: "0 20px 0 28px", fontFamily: SANS, fontSize: 30, color: INK, boxSizing: "border-box" }}>
          <div style={{ width: 44, height: 44, borderRadius: 22, border: "2px solid rgba(21,21,19,0.35)", display: "grid", placeItems: "center", fontSize: 30, color: "rgba(21,21,19,0.6)" }}>+</div>
          <div style={{ flex: 1, fontWeight: 500 }}>Make a pitch for my café</div>
          <div style={{ width: 64, height: 64, borderRadius: 32, background: INK, color: "#fff", display: "grid", placeItems: "center", fontSize: 30, fontWeight: 700 }}>↑</div>
        </div>
      </Sticker>
      <Doodle t={t} at={38} dur={14} d="M 745 500 C 800 470 850 450 880 420" head width={7} />

      {/* four kinds of work */}
      {SHOTS.map((s, i) => (
        <React.Fragment key={s.src}>
          <Sticker t={t} at={s.at} x={s.x} y={s.y} rotate={s.r} from={i % 2 ? "right" : "above"}>
            <Img src={staticFile(s.src)} style={{ width: 500, borderRadius: 14, display: "block" }} />
          </Sticker>
          <Tape t={t} at={s.at + 6} x={s.x + TAPE[i][0]} y={s.y + TAPE[i][1]} rotate={TAPE[i][2]} color={["rgba(238,140,108,0.75)", "rgba(180,165,228,0.8)", "rgba(207,227,160,0.9)", "rgba(134,168,218,0.8)"][i]} />
          <Sticker t={t} at={s.at + 9} x={s.x + LABEL[i][0]} y={s.y + LABEL[i][1]} rotate={s.r * -2} border={8}>
            <Label text={s.label} family={SANS} size={32} bg={s.bg} />
          </Sticker>
        </React.Fragment>
      ))}

      {/* the team behind it */}
      {HEADS.map((h, i) => (
        <Sticker key={h} t={t} at={160 + i * 7} x={160 + i * 118} y={770} rotate={(i % 2 ? 4 : -4) + i} border={8}>
          <Img src={staticFile(h)} style={{ width: 118, height: 118, borderRadius: 24, display: "block", objectFit: "cover" }} />
        </Sticker>
      ))}
      <Doodle t={t} at={202} dur={12} d="M 330 960 C 300 920 290 890 300 850" head width={6} />
      {t >= 206 && (
        <div style={{ position: "absolute", left: 350, top: 918, fontFamily: HAND, fontWeight: 700, fontSize: 54, color: INK, transform: `rotate(-3deg)`, opacity: Math.min(1, (t - 206) / 8) }}>
          your AI expert team
        </div>
      )}

      {/* the count, from the official line: websites, slides, spreadsheets, reports */}
      <Sticker t={t} at={232} x={1400} y={600} rotate={-8} border={12} lift={14}>
        <div style={{ width: 230, height: 230, borderRadius: "50%", background: "#FFD15C", display: "grid", placeItems: "center", textAlign: "center", color: INK, boxShadow: "inset 0 -10px 0 rgba(0,0,0,0.06)" }}>
          <div>
            <div style={{ fontFamily: SLAB, fontWeight: 800, fontSize: 118, lineHeight: 0.9, fontSynthesis: "none" }}>4</div>
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 24, letterSpacing: "0.04em" }}>KINDS OF WORK</div>
          </div>
        </div>
      </Sticker>
    </AbsoluteFill>
  );
};
