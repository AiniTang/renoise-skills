import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { useSvgShapes } from "../cinematic/Logo3D";
import { candy, PinField, SoftCanvas, usePuffGeometry } from "../cinematic/soft3d";
import { step } from "../cinematic/spring";
import { fam } from "../cinematic/type";
import { MARK_D, MARK_VB } from "./markPath";

/**
 * 05 · 3D 软萌字 + 胶囊针阵 — "Pin-art YouWare": a candy ball drops onto a field of pastel capsules; the ripple
 * raises the YouWare mark in pin-art relief; it sinks back as puffy clay letters of the wordmark drop in, and the
 * ball rolls back to nudge the last one. 330 frames.
 */
export const SOFT_LEN = 330;
const SLAB = fam("Hepta Slab");

const COLS = 62;
const ROWS = 34;
const GAP = 0.3;
const IMPACT = 24;
const RIPPLE = 0.3; // units per frame
const SINK = 150;
const LETTER_AT = 172;
const MARK_SIZE = 9.4;
const WORD_Z = 1.2;
const WORD_W = 8.6;
const LETTER_COLS = ["#F47A5A", "#FFC94A", "#7FB0EA", "#9D8CE0", "#A9C47F", "#F29BB5", "#5C82D6"];
const BALL_R = 0.62;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const sp = (f: number, w = 2.4, z = 0.42) => (f <= 0 ? 0 : step(f / 30, { w: 2 * Math.PI * w, z }));
const inOut = (v: number) => {
  const k = clamp01(v);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};

/** Rasterise the mark once; sample it per pin. */
const useMarkMask = (res = 128) =>
  useMemo(() => {
    const c = document.createElement("canvas");
    c.width = res;
    c.height = res;
    const g = c.getContext("2d")!;
    g.scale(res / MARK_VB, res / MARK_VB);
    g.fill(new Path2D(MARK_D));
    const px = g.getImageData(0, 0, res, res).data;
    return (u: number, v: number) => {
      if (u < 0 || u >= 1 || v < 0 || v >= 1) return 0;
      return px[(Math.floor(v * res) * res + Math.floor(u * res)) * 4 + 3] / 255;
    };
  }, [res]);

/** Ball path: drop at the centre, roll out to the front-right, come back to nudge the "e". */
const ballAt = (t: number) => {
  const rest = 0.5 + BALL_R;
  let x = 0;
  let z = 0;
  let y = rest;
  if (t < IMPACT) {
    const u = clamp01((t - 6) / (IMPACT - 6));
    y = 10 - (10 - rest) * u * u;
  } else if (t < IMPACT + 26) {
    const u = (t - IMPACT) / 16;
    const v = (t - IMPACT - 16) / 10;
    y = rest + (u <= 1 ? 4 * 1.6 * u * (1 - u) : 4 * 0.4 * v * (1 - v));
  }
  const out = inOut((t - 54) / 50);
  const back = inOut((t - 232) / 26);
  x = 7.6 * out + (4.6 - 7.6) * back;
  z = 3.6 * out + (WORD_Z + 0.1 - 3.6) * back;
  const dist = 8.4 * out + 3.4 * back;
  return { x, y, z, roll: dist / BALL_R };
};

export const SoftDemo: React.FC = () => {
  const t = useCurrentFrame();
  const mask = useMarkMask();
  const shapes = useSvgShapes("brand/lockup.svg");
  const letters = useMemo(() => {
    if (!shapes) return [];
    const withBox = shapes.map((s) => {
      const pts = s.getPoints();
      const xs = pts.map((p) => p.x);
      return { s, x0: Math.min(...xs), x1: Math.max(...xs) };
    });
    return withBox.filter((b) => b.x0 > 225).sort((a, b) => a.x0 - b.x0);
  }, [shapes]);
  const span = letters.length ? [letters[0].x0, letters[letters.length - 1].x1] : [0, 1];
  const k = WORD_W / (span[1] - span[0]);
  const ball = ballAt(t);
  const markPins = (x: number, z: number) => mask((x + MARK_SIZE / 2) / MARK_SIZE, (z + MARK_SIZE / 2) / MARK_SIZE);
  const relief = (x: number, z: number) => {
    const d = Math.hypot(x, z);
    const act = IMPACT + d / RIPPLE;
    const up = sp(t - act, 2.2, 0.38) * markPins(x, z);
    const sink = sp(t - (SINK + (x + 9.3) * 1.3), 2, 0.7);
    return up * (1 - sink);
  };
  const height = (_i: number, _j: number, x: number, z: number) => {
    const d = Math.hypot(x, z);
    const since = t - (IMPACT + d / RIPPLE);
    const crest = t >= IMPACT ? 0.22 * Math.exp(-Math.pow(since / 4.5, 2)) * Math.exp(-d / 12) : 0;
    const bd = Math.hypot(x - ball.x, z - ball.z);
    const press = ball.y < 0.5 + BALL_R + 0.05 ? -0.26 * Math.exp(-Math.pow(bd / 0.55, 2)) : 0;
    return relief(x, z) * 0.9 + crest + press;
  };
  const base = useMemo(() => [new THREE.Color("#A9C6EE"), new THREE.Color("#BBA9EC"), new THREE.Color("#F2B3C6")], []);
  const coral = useMemo(() => new THREE.Color("#F36440"), []);
  const tmp = useMemo(() => new THREE.Color(), []);
  const color = (_i: number, _j: number, x: number, z: number) => {
    const u = clamp01((x + 9.3) / 18.6 + z * 0.02);
    const a = u < 0.5 ? base[0] : base[1];
    const b = u < 0.5 ? base[1] : base[2];
    tmp.copy(a).lerp(b, u < 0.5 ? u * 2 : (u - 0.5) * 2);
    tmp.lerp(coral, clamp01(relief(x, z) * 1.2));
    return `#${tmp.getHexString()}`;
  };
  const ballMat = useMemo(() => candy("#F36440", 0.22), []);
  const orbit = Math.sin(t * 0.006) * 1.6;
  // dolly from the pin-art overview down to the letters
  const d = inOut((t - 150) / 70);
  const camPos: [number, number, number] = [orbit * (1 - d) + 0.4 * d, 11.5 + (7.2 - 11.5) * d, 12.2 + (12.4 - 12.2) * d];
  const camLook: [number, number, number] = [0.2 * d, 0.9 * d, 0.7 + 0.4 * d];
  const title = clamp01((t - 262) / 18);
  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg, #EDE6FA 0%, #F8F1EC 60%, #F3E7E0 100%)" }}>
      <SoftCanvas pos={camPos} look={camLook} fov={33} tilt={0.05}>
        {/* the board */}
        <mesh position={[0, -0.25, 0]} receiveShadow>
          <boxGeometry args={[COLS * GAP + 0.5, 0.5, ROWS * GAP + 0.5]} />
          <meshPhysicalMaterial color="#D8CFF3" roughness={0.5} clearcoat={0.4} />
        </mesh>
        <PinField cols={COLS} rows={ROWS} gap={GAP} radius={0.12} length={0.26} t={t} height={height} color={color} />
        {/* ball */}
        <mesh position={[ball.x, ball.y, ball.z]} rotation={[ball.roll * 0.42, 0, -ball.roll * 0.9]} castShadow material={ballMat}>
          <sphereGeometry args={[BALL_R, 48, 32]} />
        </mesh>
        {/* puffy letters */}
        {letters.map((l, i) => (
          <Letter key={i} shape={l.s} k={k} i={i} t={t} x={((l.x0 + l.x1) / 2 - (span[0] + span[1]) / 2) * k} />
        ))}
      </SoftCanvas>
      <div style={{ position: "absolute", left: 0, right: 0, top: 930 + (1 - title) * 14, textAlign: "center", opacity: title, fontFamily: SLAB, fontWeight: 600, fontSize: 56, color: "#3B2F63", textShadow: "0 0 18px rgba(255,255,255,0.9), 0 0 36px rgba(255,255,255,0.7)" }}>From answers to outcomes.</div>
      <AbsoluteFill style={{ background: "#EDE6FA", opacity: 1 - clamp01(t / 10), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

const Letter: React.FC<{ shape: THREE.Shape; k: number; i: number; t: number; x: number }> = ({ shape, k, i, t, x }) => {
  const geo = usePuffGeometry(shape, k, 46, 10);
  const mat = useMemo(() => candy(LETTER_COLS[i % LETTER_COLS.length], 0.3), [i]);
  const at = LETTER_AT + i * 7;
  if (!geo || t < at) return null;
  const lt = t - at;
  const fall = 12;
  const floor = 0.5;
  let y = floor;
  let sy = 1;
  if (lt < fall) {
    const u = lt / fall;
    y = 7 - (7 - floor) * u * u;
    sy = 1.12;
  } else {
    const since = lt - fall;
    const squash = Math.exp(-since / 4) * Math.cos(since * 0.55) * 0.28;
    sy = 1 - squash;
    const hop = since < 10 ? 4 * 0.35 * (since / 10) * (1 - since / 10) : 0;
    y = floor + hop;
  }
  // the ball nudges the last letter
  const nudge = i === 6 && t > 256 ? Math.sin((t - 256) * 0.5) * Math.exp(-(t - 256) / 10) * 0.22 : 0;
  return (
    <mesh geometry={geo} material={mat} position={[x, y, WORD_Z]} scale={[1 / Math.sqrt(sy), sy, 1 / Math.sqrt(sy)]} rotation={[0, (i - 3) * -0.04, nudge]} castShadow receiveShadow />
  );
};
