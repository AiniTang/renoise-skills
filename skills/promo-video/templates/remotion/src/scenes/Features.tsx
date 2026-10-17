import React from "react";
import { evolvePath } from "@remotion/paths";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { AnimatedText } from "../components/AnimatedText";
import { Layer } from "../components/Camera";
import { ICONS } from "../icons";
import { useTheme, useUnit } from "../theme";
import type { FeaturesScene } from "../types";

const DrawIcon: React.FC<{ d: string; size: number; delay: number; color: string }> = ({
  d,
  size,
  delay,
  color,
}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame - delay, [0, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const { strokeDasharray, strokeDashoffset } = evolvePath(p, d);
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d={d}
        stroke={color}
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={strokeDasharray}
        strokeDashoffset={strokeDashoffset}
      />
    </svg>
  );
};

export const Features: React.FC<{ scene: FeaturesScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const { u, portrait } = useUnit();
  const items = scene.items.slice(0, 6);
  const cover = scene.imageStyle === "cover";
  const cols = portrait ? (cover ? 2 : 1) : items.length <= 5 ? items.length : 3;
  const gap = (portrait ? 28 : 32) * u;
  const dense = cols >= 5;
  const pad = (cover || dense ? 28 : portrait ? 34 : 44) * u;
  const start = scene.title ? 10 : 0;
  const row = portrait && !cover;

  return (
    <Layer depth={1}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: `0 ${(portrait ? 110 : 140) * u}px`,
          gap: (portrait ? 50 : 70) * u,
        }}
      >
        {scene.title && (
          <AnimatedText
            text={scene.title}
            style={{
              fontFamily: theme.displayFont,
              fontWeight: theme.displayWeight,
              letterSpacing: theme.tracking,
              fontSize: (portrait ? 72 : 76) * u,
              lineHeight: 1.12,
              color: theme.fg,
              textAlign: "center",
            }}
          />
        )}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap,
            width: "100%",
          }}
        >
          {items.map((it, i) => {
            const delay = start + i * (dense ? 5 : 6);
            const s = spring({ frame: frame - delay, fps, config: { damping: 18, stiffness: 110 } });
            const media = it.image ? (
              <Img
                src={staticFile(it.image)}
                style={
                  cover
                    ? { width: "100%", aspectRatio: String(scene.imageAspect ?? 1.6), objectFit: "contain" }
                    : { width: "100%", height: "100%", objectFit: "contain" }
                }
              />
            ) : (
              <DrawIcon d={ICONS[it.icon ?? "spark"] ?? ICONS.spark} size={50 * u} delay={delay + 4} color={theme.highlight} />
            );
            return (
              <div
                key={i}
                style={{
                  width: `calc((100% - ${gap * (cols - 1)}px) / ${cols})`,
                  opacity: s,
                  transform: `translateY(${(1 - s) * 60 * u}px) scale(${0.94 + 0.06 * s})`,
                  background: theme.surface,
                  border: `${1.5 * u}px solid ${theme.border}`,
                  borderRadius: theme.radius * u,
                  padding: pad,
                  display: "flex",
                  flexDirection: row ? "row" : "column",
                  alignItems: row ? "center" : "flex-start",
                  gap: (cover ? 20 : 24) * u,
                  backdropFilter: theme.id === "aurora" ? `blur(${20 * u}px)` : undefined,
                }}
              >
                {cover && it.image ? (
                  media
                ) : (
                  <div
                    style={{
                      width: (it.image ? 120 : 88) * u,
                      height: (it.image ? 120 : 88) * u,
                      flexShrink: 0,
                      borderRadius: (theme.id === "kinetic" ? 8 : 24) * u,
                      background: it.image ? "transparent" : `${theme.highlight}1F`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {media}
                  </div>
                )}
                <div>
                  <div
                    style={{
                      fontFamily: theme.displayFont,
                      fontWeight: Math.min(800, theme.displayWeight),
                      fontSize: (dense ? 32 : 40) * u,
                      lineHeight: 1.2,
                      letterSpacing: "-0.01em",
                      color: theme.fg,
                    }}
                  >
                    {it.title}
                  </div>
                  {it.body && (
                    <div
                      style={{
                        marginTop: 10 * u,
                        fontFamily: theme.bodyFont,
                        fontSize: (dense ? 22 : 26) * u,
                        lineHeight: 1.45,
                        color: theme.muted,
                      }}
                    >
                      {it.body}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Layer>
  );
};
