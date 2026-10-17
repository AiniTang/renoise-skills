// 动效图标样片：lucide-animated（逐帧替身）+ Noto 动态 emoji，124 BPM 卡拍
import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { AnimatedIcon } from "../icons/AnimatedIcon";
import { NotoEmoji } from "../icons/NotoEmoji";
import type { IconName } from "../icons/la";
import { E, clamp01, mix } from "../cinematic/motion";
import { step, UI, LEAD } from "../cinematic/spring";
import { SoundCues, type Cue } from "../cinematic/sfx";

const BPM = 124;
const B = (30 * 60) / BPM;
const at = (b: number) => Math.round(b * B);
const S = { title: 0, wall: 6, flow: 22, emoji: 32, ewall: 40, end: 47, total: 54 };
export const REEL_FRAMES = at(S.total);

const INK = "#07080C";
const TXT = "#F4F5F7";
const DIM = "rgba(244,245,247,0.55)";
const FONT = '"PingFang SC", "SF Pro Display", "Helvetica Neue", sans-serif';
const PAL = ["#5B8CFF", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#06B6D4"];

const sp = (f: number, t0: number, c = UI) => (f < t0 ? 0 : step((f - t0) / 30, c));

// 应用图标底板：未点亮是玻璃，点亮是渐变 + 柔光；图标是 lucide-animated，落地那一拍开始播
const Tile: React.FC<{ name: IconName; size: number; on: number; color: string; playAt: number }> = ({ name, size, on, color, playAt }) => (
  <div style={{ position: "relative", width: size, height: size, borderRadius: size * 0.2237 }}>
    <div style={{ position: "absolute", inset: 0, borderRadius: "inherit", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)" }} />
    <div
      style={{
        position: "absolute", inset: 0, borderRadius: "inherit", opacity: on,
        background: `linear-gradient(160deg, color-mix(in srgb, ${color} 70%, white) 0%, ${color} 48%, color-mix(in srgb, ${color} 78%, black) 100%)`,
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.5), 0 ${size * 0.12}px ${size * 0.3}px color-mix(in srgb, ${color} ${35 * on}%, transparent)`,
      }}
    />
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: mix(0.55, 1, on) }}>
      <AnimatedIcon name={name} at={playAt} size={size * 0.46} color={on > 0.5 ? "#fff" : color} />
    </div>
  </div>
);

const Title: React.FC<{ f: number }> = ({ f }) => {
  const a = sp(f, at(0.5), LEAD);
  const b = sp(f, at(1.5), LEAD);
  const out = clamp01((f - at(S.wall - 0.5)) / 8);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - out }}>
      <div style={{ transform: `scale(${mix(0.6, 1, a)})`, opacity: a, marginBottom: 36 }}>
        <Tile name="sparkles" size={180} on={a} color={PAL[1]} playAt={at(1)} />
      </div>
      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 108, color: TXT, letterSpacing: -2, opacity: a, transform: `translateY(${mix(40, 0, a)}px)` }}>
        会动的图标
      </div>
      <div style={{ fontFamily: FONT, fontSize: 34, color: DIM, marginTop: 20, opacity: b, transform: `translateY(${mix(24, 0, b)}px)` }}>
        lucide-animated 467 个 · Noto 动态 emoji 881 个 · 逐帧渲染
      </div>
    </AbsoluteFill>
  );
};

const WALL: IconName[] = [
  "rocket", "bell", "message-circle-more", "settings", "search", "brain", "calendar-days", "clock",
  "layers", "cloud-upload", "shield-check", "lock", "users", "bot", "mic", "file-text",
  "link", "gauge", "git-branch", "terminal", "earth", "party-popper", "heart-pulse", "chart-column-increasing",
];
const wallLand = (i: number) => at(S.wall + 0.5) + Math.round(((i % 8) + Math.floor(i / 8)) * (B / 2));

const Wall: React.FC<{ f: number }> = ({ f }) => {
  const size = 150, gap = 44;
  const W = 8 * size + 7 * gap;
  const cap = sp(f, at(S.wall + 5), LEAD);
  const out = clamp01((f - at(S.flow - 0.5)) / 8);
  const replay = at(S.wall + 11);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - out }}>
      <div style={{ display: "flex", flexWrap: "wrap", width: W, gap, marginTop: -40 }}>
        {WALL.map((n, i) => {
          const land = wallLand(i);
          const p = sp(f, land, LEAD);
          // 第二波：从中间向外再点一次，同一个图标重播
          const again = replay + Math.round(Math.abs((i % 8) - 3.5) * (B / 3));
          return (
            <div key={n} style={{ opacity: clamp01(p * 1.4), transform: `translateY(${mix(60, 0, p)}px) scale(${mix(0.7, 1, p)})` }}>
              <Tile name={n} size={size} on={clamp01(p)} color={PAL[i % PAL.length]} playAt={f >= again ? again : land + 2} />
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 110, fontFamily: FONT, fontSize: 40, color: TXT, opacity: cap, transform: `translateY(${mix(20, 0, cap)}px)` }}>
        落地那一拍播一次，<span style={{ color: DIM }}>播完就停住</span>
      </div>
    </AbsoluteFill>
  );
};

const FLOW: { n: IconName; t: string }[] = [
  { n: "message-circle-more", t: "收到需求" },
  { n: "brain", t: "拆解思路" },
  { n: "settings", t: "自动执行" },
  { n: "circle-check", t: "人工验收" },
  { n: "send", t: "一键发布" },
];
const flowAt = (i: number) => at(S.flow + 1 + i * 1.5);

const Flow: React.FC<{ f: number }> = ({ f }) => {
  const size = 170, gap = 150;
  const W = FLOW.length * size + (FLOW.length - 1) * gap;
  const head = sp(f, at(S.flow), LEAD);
  const out = clamp01((f - at(S.emoji - 0.5)) / 8);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - out }}>
      <div style={{ position: "absolute", top: 200, fontFamily: FONT, fontSize: 64, fontWeight: 700, color: TXT, opacity: head }}>流程节点，逐个亮起</div>
      <div style={{ position: "relative", width: W, height: size + 90, marginTop: 60 }}>
        {FLOW.slice(1).map((_, i) => {
          const x0 = i * (size + gap) + size + 16;
          const len = gap - 32;
          const p = clamp01((f - flowAt(i)) / (flowAt(i + 1) - flowAt(i)));
          return (
            <div key={i} style={{ position: "absolute", left: x0, top: size / 2 - 2, height: 4, width: len * E.inOut(p), borderRadius: 2, background: `linear-gradient(90deg, ${PAL[i]}, ${PAL[i + 1]})` }} />
          );
        })}
        {FLOW.map((s, i) => {
          const p = sp(f, flowAt(i), LEAD);
          return (
            <div key={s.n} style={{ position: "absolute", left: i * (size + gap), top: 0, width: size, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ transform: `scale(${mix(0.86, 1, p)})` }}>
                <Tile name={s.n} size={size} on={clamp01(p)} color={PAL[i]} playAt={flowAt(i) + 2} />
              </div>
              <div style={{ marginTop: 28, fontFamily: FONT, fontSize: 34, color: p > 0.5 ? TXT : DIM, whiteSpace: "nowrap" }}>{s.t}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const HERO = ["🚀", "🎯", "💡", "🔥", "🎉", "🤯"];
const heroAt = (i: number) => at(S.emoji + 1 + i);

const Emoji: React.FC<{ f: number }> = ({ f }) => {
  const head = sp(f, at(S.emoji), LEAD);
  const out = clamp01((f - at(S.ewall - 0.5)) / 8);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - out }}>
      <div style={{ position: "absolute", top: 190, fontFamily: FONT, fontSize: 64, fontWeight: 700, color: TXT, opacity: head }}>emoji 也会动</div>
      <div style={{ display: "flex", gap: 70, marginTop: 80 }}>
        {HERO.map((c, i) => {
          const p = sp(f, heroAt(i), LEAD);
          return (
            <div key={c} style={{ opacity: clamp01(p * 1.5), transform: `translateY(${mix(80, 0, p)}px) scale(${mix(0.5, 1, p)})` }}>
              <NotoEmoji char={c} at={heroAt(i)} size={210} />
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", bottom: 150, fontFamily: FONT, fontSize: 34, color: DIM, opacity: sp(f, at(S.emoji + 4), LEAD) }}>
        Google Noto 动态 emoji · 矢量 Lottie，4K 也清晰
      </div>
    </AbsoluteFill>
  );
};

const EWALL = ["👋", "😎", "🤝", "📊", "💻", "🧠", "✅", "📦", "👍", "✨", "💯", "⏰", "📚", "🎬", "⚙️", "✍️", "❤️", "🚀"];
const EmojiWall: React.FC<{ f: number }> = ({ f }) => {
  const out = clamp01((f - at(S.end - 0.5)) / 8);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - out }}>
      <div style={{ display: "flex", flexWrap: "wrap", width: 9 * 150 + 8 * 40, gap: 40 }}>
        {EWALL.map((c, i) => {
          const land = at(S.ewall) + Math.round(((i % 9) + Math.floor(i / 9) * 2) * (B / 3));
          const p = sp(f, land, LEAD);
          return (
            <div key={c} style={{ opacity: clamp01(p * 1.5), transform: `scale(${mix(0.4, 1, p)})` }}>
              <NotoEmoji char={c} at={land} size={150} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const End: React.FC<{ f: number }> = ({ f }) => {
  const a = sp(f, at(S.end), LEAD);
  const b = sp(f, at(S.end + 1.5), LEAD);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", gap: 36, alignItems: "center", opacity: a, transform: `scale(${mix(0.8, 1, a)})` }}>
        <Tile name="sparkles" size={130} on={1} color={PAL[1]} playAt={at(S.end)} />
        <NotoEmoji char="✨" at={at(S.end)} size={130} />
      </div>
      <div style={{ fontFamily: FONT, fontSize: 84, fontWeight: 700, color: TXT, marginTop: 40, opacity: a }}>动效图标已接入 promo-video</div>
      <div style={{ fontFamily: FONT, fontSize: 28, color: DIM, marginTop: 28, opacity: b }}>
        Icons: lucide-animated (MIT) · Animated emoji: Google Noto
      </div>
    </AbsoluteFill>
  );
};

const cues: Cue[] = [
  { at: at(0.5), name: "swish-1", volume: 0.5 },
  { at: at(S.wall), name: "swish-2", volume: 0.45 },
  ...WALL.map((_, i) => ({ at: wallLand(i), name: "pop", volume: 0.22 })).filter((_, i) => i % 3 === 0),
  { at: at(S.flow), name: "swish-1", volume: 0.45 },
  ...FLOW.map((_, i) => ({ at: flowAt(i), name: "ding", volume: 0.3 })),
  { at: at(S.emoji), name: "swish-2", volume: 0.45 },
  ...HERO.map((_, i) => ({ at: heroAt(i), name: "pop", volume: 0.35 })),
  { at: at(S.end), name: "impact", volume: 0.5 },
];

export const Reel: React.FC = () => {
  const f = useCurrentFrame();
  const fadeOut = interpolate(f, [REEL_FRAMES - 20, REEL_FRAMES], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 50% 45%, #141726 0%, ${INK} 70%)` }}>
      <AbsoluteFill style={{ opacity: fadeOut }}>
        {f < at(S.wall) && <Title f={f} />}
        {f >= at(S.wall - 0.5) && f < at(S.flow) && <Wall f={f} />}
        {f >= at(S.flow - 0.5) && f < at(S.emoji) && <Flow f={f} />}
        {f >= at(S.emoji - 0.5) && f < at(S.ewall) && <Emoji f={f} />}
        {f >= at(S.ewall - 0.5) && f < at(S.end) && <EmojiWall f={f} />}
        {f >= at(S.end - 0.5) && <End f={f} />}
      </AbsoluteFill>
      <Audio src={staticFile("music/bgm.wav")} volume={0.8} />
      <SoundCues cues={cues} />
    </AbsoluteFill>
  );
};
