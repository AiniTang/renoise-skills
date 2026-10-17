import React, { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { EffectComposer, TiltShift2 } from "@react-three/postprocessing";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { SVGLoader } from "three/examples/jsm/loaders/SVGLoader.js";
import { random } from "remotion";
import { step, type SpringCfg } from "../spring";

/*
 * Isometric 2.5D kit (等轴): an orthographic "desk miniature" world that grows on the beat.
 * <IsoCanvas> sets the true-isometric camera (45° / 35.264°), soft shadows, neutral tone mapping and tilt-shift;
 * pieces (<IsoTile>, <House>, <Billboard>, <Bars>, <Library>, <Tree>, <Mark3D>, <IsoCard>) take a local frame `t`
 * and an `at` frame and grow in with a spring. World units: one tile = 1.
 */

const hz = (f: number) => 2 * Math.PI * f;
export const GROW: SpringCfg = { w: hz(2.6), z: 0.55 };
const g = (t: number, at: number, cfg: SpringCfg = GROW) => Math.max(0, step((t - at) / 30, cfg));

export const ISO_ELEV = Math.atan(1 / Math.SQRT2); // 35.264°

const Rig: React.FC<{ zoom: number; yaw: number; target: [number, number, number] }> = ({ zoom, yaw, target }) => {
  const { camera, gl, scene } = useThree();
  const d = 40;
  const a = Math.PI / 4 + yaw;
  camera.position.set(target[0] + Math.sin(a) * Math.cos(ISO_ELEV) * d, target[1] + Math.sin(ISO_ELEV) * d, target[2] + Math.cos(a) * Math.cos(ISO_ELEV) * d);
  camera.lookAt(target[0], target[1], target[2]);
  (camera as THREE.OrthographicCamera).zoom = zoom;
  camera.updateProjectionMatrix();
  gl.toneMapping = THREE.NeutralToneMapping;
  gl.shadowMap.type = THREE.PCFSoftShadowMap;
  scene.background = null;
  return null;
};

export const IsoCanvas: React.FC<{ zoom: number; yaw?: number; target?: [number, number, number]; tilt?: number; children: React.ReactNode; width?: number; height?: number }> = ({
  zoom,
  yaw = 0,
  target = [0, 0, 0],
  tilt = 0.08,
  children,
  width = 1920,
  height = 1080,
}) => (
  <ThreeCanvas resize={{ offsetSize: true, scroll: false }} width={width} height={height} orthographic shadows camera={{ position: [30, 30, 30], zoom, near: -200, far: 400 }} gl={{ alpha: true, antialias: true }} style={{ position: "absolute", inset: 0 }}>
    <Rig zoom={zoom} yaw={yaw} target={target} />
    <hemisphereLight args={["#FFFFFF", "#D9D2C2", 1.25]} />
    <directionalLight
      castShadow
      position={[-9, 18, 7]}
      intensity={2.2}
      shadow-mapSize={[2048, 2048]}
      shadow-camera-left={-14}
      shadow-camera-right={14}
      shadow-camera-top={14}
      shadow-camera-bottom={-14}
      shadow-bias={-0.0004}
      shadow-radius={5}
    />
    {children}
    {tilt > 0 && (
      <EffectComposer multisampling={4}>
        <TiltShift2 blur={tilt} taper={0.7} start={[0.0, 0.52]} end={[1.0, 0.52]} samples={12} />
      </EffectComposer>
    )}
  </ThreeCanvas>
);

const mat = (color: string, rough = 0.78) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0 });

/** A ground tile that pops up out of the slab with its own delay. */
export const IsoTile: React.FC<{ t: number; at: number; x: number; z: number; color: string; h?: number; size?: number }> = ({ t, at, x, z, color, h = 0.28, size = 0.96 }) => {
  const k = g(t, at);
  if (k <= 0.001) return null;
  return (
    <mesh position={[x, -h / 2 + (1 - Math.min(1, k)) * -1.2 + 0.001, z]} scale={[size, h, size]} receiveShadow castShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color={color} roughness={0.85} />
    </mesh>
  );
};

/** Grows from the ground: scale-y spring with a little squash. */
const Grow: React.FC<{ t: number; at: number; x: number; z: number; rot?: number; children: React.ReactNode }> = ({ t, at, x, z, rot = 0, children }) => {
  const k = g(t, at);
  if (k <= 0.001) return null;
  const sq = 1 + 0.12 * (1 - Math.min(1, k));
  return (
    <group position={[x, 0, z]} rotation={[0, rot, 0]} scale={[sq, Math.max(0.001, k), sq]}>
      {children}
    </group>
  );
};

export const House: React.FC<{ t: number; at: number; x: number; z: number; wall?: string; roof?: string; w?: number; d?: number; h?: number; rot?: number }> = ({
  t,
  at,
  x,
  z,
  wall = "#F5F0E6",
  roof = "#EE8C6C",
  w = 0.72,
  d = 0.72,
  h = 0.55,
  rot = 0,
}) => {
  const roofGeo = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-w / 2 - 0.05, 0);
    s.lineTo(0, 0.34);
    s.lineTo(w / 2 + 0.05, 0);
    s.closePath();
    const geo = new THREE.ExtrudeGeometry(s, { depth: d + 0.08, bevelEnabled: false });
    geo.translate(0, 0, -(d + 0.08) / 2);
    return geo;
  }, [w, d]);
  return (
    <Grow t={t} at={at} x={x} z={z} rot={rot}>
      <mesh position={[0, h / 2, 0]} castShadow receiveShadow material={mat(wall)}>
        <boxGeometry args={[w, h, d]} />
      </mesh>
      <mesh position={[0, h, 0]} geometry={roofGeo} castShadow material={mat(roof, 0.7)} />
      <mesh position={[w / 2 + 0.001, h * 0.45, 0]} rotation={[0, Math.PI / 2, 0]} material={mat("#2E3A4A", 0.3)}>
        <planeGeometry args={[0.22, 0.2]} />
      </mesh>
    </Grow>
  );
};

/** Canvas texture helper (drawn once). */
export const useCanvasTexture = (w: number, h: number, draw: (g: CanvasRenderingContext2D) => void, deps: unknown[]) =>
  useMemo(() => {
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    draw(c.getContext("2d")!);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return tex;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

/** A billboard on two posts showing a slide-like panel. */
export const Billboard: React.FC<{ t: number; at: number; x: number; z: number; accent?: string; photo?: string; rot?: number }> = ({ t, at, x, z, accent = "#7D6BC1", photo = "#FFD15C", rot = 0 }) => {
  const tex = useCanvasTexture(
    512,
    288,
    (c) => {
      c.fillStyle = "#FFFFFF";
      c.fillRect(0, 0, 512, 288);
      c.fillStyle = "#151513";
      c.fillRect(34, 44, 210, 26);
      c.fillRect(34, 82, 160, 26);
      c.fillStyle = "rgba(21,21,19,0.25)";
      c.fillRect(34, 132, 200, 10);
      c.fillRect(34, 152, 170, 10);
      c.fillStyle = accent;
      c.fillRect(280, 30, 200, 228);
      c.fillStyle = photo;
      c.beginPath();
      c.arc(380, 130, 48, 0, Math.PI * 2);
      c.fill();
    },
    [accent, photo],
  );
  return (
    <Grow t={t} at={at} x={x} z={z} rot={rot}>
      {[-0.32, 0.32].map((px) => (
        <mesh key={px} position={[px, 0.35, 0]} castShadow material={mat("#9A9486")}>
          <boxGeometry args={[0.05, 0.7, 0.05]} />
        </mesh>
      ))}
      <mesh position={[0, 0.9, 0]} castShadow>
        <boxGeometry args={[1.0, 0.58, 0.05]} />
        <meshStandardMaterial attach="material-0" color="#E7E0D1" />
        <meshStandardMaterial attach="material-1" color="#E7E0D1" />
        <meshStandardMaterial attach="material-2" color="#E7E0D1" />
        <meshStandardMaterial attach="material-3" color="#E7E0D1" />
        <meshStandardMaterial attach="material-4" map={tex} roughness={0.6} />
        <meshStandardMaterial attach="material-5" color="#E7E0D1" />
      </mesh>
    </Grow>
  );
};

/** A little bar chart on a plinth (sheets district). Bars grow one after another. */
export const Bars: React.FC<{ t: number; at: number; x: number; z: number; heights?: number[]; colors?: string[] }> = ({ t, at, x, z, heights = [0.5, 0.9, 0.7, 1.3], colors = ["#2556B6", "#BAC78D", "#7D6BC1", "#EE8C6C"] }) => (
  <group position={[x, 0, z]}>
    {heights.map((h, i) => {
      const k = g(t, at + i * 4);
      if (k <= 0.001) return null;
      return (
        <mesh key={i} position={[-0.3 + i * 0.2, (h * k) / 2, 0]} scale={[1, Math.max(0.001, k), 1]} castShadow material={mat(colors[i % colors.length], 0.6)}>
          <boxGeometry args={[0.15, h, 0.15]} />
        </mesh>
      );
    })}
  </group>
);

/** Stacked "pages" tower with a dome (reports district). */
export const Library: React.FC<{ t: number; at: number; x: number; z: number; floors?: number; colors?: string[] }> = ({ t, at, x, z, floors = 7, colors = ["#F5F0E6", "#EE8C6C"] }) => (
  <group position={[x, 0, z]}>
    {Array.from({ length: floors }, (_, i) => {
      const k = g(t, at + i * 3);
      if (k <= 0.001) return null;
      const y = 0.12 + i * 0.22;
      return (
        <mesh key={i} position={[0, y + (1 - Math.min(1, k)) * 1.5, 0]} castShadow receiveShadow material={mat(colors[i % colors.length])}>
          <boxGeometry args={[0.9 - i * 0.03, 0.2, 0.7 - i * 0.02]} />
        </mesh>
      );
    })}
    {g(t, at + floors * 3) > 0.001 && (
      <mesh position={[0, 0.12 + floors * 0.22 + 0.02, 0]} scale={Math.min(1.2, g(t, at + floors * 3))} castShadow material={mat("#2556B6", 0.4)}>
        <sphereGeometry args={[0.28, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
      </mesh>
    )}
  </group>
);

export const Tree: React.FC<{ t: number; at: number; x: number; z: number; color?: string; s?: number }> = ({ t, at, x, z, color = "#7D8F57", s = 1 }) => (
  <Grow t={t} at={at} x={x} z={z}>
    <mesh position={[0, 0.12 * s, 0]} castShadow material={mat("#8B6B4A")}>
      <cylinderGeometry args={[0.04 * s, 0.05 * s, 0.24 * s, 6]} />
    </mesh>
    <mesh position={[0, 0.42 * s, 0]} castShadow material={mat(color, 0.9)}>
      <coneGeometry args={[0.22 * s, 0.52 * s, 7]} />
    </mesh>
  </Grow>
);

/** Extruded SVG (the brand mark) — pass the raw SVG markup. Centred on the origin, `size` world units wide. */
export const Mark3D: React.FC<{ svg: string; size?: number; depth?: number; color?: string; position?: [number, number, number]; rotationY?: number; scale?: number }> = ({
  svg,
  size = 1.4,
  depth = 0.18,
  color = "#151513",
  position = [0, 0, 0],
  rotationY = 0,
  scale = 1,
}) => {
  const geo = useMemo(() => {
    const data = new SVGLoader().parse(svg);
    const shapes = data.paths.flatMap((p) => SVGLoader.createShapes(p));
    const gg = new THREE.ExtrudeGeometry(shapes, { depth: depth * 100, bevelEnabled: true, bevelThickness: 2, bevelSize: 1.2, bevelSegments: 3, curveSegments: 16 });
    gg.computeBoundingBox();
    const bb = gg.boundingBox!;
    const w = bb.max.x - bb.min.x;
    const k = size / w;
    gg.translate(-(bb.min.x + bb.max.x) / 2, -(bb.min.y + bb.max.y) / 2, -(depth * 100) / 2);
    gg.scale(k, -k, k);
    return gg;
  }, [svg, size, depth]);
  return (
    <mesh geometry={geo} position={position} rotation={[0, rotationY, 0]} scale={scale} castShadow>
      <meshStandardMaterial color={color} roughness={0.35} metalness={0.05} />
    </mesh>
  );
};

/** Floating label card that always faces the camera and bobs a little. */
export const IsoCard: React.FC<{ t: number; at: number; position: [number, number, number]; title: string; sub?: string; accent?: string; family: string; mono: string; w?: number }> = ({
  t,
  at,
  position,
  title,
  sub,
  accent = "#EE8C6C",
  family,
  mono,
  w = 1.9,
}) => {
  const { camera } = useThree();
  const tex = useCanvasTexture(
    760,
    300,
    (c) => {
      const r = 40;
      c.fillStyle = "#FFFFFF";
      c.beginPath();
      c.roundRect(10, 10, 740, 280, r);
      c.fill();
      c.fillStyle = accent;
      c.beginPath();
      c.roundRect(44, 52, 18, 196, 9);
      c.fill();
      c.fillStyle = "#151513";
      c.font = `800 92px ${family}`;
      c.fillText(title, 92, 150);
      if (sub) {
        c.fillStyle = "rgba(21,21,19,0.55)";
        c.font = `500 40px ${mono}`;
        c.fillText(sub, 94, 222);
      }
    },
    [title, sub, accent, family, mono],
  );
  const k = g(t, at, { w: hz(3), z: 0.6 });
  const q = useMemo(() => new THREE.Quaternion(), []);
  if (k <= 0.001) return null;
  q.copy(camera.quaternion);
  const bob = Math.sin((t - at) / 30 * 2.2 + position[0]) * 0.05;
  return (
    <mesh position={[position[0], position[1] + bob + (1 - Math.min(1, k)) * -0.6, position[2]]} quaternion={q} scale={Math.max(0.001, k)} renderOrder={10}>
      <planeGeometry args={[w, (w * 300) / 760]} />
      <meshBasicMaterial map={tex} transparent toneMapped={false} depthTest={false} />
    </mesh>
  );
};

/** Deterministic scatter helper. */
export const scatter = (n: number, seed: string, box: [number, number, number, number]) =>
  Array.from({ length: n }, (_, i) => [box[0] + random(`${seed}x${i}`) * (box[2] - box[0]), box[1] + random(`${seed}z${i}`) * (box[3] - box[1])] as [number, number]);
