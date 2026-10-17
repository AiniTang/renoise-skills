import React, { useId, useLayoutEffect, useRef } from "react";
import * as THREE from "three";
import { continueRender, delayRender, getRemotionEnvironment, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useFrame } from "@react-three/fiber";

/*
 * v1's judder: shot containers were CSS-scaled during transitions, R3F measured the canvas with getBoundingClientRect
 * (transforms included) when it mounted, and the composer kept that size — every render tab that mounted a shot at a
 * different moment drew a differently zoomed frame. `resize.offsetSize` measures the untransformed layout box.
 *
 * Frame gate for <ThreeCanvas>. While rendering, R3F runs its own (concurrent) reconciler and draws on the next
 * requestAnimationFrame, so Remotion can screenshot before the 3D tree has caught up with the frame — the stale
 * frames are what made v1 judder. The DOM side opens a delayRender handle for every frame; the R3F side releases
 * it from useFrame only after that same frame has actually been drawn.
 */
const pending = new Map<string, number>();
const drawn = new Set<string>();

const DomGate: React.FC<{ id: string }> = ({ id }) => {
  const f = useCurrentFrame();
  useLayoutEffect(() => {
    if (!getRemotionEnvironment().isRendering) return;
    const key = `${id}:${f}`;
    if (drawn.has(key) || pending.has(key)) return;
    pending.set(key, delayRender(`3D frame ${key}`, { timeoutInMilliseconds: 90000 }));
  }, [f, id]);
  useLayoutEffect(
    () => () => {
      for (const [k, h] of pending)
        if (k.startsWith(`${id}:`)) {
          pending.delete(k);
          continueRender(h);
        }
    },
    [id],
  );
  return null;
};

/** inside the canvas: priority 2 runs after an EffectComposer (priority 1); without one, `draw` renders here */
const GlGate: React.FC<{ id: string; draw: boolean }> = ({ id, draw }) => {
  const f = useCurrentFrame();
  const fr = useRef(f);
  useLayoutEffect(() => {
    fr.current = f;
  });
  useFrame(
    (s) => {
      if (draw) s.gl.render(s.scene, s.camera);
      const key = `${id}:${fr.current}`;
      drawn.add(key);
      const h = pending.get(key);
      if (h !== undefined) {
        pending.delete(key);
        continueRender(h);
      }
    },
    draw ? 1 : 2,
  );
  return null;
};

/** ThreeCanvas that never lets Remotion capture a frame the GPU has not drawn yet. `composer`: the scene has an EffectComposer. */
export const GL: React.FC<{ id?: string; composer?: boolean; children: React.ReactNode; exposure?: number; shadows?: boolean | "soft" | "variance" | "basic" | "percentage"; alpha?: boolean; tone?: boolean }> = ({ id: given, composer = true, children, exposure = 1, shadows = true, alpha = false, tone = true }) => {
  const auto = useId();
  const id = given ?? auto;
  return (
  <>
    <DomGate id={id} />
    <ThreeCanvas
      width={1920}
      height={1080}
      shadows={shadows === true ? "soft" : shadows}
      // measure layout size, not the CSS-transformed box: a canvas mounted inside a scaled container otherwise keeps a wrong size
      resize={{ offsetSize: true, scroll: false }}
      gl={{ antialias: true, alpha, premultipliedAlpha: true, toneMapping: tone ? THREE.ACESFilmicToneMapping : THREE.NoToneMapping, toneMappingExposure: exposure, outputColorSpace: THREE.SRGBColorSpace, preserveDrawingBuffer: true }}
    >
      {children}
      <GlGate id={id} draw={!composer} />
    </ThreeCanvas>
  </>
  );
};

/** camera set from inside the render loop (priority -1: before the composer draws), never from a lagging effect */
export type Cam = { px: number; py: number; pz: number; tx: number; ty: number; tz: number; fov: number; roll?: number };
export const applyCam = (c: THREE.PerspectiveCamera, k: Cam) => {
  c.position.set(k.px, k.py, k.pz);
  c.up.set(Math.sin(k.roll ?? 0), Math.cos(k.roll ?? 0), 0);
  c.lookAt(k.tx, k.ty, k.tz);
  c.fov = k.fov;
  c.near = 0.1;
  c.far = 5000;
  c.aspect = 16 / 9;
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
};
export const CamRig: React.FC<{ k: Cam }> = ({ k }) => {
  const kr = useRef(k);
  useLayoutEffect(() => {
    kr.current = k;
  });
  useFrame((s) => applyCam(s.camera as THREE.PerspectiveCamera, kr.current), -1);
  return null;
};
