# -*- coding: utf-8 -*-
"""Nook · 端到端自检：把护栏断言跑一遍，确认交付物的基本性质成立。"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from catalog import get_catalog
from concierge import Session

ok = 0


def check(name, cond):
    global ok
    print(("PASS  " if cond else "FAIL  ") + name)
    if cond:
        ok += 1
    return cond


cat = get_catalog()
print("=== Nook self-check ===")
check("商品库加载：240 SKU", len(cat.products) == 240)
check("SKU 唯一", len({p["sku"] for p in cat.products}) == len(cat.products))
check("双语字段完整", all(p["name"]["en"] and p["name"]["zh"]
                          and p["description"]["en"] and p["description"]["zh"]
                          for p in cat.products))

# --- 护栏 1：推荐的商品必须真实存在，价格必须来自数据库 ---
# 注意：中文界面的预算按**人民币**理解。¥18,000 ÷ 7.2 = US$2,500
s = Session("zh")
r = s.respond("客厅要个沙发，预算一万八以内")
check("常规检索有结果", bool(r["products"]))
check("推荐的 SKU 都在库内",
      all(p["sku"] in cat.by_sku for p in r["products"]))
check("价格与数据库一致（不编造）",
      all(p["price"] == cat.by_sku[p["sku"]]["price"] for p in r["products"]))
check("人民币预算换算后过滤生效（USD <= 2500）",
      all(p["price"] <= 2500 for p in r["products"]))
check("中文价格双币显示",
      all("≈ ¥" in p["price_display"] for p in r["products"]))
check("预算回显用户原话（¥18,000 而不是换算近似值）",
      "¥18,000" in r["products"][0]["reason"])

# --- 护栏 2：超范围不硬凑 ---
r2 = Session("zh").respond("我想买个耳机")
check("超范围拒答且不给商品",
      (not r2["products"]) and r2["meta"]["intent"] == "out_of_scope")
r2e = Session("en").respond("do you sell laptops?")
check("英文超范围同样拒答", r2e["meta"]["intent"] == "out_of_scope")

# --- 护栏 3：场景组包成立 ---
s3 = Session("zh")
r3 = s3.respond("我想弄个能窝着看书的地方")
check("场景识别为阅读角", r3["meta"].get("look") == "reading_corner")
check("组包成套装且跨品类", len({p["category"] for p in r3["products"]}) >= 3)

# --- 护栏 4：澄清不超过两轮 ---
s4 = Session("en")
q1 = s4.respond("I need something for my place")
check("信息不足时追问房间", q1["meta"]["intent"] == "clarify_room" and bool(q1["ask"]))
q2 = s4.respond("the living room")
check("第二轮必须给结果（不能一直问）", bool(q2["products"]))

# --- 中英一致性：同一意图应命中同一批 SKU（¥18,000 与 $2,500 等值）---
a = Session("zh").respond("客厅沙发 北欧 预算一万八")
b = Session("en").respond("living room sofa scandinavian budget 2500")
check("中英同意图命中同一批 SKU（集合一致；近似同分时顺序可能微调）",
      {p["sku"] for p in a["products"]} == {p["sku"] for p in b["products"]})

print()
print("图片域名：", sorted({p["image"].split("/")[2] for p in cat.products}))
print("价格区间：USD %d - %d" % (min(p["price"] for p in cat.products),
                              max(p["price"] for p in cat.products)))
print()
print("RESULT: %d checks passed" % ok)
sys.exit(0 if ok >= 16 else 1)
