import React, { useEffect, useState } from "react";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import type { TransitionPresentation } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import {
  AbsoluteFill,
  Audio,
  cancelRender,
  continueRender,
  delayRender,
  Easing,
  interpolate,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Background } from "./components/Background";
import { Camera } from "./components/Camera";
import { Caption } from "./components/Captions";
import { Features } from "./scenes/Features";
import { Hero3D } from "./scenes/Hero3D";
import { Outro } from "./scenes/Outro";
import { Showcase } from "./scenes/Showcase";
import { Stats } from "./scenes/Stats";
import { Statement } from "./scenes/Statement";
import { getTheme, ThemeContext, withTone } from "./theme";
import { getNetFrames, getTransitionFrames } from "./timing";
import type { Scene, Storyboard, TransitionId } from "./types";

const SceneBody: React.FC<{ scene: Scene }> = ({ scene }) => {
  switch (scene.type) {
    case "statement":
      return <Statement scene={scene} />;
    case "hero3d":
      return <Hero3D scene={scene} />;
    case "features":
      return <Features scene={scene} />;
    case "stats":
      return <Stats scene={scene} />;
    case "showcase":
      return <Showcase scene={scene} />;
    case "outro":
      return <Outro scene={scene} />;
  }
};

const presentationFor = (
  id: TransitionId,
  index: number,
): TransitionPresentation<Record<string, unknown>> => {
  const dir = index % 2 === 0 ? "from-right" : "from-left";
  if (id === "slide") return slide({ direction: dir }) as TransitionPresentation<Record<string, unknown>>;
  if (id === "wipe") return wipe({ direction: dir }) as TransitionPresentation<Record<string, unknown>>;
  return fade() as TransitionPresentation<Record<string, unknown>>;
};

export const useBrandFonts = (sb: Storyboard) => {
  const fonts = [sb.brand.fonts?.display, sb.brand.fonts?.body].filter(
    (f): f is { family: string; file: string } => Boolean(f?.file),
  );
  const [handle] = useState(() => (fonts.length ? delayRender("brand fonts") : null));
  useEffect(() => {
    if (handle === null) return;
    Promise.all(
      fonts.map((f) =>
        new FontFace(f.family, `url(${staticFile(f.file)})`, { weight: "100 1000" })
          .load()
          .then((face) => document.fonts.add(face)),
      ),
    )
      .then(() => continueRender(handle))
      .catch((err) => cancelRender(err));
  }, [handle]);
};

export const Promo: React.FC<Storyboard> = (sb) => {
  const theme = getTheme(sb);
  const { fps, durationInFrames } = useVideoConfig();
  useBrandFonts(sb);

  const net = getNetFrames(sb);
  const elements: React.ReactNode[] = [];
  sb.scenes.forEach((scene, i) => {
    const t = getTransitionFrames(sb, i);
    elements.push(
      <TransitionSeries.Sequence key={`s${i}`} durationInFrames={net[i] + t}>
        <ThemeContext.Provider value={{ theme: withTone(theme, scene.tone, sb), sb }}>
          <AbsoluteFill>
            <Camera move={scene.camera ?? theme.camera} intensity={theme.cameraIntensity}>
              <Background />
              <SceneBody scene={scene} />
            </Camera>
            {sb.captions && scene.caption ? <Caption text={scene.caption} /> : null}
          </AbsoluteFill>
        </ThemeContext.Provider>
      </TransitionSeries.Sequence>,
    );
    if (t > 0) {
      elements.push(
        <TransitionSeries.Transition
          key={`t${i}`}
          presentation={presentationFor(scene.transition ?? theme.transition, i)}
          timing={linearTiming({ durationInFrames: t, easing: Easing.inOut(Easing.cubic) })}
        />,
      );
    }
  });

  const music = sb.music;
  const vol = music?.volume ?? 0.8;

  return (
    <ThemeContext.Provider value={{ theme, sb }}>
      <AbsoluteFill style={{ background: theme.bg }}>
        <TransitionSeries>{elements}</TransitionSeries>
        {music?.file ? (
          <Audio
            src={staticFile(music.file)}
            trimBefore={Math.round((music.startOffset ?? 0) * fps)}
            volume={(f) =>
              vol *
              interpolate(
                f,
                [0, fps * 0.4, durationInFrames - fps * 1.5, durationInFrames - 1],
                [0, 1, 1, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
              )
            }
          />
        ) : null}
      </AbsoluteFill>
    </ThemeContext.Provider>
  );
};
