import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../theme";

/** Placeholder product UI drawn in code, used when no screenshot is supplied. */
export const MockUI: React.FC<{ scale: number; compact?: boolean }> = ({ scale: s, compact }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const light = theme.light;
  const card = light ? "#FFFFFF" : "rgba(255,255,255,0.06)";
  const line = light ? "#E7E2D9" : "rgba(255,255,255,0.10)";
  const bars = [0.42, 0.66, 0.5, 0.82, 0.61, 0.95, 0.74];
  const grow = (i: number) =>
    spring({ frame: frame - 12 - i * 3, fps, config: { damping: 16, stiffness: 120 } });
  const count = Math.round(
    interpolate(frame, [10, 50], [0, 12840], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  );

  const skel = (w: string, h = 10, c = line) => (
    <div style={{ width: w, height: h * s, borderRadius: 6 * s, background: c }} />
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        background: light ? "#FAF8F4" : theme.bg2,
        fontFamily: theme.bodyFont,
        color: theme.fg,
      }}
    >
      {!compact && (
        <div
          style={{
            width: "18%",
            padding: 20 * s,
            borderRight: `${1 * s}px solid ${line}`,
            display: "flex",
            flexDirection: "column",
            gap: 16 * s,
          }}
        >
          <div style={{ width: 28 * s, height: 28 * s, borderRadius: 8 * s, background: theme.accent }} />
          {[70, 55, 80, 60, 50].map((w, i) => (
            <div key={i} style={{ display: "flex", gap: 8 * s, alignItems: "center" }}>
              <div style={{ width: 14 * s, height: 14 * s, borderRadius: 4 * s, background: i === 1 ? theme.accent : line }} />
              {skel(`${w}%`, 8)}
            </div>
          ))}
        </div>
      )}
      <div style={{ flex: 1, padding: 24 * s, display: "flex", flexDirection: "column", gap: 18 * s }}>
        <div style={{ display: "flex", gap: 16 * s }}>
          {[0, 1, 2].slice(0, compact ? 2 : 3).map((k) => (
            <div
              key={k}
              style={{
                flex: 1,
                padding: 16 * s,
                borderRadius: 14 * s,
                background: card,
                border: `${1 * s}px solid ${line}`,
                display: "flex",
                flexDirection: "column",
                gap: 10 * s,
              }}
            >
              {skel("50%", 8)}
              <div style={{ fontSize: 26 * s, fontWeight: 700, color: k === 0 ? theme.accent : theme.fg }}>
                {k === 0 ? count.toLocaleString("en-US") : k === 1 ? "98.2%" : "4.9"}
              </div>
            </div>
          ))}
        </div>
        <div
          style={{
            flex: 1,
            borderRadius: 14 * s,
            background: card,
            border: `${1 * s}px solid ${line}`,
            padding: 20 * s,
            display: "flex",
            alignItems: "flex-end",
            gap: 14 * s,
          }}
        >
          {bars.map((h, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                height: `${h * 100 * grow(i)}%`,
                borderRadius: 8 * s,
                background:
                  i === 5
                    ? `linear-gradient(180deg, ${theme.accent}, ${theme.accent2})`
                    : light
                      ? "#E3DDD2"
                      : "rgba(255,255,255,0.14)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
