import React from "react";
import { AbsoluteFill, Audio, interpolate, staticFile } from "remotion";
import { keyCues, SoundCues, type Cue } from "../cinematic/sfx";
import { CH, PROMPT, typeAt } from "../youware-ladder/YouWareChain";
import { CATALOG, catalogLength, StyleCatalog, type CatalogFonts, type CatalogItem } from "../cinematic/catalog";
import { fam } from "../cinematic/type";
import { step } from "../cinematic/spring";

/** YouWare · 四种商用风格 — the style catalogue reel (P0 of the 15-style iteration). */
export const FONTS: CatalogFonts = {
  serifZh: fam("Noto Serif SC", "zh-Hans"),
  sansZh: fam("Noto Sans SC", "zh-Hans"),
  display: fam("Hepta Slab"),
  sans: fam("Manrope"),
  mono: fam("Geist Mono"),
};

export const ITEMS: CatalogItem[] = [
  {
    no: "01",
    zh: "综艺花字",
    en: "VARIETY CAPTIONS",
    desc: ["多层描边、弹簧弹跳、表情贴，", "把一段产品录屏变成综艺现场。", "三拍反应：提问、加速、震惊。"],
    tags: ["DOM · SVG", "弹簧动画", "倍速素材"],
    work: "A whole deck?!",
    tint: "#E0A43A",
    accent: "#FFD15C",
    video: "samples/variety.mp4",
  },
  {
    no: "02",
    zh: "贴纸风科普",
    en: "STICKER EXPLAINER",
    desc: ["官网素材做成模切贴纸，", "啪地贴上、胶带、手写批注，", "一张桌面讲清四种产出。"],
    tags: ["SVG 模切滤镜", "落地弹簧", "手写批注"],
    work: "Four kinds of work",
    tint: "#9FB86A",
    accent: "#CFE3A0",
    video: "samples/stickers.mp4",
  },
  {
    no: "03",
    zh: "等轴 2.5D",
    en: "ISOMETRIC",
    desc: ["正交相机下的桌面微缩城，", "一块输入框地砖长出四个街区，", "塔顶落下 YouWare 标志。"],
    tags: ["Three.js", "正交相机", "移轴景深"],
    work: "YouWare Town",
    tint: "#9A8FD0",
    accent: "#B4A5E4",
    video: "samples/iso.mp4",
  },
  {
    no: "04",
    zh: "形变动画",
    en: "SHAPE MORPH",
    desc: ["一个容器连续变形，一次一个：", "输入框、网站、幻灯片、表格、报告，", "最后变成你和你的 AI 专家团队。"],
    tags: ["SVG 逐点插值", "一次一个", "无硬切"],
    work: "From answers to outcomes",
    tint: "#EE8C6C",
    accent: "#EE8C6C",
    video: "samples/morph.mp4",
  },
];

export const REEL_LEN = catalogLength(ITEMS.length);
const CREAM = "#F4EEE2";

const mask = (file: string, color = CREAM): React.CSSProperties => ({
  WebkitMaskImage: `url(${staticFile(`brand/${file}`)})`,
  WebkitMaskSize: "100% 100%",
  maskImage: `url(${staticFile(`brand/${file}`)})`,
  maskSize: "100% 100%",
  background: color,
});

const Header: React.FC = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
    <div style={{ width: 138, height: 40, ...mask("lockup.svg") }} />
    <span style={{ fontFamily: FONTS.sansZh, fontSize: 18, color: "rgba(244,238,226,0.55)", letterSpacing: "0.06em" }}>四种商用风格 · 全部代码渲染</span>
  </div>
);

const rise = (t: number, at: number) => step(Math.max(0, (t - at) / 30), { w: 2 * Math.PI * 2.2, z: 0.8 });

/** Intro: the dot drops in and bounces, the title builds around it. */
const Intro: React.FC<{ t: number }> = ({ t }) => {
  const out = Math.min(1, Math.max(0, (t - 88) / 14));
  const bounce = (() => {
    const c = [16, 30, 38];
    if (t < c[0]) return -580 * (1 - Math.pow(t / c[0], 2));
    if (t < c[1]) {
      const u = (t - c[0]) / (c[1] - c[0]);
      return -4 * 70 * u * (1 - u);
    }
    if (t < c[2]) {
      const u = (t - c[1]) / (c[2] - c[1]);
      return -4 * 20 * u * (1 - u);
    }
    return 0;
  })();
  return (
    <AbsoluteFill style={{ opacity: 1 - out }}>
      {t < 40 && <div style={{ position: "absolute", left: 960 - 14, top: 540 - 14 + bounce, width: 28, height: 28, borderRadius: "50%", background: "#CFE3A0", boxShadow: "0 0 28px #CFE3A0" }} />}
      <div style={{ position: "absolute", left: 960 - 230, top: 350, width: 460, height: 133, transform: `translateY(${(1 - rise(t, 36)) * 30}px)`, opacity: rise(t, 36), ...mask("lockup.svg") }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 596, textAlign: "center", fontFamily: FONTS.serifZh, fontWeight: 800, fontSize: 56, color: CREAM, transform: `translateY(${(1 - rise(t, 44)) * 30}px)`, opacity: rise(t, 44) }}>
        一个 YouWare，四种商用风格
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 682, textAlign: "center", fontFamily: FONTS.sans, fontWeight: 700, fontSize: 17, letterSpacing: "0.32em", color: "rgba(244,238,226,0.6)", opacity: rise(t, 52) }}>
        ONE YOUWARE · FOUR STYLES · RENDERED IN CODE
      </div>
    </AbsoluteFill>
  );
};

/** End card after the wall folds away. */
const Lockup: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill>
    <div style={{ position: "absolute", left: 960 - 260, top: 380, width: 520, height: 150, transform: `translateY(${(1 - rise(t, 8)) * 30}px)`, opacity: rise(t, 8), ...mask("lockup.svg") }} />
    <div style={{ position: "absolute", left: 0, right: 0, top: 572, textAlign: "center", fontFamily: FONTS.display, fontWeight: 400, fontSize: 46, color: CREAM, opacity: rise(t, 18), letterSpacing: "-0.01em" }}>
      From answers to outcomes.
    </div>
    <div style={{ position: "absolute", left: 0, right: 0, top: 652, textAlign: "center", fontFamily: FONTS.sansZh, fontSize: 20, color: "rgba(244,238,226,0.55)", letterSpacing: "0.12em", opacity: rise(t, 28) }}>
      综艺花字 · 贴纸风 · 等轴 2.5D · 形变动画
    </div>
  </AbsoluteFill>
);

const O = (i: number) => CATALOG.intro + i * CATALOG.slot;
const OUT = O(ITEMS.length);
const CUES: Cue[] = [
  { at: 16, name: "tap", volume: 0.42 },
  { at: 30, name: "tap", volume: 0.28 },
  { at: 38, name: "tap", volume: 0.16 },
  { at: 36, name: "swish-1", volume: 0.14 },
  ...ITEMS.flatMap((_, i) => [
    { at: O(i) + 2, name: "pop", volume: 0.2 },
    { at: O(i) + 300, name: "swish-2", volume: 0.16 },
  ]),
  // 01 variety
  ...[12, 94, 174, 184].map((a, k) => ({ at: O(0) + a, name: ["pop", "whoosh", "slam-1", "impact"][k], volume: [0.32, 0.24, 0.3, 0.32][k] })),
  { at: O(0) + 24, name: "tap", volume: 0.14 },
  { at: O(0) + 100, name: "click", volume: 0.18 },
  { at: O(0) + 236, name: "done", volume: 0.22 },
  // 02 stickers
  ...[30, 44, 70, 96, 122].map((a, k) => ({ at: O(1) + a, name: k % 2 ? "paper-place-2" : "paper-place-1", volume: 0.34 })),
  ...[53, 79, 105, 131].map((a) => ({ at: O(1) + a, name: "tap", volume: 0.13 })),
  ...[0, 1, 2, 3, 4].map((k) => ({ at: O(1) + 160 + k * 7, name: "pop", volume: 0.11 })),
  { at: O(1) + 232, name: "slam-2", volume: 0.28 },
  // 03 iso
  { at: O(2) + 14, name: "click", volume: 0.24 },
  { at: O(2) + 24, name: "swish-3", volume: 0.18 },
  ...[58, 88, 118, 148].map((a) => ({ at: O(2) + a, name: "pop", volume: 0.18 })),
  { at: O(2) + 196, name: "whoosh", volume: 0.18 },
  { at: O(2) + 232, name: "impact", volume: 0.26 },
  // 04 morph chain (starts 16 frames into its sample)
  ...keyCues(PROMPT, Array.from(PROMPT, (_, k) => typeAt(k)), O(3) + 16, 0.3, 2),
  { at: O(3) + 16 + CH.send, name: "click", volume: 0.26 },
  { at: O(3) + 16 + CH.pair, name: "pop", volume: 0.16 },
  { at: O(3) + 16 + CH.team, name: "pop", volume: 0.13 },
  // wall + lockup
  { at: OUT + 4, name: "whoosh", volume: 0.22 },
  { at: OUT + 112, name: "impact", volume: 0.22 },
];
const musicVol = (f: number) => interpolate(f, [0, 12, REEL_LEN - 50, REEL_LEN], [0, 0.55, 0.55, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export const Reel: React.FC = () => (
  <AbsoluteFill>
    <StyleCatalog items={ITEMS} fonts={FONTS} header={<Header />} Intro={Intro} Lockup={Lockup} />
    <Audio src={staticFile("music/bgm.wav")} volume={musicVol} />
    <SoundCues cues={CUES} />
  </AbsoluteFill>
);
export { CATALOG };
