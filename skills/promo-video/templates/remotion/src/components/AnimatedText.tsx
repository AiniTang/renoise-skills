import React from "react";
import {
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useTheme } from "../theme";

const CJK = "\\u3000-\\u303f\\u3040-\\u30ff\\u3400-\\u9fff\\uff00-\\uffef";
const TOKEN = new RegExp(`[${CJK}]|[^\\s${CJK}]+|\\s+`, "g");

type Token = { text: string; start: number; space: boolean };

const tokenize = (line: string, offset: number): Token[] => {
  const out: Token[] = [];
  for (const m of line.matchAll(TOKEN)) {
    out.push({
      text: m[0],
      start: offset + (m.index ?? 0),
      space: /^\s+$/.test(m[0]),
    });
  }
  return out;
};

export const AnimatedText: React.FC<{
  text: string;
  highlight?: string;
  delay?: number;
  maxRevealSeconds?: number;
  style?: React.CSSProperties;
  highlightColor?: string;
}> = ({ text, highlight, delay = 0, maxRevealSeconds = 0.9, style, highlightColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();

  const lines = text.split("\n");
  let offset = 0;
  const tokenLines = lines.map((line) => {
    const t = tokenize(line, offset);
    offset += line.length + 1;
    return t;
  });
  const visible = tokenLines.flat().filter((t) => !t.space).length;
  const stagger = Math.min(theme.stagger, (maxRevealSeconds * fps) / Math.max(1, visible));

  const hStart = highlight ? text.indexOf(highlight) : -1;
  const hEnd = hStart >= 0 ? hStart + (highlight?.length ?? 0) : -1;

  let i = 0;
  const renderToken = (tok: Token, key: number) => {
    if (tok.space) return <span key={key}> </span>;
    const d = delay + i * stagger;
    i += 1;
    const f = frame - d;
    let transform = "none";
    let opacity = 1;
    let filter = "none";
    if (theme.textAnim === "pop") {
      const s = spring({ frame: f, fps, config: { damping: 11, stiffness: 180, mass: 0.6 } });
      opacity = interpolate(f, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      transform = `translateY(${(1 - s) * 0.35}em) scale(${0.5 + 0.5 * s})`;
    } else if (theme.textAnim === "blur") {
      const q = interpolate(f, [0, 16], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      });
      opacity = q;
      filter = `blur(${(1 - q) * 14}px)`;
      transform = `translateY(${(1 - q) * 0.18}em)`;
    } else {
      const s = spring({ frame: f, fps, config: { damping: 200 } });
      opacity = s;
      transform = `translateY(${(1 - s) * 0.5}em)`;
    }
    const hl = hStart >= 0 && tok.start < hEnd && tok.start + tok.text.length > hStart;
    return (
      <span
        key={key}
        style={{
          display: "inline-block",
          whiteSpace: "pre",
          opacity,
          transform,
          filter,
          color: hl ? highlightColor ?? theme.highlight : undefined,
        }}
      >
        {tok.text}
      </span>
    );
  };

  return (
    <div style={style}>
      {tokenLines.map((line, li) => (
        <div key={li}>{line.map((tok, ti) => renderToken(tok, ti))}</div>
      ))}
    </div>
  );
};

/** Simple whole-block entrance for secondary copy. */
export const FadeUp: React.FC<{
  delay?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
  distance?: number;
}> = ({ delay = 0, children, style, distance = 24 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  return (
    <div style={{ opacity: s, transform: `translateY(${(1 - s) * distance}px)`, ...style }}>
      {children}
    </div>
  );
};
