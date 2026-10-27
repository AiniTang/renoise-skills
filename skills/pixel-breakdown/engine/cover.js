// Pixel Breakdown 3:4 cover, loaded after engine.js (page.html?cover). Uses the engine's font, palette and footage loader.
'use strict';
// ---------- 3:4 cover (1080x1440): flat colour + light burst, one focus, two big lines, a small logo | episode line
window.renderCover = async function () {
  const cvr = EP.cover, CW = 270, CH = 360, PAL = { orange: ['#e0702b', '#ea8442', '#c45f22', '#6e3311'], blue: ['#2c5fb8', '#3670c8', '#23509f', '#18306a'], teal: ['#2a8a86', '#35a09a', '#226f6c', '#134443'], purple: ['#5a3c9e', '#6849ad', '#4a3086', '#271a4a'], red: ['#c8402f', '#d8553f', '#a8321f', '#6e1d12'], ink: ['#26232a', '#34313a', '#1b191f', '#0b0a0d'] };
  const [BGc, RAY, DEEP, SHD] = PAL[cvr.bg] || PAL.blue, OUT = document.getElementById('cover'), G = OUT.getContext('2d'), [pc, P] = mk(CW, CH), [tc, T] = mk(CW, CH);
  rect(P, 0, 0, CW, CH, BGc); const [bx, by] = cvr.burst || [135, 262];
  for (let k = 0; k < 20; k += 2) { const a0 = k / 20 * Math.PI * 2, a1 = a0 + Math.PI / 20; poly(P, [[bx, by], [bx + Math.cos(a0) * 600, by + Math.sin(a0) * 600], [bx + Math.cos(a1) * 600, by + Math.sin(a1) * 600]], RAY); }
  for (let y = 0; y < CH; y++) for (let x = 0; x < CW; x++) { const e = Math.min(x, CW - 1 - x, y, CH - 1 - y); if (e < 12 && ((x + y) & 1) === 0 && e < 5 + ((x * 7 + y * 13) % 7)) rect(P, x, y, 1, 1, DEEP); }
  const f = cvr.focus || {}, cards = [];
  if (f.kind === 'pair') { cards.push({ ...f.left, x: 26, y: 184, w: 90, h: 160 }, { ...f.right, x: 150, y: 170, w: 100, h: 178, hot: true }); }
  else if (f.kind === 'grid') { const n = f.items.length, cols = f.cols || Math.ceil(Math.sqrt(n)), cell = f.cell || R(176 / cols) - 4; f.items.forEach((g, j) => cards.push({ ...g, x: R(135 - (cols * (cell + 4) - 4) / 2) + (j % cols) * (cell + 4), y: 172 + Math.floor(j / cols) * (cell + 4), w: cell, h: cell, square: true })); }
  else cards.push({ ...f, x: 70, y: 170, w: 130, h: 176, hot: true });
  for (const c of cards) { const b = c.hot ? 4 : 3; rect(P, c.x - b + 5, c.y - b + 5, c.w + 2 * b, c.h + 2 * b, SHD); rect(P, c.x - b, c.y - b, c.w + 2 * b, c.h + 2 * b, c.hot ? '#ffd23f' : '#fff8ec'); rect(P, c.x - 1, c.y - 1, c.w + 2, c.h + 2, '#121633'); }
  G.imageSmoothingEnabled = false; G.drawImage(pc, 0, 0, CW * 4, CH * 4);
  for (const c of cards) {                                        // footage frames; pixel: true turns a real photo into pixel art on the grid
    let src; if (c.media) { src = VIDS[c.media] || placeholder(c.media); await seekTo(src, c.t || 1); } else src = IMG[c.image]; if (!src) continue;
    const sw = src.videoWidth || src.width, sh = src.videoHeight || src.height, a = c.w / c.h; let cw, ch; if (c.square) { cw = ch = Math.min(sw, sh) * (c.side || .86); } else if (sw / sh > a) { ch = sh; cw = sh * a; } else { cw = sw; ch = sw / a; } cw /= (c.zoom || 1); ch /= (c.zoom || 1);
    const cx = clamp(sw * (c.fx ?? .5) - cw / 2, 0, sw - cw), cy = clamp(sh * (c.fy ?? .5) - ch / 2, 0, sh - ch);
    if (c.pixel) { const [qc, q] = mk(c.w, c.h); q.imageSmoothingEnabled = true; q.imageSmoothingQuality = 'high'; q.drawImage(src, cx, cy, cw, ch, 0, 0, c.w, c.h); const id = q.getImageData(0, 0, c.w, c.h), d = id.data; for (let i = 0; i < d.length; i += 4) for (let k = 0; k < 3; k++) d[i + k] = R(d[i + k] / 36) * 36; q.putImageData(id, 0, 0); G.imageSmoothingEnabled = false; G.drawImage(qc, c.x * 4, c.y * 4, c.w * 4, c.h * 4); }
    else { G.imageSmoothingEnabled = true; G.imageSmoothingQuality = 'high'; G.drawImage(src, cx, cy, cw, ch, c.x * 4, c.y * 4, c.w * 4, c.h * 4); G.imageSmoothingEnabled = false; }
  }
  for (const c of cards) if (c.tag) { const w = tw(c.tag) + 10, x = R(c.x + c.w / 2 - w / 2), y = c.y + c.h - 10; rect(T, x - 1, y - 1, w + 2, 17, '#121633'); rect(T, x, y, w, 15, c.hot ? '#ffd23f' : '#fff8ec'); drawStr(T, c.tag, x + 5, y + 1, '#121633', 1); }
  if (f.kind === 'pair') { const pts = [[0, -5], [12, -5], [12, -11], [24, 0], [12, 11], [12, 5], [0, 5]], ax = 122, ay = 262; poly(T, pts.map(([u, v]) => [ax + u - 1, ay + v + 2]), '#121633'); poly(T, pts.map(([u, v]) => [ax + u, ay + v]), '#ffd23f'); }
  (cvr.lines || []).forEach(([s_, k, sc], j) => headline(T, s_, 135, j ? 60 : -4, k || (j ? '#ffd23f' : '#fff8ec'), Math.min(sc || 5, fit(s_, 250, sc || 5))));
  const lg = IMG.logo, lf = lg ? Math.min(1, 22 / lg.height, 100 / lg.width) : 1, ep = cvr.badge || '', ew = tw(ep, 2), LW = lg ? lg.width * lf : tw((EP.brand || {}).name || '', 2), gap = ep ? 16 : 0, bw = R(LW + gap + ew), bx0 = R(135 - bw / 2), by0 = 134;
  if (ep && (lg || (EP.brand || {}).name)) { const dvx = R(bx0 + LW + gap / 2); rect(T, dvx - 2, by0 + 3, 4, 20, '#121633'); rect(T, dvx - 1, by0 + 4, 2, 18, '#fff8ec'); }
  if (ep) headline(T, ep, bx0 + LW + gap + ew / 2, by0 - 3, '#ff9a3c', 2, { ow: 2, sh: 2 });
  if (!lg && (EP.brand || {}).name) headline(T, EP.brand.name, bx0 + LW / 2, by0 - 3, '#fff8ec', 2, { ow: 2, sh: 2 });   // a text brand reads in white; a logo stays as supplied
  G.drawImage(tc, 0, 0, CW * 4, CH * 4);
  if (lg) { const i = (EP.brand || {}).tint ? tinted('logo', EP.brand.tint) : lg; G.imageSmoothingEnabled = lf < 1; G.drawImage(i, R(bx0 * 4), R((by0 + (26 - i.height * lf) / 2) * 4), R(i.width * lf * 4), R(i.height * lf * 4)); G.imageSmoothingEnabled = false; }
};
