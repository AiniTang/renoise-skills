import React, { useEffect, useState } from "react";
import { AtSign, BadgeCheck, BarChart3, Bookmark, Check, Heart, MessageCircle, Repeat2, Search, Sparkles, Star, Wand2, type LucideIcon } from "lucide-react";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { AbsoluteFill, Audio, Img, cancelRender, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { E, clamp01, mix } from "../cinematic/motion";
import { SoundCues, keyCues, type Cue } from "../cinematic/sfx";
import { CAM, CURSOR, LEAD, PRESS, TRAIL, UI, dragged, step, track, trackCfg, trackColor } from "./spring";

export const FPS = 60;
export const REEL_FRAMES = 56 * 30;
const K = (n: number, o = 0) => (n - 1) * 0.5 + o;

const CANVAS = "#ECEAE6";
const INK = "#111111";
const INK2 = "#2E2E2E";
const WHITE = "#FFFFFF";
const GRAY = "#8A8680";
const LINE = "#E6E3DE";
const TEAL = "#14B8A6";
const OFF = "#D6D2CC";
const FONT = 'Geist, "PingFang SC", -apple-system, sans-serif';

const useGeist = () => {
  const [handle] = useState(() => delayRender("geist"));
  useEffect(() => {
    Promise.all(
      [
        ["Regular", 400],
        ["Medium", 500],
        ["SemiBold", 600],
        ["Bold", 700],
      ].map(([n, w]) => new FontFace("Geist", `url(${staticFile(`fonts/Geist-${n}.woff2`)})`, { weight: String(w) }).load().then((face) => document.fonts.add(face))),
    )
      .then(() => continueRender(handle))
      .catch((err) => cancelRender(err));
  }, [handle]);
};

/* ── the one shape ── */

const W: [number, number][] = [[0, 420], [K(4), 120], [K(8), 400], [K(9), 760], [K(13), 900], [K(17), 1000], [K(21), 240], [K(25), 300], [K(29), 1000], [K(33), 1040], [K(41), 820], [K(45), 760], [K(53), 420]];
const H: [number, number][] = [[0, 120], [K(9), 150], [K(13), 560], [K(17), 200], [K(21), 760], [K(25), 160], [K(29), 150], [K(33), 820], [K(41), 540], [K(45), 150], [K(53), 120]];
const RAD: [number, number][] = [[0, 60], [K(9), 75], [K(13), 40], [K(17), 100], [K(21), 120], [K(25), 80], [K(29), 75], [K(33), 40], [K(41), 28], [K(45), 75], [K(53), 60]];
const BG: [number, string][] = [[0, INK], [K(2), INK2], [K(3), INK], [K(7), TEAL], [K(9), INK], [K(13), WHITE], [K(25), OFF], [K(27), TEAL], [K(29), WHITE], [K(45), INK]];
const CAMK: [number, number][] = [[0, 2.1], [K(4), 2.35], [K(8), 2.05], [K(9), 1.2], [K(13), 1.02], [K(17), 0.96], [K(21), 1.12], [K(25), 2.1], [K(29), 0.94], [K(33), 0.88], [K(41), 1.1], [K(45), 1.2], [K(53), 2.1]];
const PRESSK: [number, number][] = [[0, 1], [K(3), 0.94], [K(3, 0.1), 1], [K(27), 0.96], [K(27, 0.1), 1]];

/* ── cursor (world coordinates, shape centre = origin) ── */

const P0: [number, number] = [300, 200];
const CUR: [number, number, number][] = [
  [0, ...P0],
  [K(1, 0.05), 70, 18],
  [K(4, 0.15), 150, 120],
  [K(10), 300, 110],
  [K(13, 0.2), 170, 330],
  [K(14, 0.15), -150, 196],
  [K(16, 0.1), -60, 250],
  [K(17, 0.05), -252, 30],
  [K(18), 80, 34],
  [K(19), 470, 30],
  [K(20, 0.1), 480, 110],
  [K(21, 0.2), 0, 300],
  [K(23), 0, -140],
  [K(23, 0.3), 0, -420],
  [K(24, 0.15), 150, -250],
  [K(26), -70, 10],
  [K(27, 0.3), 90, 110],
  [K(29, 0.1), -120, 110],
  [K(30, -0.18), -125, 4],
  [K(31, -0.18), 125, 4],
  [K(32, -0.18), 375, 4],
  [K(32, 0.3), 440, 120],
  [K(37, -0.22), -375, 40],
  [K(38, -0.22), -225, 150],
  [K(39, -0.22), -75, 190],
  [K(40, 0.05), 470, 390],
  [K(41, 0.2), 470, 330],
  [K(46), 420, 150],
  [K(54, 0.2), ...P0],
];
const PRESSES: [number, number][] = [[K(3), K(3, 0.1)], [K(15), K(15, 0.1)], [K(17, 0.35), K(20)], [K(22), K(24)], [K(27), K(27, 0.1)], [K(30), K(30, 0.08)], [K(31), K(31, 0.08)], [K(32), K(32, 0.08)]];
const cursorAt = (t: number): [number, number] => [track(t, CUR.map(([tt, x]) => [tt, x] as [number, number]), CURSOR), track(t, CUR.map(([tt, , y]) => [tt, y] as [number, number]), CURSOR)];
const pressed = (t: number) => PRESSES.some(([a, b]) => t >= a && t <= b);

/* ── helpers ── */

const swap = (t: number, tin: number, tout: number) => {
  const i = E.out(clamp01((t - tin) / 0.18));
  const o = clamp01((t - tout) / 0.1);
  return { opacity: i * (1 - o), filter: `blur(${(1 - i) * 10 + o * 8}px)`, transform: `scale(${mix(0.96, 1, i) * mix(1, 0.98, o)})` };
};
const visible = (t: number, tin: number, tout: number) => t >= tin - 0.02 && t <= tout + 0.12;

/** Positions by anchor on the outer box; the inner box takes the caller's style, so an animated transform never overrides the anchor. */
const At: React.FC<{ x: number; y: number; children: React.ReactNode; style?: React.CSSProperties; anchor?: "center" | "left" | "right" }> = ({ x, y, children, style, anchor = "center" }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: anchor === "center" ? "translate(-50%, -50%)" : anchor === "left" ? "translate(0, -50%)" : "translate(-100%, -50%)", whiteSpace: "nowrap" }}>
    <div style={style}>{children}</div>
  </div>
);

const Layer: React.FC<{ t: number; tin: number; tout: number; children: React.ReactNode }> = ({ t, tin, tout, children }) =>
  visible(t, tin, tout) ? <div style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, ...swap(t, tin, tout) }}>{children}</div> : null;

const txt = (size: number, weight: number, color: string): React.CSSProperties => ({ fontFamily: FONT, fontSize: size, fontWeight: weight, color, letterSpacing: "-0.01em", lineHeight: 1.2 });

/* ── data ── */

const TWEET = "一句话就可以做出这样的宣传片～今天真是被 Opus 5.5 硬控的一天，不接受反驳！";
const TWEET_T0 = K(13, 0.25);
const TWEET_CPS = 34;
const REPOS = [
  { n: "AetherViz", s: 1373, d: "3D 互动教学可视化" },
  { n: "MacCheck", s: 628, d: "本地 Mac 验机宝" },
  { n: "OpenClaw", s: 408, d: "Live2D 语音助手" },
  { n: "RF-DETR", s: 204, d: "浏览器实时检测" },
  { n: "HTML PPT", s: 119, d: "智能演示文稿" },
  { n: "大唐长安", s: 105, d: "网页游戏" },
];
const TABS = ["AI 工具", "提示词", "Skills", "设计编程"];
const CMD: { t: string; s: string; icon: LucideIcon }[] = [
  { t: "Berryxia.AI", s: "@berryxia · X", icon: AtSign },
  { t: "berryxia/AetherViz", s: "GitHub · 1,373★", icon: Star },
  { t: "Browse prompts", s: "提示词库", icon: Sparkles },
  { t: "Build a Skill", s: "Claude Code", icon: Wand2 },
  { t: "Bookmark thread", s: "收藏", icon: Bookmark },
];
const QUERY: [number, string][] = [[K(41), ""], [K(42), "b"], [K(43), "be"], [K(43, 0.12), "ber"], [K(43, 0.24), "berr"], [K(44), "berry"], [K(44, 0.1), "berryx"], [K(44, 0.2), "berryxi"], [K(44, 0.3), "berryxia"]];
const queryAt = (t: number) => [...QUERY].reverse().find(([tt]) => t >= tt)?.[1] ?? "";

/* ── scene ── */

export const Reel: React.FC = () => {
  useGeist();
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = f / FPS;
  const [cx, cy] = cursorAt(t);

  const scrub = dragged(t, [K(17, 0.35), K(20)], (tt) => clamp01((cursorAt(tt)[0] + 420) / 840), 0.2, 1);
  const vol = dragged(t, [K(22), K(24)], (tt) => clamp01((320 - cursorAt(tt)[1]) / 520), 0.04, 1);
  const over = dragged(t, [K(22), K(24)], (tt) => 260 * (1 - Math.exp(-Math.max(0, -200 - cursorAt(tt)[1]) / 260)), 0, 0);

  const w = track(t, W);
  const h = track(t, H) + over * 0.6;
  const r = track(t, RAD);
  const bg = trackColor(t, BG);
  const cam = track(t, CAMK, CAM);
  const press = track(t, PRESSK, PRESS);
  const lift = -over * 0.3;

  const knobL = trackCfg(t, [[0, -134], [K(27), 6, TRAIL], [K(29), -490, LEAD], [K(30), -240, TRAIL], [K(31), 10, TRAIL], [K(32), 260, TRAIL]]);
  const knobR = trackCfg(t, [[0, -6], [K(27), 134, LEAD], [K(29), -260, TRAIL], [K(30), -10, LEAD], [K(31), 240, LEAD], [K(32), 490, LEAD]]);
  const tabActive = t < K(30) ? 0 : t < K(31) ? 1 : t < K(32) ? 2 : 3;

  const hover = t >= K(37, -0.1) && t < K(40) ? (t < K(38, -0.1) ? 0 : t < K(39, -0.1) ? 1 : 2) : -1;
  const q = queryAt(t);

  const sx = 720 + cx * cam;
  const sy = 720 + cy * cam;
  const isDown = pressed(t);

  return (
    <AbsoluteFill style={{ background: CANVAS }}>
      <CameraMotionBlur shutterAngle={180} samples={4}>
        <AbsoluteFill style={{ background: CANVAS }}>
          <div style={{ position: "absolute", left: 720, top: 720, transform: `scale(${cam})` }}>
            {/* floating toggle caption */}
            <Layer t={t} tin={K(25, 0.1)} tout={K(29)}>
              <At x={0} y={-150}>
                <span style={txt(34, 600, INK)}>Vibe Coding </span>
                <span style={{ ...txt(34, 600, t >= K(27) ? TEAL : GRAY) }}>{t >= K(27) ? "ON" : "OFF"}</span>
              </At>
            </Layer>

            <div style={{ position: "absolute", left: -w / 2, top: -h / 2 + lift, width: w, height: h, borderRadius: r, background: bg, overflow: "hidden", transform: `scale(${press})`, boxShadow: "0 24px 60px rgba(17,17,17,0.12), 0 2px 6px rgba(17,17,17,0.08)" }}>
              <div style={{ position: "absolute", left: w / 2, top: h / 2 - lift }}>
                {/* 1 · button */}
                <Layer t={t} tin={-1} tout={K(4)}>
                  <At x={0} y={0} style={txt(40, 600, WHITE)}>Follow @berryxia</At>
                </Layer>
                {/* 2 · loader */}
                <Layer t={t} tin={K(4, 0.05)} tout={K(7)}>
                  <svg width={120} height={120} style={{ position: "absolute", left: -60, top: -60, transform: `rotate(${t * 540}deg)` }}>
                    <circle cx={60} cy={60} r={32} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={8} />
                    <circle cx={60} cy={60} r={32} fill="none" stroke={WHITE} strokeWidth={8} strokeLinecap="round" strokeDasharray={`${2 * Math.PI * 32 * mix(0.22, 1, step(t - K(5), UI) * 0.45 + step(t - K(6), UI) * 0.55)} 400`} />
                  </svg>
                </Layer>
                {/* 3 · check / following */}
                <Layer t={t} tin={K(7)} tout={K(9)}>
                  <svg width={70} height={70} style={{ position: "absolute", left: mix(-35, -150, step(t - K(8), UI)), top: -35 }}>
                    <path d="M16 36 L30 50 L56 22" fill="none" stroke={WHITE} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={60} strokeDashoffset={60 * (1 - E.out(clamp01((t - K(7)) / 0.28)))} />
                  </svg>
                  <div style={{ position: "absolute", left: -58, top: -24, ...txt(40, 600, WHITE), ...swap(t, K(8, 0.05), K(9)) }}>Following</div>
                </Layer>
                {/* 4 · dynamic island */}
                <Layer t={t} tin={K(9, 0.1)} tout={K(13)}>
                  <div style={{ position: "absolute", left: -357, top: -52, width: 104, height: 104, borderRadius: 52, overflow: "hidden", transform: `scale(${step(t - K(10), UI)})` }}>
                    <Img src={staticFile("images/avatar.jpg")} style={{ width: 104, height: 104 }} />
                  </div>
                  <div style={{ position: "absolute", left: -226, top: -46, ...swap(t, K(11), K(13)) }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, ...txt(40, 600, WHITE) }}>
                      Berryxia.AI <BadgeCheck size={34} strokeWidth={2} color={TEAL} />
                    </div>
                    <div style={{ ...txt(26, 400, "rgba(255,255,255,0.55)"), marginTop: 4 }}>@berryxia</div>
                  </div>
                  <div style={{ position: "absolute", right: -330, top: -50, textAlign: "right", ...swap(t, K(12), K(13)) }}>
                    <div style={{ ...txt(56, 700, WHITE), fontVariantNumeric: "tabular-nums" }}>{(4.8 * step(t - K(12), CURSOR)).toFixed(1)}万</div>
                    <div style={txt(22, 500, "rgba(255,255,255,0.55)")}>X 粉丝</div>
                  </div>
                </Layer>
                {/* 5 · tweet card */}
                <Layer t={t} tin={K(13, 0.1)} tout={K(17)}>
                  <div style={{ position: "absolute", left: -410, top: -240, width: 72, height: 72, borderRadius: 36, overflow: "hidden" }}>
                    <Img src={staticFile("images/avatar.jpg")} style={{ width: 72, height: 72 }} />
                  </div>
                  <div style={{ position: "absolute", left: -320, top: -236 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, ...txt(30, 600, INK) }}>
                      Berryxia.AI <BadgeCheck size={26} strokeWidth={2} color={TEAL} />
                    </div>
                    <div style={txt(22, 400, GRAY)}>@berryxia · 9月25日</div>
                  </div>
                  <div style={{ position: "absolute", left: -410, top: -130, width: 820, ...txt(38, 500, INK), lineHeight: 1.45, whiteSpace: "normal" }}>
                    {Array.from(TWEET).slice(0, Math.max(0, Math.floor((t - TWEET_T0) * TWEET_CPS))).join("")}
                    <span style={{ display: "inline-block", width: 3, height: 40, marginLeft: 3, verticalAlign: "-6px", background: TEAL, opacity: t < K(15) && Math.floor(t * 3) % 2 === 0 ? 1 : 0 }} />
                  </div>
                  <div style={{ position: "absolute", left: -410, top: 88, width: 820, height: 10, borderRadius: 5, background: LINE, overflow: "hidden", ...swap(t, K(16), K(17)) }}>
                    <div style={{ width: "20%", height: "100%", background: TEAL }} />
                  </div>
                  <div style={{ position: "absolute", left: -410, top: 170, width: 820, display: "flex", justifyContent: "space-between", alignItems: "center", ...txt(24, 500, GRAY) }}>
                    <span style={{ display: "flex", gap: 10, alignItems: "center" }}><MessageCircle size={30} strokeWidth={1.75} /> 回复</span>
                    <span style={{ display: "flex", gap: 10, alignItems: "center" }}><Repeat2 size={30} strokeWidth={1.75} /> 转帖</span>
                    <span style={{ display: "flex", gap: 10, alignItems: "center", color: t >= K(15) ? TEAL : GRAY, transform: `scale(${1 + 0.18 * (step(t - K(15), PRESS) - step(t - K(15, 0.12), UI))})` }}>
                      <Heart size={30} strokeWidth={1.75} fill={t >= K(15) ? TEAL : "none"} /> 喜欢
                    </span>
                    <span style={{ display: "flex", gap: 10, alignItems: "center" }}><BarChart3 size={30} strokeWidth={1.75} /> 百万级阅读</span>
                  </div>
                </Layer>
                {/* 6 · scrub */}
                <Layer t={t} tin={K(17, 0.08)} tout={K(21)}>
                  <At x={-420} y={-44} anchor="left" style={txt(26, 500, GRAY)}>阅读量</At>
                  <At x={420} y={-46} anchor="right" style={{ ...txt(40, 700, INK), fontVariantNumeric: "tabular-nums" }}>
                    {t >= K(20) ? "百万级阅读" : scrub > 0.98 ? "100万+" : `${Math.round(scrub * 100)}万`}
                  </At>
                  <div style={{ position: "absolute", left: -420, top: 23, width: 840, height: 14, borderRadius: 7, background: LINE }}>
                    <div style={{ width: `${scrub * 100}%`, height: "100%", borderRadius: 7, background: TEAL }} />
                  </div>
                  <div style={{ position: "absolute", left: -420 + scrub * 840 - 22, top: 8, width: 44, height: 44, borderRadius: 22, background: WHITE, boxShadow: "0 2px 10px rgba(0,0,0,0.18)", transform: `scale(${t >= K(17, 0.35) && t <= K(20) ? 1.15 : 1})` }} />
                </Layer>
                {/* 7 · star slider */}
                <Layer t={t} tin={K(21, 0.08)} tout={K(25)}>
                  <At x={0} y={-310 - over * 0.3} style={{ ...txt(46, 700, INK), fontVariantNumeric: "tabular-nums" }}>{Math.round(vol * 3088).toLocaleString("en-US")}</At>
                  <At x={0} y={-262 - over * 0.3} style={{ ...txt(22, 500, GRAY), display: "flex", alignItems: "center", gap: 6 }}>
                    <Star size={20} strokeWidth={2} color={TEAL} fill={TEAL} /> GitHub Stars
                  </At>
                  <div style={{ position: "absolute", left: -60, top: -200 - over * 0.6, width: 120, height: 520 + over * 0.6, borderRadius: 60, background: LINE, overflow: "hidden" }}>
                    <div style={{ position: "absolute", left: 0, bottom: 0, width: "100%", height: `${vol * 100}%`, background: TEAL, borderRadius: 60 }} />
                  </div>
                </Layer>
                {/* 8 · toggle knob, 9 · tab indicator */}
                <Layer t={t} tin={K(25, 0.08)} tout={K(33)}>
                  <div style={{ position: "absolute", left: knobL, top: t < K(29) ? -64 : -55, width: Math.max(0, knobR - knobL), height: t < K(29) ? 128 : 110, borderRadius: 64, background: t < K(29) ? WHITE : TEAL, boxShadow: t < K(29) ? "0 3px 10px rgba(0,0,0,0.18)" : "none" }} />
                </Layer>
                <Layer t={t} tin={K(29, 0.12)} tout={K(33)}>
                  {TABS.map((tab, i) => (
                    <At key={tab} x={-375 + i * 250} y={0} style={txt(30, 600, i === tabActive ? WHITE : INK)}>{tab}</At>
                  ))}
                </Layer>
                {/* 10 · chart */}
                <Layer t={t} tin={K(33, 0.1)} tout={K(41)}>
                  <At x={-460} y={-350} anchor="left" style={txt(34, 700, INK)}>开源项目 · GitHub Stars</At>
                  <At x={-460} y={-305} anchor="left" style={txt(22, 400, GRAY)}>github.com/andyhuo520</At>
                  <At x={460} y={-340} anchor="right" style={{ ...txt(34, 700, TEAL), ...swap(t, K(40), K(41)) }}>共 3,088★</At>
                  <div style={{ position: "absolute", left: -470, top: 300, width: 940, height: 2, background: LINE }} />
                  {REPOS.map((rp, i) => {
                    const bh = (rp.s / 1373) * 520 * step(t - K(34, i * 0.25), UI);
                    const x = -375 + i * 150;
                    return (
                      <React.Fragment key={rp.n}>
                        <div style={{ position: "absolute", left: x - 45, top: 300 - bh, width: 90, height: bh, borderRadius: 14, background: hover === i ? TEAL : INK }} />
                        <At x={x} y={300 - bh - 26} style={{ ...txt(22, 600, INK), opacity: clamp01(bh / 60) }}>{rp.s.toLocaleString("en-US")}</At>
                        <At x={x} y={336} style={txt(20, 500, GRAY)}>{rp.n}</At>
                      </React.Fragment>
                    );
                  })}
                </Layer>
                {/* 11 · command palette */}
                <Layer t={t} tin={K(41, 0.1)} tout={K(45)}>
                  <Search size={34} strokeWidth={1.75} color={GRAY} style={{ position: "absolute", left: -370, top: -222 }} />
                  <At x={-316} y={-205} anchor="left" style={txt(34, 500, q ? INK : GRAY)}>
                    {q || "搜索…"}
                    <span style={{ display: "inline-block", width: 3, height: 36, marginLeft: 3, verticalAlign: "-6px", background: TEAL, opacity: Math.floor(t * 3) % 2 === 0 ? 1 : 0 }} />
                  </At>
                  <At x={370} y={-205} anchor="right" style={{ ...txt(24, 600, GRAY), padding: "6px 12px", borderRadius: 10, border: `2px solid ${LINE}` }}>⌘K</At>
                  <div style={{ position: "absolute", left: -410, top: -150, width: 820, height: 2, background: LINE }} />
                  {CMD.map((it, i) => {
                    const idxAt = (qq: string) => {
                      const vis = CMD.filter((c) => c.t.toLowerCase().includes(qq));
                      return { idx: vis.indexOf(it), n: vis.length };
                    };
                    const keys = QUERY.map(([tt, qq]) => {
                      const { idx } = idxAt(qq);
                      return [tt, idx < 0 ? i : idx, idx < 0 ? 0 : 1] as const;
                    });
                    const y = -100 + track(t, keys.map(([tt, yy]) => [tt, yy] as [number, number])) * 78;
                    const op = track(t, keys.map(([tt, , o]) => [tt, o] as [number, number]));
                    const Icon = it.icon;
                    const first = idxAt(q).idx === 0;
                    return (
                      <div key={it.t} style={{ position: "absolute", left: -390, top: y - 32, width: 780, height: 64, borderRadius: 14, background: first ? "#F1EFEB" : "transparent", opacity: clamp01(op), filter: `blur(${(1 - clamp01(op)) * 6}px)`, display: "flex", alignItems: "center", gap: 18, padding: "0 16px", boxSizing: "border-box" }}>
                        <Icon size={28} strokeWidth={1.75} color={first ? TEAL : INK} />
                        <span style={txt(28, 600, INK)}>{it.t}</span>
                        <span style={{ ...txt(20, 400, GRAY), marginLeft: "auto" }}>{it.s}</span>
                      </div>
                    );
                  })}
                </Layer>
                {/* 12 · toast */}
                <Layer t={t} tin={K(45, 0.1)} tout={K(53)}>
                  <div style={{ position: "absolute", left: -332, top: -32, width: 64, height: 64, borderRadius: 32, background: TEAL, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${step(t - K(45, 0.1), UI)})` }}>
                    <Check size={36} strokeWidth={2.6} color={WHITE} />
                  </div>
                  <div style={{ position: "absolute", left: -244, top: -44, whiteSpace: "nowrap" }}>
                    <div style={txt(34, 600, WHITE)}>已关注 @berryxia</div>
                    <div style={{ ...txt(24, 400, "rgba(255,255,255,0.6)"), marginTop: 4, ...swap(t, K(46), K(53)) }}>一起把 AI 变成生产力</div>
                  </div>
                  <At x={345} y={0} anchor="right" style={{ ...txt(22, 600, TEAL), ...swap(t, K(49), K(53)) }}>x.com/berryxia</At>
                </Layer>
                {/* 13 · back to the button */}
                <Layer t={t} tin={K(53, 0.1)} tout={99}>
                  <At x={0} y={0} style={txt(40, 600, WHITE)}>Follow @berryxia</At>
                </Layer>
              </div>
            </div>

            {/* chart tooltip, outside the clipped shape */}
            {hover >= 0 && (
              <div style={{ position: "absolute", left: cx + 34, top: cy - 70, width: 330, padding: "16px 20px", borderRadius: 16, background: INK, boxShadow: "0 12px 30px rgba(0,0,0,0.2)", ...swap(t, K(37 + hover, -0.1), K(38 + hover, -0.12)) }}>
                <div style={txt(24, 600, WHITE)}>{REPOS[hover].n}</div>
                <div style={{ ...txt(22, 600, TEAL), marginTop: 2 }}>{REPOS[hover].s.toLocaleString("en-US")} ★</div>
                <div style={{ ...txt(18, 400, "rgba(255,255,255,0.6)"), marginTop: 2 }}>{REPOS[hover].d}</div>
              </div>
            )}
          </div>

          {/* cursor in screen space */}
          <svg width={48} height={48} viewBox="0 0 24 24" style={{ position: "absolute", left: sx - 5, top: sy - 3, transform: `scale(${isDown ? 0.88 : 1})`, transformOrigin: "5px 3px", filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.25))" }}>
            <path d="M5 3 L5 19 L9.5 14.8 L12.6 21 L15.2 19.8 L12.2 13.7 L18.5 13.4 Z" fill={INK} stroke={WHITE} strokeWidth={1.4} strokeLinejoin="round" />
          </svg>
        </AbsoluteFill>
      </CameraMotionBlur>
      <Audio src={staticFile("music/bgm.wav")} volume={(fr) => interpolate(fr, [0, 3, durationInFrames - 14, durationInFrames - 1], [0.35, 0.7, 0.7, 0.35], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      <SoundCues cues={cues()} />
    </AbsoluteFill>
  );
};

const at = (s: number) => Math.round(s * FPS);

const cues = (): Cue[] => [
  { at: at(K(3)), name: "click", volume: 0.8 },
  { at: at(K(4)), name: "swish-1", volume: 0.15 },
  { at: at(K(7)), name: "done", volume: 0.45 },
  { at: at(K(9)), name: "pop", volume: 0.35 },
  { at: at(K(10)), name: "tap", volume: 0.3 },
  { at: at(K(13)), name: "swish-2", volume: 0.15 },
  ...keyCues(TWEET, Array.from(TWEET).map((_, i) => (i / TWEET_CPS) * FPS), at(TWEET_T0), 0.3, 4),
  { at: at(K(15)), name: "click", volume: 0.7 },
  { at: at(K(15, 0.02)), name: "pop", volume: 0.3 },
  { at: at(K(17, 0.35)), name: "click", volume: 0.6 },
  { at: at(K(20)), name: "tap", volume: 0.4 },
  { at: at(K(22)), name: "click", volume: 0.6 },
  { at: at(K(24)), name: "tap", volume: 0.4 },
  { at: at(K(27)), name: "click", volume: 0.7 },
  ...[30, 31, 32].map((b) => ({ at: at(K(b)), name: "tap", volume: 0.45 })),
  { at: at(K(33)), name: "swish-3", volume: 0.15 },
  ...[37, 38, 39].map((b) => ({ at: at(K(b, -0.1)), name: "tap", volume: 0.2 })),
  { at: at(K(41)), name: "swish-1", volume: 0.15 },
  ...QUERY.slice(1).map(([tt], i) => ({ at: at(tt), name: `key-${(i % 7) + 1}`, volume: 0.45 })),
  { at: at(K(45)), name: "click", volume: 0.6 },
  { at: at(K(45, 0.1)), name: "pop", volume: 0.35 },
  { at: at(K(49)), name: "ding", volume: 0.25 },
  { at: at(K(53)), name: "swish-2", volume: 0.15 },
];
