// 第 __ID__ 期 · __TITLE__（母版 __TPL__）
// cine 引擎契约（references/16-cine.md）：镜头 { from, to, build(root), render(t, u) }，render 只看绝对时间 t，不依赖上一帧。
// 知识片组件在 ../../cine/engine/know.js（references/07-kit.md），资源一律用 A("img/xx.jpg") 取路径。
import { clamp, lerp, inv, eOutCubic, eInOutCubic, el, css } from "../../cine/engine/util.js";
import { appear, slam } from "../../cine/engine/ui.js";
import { TH, bg, layers, plate, vclip, keyword, counter, foot, foots, choice, seriesCard, vquote, trail, spread, bars, chapter, ask } from "../../cine/engine/know.js";

const A = (f) => new URL(`./assets/${f}`, import.meta.url).href;
const P = (f) => decodeURIComponent(new URL(`./assets/${f}`, import.meta.url).pathname).slice(1);   // music 条目：相对工作区的路径
const TM = TH.starfield;                                                   // 视觉系统：starfield / gufeng / darkgold / paper / pixel

export const COLD = 0;                     // 不拼外部冷开场
export const TAIL = 2.5;                   // 旁白结束后停 2.5 秒（尾卡）
export const meta = { title: "__TITLE__", n: "__ID__" };
export let hits = [], blur = [], clips = [], music = [];
export const sfx = [], sections = [];

export async function build(ctx) {
  const N = ctx.narr, T = (s) => N.t(s), END = N.total;
  const shots = [];
  const add = (from, to, b, r) => shots.push({ from, to, build: b, render: r });
  const cue = (t, type, o = {}) => sfx.push({ t, type, ...o });

  // 默认 BGM：cine/tools/fit_bgm.py --lesson 按片长裁好放在 assets/audio/bgm.wav（不放也行，finish.py 会自动补；音量由 bgm_mix.py 按人声校准）
  music.push({ src: P("audio/bgm.wav"), from: 0, at: 0, dur: END + TAIL, gain_curve: [[0, -11], [END, -11], [END + TAIL, -8]], fade_in: 0.3, fade_out: 1.8 });
  // 单个音效（Renoise 生成的短音效）：music.push({ src: P("audio/sfx_bell.wav"), from: 0, at: T("B07.reveal"), dur: 3, gain: -8 });
  sections.push({ t: 0, t_to: END + 2.5, level: 0 });

  // ── B01 冷开场 ──
  add(0, T("B03"), (root) => {
    const s = el(root, "shot");
    const p = plate(s, { src: A("img/a01.jpg") });
    const q = ask(s, "这里写开头那个问题", { accent: TM.accent });
    const f = foot(s);
    return { s, p, q, f };
  }, (t, u) => {
    bg(ctx, TM);
    u.p.update(t, 0, T("B03"), { from: [1.02, 0, 0], to: [1.12, -30, 0] });
    u.q.update(t, T("B01") + 0.2, T("B02"));
    foots(u.f, t, [[T("B01"), T("B02"), "出处：……"]]);
  });

  // ── 尾卡 ──
  add(END, END + TAIL, (root) => {
    const s = el(root, "shot");
    const k = keyword(s, "__TITLE__", { y: 440, size: 96, color: TM.ink, sub: "__SERIES__", subColor: TM.dim });
    return { s, k };
  }, (t, u) => { bg(ctx, TM); u.k.update(t, END + 0.1); });

  return shots;
}
