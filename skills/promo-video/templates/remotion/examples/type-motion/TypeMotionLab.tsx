import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Decode, HandReveal, OutlineFill, TrackIn, VarType, fam, useFontManifest } from "../cinematic/type";

/**
 * Type motion lab: one row per typographic motion. Fonts come from `scripts/fonts.py fetch … --to <project>`:
 *   fraunces caveat gloock anybody instrument-serif departure-mono lxgw-wenkai
 * Register: <Composition id="TypeMotionLab" component={TypeMotionLab} width={1920} height={1080} fps={30} durationInFrames={150} />
 */
export const TypeMotionLab: React.FC = () => {
  const faces = useFontManifest();
  const f = useCurrentFrame();
  if (!faces) return <AbsoluteFill style={{ background: "#F5F1E8" }} />;
  const row = (y: number, label: string, node: React.ReactNode) => (
    <div style={{ position: "absolute", left: 120, top: y, display: "flex", alignItems: "baseline", gap: 40 }}>
      <div style={{ width: 170, font: '600 14px "SF Mono", Menlo, monospace', letterSpacing: "0.14em", color: "rgba(21,21,19,0.45)" }}>{label}</div>
      {node}
    </div>
  );
  return (
    <AbsoluteFill style={{ background: "#F5F1E8", color: "#151513" }}>
      {row(70, "VARTYPE · SOFT", <VarType text="Fresh flowers, every morning." family={fam("Fraunces")} size={96} weight={[300, 560]} axes={{ SOFT: [0, 100], WONK: [0, 1], opsz: [144, 144] }} at={0} stagger={1.1} />)}
      {row(250, "VARTYPE · WDTH", <VarType text="STRETCH" family={fam("Anybody")} size={110} weight={[800, 800]} axes={{ wdth: [50, 140] }} at={10} stagger={2} dur={24} blur={0} tracking={0} />)}
      {row(430, "TRACK IN", <TrackIn text="MAISON FLEUR" family={fam("Gloock")} size={84} at={0} dur={70} from={0.6} to={0.04} />)}
      {row(580, "HAND REVEAL", <HandReveal text="a website for my flower shop?" family={fam("Caveat")} size={70} weight={600} at={4} cps={16} />)}
      {row(700, "中文手写", <HandReveal text="从答案，到成果。" family={fam("LXGW WenKai", "zh-Hans")} size={64} weight={400} at={20} cps={6} />)}
      {row(830, "DECODE", <Decode text="SIGNAL · 290+ SUBREDDITS" family={fam("Departure Mono")} size={40} at={6} perChar={1.1} />)}
      <OutlineFill parts={[{ t: "From answers " }, { t: "to outcomes.", fill: true }]} family={fam("Instrument Serif")} size={74} weight={400} x={1250} y={1010} width={900} writeAt={20} writeDur={60} fillAt={95} />
      <div style={{ position: "absolute", left: 120, top: 975, font: '600 14px "SF Mono", Menlo, monospace', letterSpacing: "0.14em", color: "rgba(21,21,19,0.45)" }}>OUTLINE → FILL</div>
      <div style={{ position: "absolute", right: 60, top: 40, font: '500 13px "SF Mono", Menlo, monospace', color: "rgba(21,21,19,0.4)" }}>f {f}</div>
    </AbsoluteFill>
  );
};
