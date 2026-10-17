import React, { createContext, useContext } from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { CameraMove } from "../types";

type CameraState = { move: CameraMove; p: number; intensity: number };
const CameraContext = createContext<CameraState>({
  move: "static",
  p: 0,
  intensity: 1,
});

const ease = Easing.bezier(0.45, 0, 0.25, 1);

/** Transform for a layer at `depth` (0 = far background, 1 = subject, >1 = foreground). */
const transformFor = ({ move, p, intensity }: CameraState, depth: number) => {
  const k = intensity * depth;
  const lerp = (a: number, b: number) => a + (b - a) * p;
  switch (move) {
    case "push-in":
      return `scale(${1 + lerp(0, 0.08) * k})`;
    case "pull-out":
      return `scale(${1 + lerp(0.1, 0) * k})`;
    case "pan-left":
      return `scale(${1 + 0.06 * k}) translateX(${lerp(3, -3) * k}%)`;
    case "pan-right":
      return `scale(${1 + 0.06 * k}) translateX(${lerp(-3, 3) * k}%)`;
    case "tilt-up":
      return `scale(${1 + 0.06 * k}) translateY(${lerp(3, -3) * k}%)`;
    case "drift": {
      const a = p * Math.PI;
      return `scale(${1 + 0.04 * k}) translate(${Math.sin(a) * 1.2 * k}%, ${
        Math.cos(a) * 0.8 * k
      }%) rotate(${lerp(-0.6, 0.6) * k}deg)`;
    }
    case "orbit":
      return `perspective(1600px) rotateY(${lerp(-7, 7) * k}deg) scale(${
        1 + 0.04 * k
      })`;
    default:
      return "none";
  }
};

export const Camera: React.FC<{
  move: CameraMove;
  intensity: number;
  children: React.ReactNode;
}> = ({ move, intensity, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = ease(
    interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  return (
    <CameraContext.Provider value={{ move, p, intensity }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>{children}</AbsoluteFill>
    </CameraContext.Provider>
  );
};

/** A parallax plane. Deeper layers move less than the subject. */
export const Layer: React.FC<{
  depth?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ depth = 1, children, style }) => {
  const cam = useContext(CameraContext);
  return (
    <AbsoluteFill
      style={{
        transform: transformFor(cam, depth),
        transformOrigin: "50% 50%",
        ...style,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
