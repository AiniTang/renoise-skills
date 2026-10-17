import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedText, FadeUp } from "../components/AnimatedText";
import { Layer } from "../components/Camera";
import { DeviceFrame } from "../components/DeviceFrame";
import { MockUI } from "../components/MockUI";
import { useTheme, useUnit } from "../theme";
import type { OutroScene, ShowcaseScene } from "../types";

export const Showcase: React.FC<{ scene: ShowcaseScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { theme, sb } = useTheme();
  const { u, portrait, width } = useUnit();
  const kind = scene.frame ?? (portrait ? "phone" : "browser");
  const siteUrl = sb.scenes.find((s): s is OutroScene => s.type === "outro")?.url;

  const enter = spring({ frame: frame - 4, fps, config: { damping: 20, stiffness: 80 } });
  const settle = interpolate(frame, [0, durationInFrames], [0, 1], { extrapolateRight: "clamp" });
  const rotY = (portrait ? 0 : -16) * (1 - enter) + (portrait ? 0 : -6) * (1 - settle);
  const rotX = 10 * (1 - enter) + 3 * (1 - settle);

  const gap = (portrait ? 70 : 90) * u;
  const inner = width - (portrait ? 140 : 260) * u;
  const deviceWidth =
    kind === "phone" ? (portrait ? 520 : 400) * u : portrait ? width * 0.8 : inner * 0.56;
  const copyWidth = portrait ? inner : Math.min(720 * u, inner - deviceWidth - gap);
  const uiScale = kind === "phone" ? deviceWidth / 520 : deviceWidth / 1000;

  const em = (line: string) =>
    Array.from(line).reduce((w, ch) => w + (/[\u3000-\u9fff\uff00-\uffef]/.test(ch) ? 1 : 0.56), 0);
  const longest = Math.max(...scene.title.split("\n").map(em));
  const titleSize = Math.min((portrait ? 76 : 84) * u, copyWidth / Math.max(1, longest));

  const device = (
    <div
      style={{
        opacity: enter,
        transform: `perspective(${2400 * u}px) translateY(${(1 - enter) * 120 * u}px) rotateY(${rotY}deg) rotateX(${rotX}deg)`,
        transformStyle: "preserve-3d",
      }}
    >
      {kind === "none" && scene.image ? (
        <Img src={staticFile(scene.image)} style={{ width: deviceWidth, display: "block" }} />
      ) : (
      <DeviceFrame kind={kind} width={deviceWidth} u={u} url={siteUrl}>
        {scene.image ? (
          <Img
            src={staticFile(scene.image)}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }}
          />
        ) : (
          <MockUI scale={uiScale} compact={kind === "phone"} />
        )}
      </DeviceFrame>
      )}
    </div>
  );

  const copy = (
    <div style={{ width: copyWidth, flexShrink: 0, textAlign: portrait ? "center" : "left" }}>
      <AnimatedText
        text={scene.title}
        style={{
          fontFamily: theme.displayFont,
          fontWeight: theme.displayWeight,
          letterSpacing: theme.tracking,
          fontSize: titleSize,
          lineHeight: 1.12,
          color: theme.fg,
        }}
      />
      {scene.body && (
        <FadeUp
          delay={14}
          style={{
            marginTop: 26 * u,
            fontFamily: theme.bodyFont,
            fontSize: 30 * u,
            lineHeight: 1.55,
            color: theme.muted,
          }}
        >
          {scene.body}
        </FadeUp>
      )}
    </div>
  );

  return (
    <Layer depth={1}>
      <AbsoluteFill
        style={{
          flexDirection: portrait ? "column" : "row",
          justifyContent: "center",
          alignItems: "center",
          gap,
          padding: portrait ? `${140 * u}px ${70 * u}px` : `0 ${130 * u}px`,
        }}
      >
        {copy}
        {device}
      </AbsoluteFill>
    </Layer>
  );
};
