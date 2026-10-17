import React from "react";
import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { useBrand } from "./cinematic/brand";
import { Lights, LogoMesh, Post, StudioEnv, useSvgShapes } from "./cinematic/Logo3D";
import { E, mix, seg } from "./cinematic/motion";

const CameraZ: React.FC<{ z: number }> = ({ z }) => {
  const { camera } = useThree();
  camera.position.set(0, 0, z);
  camera.lookAt(0, 0, z - 10);
  return null;
};

/** 118-frame opener: chrome logo lands on the music arrival, then yields to the morph. */
export const YouWareOpener: React.FC = () => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const b = useBrand();
  const shapes = useSvgShapes(b.logo ?? "brand/logo-mark.svg");
  const enter = seg(f, 0, 62, E.out);
  const hold = 1 - seg(f, 88, 28, E.in2);
  const camZ = mix(10, 4.2, seg(f, 88, 28, E.in2));
  const textOut = 1 - seg(f, 96, 16, E.inOut);
  const fadeOut = 1 - seg(f, 108, 10, E.linear);
  return (
    <AbsoluteFill style={{ background: b.ink, opacity: fadeOut }}>
      <ThreeCanvas width={width} height={height} camera={{ position: [0, 0, 10], fov: 35 }}>
        <color attach="background" args={[b.ink]} />
        <CameraZ z={camZ} />
        <StudioEnv />
        <Lights sweep={seg(f, 18, 70, E.sine)} accent={b.accent} accent2={b.accent2} />
        {shapes && (
          <LogoMesh
            shapes={shapes}
            scale={mix(3.6, 2.4, 1 - hold)}
            position={[0, mix(0.85, 0.2, enter) * hold, mix(-16, 0, enter)]}
            rotation={[mix(0.9, 0.1, enter), mix(-Math.PI * 2.4, 0, enter) + Math.sin(f / 18) * 0.05, 0]}
          />
        )}
        <Post bloom={0.85} />
      </ThreeCanvas>
      <AbsoluteFill style={{ justifyContent: "flex-end", paddingBottom: 96, opacity: textOut }}>
        {["Your AI partner.", "Already on it."].map((line, i) => (
          <div key={line} style={{ display: "flex", justifyContent: "center", overflow: "hidden", paddingBottom: 10 }}>
            {Array.from(line).map((ch, k) => {
              const p = seg(f, 28 + i * 14 + k * 0.85, 16, E.out);
              return (
                <span
                  key={k}
                  style={{
                    display: "inline-block",
                    whiteSpace: "pre",
                    color: i === 1 ? b.accent : "#F5F3EF",
                    fontFamily: b.display,
                    fontWeight: 500,
                    fontSize: 84,
                    letterSpacing: "-0.02em",
                    transform: `translateY(${(1 - p) * 110}%)`,
                    opacity: p,
                    filter: `blur(${(1 - p) * 8}px)`,
                  }}
                >
                  {ch}
                </span>
              );
            })}
          </div>
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
