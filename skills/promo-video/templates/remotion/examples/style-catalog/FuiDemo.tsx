import React from "react";
import { AbsoluteFill, staticFile, useCurrentFrame } from "remotion";
import { DataColumn, FUI, FuiPanel, Radar, Readout, Reticle, Scanlines, WireGlobe, type GlobeNode } from "../cinematic/fui";
import { fam } from "../cinematic/type";

/** 08 · 赛博朋克 HUD — "YouWare Mission Control": one brief, four agent tasks, a globe of links, the outcome locks on. 330 frames. */
export const FUI_LEN = 330;
const MONO = fam("Geist Mono");
const SANS = fam("Manrope");

const NODES: GlobeNode[] = [
  { lat: 37.8, lng: -122.4 },
  { lat: 40.7, lng: -74 },
  { lat: 51.5, lng: -0.1 },
  { lat: 52.5, lng: 13.4 },
  { lat: 35.7, lng: 139.7 },
  { lat: 1.35, lng: 103.8 },
  { lat: 31.2, lng: 121.5 },
  { lat: -33.9, lng: 151.2 },
];
const ARCS: [number, number][] = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 6],
  [6, 4],
  [4, 5],
  [5, 7],
  [0, 4],
];
const TASKS = [
  { name: "RESEARCH", at: 40 },
  { name: "OUTLINE", at: 92 },
  { name: "DESIGN", at: 144 },
  { name: "BUILD", at: 196 },
];
const TASK_LEN = 52;

export const FuiDemo: React.FC = () => {
  const t = useCurrentFrame();
  const flick = t < 14 ? (Math.floor(t / 2) % 2 ? 0.35 : 1) * (t / 14) + (t >= 12 ? 0.2 : 0) : 1;
  const done = TASKS.filter((k) => t >= k.at + TASK_LEN).length;
  const links = ARCS.filter((_, i) => t >= 40 + i * 9 + 24).length;
  const secs = (t / 30).toFixed(2).padStart(5, "0");
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 52%, #0A2330 0%, ${FUI.bg} 62%)`, opacity: Math.min(1, flick), overflow: "hidden" }}>
      <WireGlobe t={t} nodes={NODES} arcs={ARCS} width={1920} height={1080} zoom={0.8} lock={t > 262 ? 4 : undefined} />
      {/* header */}
      <div style={{ position: "absolute", left: 80, top: 60, display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ width: 34, height: 34, WebkitMaskImage: `url(${staticFile("brand/mark.svg")})`, WebkitMaskSize: "100% 100%", background: FUI.cyan }} />
        <div style={{ fontFamily: MONO, fontSize: 20, letterSpacing: "0.26em", color: FUI.cyan }}>YOUWARE // MISSION CONTROL</div>
      </div>
      <div style={{ position: "absolute", right: 80, top: 62, fontFamily: MONO, fontSize: 18, letterSpacing: "0.2em", color: FUI.cyan }}>T+ {secs}</div>
      {/* tasks */}
      <FuiPanel x={80} y={170} w={400} h={400} title="AGENT TASKS" mono={MONO} t={t} at={8}>
        {TASKS.map((k, i) => {
          const p = Math.min(1, Math.max(0, (t - k.at) / TASK_LEN));
          const ok = p >= 1;
          return (
            <div key={k.name} style={{ marginTop: i ? 26 : 8, fontFamily: MONO }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 16, letterSpacing: "0.16em", color: ok ? FUI.amber : FUI.cyan }}>
                <span>
                  0{i + 1} {k.name}
                </span>
                <span>{ok ? "DONE" : p > 0 ? `${Math.round(p * 100)}%` : "QUEUED"}</span>
              </div>
              <div style={{ marginTop: 8, height: 8, background: "rgba(63,224,255,0.12)", display: "flex", gap: 2 }}>
                {Array.from({ length: 24 }, (_, j) => (
                  <div key={j} style={{ flex: 1, background: j / 24 < p ? (ok ? FUI.amber : FUI.cyan) : "transparent", boxShadow: j / 24 < p ? `0 0 8px ${ok ? FUI.amber : FUI.cyan}` : undefined }} />
                ))}
              </div>
            </div>
          );
        })}
      </FuiPanel>
      <FuiPanel x={80} y={610} w={400} h={330} title="LOG" mono={MONO} t={t} at={16}>
        <DataColumn t={t} lines={14} mono={MONO} size={14} />
      </FuiPanel>
      {/* radar + readouts */}
      <FuiPanel x={1440} y={170} w={400} h={420} title="SCAN" mono={MONO} t={t} at={12}>
        <div style={{ display: "grid", placeItems: "center", height: "100%" }}>
          <Radar t={t} size={320} blips={[[30, 0.6], [110, 0.35], [200, 0.8], [290, 0.5], [340, 0.25]]} />
        </div>
      </FuiPanel>
      <FuiPanel x={1440} y={630} w={400} h={310} title="STATUS" mono={MONO} t={t} at={20}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", rowGap: 22 }}>
          <Readout t={t} at={24} value={done} digits={1} label="TASKS DONE / 4" mono={MONO} color={done === 4 ? FUI.amber : FUI.cyan} />
          <Readout t={t} at={24} value={links} digits={1} label={`LINKS / ${ARCS.length}`} mono={MONO} />
          <Readout t={t} at={30} value={NODES.length} digits={1} label="NODES" mono={MONO} />
          <Readout t={t} at={30} value={Number(secs)} digits={5} decimals={2} label="ELAPSED S" mono={MONO} size={30} />
        </div>
      </FuiPanel>
      <Reticle t={t} at={250} x={960} y={560} size={300} label="OUTCOME · DECK READY" sub="4 / 4 TASKS COMPLETE" mono={MONO} />
      {t >= 272 && (
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 70, textAlign: "center", fontFamily: SANS, fontWeight: 700, fontSize: 30, letterSpacing: "0.3em", color: FUI.amber, textShadow: `0 0 16px ${FUI.amber}`, opacity: Math.min(1, (t - 272) / 8) }}>
          FROM ANSWERS TO OUTCOMES
        </div>
      )}
      <Scanlines t={t} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 60%, rgba(0,0,0,0.6) 100%)", pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
