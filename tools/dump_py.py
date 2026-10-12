# -*- coding: utf-8 -*-
"""跨实现一致性验证 —— Python 侧

跑 tools/queries.json 里的全部对话，把「意图 + 返回的 SKU」dump 成 JSON。
与 tools/dump_js.js 的输出对比，确认浏览器端移植版与后端行为一致。

用法：  python tools/dump_py.py > .tmp/out_py.json
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
sys.path.insert(0, str(ROOT / "app"))

from concierge import Session          # noqa: E402

queries = json.loads((ROOT / "tools" / "queries.json").read_text(encoding="utf-8"))

out = []
for q in queries:
    s = Session(lang=q["lang"])
    steps = []
    for i, turn in enumerate(q["turns"]):
        r = s.respond(turn)
        steps.append({
            "step": i + 1,
            "intent": r["meta"].get("intent"),
            "look": r["meta"].get("look"),
            "skus": [p["sku"] for p in r["products"]],
        })
    out.append({"id": q["id"], "lang": q["lang"], "steps": steps})

json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
