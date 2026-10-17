import React from "react";
import { Atom } from "lucide-react";
import { MODEL_ICONS } from "../op/modelIcons";
import { clamp01, mix } from "./timeline";
import { UI } from "./Composer";

/*
 * YouWare's model menu, rebuilt from the user's 2026-09-29 screenshot (op/ui.tsx ModelMenu): Auto row with its toggle,
 * a divider, then model rows with Lobe icons. Native 228 px wide, rows 38 px, opening above the chip with right edges
 * aligned. GPT rows follow OpenAI's current names (GPT-6.1 Sol, GPT-6 Sol, GPT-6 Astra — developers.openai.com,
 * 2026-09-30); the effort level (Extra High = xhigh, zh-CN 「极高」) rides on the chip. Mirror a fresh screenshot of the
 * live menu before publishing.
 */
export const MENU_ROWS: [string, string][] = [
  ["GPT-6.1 Sol", "openai"],
  ["GPT-6 Sol", "openai"],
  ["GPT-6 Astra", "openai"],
  ["Claude Opus 5.5", "claude"],
  ["Claude Sonnet 5", "claude"],
  ["Gemini 3.8 Flash", "gemini"],
];
export const MENU_N = { w: 228, row0: 53, rowH: 38, h: 53 + 38 * 6 + 8 };

const Icon: React.FC<{ id: string; size?: number }> = ({ id, size = 17 }) => {
  const ic = MODEL_ICONS[id];
  if (!ic) return <div style={{ width: size, height: size }} />;
  return (
    <svg width={size} height={size} viewBox={ic.vb} style={{ flexShrink: 0 }}>
      {ic.d.map((d: string, i: number) => (
        <path key={i} d={d} fillRule="evenodd" style={{ fill: "#111" }} />
      ))}
    </svg>
  );
};

/** Drawn at native size; the caller positions/scales it. `a` open amount, `hoverRow`/`hover` the highlighted row. */
export const ModelMenu: React.FC<{ a: number; hoverRow: number; hover: number }> = ({ a, hoverRow, hover }) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      top: 0,
      width: MENU_N.w,
      height: MENU_N.h,
      borderRadius: 16,
      background: "#FFFFFF",
      border: "1px solid #ECECEC",
      boxShadow: "0 16px 44px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.05)",
      overflow: "hidden",
      fontFamily: UI,
      fontSize: 15,
      color: "#1F1F1F",
      opacity: clamp01(a * 1.25),
      transform: `translateY(${(1 - a) * 10}px) scale(${mix(0.95, 1, a)})`,
      transformOrigin: "100% 100%",
    }}
  >
    <div style={{ position: "absolute", left: 5, top: 5, width: MENU_N.w - 12, height: 36, borderRadius: 10, background: "#F4F4F4", display: "flex", alignItems: "center", gap: 11, padding: "0 12px", boxSizing: "border-box" }}>
      <Atom size={18} strokeWidth={1.6} color="#1A1A1A" />
      <span style={{ flex: 1 }}>Auto</span>
      <div style={{ position: "relative", width: 34, height: 20, borderRadius: 10, background: "#E3E3E3" }}>
        <div style={{ position: "absolute", left: 2, top: 2, width: 16, height: 16, borderRadius: 8, background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.18)" }} />
      </div>
    </div>
    <div style={{ position: "absolute", left: 11, top: 46, width: MENU_N.w - 24, height: 1, background: "#EDEDED" }} />
    {MENU_ROWS.map(([name, icon], i) => (
      <div
        key={name}
        style={{
          position: "absolute",
          left: 5,
          top: MENU_N.row0 + i * MENU_N.rowH,
          width: MENU_N.w - 12,
          height: MENU_N.rowH,
          borderRadius: 10,
          background: `rgba(0,0,0,${i === hoverRow ? 0.05 * hover : 0})`,
          display: "flex",
          alignItems: "center",
          gap: 11,
          padding: "0 12px",
          boxSizing: "border-box",
          whiteSpace: "nowrap",
        }}
      >
        <Icon id={icon} />
        {name}
      </div>
    ))}
  </div>
);
