# -*- coding: utf-8 -*-
"""静态版产物体检：相对路径、引擎引导、必需资源是否齐全"""
from __future__ import annotations

import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

D = pathlib.Path(__file__).resolve().parent.parent / "portfolio" / "demo"
REQUIRED = ["index.html", "embed.html", "store.css", "store.js",
            "nook-api.js", "nook-widget.js", "static-engine.js", "products.json"]

ok = True
print("=== portfolio/demo 体检 ===")

for f in REQUIRED:
    hit = (D / f).exists()
    ok &= hit
    size = ("%.1f KB" % ((D / f).stat().st_size / 1024)) if hit else "-"
    print("  %-20s %s  %s" % (f, "OK " if hit else "缺失", size))

print()
for f in ["index.html", "embed.html"]:
    s = (D / f).read_text(encoding="utf-8")
    absrefs = re.findall(r'(?:src|href)="(/[^"]*)"', s)
    checks = [
        ("无绝对路径", not absrefs),
        ("引擎引导", "static-engine.js" in s),
        ("就绪事件", "nook:engine-ready" in s),
        ("widget 引用", "nook-widget.js" in s),
    ]
    bad = [n for n, c in checks if not c]
    ok &= not bad
    print("  %-12s %s" % (f, "OK" if not bad else "问题: " + ", ".join(bad)))
    if absrefs:
        print("      绝对路径引用:", absrefs)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
