// 演示期：两拍、约 10 秒。只用代码画面（基础档），用来检查引擎、渲染和质检是否装好。
import { el } from "../../cine/engine/util.js";
import { TH, bg, keyword, counter, foot, foots, chapter, stamp } from "../../cine/engine/know.js";

const TM = TH.starfield;
export const COLD = 0;
export const TAIL = 1.5;
export const meta = { title: "演示", n: "demo" };
export let hits = [], blur = [], clips = [], music = [];
export const sfx = [], sections = [];

export async function build(ctx) {
  const N = ctx.narr, T = (s) => N.t(s), END = N.total;
  const shots = [];
  const add = (from, to, b, r) => shots.push({ from, to, build: b, render: r });
  sections.push({ t: 0, t_to: END + TAIL, level: 0 });
  sfx.push({ t: T("B01.ten"), type: "tick" }, { t: T("B02.fifty"), type: "slam" });
  hits.push(T("B02.fifty"));

  add(0, END + TAIL, (root) => {
    const s = el(root, "shot");
    const ch = chapter(s, { n: 1, cn: "立木", en: "THE POLE", theme: TM });
    const c = counter(s, { y: 380, label: "赏金", suffix: " 金", color: TM.accent });
    const k = keyword(s, "终于有人扛了", { y: 640, color: TM.ink });
    const st = stamp(s, "五倍", { x: 1500, y: 260, size: 120 });
    const f = foot(s);
    return { s, ch, c, k, st, f };
  }, (t, u) => {
    bg(ctx, TM);
    u.ch.update(t, 0.2);
    u.c.update(t, [[T("B01.ten") - 0.3, 0], [T("B01.ten") + 0.3, 10], [T("B02.fifty") - 0.2, 10], [T("B02.fifty") + 0.4, 50]]);
    u.st.update(t, T("B02.fifty") + 0.3);
    u.k.update(t, T("B02") + 1.2);
    foots(u.f, t, [[0, END + TAIL, "演示：《史记·商君列传》"]]);
  });
  return shots;
}
