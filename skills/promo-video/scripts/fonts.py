#!/usr/bin/env python3
"""Typography toolkit for promo films: curated catalogue → fetch → proposal sheet → subset.

  fonts.py list [--tone warm] [--script zh|ja|latin] [--role display|text|mono]
  fonts.py pairs [--tone warm]
  fonts.py similar "Söhne"                          # commercial font → free look-alikes in the catalogue
  fonts.py fetch fraunces manrope --to <project>   # cache, copy into <project>/public/fonts/<id>/, write fonts.json
  fonts.py specimen --pair warm-soft --pair tech-precise --combo gloock+inter \\
      --title "From answers to outcomes." --sub "..." --body "..." [--zh "..."] [--ja "..."] --out proposal.png
  fonts.py subset <project> --text-file copy.txt    # CJK / large OFL fonts → woff2 with only the characters used

Licences (see references/typography.md): OFL / Apache fonts may be subset. Fontshare (ITF FFL 2.0) fonts are free
for video, ads and broadcast, but must NOT be subset or format-converted and must NOT be handed to third parties:
they are fetched per machine and copied untouched. Fonts in the catalogue's "manual" list are never auto-downloaded.
"""
import argparse, html, io, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request, zipfile

if sys.platform == "win32":  # a pipe gets the ANSI code page, which cannot hold CJK copy or emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(SKILL, "assets", "fonts", "catalog.json")
CACHE = os.path.expanduser("~/.cache/promo-video/fonts")
UA = {"User-Agent": "Mozilla/5.0 (promo-video fonts.py)"}


def cat():
    return json.load(open(CATALOG, encoding="utf-8"))


def by_id():
    return {f["id"]: f for f in cat()["fonts"]}


def get(url, dest=None, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                data = r.read()
            if dest:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                open(dest, "wb").write(data)
            return data
        except Exception as e:  # noqa: BLE001
            if k == tries - 1:
                raise RuntimeError(f"download failed: {url}: {e}")
            time.sleep(1.5 * (k + 1))


def fetch_one(f):
    """Download a catalogue font into the cache; returns local file paths (fonts only)."""
    d = os.path.join(CACHE, f["id"])
    done = os.path.join(d, ".done")
    if os.path.exists(done):
        return json.load(open(done, encoding="utf-8"))
    os.makedirs(d, exist_ok=True)
    s = f["source"]
    out = []
    if s["type"] == "gf":
        base = f"https://raw.githubusercontent.com/google/fonts/main/{s['dir']}/"
        for name in s["files"]:
            p = os.path.join(d, name)
            get(base + urllib.parse.quote(name), p)
            out.append(p)
        for lic in ("OFL.txt", "LICENSE.txt", "UFL.txt"):
            try:
                get(base + lic, os.path.join(d, lic))
                break
            except RuntimeError:
                pass
    elif s["type"] == "fontshare":
        z = zipfile.ZipFile(io.BytesIO(get(f"https://api.fontshare.com/v2/fonts/download/{s['slug']}")))
        names = z.namelist()
        pick = [n for n in names if re.search(r"/Fonts/WEB/fonts/[^/]*-Variable(Italic)?\.woff2$", n)]
        if not pick:
            pick = [n for n in names if re.search(r"/Fonts/WEB/fonts/[^/]*\.woff2$", n)]
        if not pick:
            pick = [n for n in names if n.lower().endswith((".otf", ".ttf"))]
        for n in pick + [n for n in names if re.search(r"(?i)license/.*\.(txt|pdf)$", n)]:
            p = os.path.join(d, os.path.basename(n))
            open(p, "wb").write(z.read(n))  # untouched: FFL forbids conversion / subsetting
            if n in pick:
                out.append(p)
    elif s["type"] == "url":
        data = get(s["url"])
        if s["url"].lower().endswith(".zip"):
            z = zipfile.ZipFile(io.BytesIO(data))
            for n in z.namelist():
                if re.search(s["pattern"], n) or re.search(r"(?i)(^|/)(ofl|license)[^/]*\.(txt|md)$", n):
                    p = os.path.join(d, os.path.basename(n))
                    open(p, "wb").write(z.read(n))
                    if re.search(s["pattern"], n):
                        out.append(p)
        else:
            p = os.path.join(d, os.path.basename(urllib.parse.urlparse(s["url"]).path))
            open(p, "wb").write(data)
            out.append(p)
    if not out:
        raise RuntimeError(f"no font files found for {f['id']}")
    json.dump(out, open(done, "w", encoding="utf-8"))
    return out


def meta(path):
    from fontTools.ttLib import TTFont

    t = TTFont(path, lazy=True, fontNumber=0)
    axes = {a.axisTag: [a.minValue, a.defaultValue, a.maxValue] for a in t["fvar"].axes} if "fvar" in t else {}
    os2 = t["OS/2"]
    sub = (t["name"].getDebugName(17) or t["name"].getDebugName(2) or "").lower()
    italic = bool(os2.fsSelection & 1) or "italic" in sub or "oblique" in sub or "italic" in os.path.basename(path).lower()
    w = f"{int(axes['wght'][0])} {int(axes['wght'][2])}" if "wght" in axes else str(os2.usWeightClass)
    st = f"{axes['wdth'][0]:g}% {axes['wdth'][2]:g}%" if "wdth" in axes else None
    return {"axes": axes, "weight": w, "style": "italic" if italic else "normal", "stretch": st}


def cmd_fetch(a):
    fonts = by_id()
    man_path = os.path.join(a.to, "public", "fonts", "fonts.json") if a.to else None
    manifest = json.load(open(man_path, encoding="utf-8")) if man_path and os.path.exists(man_path) else []
    for fid in a.ids:
        f = fonts.get(fid)
        if not f:
            sys.exit(f"unknown font id: {fid} (try: fonts.py list)")
        files = fetch_one(f)
        print(f"{fid}: {len(files)} file(s) cached · {f['license']}{'' if f['subset_ok'] else ' · no subsetting'}")
        if not a.to:
            continue
        dst = os.path.join(a.to, "public", "fonts", fid)
        os.makedirs(dst, exist_ok=True)
        for src in os.listdir(os.path.dirname(files[0])):
            if src.startswith("."):
                continue
            shutil.copy2(os.path.join(os.path.dirname(files[0]), src), os.path.join(dst, src))
        manifest = [m for m in manifest if m["id"] != fid]
        for p in files:
            m = meta(p)
            manifest.append({"id": fid, "family": f["family"], "file": f"fonts/{fid}/{os.path.basename(p)}", **m, "license": f["license"], "subset_ok": f["subset_ok"], "scripts": f["scripts"]})
    if man_path:
        json.dump(manifest, open(man_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        lic = ["# Fonts in this project", "", "| font | licence | notes |", "|---|---|---|"]
        for fid in sorted({m["id"] for m in manifest}):
            f = fonts.get(fid, {})
            note = "free for video/ads/broadcast; do not subset, convert or pass the files to third parties" if f.get("license", "").startswith("ITF") else "open licence"
            lic.append(f"| {f.get('family', fid)} | {f.get('license', '?')} | {note} |")
        open(os.path.join(a.to, "public", "fonts", "LICENSES.md"), "w", encoding="utf-8").write("\n".join(lic) + "\n")
        print(f"manifest: {man_path} ({len(manifest)} faces)")


def cmd_subset(a):
    from fontTools import subset as fts

    man_path = os.path.join(a.project, "public", "fonts", "fonts.json")
    manifest = json.load(open(man_path, encoding="utf-8"))
    text = open(a.text_file, encoding="utf-8").read() if a.text_file else (a.text or "")
    chars = set(text) | set(" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~") | set("，。！？、：；“”‘’（）《》〈〉【】…—·「」『』・ー")
    for m in manifest:
        big = any(s in ("zh-Hans", "ja") for s in m.get("scripts", [])) or a.all
        if not big:
            continue
        if not m["subset_ok"]:
            print(f"skip {m['id']}: licence forbids subsetting")
            continue
        src = os.path.join(a.project, "public", m.get("subset_of", m["file"]))
        base = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(os.path.dirname(src), base + ".subset.woff2")
        opts = fts.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        ft = fts.load_font(src, opts)
        sub = fts.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)))
        sub.subset(ft)
        fts.save_font(ft, out, opts)
        m.setdefault("subset_of", m["file"])
        m["file"] = os.path.relpath(out, os.path.join(a.project, "public"))
        print(f"{m['id']}: {os.path.getsize(src) // 1024} KB → {os.path.getsize(out) // 1024} KB ({len(chars)} chars)")
    json.dump(manifest, open(man_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cmd_list(a):
    c = cat()
    for f in c["fonts"]:
        if a.tone and a.tone not in f["tones"]:
            continue
        if a.script and not any(s.startswith(a.script) for s in f["scripts"]):
            continue
        if a.role and a.role not in f["roles"]:
            continue
        name = f["family"] + (f" · {f['native']}" if f.get("native") else "")
        print(f"{f['id']:24s} {name:34s} {','.join(f['tones']):28s} {f['license']:11s} {'' if f['subset_ok'] else 'no-subset'}")
        if a.verbose:
            print(f"{'':24s} {f['note']}")


def cmd_pairs(a):
    c = cat()
    fonts = by_id()
    for p in c["pairings"]:
        if a.tone and p["tone"] != a.tone:
            continue
        acc = f" + {fonts[p['accent']]['family']}" if p.get("accent") else ""
        print(f"{p['id']:18s} [{c['tones'][p['tone']]}] {fonts[p['display']]['family']} × {fonts[p['text']]['family']}{acc}")
        print(f"{'':18s} 中文 {fonts[p['zh'][0]].get('native', fonts[p['zh'][0]]['family'])} × {fonts[p['zh'][1]].get('native', fonts[p['zh'][1]]['family'])}   日本語 {fonts[p['ja'][0]]['family']} × {fonts[p['ja'][1]]['family']}")
        print(f"{'':18s} {p['why']}")


def cmd_similar(a):
    c = cat()
    fonts = by_id()
    q = a.name.lower()
    hits = [(k, v) for k, v in c["similar"].items() if any(q in part.strip().lower() or part.strip().lower() in q for part in k.split("/"))]
    if not hits:
        print("no mapping; browse: fonts.py list --tone <tone>")
    for k, v in hits:
        print(f"{k}:")
        for fid in v:
            f = fonts[fid]
            print(f"  {fid:22s} {f['family']:22s} {f['license']:11s} {f['note']}")


# ── specimen: a font proposal sheet with the film's real copy, rendered by headless Chrome ──
def chrome():
    """Chrome, Chromium or Edge (all take --headless --screenshot), else a headless shell Remotion or Playwright downloaded."""
    home = os.path.expanduser("~")
    env = lambda k: os.environ.get(k) or ""  # noqa: E731
    installed = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        *(os.path.join(base, *rel) for base in (env("ProgramFiles"), env("ProgramFiles(x86)"), env("LOCALAPPDATA")) if base
          for rel in (("Google", "Chrome", "Application", "chrome.exe"), ("Microsoft", "Edge", "Application", "msedge.exe"))),
        *(shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge")),
    ]
    for c in [env("PROMO_CHROME"), *installed]:
        if c and os.path.isfile(c):
            return c
    names = ("chrome-headless-shell", "chrome-headless-shell.exe", "headless_shell", "headless_shell.exe")
    caches = [os.path.join(home, d) for d in ("Documents", "Downloads", "Desktop", "Projects", "projects")] + [
        os.path.join(home, ".cache", "ms-playwright"), os.path.join(home, "Library", "Caches", "ms-playwright"),
        os.path.join(env("LOCALAPPDATA"), "ms-playwright") if env("LOCALAPPDATA") else ""]
    for root in filter(os.path.isdir, caches):
        for d, dirs, files in os.walk(root):
            if d[len(root):].count(os.sep) >= 6:
                dirs[:] = []
            hit = next((f for f in files if f in names), None)
            if hit:
                return os.path.join(d, hit)
    sys.exit("no Chrome found (set PROMO_CHROME to Chrome, Chromium or Edge)")


DEFAULT_VAR = {
    "fraunces": "'SOFT' 100, 'WONK' 1, 'opsz' 144",
    "bricolage-grotesque": "'opsz' 96, 'wdth' 88",
    "mona-sans": "'wdth' 112",
    "anybody": "'wdth' 125",
    "archivo": "'wdth' 112",
    "newsreader": "'opsz' 72",
    "bodoni-moda": "'opsz' 96",
    "inter": "'opsz' 32",
    "roboto-serif": "'opsz' 72",
}


def face_css(f, files):
    css = []
    for p in files:
        m = meta(p)
        st = f"font-stretch:{m['stretch']};" if m["stretch"] else ""
        css.append(f"@font-face{{font-family:'F-{f['id']}';src:url('{pathlib.Path(p).resolve().as_uri()}');font-weight:{m['weight']};font-style:{m['style']};{st}}}")
    return "\n".join(css)


def weights(f):
    """(min, max) weight ranges actually present in the font's files."""
    out = []
    for p in fetch_one(f):
        w = meta(p)["weight"].split()
        out.append((int(w[0]), int(w[-1])))
    return out


def disp_weight(f):
    want = {"serif": 460, "slab": 520, "sans": 680, "rounded": 620, "mono": 500, "pixel": 400, "hand": 500, "script": 400}.get(f["cls"], 500)
    rng = weights(f)
    if any(lo <= want <= hi for lo, hi in rng):
        return want
    # static faces: take the nearest real weight (never ask Chrome to fake a bold)
    return min((abs(w - want), w) for lo, hi in rng for w in (lo, hi))[1]


def cmd_specimen(a):
    c = cat()
    fonts = by_id()
    sets = []
    for pid in a.pair or []:
        p = next((x for x in c["pairings"] if x["id"] == pid), None)
        if not p:
            sys.exit(f"unknown pairing {pid} (fonts.py pairs)")
        sets.append(dict(label=pid, tone=c["tones"][p["tone"]], display=p["display"], text=p["text"], accent=p.get("accent"), zh=p["zh"], ja=p["ja"], why=p["why"], motion=p.get("motion", "")))
    for combo in a.combo or []:
        ids = combo.split("+")
        sets.append(dict(label=combo, tone="自定义", display=ids[0], text=ids[1] if len(ids) > 1 else ids[0], accent=ids[2] if len(ids) > 2 else None, zh=a.zh_fonts.split("+") if a.zh_fonts else ["noto-serif-sc", "noto-sans-sc"], ja=a.ja_fonts.split("+") if a.ja_fonts else ["zen-old-mincho", "zen-kaku-gothic-new"], why="", motion=""))
    need = set()
    for s in sets:
        need |= {s["display"], s["text"]} | ({s["accent"]} if s["accent"] else set())
        if a.zh:
            need |= set(s["zh"])
        if a.ja:
            need |= set(s["ja"])
    css = []
    for fid in sorted(need):
        f = fonts[fid]
        print(f"fetch {fid} …", file=sys.stderr)
        css.append(face_css(f, fetch_one(f)))
    bg, fg = a.bg, a.fg
    panels = []
    H = 700 if (a.zh or a.ja) else 600
    for i, s in enumerate(sets):
        D, T, A = fonts[s["display"]], fonts[s["text"]], fonts.get(s["accent"]) if s["accent"] else None
        dv = DEFAULT_VAR.get(D["id"], "normal")
        tv = DEFAULT_VAR.get(T["id"], "normal") if T["id"] != "inter" else "'opsz' 18"
        title = html.escape(a.title)
        if a.accent_word and A:
            title = title.replace(html.escape(a.accent_word), f"<span style=\"font-family:'F-{A['id']}';font-weight:{disp_weight(A)};font-style:normal\">{html.escape(a.accent_word)}</span>")
        elif a.italic_word and any("Italic" in os.path.basename(x) or "italic" in os.path.basename(x).lower() for x in fetch_one(D)):
            title = title.replace(html.escape(a.italic_word), f"<i>{html.escape(a.italic_word)}</i>")
        lic = " · ".join(sorted({fonts[x]["license"] for x in [D["id"], T["id"]] + ([A["id"]] if A else [])}))
        cjk = ""
        if a.zh:
            z0, z1 = fonts[s["zh"][0]], fonts[s["zh"][1]]
            cjk += f"<div class='cjk'><div style=\"font-family:'F-{z0['id']}';font-weight:{disp_weight(z0)}\">{html.escape(a.zh)}</div><div class='cjkmeta'>{z0.get('native', z0['family'])} × {z1.get('native', z1['family'])}</div></div>"
        if a.ja:
            j0, j1 = fonts[s["ja"][0]], fonts[s["ja"][1]]
            cjk += f"<div class='cjk'><div style=\"font-family:'F-{j0['id']}';font-weight:{disp_weight(j0)}\">{html.escape(a.ja)}</div><div class='cjkmeta'>{j0['family']} × {j1['family']}</div></div>"
        names = f"{D['family']} × {T['family']}" + (f" + {A['family']}" if A else "")
        panels.append(f"""
<section style="height:{H}px">
  <div class="rail"><div class="no">{i + 1:02d}</div><div class="tone">{html.escape(s['tone'])}</div><div class="id">{html.escape(s['label'])}</div>
    <div class="names">{html.escape(names)}</div><div class="lic">{html.escape(lic)}</div>
    <div class="why">{html.escape(s['why'])}</div><div class="motion">{('动效 · ' + html.escape(s['motion'])) if s['motion'] else ''}</div></div>
  <div class="stage">
    <div class="eyebrow" style="font-family:'F-{T['id']}';font-variation-settings:{tv}">{html.escape(a.eyebrow)}</div>
    <h1 style="font-family:'F-{D['id']}';font-weight:{disp_weight(D)};font-variation-settings:{dv}">{title}</h1>
    <p class="sub" style="font-family:'F-{T['id']}';font-variation-settings:{tv}">{html.escape(a.sub)}</p>
    <p class="body" style="font-family:'F-{T['id']}';font-variation-settings:{tv}">{html.escape(a.body)}</p>
    <div class="nums" style="font-family:'F-{T['id']}'">0123456789 · 24% · $9.90 · 01 / 12</div>
    {cjk}
  </div>
</section>""")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{chr(10).join(css)}
*{{margin:0;padding:0;box-sizing:border-box}} body{{width:1920px;background:{bg};color:{fg};font-synthesis:none}}
section{{display:flex;border-bottom:1px solid color-mix(in srgb,{fg} 14%,transparent)}}
.rail{{width:420px;padding:56px 44px;font:500 17px/1.5 -apple-system,'PingFang SC',sans-serif;color:color-mix(in srgb,{fg} 70%,transparent);border-right:1px solid color-mix(in srgb,{fg} 10%,transparent)}}
.no{{font:600 15px/1 ui-monospace,Menlo,monospace;letter-spacing:.2em;opacity:.6}} .tone{{font-size:28px;font-weight:700;color:{fg};margin-top:18px}}
.id{{font:500 14px ui-monospace,Menlo,monospace;opacity:.55;margin-top:6px}} .names{{margin-top:22px;font-size:19px;color:{fg};font-weight:600}}
.lic{{margin-top:6px;font:500 13px ui-monospace,Menlo,monospace;opacity:.6}} .why{{margin-top:22px}} .motion{{margin-top:12px;opacity:.8}}
.stage{{flex:1;padding:64px 88px;display:flex;flex-direction:column;justify-content:center;gap:18px;overflow:hidden}}
.eyebrow{{font-size:17px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;opacity:.6}}
h1{{font-size:{a.size}px;line-height:1.02;letter-spacing:-0.02em;font-optical-sizing:auto}}
.sub{{font-size:34px;line-height:1.3;opacity:.82;max-width:1200px}} .body{{font-size:24px;line-height:1.5;opacity:.7;max-width:1050px}}
.nums{{font-size:22px;font-variant-numeric:tabular-nums;opacity:.6;letter-spacing:.02em}}
.cjk{{display:flex;align-items:baseline;gap:26px;margin-top:6px}} .cjk>div:first-child{{font-size:54px;line-height:1.25}} .cjkmeta{{font:500 14px ui-monospace,Menlo,monospace;opacity:.55}}
</style></head><body>{''.join(panels)}</body></html>"""
    tmp = tempfile.mkdtemp()
    hp = os.path.join(tmp, "specimen.html")
    open(hp, "w", encoding="utf-8").write(page)
    out = os.path.abspath(a.out)
    total = H * len(sets)
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", "--force-device-scale-factor=1", "--virtual-time-budget=8000", f"--window-size=1920,{total}", f"--screenshot={out}", pathlib.Path(hp).as_uri()], check=True, capture_output=True)
    shutil.copy(hp, os.path.splitext(out)[0] + ".html")
    print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("list"); p.add_argument("--tone"); p.add_argument("--script"); p.add_argument("--role"); p.add_argument("-v", "--verbose", action="store_true"); p.set_defaults(fn=cmd_list)
    p = sp.add_parser("pairs"); p.add_argument("--tone"); p.set_defaults(fn=cmd_pairs)
    p = sp.add_parser("similar"); p.add_argument("name"); p.set_defaults(fn=cmd_similar)
    p = sp.add_parser("fetch"); p.add_argument("ids", nargs="+"); p.add_argument("--to"); p.set_defaults(fn=cmd_fetch)
    p = sp.add_parser("subset"); p.add_argument("project"); p.add_argument("--text-file"); p.add_argument("--text"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_subset)
    p = sp.add_parser("specimen")
    p.add_argument("--pair", action="append"); p.add_argument("--combo", action="append")
    p.add_argument("--title", required=True); p.add_argument("--sub", default=""); p.add_argument("--body", default=""); p.add_argument("--eyebrow", default="")
    p.add_argument("--zh"); p.add_argument("--ja"); p.add_argument("--zh-fonts"); p.add_argument("--ja-fonts")
    p.add_argument("--italic-word"); p.add_argument("--accent-word"); p.add_argument("--size", type=int, default=104)
    p.add_argument("--bg", default="#F5F1E8"); p.add_argument("--fg", default="#151513"); p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_specimen)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
