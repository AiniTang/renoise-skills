// Pixel Breakdown engine. Every frame is a pure function of time: window.render(frame).
// Layers: #c = 480x270 pixel canvas upscaled x4, with real footage composited at full resolution;
// #ui = the simulated chat (ui.js); #top = pixel callouts, step badges and the 2x subtitle overlay.
// All content comes from window.EP (episode.js) and window.TL (timeline.js). Nothing here is episode-specific.
'use strict';
const W = 480, H = 270, S = 4, EP = window.EP, TL = window.TL, FPS = TL.fps, A = TL.a, L = n => TL.lines[n - 1];
const R = Math.round, clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v)), seg = (t, a, b) => clamp((t - a) / (b - a));
const eo = p => 1 - Math.pow(1 - p, 3), eio = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
const back = p => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };
const hash = n => { n = (n ^ 61) ^ (n >>> 16); n = n + (n << 3); n = n ^ (n >>> 4); n = Math.imul(n, 0x27d4eb2d); n = n ^ (n >>> 15); return (n >>> 0) / 4294967296; };
const mk = (w = W, h = H) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d', { willReadFrequently: true }); x.imageSmoothingEnabled = false; return [c, x]; };
const [cv, X] = mk();

// ---------- time expressions: 3.2 | "L4" (line 4 start) | "L4e" (line 4 end) | "@hit" (anchor) | any of these "+0.3" / "-0.2"
function tt(x) {
  if (typeof x === 'number') return x;
  const m = /^\s*(?:L(\d+)(e?)|@([\w-]+)|(-?\d+(?:\.\d+)?))\s*(?:([+-])\s*(\d+(?:\.\d+)?))?\s*$/.exec(String(x));
  if (!m) throw new Error('bad time expression: ' + x);
  let t = m[1] ? (L(+m[1]) ? L(+m[1])[m[2] ? 'e' : 's'] : undefined) : m[3] ? A[m[3]] : +m[4];
  if (t === undefined) throw new Error('unknown line or anchor in time expression: ' + x);
  return t + (m[5] ? (m[5] === '-' ? -1 : 1) * +m[6] : 0);
}
const ttOr = (x, d) => x === undefined || x === null ? d : tt(x);

// ---------- palette (named colours can be used anywhere a colour is expected)
const C = { ink: '#34313a', ink2: '#5d5862', paper: '#ece2cd', paper2: '#e2d5bb', grid: '#ddcfb3', white: '#f6f1e6', black: '#0e0d12',
  accent: EP.accent || '#e0702b', accent2: '#f2a868', red: '#c2463c', red2: '#e08b7f', green: '#5d8c58', green2: '#8fb886', yellow: '#e2b04a',
  blue: '#5d7a96', sky: '#9fc3d9', night: '#16151b', night2: '#1e1d24', dark: '#1d1c22', dark2: '#2a2930', dim: '#9a9184', mint: '#9fe0a8',
  muted: '#8d8a93', soft: '#cfc8bb', cream: '#fff1e2', sub: '#ff9a3c' };
const col = k => (k && C[k]) || k || C.ink;
const rgb = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16));

// ---------- integer pixel primitives
function rect(c, x, y, w, h, k) { c.fillStyle = col(k); c.fillRect(R(x), R(y), R(w), R(h)); }
function line(c, x0, y0, x1, y1, k, dash = null) {
  x0 = R(x0); y0 = R(y0); x1 = R(x1); y1 = R(y1); c.fillStyle = col(k);
  let dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1, err = dx + dy, i = 0;
  for (let n = 0; n < 4000; n++) {
    if (!dash || i % (dash[0] + dash[1]) < dash[0]) c.fillRect(x0, y0, 1, 1);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err; if (e2 >= dy) { err += dy; x0 += sx; } if (e2 <= dx) { err += dx; y0 += sy; } i++;
  }
}
function disc(c, cx, cy, r, k) { c.fillStyle = col(k); cx = R(cx); cy = R(cy); r = R(r); for (let y = -r; y <= r; y++) { const w = Math.floor(Math.sqrt(r * r - y * y) + .35); c.fillRect(cx - w, cy + y, 2 * w + 1, 1); } }
function ellipse(c, cx, cy, rx, ry, k) { c.fillStyle = col(k); cx = R(cx); cy = R(cy); rx = R(rx); ry = Math.max(1, R(ry)); for (let y = -ry; y <= ry; y++) { const w = Math.floor(rx * Math.sqrt(1 - (y * y) / (ry * ry)) + .35); c.fillRect(cx - w, cy + y, 2 * w + 1, 1); } }
function ring(c, cx, cy, r, k) {
  c.fillStyle = col(k); cx = R(cx); cy = R(cy); r = R(r); let x = r, y = 0, e = 1 - r;
  while (x >= y) { for (const [a, b] of [[x, y], [y, x], [-y, x], [-x, y], [-x, -y], [-y, -x], [y, -x], [x, -y]]) c.fillRect(cx + a, cy + b, 1, 1); y++; if (e < 0) e += 2 * y + 1; else { x--; e += 2 * (y - x) + 1; } }
}
function arc(c, cx, cy, r, a0, a1, k, dash = null) {
  c.fillStyle = col(k); const n = Math.max(2, Math.ceil(Math.abs(a1 - a0) * r * 1.5)); let last = '', i = 0;
  for (let j = 0; j <= n; j++) { const a = a0 + (a1 - a0) * j / n, x = R(cx + Math.cos(a) * r), y = R(cy + Math.sin(a) * r), key = x + ',' + y; if (key === last) continue; last = key; if (!dash || i % (dash[0] + dash[1]) < dash[0]) c.fillRect(x, y, 1, 1); i++; }
}
function poly(c, pts, k) {
  c.fillStyle = col(k); const y0 = Math.max(0, Math.floor(Math.min(...pts.map(p => p[1])))), y1 = Math.min(c.canvas.height, Math.ceil(Math.max(...pts.map(p => p[1]))));
  for (let y = y0; y < y1; y++) {
    const yc = y + .5, xs = [];
    for (let i = 0; i < pts.length; i++) { const [ax, ay] = pts[i], [bx, by] = pts[(i + 1) % pts.length]; if ((ay <= yc && by > yc) || (by <= yc && ay > yc)) xs.push(ax + (yc - ay) * (bx - ax) / (by - ay)); }
    xs.sort((a, b) => a - b);
    for (let j = 0; j + 1 < xs.length; j += 2) { const xa = Math.ceil(xs[j] - .5), xb = Math.floor(xs[j + 1] - .5); if (xb >= xa) c.fillRect(xa, y, xb - xa + 1, 1); }
  }
}
function box(c, x, y, w, h, fill, edge) { rect(c, x + 1, y, w - 2, h, edge || fill); rect(c, x, y + 1, w, h - 2, edge || fill); if (edge) rect(c, x + 1, y + 1, w - 2, h - 2, fill); }
function check(c, x, y, k, s = 1) { for (const [a, b] of [[0, 4], [1, 5], [2, 6], [3, 5], [4, 4], [5, 3], [6, 2], [7, 1], [8, 0]]) { rect(c, x + a * s, y + b * s, s, 2 * s, k); } }
function cross(c, x, y, k, n = 8) { for (let i = 0; i < n; i++) { rect(c, x + i, y + i, 2, 2, k); rect(c, x + n - 1 - i, y + i, 2, 2, k); } }
function shade(c, k, a) { c.globalAlpha = clamp(a); rect(c, 0, 0, W, H, k); c.globalAlpha = 1; }
// Bayer dither (translucent pixel fills)
const B8 = [[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25], [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]];
const MASK = {}, TMP = mk(), LAY = mk();
function mask(l) { if (MASK[l]) return MASK[l]; const [c, x] = mk(), id = x.createImageData(W, H); for (let y = 0; y < H; y++) for (let i = 0; i < W; i++) if (B8[y & 7][i & 7] < l) id.data[(y * W + i) * 4 + 3] = 255; x.putImageData(id, 0, 0); return MASK[l] = c; }
function dmix(c, src, p) { const l = R(clamp(p) * 64); if (l <= 0) return; if (l >= 64) return c.drawImage(src, 0, 0); const [tc, tx] = TMP; tx.globalCompositeOperation = 'copy'; tx.drawImage(src, 0, 0); tx.globalCompositeOperation = 'destination-in'; tx.drawImage(mask(l), 0, 0); tx.globalCompositeOperation = 'source-over'; c.drawImage(tc, 0, 0); }
function layer(fn) { const [lc, lx] = LAY; lx.clearRect(0, 0, W, H); fn(lx); return lc; }
const dpoly = (c, pts, k, p) => dmix(c, layer(l => poly(l, pts, k)), p);
const drect = (c, x, y, w, h, k, p) => dmix(c, layer(l => rect(l, x, y, w, h, k)), p);

// ---------- bitmap font (Fusion Pixel 12px from BDF); characters it lacks are rasterised from a system font at 12 px
const F = window.FONT, GC = {}, [fbc, fbx] = mk(32, 32);
function fallback(ch) {
  fbx.clearRect(0, 0, 32, 32); fbx.font = '12px "Noto Sans", "Noto Sans Thai", sans-serif'; fbx.textBaseline = 'alphabetic'; fbx.fillStyle = '#fff';
  const w = Math.max(1, Math.ceil(fbx.measureText(ch).width)); fbx.fillText(ch, 0, F.ascent); const d = fbx.getImageData(0, 0, w, 16).data, rows = [];
  for (let y = 0; y < 16; y++) { let s = ''; for (let x = 0; x < Math.ceil(w / 8) * 8; x += 8) { let b = 0; for (let k = 0; k < 8; k++) if (x + k < w && d[(y * w + x + k) * 4 + 3] > 110) b |= 0x80 >> k; s += b.toString(16).padStart(2, '0'); } rows.push(s); }
  return F.g[ch] = [w + 1, w, 16, 0, F.ascent - 16, rows.join('')];
}
const gdef = ch => F.g[ch] || (ch.charCodeAt(0) < 32 ? F.g[' '] : fallback(ch));
function glyph(ch, k) {
  const key = ch + k; if (GC[key]) return GC[key];
  const [dx, w, h, xo, yo, hex] = gdef(ch), cw = Math.max(1, w), chh = Math.max(1, h);
  const [gc, gx] = mk(cw, chh), id = gx.createImageData(cw, chh), bpr = Math.ceil(w / 8) * 2, [r, g, b] = rgb(col(k));
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (parseInt(hex.substr(y * bpr + ((x >> 3) << 1), 2), 16) & (0x80 >> (x & 7))) { const i = (y * cw + x) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255; }
  }
  gx.putImageData(id, 0, 0); return GC[key] = { c: gc, dx, w, h, xo, yo };
}
const tw = (s, sc = 1) => [...String(s)].reduce((a, ch) => a + gdef(ch)[0], 0) * sc;
function drawStr(c, s, x, y, k, sc = 1, n = Infinity) {
  let cx = x, i = 0;
  for (const ch of String(s)) { if (i++ >= n) break; const g = glyph(ch, k); if (g.w > 0 && g.h > 0) c.drawImage(g.c, cx + g.xo * sc, y + (F.ascent - g.yo - g.h) * sc, g.w * sc, g.h * sc); cx += g.dx * sc; }
}
function text(c, s, x, y, k, o = {}) {                        // y = top of the 16 px line box
  const sc = o.scale || 1, w = tw(s, sc); if (o.align === 'center') x -= w / 2; else if (o.align === 'right') x -= w; x = R(x); y = R(y);
  if (o.outline) for (const [a, b] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) drawStr(c, s, x + a * (o.ow || 1), y + b * (o.ow || 1), o.outline, sc);
  drawStr(c, s, x, y, k, sc); return w;
}
function headline(c, s, cx, y, k, sc, o = {}) {                // thick round outline + hard drop shadow (titles, covers)
  const w = tw(s, sc), x = R(cx - w / 2), ow = o.ow ?? 3, sh = o.sh ?? 4, edge = o.edge || '#121633';
  for (let dy = -ow; dy <= ow + sh; dy++) for (let dx = -ow; dx <= ow; dx++) if (dx * dx + dy * dy <= ow * ow + 1 || (dy > 0 && dx * dx + (dy - sh) * (dy - sh) <= ow * ow + 1)) drawStr(c, s, x + dx, y + dy, edge, sc);
  drawStr(c, s, x, y, k, sc); return w;
}
function fit(s, maxW, sc) { while (sc > 1 && tw(s, sc) > maxW) sc--; return sc; }
function wrap(s, maxW, sc = 1) {                              // word wrap for spaced scripts, character wrap otherwise
  const words = /\s/.test(s) ? s.split(/(\s+)/) : [...s], out = []; let cur = '';
  for (const w of words) { if (cur && tw((cur + w).trimEnd(), sc) > maxW) { out.push(cur.trim()); cur = w.trimStart(); } else cur += w; }
  if (cur.trim()) out.push(cur.trim()); return out;
}

// ---------- images (episode images, host portrait, logo)
const IMG = {}, TINT = {};
function tinted(n, k) { const key = n + k; if (TINT[key]) return TINT[key]; const i = IMG[n], [tc, tx] = mk(i.width, i.height); tx.drawImage(i, 0, 0); tx.globalCompositeOperation = 'source-in'; rect(tx, 0, 0, i.width, i.height, k); return TINT[key] = tc; }
let PAPER, GRID_D;
function prepare() {
  const [pc, px] = mk(); rect(px, 0, 0, W, H, C.paper);
  for (let x = 4; x < W; x += 12) rect(px, x, 0, 1, H, C.grid); for (let y = 6; y < H; y += 12) rect(px, 0, y, W, 1, C.grid);
  for (let i = 0; i < 900; i++) rect(px, R(hash(i * 7 + 1) * W), R(hash(i * 13 + 5) * H), 1, 1, hash(i) < .5 ? C.paper2 : '#f2eadb');
  PAPER = pc; const [gc, gx] = mk(); rect(gx, 0, 0, W, H, C.night);
  for (let x = 6; x < W; x += 12) rect(gx, x, 0, 1, H, C.night2); for (let y = 2; y < H; y += 12) rect(gx, 0, y, W, 1, C.night2); GRID_D = gc;
}
const bg = (c, kind) => kind === 'dark' ? c.drawImage(GRID_D, 0, 0) : kind === 'black' ? rect(c, 0, 0, W, H, C.black) : c.drawImage(PAPER, 0, 0);

// ---------- juice
function dust(c, t, t0, x, y, o = {}) {
  const n = o.n || 14, life = o.life || .45, sp = o.speed || 80, g = o.g ?? 160, dt = t - t0, sd = o.seed || 0;
  if (dt < 0 || dt > life) return;
  for (let i = 0; i < n; i++) {
    const a = (o.a0 ?? 0) + (o.arc ?? Math.PI * 2) * (i + hash(i * 7 + sd) * .8) / n, v = sp * (.45 + hash(i * 13 + sd)), s = dt / life < .5 ? 2 : 1;
    rect(c, x + Math.cos(a) * v * dt, y + Math.sin(a) * v * dt + g * dt * dt / 2, s, s, Array.isArray(o.col) ? o.col[i % o.col.length] : (o.col || C.white));
  }
}
function cracks(c, cx, cy, w, h, p, seed = 1) {
  for (let k = 0; k < 9; k++) {
    const a = k / 9 * Math.PI * 2 + hash(seed + k) * .5, L0 = (50 + hash(seed * 3 + k) * 70) * p; let x = cx + Math.cos(a) * w / 2, y = cy + Math.sin(a) * h / 2;
    for (let s = 0; s < 6; s++) { const j = (hash(seed * 17 + k * 7 + s) - .5) * 1.1, nx = x + Math.cos(a + j) * L0 / 6, ny = y + Math.sin(a + j) * L0 / 6; line(c, x, y, nx, ny, '#5a1d18'); line(c, x + 1, y, nx + 1, ny, '#f2d9d0'); x = nx; y = ny; }
  }
}
function stamp(c, t, t0, txt, k, cx, cy) {                     // slams in big, settles, flash, cracks, dust
  const dt = t - t0; if (dt < 0) return; k = col(k);
  let sc = dt < 1 / 30 ? 6 : dt < 2 / 30 ? 5 : dt < 3 / 30 ? 4 : 3; const sc0 = fit(txt, W - 40, 3); sc = Math.min(sc, sc0 + 3); if (dt >= 3 / 30) sc = sc0;
  const w = tw(txt, sc) + 8 * sc, h = 19 * sc, x = R(cx - w / 2), y = R(cy - h / 2);
  if (dt >= 3 / 30) cracks(c, cx, cy, w, h, eo(seg(t, t0 + .1, t0 + .3)), R(t0 * 10));
  box(c, x, y, w, h, C.paper);
  for (let j = 0; j < 2; j++) { rect(c, x + j, y + j, w - 2 * j, 1, k); rect(c, x + j, y + h - 1 - j, w - 2 * j, 1, k); rect(c, x + j, y + j, 1, h - 2 * j, k); rect(c, x + w - 1 - j, y + j, 1, h - 2 * j, k); }
  text(c, txt, cx, y + 2 * sc, k, { scale: sc, align: 'center' });
  dust(c, t, t0 + .1, cx, cy, { n: 22, speed: 150, col: [C.paper, C.white, k], life: .5, seed: 3 });
  if (dt < 2 / 30) shade(c, C.white, .5);
}
function bigX(c, t, t0, cx, cy, s = 30) {
  const dt = t - t0; if (dt < 0) return; const q = dt < 1 / 30 ? 1.6 : dt < 2 / 30 ? 1.3 : 1, r = s * q, w = 6 * q;
  for (const d of [1, -1]) poly(c, [[cx - r, cy - d * r + w], [cx - r + w, cy - d * r], [cx + r, cy + d * r - w], [cx + r - w, cy + d * r]], '#7a1f19');
  for (const d of [1, -1]) poly(c, [[cx - r + 1, cy - d * r + w - 1], [cx - r + w - 1, cy - d * r + 1], [cx + r - 1, cy + d * r - w + 1], [cx + r - w + 1, cy + d * r - 1]], C.red);
  dust(c, t, t0 + .05, cx, cy, { n: 18, speed: 120, col: [C.red, C.white], seed: R(cx) });
}
function popY(t, t0, d = 14) { const p = back(seg(t, t0, t0 + .25)); return t < t0 ? null : R((1 - clamp(p, 0, 1.2)) * d); }
function chip(c, x, y, label, bgk = 'accent', fg = 'white', align = 'left') { const w = tw(label) + 10; if (align === 'center') x -= w / 2; box(c, R(x), R(y), w, 16, col(bgk), C.ink); text(c, label, R(x) + 5, R(y) - 1, fg); return w; }
function arrow(c, x, y, len, k = 'accent', dir = 1) {
  if (len < 8) return; const P = q => q.map(([u, v]) => [x + dir * u, y + v]);
  poly(c, P([[-1, -3], [len - 8, -3], [len - 8, -8], [len + 2, 0], [len - 8, 8], [len - 8, 3], [-1, 3]]), C.night); poly(c, P([[0, -2], [len - 7, -2], [len - 7, -6], [len, 0], [len - 7, 6], [len - 7, 2], [0, 2]]), k);
}
function win(c, x, y, w, h, title, o = {}) {                   // pixel window chrome; p < 1 pops in, returns true once fully open
  const p = o.p === undefined ? 1 : o.lin ? clamp(o.p) : clamp(back(o.p), 0, 1.12), cw = R(w * p), ch = R(h * p), cx = R(x + (w - cw) / 2), cy = R(y + (h - ch) / 2);
  if (p <= .02) return false;
  c.globalAlpha = .35; rect(c, cx + 3, cy + 4, cw, ch, C.black); c.globalAlpha = 1; rect(c, cx, cy, cw, ch, C.ink); rect(c, cx + 1, cy + 1, cw - 2, ch - 2, o.dark ? C.dark : '#f4eee2');
  if (p < .96) return false;
  rect(c, x + 1, y + 1, w - 2, 15, o.dark ? C.dark2 : '#e2d6bf'); rect(c, x + 1, y + 16, w - 2, 1, C.ink);
  ['#d9695a', '#e2b04a', '#7fae6b'].forEach((k, j) => disc(c, x + 9 + j * 9, y + 8, 2, k));
  if (title) text(c, title, x + w / 2, y - 1, o.dark ? C.soft : C.ink, { align: 'center' }); return true;
}
function phone(c, s) { const { x, y, w, h } = s; rect(c, x - 6, y - 10, w + 12, h + 20, C.ink); rect(c, x - 5, y - 9, w + 10, h + 18, '#2b2a31'); rect(c, x + w / 2 - 9, y - 6, 18, 2, C.night); rect(c, x + w / 2 - 6, y + h + 5, 12, 2, '#3b3a42'); rect(c, x, y, w, h, '#000'); }
function frame(c, s, k = 'white', b = 3) { rect(c, s.x - b + 4, s.y - b + 4, s.w + 2 * b, s.h + 2 * b, C.black); rect(c, s.x - b, s.y - b, s.w + 2 * b, s.h + 2 * b, k); rect(c, s.x - 1, s.y - 1, s.w + 2, s.h + 2, C.ink); }
function outlineBox(c, x, y, w, h, t, k = 'accent') { const blink = Math.floor(t * 6) % 2; for (const [kk, o] of [[C.ink, 0], [k, 1], [blink ? C.accent2 : k, 2]]) { rect(c, x + o, y + o, w - 2 * o, 1, kk); rect(c, x + o, y + h - 1 - o, w - 2 * o, 1, kk); rect(c, x + o, y + o, 1, h - 2 * o, kk); rect(c, x + w - 1 - o, y + o, 1, h - 2 * o, kk); } }
function crtOn(c, p) {
  if (p >= 1) return; const bw = p < .45 ? R(eo(p / .45) * W) : W, bh = p < .45 ? 2 : Math.max(2, R(eo((p - .45) / .55) * H)), x0 = R((W - bw) / 2), y0 = R((H - bh) / 2);
  rect(c, 0, 0, W, y0, '#000'); rect(c, 0, y0 + bh, W, H, '#000'); rect(c, 0, y0, x0, bh, '#000'); rect(c, x0 + bw, y0, W, bh, '#000'); if (p < .45) rect(c, x0, y0, bw, bh, C.white);
}
const CUR = ['X.......', 'XX......', 'XWX.....', 'XWWX....', 'XWWWX...', 'XWWWWX..', 'XWWXXXX.', 'XXX.....'];
function cursor(c, x, y, clickT, t) {
  if (clickT !== undefined && t > clickT && t < clickT + .3) { const r = R(3 + (t - clickT) * 40); ring(c, x, y, r, C.accent); ring(c, x, y, r + 1, C.white); }
  const d = clickT !== undefined && t > clickT && t < clickT + .08 ? 1 : 0; CUR.forEach((r, j) => [...r].forEach((ch, i) => { if (ch !== '.') rect(c, x + i * 2 + d, y + j * 2 + d, 2, 2, ch === 'X' ? C.ink : C.white); }));
}
function padlock(c, x, y, closed = true, k = 'yellow') { const sh = closed ? 0 : 5; rect(c, x + 3, y - sh, 10, 2, C.ink); rect(c, x + 3, y - sh, 2, 8, C.ink); rect(c, x + 11, y - sh + (closed ? 0 : 4), 2, closed ? 8 : 4, C.ink); box(c, x, y + 7, 16, 12, col(k), C.ink); rect(c, x + 7, y + 11, 2, 4, C.ink); }
// ~20x20 procedural icons, drawn at scale s from the top-left corner
const ICON = {
  camera: (c, x, y, s) => { rect(c, x, y + 5 * s, 22 * s, 14 * s, C.ink); rect(c, x + s, y + 6 * s, 20 * s, 12 * s, '#57535e'); disc(c, x + 11 * s, y + 12 * s, 4 * s, C.ink); disc(c, x + 11 * s, y + 12 * s, 2 * s, C.sky); rect(c, x + 3 * s, y + 2 * s, 7 * s, 3 * s, C.ink); },
  video: (c, x, y, s) => { rect(c, x, y + 4 * s, 22 * s, 14 * s, C.ink); rect(c, x + s, y + 5 * s, 20 * s, 12 * s, '#3b3a42'); poly(c, [[x + 8 * s, y + 8 * s], [x + 15 * s, y + 11 * s], [x + 8 * s, y + 14 * s]], C.white); },
  phone: (c, x, y, s) => { rect(c, x + 5 * s, y, 12 * s, 22 * s, C.ink); rect(c, x + 6 * s, y + 2 * s, 10 * s, 16 * s, C.sky); rect(c, x + 9 * s, y + 19 * s, 4 * s, s, C.soft); },
  person: (c, x, y, s) => { disc(c, x + 11 * s, y + 5 * s, 4 * s, C.ink); rect(c, x + 6 * s, y + 10 * s, 10 * s, 11 * s, C.ink); rect(c, x + 7 * s, y + 11 * s, 8 * s, 9 * s, C.blue); },
  lock: (c, x, y, s) => padlock(c, x + 3 * s, y + s, true),
  swap: (c, x, y, s) => { arc(c, x + 11 * s, y + 11 * s, 8 * s, -2.6, .3, C.accent); arc(c, x + 11 * s, y + 11 * s, 7 * s, -2.6, .3, C.accent); poly(c, [[x + 17 * s, y + 9 * s], [x + 21 * s, y + 13 * s], [x + 14 * s, y + 14 * s]], C.accent); arc(c, x + 11 * s, y + 11 * s, 8 * s, .55, 3.4, C.ink); poly(c, [[x + 5 * s, y + 13 * s], [x + s, y + 9 * s], [x + 8 * s, y + 8 * s]], C.ink); },
  check: (c, x, y, s) => { disc(c, x + 11 * s, y + 11 * s, 10 * s, C.green); check(c, x + 6 * s, y + 7 * s, C.white, s); },
  cross: (c, x, y, s) => { disc(c, x + 11 * s, y + 11 * s, 10 * s, C.red); cross(c, x + 7 * s, y + 7 * s, C.white, 9 * s); },
  heart: (c, x, y, s) => { disc(c, x + 7 * s, y + 8 * s, 5 * s, '#e5433a'); disc(c, x + 15 * s, y + 8 * s, 5 * s, '#e5433a'); poly(c, [[x + 2 * s, y + 10 * s], [x + 20 * s, y + 10 * s], [x + 11 * s, y + 20 * s]], '#e5433a'); },
  star: (c, x, y, s) => { const P = []; for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, r = (k % 2 ? 4 : 10) * s; P.push([x + 11 * s + Math.cos(a) * r, y + 11 * s + Math.sin(a) * r]); } poly(c, P, C.yellow); },
  eye: (c, x, y, s) => { ellipse(c, x + 11 * s, y + 11 * s, 11 * s, 6 * s, C.ink); ellipse(c, x + 11 * s, y + 11 * s, 10 * s, 5 * s, C.white); disc(c, x + 11 * s, y + 11 * s, 4 * s, C.blue); disc(c, x + 11 * s, y + 11 * s, 2 * s, C.ink); },
  ear: (c, x, y, s) => { for (let k = 0; k < 3; k++) arc(c, x + 6 * s, y + 11 * s, (5 + k * 5) * s, -1.1, 1.1, k ? C.mint : C.white); disc(c, x + 3 * s, y + 11 * s, 3 * s, C.white); },
  film: (c, x, y, s) => { rect(c, x, y + 2 * s, 22 * s, 18 * s, C.ink); rect(c, x + 4 * s, y + 5 * s, 14 * s, 12 * s, C.sky); for (let k = 0; k < 4; k++) { rect(c, x + s, y + (4 + k * 4) * s, 2 * s, 2 * s, C.white); rect(c, x + 19 * s, y + (4 + k * 4) * s, 2 * s, 2 * s, C.white); } },
  image: (c, x, y, s) => { rect(c, x, y + 2 * s, 22 * s, 18 * s, C.ink); rect(c, x + s, y + 3 * s, 20 * s, 16 * s, '#bfe0f0'); poly(c, [[x + 2 * s, y + 18 * s], [x + 9 * s, y + 9 * s], [x + 15 * s, y + 18 * s]], C.green); disc(c, x + 16 * s, y + 7 * s, 2 * s, C.yellow); },
  note: (c, x, y, s) => { rect(c, x + 8 * s, y + 2 * s, 2 * s, 14 * s, C.ink); rect(c, x + 18 * s, y, 2 * s, 14 * s, C.ink); rect(c, x + 8 * s, y, 12 * s, 3 * s, C.ink); disc(c, x + 6 * s, y + 16 * s, 3 * s, C.ink); disc(c, x + 16 * s, y + 14 * s, 3 * s, C.ink); },
  clock: (c, x, y, s) => { disc(c, x + 11 * s, y + 11 * s, 10 * s, C.ink); disc(c, x + 11 * s, y + 11 * s, 8 * s, C.white); rect(c, x + 10 * s, y + 5 * s, 2 * s, 7 * s, C.ink); rect(c, x + 10 * s, y + 10 * s, 6 * s, 2 * s, C.ink); },
  coin: (c, x, y, s) => { disc(c, x + 11 * s, y + 11 * s, 10 * s, '#a87a1f'); disc(c, x + 11 * s, y + 11 * s, 8 * s, C.yellow); text(c, '$', x + 11 * s, y + 3 * s, '#a87a1f', { align: 'center', scale: s }); },
  bolt: (c, x, y, s) => poly(c, [[x + 13 * s, y], [x + 4 * s, y + 13 * s], [x + 10 * s, y + 13 * s], [x + 8 * s, y + 22 * s], [x + 18 * s, y + 8 * s], [x + 12 * s, y + 8 * s]], C.yellow),
  chat: (c, x, y, s) => { box(c, x, y + 2 * s, 22 * s, 14 * s, C.white, C.ink); poly(c, [[x + 5 * s, y + 15 * s], [x + 10 * s, y + 15 * s], [x + 5 * s, y + 21 * s]], C.ink); for (let k = 0; k < 3; k++) rect(c, x + (5 + k * 5) * s, y + 8 * s, 2 * s, 2 * s, C.ink); },
  building: (c, x, y, s) => { for (const [dx, h] of [[0, 16], [8, 22], [15, 12]]) { rect(c, x + dx * s, y + (22 - h) * s, 7 * s, h * s, '#8d8a93'); for (let yy = 24 - h; yy < 20; yy += 4) rect(c, x + (dx + 2) * s, y + yy * s, 3 * s, 2 * s, C.yellow); } },
  fan: (c, x, y, s) => { for (let k = 0; k < 3; k++) { const a = k * 2.094 - .4, ca = Math.cos(a), sa = Math.sin(a); poly(c, [[x + 11 * s + ca * 2 * s - sa * s, y + 11 * s + sa * 2 * s + ca * s], [x + 11 * s + ca * 10 * s - sa * 3 * s, y + 11 * s + sa * 10 * s + ca * 3 * s], [x + 11 * s + ca * 10 * s + sa * 3 * s, y + 11 * s + sa * 10 * s - ca * 3 * s]], '#a08a70'); } disc(c, x + 11 * s, y + 11 * s, 3 * s, C.ink); },
  paw: (c, x, y, s) => { disc(c, x + 11 * s, y + 14 * s, 5 * s, C.ink); for (const [dx, dy] of [[4, 7], [9, 4], [14, 4], [18, 7]]) disc(c, x + dx * s, y + dy * s, 2 * s, C.ink); },
  sparkle: (c, x, y, s) => { for (const [dx, dy, r] of [[11, 11, 7], [4, 4, 3], [18, 17, 3]]) { rect(c, x + (dx - r) * s, y + dy * s, (2 * r + 1) * s, s, C.yellow); rect(c, x + dx * s, y + (dy - r) * s, s, (2 * r + 1) * s, C.yellow); } },
  gear: (c, x, y, s) => { for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; disc(c, x + 11 * s + Math.cos(a) * 8 * s, y + 11 * s + Math.sin(a) * 8 * s, 2 * s, C.ink2); } disc(c, x + 11 * s, y + 11 * s, 7 * s, C.ink2); disc(c, x + 11 * s, y + 11 * s, 3 * s, C.paper); },
};
const icon = (c, name, x, y, s = 1) => (ICON[name] || ICON.sparkle)(c, R(x), R(y), s);

// ---------- footage: all-intra clips (exact seeking) drawn at full resolution into the 4x frame
const FC = document.getElementById('c'), FX = FC.getContext('2d'); FX.imageSmoothingEnabled = false;
const [c2, X2] = mk(), FULL_A = mk(W * S, H * S), FULL_B = mk(W * S, H * S), PXC = mk(8, 8), VIDS = {};
function placeholder(name) {
  const [c, x] = mk(432, 768); x.fillStyle = '#2a2930'; x.fillRect(0, 0, 432, 768); x.fillStyle = '#35333d';
  for (let k = -768; k < 432; k += 48) { x.beginPath(); x.moveTo(k, 0); x.lineTo(k + 24, 0); x.lineTo(k + 792, 768); x.lineTo(k + 768, 768); x.fill(); }
  x.textAlign = 'center'; x.font = 'bold 34px sans-serif'; x.fillStyle = '#ff9a3c'; x.fillText('MISSING', 216, 360); x.font = '22px monospace'; x.fillStyle = '#fff'; x.fillText(name, 216, 400);
  c.placeholder = true; c.duration = 10; return c;
}
function seekTo(v, t) {
  if (v.placeholder) return Promise.resolve();
  return new Promise(r => {                                     // never hang on a lost 'seeked' event: give up after 1.5 s and count it
    const tt_ = Math.max(0, Math.min(v.duration - 1 / 30, t)); if (Math.abs(v.currentTime - tt_) < .01 && v.readyState >= 2) return r();
    let done = false; const fin = late => { if (done) return; done = true; if (late) window.SLOW_SEEKS = (window.SLOW_SEEKS || 0) + 1; r(); };
    v.addEventListener('seeked', () => fin(false), { once: true }); setTimeout(() => fin(true), 1500); v.currentTime = tt_; });
}
const durOf = key => (VIDS[key] && VIDS[key].duration) || 10;
// media clock: number = media seconds at scene start | {at, media} = media time 'media' at time 'at', real speed | {from, to, loop:[a,b]} looping range
function clock(spec, t, t0 = 0, key) {
  const d = durOf(key) - .05; if (spec === undefined) return clamp(t - t0, 0, d);
  if (typeof spec === 'number') return clamp(spec + (t - t0), 0, d);
  const sp = spec.speed ?? 1;
  if (spec.loop) { const [a, b] = spec.loop, span = Math.max(.1, b - a); return a + (((t - ttOr(spec.at, t0)) * sp) % span + span) % span; }
  if (spec.hold !== undefined) return clamp(spec.hold, 0, d);
  return clamp((spec.media ?? 0) + (t - ttOr(spec.at, t0)) * sp, 0, d);
}
async function drawMedia(G, m) {                              // m: {v | img, t, x, y, w, h (art px), pix 0..1, ax, ay, side, fx, fy, dim}
  let src; if (m.v) { src = VIDS[m.v] || (VIDS[m.v] = placeholder(m.v)); await seekTo(src, m.t || 0); } else src = IMG[m.img]; if (!src) return;
  const sw = src.videoWidth || src.width, sh = src.videoHeight || src.height, dw = R(m.w * S), dh = R(m.h * S), dx = R(m.x * S), dy = R(m.y * S);
  let cx, cy, cw, ch;
  if (m.side) { cw = sw * m.side; ch = cw * dh / dw; cx = clamp(sw * (m.fx ?? .5) - cw / 2, 0, sw - cw); cy = clamp(sh * (m.fy ?? .5) - ch / 2, 0, Math.max(0, sh - ch)); }
  else { const a = dw / dh; if (sw / sh > a) { ch = sh; cw = sh * a; } else { cw = sw; ch = sw / a; } cx = (sw - cw) * (m.ax ?? .5); cy = (sh - ch) * (m.ay ?? .5); }
  if ((m.pix || 0) > .02) {
    const ps = Math.max(2, R(m.pix * 28)), w_ = Math.max(1, R(dw / ps)), h_ = Math.max(1, R(dh / ps)), [pc, px] = PXC;
    pc.width = w_; pc.height = h_; px.imageSmoothingEnabled = true; px.drawImage(src, cx, cy, cw, ch, 0, 0, w_, h_); G.imageSmoothingEnabled = false; G.drawImage(pc, 0, 0, w_, h_, dx, dy, dw, dh);
  } else { G.imageSmoothingEnabled = true; G.imageSmoothingQuality = 'high'; G.drawImage(src, cx, cy, cw, ch, dx, dy, dw, dh); G.imageSmoothingEnabled = false; }
  if (m.dim) { G.globalAlpha = m.dim; G.fillStyle = C.black; G.fillRect(dx, dy, dw, dh); G.globalAlpha = 1; }
}
async function compose(scn, t, G) {
  X.clearRect(0, 0, W, H); if (scn.base) scn.base(X); G[1].imageSmoothingEnabled = false; G[1].drawImage(cv, 0, 0, W * S, H * S);
  for (const m of scn.media || []) await drawMedia(G[1], m);
  X2.clearRect(0, 0, W, H); if (scn.top) scn.top(X2); G[1].drawImage(c2, 0, 0, W * S, H * S);
}
const reveal = (t, t0, d = .35) => 1 - eo(seg(t, t0, t0 + d));

// ---------- the host: a pixel portrait (480x270) that bobs with the narration; or a plain paper studio
const env = t => TL.env ? (TL.env[R(t * FPS)] || 0) : 0;
function hostBg(c, t) { if (EP.host && IMG.host) { const e = env(t), y = R(-e * 2); c.drawImage(IMG.host, 0, y, W, H + (y ? 2 : 0)); } else bg(c, 'paper'); }
function brandMark(c, x, y, k = 'ink', align = 'left', sc = 1) {           // logo image (as supplied, or tinted) else the brand name in pixel type
  const b = EP.brand || {}; if (!b.name && !IMG.logo) return 0;
  if (IMG.logo) { const i = b.tint ? tinted('logo', b.tint) : IMG.logo, f = Math.min(1, 16 / i.height, 110 / i.width) * sc, w = R(i.width * f), h = R(i.height * f), x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x; c.imageSmoothingEnabled = f < 1; c.drawImage(i, R(x0), R(y), w, h); c.imageSmoothingEnabled = false; return w; }
  return text(c, b.name, x, y, k, { scale: sc + 1, align });
}

// ---------- panel items: the building blocks of boards, split-screen panels and side columns (see the episode guide)
function compileItems(items, base = 0) { return (items || []).map(it => ({ ...it, _at: ttOr(it.at, base), _until: ttOr(it.until, 1e9) })); }
function drawItems(items, t, out) {                           // out = {base: [], media: [], top: []} draw callbacks / media
  for (const it of items) {
    if (t < it._at - .001 || t > it._until) continue;
    const y0 = popY(t, it._at, it.pop ?? 10) || 0, X0 = it.x ?? 240, Y0 = (it.y ?? 120) - y0, k = it.kind;
    if (k === 'chip') out.base.push(c => chip(c, X0, Y0, it.text, it.color || 'accent', it.fg || 'white', it.align || 'center'));
    else if (k === 'text') out.base.push(c => text(c, it.text, X0, Y0, it.color || 'ink', { scale: it.scale || 1, align: it.align || 'center' }));
    else if (k === 'stamp') out.top.push(c => stamp(c, t, it._at, it.text, it.color || 'red', it.x ?? 240, it.y ?? 120));
    else if (k === 'cross') out.top.push(c => bigX(c, t, it._at, X0, it.y ?? 120, it.size || 20));
    else if (k === 'icon') out.base.push(c => { const s = it.scale || 1; icon(c, it.name, X0 - 11 * s, Y0 - 11 * s, s); if (it.label) text(c, it.label, X0, Y0 + 12 * s, it.color || 'ink', { align: 'center' }); });
    else if (k === 'arrow') out.base.push(c => arrow(c, X0, Y0, R((it.len || 30) * eo(seg(t, it._at, it._at + .3))), it.color || 'accent', it.dir || 1));
    else if (k === 'bullets') out.base.push(c => {
      const w = it.w || 200, lines = it.lines || [], hh = (it.title ? 22 : 6) + lines.length * (it.gap || 20) + 4; box(c, X0, Y0, w, hh, col(it.fill || 'white'), C.ink);
      if (it.title) text(c, it.title, X0 + 8, Y0 + 3, it.titleColor || 'ink', { scale: it.titleScale || 1 });
      lines.forEach((ln, j) => { const L_ = typeof ln === 'string' ? { text: ln } : ln, ta = ttOr(L_.at, it._at); if (t < ta) return; const yy = Y0 + (it.title ? 22 : 6) + j * (it.gap || 20);
        const ic = L_.icon || it.icon; let xx = X0 + 8; if (ic === 'dot') { disc(c, xx + 3, yy + 7, 2, it.dotColor || 'accent'); xx += 10; } else if (ic) { icon(c, ic, xx, yy, .6); xx += 16; }
        text(c, L_.text, xx, yy, L_.color || it.color || 'ink'); });
    });
    else if (k === 'card') out.base.push(c => {
      const w = it.w || 120, hh = it.h || 150, hot = it.hot ? t > it._at && t < it._at + .6 : false; box(c, X0, Y0, w, hh, col(it.fill || (hot ? 'cream' : 'white')), col(it.edge || (hot ? 'accent' : 'ink')));
      let yy = Y0 + 4; if (it.title) { const sc = fit(it.title, w - 8, it.titleScale || 2); text(c, it.title, X0 + w / 2, yy, it.titleColor || 'ink', { scale: sc, align: 'center' }); yy += 13 * sc + 4; }
      if (it.icon) { icon(c, it.icon, X0 + w - 26, Y0 + 5, 1); }
      if (it.chip) { chip(c, X0 + w / 2, yy, it.chip, it.chipColor || 'accent', 'white', 'center'); yy += 20; }
      if (it.media) { const m = it.mediaBox = { x: X0 + 6, y: yy, w: w - 12, h: it.mediaH || 80 }; rect(c, m.x - 1, m.y - 1, m.w + 2, m.h + 2, C.ink); yy += m.h + 4; }
      (it.lines || []).forEach((ln, j) => { const L_ = typeof ln === 'string' ? { text: ln } : ln; if (t < ttOr(L_.at, it._at)) return; let xx = X0 + 8; if (L_.icon) { icon(c, L_.icon, xx, yy + j * 18, .6); xx += 16; } text(c, L_.text, xx, yy + j * 18, L_.color || 'ink2'); });
      if (it.note) text(c, it.note, X0 + w / 2, Y0 + hh - 18, it.noteColor || 'ink2', { align: 'center' });
    });
    else if (k === 'timeline') out.base.push(c => {
      const w = it.w || 300, d = it.duration || 10, px = s => R(X0 + s / d * w), bh = it.barH || 14, y = Y0 + (it.thumbs ? 58 : 18);
      if (it.title) text(c, it.title, X0, Y0, it.titleColor || 'ink', { scale: it.titleScale || 1 });
      (it.segments || []).forEach(([s0, s1, k2, label], j) => { if (t < it._at + j * .06) return; rect(c, px(s0), y, Math.max(1, px(s1) - px(s0) - 1), bh, k2 || 'accent'); if (label) text(c, label, (px(s0) + px(s1)) / 2, y + bh + 2, it.labelColor || 'ink2', { align: 'center' }); });
      if (it.ticks !== false) { rect(c, X0, y + bh + 1, w, 1, C.ink); const st = it.tickStep || Math.max(1, R(d / 5)); for (let s = 0; s <= d + .001; s += st) { rect(c, px(s), y + bh + 1, 1, 3, C.ink); if (!it.segments || !it.segments.some(g => g[3])) text(c, String(+s.toFixed(1)), px(s), y + bh + 4, 'ink2', { align: 'center' }); } }
      (it.markers || []).forEach((m, j) => { const ta = ttOr(m.at, it._at + .1 + j * .12); if (t < ta) return; const dy = popY(t, ta, 8), x = px(m.t); if (m.icon) icon(c, m.icon, x - 7, y - 20 - dy, .65); else poly(c, [[x - 4, y - 9 - dy], [x + 4, y - 9 - dy], [x, y - 2 - dy]], m.color || 'red'); if (m.label) text(c, m.label, x, it.thumbs ? y + bh + 16 : y - 24 - dy - (m.icon ? 6 : 0), m.color || 'red', { align: 'center' }); });
      if (it.thumbs) it.thumbs.forEach((th, j) => { if (t < ttOr(th.at, it._at + .2 + j * .1)) return; const x = px(th.t ?? (j + .5) * d / it.thumbs.length); rect(c, x - 13, Y0 + 14, 26, 46, C.ink); });
    });
    else if (k === 'slot') out.base.push(c => { const w = it.w || 112, hh = it.h || 112; box(c, X0 - 14, Y0 - 34, w + 28, hh + 62, C.cream, C.accent); chip(c, X0 + w / 2, Y0 - 26, it.title || '{{slot}}', it.color || 'accent', 'white', 'center'); rect(c, X0 - 1, Y0 - 1, w + 2, hh + 2, C.ink); if (t < ttOr(it.spinAt, it._at + .4)) { rect(c, X0, Y0, w, hh, C.dark2); text(c, '?', X0 + w / 2, Y0 + hh / 2 - 26, 'accent', { scale: 4, align: 'center' }); } });
    else if (k === 'phones') out.base.push(c => (it.items || []).forEach((p, j) => { const ta = ttOr(p.at, it._at + j * .15); if (t < ta) return; const yy = popY(t, ta, 16) || 0, s = phoneBox(it, j, yy); if (ttOr(p.hot, 1e9) <= t) rect(c, s.x - 9, s.y - 13, s.w + 18, s.h + 26, C.accent); phone(c, s); if (j && it.arrows !== false) arrow(c, s.x - (it.gapX || 150) + s.w + 12, s.y + s.h / 2, (it.gapX || 150) - s.w - 30, 'accent'); }));
    else if (k === 'grid') out.base.push(c => (it.items || []).forEach((g, j) => { const ta = ttOr(g.at, it._at + j * (it.stagger ?? .06)); if (t < ta) return; const s = gridBox(it, j, popY(t, ta, 12) || 0); rect(c, s.x - 2, s.y - 2, s.w + 4, s.h + 4, g.hot && t >= ttOr(g.hot, 1e9) ? C.accent : C.white); rect(c, s.x - 1, s.y - 1, s.w + 2, s.h + 2, C.ink); }));
    else if (k === 'media') out.base.push(c => { if (it.phone) phone(c, { x: X0, y: Y0, w: it.w, h: it.h }); else frame(c, { x: X0, y: Y0, w: it.w, h: it.h }, it.frameColor || 'white'); });
    else if (k === 'boxes') out.top.push(c => (it.boxes || []).forEach(b => { if (t < ttOr(b.at, it._at) || t > ttOr(b.until, 1e9)) return; const [fx0, fy0, fx1, fy1] = b.box, x = R(it.x + fx0 * it.w), y = R(it.y + fy0 * it.h), w = R((fx1 - fx0) * it.w), h = R((fy1 - fy0) * it.h); outlineBox(c, x, y, w, h, t, b.color || 'accent'); if (b.label) chip(c, x + w / 2, y + h + 2, b.label, b.color || 'accent', 'white', 'center'); }));
    // footage that belongs to the item
    if (k === 'media') out.media.push({ ...(it.image ? { img: it.image } : { v: it.media, t: clock(it.clock, t, it._at, it.media) }), x: X0, y: Y0, w: it.w, h: it.h, ax: it.ax, ay: it.ay, pix: reveal(t, it._at), dim: it.dimAt && t > tt(it.dimAt) ? .5 : 0 });
    if (k === 'card' && it.media) { const yy = Y0 + 4 + (it.title ? 13 * fit(it.title, (it.w || 120) - 8, it.titleScale || 2) + 4 : 0) + (it.chip ? 20 : 0); out.media.push({ ...(it.image ? { img: it.image } : { v: it.media, t: clock(it.clock, t, it._at, it.media) }), x: X0 + 6, y: yy, w: (it.w || 120) - 12, h: it.mediaH || 80, ay: it.ay, pix: reveal(t, it._at) }); }
    if (k === 'timeline' && it.thumbs) { const w = it.w || 300, d = it.duration || 10; it.thumbs.forEach((th, j) => { if (t < ttOr(th.at, it._at + .2 + j * .1)) return; const x = R(X0 + (th.t ?? (j + .5) * d / it.thumbs.length) / d * w); out.media.push({ v: th.media, t: th.mt ?? 1, x: x - 12, y: Y0 + 15, w: 24, h: 44, ay: th.ay ?? .3 }); }); }
    if (k === 'phones') (it.items || []).forEach((p, j) => { const ta = ttOr(p.at, it._at + j * .15); if (t < ta) return; const s = phoneBox(it, j, popY(t, ta, 16) || 0); out.media.push({ v: p.media, t: clock(p.clock || { loop: p.loop || [0, durOf(p.media)] }, t, it._at, p.media), ...s, pix: reveal(t, ta), dim: p.hot !== undefined && t < tt(p.hot) ? .35 : 0 }); if (p.label) out.base.push(c => { chip(c, s.x + s.w / 2, s.y + s.h + 12, p.label, ttOr(p.hot, 1e9) <= t ? 'accent' : 'ink', 'white', 'center'); if (p.sub) text(c, p.sub, s.x + s.w / 2, s.y + s.h + 30, 'ink2', { align: 'center' }); }); });
    if (k === 'grid') (it.items || []).forEach((g, j) => { const ta = ttOr(g.at, it._at + j * (it.stagger ?? .06)); if (t < ta) return; const s = gridBox(it, j, popY(t, ta, 12) || 0); out.media.push({ ...(g.image ? { img: g.image } : { v: g.media, t: g.mt ?? clock(g.clock, t, ta, g.media) }), ...s, side: it.square ? (g.side || .86) : undefined, fx: g.fx, fy: g.fy, ay: g.ay, pix: reveal(t, ta, .3), dim: it.dimAt && t > tt(it.dimAt) && !(g.hot && t >= tt(g.hot)) ? .55 : 0 }); if (g.label) out.base.push(c => chip(c, s.x + s.w / 2, s.y + s.h + 4, g.label, g.labelColor || 'accent', 'white', 'center')); });
    if (k === 'slot' && t >= ttOr(it.spinAt, it._at + .4) && it.spin) { const sp = it.spin, j = Math.floor(Math.max(0, t - ttOr(it.spinAt, it._at + .4)) / (t < ttOr(it.spinAt, it._at + .4) + 1 ? .09 : .3)) % sp.length; out.media.push({ v: sp[j].media, t: sp[j].mt ?? 1, x: X0, y: Y0, w: it.w || 112, h: it.h || 112, ay: sp[j].ay ?? .4 }); if (sp[j].label) out.top.push(c => chip(c, X0 + (it.w || 112) / 2, Y0 + (it.h || 112) + 6, sp[j].label, 'ink', 'white', 'center')); }
    if (it.dust !== false && ['chip', 'stamp', 'card', 'icon'].includes(k)) out.top.push(c => dust(c, t, it._at + .05, X0 + (k === 'card' ? (it.w || 120) / 2 : 0), Y0 + 8, { n: 10, speed: 80, col: [C.accent, C.white], seed: R(X0 + Y0) }));
  }
}
const phoneBox = (it, j, dy) => { const w = it.w || 72, h = it.h || 128, gx = it.gapX || 150, n = (it.items || []).length, x0 = it.x ?? R(240 - ((n - 1) * gx + w) / 2); return { x: x0 + j * gx, y: (it.y ?? 40) - dy - (it.rise ?? 6) * j, w, h }; };
const gridBox = (it, j, dy) => { const cols = it.cols || 3, cw = it.cell || 60, ch = it.cellH || cw, g = it.gap ?? 4, n = (it.items || []).length, rows = Math.ceil(n / cols), x0 = it.x ?? R(240 - (cols * cw + (cols - 1) * g) / 2); return { x: x0 + (j % cols) * (cw + g), y: (it.y ?? 40) + Math.floor(j / cols) * (ch + g) - dy, w: cw, h: ch, rows }; };
function itemsScene(items, t) { const out = { base: [], media: [], top: [] }; drawItems(items, t, out); return out; }

// ---------- scene library -----------------------------------------------------------------------------------------
const PORTRAIT = [{ x: 118, y: 30, w: 108, h: 192 }, { x: 254, y: 30, w: 108, h: 192 }], LANDSCAPE = [{ x: 22, y: 64, w: 210, h: 118 }, { x: 248, y: 64, w: 210, h: 118 }];
const SCENES = {
  // two clips side by side, in sync (hook); optional side columns built from items
  compare(s) {
    const P = s.orient === 'landscape' ? LANDSCAPE : PORTRAIT, items = compileItems(s.items, s._t0), vs = ttOr(s.vs, null);
    return t => {
      const up = j => R((1 - clamp(back(seg(t, s._t0 + .02 + j * .08, s._t0 + .4 + j * .08)), 0, 1.1)) * 260), a = { ...P[0], y: P[0].y + up(0) }, b = { ...P[1], y: P[1].y + up(1) };
      const ia = itemsScene(items, t), sides = [s.left, s.right], boxes = [a, b];
      return {
        base: c => { bg(c, s.bg || 'dark'); phone(c, a); phone(c, b); ia.base.forEach(f => f(c)); },
        media: [...sides.map((sd, j) => ({ v: sd.media, t: clock(sd.clock ?? s.clock, t, s._t0, sd.media), ...boxes[j], pix: reveal(t, s._t0 + .3 + j * .15) })), ...ia.media],
        top: c => {
          sides.forEach((sd, j) => { const ta = ttOr(sd.labelAt, s._t0 + .45 + j * .1); if (t > ta && sd.label) { const y = popY(t, ta, 8); chip(c, boxes[j].x + boxes[j].w / 2, boxes[j].y + 4 - y, sd.label, sd.labelColor || (j ? 'accent' : 'ink'), 'white', 'center'); } });
          if (vs !== null && t > vs) { const dt = t - vs, sc = dt < 1 / 30 ? 4 : dt < 2 / 30 ? 3 : 2, cx = (a.x + a.w + b.x) / 2, cy = 126; disc(c, cx, cy, 7 * sc, C.accent); disc(c, cx, cy, 7 * sc - 2, C.ink); text(c, 'VS', cx + 1, cy - 8.5 * sc, C.white, { scale: sc, align: 'center' }); dust(c, t, vs + .05, cx, cy, { n: 18, speed: 120, col: [C.accent, C.white], seed: 2 }); }
          ia.top.forEach(f => f(c)); if (s.crt) crtOn(c, (t - s._t0) / .16);
        },
      };
    };
  },
  // one source clip splits into a row of N variants (batch / fission hook, or a results wall)
  row(s) {
    const items = s.items || [], n = items.length, gap = 4, w = Math.min(84, Math.floor((466 - (n - 1) * gap) / n)), h = Math.min(132, R(w * 16 / 9)), ww = R(h * 9 / 16) < w ? R(h * 9 / 16) : w;
    const x0 = R(240 - (n * ww + (n - 1) * gap) / 2), y0 = s.y ?? 80, split = ttOr(s.splitAt, s._t0), extra = compileItems(s.extras, s._t0), hl = s.highlight ? { i: s.highlight.index, at: tt(s.highlight.at), label: s.highlight.label } : null;
    const BIG = { x: 186, y: 22, w: 108, h: 192 }, SMALL = { x: 240 - 18, y: 4, w: 36, h: 64 }, cuts = s.cutFlash || [];
    const tile = j => ({ x: x0 + j * (ww + gap), y: y0, w: ww, h }), tIn = j => split + .1 + Math.abs(j - (n - 1) / 2) * .05;
    return t => {
      const sh = s.source ? eio(seg(t, split - .3, split + .05)) : 1, LL = (p, q) => R(p + (q - p) * sh), o = { x: LL(BIG.x, SMALL.x), y: LL(BIG.y, SMALL.y), w: LL(BIG.w, SMALL.w), h: LL(BIG.h, SMALL.h) };
      const ts = clock(s.clock, t, s._t0, s.source ? s.source.media : items[0] && items[0].media), tiles = items.map((it, j) => { const dy = popY(t, tIn(j), 20); return dy === null ? null : { ...tile(j), y: tile(j).y + dy }; });
      const ex = itemsScene(extra, t), flash = cuts.some(cc => ts >= cc && ts < cc + .1), dimOthers = hl && t > hl.at;
      return {
        base: c => {
          bg(c, s.bg || 'dark');
          if (s.source && sh > 0) tiles.forEach(r => { if (!r) return; const q = eo(seg(t, tIn(0), tIn(0) + .3)); line(c, 240, SMALL.y + SMALL.h + 2, R(240 + (r.x + r.w / 2 - 240) * q), R(SMALL.y + SMALL.h + 2 + (r.y - 4 - SMALL.y - SMALL.h) * q), 'accent'); });
          tiles.forEach((r, j) => { if (r) rect(c, r.x - 1, r.y - 1, r.w + 2, r.h + 2, hl && dimOthers && j === hl.i ? C.accent : C.ink); });
          if (s.source) { if (sh < 1) phone(c, o); else rect(c, o.x - 1, o.y - 1, o.w + 2, o.h + 2, C.accent); }
          ex.base.forEach(f => f(c));
        },
        media: [...(s.source ? [{ v: s.source.media, t: ts, ...o, pix: reveal(t, s._t0 + .3) }] : []), ...items.map((it, j) => tiles[j] && { v: it.media, t: it.clock !== undefined ? clock(it.clock, t, s._t0, it.media) : ts, ...tiles[j], pix: reveal(t, tIn(j), .3), dim: dimOthers && j !== hl.i ? .55 : 0 }).filter(Boolean), ...ex.media],
        top: c => {
          if (s.source && sh < .5 && s.source.label && t > s._t0 + .4) chip(c, 240, BIG.y + 4 - (popY(t, s._t0 + .4, 8) || 0), s.source.label, 'ink', 'white', 'center');
          if (s.source && sh >= 1 && s.source.short) chip(c, SMALL.x - 20, 10, s.source.short, 'ink', 'white', 'center');
          items.forEach((it, j) => { const r = tiles[j]; if (!r || !it.label || t < ttOr(it.at, 1e9)) return; const ta = tt(it.at); if (t < ta + .35) outlineBox(c, r.x - 3, r.y - 3, r.w + 6, r.h + 6, t); chip(c, r.x + r.w / 2, r.y + r.h + 4 - (popY(t, ta, 8) || 0), it.label, 'accent', 'white', 'center'); });
          (s.groups || []).forEach(g => { const ta = tt(g.at); if (t < ta) return; const a = tile(g.from), b = tile(g.to); if (t < ta + .35) outlineBox(c, a.x - 3, a.y - 3, b.x + b.w - a.x + 6, a.h + 6, t); chip(c, (a.x + b.x + b.w) / 2, a.y + a.h + 4 - (popY(t, ta, 8) || 0), g.label, 'accent', 'white', 'center'); });
          if (hl && t > hl.at && hl.label) { const r = tiles[hl.i]; if (r) chip(c, r.x + r.w / 2, r.y - 20 - (popY(t, hl.at, 8) || 0), hl.label, 'red', 'white', 'center'); }
          if (flash && sh >= 1) { c.globalAlpha = .45; tiles.forEach(r => r && rect(c, r.x, r.y, r.w, r.h, C.white)); if (s.source) rect(c, o.x, o.y, o.w, o.h, C.white); c.globalAlpha = 1; }
          ex.top.forEach(f => f(c)); if (s.tag) chip(c, 462, 4, s.tag, '#4a4752', 'white', 'center'); if (s.crt) crtOn(c, (t - s._t0) / .16);
        },
      };
    };
  },
  // title card over the host portrait (or a paper studio)
  title(s) {
    const lines = s.lines || [], st = s.stamp ? { at: tt(s.stamp.at), text: s.stamp.text, color: s.stamp.color || 'red' } : null, at = ttOr(s.cardAt, s._t0 + .25), items = compileItems(s.items, s._t0);
    return t => {
      const ia = itemsScene(items, t), host = EP.host && IMG.host, cx = host ? 106 : 240, bw = host ? 184 : 300, bx = R(cx - bw / 2);
      return {
        base: c => { hostBg(c, t); if (!host) dust(c, t, at, 240, 120, { n: 26, speed: 140, col: ['accent', 'ink2'], seed: 5 }); },
        media: ia.media,
        top: c => {
          const y = popY(t, at, 40); if (y !== null) {
            const by = (host ? 26 : 60) - y; let hh = 18; lines.forEach(([s_, , sc]) => { hh += 13 * fit(s_, bw - 16, sc || 3) + 6; }); if (s.sub) hh += 18; if (EP.brand && (EP.brand.name || IMG.logo)) hh += 26;
            box(c, bx, by, bw, hh, C.paper, C.ink); let yy = by + 8;
            if (EP.brand && (EP.brand.name || IMG.logo)) { brandMark(c, cx, yy, 'ink', 'center'); yy += 26; }
            lines.forEach(([s_, k, sc]) => { const sc2 = fit(s_, bw - 16, sc || 3); text(c, s_, cx, yy, k || 'accent', { scale: sc2, align: 'center' }); yy += 13 * sc2 + 6; });
            if (s.sub) text(c, s.sub, cx, yy, 'ink2', { align: 'center' });
          }
          if (st && t > st.at) { const dt = t - st.at, sc = dt < 1 / 30 ? 4 : dt < 2 / 30 ? 3 : 2, w = tw(st.text, sc) + 20, sy = host ? 140 : 190; box(c, R(cx - w / 2), sy, w, 13 * sc + 10, col(st.color), C.ink); text(c, st.text, cx, sy + 3, C.white, { scale: sc, align: 'center' }); dust(c, t, st.at, cx, sy + 10, { n: 18, speed: 120, col: [C.red2, C.white], seed: 6 }); }
          ia.top.forEach(f => f(c));
        },
      };
    };
  },
  // free board: paper / dark grid background, an optional phone with the clip, and any panel items
  board(s) {
    const items = compileItems(s.items, s._t0), ph = s.phone, PH = ph ? { ...(ph.box || (ph.pos === 'left' ? { x: 24, y: 30, w: 108, h: 192 } : ph.pos === 'center' ? { x: 186, y: 22, w: 108, h: 192 } : { x: 344, y: 30, w: 108, h: 192 })) } : null;
    const pbox = ph ? compileItems([{ kind: 'boxes', x: PH.x, y: PH.y, w: PH.w, h: PH.h, boxes: ph.boxes || [], at: s._t0 }]) : [], pchips = compileItems((ph && ph.chips) || [], s._t0);
    return t => {
      const ia = itemsScene(items, t), pb = itemsScene(pbox, t);
      return {
        base: c => { bg(c, s.bg || 'paper'); if (PH) phone(c, PH); ia.base.forEach(f => f(c)); },
        media: [...(PH ? [{ v: ph.media, t: clock(ph.clock, t, s._t0, ph.media), ...PH, pix: reveal(t, s._t0 + .1) }] : []), ...ia.media],
        top: c => { pb.top.forEach(f => f(c)); pchips.forEach(ch => { if (t < ch._at || t > ch._until) return; const y = popY(t, ch._at, 8); chip(c, PH.x + PH.w / 2, (ch.pos === 'bottom' ? PH.y + PH.h - 22 : PH.y + 4) - y, ch.text, ch.color || 'ink', 'white', 'center'); }); ia.top.forEach(f => f(c)); },
      };
    };
  },
  // ending: host portrait with chips, a follow button, then the brand end card
  outro(s) {
    const chips = compileItems(s.chips, s._t0), fol = s.follow ? { at: tt(s.follow.at), label: s.follow.label || '+ Follow', done: s.follow.done || '♥ Following' } : null, end = ttOr(s.endAt, null);
    return t => {
      if (end !== null && t >= end) return {
        base: c => {
          bg(c, 'paper'); const lp = seg(t, end, end + .5), y = R(70 - (1 - bounce(lp)) * 110); if (lp > 0) brandMark(c, 240, y, 'ink', 'center', 2);
          dust(c, t, end + .2, 240, 100, { n: 20, speed: 110, col: ['ink2', 'accent'], seed: 14 });
          if (s.endText && t > end + .4) { const yy = popY(t, end + .4, 10); const w = tw(s.endText) + 24; box(c, R(240 - w / 2), 128 - yy, w, 20, C.ink); text(c, s.endText, 240, 130 - yy, C.white, { align: 'center' }); }
          const f = seg(t, TL.dur - .45, TL.dur - .05); if (f > 0) shade(c, '#000', f);
        },
      };
      return {
        base: c => hostBg(c, t),
        top: c => {
          chips.forEach((ch, j) => { if (t < ch._at) return; const y = popY(t, ch._at, 10); chip(c, ch.x ?? 80, (ch.y ?? 60 + j * 26) - y, ch.text, ch.color || (j % 2 ? 'accent' : 'ink'), 'white', 'center'); dust(c, t, ch._at + .05, ch.x ?? 80, (ch.y ?? 60 + j * 26) + 8, { n: 12, speed: 90, col: [C.accent, C.white], seed: 12 + j }); });
          if (fol && t > fol.at) {
            const p = back(seg(t, fol.at, fol.at + .25)), clk = fol.at + .6, done = t > clk, bx = 356, by = R(176 + (1 - clamp(p)) * 20), dn = t > clk && t < clk + .1 ? 1 : 0;
            box(c, bx, by + 2, 96, 26, '#7a3a17'); box(c, bx, by + dn, 96, 24, done ? C.white : C.accent, C.ink); text(c, done ? fol.done : fol.label, bx + 48, by + 4 + dn, done ? C.accent : C.white, { align: 'center' });
            const cp = eio(seg(t, fol.at + .15, clk)); if (t < clk + .6) cursor(c, R(470 - (470 - (bx + 60)) * cp), R(262 - (262 - (by + 14)) * cp), clk, t);
            dust(c, t, clk, bx + 48, by + 12, { n: 22, speed: 120, col: [C.accent, C.red2, C.white], seed: 13 });
          }
        },
      };
    };
  },
};
const bounce = p => { const n = 7.5625, d = 2.75; if (p < 1 / d) return n * p * p; if (p < 2 / d) return n * (p -= 1.5 / d) * p + .75; if (p < 2.5 / d) return n * (p -= 2.25 / d) * p + .9375; return n * (p -= 2.625 / d) * p + .984375; };

// ---------- edit decision list
let SC = []; const SHAKES = [];
function compileScenes() {                                    // after ui.js has loaded (it provides the chat scene)
  SC = EP.scenes.map(s => ({ ...s, _t0: tt(s.at) })).sort((a, b) => a._t0 - b._t0);
  SC.forEach(s => { if (!SCENES[s.type] && s.type !== 'chat') throw new Error('unknown scene type ' + s.type); s.fn = s.type === 'chat' ? window.chatScene(s) : SCENES[s.type](s); s.d = s.d ?? (s.tr === 'whip' ? .16 : s.tr === 'pblocks' ? .4 : s.tr === 'blocks' ? .25 : 0); });
  SC.forEach(s => (s.items || []).concat(s.extras || []).forEach(it => { if (it.kind === 'stamp' && it.shake !== false) SHAKES.push([tt(it.at), .22, 3]); }));
  (EP.shakes || []).forEach(([a, d, m]) => SHAKES.push([tt(a), d || .2, m || 3]));
}
const shakeAt = t => { let a = 0; for (const [s, d, m] of SHAKES) if (t >= s && t < s + d) a = Math.max(a, m * (1 - (t - s) / d)); return a ? [R(Math.sin(t * 97) * a), R(Math.cos(t * 83) * a * .6)] : [0, 0]; };
// step badges + tracker (optional): EP.steps = [{at, big: 'Step 1', label: 'Drop'}...], hidden after EP.stepsUntil
const STEPS = (EP.steps || []).map(s => ({ ...s, _at: tt(s.at) })), STEPS_END = ttOr(EP.stepsUntil, 1e9);
const STEP_W = STEPS.map(s => 22 + tw(s.short || s.label || '')), STEP_X0 = 480 - 8 - STEP_W.reduce((a, b) => a + b, 4);
const stepX = j => STEP_X0 + 11 + STEP_W.slice(0, j).reduce((a, b) => a + b, 0);
function stepBadge(c, t) {
  STEPS.forEach((s, j) => {
    const dt = t - s._at; if (dt < 0 || dt > .95) return; const tx = stepX(j), ty = 9;
    if (dt < .6) { const sc = dt < 1 / 30 ? 5 : dt < 2 / 30 ? 4 : 3, big = s.big || String(j + 1), sc2 = Math.min(sc, fit(big, 300, sc)), w = Math.max(tw(big, sc2), tw(s.label || '', 2)) + 24; box(c, R(240 - w / 2), 66, w, 13 * sc2 + 34, C.accent, C.ink); text(c, big, 240, 70, C.white, { scale: sc2, align: 'center' }); text(c, s.label || '', 240, 70 + 13 * sc2, C.ink, { scale: 2, align: 'center' }); dust(c, t, s._at + .07, 240, 110, { n: 24, speed: 150, col: [C.accent, C.white, C.yellow], seed: 50 + j }); }
    else { const q = eio((dt - .6) / .35); disc(c, 240 + (tx - 240) * q, 100 + (ty - 100) * q, R(14 - 8 * q), C.accent); }
  });
}
function tracker(c, t) {
  if (!STEPS.length || t < STEPS[0]._at + .9 || t > STEPS_END) return;
  c.globalAlpha = .85; box(c, STEP_X0, 1, 480 - 8 - STEP_X0, 17, '#1b1a20'); c.globalAlpha = 1;
  STEPS.forEach((s, j) => { const x = stepX(j) + 2, on = t >= s._at + .9, cur = on && (j === STEPS.length - 1 || t < STEPS[j + 1]._at), done = on && !cur; disc(c, x, 9, 6, cur ? C.accent : done ? C.green : '#4a4752'); if (done) check(c, x - 4, 6, C.white); else text(c, String(j + 1), x + 1, 0, C.white, { align: 'center' }); text(c, s.short || s.label || '', x + 8, 1, cur ? C.white : C.muted); });
}

// ---------- subtitles: 2x overlay, no box, outline + drop shadow, keywords in orange that hop when spoken
const OC = document.createElement('canvas'); OC.width = W * 2; OC.height = H * 2; const O = OC.getContext('2d'); O.imageSmoothingEnabled = false;
const SUBS = [], SUB_SC = EP.subtitleScale || 3, SUB_MAX = 900;
TL.lines.forEach(Ln => {
  const kws = (EP.keywords || {})[Ln.n] || [], clean = Ln.chars.map(c => c[0]).join('').toLowerCase();
  let buf = null;
  Ln.phr.forEach((p, i) => {
    if (!buf) buf = { text: p.text, s: p.s, e: p.e }; else { buf.text += (/\s/.test(Ln.text) ? ' ' : '，') + p.text; buf.e = p.e; }
    if ([...p.text].length <= 2 && i < Ln.phr.length - 1 && tw(buf.text, SUB_SC) < SUB_MAX * .6) return;
    const rows = wrap(buf.text, SUB_MAX, SUB_SC); let off = 0;
    for (const row of rows) {
      const start = buf.text.indexOf(row, off); off = start + row.length; const hot = [];
      for (const k of kws) { let j = row.toLowerCase().indexOf(k.toLowerCase()); while (j >= 0) { const ci = clean.indexOf(k.replace(/[\s\p{P}]/gu, '').toLowerCase()); hot.push([j, [...k].length, ci >= 0 && Ln.chars[ci] ? Ln.chars[ci][1] : buf.s]); j = row.toLowerCase().indexOf(k.toLowerCase(), j + 1); } }
      SUBS.push({ rows: [row], s: buf.s, e: buf.e, line: Ln.n, hot });
    }
    buf = null;
  });
});
// rows from one phrase that wrapped are shown together (max two), in sequence otherwise
for (let i = SUBS.length - 1; i > 0; i--) if (SUBS[i].s === SUBS[i - 1].s && SUBS[i - 1].rows.length === 1) { SUBS[i - 1].rows.push(SUBS[i].rows[0]); SUBS[i - 1].hot2 = SUBS[i].hot; SUBS.splice(i, 1); }
SUBS.forEach((s, i) => { const n = SUBS[i + 1]; s.until = n && n.line === s.line ? n.s - .02 : Math.min(s.e + .35, n ? n.s - .05 : 1e9); });
function subtitles(c, t) {
  if (EP.subtitles === false) return; const s = SUBS.find(s => t >= s.s - .06 && t < s.until); if (!s) return;
  const sc = SUB_SC, lh = 13 * sc + 6, y00 = 468 - (s.rows.length - 1) * lh + R((1 - eo(seg(t, s.s - .06, s.s + .04))) * 8);
  s.rows.forEach((row, r) => {
    const chars = [...row], cols = chars.map(() => C.white), dy = chars.map(() => 0);
    for (const [j, n, ts] of (r ? s.hot2 || [] : s.hot)) for (let k = j; k < j + n && k < chars.length; k++) { cols[k] = C.sub; const q = seg(t, ts - .02, ts + .2); dy[k] = q > 0 && q < 1 ? -R(Math.sin(q * Math.PI) * 6) : 0; }
    const x0 = R(480 - tw(row, sc) / 2), y0 = y00 + r * lh;
    const pass = (k, ox, oy) => { let x = x0; chars.forEach((ch, i) => { drawStr(c, ch, x + ox, y0 + oy + dy[i], k || cols[i], sc, 1); x += tw(ch, sc); }); };
    for (const [ox, oy] of [[0, 5], [3, 5], [-3, 5]]) pass('#0e0d12', ox, oy);
    for (const [ox, oy] of [[-3, 0], [3, 0], [0, -3], [0, 3], [-3, -3], [3, -3], [-3, 3], [3, 3]]) pass('#16141a', ox, oy);
    pass(null, 0, 0);
  });
}

// ---------- transitions + the render loop
const TC = document.getElementById('top'), TX = TC.getContext('2d'); TX.imageSmoothingEnabled = false;
function blocksFull(G, src, p) { const B = 120; for (let gy = 0; gy < Math.ceil(H * S / B); gy++) for (let gx = 0; gx < Math.ceil(W * S / B); gx++) { const d = (gx + gy) / 25, q = clamp(p * 1.8 - d * .8); if (q <= 0) continue; const sz = Math.max(4, R(q * B / 4) * 4), x = gx * B + (B - sz) / 2, y = gy * B + (B - sz) / 2; G.drawImage(src, x, y, sz, sz, x, y, sz, sz); } }
function pixBlocks(c, k) { const B = 30; for (let gy = 0; gy < Math.ceil(H / B); gy++) for (let gx = 0; gx < Math.ceil(W / B); gx++) { const d = (gx + gy) / 25, q = clamp(k * 1.7 - d * .7); if (q <= 0) continue; const sz = R(q * B); rect(c, gx * B + (B - sz) / 2, gy * B + (B - sz) / 2, sz, sz, C.black); } }
function streaks(c, t, k) { const sd = Math.floor(t * 30); dmix(c, layer(l => { for (let i = 0; i < 30; i++) rect(l, R(hash(sd * 3 + i) * W) - 60, R(hash(sd * 7 + i) * H), 40 + R(hash(i + sd) * 200), 1 + (i % 3 === 0), i % 4 ? '#f3efe6' : '#bfb8ab'); }), k); }
const UIROOT = document.getElementById('ui');
window.render = async function (frame) {
  const t = frame / FPS; let i = 0; while (i + 1 < SC.length && t >= SC[i + 1]._t0) i++;
  const s = SC[i], p = s.d ? (t - s._t0) / s.d : 1, [sx, sy] = shakeAt(t); let cur = s, blk = 0;
  if (s.tr === 'pblocks' && i > 0 && p < 1) { if (p < .5) cur = SC[i - 1]; blk = 1 - Math.abs(p - .5) * 2; }
  const scn = cur.fn(t); FX.setTransform(1, 0, 0, 1, 0, 0); FX.fillStyle = C.black; FX.fillRect(0, 0, W * S, H * S);
  await compose(scn, t, FULL_A);
  if ((s.tr === 'whip' || s.tr === 'blocks') && i > 0 && p < 1) {
    await compose(SC[i - 1].fn(t), t, FULL_B);
    if (s.tr === 'whip') { const q = eio(p); FX.drawImage(FULL_B[0], R(-q * W) * S, 0); FX.drawImage(FULL_A[0], R(W * (1 - q)) * S, 0); X2.clearRect(0, 0, W, H); streaks(X2, t, .75 * Math.sin(Math.PI * p)); FX.drawImage(c2, 0, 0, W * S, H * S); }
    else { FX.drawImage(FULL_B[0], 0, 0); blocksFull(FX, FULL_A[0], p); }
  } else FX.drawImage(FULL_A[0], sx * S, sy * S);
  if (scn.ui) { UIROOT.style.display = 'block'; await scn.ui(); } else UIROOT.style.display = 'none';
  X2.clearRect(0, 0, W, H); if (scn.callouts) scn.callouts(X2); stepBadge(X2, t); tracker(X2, t); if (blk > 0) pixBlocks(X2, blk);
  TX.clearRect(0, 0, W * S, H * S); TX.drawImage(c2, 0, 0, W * S, H * S); O.clearRect(0, 0, W * 2, H * 2); subtitles(O, t); TX.drawImage(OC, 0, 0, W * S, H * S);
};

// ---------- sound cues for mix.py, derived from the same timing as the picture
window.CUES = () => {
  const E = [], add = (t, type, o = {}) => { if (t >= 0 && t < TL.dur) E.push({ t: +t.toFixed(3), type, ...o }); };
  SC.forEach((s, j) => {
    if (j && s.tr) add(s._t0, s.tr === 'whip' ? 'whip' : 'blocks'); if (s.crt) add(s._t0, 'crt');
    if (s.type === 'compare') { add(s._t0 + .3, 'whoosh'); if (s.vs) add(tt(s.vs), 'stamp', { soft: 1 }); }
    if (s.type === 'row') { const sp = ttOr(s.splitAt, s._t0); add(sp - .3, 'whoosh'); (s.items || []).forEach((it, k) => { add(sp + .1 + Math.abs(k - ((s.items.length - 1) / 2)) * .05, 'blip'); if (it.label && it.at) add(tt(it.at) - .1, 'pop'); }); (s.groups || []).forEach(g => add(tt(g.at) - .1, 'pop')); if (s.highlight) add(tt(s.highlight.at), 'sparkle'); }
    if (s.type === 'title') { add(ttOr(s.cardAt, s._t0 + .25), 'whoosh'); add(ttOr(s.cardAt, s._t0 + .25) + .15, 'chime'); if (s.stamp) add(tt(s.stamp.at), 'stamp', { soft: 1 }); }
    if (s.type === 'outro') { (s.chips || []).forEach(ch => add(tt(ch.at), 'pop')); if (s.follow) { add(tt(s.follow.at), 'pop'); add(tt(s.follow.at) + .6, 'click'); add(tt(s.follow.at) + .62, 'sparkle'); } if (s.endAt) { add(tt(s.endAt), 'blocks'); add(tt(s.endAt) + .2, 'chime'); } }
    if (s.type === 'chat' && window.chatCues) window.chatCues(s, add);
    const walk = items => (items || []).forEach(it => { const a = ttOr(it.at, s._t0); if (it.sound === false) return;
      if (it.kind === 'stamp') add(a - .05, 'stamp'); else if (it.kind === 'cross') add(a, 'stamp', { soft: 1 }); else if (['chip', 'card', 'icon', 'bullets', 'slot', 'text'].includes(it.kind)) add(a, 'pop'); else if (it.kind === 'media') add(a, 'blip');
      if (it.kind === 'timeline') (it.markers || []).forEach((m, k) => add(ttOr(m.at, a + .1 + k * .12), 'tick'));
      if (it.kind === 'phones' || it.kind === 'grid') (it.items || []).forEach((p, k) => add(ttOr(p.at, a + k * (it.kind === 'grid' ? .06 : .15)), 'whoosh2'));
      if (it.kind === 'slot' && it.spin) for (let k = 0; k < 12; k++) add(ttOr(it.spinAt, a + .4) + k * .09, 'tick');
      if (it.kind === 'bullets') (it.lines || []).forEach(ln => { if (ln && ln.at) add(tt(ln.at), 'tick'); }); });
    walk(s.items); walk(s.extras);
    if (s.type === 'chat') (s.split || []).forEach(sp => (sp.panels || []).forEach(pn => walk(pn.items)));
  });
  STEPS.forEach(s => { add(s._at, 'stamp', { soft: 1 }); add(s._at + .6, 'swish'); });
  (EP.cues || []).forEach(c => add(tt(c.at), c.type, c));
  return { dur: TL.dur, events: E.sort((a, b) => a.t - b.t), music: EP.music || {} };
};

// ---------- loading
window.DURATION = TL.dur;
window.ready = async () => {
  const imgs = { ...(EP.images || {}) }; if (EP.host && EP.host.image) imgs.host = EP.host.image; if (EP.brand && EP.brand.logo) imgs.logo = EP.brand.logo;
  await Promise.all(Object.entries(imgs).map(([k, src]) => new Promise(ok => { const i = new Image(); i.onload = () => { IMG[k] = i; ok(); }; i.onerror = () => { console.warn('missing image ' + src); ok(); }; i.src = src; })));
  await Promise.all(Object.entries(EP.media || {}).map(([k, src]) => new Promise(ok => { const v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.playsInline = true;
    v.addEventListener('loadeddata', () => { VIDS[k] = v; ok(); }, { once: true }); v.addEventListener('error', () => { console.warn('missing media ' + src); VIDS[k] = placeholder(k); ok(); }, { once: true }); v.src = src; })));
  prepare(); compileScenes(); if (window.chatReady) await window.chatReady(); return true;
};
