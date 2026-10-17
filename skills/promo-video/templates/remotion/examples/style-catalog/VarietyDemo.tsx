import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { Burst, Confetti, HUAZI, HuaZi, Mark, shake, SpeedLines, Telop, zoomPunch } from "../cinematic/variety";
import { fam } from "../cinematic/type";

/**
 * 01 · 综艺花字 — YouWare's own "finance deck" demo in three sped-up beats, with variety captions on each reaction.
 * 300 frames @ 30 fps. Speeds shown on screen are the real playback rates of the footage.
 */
export const VARIETY_LEN = 330; // 300 on screen + 30 so the catalogue window can close over live footage
const EN = fam("Bricolage Grotesque");

const BEATS = [
  { from: 0, len: 90, src: 3.0, rate: 2.6 },
  { from: 90, len: 80, src: 12.5, rate: 7 },
  { from: 170, len: 160, src: 34.0, rate: 3.2 },
];
const HITS = [14, 96, 186];

const Clip: React.FC<{ src: number; rate: number }> = ({ src, rate }) => (
  <OffthreadVideo src={staticFile("clips/finance-deck.mp4")} muted startFrom={Math.round(src * 30)} playbackRate={rate} style={{ width: 1920, height: 1080, objectFit: "cover" }} />
);

export const VarietyDemo: React.FC<{ t?: number }> = ({ t: tProp }) => {
  const frame = useCurrentFrame();
  const t = tProp ?? frame;
  const z = zoomPunch(t, HITS, 0.07);
  const { dx, dy } = shake(t, [186], 12);
  return (
    <AbsoluteFill style={{ background: "#2B3320", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${dx}px, ${dy}px) scale(${z})` }}>
        {BEATS.map((b, i) => (
          <Sequence key={i} from={b.from} durationInFrames={b.len} layout="none">
            <AbsoluteFill>
              <Clip src={b.src} rate={b.rate} />
            </AbsoluteFill>
          </Sequence>
        ))}
      </AbsoluteFill>
      {/* beat 1 — the prompt */}
      <HuaZi text="ONE PROMPT?" t={t} at={12} out={84} x={960} y={190} size={132} family={EN} preset={HUAZI.fresh} rotate={-3} />
      <Mark kind="question" t={t} at={24} out={84} x={1470} y={150} size={110} rotate={12} />
      <Mark kind="question" t={t} at={30} out={84} x={430} y={230} size={80} rotate={-14} />
      {/* beat 2 — the agent works, fast-forwarded */}
      <SpeedLines t={t} at={90} dur={80} inner={560} color="rgba(255,255,255,0.55)" count={72} />
      <HuaZi text="IT'S ON IT…" t={t} at={94} out={166} x={960} y={200} size={124} family={EN} preset={HUAZI.cool} rotate={2} pop="drop" />
      <Mark kind="sweat" t={t} at={104} out={166} x={1440} y={140} size={90} rotate={10} />
      <Telop t={t} at={100} out={166} x={120} y={900} text="Working through the brief" family={EN} size={40} chip="#2A7DFF" chipText="▶▶ ×7" />
      {/* beat 3 — the deck lands */}
      <HuaZi text="WAIT…" t={t} at={174} out={296} x={560} y={170} size={92} family={EN} preset={HUAZI.note} rotate={-6} pop="slam" wobble={0.6} />
      <Burst t={t} at={184} out={296} x={1250} y={300} r={265} fill="#FFE14D">
        <HuaZi text={"A WHOLE\nDECK?!"} t={t} at={186} out={296} x={0} y={0} size={88} family={EN} preset={HUAZI.shock} rotate={-6} stagger={1.2} />
      </Burst>
      <Confetti t={t} at={190} x={1250} y={330} />
      <Mark kind="sparkle" t={t} at={200} out={296} x={900} y={420} size={70} />
      <Mark kind="sparkle" t={t} at={206} out={296} x={1620} y={560} size={56} />
      <Mark kind="bang" t={t} at={196} out={296} x={1560} y={120} size={90} rotate={14} />
      <Telop t={t} at={236} out={298} x={120} y={900} text="Made with YouWare" family={EN} size={40} chip="#7D8F57" chipText="✓ DONE" />
    </AbsoluteFill>
  );
};
