#!/usr/bin/env python3
"""Lint the words that appear on screen: real punctuation, dangling separators, orphans.

Usage:
  python3 typo_lint.py storyboard.json            # every on-screen string in a template-mode storyboard
  python3 typo_lint.py --fix storyboard.json      # apply the unambiguous fixes in place
  python3 typo_lint.py --ts src/film/poem.ts src/film/Overlay.tsx   # string literals / JSX text in cinematic-mode sources (report only)

Rules (see references/typography.md section 7):
  apos     straight ' inside a word (it's, Anthropic's)               -> ’            (fixable)
  quote    straight "..." around words                                -> “...”        (fixable in JSON)
  ellipsis "..."                                                      -> …            (fixable)
  dash     " -- " / " - " between words                               -> " — "        (-- fixable, - report)
  dspace   two spaces in a row                                        -> one          (fixable)
  cjk      half-width , ; ? ! : right after a CJK character           -> full-width   (fixable)
  hang     a line ends with a separator (·  —  |  /) before a break   -> drop it / move it (report)
  orphan   last line of a hand-set break is one short word            -> re-break     (report)
"""
import argparse
import json
import re
import sys

CJK = r"[㐀-鿿　-〿＀-￯]"
SKIP_KEYS = {"src", "url", "path", "id", "type", "style", "font", "family", "icon", "color", "bg", "background", "from", "to", "anim", "variant", "ease", "file", "image", "logo", "music", "voice", "lang", "mode", "layout", "align", "kind", "name"}


def looks_like_prose(s: str) -> bool:
    if not re.search(r"[A-Za-z㐀-鿿]", s):
        return False
    if re.match(r"^(#[0-9a-fA-F]{3,8}|https?://|/|\.{0,2}/|[\w.-]+\.(png|jpe?g|svg|mp4|wav|mp3|woff2?|json|tsx?|css))", s.strip()):
        return False
    if re.search(r"(=>|\bimport\b|\bconst\b|\bfunction\b|\brgba?\(|\bpx\b|\$\{|[{};]\s*$)", s):
        return False
    return True


def looks_like_prose_ts(s: str) -> bool:
    """TS/TSX candidates: also reject anything that reads like code."""
    if not looks_like_prose(s):
        return False
    return not re.search(r"[=;]|&&|\|\||\)\s*\{|\w\(\w*[,)]|\bseg\(|\bf\b\s*[<>]|\?\s*[\w(]+\s*:", s)


def check(s: str):
    """Yield (rule, message, fixed_text_or_None)."""
    out = []
    t = s
    if re.search(r"(?<=[A-Za-z])'(?=[A-Za-z])|(?<=[sS])'(?=\s|$)", s):
        t2 = re.sub(r"(?<=[A-Za-z])'(?=[A-Za-z])", "’", s)
        t2 = re.sub(r"(?<=[sS])'(?=\s|$)", "’", t2)
        out.append(("apos", "straight apostrophe: use ’", t2))
    if re.search(r"(?<![\w\"])\"[^\"\n]+\"(?![\w\"])", s) and s.count('"') % 2 == 0:
        t2 = re.sub(r"\"([^\"\n]+)\"", "“\\1”", s)
        out.append(("quote", "straight quotes: use “ ”", t2))
    if "..." in s:
        out.append(("ellipsis", "three dots: use …", s.replace("...", "…")))
    if re.search(r"\w --? \w|\w -- \w", s) and not re.search(CJK, s):
        out.append(("dash", "hyphen used as a dash: use —", re.sub(r"(?<=\w) -- (?=\w)", " — ", s) if " -- " in s else None))
    if "  " in s.strip():
        out.append(("dspace", "double space", re.sub(r" {2,}", " ", s)))
    if re.search(CJK + r"[,;?!:]", s):
        t2 = re.sub(f"({CJK}),", r"\1，", s)
        t2 = re.sub(f"({CJK});", r"\1；", t2)
        t2 = re.sub(f"({CJK})\\?", r"\1？", t2)
        t2 = re.sub(f"({CJK})!", r"\1！", t2)
        t2 = re.sub(f"({CJK}):", r"\1：", t2)
        out.append(("cjk", "half-width punctuation after CJK: use full-width", t2))
    if re.search(f"(?<={CJK}) +(?={CJK})", s):
        out.append(("cjk-space", "space between two CJK characters / punctuation", re.sub(f"(?<={CJK}) +(?={CJK})", "", s)))
    lines = s.split("\n")
    if len(lines) > 1:
        for ln in lines[:-1]:
            if re.search(r"\s[·—|/]\s*$", ln):
                out.append(("hang", f"line ends with a separator: {ln.strip()[-12:]!r}", None))
        last = lines[-1].strip()
        if re.fullmatch(r"[A-Za-z’'.,;:!?—-]{1,5}", last) and len(lines[-2].strip()) >= 18:
            out.append(("orphan", f"one short word on the last line: {last!r}", None))
    return out


def walk_json(o, path="", key=None):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_json(v, f"{path}.{k}" if path else k, k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_json(v, f"{path}[{i}]", key)
    elif isinstance(o, str) and key not in SKIP_KEYS and looks_like_prose(o):
        yield path, o


def fix_json(o, key=None):
    if isinstance(o, dict):
        return {k: fix_json(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [fix_json(v, key) for v in o]
    if isinstance(o, str) and key not in SKIP_KEYS and looks_like_prose(o):
        cur = o
        for _ in range(6):                      # apply fixes one after another until stable
            fixed = [f for _, _, f in check(cur) if f and f != cur]
            if not fixed:
                break
            cur = fixed[0]
        return cur
    return o


STR_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`')
JSX_RE = re.compile(r">([^<>{}\n][^<>{}]*)<")


def ts_strings(text: str):
    for m in STR_RE.finditer(text):
        s = m.group(1) if m.group(1) is not None else m.group(2)
        yield text.count("\n", 0, m.start()) + 1, s.encode().decode("unicode_escape", errors="ignore") if "\\n" in s else s
    for m in JSX_RE.finditer(text):
        yield text.count("\n", 0, m.start()) + 1, m.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--ts", action="store_true", help="treat files as TS/TSX sources")
    ap.add_argument("--fix", action="store_true", help="apply fixes (JSON only)")
    ap.add_argument("--ignore", default="", help="comma-separated rule ids to skip, e.g. dspace (intentional spacing in mono labels)")
    a = ap.parse_args()
    skip = {r.strip() for r in a.ignore.split(",") if r.strip()}
    n = 0
    for path in a.files:
        if a.ts or path.endswith((".ts", ".tsx")):
            src = open(path, encoding="utf-8").read()
            for line, s in ts_strings(src):
                if not looks_like_prose_ts(s) or " " not in s.strip():
                    continue
                for rule, msg, _ in check(s):
                    if rule in skip:
                        continue
                    n += 1
                    print(f"{path}:{line}: [{rule}] {msg}  ← {s[:70]!r}")
        else:
            data = json.load(open(path, encoding="utf-8"))
            for p, s in walk_json(data):
                for rule, msg, fixed in check(s):
                    if rule in skip:
                        continue
                    n += 1
                    print(f"{path}: {p}: [{rule}] {msg}  ← {s[:70]!r}")
            if a.fix:
                fixed = fix_json(data)
                if fixed != data:
                    json.dump(fixed, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                    print(f"{path}: fixes applied")
    print("typo_lint: clean" if n == 0 else f"typo_lint: {n} finding(s)")
    sys.exit(1 if n and not a.fix else 0)


if __name__ == "__main__":
    main()
