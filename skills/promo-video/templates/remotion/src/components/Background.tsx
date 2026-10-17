import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "../theme";
import { Layer } from "./Camera";

const Grain: React.FC<{ opacity: number }> = ({ opacity }) => (
  <AbsoluteFill style={{ opacity, mixBlendMode: "overlay" }}>
    <svg width="100%" height="100%">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  </AbsoluteFill>
);

export const Background: React.FC = () => {
  const { theme } = useTheme();
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;

  if (theme.id === "kinetic") {
    const cell = Math.round(Math.min(width, height) / 9);
    const offset = (t * 40) % cell;
    return (
      <AbsoluteFill style={{ background: theme.bg }}>
        <Layer depth={0.3}>
          <AbsoluteFill
            style={{
              backgroundImage: `linear-gradient(${theme.border} 1px, transparent 1px), linear-gradient(90deg, ${theme.border} 1px, transparent 1px)`,
              backgroundSize: `${cell}px ${cell}px`,
              backgroundPosition: `${offset}px ${offset}px`,
              opacity: 0.5,
              maskImage:
                "radial-gradient(ellipse at center, black 30%, transparent 75%)",
            }}
          />
        </Layer>
        <Grain opacity={0.12} />
      </AbsoluteFill>
    );
  }

  if (theme.id === "aurora") {
    const blob = (
      color: string,
      x: number,
      y: number,
      r: number,
      phase: number,
    ) => (
      <div
        style={{
          position: "absolute",
          left: `${x + Math.sin(t * 0.5 + phase) * 8}%`,
          top: `${y + Math.cos(t * 0.4 + phase) * 8}%`,
          width: `${r}%`,
          aspectRatio: "1",
          borderRadius: "50%",
          background: color,
          filter: `blur(${Math.min(width, height) * 0.12}px)`,
          opacity: 0.42,
          transform: "translate(-50%, -50%)",
        }}
      />
    );
    return (
      <AbsoluteFill style={{ background: theme.bg }}>
        <Layer depth={0.25}>
          {blob(theme.accent, 25, 30, 55, 0)}
          {blob(theme.accent2, 78, 70, 50, 2)}
          {blob(theme.accent, 70, 15, 30, 4)}
        </Layer>
        <Grain opacity={0.1} />
      </AbsoluteFill>
    );
  }

  if (theme.id === "editorial") {
    return (
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 30% 20%, ${theme.bg} 0%, ${theme.bg2} 100%)`,
        }}
      >
        <Grain opacity={0.18} />
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ background: theme.bg }}>
      <Layer depth={0.3}>
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse 60% 50% at 50% ${
              45 + Math.sin(t * 0.6) * 5
            }%, ${theme.accent}22 0%, transparent 70%)`,
          }}
        />
      </Layer>
      <Grain opacity={0.06} />
    </AbsoluteFill>
  );
};
