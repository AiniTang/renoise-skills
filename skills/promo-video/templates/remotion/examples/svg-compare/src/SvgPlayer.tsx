import React, { useLayoutEffect, useRef } from "react";

export type Box4 = [number, number, number, number];

/**
 * Plays an animated SVG frame-deterministically.
 * - SMIL: paused and seeked with setCurrentTime().
 * - CSS animations: the markup (tools/prep_svgs.py) forces every animation paused with animation-delay = -var(--t)s,
 *   so the style itself encodes the time. (Seeking through getAnimations() raced the first style pass: animations
 *   that did not exist yet kept running on wall-clock time and two renders of one frame differed.)
 * - Zoom: `win` (a window inside `base`, the root viewBox) is shown full-size by transforming the #<p>-zoom group —
 *   the root viewBox never changes, so view-box-relative transform-origins stay put. Still pure vector.
 */
export const SvgPlayer: React.FC<{ markup: string; prefix: string; time: number; base: Box4; win?: Box4; style?: React.CSSProperties }> = ({ markup, prefix, time, base, win, style }) => {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const root = ref.current;
    const svg = root?.querySelector("svg") as SVGSVGElement | null;
    if (!svg) return;
    const t = Math.max(0, time);
    svg.style.setProperty("--t", t.toFixed(4));
    svg.pauseAnimations();
    svg.setCurrentTime(t);
    const g = root?.querySelector(`#${prefix}-zoom`);
    if (g) {
      const w = win ?? base;
      const k = base[2] / w[2];
      const tx = base[0] - w[0] * k;
      const ty = base[1] - w[1] * k;
      g.setAttribute("transform", `translate(${tx.toFixed(3)} ${ty.toFixed(3)}) scale(${k.toFixed(5)})`);
    }
  });
  return <div ref={ref} style={{ width: "100%", height: "100%", ...style }} dangerouslySetInnerHTML={{ __html: markup }} />;
};
