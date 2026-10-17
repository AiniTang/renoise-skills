import React, { useLayoutEffect, useMemo, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { EffectComposer, TiltShift2 } from "@react-three/postprocessing";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { StudioEnv } from "../Logo3D";

/*
 * Soft 3D kit (3D 软萌字 + 胶囊针阵): candy-clay materials, a pin-art field of capsules whose heights are a pure
 * function of (pin, frame), and puffy extruded letters from SVG shapes.
 * - <SoftCanvas>: perspective camera with a slow orbit, studio environment (reflections), one soft shadow light,
 *   neutral tone mapping, gentle horizontal tilt-shift. Transparent, so an HTML gradient shows behind.
 * - <PinField>: InstancedMesh of capsules standing on y=0 on a cols×rows grid; `height(i, j, x, z, t)` → y offset,
 *   `color(i, j, x, z, t)` → hex; both are re-evaluated every frame.
 * - <PuffLetter>: one extruded shape with a deep rounded bevel (soft toy look), centred on its own baseline.
 * Render Three.js samples to video before putting them in a scaled catalogue window (see style-pack-05).
 */

const Rig: React.FC<{ pos: [number, number, number]; look: [number, number, number]; fov: number }> = ({ pos, look, fov }) => {
  const { camera, gl, scene } = useThree();
  camera.position.set(...pos);
  camera.lookAt(...look);
  (camera as THREE.PerspectiveCamera).fov = fov;
  camera.updateProjectionMatrix();
  gl.toneMapping = THREE.NeutralToneMapping;
  gl.shadowMap.type = THREE.PCFSoftShadowMap;
  scene.background = null;
  scene.environmentIntensity = 0.32;
  return null;
};

export const SoftCanvas: React.FC<{ pos: [number, number, number]; look?: [number, number, number]; fov?: number; tilt?: number; children: React.ReactNode; width?: number; height?: number }> = ({
  pos,
  look = [0, 0, 0],
  fov = 32,
  tilt = 0.06,
  children,
  width = 1920,
  height = 1080,
}) => (
  <ThreeCanvas resize={{ offsetSize: true, scroll: false }} width={width} height={height} shadows camera={{ position: pos, fov, near: 0.1, far: 200 }} gl={{ alpha: true, antialias: true }} style={{ position: "absolute", inset: 0 }}>
    <Rig pos={pos} look={look} fov={fov} />
    <StudioEnv />
    <hemisphereLight args={["#FFFFFF", "#B9AEDC", 0.7]} />
    <directionalLight
      castShadow
      position={[-6, 14, 8]}
      intensity={2.6}
      shadow-mapSize={[2048, 2048]}
      shadow-camera-left={-14}
      shadow-camera-right={14}
      shadow-camera-top={10}
      shadow-camera-bottom={-10}
      shadow-bias={-0.0005}
      shadow-radius={6}
    />
    {children}
    {tilt > 0 && (
      <EffectComposer multisampling={4}>
        <TiltShift2 blur={tilt} taper={0.75} start={[0, 0.5]} end={[1, 0.5]} samples={10} />
      </EffectComposer>
    )}
  </ThreeCanvas>
);

export const candy = (color: string, rough = 0.32) => new THREE.MeshPhysicalMaterial({ color: new THREE.Color(color), roughness: rough, metalness: 0, clearcoat: 0.8, clearcoatRoughness: 0.25, sheen: 0.4, sheenColor: new THREE.Color("#FFFFFF") });

export const PinField: React.FC<{
  cols: number;
  rows: number;
  gap: number;
  radius?: number;
  length?: number;
  t: number;
  height: (i: number, j: number, x: number, z: number, t: number) => number;
  /** May depend on t (pins can change colour with their height). */
  color: (i: number, j: number, x: number, z: number, t: number) => string;
  z0?: number;
}> = ({ cols, rows, gap, radius = 0.15, length = 0.34, t, height, color, z0 = 0 }) => {
  const ref = useRef<THREE.InstancedMesh>(null);
  const n = cols * rows;
  const geo = useMemo(() => new THREE.CapsuleGeometry(radius, length, 6, 14), [radius, length]);
  const mtl = useMemo(() => new THREE.MeshPhysicalMaterial({ roughness: 0.3, metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.3 }), []);
  const cells = useMemo(
    () =>
      Array.from({ length: n }, (_, k) => {
        const i = k % cols;
        const j = Math.floor(k / cols);
        return { i, j, x: (i - (cols - 1) / 2) * gap, z: z0 + (j - (rows - 1) / 2) * gap };
      }),
    [n, cols, rows, gap, z0],
  );
  useLayoutEffect(() => {
    const m = ref.current;
    if (!m) return;
    const o = new THREE.Object3D();
    const c = new THREE.Color();
    const half = length / 2 + radius;
    cells.forEach(({ i, j, x, z }, k) => {
      o.position.set(x, half + height(i, j, x, z, t), z);
      o.updateMatrix();
      m.setMatrixAt(k, o.matrix);
      m.setColorAt(k, c.set(color(i, j, x, z, t)));
    });
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  });
  return <instancedMesh ref={ref} args={[geo, mtl, n]} castShadow receiveShadow />;
};

/** A puffy extruded glyph: `shape` in SVG units, scaled by `k` (units per SVG px); pivot at bottom-centre. */
export const usePuffGeometry = (shape: THREE.Shape | null, k: number, depth = 40, bevel = 9) =>
  useMemo(() => {
    if (!shape) return null;
    const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel * 0.8, bevelSegments: 10, curveSegments: 24 });
    g.computeBoundingBox();
    // clone: scale() recomputes geometry.boundingBox in place, which would corrupt the numbers used below
    const bb = g.boundingBox!.clone();
    // SVG y points down. Mirror y *and* z (= a 180° turn about x) so the triangle winding survives — mirroring y
    // alone turns every face inside-out and back-face culling hides the letter. Then pivot on the bottom-centre.
    g.scale(k, -k, -k);
    g.translate(-((bb.min.x + bb.max.x) / 2) * k, bb.max.y * k, (depth / 2) * k);
    g.computeVertexNormals();
    return g;
  }, [shape, k, depth, bevel]);
