// Pixel Breakdown: the simulated agent chat (DOM layer), screenshotted together with the canvases.
// One chat scene per episode. Messages come from the scene's data; the camera follows the newest message; a split screen
// shrinks the recording into a window on the left while pixel panels explain on the right. Loaded after engine.js.
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
const CSS = `
#cam{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0}
.bw{position:absolute;inset:0;background:#dfe3e8}.tl{position:absolute;top:16px;width:12px;height:12px;border-radius:50%}.tl.r{left:20px;background:#ff5f57}.tl.y{left:40px;background:#febc2e}.tl.g{left:60px;background:#28c840}
.tab{position:absolute;left:92px;top:8px;width:320px;height:36px;background:#fff;border-radius:10px 10px 0 0;display:flex;align-items:center;gap:8px;padding:0 12px;font-size:13px;color:#3c4043;box-sizing:border-box}
.tab .fav{width:16px;height:16px;border-radius:4px;background:var(--acc);color:#fff;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center}.tab .x{margin-left:auto;color:#5f6368}
.bar{position:absolute;top:44px;left:0;right:0;height:46px;background:#fff;display:flex;align-items:center;gap:16px;padding:0 16px;box-sizing:border-box;border-bottom:1px solid #e3e3e3}
.nav{font-size:19px;color:#5f6368;width:20px;text-align:center}.omni{flex:1;height:32px;background:#f1f3f4;border-radius:16px;display:flex;align-items:center;padding:0 14px;gap:8px}.mz{image-rendering:pixelated}.prof{width:26px;height:26px;border-radius:50%;background:var(--acc)}
.view{position:absolute;top:90px;left:0;width:1920px;height:990px;overflow:hidden;background:#faf9f5}.chat{position:absolute;inset:0;display:flex}
.side{width:288px;background:#f5f4ee;border-right:1px solid #e8e6de;padding:18px 14px;box-sizing:border-box;position:relative}.brand{font-size:22px;font-weight:700;padding:4px 10px 18px;color:#3d3a32}
.sitem{font-size:15px;padding:8px 10px;border-radius:8px;color:#3d3a32}.sitem.on{background:#ebe8df}.sitem.new{color:var(--acc);font-weight:600}.sh2{font-size:12px;color:#8a877f;margin:22px 10px 6px}
.me{position:absolute;bottom:20px;left:14px;right:14px;display:flex;gap:10px;align-items:center;font-size:14px}.av{width:32px;height:32px;border-radius:50%;background:#3d3a32;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}
.main{flex:1;position:relative;overflow:hidden}.ctitle{position:absolute;top:16px;left:24px;font-size:15px;color:#3d3a32}.greet{position:absolute;top:300px;width:100%;text-align:center;font-size:38px;color:#3d3a32}
.col{position:absolute;left:50%;width:780px;margin-left:-390px;top:64px;bottom:170px;overflow:hidden}#msgs{position:absolute;left:0;right:0;top:0}
.composer{position:absolute;left:50%;width:780px;margin-left:-390px;background:#fff;border:1px solid #e3e0d6;border-radius:22px;box-shadow:0 4px 18px rgba(0,0,0,.05);padding:14px 16px 12px;box-sizing:border-box}
.atts{display:flex;gap:10px}.att{width:116px;height:88px;border-radius:10px;overflow:hidden;border:1px solid #e3e0d6;position:relative;background:#eee}.att img{width:100%;height:100%;object-fit:cover}
.att .fn{position:absolute;left:0;right:0;bottom:0;font-size:11px;color:#fff;background:linear-gradient(transparent,rgba(0,0,0,.65));padding:12px 7px 5px}
.ctext{font-size:17px;min-height:28px;padding:8px 2px;color:#29261b}.ctext .phl{color:#a39f95}.crow2{display:flex;align-items:center;gap:10px;font-size:14px;color:#6b6860}
.plus{width:32px;height:32px;border:1px solid #e3e0d6;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:18px}.tool{border:1px solid #e3e0d6;border-radius:9px;padding:5px 10px}
.model{margin-left:auto}.send{width:34px;height:34px;border-radius:9px;background:var(--acc);color:#fff;display:flex;align-items:center;justify-content:center;font-size:18px;opacity:.4}.send.on{opacity:1}
.fly{position:absolute;width:150px;height:112px;border-radius:12px;overflow:hidden;box-shadow:0 14px 34px rgba(0,0,0,.25);display:none}.fly img{width:100%;height:100%;object-fit:cover}
.m{margin:0 0 18px;display:none}.mu{display:none;flex-direction:column;align-items:flex-end;gap:8px;margin:0 0 22px}.bub{background:#f0eee6;border-radius:16px;padding:11px 16px;font-size:17px;max-width:560px}
.mc{font-size:17px;line-height:1.75;color:#29261b}.mc h4{font-size:17px;margin:4px 0 2px}.mc ul{margin:0;padding-left:22px}.mc li{margin:1px 0}
.trow{display:flex;align-items:center;gap:10px;border:1px solid #e7e4da;border-radius:12px;padding:10px 14px;font-size:15px;color:#3d3a32;background:#fdfcf9;margin:0 0 10px}
.trow .ti{width:18px;height:18px;border-radius:5px;background:var(--acc)}.trow .tn{font-family:Menlo,monospace;font-size:14px;color:#6b6860}.trow .st{margin-left:auto;color:#2f7a3c;font-size:14px}
.spin{margin-left:auto;width:16px;height:16px;border:2px solid #e3e0d6;border-top-color:var(--acc);border-radius:50%}
.tbl{display:grid;grid-template-columns:auto 1fr;border:1px solid #e7e4da;border-radius:12px;overflow:hidden;font-size:15px;margin-top:6px}.tbl div{padding:7px 14px;border-top:1px solid #f0eee8}.tbl .hd{background:#faf9f5;color:#8a877f;font-size:13px;border-top:0}
.tbl img{width:26px;height:26px;border-radius:6px;object-fit:cover;vertical-align:middle;margin-right:8px}code{background:#fbeee6;color:#b4532a;border-radius:5px;padding:1px 6px;font-family:Menlo,monospace;font-size:14px}
.qcard{border:1px solid #e7e4da;border-radius:14px;padding:12px 18px;background:#fdfcf9;font-size:15.5px;line-height:1.85;margin-top:6px}.qcard .k{color:#8a877f;display:inline-block;width:80px}.qcard .cost{font-size:22px;font-weight:700;color:var(--acc)}
.imgs{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}.imgs img{border-radius:10px;border:1px solid #e7e4da;object-fit:cover}
.w9{display:grid;grid-template-columns:repeat(3,1fr);gap:7px 18px;margin:8px 0 12px;font-size:13px}.w9 div{display:flex;align-items:center;gap:6px}.w9 .nm{width:62px;overflow:hidden;white-space:nowrap}
.w9 i.b{flex:1;height:6px;background:#efede6;border-radius:3px;overflow:hidden;position:relative}.w9 i.b b{position:absolute;left:0;top:0;bottom:0;background:var(--acc)}.w9 .ok{color:#2f7a3c;width:50px;font-size:12px}
.res{border:1px solid #e7e4da;border-radius:16px;overflow:hidden;padding:12px;background:#fff}.rv{display:flex;gap:6px}.rv video{border-radius:8px;object-fit:cover;background:#000}.cap{font-size:14px;color:#8a877f;margin-top:8px}
.dl{display:inline-block;background:#1a1915;color:#fff;padding:6px 14px;border-radius:9px;font-size:13px;font-weight:600;margin-left:10px}
.cursor{position:absolute;width:30px;height:38px;z-index:50}.ripple{position:absolute;border:3px solid var(--acc);border-radius:50%;z-index:49;display:none}`;
const ARROW = '<svg viewBox="0 0 30 38" width="30" height="38"><path d="M3 2 L3 30 L10 23 L15 35 L20 33 L15 21 L25 21 Z" fill="#111" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg>';
function mosaic(str, px, k, bgc, b = 8) {                        // a URL pixelated beyond reading: no readable link on screen
  const [c, g] = mk(8, 8), font = `${px}px sans-serif`; g.font = font; const w = Math.ceil(g.measureText(str).width / b) * b, h = Math.ceil(px * 1.35 / b) * b;
  c.width = w; c.height = h; g.fillStyle = bgc; g.fillRect(0, 0, w, h); g.font = font; g.fillStyle = k; g.textBaseline = 'middle'; g.fillText(str, 0, h / 2 + 1);
  const d = g.getImageData(0, 0, w, h).data, B = rgb(bgc);
  for (let y = 0; y < h; y += b) for (let x = 0; x < w; x += b) { const m = [0, 0, 0]; for (let yy = 0; yy < b; yy++) for (let xx = 0; xx < b; xx++) { const i = ((y + yy) * w + x + xx) * 4; for (let j = 0; j < 3; j++) m[j] += d[i + j]; } g.fillStyle = `rgb(${m.map((v, j) => clamp(B[j] + (v / b / b - B[j]) * 1.7, 0, 255) | 0).join(',')})`; g.fillRect(x, y, b, b); }
  return `<img class="mz" src="${c.toDataURL()}" width="${w}" height="${h}">`;
}
const msgHTML = m => {
  const id = esc(m.id), row = (name, st) => `<span class="ti"></span><span>${esc(m.tool || CH.app.tool || 'Tools')}</span><span class="tn">${esc(name)}</span>${st}`;
  if (m.role === 'user') return `<div id="${id}" class="mu">${m.attachments ? `<div class="atts">${m.attachments.map(a => `<div class="att"><img src="${esc(a.thumb)}"><div class="fn">${esc(a.name)}</div></div>`).join('')}</div>` : ''}<div class="bub" id="${id}-b">${esc(m.text)}</div></div>`;
  if (m.role === 'assistant') return `<div id="${id}" class="m mc"></div>`;
  if (m.role === 'tool') return `<div id="${id}" class="m trow">${row(m.name + (m.detail ? ' · ' + m.detail : ''), m.doneAt ? `<span id="${id}-s" class="spin"></span>` : `<span class="st">${esc(m.status || '✓')}</span>`)}</div>`;
  if (m.role === 'list') return `<div id="${id}" class="m mc">${m.title ? `<h4>${esc(m.title)}</h4>` : ''}<ul>${m.items.map((x, j) => `<li id="${id}-i${j}">${esc(x)}</li>`).join('')}</ul></div>`;
  if (m.role === 'table') return `<div id="${id}" class="m mc">${m.title ? `<h4>${esc(m.title)}</h4>` : ''}${m.text ? esc(m.text) : ''}<div class="tbl" id="${id}-t">${(m.head || []).map(h => `<div class="hd">${esc(h)}</div>`).join('')}${m.rows.map((r, j) => `<div id="${id}-r${j}">${r[2] ? `<img src="${esc(r[2])}">` : ''}${r[0].startsWith('{{') ? `<code>${esc(r[0])}</code>` : esc(r[0])}</div><div id="${id}-v${j}">${esc(r[1])}</div>`).join('')}</div></div>`;
  if (m.role === 'images') return `<div id="${id}" class="m mc">${esc(m.text || '')}<div class="imgs">${m.images.map(src => `<img src="${esc(src)}" style="width:${m.size || 300}px">`).join('')}</div></div>`;
  if (m.role === 'quote') return `<div id="${id}" class="m mc"><h4>${esc(m.title || 'Before I generate')}</h4><div class="qcard">${m.rows.map((r, j) => `<div id="${id}-r${j}"><span class="k">${esc(r[0])}</span>${j === m.costRow ? `<span class="cost">${esc(r[1])}</span>` : esc(r[1])}</div>`).join('')}${m.note ? `<div id="${id}-n">${esc(m.note)}</div>` : ''}</div></div>`;
  if (m.role === 'progress') return `<div id="${id}" class="m"><div class="trow" style="margin:0">${row(m.name || 'wait', `<span id="${id}-s" class="st">${esc(m.runLabel || 'Running…')}</span>`)}</div><div class="w9" id="${id}-g" style="grid-template-columns:repeat(${Math.min(3, m.items.length)},1fr)">${m.items.map((x, j) => `<div><span class="nm">${esc(x.label)}</span><i class="b"><b id="${id}-w${j}"></b></i><span class="ok" id="${id}-k${j}"></span></div>`).join('')}</div></div>`;
  if (m.role === 'result') { const vids = m.videos || [m.video], n = vids.length, vw = n > 1 ? Math.min(150, R((740 - (n - 1) * 6) / n)) : 176;
    return `<div id="${id}" class="m"><div class="trow">${row(m.name || 'show_result', `<span class="st">${esc(m.status || '✓')}</span>`)}</div><div class="res"><div class="rv">${vids.map(v => `<video class="rvid" muted playsinline preload="auto" src="${esc(EP.media[v])}" style="width:${vw}px;height:${R(vw * (m.landscape ? 9 / 16 : 16 / 9))}px"></video>`).join('')}</div><div class="cap">${esc(m.caption || '')}${m.download ? `<span class="dl" id="${id}-d">${esc(m.download)}</span>` : ''}</div></div></div>`; }
  throw new Error('unknown chat message role ' + m.role);
};
let CH = null, T = {}, CAM = { s: 1, tx: 0, ty: 0 }, CALL = [];
const VP = { x: 0, y: 0, w: 1920, h: 1080, k: 0 }, VPF = { x: 36, y: 148, w: 712, h: 760 };
window.chatScene = function (s) {
  if (CH) throw new Error('only one chat scene per episode'); CH = s; s.app = s.app || {};
  const M = s.messages.map(m => ({ ...m, _at: ttOr(m.at, ttOr(m.sendAt, s._t0)) })), first = M.find(m => m.role === 'user');
  s._M = M; s._send = first ? tt(first.sendAt) : s._t0; s._split = (s.split || []).map(sp => ({ ...sp, _from: tt(sp.from), _to: tt(sp.to), panels: (sp.panels || []).map(pn => ({ ...pn, _from: ttOr(pn.from, tt(sp.from) + .3), _to: ttOr(pn.to, tt(sp.to)), items: compileItems(pn.items, ttOr(pn.from, tt(sp.from) + .3)) })) }));
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st); UIROOT.style.setProperty('--acc', EP.accent || '#d97757');
  const app = s.app, urls = [app.url || 'app.example.com/new', app.url2 || 'app.example.com/chat/8d1f02a7'];
  UIROOT.innerHTML = `<div id="cam"><div class="bw"><span class="tl r"></span><span class="tl y"></span><span class="tl g"></span>
   <div class="tab"><span class="fav">${esc((app.name || 'A')[0])}</span><span id="tabt"></span><span class="x">×</span></div>
   <div class="bar"><span class="nav">←</span><span class="nav">→</span><span class="nav">↻</span><div class="omni"><span id="url">${urls.map((u, j) => mosaic(u, 15, '#202124', '#f1f3f4').replace('<img', `<img data-k="${j}"`)).join('')}</span></div><span class="prof"></span></div>
   <div class="view" id="view"><div class="chat"><div class="side"><div class="brand">${esc(app.name || 'Agent')}</div><div class="sitem new">＋ ${esc(app.newChat || 'New chat')}</div>
    <div class="sh2">${esc(app.recentLabel || 'Recent')}</div><div class="sitem on" id="cur"></div>${(app.sidebar || []).map(x => `<div class="sitem">${esc(x)}</div>`).join('')}
    <div class="me"><span class="av">${esc((app.user || 'You')[0])}</span><div><b>${esc(app.user || 'You')}</b></div></div></div>
    <div class="main" id="main"><div class="ctitle" id="ctitle"></div><div class="greet" id="greet">${esc(app.greeting || '')}</div><div class="col" id="col"><div id="msgs">${M.map(msgHTML).join('')}</div></div>
     <div class="composer" id="comp"><div id="atts" class="atts" style="display:none;margin-bottom:8px">${first && first.attachments ? first.attachments.map(a => `<div class="att"><img src="${esc(a.thumb)}"><div class="fn">${esc(a.name)}</div></div>`).join('') : ''}</div><div id="ctext" class="ctext"></div>
      <div class="crow2"><span class="plus">+</span>${app.tool ? `<span class="tool">${esc(app.tool)}</span>` : ''}<span class="model">${esc(app.model || '')} ⌄</span><span id="send" class="send">↑</span></div></div></div></div>
    ${first && first.attachments ? first.attachments.slice(0, 3).map((a, j) => `<div id="fly${j}" class="fly"><img src="${esc(a.thumb)}"></div>`).join('') : ''}</div></div>
   <div id="ripple" class="ripple"></div><div id="cursor" class="cursor">${ARROW}</div></div>`;
  return t => ({ base: c => chatBase(c, t), media: chatMedia(t), top: c => chatTop(c, t), ui: () => chatFrame(t), callouts: c => { calloutsDraw(c, t); skipBadge(c, t); } });
};
window.chatReady = async () => {
  if (!CH) return; await Promise.all([...UIROOT.querySelectorAll('img')].map(i => i.decode().catch(() => {})));
  await Promise.all([...UIROOT.querySelectorAll('video')].map(v => new Promise(ok => { if (v.readyState >= 2) return ok(); v.addEventListener('loadeddata', ok, { once: true }); v.addEventListener('error', ok, { once: true }); v.load(); })));
};
const disp = (id, on, how = 'block') => { const e = $(id); if (e) e.style.display = on ? how : 'none'; };
const vis = (id, on) => { const e = $(id); if (e) e.style.visibility = on ? 'visible' : 'hidden'; };
function grow(id, t, t0, how = 'block') { const el = $(id), on = t > t0; el.style.display = on ? how : 'none'; if (!on) return; const p = eo(clamp((t - t0) / .25)); if (p < 1) { el.style.overflow = 'hidden'; el.style.maxHeight = R(p * el.scrollHeight) + 'px'; } else { el.style.overflow = ''; el.style.maxHeight = 'none'; } }
function setCam(s, fx, fy, sx = 960, sy = 540, vw = 1920, vh = 1080, top = 0) { CAM = { s, tx: clamp(sx - fx * s, vw - 1920 * s, 0), ty: clamp(sy - fy * s, vh - 1080 * s, -top * s) }; $('cam').style.transform = `translate(${CAM.tx}px, ${CAM.ty}px) scale(${s})`; }
const rectOf = id => { const e = $(id); if (!e) return null; const r = e.getBoundingClientRect(), o = UIROOT.getBoundingClientRect(); return { x: (r.left - o.left - CAM.tx) / CAM.s, y: (r.top - o.top - CAM.ty) / CAM.s, w: r.width / CAM.s, h: r.height / CAM.s }; };
const ctr = r => [r.x + r.w / 2, r.y + r.h / 2];
function keys(K, t) { if (t <= K[0][0]) return K[0].slice(1); for (let i = 0; i + 1 < K.length; i++) { const a = K[i], b = K[i + 1]; if (t < b[0]) { const p = eio(seg(t, a[0], b[0])); return a.slice(1).map((v, k) => v + (b[k + 1] - v) * p); } } return K[K.length - 1].slice(1); }
const typedS = (s, t, t0, cps) => [...String(s)].slice(0, Math.max(0, Math.floor((t - t0) * cps))).join('');
const splitK = t => { let k = 0; for (const sp of CH._split) k = Math.max(k, eio(seg(t, sp._from, sp._from + .45)) * (1 - eio(seg(t, sp._to, sp._to + .45)))); return k; };
function vpAt(t) { const k = splitK(t), f = (a, b) => R((a + (b - a) * k) / 4) * 4; return { x: f(0, VPF.x), y: f(0, VPF.y), w: f(1920, VPF.w), h: f(1080, VPF.h), k }; }
async function chatFrame(t) {
  CALL.length = 0; const s = CH, M = s._M, sent = t > s._send;
  ['cursor', 'ripple', 'fly0', 'fly1', 'fly2'].forEach(id => disp(id, false));
  Object.assign(VP, vpAt(t)); Object.assign(UIROOT.style, { left: VP.x + 'px', top: VP.y + 'px', width: VP.w + 'px', height: VP.h + 'px' });
  for (const e of $('url').children) e.style.display = +e.dataset.k === (sent ? 1 : 0) ? 'inline-block' : 'none';
  $('tabt').textContent = (sent ? (s.app.title || s.app.name || 'Chat') : (s.app.newChat || 'New chat')) + ' – ' + (s.app.name || 'Agent');
  setCam(1, 960, 540);
  const comp = $('comp'), main = $('main'), first = M.find(m => m.role === 'user');
  disp('greet', !sent); $('ctitle').textContent = sent ? (s.app.title || '') + ' ⌄' : ''; $('cur').textContent = sent ? (s.app.title || '') : (s.app.newChat || 'New chat');
  const dock = eio(seg(t, s._send, s._send + .3)), top0 = 400, top1 = main.clientHeight - 24 - comp.offsetHeight; comp.style.top = R(top0 + (top1 - top0) * dock) + 'px';
  // composer: the first user message is dragged in and typed; later user messages are typed into the docked composer
  let ctext = '', on = false, cur = null; const clicks = [], cr0 = rectOf('comp'), vr = rectOf('view');
  const dropAt = first && first.dropAt ? tt(first.dropAt) : null; disp('atts', first && first.attachments && dropAt !== null && t > dropAt && !sent, 'flex');
  for (const m of M) if (m.role === 'user' && m.typeAt) { const ta = tt(m.typeAt), sa = tt(m.sendAt); if (t > ta && t < sa) { ctext = typedS(m.text, t, ta, m.cps || 9); on = true; } }
  $('ctext').innerHTML = ctext ? esc(ctext) : `<span class="phl">${esc(sent ? (s.app.replyHint || 'Reply…') : (s.app.placeholder || 'What do you want to make?'))}</span>`; $('send').className = on ? 'send on' : 'send';
  if (dropAt !== null && first.attachments) first.attachments.slice(0, 3).forEach((a, j) => { const f0 = dropAt - .6, fp = eio(seg(t, f0, dropAt)), live = t > f0 && t < dropAt; disp('fly' + j, live); if (live) { const x0 = 1760 + j * 40, y0 = 760 + j * 30, x1 = cr0.x - vr.x + 16 + j * 126, y1 = cr0.y - vr.y + 14; Object.assign($('fly' + j).style, { left: R(x0 + (x1 - x0) * fp) + 'px', top: R(y0 + (y1 - y0) * fp) + 'px', transform: `rotate(${(1 - fp) * (j % 2 ? 6 : -4)}deg)` }); } });
  // messages unfold in order
  for (const m of M) {
    const id = m.id, at = m._at;
    if (m.role === 'user') { grow(id, t, tt(m.sendAt), 'flex'); continue; }
    if (m.role === 'assistant') { grow(id, t, at); $(id).textContent = typedS(m.text, t, at, m.cps || 30); continue; }
    if (m.role === 'tool') { grow(id, t, at, 'flex'); if (m.doneAt) { const d = t > tt(m.doneAt), e = $(id + '-s'); e.className = d ? 'st' : 'spin'; e.textContent = d ? (m.doneLabel || '✓') : ''; } continue; }
    grow(id, t, at);
    if (m.role === 'list') m.items.forEach((x, j) => vis(`${id}-i${j}`, t > at + .15 + j * (m.step ?? .15)));
    if (m.role === 'table') m.rows.forEach((r, j) => { const on_ = t > at + .2 + j * (m.step ?? .12); vis(`${id}-r${j}`, on_); vis(`${id}-v${j}`, on_); });
    if (m.role === 'quote') { m.rows.forEach((r, j) => vis(`${id}-r${j}`, t > at + .15 + j * (m.step ?? .25))); vis(`${id}-n`, t > at + .15 + m.rows.length * (m.step ?? .25)); }
    if (m.role === 'progress') { const sk = ttOr(m.skipAt, at + 4), dn = ttOr(m.doneAt, sk + .9), mx = Math.max(...m.items.map(x => x.minutes || 1)), mins = t < sk ? seg(t, at, at + 4) * mx * .07 : mx * .07 + (mx * 1.01 - mx * .07) * eio(seg(t, sk, dn));
      m.items.forEach((x, j) => { const f = clamp(mins / (x.minutes || mx)); $(`${id}-w${j}`).style.width = R(f * 100) + '%'; $(`${id}-k${j}`).textContent = f >= 1 ? '✓ ' + (x.done || '') : ''; }); $(id + '-s').textContent = t > dn ? (m.doneLabel || '✓ Done') : (m.runLabel || 'Running…'); }
    if (m.role === 'result' && t > at) { const st0 = m.mt ?? 1, span = m.loop ?? 8; for (const v of $(id).querySelectorAll('video')) await seekTo(v, st0 + (t - at) % span); }
  }
  // camera: composer close-up before the first send, then follow the newest content; the split screen frames the column
  const col_ = $('col'), msgs = $('msgs'); msgs.style.transform = `translateY(${-Math.max(0, msgs.scrollHeight - col_.clientHeight)}px)`;
  const cr = rectOf('comp'), [ccx] = ctr(cr), mr = rectOf('msgs'), cl = rectOf('col'), fb = Math.min(mr.y + mr.h, cl.y + cl.h), pre = [ccx, cr.y + cr.h / 2];
  let cam = !sent ? [1.6, pre[0], pre[1], 960, 540] : (() => { const d = eio(seg(t, s._send, s._send + .35)); return [1.6, pre[0], pre[1] + (fb - pre[1]) * d, 960, 540 + 150 * d]; })();
  if (VP.k > 0) { const cs = [.9, ccx, fb, VPF.w / 2, VPF.h - 140]; cam = cam.map((a, i) => a + (cs[i] - a) * VP.k); }
  const res = [...M].reverse().find(m => m.role === 'result' && t > m._at - .1); if (res && VP.k < .5) { const rr = rectOf(res.id), z = eio(seg(t, res._at, res._at + .4)); cam = [cam[0] + (res.zoom ?? .08) * z, cam[1], cam[2] + (rr.y + rr.h / 2 - cam[2]) * z, 960, cam[4] + (520 - cam[4]) * z]; }
  // cursor: drags the attachments, presses send for every user message
  const ar = rectOf('send'), [sx, sy] = ctr(ar);
  for (const m of M) if (m.role === 'user') { const sa = tt(m.sendAt), from = m === first && dropAt !== null ? dropAt - .8 : (m.typeAt ? tt(m.typeAt) : sa - .6); if (t > from && t < sa + .45) { cur = m === first && dropAt !== null ? keys([[dropAt - .8, 1760 + vr.x + 70, 760 + vr.y + 50], [dropAt, cr0.x + 120, cr0.y + 50], [sa - .25, sx + 4, sy + 4]], t) : [sx + 4, sy + 4]; clicks.push(sa); } }
  for (const c of s.callouts || []) { const f = tt(c.from), to = ttOr(c.to, f + 1.2); if (t < f || t > to) continue; const [mid, sub] = c.target.split('.'), r = rectOf(sub ? `${mid}-${sub}` : mid); if (r) CALL.push([r, VP.k > .5 ? null : c.label]); }
  setCam(...cam, VP.w, VP.h, 90 * VP.k);
  disp('cursor', !!cur); if (cur) Object.assign($('cursor').style, { left: R(cur[0] - 3) + 'px', top: R(cur[1] - 2) + 'px' });
  const ck = clicks.filter(c => t >= c && t < c + .35).pop(); disp('ripple', ck !== undefined && !!cur);
  if (ck !== undefined && cur) { const q = (t - ck) / .35, r = 8 + 34 * q; Object.assign($('ripple').style, { left: cur[0] - r + 'px', top: cur[1] - r + 'px', width: 2 * r + 'px', height: 2 * r + 'px', opacity: 1 - q }); }
  for (const c of CALL) { const r = c[0], x0 = Math.max(r.x * CAM.s + CAM.tx, 14), y0 = Math.max(r.y * CAM.s + CAM.ty, 14), x1 = Math.min((r.x + r.w) * CAM.s + CAM.tx, VP.w - 14), y1 = Math.min((r.y + r.h) * CAM.s + CAM.ty, VP.h - 14); c[0] = { x: VP.x + x0, y: VP.y + y0, w: x1 - x0, h: y1 - y0 }; }
}
function calloutsDraw(c, t) {
  for (const [r, label] of CALL) { if (r.w <= 0 || r.h <= 0) continue; const x = Math.floor(r.x / 4) - 3, y = Math.floor(r.y / 4) - 3, w = Math.ceil(r.w / 4) + 6, h = Math.ceil(r.h / 4) + 6; outlineBox(c, x, y, w, h, t);
    if (label) { const lw = tw(label) + 10, ly = y - 18 >= 0 ? y - 18 : y + h + 2; box(c, x, ly, lw, 16, C.accent, C.ink); text(c, label, x + 5, ly - 1, C.white); } }
}
function skipBadge(c, t) {
  for (const m of CH._M) { if (m.role !== 'progress' || !m.skipLabel) continue; const t0 = ttOr(m.skipAt, m._at + 4); if (t < t0 || t > t0 + 1.1) continue; const y = popY(t, t0, 14) || 0, w = Math.max(144, tw(m.skipLabel) + 50);
    box(c, R(240 - w / 2), 40 - y, w, 34, C.accent, C.ink); for (let k = 0; k < 2; k++) poly(c, [[R(240 - w / 2) + 16 + k * 10, 48 - y], [R(240 - w / 2) + 24 + k * 10, 57 - y], [R(240 - w / 2) + 16 + k * 10, 66 - y]], C.white); text(c, m.skipLabel, 252, 47 - y, C.white, { align: 'center' }); }
}
// split screen: a recording window on the left, pixel panels (windows of items) on the right
const gone = t => { let g = 0; for (const sp of CH._split) if (t > sp._to - .1 && t < sp._to + .6) g = R(230 * eio(seg(t, sp._to - .1, sp._to + .25))); return g; };
const livePanels = t => { const out = []; for (const sp of CH._split) if (t >= sp._from && t < sp._to + .5) for (const pn of sp.panels) if (t >= pn._from - .001 && t < pn._to + (pn._to >= sp._to ? .5 : 0)) out.push(pn); return out; };
function shifted(items, dy) { return dy ? items.map(it => ({ ...it, y: (it.y ?? 120) + dy, ...(it.kind === 'boxes' ? { y: it.y + dy } : {}) })) : items; }
function chatBase(c, t) {
  const v = vpAt(t); if (v.k <= 0) { rect(c, 0, 0, W, H, C.black); return; }
  bg(c, 'dark'); const x = v.x / 4, y = v.y / 4, w = v.w / 4, h = v.h / 4, bar = R(16 * v.k);
  c.globalAlpha = .35; rect(c, x + 3, y - bar + 3, w, h + bar, C.black); c.globalAlpha = 1; rect(c, x - 1, y - bar - 1, w + 2, h + bar + 2, C.ink);
  if (bar >= 12) { rect(c, x, y - bar, w, bar, C.dark2); if (Math.floor(t * 2.5) % 2 === 0) disc(c, x + 9, y - 9, 3, '#e5433a'); else ring(c, x + 9, y - 9, 3, '#e5433a'); text(c, CH.app.recLabel || 'REC', x + 17, y - 18, C.soft); }
  if (v.k < .9) return; const dy = gone(t);
  for (const pn of livePanels(t)) { if (pn.window) { const out = seg(t, pn._to, pn._to + .12); if (!win(c, 196, 20 + dy, 276, 208, pn.title || '', out > 0 ? { dark: true, p: 1 - out, lin: true } : { dark: true, p: seg(t, pn._from, pn._from + .25) })) continue; } else if (pn.title) text(c, pn.title, 334, 22 + dy, C.white, { align: 'center' }); const o = itemsScene(shifted(pn.items, dy), t); o.base.forEach(f => f(c)); }
}
function chatMedia(t) { const v = vpAt(t); if (v.k < .9) return []; const dy = gone(t), M = []; for (const pn of livePanels(t)) { if (pn.window && (t < pn._from + .25 || t > pn._to)) continue; M.push(...itemsScene(shifted(pn.items, dy), t).media); } return M; }
function chatTop(c, t) { const v = vpAt(t); if (v.k < .9) return; const dy = gone(t); for (const pn of livePanels(t)) { if (pn.window && (t < pn._from + .25 || t > pn._to)) continue; itemsScene(shifted(pn.items, dy), t).top.forEach(f => f(c)); } }
// sound cues for the chat (called from engine CUES)
window.chatCues = (s, add) => {
  for (const m of s._M) {
    if (m.role === 'user') { if (m.dropAt) { add(tt(m.dropAt) - .6, 'whoosh'); add(tt(m.dropAt), 'pop'); } if (m.typeAt) { const ta = tt(m.typeAt), n = [...m.text].length; for (let k = 0; k < n; k += 2) add(ta + k / (m.cps || 9), 'type'); } add(tt(m.sendAt), 'click'); add(tt(m.sendAt) + .05, 'swish'); }
    else if (m.role === 'tool') { add(m._at, 'blip'); if (m.doneAt) add(tt(m.doneAt), 'ding'); }
    else if (m.role === 'list') m.items.forEach((x, j) => add(m._at + .15 + j * (m.step ?? .15), 'tick'));
    else if (m.role === 'table') m.rows.forEach((r, j) => add(m._at + .2 + j * (m.step ?? .12), 'pop'));
    else if (m.role === 'quote') { add(m._at, 'pop'); if (m.costRow !== undefined) add(m._at + .15 + m.costRow * (m.step ?? .25), 'count', { dur: .4 }); }
    else if (m.role === 'progress') { const sk = ttOr(m.skipAt, m._at + 4); add(m._at, 'blip'); if (m.skipLabel) add(sk, 'whoosh'); add(ttOr(m.doneAt, sk + .9), 'ding'); }
    else if (m.role === 'result') add(m._at, 'chime');
    else add(m._at, 'pop');
  }
  for (const sp of s._split) { add(sp._from, 'swish'); add(sp._to, 'swish'); sp.panels.forEach(pn => add(pn._from, 'swish')); }
};
