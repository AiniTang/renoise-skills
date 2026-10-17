import React from "react";
import { AbsoluteFill } from "remotion";
import { SvgPlayer } from "./SvgPlayer";
import { SVG_SOL } from "./svgs";

// zoom on the sun two ways: G = our group transform, V = root viewBox set to the window (spec-clear for px origins)
const W: [number, number, number, number] = [40, 10, 480, 290];
export const RaysTest: React.FC<{ v: string }> = ({ v }) => (
  <AbsoluteFill style={{ background: "#fff" }}>
    <div style={{ position: "absolute", left: 0, top: 0, width: 1760, height: 1063 }}>
      {v === "G" ? (
        <SvgPlayer markup={SVG_SOL} prefix="sol" time={3.3} base={[0, 0, 960, 580]} win={W} />
      ) : (
        <SvgPlayer markup={SVG_SOL.replace('viewBox="0 0 960 580"', `viewBox="${W.join(" ")}"`)} prefix="sol" time={3.3} base={[0, 0, 960, 580]} />
      )}
    </div>
  </AbsoluteFill>
);
