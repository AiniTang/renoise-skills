import React, { useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { random } from "remotion";

/*
 * Sci-fi interface kit (赛博朋克 HUD / FUI): wireframe globe with arcs and travelling pulses (three.js + bloom),
 * radar sweep, lock-on reticle, scrolling data column, ticking readouts, cut-corner panels, scanlines.
 * All pure functions of the local frame `t` (30 fps).
 */

export const FUI = { bg: "#03080D", cyan: "#3FE0FF", teal: "#1FB7C9", dim: "rgba(63,224,255,0.28)", amber: "#FFA23A", red: "#FF4D5E", white: "#E8FBFF" };
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/* ── globe ─────────────────────────────────────────────────────────────── */

const latLng = (lat: number, lng: number, r: number) => {
  const phi = ((90 - lat) * Math.PI) / 180;
  const th = ((lng + 180) * Math.PI) / 180;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
};

export type GlobeNode = { lat: number; lng: number };

const GlobeRig: React.FC<{ dist: number }> = ({ dist }) => {
  const { camera } = useThree();
  camera.position.set(0, 0.35, dist);
  camera.lookAt(0, 0, 0);
  return null;
};

const Globe: React.FC<{ t: number; nodes: GlobeNode[]; arcs: [number, number][]; lock?: number; color: string; lockColor: string; draw: number }> = ({ t, nodes, arcs, lock, color, lockColor, draw }) => {
  const R = 1;
  const grid = useMemo(() => {
    const pts: number[] = [];
    for (let lat = -75; lat <= 75; lat += 15)
      for (let lng = -180; lng < 180; lng += 4) {
        const a = latLng(lat, lng, R);
        const b = latLng(lat, lng + 4, R);
        pts.push(a.x, a.y, a.z, b.x, b.y, b.z);
      }
    for (let lng = -180; lng < 180; lng += 20)
      for (let lat = -88; lat < 88; lat += 4) {
        const a = latLng(lat, lng, R);
        const b = latLng(lat + 4, lng, R);
        pts.push(a.x, a.y, a.z, b.x, b.y, b.z);
      }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return g;
  }, []);
  // procedural "land" dots: a smooth noise field on the sphere
  const dots = useMemo(() => {
    const pts: number[] = [];
    for (let i = 0; i < 5200; i++) {
      const lat = Math.asin(2 * random(`gl${i}`) - 1) * (180 / Math.PI);
      const lng = random(`gn${i}`) * 360 - 180;
      const n = Math.sin(lat * 0.09 + 1.3) * Math.cos(lng * 0.05) + Math.sin(lng * 0.11 - lat * 0.05) * 0.6;
      if (n > 0.35) {
        const p = latLng(lat, lng, R * 1.003);
        pts.push(p.x, p.y, p.z);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return g;
  }, []);
  const arcCurves = useMemo(
    () =>
      arcs.map(([a, b]) => {
        const p0 = latLng(nodes[a].lat, nodes[a].lng, R);
        const p2 = latLng(nodes[b].lat, nodes[b].lng, R);
        const mid = p0.clone().add(p2).multiplyScalar(0.5);
        const lift = 1 + 0.35 * p0.distanceTo(p2);
        const p1 = mid.normalize().multiplyScalar(R * lift);
        return new THREE.QuadraticBezierCurve3(p0, p1, p2);
      }),
    [arcs, nodes],
  );
  const arcLines = useMemo(
    () => arcCurves.map((c) => new THREE.Line(new THREE.BufferGeometry().setFromPoints(c.getPoints(60)), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.85 }))),
    [arcCurves, color],
  );
  const col = new THREE.Color(color);
  const lcol = new THREE.Color(lockColor);
  return (
    <group rotation={[0.35, t * 0.006 + 0.6, 0]}>
      <mesh>
        <sphereGeometry args={[R * 0.985, 48, 32]} />
        <meshBasicMaterial color="#021018" transparent opacity={0.85} />
      </mesh>
      <lineSegments geometry={grid}>
        <lineBasicMaterial color={col} transparent opacity={0.22 * draw} />
      </lineSegments>
      <points geometry={dots}>
        <pointsMaterial color={col} size={0.012} sizeAttenuation transparent opacity={0.9 * draw} />
      </points>
      {arcCurves.map((c, i) => {
        const on = clamp01((t - 40 - i * 9) / 24);
        if (on <= 0) return null;
        const line = arcLines[i];
        line.geometry.setDrawRange(0, Math.max(2, Math.floor(61 * on)));
        const pulseU = ((t - 40 - i * 9) / 45) % 1;
        const pp = c.getPoint(Math.max(0, pulseU));
        return (
          <group key={i}>
            <primitive object={line} />
            {on >= 1 && (
              <mesh position={pp}>
                <sphereGeometry args={[0.018, 8, 8]} />
                <meshBasicMaterial color={FUI.white} />
              </mesh>
            )}
          </group>
        );
      })}
      {nodes.map((n, i) => {
        const p = latLng(n.lat, n.lng, R * 1.01);
        const isLock = lock !== undefined && i === lock;
        const pulse = 1 + 0.4 * Math.sin(t * 0.25 + i);
        return (
          <mesh key={i} position={p} scale={pulse * (isLock ? 1.6 : 1)}>
            <sphereGeometry args={[0.022, 10, 10]} />
            <meshBasicMaterial color={isLock ? lcol : col} />
          </mesh>
        );
      })}
    </group>
  );
};

/** Wireframe globe canvas. Place it in a box; it renders at the given width/height. */
export const WireGlobe: React.FC<{ t: number; nodes: GlobeNode[]; arcs: [number, number][]; lock?: number; width: number; height: number; color?: string; lockColor?: string; zoom?: number }> = ({
  t,
  nodes,
  arcs,
  lock,
  width,
  height,
  color = FUI.cyan,
  lockColor = FUI.amber,
  zoom = 1,
}) => (
  <ThreeCanvas resize={{ offsetSize: true, scroll: false }} width={width} height={height} camera={{ fov: 30, position: [0, 0, 4.2] }} gl={{ alpha: true, antialias: true }} style={{ position: "absolute", inset: 0 }}>
    <GlobeRig dist={4.2 / zoom} />
    <Globe t={t} nodes={nodes} arcs={arcs} lock={lock} color={color} lockColor={lockColor} draw={clamp01(t / 30)} />
    <EffectComposer multisampling={4}>
      <Bloom intensity={1.1} luminanceThreshold={0.05} luminanceSmoothing={0.3} mipmapBlur />
    </EffectComposer>
  </ThreeCanvas>
);

/* ── 2D pieces ─────────────────────────────────────────────────────────── */

/** Panel with cut corners, tick marks and a header. */
export const FuiPanel: React.FC<{ x: number; y: number; w: number; h: number; title: string; mono: string; t: number; at?: number; color?: string; children?: React.ReactNode }> = ({
  x,
  y,
  w,
  h,
  title,
  mono,
  t,
  at = 0,
  color = FUI.cyan,
  children,
}) => {
  const k = clamp01((t - at) / 12);
  const c = 14;
  const path = `M ${c} 0 H ${w - c} L ${w} ${c} V ${h - c} L ${w - c} ${h} H ${c} L 0 ${h - c} V ${c} Z`;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, opacity: k, transform: `scaleY(${0.3 + 0.7 * k})`, transformOrigin: "50% 0%" }}>
      <svg width={w} height={h} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <path d={path} fill="rgba(3,20,28,0.55)" stroke={color} strokeOpacity={0.55} strokeWidth={1.4} />
        {Array.from({ length: 12 }, (_, i) => (
          <line key={i} x1={c + ((w - 2 * c) * i) / 11} x2={c + ((w - 2 * c) * i) / 11} y1={h} y2={h - (i % 3 === 0 ? 8 : 4)} stroke={color} strokeOpacity={0.5} />
        ))}
        <rect x={0} y={-3} width={42} height={3} fill={color} />
      </svg>
      <div style={{ position: "absolute", left: 18, top: 12, fontFamily: mono, fontSize: 13, letterSpacing: "0.2em", color }}>{title}</div>
      <div style={{ position: "absolute", left: 18, top: 40, right: 18, bottom: 16 }}>{children}</div>
    </div>
  );
};

/** Radar: range rings, a conic sweep with a fading trail, blips that flash when the beam passes. */
export const Radar: React.FC<{ t: number; size: number; color?: string; blips?: [number, number][]; speed?: number }> = ({ t, size, color = FUI.cyan, blips = [], speed = 4 }) => {
  const ang = (t * speed) % 360;
  const r = size / 2;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: `conic-gradient(from ${ang - 60}deg, transparent 0deg, ${color}00 0deg, ${color}66 58deg, ${color} 60deg, transparent 60.5deg)`, opacity: 0.55 }} />
      <svg width={size} height={size} style={{ position: "absolute", inset: 0 }}>
        {[0.33, 0.66, 1].map((k) => (
          <circle key={k} cx={r} cy={r} r={r * k - 1} fill="none" stroke={color} strokeOpacity={0.35} />
        ))}
        <line x1={r} y1={0} x2={r} y2={size} stroke={color} strokeOpacity={0.2} />
        <line x1={0} y1={r} x2={size} y2={r} stroke={color} strokeOpacity={0.2} />
        {blips.map(([a, d], i) => {
          const diff = (((ang - a) % 360) + 360) % 360;
          const glow = Math.exp(-diff / 50);
          const x = r + Math.cos(((a - 90) * Math.PI) / 180) * d * r;
          const y = r + Math.sin(((a - 90) * Math.PI) / 180) * d * r;
          return <circle key={i} cx={x} cy={y} r={3 + 3 * glow} fill={color} opacity={0.25 + 0.75 * glow} />;
        })}
      </svg>
    </div>
  );
};

/** Lock-on reticle: brackets close in, a dashed ring spins, label flips to LOCKED in amber. */
export const Reticle: React.FC<{ t: number; at: number; x: number; y: number; size?: number; label: string; mono: string; sub?: string }> = ({ t, at, x, y, size = 180, label, mono, sub }) => {
  const lt = t - at;
  if (lt < 0) return null;
  const close = clamp01(lt / 16);
  const locked = lt > 18;
  const col = locked ? FUI.amber : FUI.cyan;
  const s = size * (1.9 - 0.9 * (1 - Math.pow(1 - close, 3)));
  const blink = locked && Math.floor(lt / 4) % 2 === 0 ? 1 : 0.85;
  const b = s * 0.22;
  return (
    <div style={{ position: "absolute", left: x - s / 2, top: y - s / 2, width: s, height: s, opacity: blink }}>
      <svg width={s} height={s} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        {[
          [0, 0, 1, 1],
          [s, 0, -1, 1],
          [0, s, 1, -1],
          [s, s, -1, -1],
        ].map(([cx, cy, dx, dy], i) => (
          <path key={i} d={`M ${cx} ${cy + dy * b} V ${cy} H ${cx + dx * b}`} fill="none" stroke={col} strokeWidth={3} />
        ))}
        <circle cx={s / 2} cy={s / 2} r={s * 0.34} fill="none" stroke={col} strokeWidth={1.5} strokeDasharray="6 8" transform={`rotate(${lt * 4} ${s / 2} ${s / 2})`} />
        <line x1={s / 2 - 10} x2={s / 2 + 10} y1={s / 2} y2={s / 2} stroke={col} />
        <line x1={s / 2} x2={s / 2} y1={s / 2 - 10} y2={s / 2 + 10} stroke={col} />
      </svg>
      <div style={{ position: "absolute", left: s + 12, top: s * 0.28, fontFamily: mono, fontSize: 16, letterSpacing: "0.18em", color: col, whiteSpace: "nowrap" }}>
        <div style={{ background: locked ? FUI.amber : "transparent", color: locked ? FUI.bg : col, padding: "3px 8px", display: "inline-block", border: `1px solid ${col}` }}>{locked ? "LOCKED" : "SEARCHING"}</div>
        <div style={{ marginTop: 8 }}>{label}</div>
        {sub && <div style={{ marginTop: 4, opacity: 0.7, fontSize: 13 }}>{sub}</div>}
      </div>
    </div>
  );
};

/** Scrolling log / hex column. */
export const DataColumn: React.FC<{ t: number; lines: number; mono: string; color?: string; seed?: string; speed?: number; size?: number }> = ({ t, lines, mono, color = FUI.cyan, seed = "dc", speed = 0.35, size = 13 }) => {
  const off = t * speed;
  const first = Math.floor(off);
  const frac = off - first;
  const hex = (i: number) =>
    `${String(((first + i) * 7) % 1000).padStart(3, "0")}  0x${Math.floor(random(`${seed}${first + i}`) * 0xffffff)
      .toString(16)
      .padStart(6, "0")
      .toUpperCase()}  ${["SYNC", "PASS", "BUILD", "READ", "LINK", "OK"][Math.floor(random(`${seed}w${first + i}`) * 6)]}`;
  return (
    <div style={{ fontFamily: mono, fontSize: size, lineHeight: 1.55, color, overflow: "hidden", height: lines * size * 1.55, transform: `translateY(${-frac * size * 1.55}px)` }}>
      {Array.from({ length: lines + 1 }, (_, i) => (
        <div key={i} style={{ opacity: 0.35 + 0.65 * (i / lines) }}>
          {hex(i)}
        </div>
      ))}
    </div>
  );
};

/** A number that rolls toward its target with jittery digits. */
export const Readout: React.FC<{ t: number; at: number; value: number; digits?: number; label: string; mono: string; color?: string; size?: number; decimals?: number }> = ({
  t,
  at,
  value,
  digits = 4,
  label,
  mono,
  color = FUI.cyan,
  size = 40,
  decimals = 0,
}) => {
  const k = clamp01((t - at) / 24);
  const e = 1 - Math.pow(1 - k, 3);
  const jitter = k < 1 ? (random(`ro${Math.floor(t)}`) - 0.5) * value * 0.02 : 0;
  const v = (value * e + jitter).toFixed(decimals).padStart(digits, "0");
  return (
    <div style={{ fontFamily: mono, color }}>
      <div style={{ fontSize: 12, letterSpacing: "0.2em", opacity: 0.7 }}>{label}</div>
      <div style={{ fontSize: size, fontWeight: 500, letterSpacing: "0.04em" }}>{v}</div>
    </div>
  );
};

/** CRT scanlines + vignette. */
export const Scanlines: React.FC<{ t: number; opacity?: number }> = ({ t, opacity = 0.18 }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      pointerEvents: "none",
      opacity,
      background: `repeating-linear-gradient(0deg, rgba(0,0,0,0.9) 0px, rgba(0,0,0,0.9) 1px, transparent 1px, transparent 3px)`,
      backgroundPositionY: `${(t * 0.6) % 3}px`,
      mixBlendMode: "multiply",
    }}
  />
);
