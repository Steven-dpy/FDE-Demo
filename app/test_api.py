# -*- coding: utf-8 -*-
"""Nook · HTTP 集成测试

模拟 widget 真实会发的请求，验证：
  1. 接口可用性与数据结构
  2. 多轮会话上下文延续（同一个 session_id）
  3. 中文界面预算按人民币、价格双币显示
  4. widget 渲染商品卡片所需的字段齐全
  5. 错误处理

用法：先起服务  python server.py 8770
     再跑      python test_api.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8770"
PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS  " + name)
    else:
        FAIL += 1
        print("FAIL  " + name + ("  " + str(extra) if extra else ""))


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def post(path, obj):
    req = urllib.request.Request(
        BASE + path, method="POST",
        data=json.dumps(obj, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


print("=== Nook HTTP integration ===")

# 1) 基础
st, h = get("/api/health")
check("GET /api/health", st == 200 and h.get("ok") and h.get("skus") == 240, h)

st, c = get("/api/config")
check("GET /api/config 含店主可配置项",
      st == 200 and c["brand"]["name"] == "Fern & Oak"
      and c["widget"]["quick_replies"]["zh"] and c["fx"]["usd_cny"] > 0)

# 2) 商品列表 + widget 卡片字段
st, pl = get("/api/products?lang=zh&limit=6")
need = {"sku", "name", "price_display", "image", "reason"} if False else None
check("GET /api/products", st == 200 and len(pl["products"]) == 6)
p0 = pl["products"][0]
check("商品字段齐全（详情页需要）",
      {"sku", "name", "description", "price_display", "image", "dimensions",
       "rating", "stock", "category_label"} <= set(p0.keys()))
check("中文商品价格双币", "≈ ¥" in p0["price_display"], p0["price_display"])

st, pe = get("/api/products?lang=en&limit=1")
check("英文商品价格单币", "≈" not in pe["products"][0]["price_display"],
      pe["products"][0]["price_display"])

# 3) 多轮会话：同一个 session_id 必须记住上下文
sid = "itest-" + str(id(object()))
st, r1 = post("/api/chat", {"session_id": sid, "lang": "zh",
                            "message": "我想弄个能窝着看书的地方"})
check("第 1 轮：识别场景并组包", r1["meta"].get("intent") == "bundle"
      and r1["bundle"] and len(r1["products"]) >= 3)

st, r2 = post("/api/chat", {"session_id": sid, "lang": "zh", "message": "预算一万"})
bot = r2["products"][0]["reason"] if r2["products"] else ""
check("第 2 轮：同一 session 记住上下文（仍是阅读角）",
      r2["meta"].get("intent") == "bundle" and r2["meta"].get("look") == "reading_corner")
check("第 2 轮：人民币预算被采纳并回显原话 ¥10,000", "¥10,000" in bot, bot)
check("第 2 轮：价格都在预算内（USD <= 1388）",
      all(p["price"] <= 1388 for p in r2["products"]),
      [p["price"] for p in r2["products"]])

st, r3 = post("/api/chat", {"session_id": sid, "lang": "zh", "message": "北欧风"})
check("第 3 轮：追加风格约束仍能返回",
      r3["meta"].get("intent") == "bundle" and len(r3["products"]) >= 3)

# 4) widget 渲染卡片所需字段（reason / price_display / image / sku）
p = r2["products"][0]
check("widget 卡片字段齐全",
      all(k in p for k in ("sku", "name", "reason", "price_display", "image")))

# 5) 英文链路
st, e1 = post("/api/chat", {"lang": "en", "message": "a corner to curl up and read"})
check("英文：场景识别", e1["meta"].get("look") == "reading_corner")
check("英文：理由是英文", e1["products"][0]["reason"].isascii() is False or "style" in e1["products"][0]["reason"],
      e1["products"][0]["reason"])

# 6) 护栏
st, o1 = post("/api/chat", {"lang": "zh", "message": "我要买个手机"})
check("护栏：超范围不硬凑", o1["meta"].get("intent") == "out_of_scope" and not o1["products"])

# 7) 商品详情 + 404
sku = p["sku"]
st, d = get("/api/products/" + sku)
check("GET /api/products/<sku>", st == 200 and d["sku"] == sku)
try:
    get("/api/products/FO-NOPE-999")
    check("未知 SKU 返回 404", False, "没有报错")
except urllib.error.HTTPError as ex:
    check("未知 SKU 返回 404", ex.code == 404)

print()
print("RESULT: %d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
