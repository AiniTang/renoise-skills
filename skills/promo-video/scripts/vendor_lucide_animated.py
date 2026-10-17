#!/usr/bin/env python3
"""把 lucide-animated（github.com/pqoqubbw/icons，MIT）的图标源码拷进 Remotion 工程并改成逐帧可渲染。
用法: vendor_lucide_animated.py <icons 仓库目录> <目标目录，如 src/icons/la>
- motion/react → ../motion-shim；@/lib/utils → ../cn；Math.random() → __rand()（确定性）
- 生成 index.ts：ICONS = { "rocket": RocketIcon, ... } 与 ICON_NAMES
"""
import re, sys, pathlib, shutil
src = pathlib.Path(sys.argv[1]); dst = pathlib.Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True)
names = []
for f in sorted((src / "icons").glob("*.tsx")):
    s = f.read_text(encoding="utf-8")
    s = s.replace('"use client";\n', "")
    s = re.sub(r'from "motion/react"', 'from "../motion-shim"', s)
    s = s.replace('from "@/lib/utils"', 'from "../cn"')
    if "Math.random()" in s:
        s = s.replace("Math.random()", "__rand()")
        s = re.sub(r'import \{([^}]*)\} from "../motion-shim"', lambda m: 'import {%s, __rand } from "../motion-shim"' % m.group(1).rstrip().rstrip(','), s, count=1)
    m = re.search(r"export \{ (?:\w+ as )?(\w+Icon) \}", s) or re.search(r"export const (\w+Icon) = forwardRef", s)
    if not m:
        print("skip (no export):", f.name); continue
    (dst / f.name).write_text("// @ts-nocheck\n" + s, encoding="utf-8")
    names.append((f.stem, m.group(1)))
lines = ["// 自动生成：vendor_lucide_animated.py。图标来自 lucide-animated (MIT)，见 LICENSE", ""]
lines += [f'import {{ {c} }} from "./{n}";' for n, c in names]
lines += ["", "export const ICONS = {"] + [f'  "{n}": {c},' for n, c in names] + ["} as const;", "export type IconName = keyof typeof ICONS;", "export const ICON_NAMES = Object.keys(ICONS) as IconName[];", ""]
(dst / "index.ts").write_text("\n".join(lines), encoding="utf-8")
shutil.copy(src / "LICENSE", dst / "LICENSE")
print(len(names), "icons ->", dst)
