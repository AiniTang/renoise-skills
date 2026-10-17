import React from "react";
import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedText, FadeUp } from "../components/AnimatedText";
import { Layer } from "../components/Camera";
import { useTheme, useUnit } from "../theme";
import type { Hero3DScene } from "../types";

const Shape: React.FC<{ shape: NonNullable<Hero3DScene["shape"]>; accent: string; accent2: string }> = ({
  shape,
  accent,
  accent2,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 70 } });

  if (shape === "orbs") {
    return (
      <group scale={enter} rotation={[0.35, t * 0.5, 0]}>
        <mesh>
          <sphereGeometry args={[0.9, 64, 64]} />
          <meshPhysicalMaterial color={accent} metalness={0.4} roughness={0.15} clearcoat={1} />
        </mesh>
        {Array.from({ length: 6 }).map((_, i) => {
          const a = (i / 6) * Math.PI * 2 + t * 0.8;
          const r = 2.1;
          return (
            <mesh key={i} position={[Math.cos(a) * r, Math.sin(a * 2) * 0.35, Math.sin(a) * r]}>
              <sphereGeometry args={[0.18 + (i % 3) * 0.08, 48, 48]} />
              <meshPhysicalMaterial color={i % 2 ? accent2 : "#ffffff"} metalness={0.3} roughness={0.2} />
            </mesh>
          );
        })}
      </group>
    );
  }

  if (shape === "cubes") {
    const n = 7;
    return (
      <group scale={enter * 0.55} rotation={[0.9, t * 0.25, 0]}>
        {Array.from({ length: n * n }).map((_, k) => {
          const x = (k % n) - (n - 1) / 2;
          const z = Math.floor(k / n) - (n - 1) / 2;
          const d = Math.hypot(x, z);
          const h = 0.6 + (Math.sin(d * 0.9 - t * 3) + 1) * 0.9;
          return (
            <mesh key={k} position={[x * 1.1, h / 2, z * 1.1]}>
              <boxGeometry args={[0.9, h, 0.9]} />
              <meshStandardMaterial color={d < 1.5 ? accent2 : accent} metalness={0.35} roughness={0.35} />
            </mesh>
          );
        })}
      </group>
    );
  }

  return (
    <group scale={enter} rotation={[t * 0.35, t * 0.5, 0]}>
      <mesh>
        <torusKnotGeometry args={[1, 0.34, 256, 48]} />
        <meshPhysicalMaterial color={accent} metalness={0.55} roughness={0.18} clearcoat={1} clearcoatRoughness={0.1} />
      </mesh>
      <mesh rotation={[0, t * -0.3, 0]}>
        <icosahedronGeometry args={[2.3, 1]} />
        <meshBasicMaterial color={accent2} wireframe transparent opacity={0.18} />
      </mesh>
    </group>
  );
};

export const Hero3D: React.FC<{ scene: Hero3DScene }> = ({ scene }) => {
  const { theme } = useTheme();
  const { u, portrait, width, height } = useUnit();
  return (
    <>
      <Layer depth={0.6}>
        <ThreeCanvas resize={{ offsetSize: true, scroll: false }}
          width={width}
          height={height}
          camera={{ position: [0, 0, portrait ? 12 : 7], fov: 40 }}
          style={{ position: "absolute", inset: 0 }}
        >
          <ambientLight intensity={0.45} />
          <directionalLight position={[5, 6, 5]} intensity={2.2} />
          <pointLight position={[-4, -2, 3]} intensity={40} color={theme.accent2} decay={1.5} />
          <pointLight position={[4, 3, -2]} intensity={25} color="#ffffff" decay={1.5} />
          <group position={portrait ? [0, 2.2, 0] : [1.7, 0, 0]}>
            <Shape shape={scene.shape ?? "knot"} accent={theme.accent} accent2={theme.accent2} />
          </group>
        </ThreeCanvas>
      </Layer>
      <Layer depth={1}>
        <AbsoluteFill
          style={{
            justifyContent: portrait ? "flex-end" : "center",
            alignItems: portrait ? "center" : "flex-start",
            padding: portrait ? `0 ${80 * u}px ${380 * u}px` : `0 0 0 ${150 * u}px`,
            textAlign: portrait ? "center" : "left",
          }}
        >
          <AnimatedText
            text={scene.title}
            delay={8}
            style={{
              fontFamily: theme.displayFont,
              fontWeight: theme.displayWeight,
              letterSpacing: theme.tracking,
              fontSize: (portrait ? 96 : 110) * u,
              lineHeight: 1.1,
              color: theme.fg,
              maxWidth: portrait ? "100%" : `${860 * u}px`,
            }}
          />
          {scene.subtitle && (
            <FadeUp
              delay={20}
              style={{
                marginTop: 28 * u,
                fontFamily: theme.bodyFont,
                fontSize: 34 * u,
                lineHeight: 1.45,
                color: theme.muted,
                maxWidth: portrait ? "100%" : `${720 * u}px`,
              }}
            >
              {scene.subtitle}
            </FadeUp>
          )}
        </AbsoluteFill>
      </Layer>
    </>
  );
};
