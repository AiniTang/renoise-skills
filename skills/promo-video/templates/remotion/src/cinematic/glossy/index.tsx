import React from "react";

/*
 * Glossy liquid kit (液态流动). `GlossyDefs` is an SVG filter that turns flat shapes (circles, ellipses, text) into
 * merged, shiny liquid: blur + alpha threshold (metaballs), then diffuse + specular lighting that uses the blob's own
 * blurred alpha as a height map, so every blob gets a domed body, a soft rim and a wet highlight. Put the shapes in
 * `<g filter="url(#id)">` inside a full-frame <svg>. All props are plain numbers, so animating `blur` or `light`
 * per frame stays deterministic. Complements ../Liquid.tsx (flat goo, blob morphing).
 *
 * Tips: keep `blur` ≈ 0.2 × the smallest blob radius (smaller blobs vanish under the threshold); text needs
 * blur ≤ 10 to keep its counters; `dome` sets how far the bevel reaches into a shape (bigger = rounder).
 */

export const GlossyDefs: React.FC<{
  id?: string;
  blur?: number;
  dome?: number;
  light?: [number, number, number];
  spec?: number;
  shine?: number;
  w?: number;
  h?: number;
}> = ({ id = "glossy", blur = 16, dome = 14, light = [620, 160, 380], spec = 1.25, shine = 34, w = 1920, h = 1080 }) => (
  <svg width={0} height={0} style={{ position: "absolute" }}>
    <defs>
      <filter id={id} filterUnits="userSpaceOnUse" x={0} y={0} width={w} height={h} colorInterpolationFilters="sRGB">
        <feGaussianBlur in="SourceGraphic" stdDeviation={blur} result="blur" />
        <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 26 -11" result="goo" />
        <feGaussianBlur in="goo" stdDeviation={dome} result="bump" />
        <feDiffuseLighting in="bump" surfaceScale={dome * 0.5} diffuseConstant={1} lightingColor="#FFFFFF" result="diff">
          <feDistantLight azimuth={235} elevation={55} />
        </feDiffuseLighting>
        <feComposite in="goo" in2="diff" operator="arithmetic" k1={1.08} k2={0.1} k3={0} k4={0} result="shaded" />
        <feSpecularLighting in="bump" surfaceScale={dome * 0.7} specularConstant={spec} specularExponent={shine} lightingColor="#FFFFFF" result="spec">
          <fePointLight x={light[0]} y={light[1]} z={light[2]} />
        </feSpecularLighting>
        <feComposite in="spec" in2="goo" operator="in" result="specIn" />
        <feComposite in="specIn" in2="shaded" operator="arithmetic" k1={0} k2={1} k3={1} k4={0} result="lit" />
        <feComposite in="lit" in2="goo" operator="in" />
      </filter>
    </defs>
  </svg>
);

/** A drop that falls from (`x0`, `y0`) — growing out of its source — lands on `floor`, squashes, bounces twice and jiggles to rest. Null before `at`. */
export const dropAt = (t: number, at: number, x: number, r: number, floor: number, y0 = -140, x0 = x) => {
  const lt = t - at;
  if (lt < 0) return null;
  const fall = 16;
  const bounces: [number, number, number][] = [
    [fall, 14, 64],
    [fall + 14, 10, 18],
  ];
  let y = floor - r;
  let sx = 1;
  let sy = 1;
  if (lt < fall) {
    const u = lt / fall;
    y = y0 + (floor - r - y0) * u * u;
    sy = 1 + 0.22 * u;
    sx = 1 - 0.1 * u;
    const grow = 0.45 + 0.55 * Math.min(1, lt / 6);
    return { x: x0 + (x - x0) * Math.sin((u * Math.PI) / 2), y, rx: r * sx * grow, ry: r * sy * grow };
  } else {
    for (const [s, len, hgt] of bounces) {
      if (lt >= s && lt < s + len) {
        const u = (lt - s) / len;
        y = floor - r - 4 * hgt * u * (1 - u);
      }
    }
    const since = lt - fall;
    const land2 = lt - (fall + 14);
    const squash = Math.exp(-since / 3.2) * 0.42 + (land2 >= 0 ? Math.exp(-land2 / 2.6) * 0.16 : 0);
    const jiggle = Math.sin(since * 0.55) * Math.exp(-since / 14) * 0.06;
    sy = 1 - squash - jiggle;
    sx = 1 + squash * 0.8 + jiggle;
    y += r * (1 - sy);
  }
  return { x, y, rx: r * sx, ry: r * sy };
};

/** Children plus a mirrored, fading reflection below `floorY` (reflection fades over `depth` px). */
export const Reflect: React.FC<{ floorY: number; children: React.ReactNode; opacity?: number; depth?: number; h?: number }> = ({ floorY, children, opacity = 0.3, depth = 240, h = 1080 }) => (
  <>
    <div
      style={{
        position: "absolute",
        inset: 0,
        transform: `translateY(${floorY * 2}px) scaleY(-1)`,
        transformOrigin: "0 0",
        opacity,
        WebkitMaskImage: `linear-gradient(0deg, #000 ${h - floorY}px, transparent ${h - floorY + depth}px)`,
        filter: "blur(3px)",
      }}
    >
      {children}
    </div>
    {children}
  </>
);
