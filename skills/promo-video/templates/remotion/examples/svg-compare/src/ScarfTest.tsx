import React from "react";
import { AbsoluteFill } from "remotion";
import { SvgPlayer } from "./SvgPlayer";
import { SVG_G61 } from "./svgs";

// A: original viewBox · B: widened viewBox, original pivot (prep output) · C: widened + pivot shifted by 50 (wrong)
const VARIANTS: Record<string, { markup: string; base: [number, number, number, number] }> = {
  A: { markup: SVG_G61.replace('viewBox="-50 0 860 520"', 'viewBox="0 0 760 520"'), base: [0, 0, 760, 520] },
  B: { markup: SVG_G61, base: [-50, 0, 860, 520] },
  C: { markup: SVG_G61.replace("transform-origin:450px 238px", "transform-origin:500px 238px"), base: [-50, 0, 860, 520] },
};
export const ScarfTest: React.FC<{ v: string }> = ({ v }) => (
  <AbsoluteFill style={{ background: "#FFFDF5" }}>
    <div style={{ position: "absolute", left: 0, top: 0, width: 1720, height: 1040 }}>
      <SvgPlayer markup={VARIANTS[v].markup} prefix="g61" time={0.4} base={VARIANTS[v].base} />
    </div>
  </AbsoluteFill>
);
