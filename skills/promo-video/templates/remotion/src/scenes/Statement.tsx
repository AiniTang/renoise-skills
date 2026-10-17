import React from "react";
import { AbsoluteFill } from "remotion";
import { AnimatedText, FadeUp } from "../components/AnimatedText";
import { Layer } from "../components/Camera";
import { useTheme, useUnit } from "../theme";
import type { StatementScene } from "../types";

export const fitScale = (text: string, comfortable: number) => {
  const len = Array.from(text.replace(/\s+/g, "")).length;
  return Math.max(0.5, Math.min(1, Math.sqrt(comfortable / Math.max(1, len))));
};

export const Statement: React.FC<{ scene: StatementScene }> = ({ scene }) => {
  const { theme } = useTheme();
  const { u, portrait } = useUnit();
  const size = (portrait ? 104 : 124) * u * fitScale(scene.text, portrait ? 10 : 14);
  return (
    <Layer depth={1}>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: `0 ${(portrait ? 80 : 160) * u}px`,
          textAlign: "center",
        }}
      >
        {scene.eyebrow && (
          <FadeUp
            style={{
              fontFamily: theme.bodyFont,
              fontSize: 28 * u,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: theme.highlight,
              marginBottom: 36 * u,
              fontWeight: 600,
            }}
          >
            {scene.eyebrow}
          </FadeUp>
        )}
        <AnimatedText
          text={scene.text}
          highlight={scene.highlight}
          delay={scene.eyebrow ? 6 : 0}
          style={{
            fontFamily: theme.displayFont,
            fontWeight: theme.displayWeight,
            letterSpacing: theme.tracking,
            fontSize: size,
            lineHeight: 1.12,
            color: theme.fg,
          }}
        />
      </AbsoluteFill>
    </Layer>
  );
};
