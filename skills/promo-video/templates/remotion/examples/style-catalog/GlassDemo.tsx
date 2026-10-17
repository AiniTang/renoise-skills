import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Aurora, Bloom, Glass, GlassMark, Thumb } from "../cinematic/glass";
import { step as stepS } from "../cinematic/spring";
import { fam } from "../cinematic/type";

/**
 * 10 · 弥散渐变·玻璃拟态 — "Glass desk": a frosted YouWare prompt bar over a brand-colour aurora; four glass work cards
 * fan out, catch a sheen, fold into one "Launch kit" panel, then a glass mark + slogan. 330 frames.
 */
export const GLASS_LEN = 330;
const SANS = fam("Manrope");
const SLAB = fam("Hepta Slab");
const DISPLAY = fam("Bricolage Grotesque");

const BLOOMS: Bloom[] = [
  { color: "#F36440", x: 360, y: 280, r: 560, speed: 0.011 },
  { color: "#7D6BC1", x: 1520, y: 240, r: 640, speed: 0.009 },
  { color: "#2F6BD8", x: 1320, y: 920, r: 600, speed: 0.012 },
  { color: "#FFB23F", x: 560, y: 980, r: 460, speed: 0.014, ay: 70 },
  { color: "#C98BE8", x: 980, y: 560, r: 300, speed: 0.016, ax: 300 },
];

const PROMPT = "Turn my notes into a launch kit";
const CARDS = [
  { title: "Website", sub: "Landing page", src: "site/capability-websites.png", nat: [2246, 1424] as [number, number], crop: [0.29, 0.17, 0.985, 0.97] as [number, number, number, number], icon: "web" },
  { title: "Slide deck", sub: "Pitch story", src: "site/capability-slide-decks.png", nat: [2534, 1600] as [number, number], crop: [0.41, 0.3, 0.95, 0.82] as [number, number, number, number], icon: "slides" },
  { title: "Spreadsheet", sub: "Budget model", src: "site/capability-spreadsheets.png", nat: [2246, 1424] as [number, number], crop: [0.29, 0.2, 0.96, 0.9] as [number, number, number, number], icon: "sheet" },
  { title: "Report", sub: "Market brief", src: "site/capability-research-reports.png", nat: [2246, 1424] as [number, number], crop: [0.5, 0.2, 0.88, 0.75] as [number, number, number, number], icon: "doc" },
];
const CW = 380;
const CH = 330;
const GAP = 34;
const ROW_Y = 470;
const OUT = { cards: 84, sheen: 150, fold: 198, panel: 206, lock: 246 };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const ease = (v: number) => {
  const k = clamp01(v);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
/** Springs take seconds; our timeline is in frames. */
const step = (frames: number, c: { w: number; z: number }) => stepS(frames / 30, c);
const SOFT = { w: 2 * Math.PI * 2.4, z: 0.62 };
const POP = { w: 2 * Math.PI * 3, z: 0.5 };

const Icon: React.FC<{ kind: string; size?: number }> = ({ kind, size = 30 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    {kind === "web" && (
      <>
        <circle cx={12} cy={12} r={9} />
        <path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18" />
      </>
    )}
    {kind === "slides" && (
      <>
        <rect x={3} y={4} width={18} height={12} rx={2} />
        <path d="M12 16v4M8 20h8" />
      </>
    )}
    {kind === "sheet" && (
      <>
        <rect x={3} y={4} width={18} height={16} rx={2} />
        <path d="M3 10h18M3 15h18M9 4v16" />
      </>
    )}
    {kind === "doc" && (
      <>
        <path d="M6 3h8l4 4v14H6z" />
        <path d="M14 3v4h4M9 12h6M9 16h6" />
      </>
    )}
    {kind === "check" && <path d="M5 12.5l4.2 4.2L19 7" strokeWidth={2.4} />}
    {kind === "send" && <path d="M12 19V5M6 11l6-6 6 6" strokeWidth={2.4} />}
  </svg>
);

const Chip: React.FC<{ children: React.ReactNode; size?: number }> = ({ children, size = 56 }) => (
  <div style={{ width: size, height: size, borderRadius: size / 2, background: "rgba(255,255,255,0.16)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.5)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{children}</div>
);

const PromptBar: React.FC<{ t: number }> = ({ t }) => {
  const inK = step(t - 10, SOFT);
  const typed = PROMPT.slice(0, Math.floor(clamp01((t - 26) / 36) * PROMPT.length));
  const press = t >= 66 && t < 74 ? 1 - Math.sin(((t - 66) / 8) * Math.PI) * 0.08 : 1;
  // after sending, the bar rises and shrinks to the top
  const up = ease((t - 72) / 22);
  const w = 1040 - 300 * up;
  const y = 470 + (1 - inK) * 70 - 330 * up;
  const fade = 1 - clamp01((t - OUT.fold) / 16);
  return (
    <Glass x={960 - w / 2} y={y} w={w} h={112 - 22 * up} radius={60} opacity={clamp01(inK * 1.4) * fade} transform={`scale(${press})`}>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", padding: "0 18px 0 40px", gap: 20, fontFamily: SANS, fontSize: 38 - 8 * up, fontWeight: 600, color: "#fff" }}>
        <span style={{ flex: 1, whiteSpace: "nowrap", overflow: "hidden" }}>
          {typed || <span style={{ opacity: 0.6 }}>Ask YouWare anything…</span>}
          {t < 66 && typed && <span style={{ display: "inline-block", width: 3, height: 40, marginLeft: 4, verticalAlign: -6, background: "#fff", opacity: Math.floor(t / 7) % 2 ? 0.2 : 1 }} />}
        </span>
        <div style={{ width: 76 - 16 * up, height: 76 - 16 * up, borderRadius: 40, background: "#F36440", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 24px rgba(243,100,64,0.45)" }}>
          <Icon kind="send" size={34 - 6 * up} />
        </div>
      </div>
    </Glass>
  );
};

const Card: React.FC<{ t: number; i: number }> = ({ t, i }) => {
  const c = CARDS[i];
  const k = step(t - OUT.cards - i * 7, POP);
  const x1 = 960 - (4 * CW + 3 * GAP) / 2 + i * (CW + GAP);
  const x0 = 960 - CW / 2;
  const drift = Math.sin(t * 0.045 + i * 1.4) * 9;
  const fold = ease((t - OUT.fold - i * 2) / 20);
  const x = x0 + (x1 - x0) * k + (x0 - x1) * fold;
  const y = 260 + (ROW_Y - 260) * k + drift * (1 - fold) + (340 - ROW_Y) * fold * 0.6;
  const s = (0.55 + 0.45 * k) * (1 - 0.35 * fold);
  const rot = (1 - k) * (i - 1.5) * -6 + (i - 1.5) * 1.2 * (1 - fold);
  const sheen = clamp01((t - OUT.sheen - i * 6) / 26);
  const op = clamp01(k * 2) * (1 - clamp01((t - OUT.fold - 6) / 12));
  if (op <= 0) return null;
  return (
    <Glass x={x} y={y} w={CW} h={CH} radius={34} opacity={op} sheen={sheen} transform={`scale(${s}) rotate(${rot}deg)`}>
      <div style={{ position: "absolute", left: 24, right: 24, top: 22, display: "flex", alignItems: "center", gap: 16 }}>
        <Chip size={54}>
          <Icon kind={c.icon} size={28} />
        </Chip>
        <div style={{ fontFamily: SANS, color: "#fff" }}>
          <div style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.1 }}>{c.title}</div>
          <div style={{ fontSize: 20, fontWeight: 500, opacity: 0.72, marginTop: 4 }}>{c.sub}</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 24, top: 106 }}>
        <Thumb src={c.src} nat={c.nat} crop={c.crop} w={CW - 48} h={CH - 130} radius={18} style={{ boxShadow: "0 10px 30px rgba(8,4,30,0.3)", opacity: 0.95 }} />
      </div>
    </Glass>
  );
};

const Panel: React.FC<{ t: number }> = ({ t }) => {
  const k = step(t - OUT.panel, SOFT);
  const out = ease((t - OUT.lock) / 16);
  if (k <= 0.001) return null;
  const W = 640;
  const H = 520;
  return (
    <Glass x={960 - W / 2} y={280 - (1 - k) * 30} w={W} h={H} radius={44} opacity={clamp01(k * 1.5) * (1 - out)} transform={`scale(${0.9 + 0.1 * k + out * 0.06})`} sheen={clamp01((t - OUT.panel - 10) / 30)}>
      <div style={{ position: "absolute", left: 44, right: 44, top: 38, fontFamily: SANS, color: "#fff" }}>
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "0.14em", opacity: 0.7 }}>YOUWARE</div>
        <div style={{ fontFamily: SLAB, fontSize: 52, fontWeight: 500, marginTop: 8, letterSpacing: "-0.01em" }}>Launch kit</div>
        <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 14 }}>
          {CARDS.map((c, i) => {
            const on = step(t - OUT.panel - 8 - i * 6, POP);
            return (
              <div key={c.title} style={{ display: "flex", alignItems: "center", gap: 18, padding: "12px 16px", borderRadius: 20, background: "rgba(255,255,255,0.1)", opacity: clamp01(on * 2), transform: `translateX(${(1 - on) * 30}px)` }}>
                <Chip size={46}>
                  <Icon kind={c.icon} size={24} />
                </Chip>
                <span style={{ flex: 1, fontSize: 30, fontWeight: 600 }}>{c.title}</span>
                <div style={{ width: 40, height: 40, borderRadius: 20, background: "#3FBF7F", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${on})` }}>
                  <Icon kind="check" size={24} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Glass>
  );
};

const Orbs: React.FC<{ t: number }> = ({ t }) => (
  <>
    {[
      { x: 250, y: 820, r: 90, sp: 0.02 },
      { x: 1690, y: 210, r: 120, sp: 0.016 },
      { x: 1540, y: 880, r: 60, sp: 0.025 },
    ].map((o, i) => {
      const x = o.x + Math.sin(t * o.sp + i) * 40;
      const y = o.y + Math.cos(t * o.sp * 1.2 + i) * 30;
      return <Glass key={i} x={x - o.r} y={y - o.r} w={o.r * 2} h={o.r * 2} radius={o.r} blur={16} opacity={clamp01((t - 6 - i * 6) / 20)} style={{ boxShadow: "inset 0 2px 0 rgba(255,255,255,0.55), inset 0 -8px 20px rgba(255,255,255,0.12), 0 30px 60px rgba(8,4,30,0.25)" }} />;
    })}
  </>
);

export const GlassDemo: React.FC = () => {
  const t = useCurrentFrame();
  const lk = step(t - OUT.lock - 4, SOFT);
  const word = clamp01((t - OUT.lock - 18) / 14);
  const sub = clamp01((t - OUT.lock - 28) / 16);
  return (
    <AbsoluteFill style={{ background: "#150F2E", overflow: "hidden" }}>
      <Aurora t={t + 40} blooms={BLOOMS} base="#110B26" />
      <Orbs t={t} />
      <PromptBar t={t} />
      {CARDS.map((_, i) => (
        <Card key={i} t={t} i={i} />
      ))}
      <Panel t={t} />
      {lk > 0.001 && <GlassMark src="brand/mark.svg" x={960} y={400} size={300} opacity={clamp01(lk * 1.6)} transform={`scale(${0.8 + 0.2 * lk}) rotate(${(1 - lk) * -20}deg)`} />}
      <div style={{ position: "absolute", left: 0, right: 0, top: 590 + (1 - word) * 16, textAlign: "center", opacity: word, fontFamily: DISPLAY, fontWeight: 700, fontSize: 104, color: "#fff", letterSpacing: "-0.02em" }}>YouWare</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 730 + (1 - sub) * 14, textAlign: "center", opacity: sub * 0.92, fontFamily: SLAB, fontWeight: 400, fontSize: 48, color: "#fff" }}>From answers to outcomes.</div>
      <AbsoluteFill style={{ background: "#150F2E", opacity: 1 - clamp01(t / 14), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
