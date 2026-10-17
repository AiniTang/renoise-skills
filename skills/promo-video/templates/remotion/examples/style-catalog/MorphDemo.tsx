import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import type { SpecimenTheme } from "../cinematic/specimen";
import { CHAIN_LEN, YouWareChain } from "../youware-ladder/YouWareChain";

/** 04 · 形变动画 — the YouWare product-detail morph chain (prompt → site → slides → sheet → report → heads → team → dot). 300 frames. */
export const MORPH_LEN = 330;
const PRE = 16;

export const MORPH_TH: SpecimenTheme = {
  ink: "#151513",
  paper: "#F5F0E6",
  paper2: "#ECE5D6",
  cream: "#F4EEE2",
  accent: "#CFE3A0",
  accent2: "#EE8C6C",
  palette: [],
  sprinkle: ["#B4A5E4", "#CFE3A0", "#EE8C6C", "#4FA597", "#86A8DA", "#BBC98D"],
  serif: '"Hepta Slab", Georgia, serif',
  sans: '"Manrope", -apple-system, sans-serif',
  mono: '"Geist Mono", Menlo, monospace',
};

export const MorphDemo: React.FC<{ t?: number }> = ({ t: tProp }) => {
  const frame = useCurrentFrame();
  const t = tProp ?? frame;
  return (
    <AbsoluteFill>
      <YouWareChain th={MORPH_TH} t={Math.min(CHAIN_LEN, Math.max(0, t - PRE))} />
      {t - PRE >= 242 && <div style={{ position: "absolute", left: 960 - 14, top: 520 - 14, width: 28, height: 28, borderRadius: "50%", background: MORPH_TH.ink, transform: `scale(${Math.min(1, (t - PRE - 242) / 4)})` }} />}
    </AbsoluteFill>
  );
};
