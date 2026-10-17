import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedText, FadeUp } from "../components/AnimatedText";
import { Layer } from "../components/Camera";
import { useTheme, useUnit } from "../theme";
import type { StatsScene } from "../types";

export const Stats: React.FC<{ scene: StatsScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const { u, portrait } = useUnit();
  const start = scene.title ? 10 : 0;
  const items = scene.items.slice(0, 4);

  return (
    <Layer depth={1}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          gap: 80 * u,
          padding: `0 ${120 * u}px`,
        }}
      >
        {scene.title && (
          <AnimatedText
            text={scene.title}
            style={{
              fontFamily: theme.displayFont,
              fontWeight: theme.displayWeight,
              letterSpacing: theme.tracking,
              fontSize: 64 * u,
              color: theme.fg,
              textAlign: "center",
            }}
          />
        )}
        <div
          style={{
            display: "flex",
            flexDirection: portrait ? "column" : "row",
            gap: (portrait ? 70 : 0) * u,
            width: "100%",
            justifyContent: "space-evenly",
          }}
        >
          {items.map((it, i) => {
            const delay = start + i * 5;
            const p = interpolate(frame - delay, [0, fps * 1.3], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const value = (it.value * p).toLocaleString("en-US", {
              minimumFractionDigits: it.decimals ?? 0,
              maximumFractionDigits: it.decimals ?? 0,
            });
            return (
              <FadeUp key={i} delay={delay} style={{ textAlign: "center", flex: 1 }}>
                <div
                  style={{
                    fontFamily: theme.displayFont,
                    fontWeight: theme.displayWeight,
                    letterSpacing: theme.tracking,
                    fontSize: (portrait ? 150 : 150) * u,
                    lineHeight: 1,
                    color: theme.fg,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {it.prefix}
                  {value}
                  <span style={{ color: theme.highlight }}>{it.suffix}</span>
                </div>
                <div
                  style={{
                    marginTop: 20 * u,
                    fontFamily: theme.bodyFont,
                    fontSize: 30 * u,
                    color: theme.muted,
                  }}
                >
                  {it.label}
                </div>
              </FadeUp>
            );
          })}
        </div>
      </AbsoluteFill>
    </Layer>
  );
};
