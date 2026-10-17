import React, { useMemo } from "react";

/* A client's own line drawing, drawn in pen order (first used on the HEYTEA film, 2026-10-02).
   Data: scripts/pen_order.py → pen json (centre-line strokes in drawing order, brush width = local line width)
         scripts/vectorize_lineart.py → vec json (the drawing as one even-odd path, sharp at 4K)
   The strokes are only a MASK: what appears is always the client's drawing, revealed stroke by stroke.

   import PEN from "./pen.json"; import VEC from "./vec.json";
   <PenArt pen={PEN.drinker} vec={VEC.drinker} t={t} at={41.99} dur={0.93} x={508} y={120} h={860} id="drinker" />
   // a group from pen_order.py --group pops on its own (vec of <name>-<group>, main drawing = <name>-main):
   <PenArt pen={PEN.phone} vec={VEC["phone-main"]} groups={{ hey: { at: 2.2, dur: 0.16, pop: true, vec: VEC["phone-hey"] } }} … />  */

export type PenStroke = { d: string; len: number; w: number; lift?: number; g?: string };
export type PenSet = { w: number; h: number; strokes: PenStroke[]; groups?: Record<string, { cx: number; cy: number }> };
export type VecArt = { w: number; h: number; d: string; color: string };
export type PenGroupCue = { at: number; dur: number; pop?: boolean; vec: VecArt };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const sine = (x: number) => -(Math.cos(Math.PI * x) - 1) / 2;
const spring = (lt: number, k = 18, z = 0.35) => (lt <= 0 ? 0 : 1 - Math.exp(-z * k * lt) * Math.cos(k * Math.sqrt(1 - z * z) * lt));
const LIFT = 6; // pen-lift pause between strokes, in px of travel

const plan = (S: PenSet, group: string) => {
  let acc = 0;
  const items: { s: PenStroke; a: number; z: number }[] = [];
  for (const s of S.strokes) {
    if ((s.g ?? "main") !== group) continue;
    const a = acc;
    acc += s.len * (1 + s.w / 60); // fat brushes (solid shapes) ink in more slowly, else they pop in two frames
    items.push({ s, a, z: acc });
    if (s.lift) acc += LIFT;
  }
  return { items, total: acc };
};

const PenMask: React.FC<{ id: string; S: PenSet; P: ReturnType<typeof plan>; head: number; full: number }> = ({ id, S, P, head, full }) => (
  <mask id={id} maskUnits="userSpaceOnUse" x={-200} y={-200} width={S.w + 400} height={S.h + 400}>
    {P.items.map(({ s, a, z }, i) => {
      const p = clamp01((head - a) / Math.max(0.5, z - a));
      if (p <= 0) return null;
      return <path key={i} d={s.d} fill="none" stroke="white" strokeWidth={s.w} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={p >= 1 ? undefined : `${p} 2`} />;
    })}
    {/* safety net: anything the brush missed fades in right after the pen finishes */}
    {full > 0.001 && <rect x={-200} y={-200} width={S.w + 400} height={S.h + 400} fill="white" opacity={full} />}
  </mask>
);

export const PenArt: React.FC<{
  pen: PenSet;
  vec: VecArt;
  t: number;
  at: number;
  dur: number;
  x: number;
  y: number;
  h: number;
  id: string;
  groups?: Record<string, PenGroupCue>;
  ease?: (x: number) => number;
  color?: string;
  style?: React.CSSProperties;
}> = ({ pen: S, vec, t, at, dur, x, y, h, id, groups, ease = sine, color, style }) => {
  const main = useMemo(() => plan(S, "main"), [S]);
  const gplans = useMemo(() => Object.fromEntries(Object.keys(S.groups ?? {}).map((g) => [g, plan(S, g)])), [S]);
  if (t < at) return null;
  const w = (h * S.w) / S.h;
  const head = ease(clamp01((t - at) / dur)) * main.total;
  const full = clamp01((t - at - dur) / 0.18);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${S.w} ${S.h}`} style={{ position: "absolute", left: x, top: y, overflow: "visible", ...style }}>
      <defs>
        <PenMask id={`pm-${id}`} S={S} P={main} head={head} full={full} />
        {Object.entries(groups ?? {}).map(([g, cue]) =>
          gplans[g] ? <PenMask key={g} id={`pm-${id}-${g}`} S={S} P={gplans[g]} head={clamp01((t - cue.at) / cue.dur) * gplans[g].total} full={clamp01((t - cue.at - cue.dur) / 0.12)} /> : null,
        )}
      </defs>
      <path d={vec.d} fill={color ?? vec.color} fillRule="evenodd" mask={`url(#pm-${id})`} />
      {Object.entries(groups ?? {}).map(([g, cue]) => {
        const G = S.groups?.[g];
        if (!G || t < cue.at) return null;
        const k = cue.pop ? 0.4 + 0.6 * spring(t - cue.at) : 1;
        return (
          <g key={g} transform={`translate(${G.cx} ${G.cy}) scale(${k}) translate(${-G.cx} ${-G.cy})`}>
            <path d={cue.vec.d} fill={color ?? cue.vec.color} fillRule="evenodd" mask={`url(#pm-${id}-${g})`} />
          </g>
        );
      })}
    </svg>
  );
};
