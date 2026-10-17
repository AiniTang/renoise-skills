import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme, useUnit } from "../theme";

export const Caption: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { theme } = useTheme();
  const { u, portrait } = useUnit();
  const opacity = interpolate(
    frame,
    [6, 14, durationInFrames - 12, durationInFrames - 4],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: (portrait ? 260 : 70) * u,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          maxWidth: "80%",
          padding: `${10 * u}px ${22 * u}px`,
          borderRadius: 10 * u,
          background: "rgba(0,0,0,0.55)",
          color: "#fff",
          fontFamily: theme.bodyFont,
          fontSize: 34 * u,
          lineHeight: 1.4,
          textAlign: "center",
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
