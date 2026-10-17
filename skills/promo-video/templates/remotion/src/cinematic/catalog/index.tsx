import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";
import { step, type SpringCfg } from "../spring";

/*
 * Style catalogue reel (风格目录片): each style is a live mini-film in a player window with an info card
 * (number / name / English name / what it is / tech tags / work title / ▶ now playing + segmented progress).
 * Windows open out of a dot and close back into it; the dot travels to the next window, so there are no cuts.
 * It ends on a wall of every sample still playing, then folds into one dot for the lockup.
 */

const hz = (f: number) => 2 * Math.PI * f;
const SOFT: SpringCfg = { w: hz(2.2), z: 0.8 };
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

export type CatalogItem = {
  no: string; // "01"
  zh: string; // 综艺花字
  en: string; // VARIETY CAPTIONS
  desc: string[]; // 2–3 short lines
  tags: string[];
  work: string; // 作品名
  tint: string; // ambient glow colour
  accent: string;
  Sample?: React.FC; // live: renders at 1920×1080 using its own useCurrentFrame (DOM/SVG/canvas only)
  video?: string; // pre-rendered sample under public/ (use this for Three.js samples: WebGL measures its size through CSS scale)
  thumb?: string; // small proxy of `video` for the end wall (e.g. 640×360, keyframe every 6 frames): 15 full-HD decodes per frame time out
  len?: number; // on-screen sample length in frames (default 300); the clip should run ~30 frames longer for the close
};

export type CatalogFonts = { serifZh: string; sansZh: string; display: string; sans: string; mono: string };

export const CATALOG = { intro: 105, slot: 330, open: 18, close: 16, outro: 195 };
export const catalogLength = (n: number) => CATALOG.intro + n * CATALOG.slot + CATALOG.outro;

const WIN = { w: 1180, h: 664 };
const winCenter = (i: number) => ({ x: i % 2 === 0 ? 1190 : 730, y: 548 });

/** Wall tile i of n: centre, size and a small stagger (tiles fly out from the middle one ring at a time). */
const wallGrid = (n: number, i: number) => {
  if (n <= 4) {
    const w = 780;
    const h = (w * 9) / 16;
    return { x: i % 2 === 0 ? 960 - w / 2 - 14 : 960 + w / 2 + 14, y: i < 2 ? 540 - h / 2 - 14 : 540 + h / 2 + 14, w, h, delay: 0 };
  }
  const cols = n <= 6 ? 3 : n <= 12 ? 4 : 5;
  const rows = Math.ceil(n / cols);
  const gap = 18;
  const w = Math.min((1920 - 2 * 70 - (cols - 1) * gap) / cols, ((1080 - 2 * 90 - (rows - 1) * gap) / rows) * (16 / 9));
  const h = (w * 9) / 16;
  const r = Math.floor(i / cols);
  const inRow = r === rows - 1 ? n - r * cols : cols;
  const c = i - r * cols;
  const x = 960 + (c - (inRow - 1) / 2) * (w + gap);
  const y = 540 + (r - (rows - 1) / 2) * (h + gap);
  const ring = Math.max(Math.abs(c - (inRow - 1) / 2), Math.abs(r - (rows - 1) / 2));
  return { x, y, w, h, delay: ring * 3 };
};

/** The dot's position at frame f: rests in window centres, springs between them. */
const dotAt = (f: number, n: number) => {
  const { intro, slot, open, close } = CATALOG;
  const centres = Array.from({ length: n }, (_, i) => winCenter(i));
  const keys: [number, { x: number; y: number }][] = [[0, { x: 960, y: 540 }]];
  centres.forEach((c, i) => keys.push([intro - 12 + i * slot - (i === 0 ? 0 : open), c]));
  keys.push([intro + n * slot - 14, { x: 960, y: 540 }]);
  let x = keys[0][1].x;
  let y = keys[0][1].y;
  for (let k = 1; k < keys.length; k++) {
    const s = step((f - keys[k][0]) / 30, SOFT);
    x += (keys[k][1].x - keys[k - 1][1].x) * s;
    y += (keys[k][1].y - keys[k - 1][1].y) * s - Math.sin(Math.PI * clamp01(s)) * 60 * (k > 1 && k < keys.length - 1 ? 1 : 0);
  }
  return { x, y };
};

/** A sample at window size: a pre-rendered clip (preferred) or a live component scaled down from 1920×1080. */
const SampleView: React.FC<{ item: CatalogItem; w: number; h: number; from?: number; proxy?: boolean }> = ({ item, w, h, from = 0, proxy }) =>
  item.video ? (
    <OffthreadVideo src={staticFile(proxy && item.thumb ? item.thumb : item.video)} muted startFrom={from} style={{ width: w, height: h, objectFit: "cover", display: "block" }} />
  ) : item.Sample ? (
    <div style={{ width: 1920, height: 1080, transform: `scale(${w / 1920})`, transformOrigin: "0 0" }}>
      <item.Sample />
    </div>
  ) : null;

const Window: React.FC<{ item: CatalogItem; local: number; center: { x: number; y: number }; w?: number; h?: number; label?: boolean; fonts?: CatalogFonts }> = ({
  item,
  local,
  center,
  w = WIN.w,
  h = WIN.h,
  label,
  fonts,
}) => {
  const { open, slot, close } = CATALOG;
  const len = item.len ?? 300;
  const o = ease(clamp01(local / open));
  const c = ease(clamp01((local - len) / close));
  const r = Math.hypot(w, h) / 2;
  const rad = 14 + (r - 14) * o * (1 - c);
  const scale = 0.94 + 0.06 * o;
  if (local < 0 || local > len + close + 2) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: center.x - w / 2,
        top: center.y - h / 2,
        width: w,
        height: h,
        borderRadius: 16,
        overflow: "hidden",
        clipPath: `circle(${rad}px at 50% 50%)`,
        transform: `scale(${scale})`,
        boxShadow: "0 40px 90px rgba(0,0,0,0.45)",
        background: "#000",
      }}
    >
      <SampleView item={item} w={w} h={h} />
      <div style={{ position: "absolute", inset: 0, borderRadius: 16, boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.08)", pointerEvents: "none" }} />
      {label && fonts && (
        <div style={{ position: "absolute", left: 18, bottom: 16, display: "flex", gap: 10, alignItems: "baseline", background: "rgba(20,19,18,0.72)", padding: "8px 14px", borderRadius: 10 }}>
          <span style={{ fontFamily: fonts.mono, fontSize: 18, color: item.accent }}>{item.no}</span>
          <span style={{ fontFamily: fonts.serifZh, fontWeight: 800, fontSize: 22, color: "#F4EEE2" }}>{item.zh}</span>
        </div>
      )}
    </div>
  );
};

const Panel: React.FC<{ item: CatalogItem; local: number; total: number; side: "left" | "right"; fonts: CatalogFonts; count: number }> = ({ item, local, side, fonts, count }) => {
  const len = item.len ?? 300;
  const inK = (i: number) => step(Math.max(0, (local - 6 - i * 3) / 30), SOFT);
  const outK = ease(clamp01((local - len + 4) / 14));
  const x = side === "left" ? 110 : 1400;
  const line = (i: number, node: React.ReactNode, mt = 0) => (
    <div style={{ transform: `translateY(${(1 - inK(i)) * 26}px)`, opacity: Math.min(1, inK(i) * 1.3) * (1 - outK), marginTop: mt }}>{node}</div>
  );
  const secs = Math.max(0, Math.min(len, local)) / 30;
  const segs = 10;
  const prog = clamp01(local / len);
  const mmss = (s: number) => `00:${String(Math.floor(s)).padStart(2, "0")}`;
  return (
    <div style={{ position: "absolute", left: x, top: 250, width: 420, color: "#F4EEE2" }}>
      {line(0, <div style={{ fontFamily: fonts.mono, fontSize: 40, color: item.accent }}>{item.no}<span style={{ fontSize: 20, color: "rgba(244,238,226,0.45)" }}> / {String(count).padStart(2, "0")}</span></div>)}
      {line(1, <div style={{ fontFamily: fonts.serifZh, fontWeight: 900, fontSize: 72, lineHeight: 1.08, letterSpacing: "0.01em" }}>{item.zh}</div>, 14)}
      {line(2, <div style={{ fontFamily: fonts.sans, fontWeight: 700, fontSize: 17, letterSpacing: "0.3em", color: "rgba(244,238,226,0.62)" }}>{item.en}</div>, 12)}
      {line(3, <div style={{ width: 42, height: 3, background: item.accent, borderRadius: 2 }} />, 22)}
      {line(
        4,
        <div style={{ fontFamily: fonts.sansZh, fontSize: 22, lineHeight: 1.62, color: "rgba(244,238,226,0.82)" }}>
          {item.desc.map((d, i) => (
            <div key={i}>{d}</div>
          ))}
        </div>,
        22,
      )}
      {line(
        5,
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {item.tags.map((tg) => (
            <span key={tg} style={{ fontFamily: fonts.mono, fontSize: 15, color: "rgba(244,238,226,0.75)", border: "1px solid rgba(244,238,226,0.25)", borderRadius: 999, padding: "5px 12px" }}>
              {tg}
            </span>
          ))}
        </div>,
        24,
      )}
      {line(
        6,
        <div style={{ borderTop: "1px solid rgba(244,238,226,0.14)", paddingTop: 18 }}>
          <div style={{ fontFamily: fonts.sansZh, fontSize: 16, color: "rgba(244,238,226,0.55)" }}>
            作品&nbsp;&nbsp;<span style={{ fontFamily: fonts.sans, fontWeight: 600, color: "#F4EEE2" }}>{item.work}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14, fontFamily: fonts.mono, fontSize: 15, color: "rgba(244,238,226,0.7)" }}>
            <span>
              ▶ <span style={{ fontFamily: fonts.sansZh }}>正在播放</span>
            </span>
            <span>
              {mmss(secs)} / {mmss(len / 30)}
            </span>
          </div>
          <div style={{ display: "flex", gap: 5, marginTop: 10 }}>
            {Array.from({ length: segs }, (_, i) => (
              <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: "rgba(244,238,226,0.16)", overflow: "hidden" }}>
                <div style={{ width: `${clamp01(prog * segs - i) * 100}%`, height: "100%", background: item.accent }} />
              </div>
            ))}
          </div>
        </div>,
        40,
      )}
    </div>
  );
};

/** The whole reel. `title`/`sub` show in the intro; `Lockup` renders the end card. */
export const StyleCatalog: React.FC<{
  items: CatalogItem[];
  fonts: CatalogFonts;
  header: React.ReactNode;
  Intro: React.FC<{ t: number }>;
  Lockup: React.FC<{ t: number }>;
  dot?: string;
}> = ({ items, fonts, header, Intro, Lockup, dot = "#CFE3A0" }) => {
  const f = useCurrentFrame();
  const { intro, slot, outro, open } = CATALOG;
  const n = items.length;
  const outroAt = intro + n * slot;
  const cur = Math.min(n - 1, Math.max(0, Math.floor((f - intro) / slot)));
  const inItems = f >= intro && f < outroAt;
  const local = f - intro - cur * slot;
  const tint = inItems ? items[cur].tint : "#2A2723";
  const tintK = inItems ? ease(clamp01(local / 20)) * (1 - ease(clamp01((local - 300) / 20))) : 0;
  const d = dotAt(f, n);
  const itemOpen = inItems && local >= 0 && local < (items[cur].len ?? 300) + 14;
  const wall = f >= outroAt + 4;
  const wallK = ease(clamp01((f - outroAt - 4) / 18)) * (1 - ease(clamp01((f - outroAt - 108) / 16)));
  return (
    <AbsoluteFill style={{ background: "#141312" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${inItems ? winCenter(cur).x / 19.2 : 50}% 52%, ${tint} 0%, transparent 62%)`, opacity: 0.55 * tintK }} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,0.55) 100%)" }} />
      <div style={{ position: "absolute", left: 110, top: 64, opacity: f > 60 && f < outroAt + 2 ? 1 : 0 }}>{header}</div>

      {f < intro + open && <Intro t={f} />}

      {items.map((it, i) => (
        <Sequence key={it.no} from={intro + i * slot} durationInFrames={slot} layout="none">
          <Window item={it} local={f - intro - i * slot} center={winCenter(i)} />
          <Panel item={it} local={f - intro - i * slot} total={slot} side={i % 2 === 0 ? "left" : "right"} fonts={fonts} count={n} />
        </Sequence>
      ))}

      {/* the travelling dot (hidden while a window is open) */}
      {!itemOpen && !wall && f >= 20 && <div style={{ position: "absolute", left: d.x - 14, top: d.y - 14, width: 28, height: 28, borderRadius: "50%", background: dot, boxShadow: `0 0 28px ${dot}` }} />}

      {/* the wall: every sample still playing (2×2 up to four styles, then a centred grid) */}
      {wall && wallK > 0 &&
        items.map((it, i) => {
          const g = wallGrid(n, i);
          const k = ease(clamp01((f - outroAt - 4 - g.delay) / 18)) * (1 - ease(clamp01((f - outroAt - 108 + g.delay * 0.5) / 16)));
          if (k <= 0) return null;
          const cx = 960 + (g.x - 960) * k;
          const cy = 540 + (g.y - 540) * k;
          const s = 0.2 + 0.8 * k;
          const lab = g.w / 780;
          return (
            <Sequence key={`w${it.no}`} from={it.video ? outroAt + 4 : outroAt - 150} layout="none">
              <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transform: `translate(${cx - 960}px, ${cy - 540}px) scale(${s})`, transformOrigin: "960px 540px", opacity: k }}>
                <div style={{ position: "absolute", left: 960 - g.w / 2, top: 540 - g.h / 2, width: g.w, height: g.h, borderRadius: 14 * Math.max(0.6, lab), overflow: "hidden", boxShadow: "0 30px 70px rgba(0,0,0,0.5)" }}>
                  <SampleView item={it} w={g.w} h={g.h} from={it.video ? 150 : 0} proxy />
                  <div style={{ position: "absolute", left: 16 * lab + 4, bottom: 14 * lab + 4, display: "flex", gap: 10 * Math.max(0.6, lab), alignItems: "baseline", background: "rgba(20,19,18,0.72)", padding: `${7 * Math.max(0.6, lab)}px ${13 * Math.max(0.6, lab)}px`, borderRadius: 10 * Math.max(0.6, lab) }}>
                    <span style={{ fontFamily: fonts.mono, fontSize: Math.max(13, 17 * lab), color: it.accent }}>{it.no}</span>
                    <span style={{ fontFamily: fonts.serifZh, fontWeight: 800, fontSize: Math.max(15, 21 * lab), color: "#F4EEE2" }}>{it.zh}</span>
                  </div>
                </div>
              </div>
            </Sequence>
          );
        })}
      {f >= outroAt + 108 && <Lockup t={f - outroAt - 108} />}
    </AbsoluteFill>
  );
};
