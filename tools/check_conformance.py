# -*- coding: utf-8 -*-
"""跨实现一致性验证 —— 比对 Python 与浏览器端引擎

用法：
    1)  python tools/dump_py.py > .tmp/out_py.json
    2)  node   tools/dump_js.js > .tmp/out_js.json
    3)  python tools/check_conformance.py

也可比对打包后的静态版：
    2b) node   tools/dump_js.js portfolio/demo > .tmp/out_js.json
"""
from __future__ import annotations

import json
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = ROOT / ".tmp" / "out_py.json"
JS = ROOT / ".tmp" / "out_js.json"


def load(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main():
    if not PY.exists() or not JS.exists():
        raise SystemExit("先跑 dump_py.py 和 dump_js.js 生成两份输出")

    a, b = load(PY), load(JS)
    if len(a) != len(b):
        raise SystemExit("用例数量不一致：py=%d js=%d" % (len(a), len(b)))

    same = diff = 0
    for x, y in zip(a, b):
        for sx, sy in zip(x["steps"], y["steps"]):
            ok = (sx["intent"] == sy["intent"] and sx["skus"] == sy["skus"])
            if ok:
                same += 1
            else:
                diff += 1
                print("DIFF  %s step%d  (%s)" % (x["id"], sx["step"], x["lang"]))
                print("      py: intent=%s look=%s skus=%s" % (sx["intent"], sx.get("look"), sx["skus"]))
                print("      js: intent=%s look=%s skus=%s" % (sy["intent"], sy.get("look"), sy["skus"]))

    total = same + diff
    print()
    print("用例 %d 条 / 对话步 %d 步" % (len(a), total))
    print("一致 %d   不一致 %d" % (same, diff))
    print("RESULT:", "PASS" if diff == 0 else "FAIL")
    return 0 if diff == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
