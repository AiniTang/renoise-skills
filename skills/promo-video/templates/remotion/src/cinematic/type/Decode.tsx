import React from "react";
import { useCurrentFrame } from "remotion";

const GLYPHS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%&*+=<>/";
const h = (n: number) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};
/** Tech / retro: characters scramble (deterministic) and lock in left to right. Use a mono font. */
export const Decode: React.FC<{ text: string; family: string; size: number; at?: number; perChar?: number; settle?: number; color?: string; style?: React.CSSProperties }> = ({ text, family, size, at = 0, perChar = 1.2, settle = 8, color = "currentColor", style }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ fontFamily: family, fontSize: size, color, whiteSpace: "pre", fontVariantNumeric: "tabular-nums", ...style }}>
      {Array.from(text).map((ch, i) => {
        const lock = at + i * perChar + settle;
        if (ch === " " || f >= lock) return <span key={i}>{ch}</span>;
        if (f < at + i * perChar) return <span key={i} style={{ opacity: 0 }}>{ch}</span>;
        return (
          <span key={i} style={{ opacity: 0.55 }}>
            {GLYPHS[Math.floor(h(i * 31 + Math.floor(f / 2)) * GLYPHS.length)]}
          </span>
        );
      })}
    </div>
  );
};
