import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile } from "remotion";
import { keyCues, SoundCues, type Cue } from "../cinematic/sfx";
import { CH, PROMPT, typeAt } from "../youware-ladder/YouWareChain";
import { CATALOG, catalogLength, StyleCatalog, type CatalogItem } from "../cinematic/catalog";
import { step } from "../cinematic/spring";
import { FONTS, ITEMS as P0 } from "./Reel";
import { PIXEL_CUES } from "./PixelDemo";

/**
 * YouWare · 十五种商用风格 — the full style catalogue (~175 s). Three acts: paper & craft → design & motion →
 * dimension & retro. Every sample is pre-rendered (public/samples/*.mp4, 330 frames).
 * Music: the library track (base.wav, bar-aligned repeat) for slots 01–12, code-synthesised retro beds for 13–15,
 * then the song's own last bars (ending.wav) under the wall and lockup.
 */
const p0 = (no: string) => P0.find((i) => i.en === no)!;

const ITEMS15_RAW: CatalogItem[] = [
  {
    no: "01", zh: "逐帧手绘", en: "FRAME-BY-FRAME DOODLE",
    desc: ["线条一拍二地抖动，像铅笔在纸上呼吸；", "关键姿势逐帧替换：挤压、拉伸、眨眼；", "蜡笔排线上色，再交给手写标语。"],
    tags: ["一拍二", "关键帧替换", "蜡笔排线"], work: "Doodle day", tint: "#D9A27E", accent: "#F36440", video: "samples/hand.mp4",
  },
  {
    no: "02", zh: "线条艺术", en: "ONE-LINE DRAWING",
    desc: ["一根墨线贯穿全片：", "气泡、网站、幻灯片、报告；", "线条是答案，填色才是成果。"],
    tags: ["路径描线", "镜头跟笔", "错版填色"], work: "One line", tint: "#BFAF90", accent: "#F36440", video: "samples/line.mp4",
  },
  { ...p0("STICKER EXPLAINER"), no: "03" },
  {
    no: "04", zh: "拼贴风", en: "COLLAGE",
    desc: ["牛皮纸上撕纸、胶带、网点印刷，", "四张真实作品剪下来一拍二地贴上，", "盖章 DONE，勒索信字母拼出品牌。"],
    tags: ["真网点阈值", "撕纸边", "定格抖动"], work: "YouWare scrapbook", tint: "#B89468", accent: "#E0503F", video: "samples/collage.mp4",
  },
  {
    no: "05", zh: "扁平插画", en: "FLAT ILLUSTRATION",
    desc: ["用品牌自己的插画语言：", "侧脸头像两两叠色，坐成一间工作室；", "访客一句话，AI 专家把成果钉上墙。"],
    tags: ["品牌头像", "正片叠底", "SVG 场景"], work: "YouWare studio", tint: "#D8A57E", accent: "#ADC8E6", video: "samples/flat.mp4",
  },
  {
    no: "06", zh: "包豪斯海报", en: "BAUHAUS POSTER",
    desc: ["圆、方、三角与三原色的编舞，", "拆成四格讲四种工作，", "再用四种原色把标志拼回来。"],
    tags: ["网格排版", "几何原形", "Unbounded"], work: "Primary geometry", tint: "#C9962F", accent: "#E0503F", video: "samples/bauhaus.mp4",
  },
  { ...p0("SHAPE MORPH"), no: "07" },
  { ...p0("VARIETY CAPTIONS"), no: "08" },
  {
    no: "09", zh: "液态流动", en: "GLOSSY LIQUID",
    desc: ["四滴品牌色落下、回弹、融合，", "在镜面地板上摊开成一汪，", "再升起成液态的 YouWare 字标。"],
    tags: ["SVG 光照滤镜", "元球融合", "镜面倒影"], work: "One pour", tint: "#D9A58E", accent: "#FFB23F", video: "samples/liquid.mp4",
  },
  {
    no: "10", zh: "弥散玻璃", en: "MESH GRADIENT · GLASS",
    desc: ["品牌色弥散光斑缓慢流动，", "真实背景模糊的磨砂卡片从输入框展开，", "收成一张清单，落下玻璃标志。"],
    tags: ["backdrop-filter", "弥散光斑", "颗粒防色带"], work: "Glass desk", tint: "#7A5FC4", accent: "#C98BE8", video: "samples/glass.mp4",
  },
  { ...p0("ISOMETRIC"), no: "11" },
  {
    no: "12", zh: "3D 软萌字", en: "SOFT 3D · PIN ART",
    desc: ["小球落进两千根胶囊针阵，", "涟漪推出 YouWare 标志的针雕浮雕，", "再落下糖果质感的软萌字母。"],
    tags: ["Three.js 实例化", "物理弹跳", "胶囊针阵"], work: "Pin-art YouWare", tint: "#A493DA", accent: "#F29BB5", video: "samples/soft.mp4",
  },
  {
    no: "13", zh: "赛博 HUD", en: "CYBER HUD · FUI",
    desc: ["线框地球、雷达扫描、滚动数据列，", "四个任务在控制台里依次完成，", "准星落下：成果已就绪。"],
    tags: ["Three.js 线框", "辉光", "数据读数"], work: "Mission control", tint: "#1B6A86", accent: "#3FE0FF", video: "samples/fui.mp4",
  },
  {
    no: "14", zh: "像素风", en: "PIXEL ART",
    desc: ["320×180 真低分辨率画布放大，", "YouWare 头像跑酷，顶开四个问号砖；", "调色板轮换的天空，抖动淡入。"],
    tags: ["最近邻放大", "调色板轮换", "芯片音效"], work: "YouWare Quest", tint: "#5D4592", accent: "#FFD15C", video: "samples/pixel.mp4",
  },
  {
    no: "15", zh: "复古合成波", en: "RETRO SYNTHWAVE",
    desc: ["霓虹网格公路开向条纹落日，", "四个出口路牌呼啸而过，", "铬字 YOUWARE 与 VHS 画面收尾。"],
    tags: ["透视投影", "条纹太阳", "VHS 扫描线"], work: "YouWare Drive", tint: "#A03884", accent: "#FF6AD5", video: "samples/synthwave.mp4",
  },
];

/** Wall proxies: public/samples/wall/<name>.mp4 (640×360, -g 6). */
export const ITEMS15: CatalogItem[] = ITEMS15_RAW.map((it) => ({ ...it, thumb: it.video?.replace("samples/", "samples/wall/") }));

export const REEL15_LEN = catalogLength(ITEMS15.length);
const CREAM = "#F4EEE2";
const N = ITEMS15.length;

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
    <span style={{ fontFamily: FONTS.sansZh, fontSize: 18, color: "rgba(244,238,226,0.55)", letterSpacing: "0.06em" }}>十五种商用风格 · 全部代码渲染</span>
  </div>
);

const rise = (t: number, at: number) => step(Math.max(0, (t - at) / 30), { w: 2 * Math.PI * 2.2, z: 0.8 });

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
        一个 YouWare，十五种商用风格
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 682, textAlign: "center", fontFamily: FONTS.sans, fontWeight: 700, fontSize: 17, letterSpacing: "0.32em", color: "rgba(244,238,226,0.6)", opacity: rise(t, 52) }}>
        ONE YOUWARE · FIFTEEN STYLES · RENDERED IN CODE
      </div>
    </AbsoluteFill>
  );
};

const ACTS = ["逐帧手绘 · 线条艺术 · 贴纸风 · 拼贴风 · 扁平插画", "包豪斯 · 形变 · 综艺花字 · 液态 · 弥散玻璃", "等轴 2.5D · 3D 软萌字 · 赛博 HUD · 像素 · 合成波"];
const Lockup: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill>
    <div style={{ position: "absolute", left: 960 - 260, top: 330, width: 520, height: 150, transform: `translateY(${(1 - rise(t, 8)) * 30}px)`, opacity: rise(t, 8), ...mask("lockup.svg") }} />
    <div style={{ position: "absolute", left: 0, right: 0, top: 522, textAlign: "center", fontFamily: FONTS.display, fontWeight: 400, fontSize: 46, color: CREAM, opacity: rise(t, 18), letterSpacing: "-0.01em" }}>
      From answers to outcomes.
    </div>
    {ACTS.map((a, i) => (
      <div key={i} style={{ position: "absolute", left: 0, right: 0, top: 612 + i * 38, textAlign: "center", fontFamily: FONTS.sansZh, fontSize: 19, color: "rgba(244,238,226,0.55)", letterSpacing: "0.12em", opacity: rise(t, 28 + i * 5) }}>
        {a}
      </div>
    ))}
  </AbsoluteFill>
);

/* ---------------------------------------------------------------- sound */
const O = (i: number) => CATALOG.intro + i * CATALOG.slot;
const OUT = O(N);
const at = (i: number, list: [number, string, number][]): Cue[] => list.map(([f, name, volume]) => ({ at: O(i) + f, name, volume }));
const GLASS_PROMPT = "Turn my notes into a launch kit";

const CUES: Cue[] = [
  { at: 16, name: "tap", volume: 0.42 },
  { at: 30, name: "tap", volume: 0.28 },
  { at: 38, name: "tap", volume: 0.16 },
  { at: 36, name: "swish-1", volume: 0.14 },
  ...ITEMS15.flatMap((_, i) => [
    { at: O(i) + 2, name: "pop", volume: 0.16 },
    { at: O(i) + 300, name: "swish-2", volume: 0.14 },
  ]),
  // 01 hand-drawn
  ...at(0, [[12, "pop", 0.22], [18, "tap", 0.2], [66, "ding", 0.16], [84, "swish-3", 0.12], [110, "swish-3", 0.12], [136, "swish-3", 0.12], [162, "swish-3", 0.12], [196, "whoosh", 0.14], [214, "pop", 0.2], [222, "tap", 0.18], [244, "swish-2", 0.14], [256, "ding", 0.14]]),
  // 02 line
  ...at(1, [[18, "swish-1", 0.1], [50, "pop", 0.12], [72, "swish-1", 0.1], [112, "pop", 0.12], [126, "swish-1", 0.1], [164, "pop", 0.12], [178, "swish-1", 0.1], [214, "pop", 0.12], [228, "swish-2", 0.12], [256, "ding", 0.14]]),
  // 03 stickers (P0 timings)
  ...[30, 44, 70, 96, 122].map((a, k) => ({ at: O(2) + a, name: k % 2 ? "paper-place-2" : "paper-place-1", volume: 0.3 })),
  ...[0, 1, 2, 3, 4].map((k) => ({ at: O(2) + 160 + k * 7, name: "pop", volume: 0.1 })),
  { at: O(2) + 232, name: "slam-2", volume: 0.24 },
  // 04 collage
  ...at(3, [[8, "paper-place-1", 0.3], [40, "paper-place-2", 0.3], [70, "paper-place-1", 0.3], [100, "paper-place-2", 0.3], [130, "paper-place-1", 0.3], [178, "slam-3", 0.16], [186, "slam-3", 0.14], [194, "slam-3", 0.14], [202, "slam-3", 0.14], [262, "paper-place-2", 0.3]]),
  ...Array.from({ length: 7 }, (_, k) => ({ at: O(3) + 222 + k * 4, name: "tap", volume: 0.14 })),
  // 05 flat
  ...at(4, [[50, "pop", 0.18], [64, "pop", 0.14], [72, "pop", 0.14], [80, "pop", 0.14], [88, "pop", 0.14], [112, "swish-1", 0.1], [138, "tap", 0.16], [158, "tap", 0.16], [178, "tap", 0.16], [198, "tap", 0.16], [252, "swish-2", 0.14]]),
  // 06 bauhaus
  ...at(5, [[4, "swish-2", 0.14], [20, "whoosh", 0.12], [34, "slam-1", 0.14], [40, "tap", 0.16], [86, "swish-3", 0.12], [100, "pop", 0.12], [112, "pop", 0.12], [124, "pop", 0.12], [136, "pop", 0.12], [192, "whoosh", 0.12], [222, "tap", 0.14], [236, "tap", 0.14], [246, "tap", 0.14]]),
  // 07 morph (chain starts 16 frames into its sample)
  ...keyCues(PROMPT, Array.from(PROMPT, (_, k) => typeAt(k)), O(6) + 16, 0.28, 2),
  { at: O(6) + 16 + CH.send, name: "click", volume: 0.24 },
  { at: O(6) + 16 + CH.pair, name: "pop", volume: 0.14 },
  { at: O(6) + 16 + CH.team, name: "pop", volume: 0.12 },
  // 08 variety
  ...[12, 94, 174, 184].map((a, k) => ({ at: O(7) + a, name: ["pop", "whoosh", "slam-1", "impact"][k], volume: [0.3, 0.22, 0.26, 0.26][k] })),
  { at: O(7) + 100, name: "click", volume: 0.16 },
  { at: O(7) + 236, name: "done", volume: 0.2 },
  // 09 liquid
  ...at(8, [[56, "pop", 0.2], [68, "pop", 0.2], [80, "pop", 0.2], [92, "pop", 0.2], [132, "swish-1", 0.1], [206, "swish-3", 0.12], [230, "whoosh", 0.1], [266, "ding", 0.14]]),
  // 10 glass
  ...keyCues(GLASS_PROMPT, Array.from(GLASS_PROMPT, (_, k) => 26 + (k / GLASS_PROMPT.length) * 36), O(9), 0.26, 2),
  ...at(9, [[66, "click", 0.24], [84, "pop", 0.12], [91, "pop", 0.12], [98, "pop", 0.12], [105, "pop", 0.12], [150, "swish-1", 0.1], [198, "swish-2", 0.12], [214, "tap", 0.12], [220, "tap", 0.12], [226, "tap", 0.12], [232, "tap", 0.12], [250, "ding", 0.14]]),
  // 11 iso
  ...at(10, [[14, "click", 0.22], [24, "swish-3", 0.16], [58, "pop", 0.16], [88, "pop", 0.16], [118, "pop", 0.16], [148, "pop", 0.16], [196, "whoosh", 0.16], [232, "impact", 0.2]]),
  // 12 soft 3D
  ...at(11, [[24, "tap", 0.34], [24, "pop", 0.18], [40, "tap", 0.16], [50, "tap", 0.1], [28, "swish-3", 0.12], [60, "whoosh", 0.08], [262, "ding", 0.14]]),
  ...Array.from({ length: 7 }, (_, k) => ({ at: O(11) + 184 + k * 7, name: "pop", volume: 0.14 })),
  { at: O(11) + 256, name: "tap", volume: 0.18 },
  // 13 HUD
  ...at(12, [[40, "click", 0.14], [92, "click", 0.14], [144, "click", 0.14], [196, "click", 0.14], [250, "ding", 0.14], [272, "done", 0.16]]),
  // 14 pixel (chiptune effects)
  ...PIXEL_CUES.jumps.map((f) => ({ at: O(13) + f, name: "chip-jump", volume: 0.28 })),
  ...PIXEL_CUES.hits.map((f) => ({ at: O(13) + f, name: "chip-bump", volume: 0.3 })),
  ...PIXEL_CUES.coins.map((f) => ({ at: O(13) + f, name: "chip-coin", volume: 0.24 })),
  { at: O(13) + PIXEL_CUES.flag, name: "chip-fanfare", volume: 0.3 },
  // 15 synthwave
  ...at(14, [[50, "whoosh", 0.12], [95, "whoosh", 0.12], [140, "whoosh", 0.12], [185, "whoosh", 0.12], [228, "slam-1", 0.14], [248, "swish-2", 0.12]]),
  // wall + lockup
  { at: OUT + 4, name: "whoosh", volume: 0.2 },
  { at: OUT + 126, name: "impact", volume: 0.12 }, // doubles the music's final hit (HIT_AT)
];

/* music: base (slots 01–12) → retro beds (13–15) → the song's own ending under wall + lockup */
const RETRO = O(12); // HUD slot start
const END_LEN = 6.488; // ending.wav, s: 2 bars of groove + the final hit + its decay (build_audio.py)
const HIT_OFFSET = 4.138; // s from the start of ending.wav to the final hit
const HIT_AT = OUT + 108 + 18; // the hit lands as the slogan rises in the lockup
const END_AT = HIT_AT - Math.round(HIT_OFFSET * 30); // = just as the synthwave bed fades and the wall opens
const MUSIC = 0.5;
const baseVol = (f: number) => interpolate(f, [0, 12, RETRO - 6, RETRO + 18], [0, MUSIC, MUSIC, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const bed = (v: number) => (f: number) => interpolate(f, [0, 18, CATALOG.slot - 2, CATALOG.slot + 18], [0, v, v, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const endVol = (f: number) => interpolate(f, [0, 14], [0, MUSIC], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export const Reel15: React.FC = () => (
  <AbsoluteFill>
    <StyleCatalog items={ITEMS15} fonts={FONTS} header={<Header />} Intro={Intro} Lockup={Lockup} />
    <Sequence from={0} durationInFrames={RETRO + 24} layout="none">
      <Audio src={staticFile("music/base.wav")} volume={baseVol} />
    </Sequence>
    {["retro-hud", "retro-chip", "retro-synth"].map((b, k) => (
      <Sequence key={b} from={O(12 + k) - 6} durationInFrames={CATALOG.slot + 24} layout="none">
        <Audio src={staticFile(`music/${b}.wav`)} volume={bed([0.5, 0.42, 0.55][k])} />
      </Sequence>
    ))}
    <Sequence from={END_AT} layout="none">
      <Audio src={staticFile("music/ending.wav")} volume={endVol} />
    </Sequence>
    <SoundCues cues={CUES} />
  </AbsoluteFill>
);
