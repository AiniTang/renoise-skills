import React from "react";
import { ArrowUp, ChevronDown, Plus } from "lucide-react";
import { clamp01, mix } from "./timeline";

/*
 * The YouWare chat input box, rebuilt at its native size (552×118, DM Sans 15 px — from the Opus 5.5 ad's ui.tsx)
 * and drawn at any rect: the native face is scaled by w / 552. The box itself can morph (height, radii, colour) so it
 * can dock into a window banner or become the CTA pill; the face fades before the shape stops being a box.
 */
export const NATIVE = { w: 552, h: 118 };
export const UI = '"DM Sans", -apple-system, "Helvetica Neue", sans-serif';
export const INK = "#151513";
const TEXT = "#1F1F1F";
const LINE = "#E7E7E7";

/** Native chip geometry: right edge 58 px from the box's right, 30 px tall, 14 px from the bottom. */
export const chipBox = (label: string, measure: (s: string) => number) => {
  const w = Math.ceil(measure(label) + 8.4 + 25);
  return { x: NATIVE.w - 58 - w, y: NATIVE.h - 44, w, h: 30 };
};
export const SEND_C = { x: NATIVE.w - 48 + 17, y: NATIVE.h - 46 + 17 };

let ctx: CanvasRenderingContext2D | null = null;
/** Width of chip text (DM Sans 500 13.5 px) in native px; fonts are loaded before the film renders. */
export const measureChip = (s: string) => {
  if (!ctx) ctx = document.createElement("canvas").getContext("2d");
  if (!ctx) return s.length * 7.4;
  ctx.font = `500 13.5px "DM Sans"`;
  return ctx.measureText(s).width;
};

export type ChipState = { from: string; to?: string; roll?: number; hot?: number; pressed?: number; opacity?: number; textOpacity?: number };

const Chip: React.FC<ChipState> = ({ from, to, roll = 0, hot = 0, pressed = 0, opacity = 1, textOpacity = 1 }) => {
  const a = chipBox(from, measureChip);
  const b = to ? chipBox(to, measureChip) : a;
  const w = mix(a.w, b.w, clamp01(roll * 1.4));
  const label: React.CSSProperties = { position: "absolute", right: 25, top: 0, height: 30, display: "flex", alignItems: "center", whiteSpace: "nowrap", fontSize: 13.5, fontWeight: 500, color: TEXT };
  return (
    <div style={{ position: "absolute", right: 58, top: a.y, width: w, height: 30, borderRadius: 9, opacity, transform: `scale(${1 + 0.05 * hot})`, transformOrigin: "100% 50%", boxShadow: hot > 0.01 ? `0 0 0 ${2 + 3 * hot}px rgba(255,208,95,${0.55 * hot})` : undefined }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: 9, background: "rgba(0,0,0,0.065)", opacity: pressed }} />
      <div style={{ position: "absolute", inset: 0, borderRadius: 9, background: "rgba(255,208,95,0.5)", opacity: hot }} />
      <span style={{ ...label, opacity: (1 - clamp01(roll / 0.45)) * textOpacity, transform: `translateY(${-8 * roll}px)` }}>{from}</span>
      {to && <span style={{ ...label, opacity: clamp01((roll - 0.45) / 0.5) * textOpacity, transform: `translateY(${8 * (1 - roll)}px)` }}>{to}</span>}
      <ChevronDown size={14} strokeWidth={1.75} color={TEXT} style={{ position: "absolute", right: 7, top: 8 }} />
    </div>
  );
};

export type Face = {
  text: string;
  caret?: boolean;
  placeholder?: string;
  placeholderColor?: string;
  fontSize?: number; // native px (YouWare: 15)
  chip: ChipState;
  sendOn?: number; // 0 grey, 1 ink
  press?: number;
  working?: number; // 0..1: the send button becomes a stop square while the chat works
};

export const ComposerFace: React.FC<Face> = ({ text, caret, placeholder = "Chat with YouWare", placeholderColor = "#B5B5B5", fontSize = 15, chip, sendOn = 1, press = 0, working = 0 }) => {
  const caretH = fontSize * 1.2;
  return (
    <>
      <div style={{ position: "absolute", left: 20, top: 16, right: 20, fontFamily: UI, fontSize, lineHeight: 1.5, color: TEXT, whiteSpace: "nowrap" }}>
        {text.length === 0 ? (
          <>
            <span style={{ color: placeholderColor }}>{placeholder}</span>
            {caret && <span style={{ position: "absolute", left: 0, top: fontSize * 0.15, width: 1.6, height: caretH, background: INK }} />}
          </>
        ) : (
          <span>
            {text}
            {caret && <span style={{ display: "inline-block", width: 1.6, height: caretH, background: INK, marginLeft: 1, verticalAlign: -fontSize * 0.2 }} />}
          </span>
        )}
      </div>
      {/* centred on the chip / send row (y 89 native) */}
      <Plus size={20} strokeWidth={1.75} color="#555" style={{ position: "absolute", left: 18, top: 79 }} />
      <div style={{ fontFamily: UI }}>
        <Chip {...chip} />
      </div>
      <div style={{ position: "absolute", right: 14, bottom: 12, width: 34, height: 34, borderRadius: 17, background: sendOn > 0.5 || working > 0 ? INK : "#D5D5D5", display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${1 - 0.12 * press})` }}>
        <ArrowUp size={18} strokeWidth={2.2} color="#fff" style={{ position: "absolute", opacity: 1 - working, transform: `scale(${1 - 0.4 * working})` }} />
        <div style={{ position: "absolute", width: 11, height: 11, borderRadius: 2.5, background: "#fff", opacity: working, transform: `scale(${0.6 + 0.4 * working})` }} />
      </div>
    </>
  );
};

export type BoxShape = {
  x: number;
  y: number;
  w: number;
  h?: number; // defaults to the native aspect
  r?: string; // CSS border-radius (screen px)
  bg?: string;
  border?: number; // hairline opacity
  shadow?: number; // 0..1
  faceOpacity?: number;
  opacity?: number;
  scale?: number; // extra scale about the centre (press / breathe)
};

/** The box at a screen rect. The face is laid out at native size and scaled by w / 552. */
export const Composer: React.FC<BoxShape & { face?: Face; children?: React.ReactNode }> = ({ x, y, w, h, r, bg = "#FFFFFF", border = 1, shadow = 1, faceOpacity = 1, opacity = 1, scale = 1, face, children }) => {
  const s = w / NATIVE.w;
  const H = h ?? NATIVE.h * s;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: H,
        borderRadius: r ?? `${20 * s}px`,
        background: bg,
        boxShadow: `0 0 0 1px rgba(231,231,231,${border}), 0 ${6 * s}px ${24 * s}px rgba(60,40,0,${0.07 * shadow})`,
        opacity,
        transform: scale !== 1 ? `scale(${scale})` : undefined,
        overflow: "hidden",
      }}
    >
      {face && faceOpacity > 0.001 && (
        <div style={{ position: "absolute", left: 0, top: 0, width: NATIVE.w, height: NATIVE.h, transform: `scale(${s})`, transformOrigin: "0 0", opacity: faceOpacity }}>
          <ComposerFace {...face} />
        </div>
      )}
      {children}
    </div>
  );
};

export { LINE };
