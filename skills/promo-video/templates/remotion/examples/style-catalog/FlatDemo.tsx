import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { step as stepS } from "../cinematic/spring";
import { fam } from "../cinematic/type";
import { headPath, HEADS } from "../youware-ladder/YouWareChain";
import { MARK_D as MARK } from "./markPath";

/**
 * 03 · 扁平矢量插画 — "YouWare studio": a flat-illustrated room in the brand's own illustration language (profile
 * heads overlapping in multiply). A visitor asks for a café launch; four agent pairs pop up behind their laptops and
 * pin a website, a deck, a sheet and a report to the board. 330 frames.
 */
export const FLAT_LEN = 330;
const SANS = fam("Manrope");
const SLAB = fam("Hepta Slab");
const P = { wall: "#F4ECE1", floor: "#E6D6C2", ink: "#2A2140", wood: "#D9A273", woodDk: "#B98356", board: "#FFFFFF", leaf: "#5E8C61", leafDk: "#3F6B4A", pot: "#F36440" };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const out3 = (v: number) => 1 - Math.pow(1 - clamp01(v), 3);
const inOut = (v: number) => {
  const k = clamp01(v);
  return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
};
const sp = (f: number, w = 2.6, z = 0.5) => stepS(f / 30, { w: 2 * Math.PI * w, z });
const headH = (w: number) => (124 * w) / 106;

const DESK_Y = 800;
const AGENTS = [
  { x: 270, a: HEADS.blue, b: HEADS.sage, o: HEADS.blueSage, face: "right" as const, at: 64, item: "web" },
  { x: 575, a: HEADS.lavender, b: HEADS.coral, o: HEADS.lavCoral, face: "right" as const, at: 72, item: "slides" },
  { x: 880, a: HEADS.blue, b: HEADS.yellow, o: HEADS.blueYellow, face: "left" as const, at: 80, item: "sheet" },
  { x: 1185, a: HEADS.lavender, b: HEADS.sky, o: HEADS.skyLav, face: "left" as const, at: 88, item: "report" },
];
const SLOTS = [
  [1045, 222],
  [1335, 222],
  [1045, 438],
  [1335, 438],
];
const FLY = 112; // first item leaves its laptop
const FLY_GAP = 20;

/** Two overlapping profile heads (brand avatar), overlap in multiply. */
const Pair: React.FC<{ x: number; y: number; w: number; a: string; b: string; o: string; face: "left" | "right" }> = ({ x, y, w, a, b, o, face }) => {
  const dx = face === "left" ? -w * 0.62 : w * 0.62;
  const front = headPath(x - w / 2, y, w, face);
  const back = headPath(x - w / 2 + dx, y - w * 0.12, w * 0.94, face);
  const id = `clip-${Math.round(x)}-${Math.round(y)}`;
  return (
    <g>
      <defs>
        <clipPath id={id}>
          <path d={back} />
        </clipPath>
      </defs>
      <path d={back} fill={b} />
      <path d={front} fill={a} />
      <path d={front} fill={o} clipPath={`url(#${id})`} />
    </g>
  );
};

const Item: React.FC<{ kind: string; x: number; y: number; s?: number; rot?: number }> = ({ kind, x, y, s = 1, rot = 0 }) => {
  const W = 250;
  const H = 170;
  const bg = { web: "#FFFFFF", slides: HEADS.lavender, sheet: HEADS.sage, report: HEADS.yellow }[kind]!;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s}) translate(${-W / 2} ${-H / 2})`}>
      <rect x={6} y={8} width={W} height={H} rx={14} fill="rgba(42,33,64,0.14)" />
      <rect width={W} height={H} rx={14} fill={bg} />
      {kind === "web" && (
        <>
          <rect width={W} height={30} rx={14} fill={HEADS.coral} />
          <rect y={16} width={W} height={14} fill={HEADS.coral} />
          <rect x={18} y={46} width={W - 36} height={64} rx={8} fill={HEADS.sky} />
          <circle cx={W - 54} cy={70} r={12} fill={HEADS.yellow} />
          <path d={`M 18 110 L 70 76 L 104 98 L 140 70 L ${W - 18} 110 Z`} fill={HEADS.skyLav} />
          <rect x={18} y={124} width={130} height={12} rx={6} fill={P.ink} opacity={0.8} />
          <rect x={18} y={146} width={90} height={10} rx={5} fill={P.ink} opacity={0.35} />
        </>
      )}
      {kind === "slides" && (
        <>
          <rect x={20} y={20} width={120} height={14} rx={7} fill="#FFFFFF" />
          {[50, 80, 110].map((h, i) => (
            <rect key={i} x={30 + i * 50} y={150 - h} width={34} height={h} rx={4} fill={i === 2 ? HEADS.yellow : "#FFFFFF"} />
          ))}
          <path d="M 190 120 Q 210 90 228 52" stroke="#FFFFFF" strokeWidth={6} fill="none" strokeLinecap="round" />
        </>
      )}
      {kind === "sheet" && (
        <>
          <rect x={16} y={16} width={W - 32} height={H - 32} rx={6} fill="#FFFFFF" />
          <rect x={16} y={16} width={W - 32} height={26} rx={6} fill={HEADS.blueSage} />
          {[1, 2, 3].map((r) => (
            <rect key={r} x={16} y={42 + r * 26} width={W - 32} height={2} fill={HEADS.sage} />
          ))}
          {[1, 2].map((c) => (
            <rect key={c} x={16 + c * 72} y={42} width={2} height={H - 58} fill={HEADS.sage} />
          ))}
          <rect x={172} y={100} width={46} height={22} rx={4} fill={HEADS.coral} opacity={0.85} />
        </>
      )}
      {kind === "report" && (
        <>
          <rect x={20} y={20} width={100} height={130} rx={6} fill="#FFFFFF" />
          <rect x={32} y={34} width={64} height={10} rx={5} fill={P.ink} />
          {[0, 1, 2, 3].map((r) => (
            <rect key={r} x={32} y={58 + r * 20} width={76 - r * 8} height={7} rx={3.5} fill={P.ink} opacity={0.3} />
          ))}
          <circle cx={184} cy={86} r={46} fill="#FFFFFF" />
          <path d="M 184 86 L 184 40 A 46 46 0 0 1 226 104 Z" fill={HEADS.coral} />
        </>
      )}
      <circle cx={W / 2} cy={4} r={11} fill={HEADS.coral} />
      <circle cx={W / 2 - 3} cy={1} r={4} fill="#FFFFFF" opacity={0.7} />
    </g>
  );
};

const Room: React.FC<{ t: number }> = ({ t }) => (
  <>
    <rect width={1920} height={1080} fill={P.wall} />
    <rect y={900} width={1920} height={180} fill={P.floor} />
    {/* window with a flat skyline */}
    <rect x={90} y={100} width={560} height={470} rx={26} fill={P.ink} />
    <rect x={108} y={118} width={524} height={434} rx={16} fill={HEADS.sky} />
    <circle cx={520} cy={250 + Math.sin(t * 0.02) * 4} r={46} fill={HEADS.yellow} />
    {[0, 1, 2].map((i) => {
      const cx = 108 + ((i * 230 + t * 0.9) % 700) - 90;
      return (
        <g key={i} opacity={0.95}>
          <rect x={cx} y={170 + i * 42} width={120} height={30} rx={15} fill="#FFFFFF" />
          <rect x={cx + 26} y={156 + i * 42} width={60} height={30} rx={15} fill="#FFFFFF" />
        </g>
      );
    })}
    <g clipPath="url(#win)">
      {[
        [108, 380, 90, HEADS.skyLav],
        [190, 330, 70, HEADS.lavender],
        [255, 400, 110, HEADS.skyLav],
        [360, 300, 80, HEADS.blue],
        [438, 360, 100, HEADS.skyLav],
        [535, 410, 110, HEADS.lavender],
      ].map(([x, y, w, c], i) => (
        <rect key={i} x={x as number} y={y as number} width={w as number} height={560 - (y as number)} fill={c as string} />
      ))}
      {Array.from({ length: 18 }, (_, i) => (
        <rect key={i} x={124 + (i % 6) * 84 + (i % 2) * 18} y={420 + Math.floor(i / 6) * 40} width={14} height={18} fill={HEADS.yellow} opacity={(i * 7 + Math.floor(t / 20)) % 5 === 0 ? 0.3 : 0.9} />
      ))}
    </g>
    <defs>
      <clipPath id="win">
        <rect x={108} y={118} width={524} height={434} rx={16} />
      </clipPath>
    </defs>
    <rect x={362} y={118} width={16} height={434} fill={P.ink} />
    {/* board */}
    <rect x={895} y={96} width={590} height={488} rx={22} fill={P.ink} />
    <rect x={911} y={112} width={558} height={456} rx={14} fill={P.board} />
    {SLOTS.map(([x, y], i) => (
      <rect key={i} x={x - 125} y={y - 85} width={250} height={170} rx={14} fill="none" stroke="#E7DDF3" strokeWidth={3} strokeDasharray="10 10" />
    ))}
    {/* pendant lamps */}
    {[250, 1640].map((x, i) => {
      const sw = Math.sin(t * 0.04 + i) * 2;
      return (
        <g key={x} transform={`rotate(${sw} ${x} 0)`}>
          <rect x={x - 2} y={0} width={4} height={50} fill={P.ink} />
          <path d={`M ${x - 46} 96 L ${x - 22} 50 L ${x + 22} 50 L ${x + 46} 96 Z`} fill={HEADS.coral} />
          <ellipse cx={x} cy={96} rx={46} ry={8} fill="#FFE6A3" />
        </g>
      );
    })}
    {/* tall plant */}
    <Plant x={1858} y={900} t={t} s={0.92} />
  </>
);

const Plant: React.FC<{ x: number; y: number; t: number; s?: number }> = ({ x, y, t, s = 1 }) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    {[
      [-60, -250, -28],
      [40, -290, 22],
      [-20, -330, -6],
      [70, -200, 40],
      [-90, -170, -46],
    ].map(([dx, dy, r], i) => (
      <g key={i} transform={`rotate(${r + Math.sin(t * 0.05 + i) * 3} 0 -60)`}>
        <rect x={-3} y={dy + 40} width={6} height={-dy - 90} fill={P.leafDk} />
        <ellipse cx={dx * 0.2} cy={dy + 30} rx={34} ry={62} fill={i % 2 ? P.leaf : P.leafDk} />
      </g>
    ))}
    <path d="M -70 -80 L 70 -80 L 54 0 L -54 0 Z" fill={P.pot} />
    <rect x={-78} y={-94} width={156} height={20} rx={6} fill="#C94A2C" />
  </g>
);

const Visitor: React.FC<{ t: number }> = ({ t }) => {
  const walk = inOut((t - 8) / 46);
  const x = 2080 + (1650 - 2080) * walk;
  const moving = walk > 0 && walk < 1;
  const bob = moving ? Math.abs(Math.sin(t * 0.42)) * -10 : Math.sin(t * 0.06) * 2;
  const leg = moving ? Math.sin(t * 0.42) * 16 : 0;
  const turn = "left" as const;
  const hw = 132;
  const y0 = 470 + bob;
  return (
    <g>
      <rect x={x - 42 + leg} y={y0 + 300} width={30} height={140} rx={14} fill={P.ink} />
      <rect x={x + 8 - leg} y={y0 + 300} width={30} height={140} rx={14} fill={P.ink} />
      <path d={`M ${x - 80} ${y0 + 320} L ${x - 80} ${y0 + 200} Q ${x - 80} ${y0 + 150} ${x - 30} ${y0 + 150} L ${x + 30} ${y0 + 150} Q ${x + 80} ${y0 + 150} ${x + 80} ${y0 + 200} L ${x + 80} ${y0 + 320} Z`} fill={HEADS.coral} />
      <path d={headPath(x - hw / 2, y0, hw, turn)} fill={HEADS.sky} />
      {/* smile slot, as on the brand's hero avatar */}
      <path d={turn === "left" ? `M ${x - 44} ${y0 + 66} Q ${x - 22} ${y0 + 84} ${x} ${y0 + 66} Z` : `M ${x + 44} ${y0 + 66} Q ${x + 22} ${y0 + 84} ${x} ${y0 + 66} Z`} fill="#FFFFFF" />
      {/* mug */}
      <rect x={x + (turn === "left" ? -120 : 84)} y={y0 + 228} width={40} height={46} rx={8} fill="#FFFFFF" />
      {[0, 1].map((i) => (
        <path key={i} d={`M ${x + (turn === "left" ? -108 : 96) + i * 14} ${y0 + 218} q 8 -14 0 -26 q -8 -12 0 -26`} stroke="#FFFFFF" strokeWidth={4} fill="none" strokeLinecap="round" opacity={0.5 + 0.5 * Math.sin(t * 0.15 + i * 2)} transform={`translate(0 ${-((t * 0.6) % 8)})`} />
      ))}
    </g>
  );
};

const Bubble: React.FC<{ t: number }> = ({ t }) => {
  const k = sp(t - 50, 2.8, 0.55);
  const out = inOut((t - 118) / 12);
  if (k <= 0.001 || out >= 1) return null;
  const typed = "Plan my café launch".slice(0, Math.floor(clamp01((t - 54) / 18) * 19));
  return (
    <div style={{ position: "absolute", left: 1330, top: 330, width: 420, transformOrigin: "85% 100%", transform: `scale(${k * (1 - out)})` }}>
      <div style={{ background: "#FFFFFF", borderRadius: 30, padding: "22px 30px", fontFamily: SANS, fontWeight: 700, fontSize: 36, color: P.ink, boxShadow: "8px 10px 0 rgba(42,33,64,0.12)" }}>{typed || " "}</div>
      <svg width={60} height={40} style={{ position: "absolute", right: 60, bottom: -30 }}>
        <path d="M 0 0 L 50 0 L 40 34 Z" fill="#FFFFFF" />
      </svg>
    </div>
  );
};

export const FlatDemo: React.FC = () => {
  const t = useCurrentFrame();
  const banner = sp(t - 252, 2, 0.45);
  const cam = 1 + 0.03 * inOut(t / 330);
  return (
    <AbsoluteFill style={{ background: P.wall, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${cam})`, transformOrigin: "50% 60%" }}>
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          <Room t={t} />
          {/* agents behind the desk (clipped to the desk top so they rise from behind it) */}
          <defs>
            <clipPath id="above-desk">
              <rect x={0} y={0} width={1920} height={DESK_Y} />
            </clipPath>
          </defs>
          <g clipPath="url(#above-desk)">
          {AGENTS.map((g, i) => {
            const k = sp(t - g.at, 2.4, 0.45);
            const work = t > g.at + 20 && t < FLY + i * FLY_GAP + 10;
            const bob = work ? Math.abs(Math.sin(t * 0.5 + i)) * -6 : Math.sin(t * 0.05 + i) * 2;
            const hw = 118;
            const y = DESK_Y - 318 + (1 - k) * 380 + bob;
            return (
              <g key={i}>
                <path d={`M ${g.x - 90} ${DESK_Y} L ${g.x - 90} ${y + 190} Q ${g.x - 90} ${y + 150} ${g.x - 50} ${y + 150} L ${g.x + 50} ${y + 150} Q ${g.x + 90} ${y + 150} ${g.x + 90} ${y + 190} L ${g.x + 90} ${DESK_Y} Z`} fill={P.ink} />
                <Pair x={g.x} y={y + 14} w={hw} a={g.a} b={g.b} o={g.o} face={g.face} />
              </g>
            );
          })}
          </g>
          {/* desk + laptops (lids face us, mark lights up while working) */}
          <rect x={80} y={DESK_Y} width={1440} height={30} rx={8} fill={P.wood} />
          <rect x={120} y={DESK_Y + 30} width={1360} height={120} fill={P.woodDk} />
          <rect x={140} y={DESK_Y + 150} width={26} height={110} fill={P.ink} />
          <rect x={1434} y={DESK_Y + 150} width={26} height={110} fill={P.ink} />
          {AGENTS.map((g, i) => {
            const lit = clamp01((t - g.at - 18) / 8) * (1 - clamp01((t - FLY - i * FLY_GAP - 10) / 30) * 0.6);
            return (
              <g key={i}>
                <path d={`M ${g.x - 110} ${DESK_Y} L ${g.x - 96} ${DESK_Y - 150} L ${g.x + 96} ${DESK_Y - 150} L ${g.x + 110} ${DESK_Y} Z`} fill="#D6D1E4" />
                <circle cx={g.x} cy={DESK_Y - 76} r={30} fill={g.a} opacity={lit * 0.35} />
                <g transform={`translate(${g.x - 22} ${DESK_Y - 98}) scale(${44 / 204})`}>
                  <path d={MARK} fill={lit > 0.05 ? g.a : "#FFFFFF"} opacity={0.6 + 0.4 * lit} />
                </g>
              </g>
            );
          })}
          <Visitor t={t} />
          {/* items fly from laptops to the board */}
          {AGENTS.map((g, i) => {
            const at = FLY + i * FLY_GAP;
            if (t < at) return null;
            const u = inOut((t - at) / 26);
            const [sx, sy] = [g.x, DESK_Y - 170];
            const [tx, ty] = SLOTS[i];
            const x = sx + (tx - sx) * u;
            const y = sy + (ty - sy) * u - Math.sin(u * Math.PI) * 180;
            const pop = sp(t - at, 3, 0.5);
            const land = t > at + 26 ? Math.sin((t - at - 26) * 0.6) * Math.exp(-(t - at - 26) / 6) * 4 : 0;
            return <Item key={i} kind={g.item} x={x} y={y} s={0.4 + 0.6 * Math.min(1, pop)} rot={(1 - u) * (i % 2 ? 14 : -14) + land} />;
          })}
        </svg>
        {/* the desk front carries the lockup */}
        <div style={{ position: "absolute", left: 120, width: 1360, top: DESK_Y + 58, display: "flex", justifyContent: "center", opacity: 0.9 }}>
          <Img src={staticFile("brand/lockup.svg")} style={{ height: 64, filter: "invert(1) brightness(1.2)" }} />
        </div>
        <Bubble t={t} />
      </AbsoluteFill>
      {/* banner */}
      <div style={{ position: "absolute", left: 0, right: 0, top: -140 + 148 * banner, display: "flex", justifyContent: "center", transform: `rotate(${(1 - Math.min(1, banner)) * -3}deg)` }}>
        <div style={{ position: "relative", background: HEADS.coral, color: "#FFFFFF", fontFamily: SLAB, fontWeight: 500, fontSize: 58, padding: "20px 70px", borderRadius: 12, boxShadow: "10px 12px 0 rgba(42,33,64,0.18)" }}>From answers to outcomes.</div>
      </div>
      <AbsoluteFill style={{ background: P.wall, opacity: 1 - clamp01(t / 10), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

