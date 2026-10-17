import React, { useMemo } from "react";
import { AbsoluteFill } from "remotion";
import { getLength, getPointAtLength } from "@remotion/paths";
import { clamp01, easeBack, easeInOut, easeOut, mix, rgba, type SpecimenTheme } from "../cinematic/specimen";

/*
 * "One thing at a time" (after Apple's design film): YouWare's own product details on one clean stage,
 * each morphing into the next — dot → prompt bar → website → slides → sheet → report → the YouWare
 * head profile → you + your AI expert → the team → dot. Everything is drawn from frame `t` (local).
 */

/** Brand avatar colours sampled from youware.com (pairs + their darker overlap). */
export const HEADS = {
  coral: "#F36440",
  lavender: "#7D6BC1",
  lavCoral: "#772A30",
  blue: "#2556B6",
  sage: "#BAC78D",
  blueSage: "#1B4365",
  yellow: "#FFD15C",
  blueYellow: "#254642",
  sky: "#ADC8E6",
  skyLav: "#5554AE",
};

/**
 * The YouWare head profile (traced from the official agent avatars): half-ellipse crown, flat back,
 * triangular nose, flat chin. `w` = width of the head block; nose sticks out 16 % in front. y is the crown top.
 */
export const headPath = (x: number, y: number, w: number, facing: "left" | "right") => {
  const s = w / 106;
  const H = 124 * s;
  const arch = 45 * s;
  const n = 17 * s;
  const noseTop = 57 * s;
  const noseTip = 87 * s;
  const noseBot = 89 * s;
  const f = facing === "left" ? 1 : -1; // front edge on the left when facing left
  const fx = facing === "left" ? x : x + w; // front edge x
  const bx = facing === "left" ? x + w : x; // back edge x
  return [
    `M ${fx} ${y + H}`,
    `L ${fx} ${y + noseBot}`,
    `L ${fx - f * n} ${y + noseBot - 1.5 * s}`,
    `L ${fx - f * n * 0.92} ${y + noseTip - 2 * s}`,
    `L ${fx} ${y + noseTop}`,
    `L ${fx} ${y + arch}`,
    `A ${w / 2} ${arch} 0 0 ${facing === "left" ? 1 : 0} ${bx} ${y + arch}`,
    `L ${bx} ${y + H}`,
    "Z",
  ].join(" ");
};
const headH = (w: number) => (124 * w) / 106;

const rrect = (cx: number, cy: number, w: number, h: number, r: number) => {
  const x = cx - w / 2;
  const y = cy - h / 2;
  const rr = Math.min(r, w / 2, h / 2);
  // start at the bottom-left, clockwise (matches headPath's start corner for smooth morphs)
  return `M ${x} ${y + h - rr} L ${x} ${y + rr} A ${rr} ${rr} 0 0 1 ${x + rr} ${y} L ${x + w - rr} ${y} A ${rr} ${rr} 0 0 1 ${x + w} ${y + rr} L ${x + w} ${y + h - rr} A ${rr} ${rr} 0 0 1 ${x + w - rr} ${y + h} L ${x + rr} ${y + h} A ${rr} ${rr} 0 0 1 ${x} ${y + h - rr} Z`;
};

/** Point-by-point morph between two closed paths (resampled by arc length). */
export const morphD = (a: string, b: string, t: number, n = 180) => {
  const la = getLength(a);
  const lb = getLength(b);
  let d = "";
  for (let i = 0; i < n; i++) {
    const pa = getPointAtLength(a, (la * i) / n);
    const pb = getPointAtLength(b, (lb * i) / n);
    d += `${i ? "L" : "M"}${mix(pa.x, pb.x, t).toFixed(1)} ${mix(pa.y, pb.y, t).toFixed(1)} `;
  }
  return d + "Z";
};

const w = (t: number, a: number, d: number, e: (x: number) => number = easeInOut) => e(clamp01((t - a) / d));

/** Local frame marks (30 fps). The chain lasts CHAIN_LEN frames. */
export const CH = { bar: 0, type: 14, send: 45, site: 49, slide: 85, sheet: 118, report: 150, head: 180, pair: 196, team: 214, out: 238 };
export const CHAIN_LEN = 246;
export const PROMPT = "Make a site for my café";
export const typeAt = (i: number) => CH.type + 3 + i * 1.15;

export const YouWareChain: React.FC<{ th: SpecimenTheme; t: number }> = ({ th, t }) => {
  const ink = th.ink;
  const card = "#FFFFFF";
  const soft = "#E9E3D6";
  const cx = 960;
  const cy = 520;

  // ── the one container that everything lives in ──
  const pBar = w(t, CH.bar, 16, easeOut);
  const pSite = w(t, CH.site, 20);
  const pSlide = w(t, CH.slide, 18);
  const pSheet = w(t, CH.sheet, 18);
  const pReport = w(t, CH.report, 18);
  const pHead = w(t, CH.head, 14);
  let box = { w: mix(20, 820, pBar), h: mix(20, 96, pBar), r: mix(10, 48, pBar) };
  box = { w: mix(box.w, 1000, pSite), h: mix(box.h, 600, pSite), r: mix(box.r, 18, pSite) };
  box = { w: mix(box.w, 800, pSlide), h: mix(box.h, 450, pSlide), r: mix(box.r, 10, pSlide) };
  box = { w: mix(box.w, 860, pSheet), h: mix(box.h, 520, pSheet), r: mix(box.r, 8, pSheet) };
  box = { w: mix(box.w, 420, pReport), h: mix(box.h, 560, pReport), r: mix(box.r, 6, pReport) };
  const boxCol = pReport > 0.5 ? HEADS.coral : card;
  const HW = 330; // head width
  const headD = useMemo(() => headPath(cx - HW / 2 + 40, cy - headH(HW) / 2, HW, "left"), []);
  const rectD = rrect(cx, cy, box.w, box.h, box.r);
  const outline = pHead > 0 && pHead < 1 ? morphD(rectD, headD, pHead) : pHead >= 1 ? headD : rectD;
  const shrink = w(t, CH.out, 6, (x) => x);

  // ── contents fade between stages ──
  const aBar = w(t, CH.type - 4, 6) * (1 - w(t, CH.site, 8));
  const aSite = w(t, CH.site + 8, 10) * (1 - w(t, CH.slide, 8));
  const aSlide = w(t, CH.slide + 8, 10) * (1 - w(t, CH.sheet, 8));
  const aSheet = w(t, CH.sheet + 8, 10) * (1 - w(t, CH.report, 8));
  const aReport = w(t, CH.report + 8, 10) * (1 - w(t, CH.head, 6));
  const typed = PROMPT.slice(0, PROMPT.split("").filter((_, i) => t >= typeAt(i)).length);
  const press = 1 - 0.1 * Math.exp(-Math.pow((t - CH.send) / 2.2, 2));
  const fly = w(t, CH.send + 2, 10, easeOut);

  const X = cx - box.w / 2;
  const Y = cy - box.h / 2;
  const block = (x: number, y: number, bw: number, bh: number, fill: string, a: number, r = 4, key?: string) => (
    <rect key={key} x={x} y={y} width={bw} height={bh} rx={r} fill={fill} opacity={a} />
  );
  const stag = (base: number, i: number, a: number) => a * easeOut(clamp01((t - base - i * 3) / 8));

  const pair = w(t, CH.pair, 14, easeOut);
  const team = w(t, CH.team, 12, (x) => easeBack(x, 1.4));
  const headScale = 1 - 0.35 * team;

  return (
    <AbsoluteFill style={{ background: th.paper }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 46%, #FFFFFF 0%, ${th.paper} 55%, ${soft} 100%)` }} />
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id="chain-shadow" x="-20%" y="-20%" width="140%" height="160%">
            <feDropShadow dx="0" dy="18" stdDeviation="22" floodColor="#3A3020" floodOpacity={0.14 * (1 - pHead)} />
          </filter>
          <clipPath id="head-front">
            <path d={headD} />
          </clipPath>
        </defs>
        <g transform={`translate(${cx} ${cy}) scale(${(pHead >= 1 ? headScale : 1) * (1 - shrink)}) translate(${-cx} ${-cy})`}>
          {/* second head (you) slides in behind, facing the expert */}
          {pair > 0 && (
            <g transform={`translate(${mix(-420, -150, pair)} ${-6})`} opacity={pair}>
              <path d={headPath(cx - HW / 2 - 10, cy - headH(HW) / 2 + 12, HW * 0.94, "right")} fill={HEADS.lavender} />
            </g>
          )}
          <path d={outline} fill={pHead > 0.5 ? HEADS.coral : boxCol} filter="url(#chain-shadow)" />
          {pair > 0 && (
            <g clipPath="url(#head-front)">
              <g transform={`translate(${mix(-420, -150, pair)} ${-6})`} opacity={pair}>
                <path d={headPath(cx - HW / 2 - 10, cy - headH(HW) / 2 + 12, HW * 0.94, "right")} fill={HEADS.lavCoral} />
              </g>
            </g>
          )}
          {/* the team: two more pairs arrive left and right */}
          {team > 0 &&
            [
              { dx: -620, a: HEADS.blue, b: HEADS.sage, o: HEADS.blueSage },
              { dx: 620, a: HEADS.blue, b: HEADS.yellow, o: HEADS.blueYellow },
            ].map((p, i) => {
              const k = clamp01(team * 1.3 - i * 0.3);
              const s = 0.62 * k;
              const hw = HW * s;
              const bx = cx + p.dx * (0.6 + 0.4 * k);
              const front = headPath(bx - hw / 2 + 30 * s, cy - headH(hw) / 2, hw, "left");
              const back = headPath(bx - hw / 2 - 120 * s, cy - headH(hw) / 2 + 8 * s, hw * 0.94, "right");
              return (
                <g key={i} opacity={k}>
                  <defs>
                    <clipPath id={`team-${i}`}>
                      <path d={front} />
                    </clipPath>
                  </defs>
                  <path d={back} fill={p.a} />
                  <path d={front} fill={p.b} />
                  <path d={back} fill={p.o} clipPath={`url(#team-${i})`} />
                </g>
              );
            })}

          {/* ── prompt bar ── */}
          {aBar > 0 && (
            <g opacity={aBar}>
              <circle cx={X + 52} cy={cy} r={22} fill="none" stroke={rgba(ink, 0.35)} strokeWidth={2} />
              <path d={`M ${X + 52} ${cy - 9} V ${cy + 9} M ${X + 43} ${cy} H ${X + 61}`} stroke={rgba(ink, 0.55)} strokeWidth={2.4} strokeLinecap="round" />
              <text x={X + 96} y={cy + 11} fontFamily={th.sans} fontSize={31} fill={ink}>
                {typed}
                {t < CH.send && Math.floor(t / 8) % 2 === 0 && <tspan fill={rgba(ink, 0.6)}>|</tspan>}
              </text>
              {[0, 1, 2, 3, 4].map((i) => {
                const lvl = t > CH.send - 8 && t < CH.send + 2 ? 0.35 + 0.65 * Math.abs(Math.sin(t * 0.7 + i * 1.3)) : 0.35 + 0.15 * Math.sin(i * 2);
                const bh = 28 * lvl;
                return <rect key={i} x={X + box.w - 150 + i * 9} y={cy - bh / 2} width={4} height={bh} rx={2} fill={rgba(ink, 0.55)} />;
              })}
              <g transform={`translate(${X + box.w - 52} ${cy}) scale(${press})`}>
                <circle r={30} fill={ink} />
                <path d={`M 0 ${9 - 90 * fly} V ${-9 - 90 * fly} M -8 ${-1 - 90 * fly} L 0 ${-9 - 90 * fly} L 8 ${-1 - 90 * fly}`} stroke="#fff" strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" fill="none" opacity={1 - fly} />
              </g>
            </g>
          )}

          {/* ── website ── */}
          {aSite > 0 && (
            <g opacity={aSite}>
              {[HEADS.coral, HEADS.yellow, HEADS.sage].map((c, i) => (
                <circle key={i} cx={X + 30 + i * 22} cy={Y + 28} r={6.5} fill={c} />
              ))}
              {block(cx - 170, Y + 16, 340, 24, soft, 1, 12)}
              <line x1={X} x2={X + box.w} y1={Y + 56} y2={Y + 56} stroke={soft} strokeWidth={2} />
              {block(X + 48, Y + 96, 280, 26, ink, stag(CH.site + 8, 0, 1))}
              {block(X + 48, Y + 136, 220, 26, ink, stag(CH.site + 8, 1, 1))}
              {block(X + 48, Y + 184, 300, 12, rgba(ink, 0.25), stag(CH.site + 8, 2, 1), 6)}
              {block(X + 48, Y + 206, 250, 12, rgba(ink, 0.25), stag(CH.site + 8, 2, 1), 6)}
              {block(X + 48, Y + 250, 140, 44, HEADS.coral, stag(CH.site + 8, 3, 1), 22)}
              {block(X + 440, Y + 90, box.w - 488, 240, th.accent, stag(CH.site + 8, 2, 1), 14)}
              <circle cx={X + 440 + (box.w - 488) * 0.72} cy={Y + 160} r={34} fill={HEADS.yellow} opacity={stag(CH.site + 8, 4, 1)} />
              {[0, 1, 2].map((i) =>
                block(X + 48 + i * ((box.w - 96 - 40) / 3 + 20), Y + 372, (box.w - 96 - 40) / 3, 180, [HEADS.sky, "#F3E2D4", HEADS.sage][i], stag(CH.site + 14, i + 2, 1), 12, `c${i}`),
              )}
            </g>
          )}

          {/* ── slides ── */}
          {aSlide > 0 && (
            <g opacity={aSlide}>
              {[2, 1].map((k) => {
                const fan = w(t, CH.slide + 16, 14, easeOut);
                return (
                  <g key={k} transform={`translate(${cx} ${cy}) rotate(${(k === 1 ? -5 : 5) * fan}) translate(${(k === 1 ? -150 : 150) * fan} ${20 * fan}) translate(${-cx} ${-cy})`} opacity={fan}>
                    <rect x={X} y={Y} width={box.w} height={box.h} rx={10} fill={k === 1 ? "#F7F1E4" : "#EFE7D6"} />
                  </g>
                );
              })}
              <rect x={X} y={Y} width={box.w} height={box.h} rx={box.r} fill={card} />
              {block(X + 56, Y + 70, 300, 36, ink, stag(CH.slide + 6, 0, 1))}
              {block(X + 56, Y + 118, 230, 36, ink, stag(CH.slide + 6, 1, 1))}
              {block(X + 56, Y + 184, 280, 12, rgba(ink, 0.25), stag(CH.slide + 6, 2, 1), 6)}
              {block(X + 56, Y + 206, 240, 12, rgba(ink, 0.25), stag(CH.slide + 6, 2, 1), 6)}
              {block(X + 430, Y + 50, 320, 350, HEADS.coral, stag(CH.slide + 6, 1, 1), 8)}
              <circle cx={X + 590} cy={Y + 190} r={70} fill={HEADS.yellow} opacity={stag(CH.slide + 6, 3, 1)} />
              {block(X + 56, Y + 360, 120, 8, th.accent, stag(CH.slide + 6, 3, 1), 4)}
            </g>
          )}

          {/* ── sheet ── */}
          {aSheet > 0 && (
            <g opacity={aSheet}>
              {block(X, Y, box.w, 54, HEADS.sage, 1, 8)}
              {Array.from({ length: 8 }, (_, c) =>
                Array.from({ length: 8 }, (_, r) => {
                  const cw = box.w / 8;
                  const rh = (box.h - 54) / 8;
                  const a = stag(CH.sheet + 6, (c + r) * 0.45, 1);
                  const hi = c === 5;
                  const len = 0.35 + 0.5 * ((Math.sin(c * 7.1 + r * 3.3) + 1) / 2);
                  return (
                    <g key={`${c}-${r}`}>
                      {hi && <rect x={X + c * cw} y={Y + 54 + r * rh} width={cw} height={rh} fill={rgba(HEADS.lavender, 0.18)} opacity={a} />}
                      <rect x={X + c * cw + 12} y={Y + 54 + r * rh + rh / 2 - 5} width={(cw - 24) * len} height={10} rx={5} fill={rgba(ink, c === 0 ? 0.45 : 0.2)} opacity={a} />
                    </g>
                  );
                }),
              )}
              {Array.from({ length: 9 }, (_, c) => (
                <line key={c} x1={X + (c * box.w) / 8} x2={X + (c * box.w) / 8} y1={Y + 54} y2={Y + box.h} stroke={soft} strokeWidth={1.5} />
              ))}
              {/* the highlighted column rises into a bar chart */}
              {[0, 1, 2, 3, 4].map((i) => {
                const g = w(t, CH.sheet + 20 + i * 2, 12, easeOut);
                const bh = (60 + [140, 90, 190, 120, 230][i]) * g;
                return <rect key={i} x={X + box.w * 0.18 + i * 120} y={Y + box.h - 30 - bh} width={70} height={bh} rx={8} fill={[HEADS.blue, HEADS.sage, HEADS.lavender, HEADS.sky, HEADS.coral][i]} opacity={g * 0.95} />;
              })}
            </g>
          )}

          {/* ── report ── */}
          {aReport > 0 && (
            <g opacity={aReport}>
              {[2, 1].map((k) => (
                <rect key={k} x={X + k * 18} y={Y - k * 14} width={box.w} height={box.h} rx={6} fill={k === 1 ? "#F6D9CC" : "#EFE3D4"} opacity={w(t, CH.report + 10, 10)} />
              ))}
              <rect x={X} y={Y} width={box.w} height={box.h} rx={box.r} fill={HEADS.coral} />
              {block(X + 36, Y + 44, 240, 26, th.cream, stag(CH.report + 6, 0, 1))}
              {block(X + 36, Y + 80, 180, 26, th.cream, stag(CH.report + 6, 1, 1))}
              {(() => {
                const R = 92;
                const C = 2 * Math.PI * R;
                const segs = [0.46, 0.27, 0.18, 0.09];
                const cols = [th.cream, "#FBD3C4", HEADS.yellow, HEADS.lavCoral];
                let acc = 0;
                const g = w(t, CH.report + 8, 16, easeOut);
                return (
                  <g transform={`translate(${cx} ${Y + 330}) rotate(-90)`}>
                    {segs.map((s, i) => {
                      const el = <circle key={i} r={R} fill="none" stroke={cols[i]} strokeWidth={34} strokeDasharray={`${C * s * g} ${C}`} strokeDashoffset={-C * acc * g} />;
                      acc += s;
                      return el;
                    })}
                  </g>
                );
              })()}
              {block(X + 36, Y + box.h - 60, 160, 10, rgba(th.cream, 0.7), stag(CH.report + 6, 3, 1), 5)}
            </g>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
