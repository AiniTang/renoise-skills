import React from "react";
import { AbsoluteFill, Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { FadeUp } from "../components/AnimatedText";
import { Layer } from "../components/Camera";
import { useTheme, useUnit } from "../theme";
import type { OutroScene } from "../types";

export const Outro: React.FC<{ scene: OutroScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, sb } = useTheme();
  const { u, portrait } = useUnit();
  const s = spring({ frame, fps, config: { damping: 14, stiffness: 90 } });
  const invert = theme.light ? undefined : "invert(1)";
  const markSize = (portrait ? 110 : 120) * u;

  const logo = sb.brand.logo ? (
    <div style={{ display: "flex", alignItems: "center", gap: markSize * 0.28 }}>
      <Img src={staticFile(sb.brand.logo)} style={{ height: markSize, filter: invert }} />
      {sb.brand.wordmark && (
        <Img src={staticFile(sb.brand.wordmark)} style={{ height: markSize * 0.52, filter: invert }} />
      )}
    </div>
  ) : (
    <div
      style={{
        fontFamily: theme.displayFont,
        fontWeight: theme.displayWeight,
        letterSpacing: theme.tracking,
        fontSize: (portrait ? 120 : 140) * u,
        color: theme.fg,
      }}
    >
      {sb.brand.name}
      <span style={{ color: theme.highlight }}>.</span>
    </div>
  );

  return (
    <>
      <Layer depth={1}>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center", gap: 34 * u }}>
          <div style={{ transform: `scale(${0.8 + 0.2 * s})`, opacity: s }}>{logo}</div>
          {scene.tagline && (
            <FadeUp
              delay={10}
              style={{
                fontFamily: theme.displayFont,
                fontSize: 48 * u,
                letterSpacing: theme.tracking,
                color: theme.fg,
                padding: `0 ${80 * u}px`,
              }}
            >
              {scene.tagline}
            </FadeUp>
          )}
          {scene.cta && (
            <FadeUp delay={18} style={{ marginTop: 12 * u }}>
              <div
                style={{
                  display: "inline-block",
                  padding: `${20 * u}px ${52 * u}px`,
                  borderRadius: theme.id === "kinetic" ? 6 * u : 999,
                  background: theme.button,
                  color: theme.onButton,
                  fontFamily: theme.bodyFont,
                  fontWeight: 600,
                  fontSize: 32 * u,
                }}
              >
                {scene.cta}
              </div>
            </FadeUp>
          )}
          {scene.url && (
            <FadeUp delay={24} style={{ fontFamily: theme.bodyFont, fontSize: 28 * u, color: theme.muted, letterSpacing: "0.04em" }}>
              {scene.url}
            </FadeUp>
          )}
        </AbsoluteFill>
      </Layer>
      {sb.brand.disclaimer && (
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: (portrait ? 120 : 48) * u }}>
          <FadeUp delay={20} style={{ fontFamily: theme.bodyFont, fontSize: 20 * u, color: theme.muted, opacity: 0.8, padding: `0 ${60 * u}px`, textAlign: "center" }}>
            {sb.brand.disclaimer}
          </FadeUp>
        </AbsoluteFill>
      )}
    </>
  );
};
