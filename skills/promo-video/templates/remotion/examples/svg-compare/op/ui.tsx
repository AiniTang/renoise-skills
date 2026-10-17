import React from "react";
import { ArrowUp, Atom, Check, ChevronDown, ChevronRight, Download, Maximize, Maximize2, MoreHorizontal, PanelLeft, PanelRight, Play, Plus, UserPlus, Video, Volume2, X } from "lucide-react";
import { C, CHIP, CHIP_AUTO_W, clamp01, DL, INPUT, MENU, mix, MODELS, PLAYER, SECTIONS, SEC_COLORS, SEND, UI, WIN } from "./theme";
import { MODEL_ICONS } from "./modelIcons";

const abs = (x: number, y: number, w?: number, h?: number): React.CSSProperties => ({ position: "absolute", left: x, top: y, width: w, height: h });

/* ── window chrome (world coordinates) ─────────────────────────────────────── */
export const WindowFrame: React.FC<{ title: string; tab: number; children?: React.ReactNode }> = ({ title, tab, children }) => (
  <div style={{ ...abs(WIN.x, WIN.y, WIN.w, WIN.h), borderRadius: 18, background: C.win, overflow: "hidden", boxShadow: "0 2px 6px rgba(60,40,0,0.06), 0 30px 80px rgba(60,40,0,0.16)", fontFamily: UI, color: C.text }}>
    <div style={{ ...abs(0, 0, WIN.w, 20), background: C.banner }} />
    {/* chat header */}
    <div style={{ ...abs(0, 20, WIN.chat, 52), display: "flex", alignItems: "center", gap: 14, padding: "0 22px", boxSizing: "border-box" }}>
      <PanelLeft size={19} strokeWidth={1.75} color="#555" />
      <div style={{ flex: 1, fontSize: 15.5, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{title}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, color: "#444" }}>
        <UserPlus size={16} strokeWidth={1.75} /> Invite
      </div>
      <MoreHorizontal size={18} strokeWidth={1.75} color="#666" />
    </div>
    {/* panel header */}
    <div style={{ ...abs(WIN.chat, 20, WIN.w - WIN.chat, 52), display: "flex", alignItems: "center", padding: "0 20px", boxSizing: "border-box", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, padding: "6px 12px", borderRadius: 10, background: "rgba(0,0,0,0.04)", opacity: tab, transform: `translateY(${(1 - tab) * 8}px)` }}>
        <Video size={16} strokeWidth={1.75} /> motion_reel.mp4 <X size={14} strokeWidth={1.75} color="#888" />
      </div>
      <div style={{ flex: 1 }} />
      <Maximize2 size={17} strokeWidth={1.75} color="#666" />
      <PanelRight size={18} strokeWidth={1.75} color="#666" style={{ marginLeft: 14 }} />
    </div>
    <div style={{ ...abs(WIN.chat, 72, 1, WIN.h - 72), background: C.line }} />
    <div style={{ ...abs(WIN.chat + 1, 72, WIN.w - WIN.chat - 1, WIN.h - 72), background: C.panel }} />
    <div style={{ ...abs(-WIN.x, -WIN.y, 1920, 1080) }}>{children}</div>
  </div>
);

export const PathBar: React.FC<{ a: number }> = ({ a }) => (
  <div style={{ ...abs(WIN.x + WIN.chat + 20, WIN.y + 84, WIN.w - WIN.chat - 140, 30), borderRadius: 999, background: "rgba(0,0,0,0.035)", display: "flex", alignItems: "center", padding: "0 14px", fontFamily: UI, fontSize: 12.5, color: "#8A8A8A", opacity: a }}>
    /artifacts/motion_reel.mp4
  </div>
);

export const DownloadButton: React.FC<{ a: number; hot: number; press: number }> = ({ a, hot, press }) => (
  <>
    <div style={{ ...abs(DL.x, DL.y, DL.w, DL.h), display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 8, background: `rgba(255,208,95,${0.55 * hot})`, transform: `scale(${1 - 0.1 * press})`, opacity: a }}>
      <Download size={17} strokeWidth={1.9} color="#333" />
    </div>
    <div style={{ ...abs(DL.x + 34, DL.y + 6, 30, 18), borderRadius: 5, background: C.yellow, fontFamily: UI, fontSize: 10.5, fontWeight: 700, color: "#6B4B00", display: "flex", alignItems: "center", justifyContent: "center", opacity: a }}>Pro</div>
  </>
);

/* ── chat column ─────────────────────────────────────────────────────────────── */
export const UserBubble: React.FC<{ a: number; dy: number }> = ({ a, dy }) => (
  <div style={{ position: "absolute", left: WIN.x + 110, top: WIN.y + 96 + dy, width: 460, padding: "14px 18px", boxSizing: "border-box", borderRadius: 18, background: C.bubble, fontFamily: UI, fontSize: 15, lineHeight: 1.5, color: C.text, opacity: a }}>
    Make a dynamic 15-second motion graphics video that shows what an incredible motion designer you are.
  </div>
);

export const WorkLine: React.FC<{ t: number; t0: number; done: number; a: number }> = ({ t, t0, done, a }) => {
  // time-lapse: the real "Worked for 46m 8s", counted up fast
  const total = 46 * 60 + 8;
  const p = clamp01((t - t0) / 4.6);
  const secs = Math.round(total * (1 - Math.pow(1 - p, 1.6)));
  const mm = Math.floor(secs / 60);
  const ss = secs % 60;
  const spin = (t * 360) % 360;
  return (
    <div style={{ position: "absolute", left: WIN.x + 26, top: WIN.y + 196, display: "flex", alignItems: "center", gap: 8, fontFamily: UI, fontSize: 14, color: "#8F8F8F", opacity: a }}>
      {done < 1 ? (
        <>
          <div style={{ width: 13, height: 13, borderRadius: 7, border: "2px solid #D6D6D6", borderTopColor: C.ink, transform: `rotate(${spin}deg)` }} />
          <span style={{ color: "#555" }}>Working</span>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>{mm}m {String(ss).padStart(2, "0")}s</span>
        </>
      ) : (
        <>
          Worked for 46m 8s <ChevronRight size={14} strokeWidth={1.75} />
        </>
      )}
    </div>
  );
};

const INTRO_H = 92 + 6 + 14.5 * 1.55 + 10;

/** The agent's reply (text from the recording, lightly shortened). */
export const AgentMessage: React.FC<{ intro: number; items: number[]; active: number; hl: number }> = ({ intro, items, active, hl }) => (
  <div style={{ position: "absolute", left: WIN.x + 26, top: WIN.y + 232, width: 548, fontFamily: UI, fontSize: 14.5, lineHeight: 1.55, color: C.body }}>
    {/* the reply's intro opens above the list when the work is done (no reserved gap while working) */}
    <div style={{ height: INTRO_H * intro, overflow: "hidden" }}>
      <div style={{ opacity: clamp01(intro * 1.4 - 0.4), transform: `translateY(${(1 - intro) * 8}px)` }}>
        <div style={{ height: 92 }}>
          Your video is ready: <b style={{ fontWeight: 600 }}>motion_reel.mp4</b> runs exactly 15 seconds at 1920×1080 and 60 fps, with a stereo soundtrack. I rendered every frame in code and checked sample frames from the final file.
        </div>
        <div style={{ paddingTop: 6, paddingBottom: 10 }}>It’s cut to a 120 BPM beat; each section shows off a different motion-design skill:</div>
      </div>
    </div>
    {SECTIONS.map((s, i) => {
      const e = items[i];
      const on = i === active ? hl : 0;
      return (
        <div key={s.name} style={{ position: "relative", padding: "5px 10px", margin: "0 -10px 2px", borderRadius: 10, background: `rgba(255,208,95,${0.32 * on})`, opacity: e, transform: `translateX(${(1 - e) * 14}px)` }}>
          <span style={{ fontWeight: 600, color: C.text }}>
            {i + 1}. {s.name} ({s.t0}–{s.t1}s):
          </span>{" "}
          {s.line}
          {e >= 1 && on < 0.5 && i < 7 && <Check size={14} strokeWidth={2.2} color="#7D8F57" style={{ position: "absolute", right: -6, top: 9, opacity: e }} />}
        </div>
      );
    })}
  </div>
);

/* ── the input box ───────────────────────────────────────────────────────────── */
type Face = { text: string; caret: boolean; chipHot: number; sendOn: number; press: number; placeholder?: number; model?: number; chipOpen?: number };

/** The model chip: "Auto" (model 0) → "Claude Opus 5.5" (model 1); right edge fixed next to the send button. */
const ModelChip: React.FC<{ model: number; chipHot: number; chipOpen: number }> = ({ model, chipHot, chipOpen }) => {
  const right = INPUT.x + INPUT.w - CHIP.x - CHIP.w;
  const bottom = INPUT.y + INPUT.h - CHIP.y - CHIP.h;
  const glow = chipHot > 0.01 ? `0 0 0 ${2 + 3 * chipHot}px rgba(255,208,95,${0.55 * chipHot})` : undefined;
  if (model >= 1 && chipOpen <= 0)
    return (
      <div style={{ position: "absolute", right, bottom, height: CHIP.h, width: CHIP.w, borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, fontSize: 13.5, fontWeight: 500, color: C.text, background: `rgba(255,208,95,${0.5 * chipHot})`, boxShadow: glow, transform: `scale(${1 + 0.05 * chipHot})` }}>
        Claude Opus 5.5 <ChevronDown size={14} strokeWidth={1.75} />
      </div>
    );
  const label: React.CSSProperties = { position: "absolute", right: 25, top: 0, height: CHIP.h, display: "flex", alignItems: "center", whiteSpace: "nowrap", fontSize: 13.5, fontWeight: 500, color: C.text };
  return (
    // the chip reaches full width before the Opus label shows, so the label is never clipped
    <div style={{ position: "absolute", right, bottom, height: CHIP.h, width: mix(CHIP_AUTO_W, CHIP.w, clamp01(model / 0.6)), borderRadius: 9, boxShadow: glow, transform: `scale(${1 + 0.05 * chipHot})` }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 9, background: "rgba(0,0,0,0.065)", opacity: chipOpen }} />
      <div style={{ position: "absolute", inset: 0, borderRadius: 9, background: "rgba(255,208,95,0.5)", opacity: chipHot }} />
      <span style={{ ...label, opacity: 1 - clamp01(model / 0.4), transform: `translateY(${-7 * model}px)` }}>Auto</span>
      <span style={{ ...label, opacity: clamp01((model - 0.5) / 0.5), transform: `translateY(${7 * (1 - model)}px)` }}>Claude Opus 5.5</span>
      <ChevronDown size={14} strokeWidth={1.75} color={C.text} style={{ position: "absolute", right: 7, top: 8 }} />
    </div>
  );
};

/** The inside of the input box, anchored to the box edges (the end-card morph reuses it). */
export const InputFace: React.FC<Face> = ({ text, caret, chipHot, sendOn, press, placeholder = 1, model = 1, chipOpen = 0 }) => (
  <>
    <div style={{ position: "absolute", left: 20, top: 16, right: 20, fontSize: 15, lineHeight: 1.5, color: C.text }}>
      {text.length === 0 ? (
        <span style={{ color: "#B5B5B5", opacity: placeholder }}>Chat with YouWare</span>
      ) : (
        <span>
          {text}
          {caret && <span style={{ display: "inline-block", width: 1.6, height: 18, background: C.ink, marginLeft: 1, verticalAlign: -3 }} />}
        </span>
      )}
      {text.length === 0 && caret && <span style={{ position: "absolute", left: 0, top: 2, width: 1.6, height: 18, background: C.ink }} />}
    </div>
    <Plus size={20} strokeWidth={1.75} color="#555" style={{ position: "absolute", left: 18, bottom: 14 }} />
    <ModelChip model={model} chipHot={chipHot} chipOpen={chipOpen} />
    <div style={{ position: "absolute", right: INPUT.x + INPUT.w - SEND.x - SEND.w, bottom: INPUT.y + INPUT.h - SEND.y - SEND.h, width: SEND.w, height: SEND.h, borderRadius: 17, background: sendOn > 0.5 ? C.ink : "#D5D5D5", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${1 - 0.12 * press})` }}>
      <ArrowUp size={18} strokeWidth={2.2} color="#fff" />
    </div>
  </>
);

export const ChatInput: React.FC<Face & { a?: number }> = ({ a = 1, ...face }) => (
  <div style={{ ...abs(INPUT.x, INPUT.y, INPUT.w, INPUT.h), borderRadius: 20, background: "#FFFFFF", border: `1px solid ${C.line}`, boxShadow: "0 6px 24px rgba(0,0,0,0.05)", fontFamily: UI, opacity: a }}>
    <InputFace {...face} />
  </div>
);

/* ── the model menu (from the user's screenshot of YouWare) ─────────────────── */
const ModelIcon: React.FC<{ id: string; size?: number }> = ({ id, size = 17 }) => {
  const ic = MODEL_ICONS[id];
  return (
    <svg width={size} height={size} viewBox={ic.vb} style={{ flexShrink: 0 }}>
      {ic.d.map((d, i) => (
        <path key={i} d={d} fillRule="evenodd" style={{ fill: "#111" }} />
      ))}
    </svg>
  );
};

/** a: open amount; hover: the row under the cursor (-1 none) and its highlight amount. */
export const ModelMenu: React.FC<{ a: number; hoverRow: number; hover: number }> = ({ a, hoverRow, hover }) => (
  <div style={{ ...abs(MENU.x, MENU.y, MENU.w, MENU.h), borderRadius: 16, background: "#FFFFFF", border: "1px solid #ECECEC", boxShadow: "0 16px 44px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.05)", overflow: "hidden", fontFamily: UI, fontSize: 15, color: C.text, opacity: clamp01(a * 1.25), transform: `translateY(${(1 - a) * 10}px) scale(${mix(0.95, 1, a)})`, transformOrigin: "100% 100%" }}>
    <div style={{ ...abs(5, 5, MENU.w - 12, 36), borderRadius: 10, background: "#F4F4F4", display: "flex", alignItems: "center", gap: 11, padding: "0 12px", boxSizing: "border-box" }}>
      <Atom size={18} strokeWidth={1.6} color="#1A1A1A" />
      <span style={{ flex: 1 }}>Auto</span>
      <div style={{ position: "relative", width: 34, height: 20, borderRadius: 10, background: "#E3E3E3" }}>
        <div style={{ position: "absolute", left: 2, top: 2, width: 16, height: 16, borderRadius: 8, background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.18)" }} />
      </div>
    </div>
    <div style={{ ...abs(11, 46, MENU.w - 24, 1), background: "#EDEDED" }} />
    {MODELS.map(([name, icon], i) => (
      <div key={name} style={{ ...abs(5, MENU.row0 + i * MENU.rowH, MENU.w - 12, MENU.rowH), borderRadius: 10, background: `rgba(0,0,0,${i === hoverRow ? 0.045 * hover : 0})`, display: "flex", alignItems: "center", gap: 11, padding: "0 12px", boxSizing: "border-box", whiteSpace: "nowrap" }}>
        <ModelIcon id={icon} />
        {name}
      </div>
    ))}
  </div>
);

/* ── the player (right panel) ────────────────────────────────────────────────── */
export const PlayerChrome: React.FC<{ reelT: number; a: number; playing: boolean }> = ({ reelT, a, playing }) => {
  const p = clamp01(reelT / 15);
  const sec = Math.floor(Math.max(0, reelT));
  return (
    // tall enough to cover the recorded player's own controls and the recorder's hand cursor (bottom 180 px of the source)
    <div style={{ ...abs(PLAYER.x, PLAYER.y + PLAYER.h - 110, PLAYER.w, 110), opacity: a, pointerEvents: "none" }}>
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.3) 24%, rgba(0,0,0,0.88) 42%, #000 52%)" }} />
      <div style={{ position: "absolute", left: 18, right: 18, bottom: 40, height: 3, borderRadius: 2, background: "rgba(255,255,255,0.28)" }}>
        <div style={{ width: `${p * 100}%`, height: "100%", borderRadius: 2, background: "#fff" }} />
      </div>
      <div style={{ position: "absolute", left: 18, bottom: 10, display: "flex", alignItems: "center", gap: 12, fontFamily: UI, fontSize: 13, color: "#fff" }}>
        {playing ? <div style={{ display: "flex", gap: 3 }}><div style={{ width: 3.5, height: 13, background: "#fff", borderRadius: 1 }} /><div style={{ width: 3.5, height: 13, background: "#fff", borderRadius: 1 }} /></div> : <Play size={14} fill="#fff" strokeWidth={0} />}
        <span style={{ fontVariantNumeric: "tabular-nums" }}>0:{String(sec).padStart(2, "0")} / 0:15</span>
      </div>
      <div style={{ position: "absolute", right: 18, bottom: 10, display: "flex", gap: 16 }}>
        <Volume2 size={16} strokeWidth={1.9} color="#fff" />
        <Maximize size={15} strokeWidth={1.9} color="#fff" />
      </div>
    </div>
  );
};

/** The reel's arrangement on a timeline, with a live playhead. */
export const Arrangement: React.FC<{ reelT: number; a: number }> = ({ reelT, a }) => {
  const y = PLAYER.y + PLAYER.h + 22;
  return (
    <div style={{ ...abs(PLAYER.x, y, PLAYER.w, 54), opacity: a, fontFamily: UI }}>
      <div style={{ position: "absolute", left: 0, top: 0, right: 0, height: 34, display: "flex", gap: 4 }}>
        {SECTIONS.map((s, i) => {
          const on = reelT >= s.t0 && reelT < s.t1 ? 1 : 0;
          return (
            <div key={s.name} style={{ flex: s.t1 - s.t0, borderRadius: 8, background: on ? C.ink : "#FFFFFF", border: `1px solid ${on ? C.ink : C.line}`, display: "flex", alignItems: "center", gap: 7, padding: "0 10px", overflow: "hidden", fontSize: 13, fontWeight: 600, color: on ? "#fff" : "#555", whiteSpace: "nowrap" }}>
              <div style={{ width: 8, height: 8, borderRadius: 4, background: SEC_COLORS[i], flexShrink: 0, boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.12)" }} />
              {s.name}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: `${clamp01(reelT / 15) * 100}%`, top: -6, width: 2, height: 46, background: C.coral, borderRadius: 1, boxShadow: "0 0 0 2px rgba(242,107,58,0.18)" }} />
    </div>
  );
};

export const Toast: React.FC<{ a: number }> = ({ a }) => (
  <div style={{ ...abs(WIN.x + WIN.w - 420, WIN.y + 128, 380, 64), borderRadius: 16, background: "#FFFFFF", boxShadow: "0 12px 40px rgba(0,0,0,0.14)", border: `1px solid ${C.line}`, display: "flex", alignItems: "center", gap: 14, padding: "0 18px", boxSizing: "border-box", fontFamily: UI, opacity: a, transform: `translateY(${(1 - a) * -14}px)` }}>
    <div style={{ width: 30, height: 30, borderRadius: 15, background: "#EAF3DE", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Check size={17} strokeWidth={2.4} color="#5E7A2E" />
    </div>
    <div>
      <div style={{ fontSize: 15, fontWeight: 600, color: C.text }}>Downloaded</div>
      <div style={{ fontSize: 13, color: C.grey }}>motion_reel.mp4 · 15 s · 1080p · 60 fps</div>
    </div>
  </div>
);

export const Cursor: React.FC<{ x: number; y: number; press: number; a: number; scale?: number }> = ({ x, y, press, a, scale = 1 }) => (
  <svg width={34} height={34} viewBox="0 0 24 24" style={{ position: "absolute", left: x - 5 * scale, top: y - 3 * scale, opacity: a, transform: `scale(${scale * (1 - 0.1 * press)})`, transformOrigin: "5px 3px", filter: "drop-shadow(0 3px 6px rgba(0,0,0,0.35))", zIndex: 50 }}>
    <path d="M5 3 L19 12.5 L12.4 13.9 L16.1 21 L13.3 22.4 L9.6 15.3 L5 19.6 Z" style={{ fill: "#111", stroke: "#fff", strokeWidth: 1.5, strokeLinejoin: "round" }} />
  </svg>
);

export { mix };
