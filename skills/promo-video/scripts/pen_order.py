"""Pen paths for a client's own line art (first used on the HEYTEA film, 2026-10-02): thins each drawing to its centre lines (Zhang–Suen), splits the skeleton
into strokes at the junctions and orders them like a hand would draw them — from a start point, always continuing with
the nearest unfinished stroke. Each stroke is cut into short chunks whose brush width follows the local line width
(distance transform), so a solid shape (the drinker's hair) gets a fat brush and a fine line a thin one.

The film uses these only as an animated MASK over the artwork (raster, or better its vector trace from
vectorize_lineart.py): what appears on screen is always the client's drawing, revealed in drawing order.

  python3 pen_order.py public/art/drinker.png --start 20,330 --out src/film/pen.json
  python3 pen_order.py public/art/phone.png --start 40,960 --group hey=470,120,620,300 --out src/film/pen.json
     (--group: ink components fully inside the box animate on their own; writes <name>-main.png / <name>-<group>.png)

Merges {name: {w, h, strokes: [{d, len, w, lift?, g?}], groups?}} into --out and writes <out dir>/pen-<name>.png
(stroke order, blue → red) for review. Draw with templates/remotion/src/cinematic/lineart/PenArt.tsx."""
import json
from pathlib import Path
import cv2
import numpy as np

CHUNK = 18


def thin(img):
    """Zhang–Suen thinning on a 0/1 uint8 image."""
    img = img.copy()
    while True:
        changed = False
        for step in range(2):
            P = np.pad(img, 1)
            p2, p3, p4, p5 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:], P[2:, 2:]
            p6, p7, p8, p9 = P[2:, 1:-1], P[2:, :-2], P[1:-1, :-2], P[:-2, :-2]
            B = p2.astype(int) + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(int) for i in range(8))
            if step == 0:
                c = ((p2 * p4 * p6) == 0) & ((p4 * p6 * p8) == 0)
            else:
                c = ((p2 * p4 * p8) == 0) & ((p2 * p6 * p8) == 0)
            m = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if m.any():
                img[m] = 0
                changed = True
        if not changed:
            return img


NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def graph(sk):
    """skeleton → nodes (junction clusters + ends) and edges (ordered pixel chains between nodes)"""
    h, w = sk.shape
    pts = set(zip(*np.nonzero(sk)))
    deg = {p: sum((p[0] + dy, p[1] + dx) in pts for dy, dx in NB) for p in pts}
    junc = {p for p, d in deg.items() if d >= 3}
    # junction clusters
    node_of = {}
    nodes = []
    for p in junc:
        if p in node_of:
            continue
        stack = [p]
        cl = []
        node_of[p] = len(nodes)
        while stack:
            q = stack.pop()
            cl.append(q)
            for dy, dx in NB:
                r = (q[0] + dy, q[1] + dx)
                if r in junc and r not in node_of:
                    node_of[r] = len(nodes)
                    stack.append(r)
        nodes.append(tuple(np.mean(cl, 0)))
    chain_pts = pts - junc
    seen = set()
    edges = []
    for p in chain_pts:
        if p in seen:
            continue
        # collect this chain component
        comp = []
        stack = [p]
        seen.add(p)
        while stack:
            q = stack.pop()
            comp.append(q)
            for dy, dx in NB:
                r = (q[0] + dy, q[1] + dx)
                if r in chain_pts and r not in seen:
                    seen.add(r)
                    stack.append(r)
        cset = set(comp)
        nbr = lambda q: [(q[0] + dy, q[1] + dx) for dy, dx in NB if (q[0] + dy, q[1] + dx) in cset]
        ends = [q for q in comp if len(nbr(q)) <= 1]
        start = ends[0] if ends else comp[0]
        # walk the chain
        order = [start]
        vis = {start}
        cur = start
        while True:
            nx = [r for r in nbr(cur) if r not in vis]
            if not nx:
                break
            # prefer 4-neighbours so the walk does not skip a corner pixel
            nx.sort(key=lambda r: abs(r[0] - cur[0]) + abs(r[1] - cur[1]))
            cur = nx[0]
            vis.add(cur)
            order.append(cur)
        if len(order) < len(comp):  # odd little loops: append the rest by proximity
            rest = [q for q in comp if q not in vis]
            order += rest

        def attach(q):
            for dy, dx in NB:
                r = (q[0] + dy, q[1] + dx)
                if r in node_of:
                    return node_of[r]
            return None

        a = attach(order[0])
        z = attach(order[-1])
        loop = not ends
        if a is None:
            nodes.append(tuple(map(float, order[0])))
            a = len(nodes) - 1
        if z is None:
            if loop:
                z = a
            else:
                nodes.append(tuple(map(float, order[-1])))
                z = len(nodes) - 1
        poly = [nodes[a]] + [tuple(map(float, q)) for q in order] + [nodes[z]]
        if loop:
            poly = [tuple(map(float, q)) for q in order] + [tuple(map(float, order[0]))]
        edges.append({"a": a, "z": z, "poly": poly})
    # isolated junction clusters with no chains (tiny dots)
    used = {e["a"] for e in edges} | {e["z"] for e in edges}
    for i, n in enumerate(nodes):
        if i not in used:
            edges.append({"a": i, "z": i, "poly": [n, n]})
    return nodes, edges


def plen(poly):
    p = np.array(poly)
    return float(np.sqrt((np.diff(p, axis=0) ** 2).sum(1)).sum()) if len(p) > 1 else 0.0


def order_edges(nodes, edges, start_xy):
    """pen order: from the node nearest the start, keep drawing; at a dead end jump to the nearest unfinished stroke"""
    inc = {}
    for i, e in enumerate(edges):
        inc.setdefault(e["a"], []).append(i)
        inc.setdefault(e["z"], []).append(i)
    left = set(range(len(edges)))
    N = np.array([(n[1], n[0]) for n in nodes])  # (x, y)
    cur = int(np.argmin(((N - np.array(start_xy)) ** 2).sum(1)))
    heading = None
    out = []
    while left:
        cand = [i for i in inc.get(cur, []) if i in left]
        if cand:
            def score(i):
                e = edges[i]
                poly = e["poly"] if e["a"] == cur else e["poly"][::-1]
                k = min(len(poly) - 1, 6)
                d = np.array(poly[k]) - np.array(poly[0])
                d = d / (np.linalg.norm(d) + 1e-9)
                turn = 0.0 if heading is None else 1 - float(d @ heading)
                return turn * 40 + min(plen(poly), 400) * 0.02  # keep going straight; small details first on ties
            i = min(cand, key=score)
            e = edges[i]
            poly = e["poly"] if e["a"] == cur else e["poly"][::-1]
            out.append({"poly": poly, "jump": False})
            left.discard(i)
            cur = e["z"] if e["a"] == cur else e["a"]
            k = max(0, len(poly) - 7)
            d = np.array(poly[-1]) - np.array(poly[k])
            heading = d / (np.linalg.norm(d) + 1e-9)
        else:
            # nearest node that still has strokes
            pos = N[cur]
            best = None
            for i in left:
                for nd in (edges[i]["a"], edges[i]["z"]):
                    dd = float(((N[nd] - pos) ** 2).sum())
                    if best is None or dd < best[0]:
                        best = (dd, nd)
            cur = best[1]
            heading = None
            if out:
                out[-1]["jump_after"] = True
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("art", help="black line art PNG (alpha or white ground)")
    ap.add_argument("--start", default="0,0", help="x,y where the pen starts, in art pixels")
    ap.add_argument("--group", action="append", default=[], help="name=x0,y0,x1,y1")
    ap.add_argument("--name", help="key in the json (default: file stem)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    art = Path(a.art)
    name = a.name or art.stem
    cfg = {"start": tuple(float(v) for v in a.start.split(",")), "groups": {}}
    for g in a.group:
        k, box = g.split("=")
        cfg["groups"][k] = tuple(int(v) for v in box.split(","))
    outp = Path(a.out)
    res = json.load(open(outp, encoding="utf-8")) if outp.exists() else {}
    if True:
        im = cv2.imread(str(art), cv2.IMREAD_UNCHANGED)
        h, w = im.shape[:2]
        a = im[..., 3] if im.shape[2] == 4 else np.full((h, w), 255, np.uint8)
        ink = ((a > 40) & (im[..., :3].mean(-1) < 160)).astype(np.uint8)
        dist = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
        sk = thin(ink)
        nodes, edges = graph(sk)
        # stroke groups: ink components that sit fully inside a group's box (e.g. the "hey!" letters)
        ncomp, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
        comp_group = {}
        for g, (gx0, gy0, gx1, gy1) in cfg.get("groups", {}).items():
            for i in range(1, ncomp):
                x, y, bw, bh, _ = st[i]
                if x >= gx0 and y >= gy0 and x + bw <= gx1 and y + bh <= gy1:
                    comp_group[i] = g
        # prune tiny spurs (thinning noise at blob edges): end chains shorter than the local radius
        deg = {}
        for e in edges:
            deg[e["a"]] = deg.get(e["a"], 0) + 1
            deg[e["z"]] = deg.get(e["z"], 0) + 1
        keep = []
        for e in edges:
            L = plen(e["poly"])
            p = e["poly"][len(e["poly"]) // 2]
            r = float(dist[int(p[0]), int(p[1])])
            # a spur is a short free end hanging off a real junction (degree ≥ 3); short strokes of small shapes
            # (the drinker's closed eye splits into two halves at a degree-2 node) are kept
            ends = (deg[e["a"]], deg[e["z"]])
            spur = (1 in ends) and max(ends) >= 3
            if spur and L < max(4.0, 1.6 * r):
                continue
            keep.append(e)
        edges = keep
        seq = order_edges(nodes, edges, cfg["start"])
        strokes = []
        for s in seq:
            poly = np.array(s["poly"])  # (y, x)
            if len(poly) < 2:
                poly = np.vstack([poly, poly])
            seglen = np.r_[0, np.cumsum(np.sqrt((np.diff(poly, axis=0) ** 2).sum(1)))]
            L = seglen[-1]
            n = max(1, int(np.ceil(L / CHUNK)))
            for k in range(n):
                lo, hi = L * k / n, L * (k + 1) / n
                idx = np.nonzero((seglen >= lo - 0.01) & (seglen <= hi + 0.01))[0]
                if len(idx) == 0:
                    idx = np.array([int(np.searchsorted(seglen, lo))])
                i0, i1 = max(0, idx[0] - 1), min(len(poly) - 1, idx[-1] + 1)
                pts = poly[i0 : i1 + 1]
                r = max(float(dist[int(round(y)), int(round(x))]) for y, x in poly[max(0, i0 - 3) : i1 + 4])
                ap = cv2.approxPolyDP(pts[:, ::-1].astype(np.float32).reshape(-1, 1, 2), 0.8, False).reshape(-1, 2)
                if len(ap) == 1:
                    ap = np.vstack([ap, ap + [0.1, 0]])
                d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in ap)
                st_ = {"d": d, "len": round(max(1.0, hi - lo), 1), "w": round(2 * r + 12, 1)}
                yy, xx = poly[i0]
                g = comp_group.get(int(lab[int(round(yy)), int(round(xx))]))
                if g:
                    st_["g"] = g
                strokes.append(st_)
            if s.get("jump_after"):
                strokes[-1]["lift"] = 1
        total = sum(s["len"] for s in strokes)
        res[name] = {"w": w, "h": h, "strokes": strokes}
        if comp_group:
            # split the raster so a group can animate on its own: <name>-main.png + <name>-<group>.png
            from PIL import Image
            src = np.array(Image.open(art).convert("RGBA"))
            gmask = {}
            for ci, g in comp_group.items():
                gmask.setdefault(g, np.zeros((h, w), bool))
                gmask[g] |= cv2.dilate((lab == ci).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            allg = np.zeros((h, w), bool)
            res[name]["groups"] = {}
            for g, gm in gmask.items():
                part = src.copy()
                part[~gm, 3] = 0
                Image.fromarray(part).save(art.with_name(f"{name}-{g}.png"))
                ys, xs = np.nonzero(gm)
                res[name]["groups"][g] = {"cx": float(xs.mean()), "cy": float(ys.mean()), "x0": int(xs.min()), "y0": int(ys.min()), "x1": int(xs.max()), "y1": int(ys.max())}
                allg |= gm
            main_ = src.copy()
            main_[allg, 3] = 0
            Image.fromarray(main_).save(art.with_name(f"{name}-main.png"))
        print(f"{name}: {len(edges)} strokes → {len(strokes)} chunks, pen length {total:.0f}px, lifts {sum(s.get('lift', 0) for s in strokes)}")
        # preview: order as colour
        vis = np.full((h, w, 3), 255, np.uint8)
        vis[ink > 0] = (215, 215, 215)
        acc = 0
        for s in strokes:
            u = acc / total
            acc += s["len"]
            col = (int(255 * (1 - u)), 40, int(255 * u))
            pts = np.array([[float(v) for v in p.split()] for p in s["d"][2:].split(" L ")])
            cv2.polylines(vis, [pts.astype(np.int32)], False, col, 2)
        cv2.imwrite(str(outp.with_name(f"pen-{name}.png")), vis)
    json.dump(res, open(outp, "w", encoding="utf-8"))


main()
