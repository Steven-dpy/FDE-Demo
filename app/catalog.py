# -*- coding: utf-8 -*-
"""Nook · 商品检索层

把「用户的一句话」变成「一批候选商品」。

- 结构化硬过滤：品类 / 价格 / 房间 / 风格 / 材质 / 尺寸上限 / 标签 / 库存
- 中英混合词法打分：字段加权（标题 ×3、正文 ×1）+ IDF
- 无结果时按软条件逐级放宽，并**如实报告放宽了什么**（不假装有结果）

设计前提：这一层不依赖任何外部 API，永远可运行。
语义检索（embedding）是可选增强，见 search(..., semantic=fn)。
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from collections import Counter

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "products.json"

# ------------------------------------------------------------------ 中文口语 → 目录属性值
# 「听懂人话」的第一层：不需要 LLM 也能把口语映射到结构化字段。
ALIASES = {
    "沙发": "sofa", "长椅": "sofa",
    "单人椅": "armchair", "扶手椅": "armchair", "休闲椅": "armchair", "单人沙发": "armchair",
    "三人沙发": "sofa",
    "茶几": "coffee table", "边几": "coffee table",
    "餐桌": "dining table", "饭桌": "dining table",
    "餐椅": "dining chair", "椅子": "dining chair",
    "床架": "bed", "双人床": "bed", "床": "bed",
    "衣柜": "wardrobe", "衣橱": "wardrobe",
    "书架": "bookshelf", "书柜": "bookshelf", "置物架": "bookshelf",
    "书桌": "desk", "办公桌": "desk", "工作台": "desk",
    "落地灯": "floor lamp", "台灯": "table lamp", "灯": "lamp",
    "地毯": "rug", "地垫": "rug",
    "收纳": "storage", "储物": "storage", "柜子": "cabinet",
    "户外": "outdoor", "阳台": "outdoor", "庭院": "outdoor", "露台": "outdoor",
    "小户型": "small space", "小空间": "small space", "地方小": "small space",
    "看书": "reading", "阅读": "reading", "读书": "reading",
    "办公": "work from home", "居家办公": "work from home", "在家上班": "work from home",
    "宠物": "pet", "猫": "pet", "狗": "pet",
    "孩子": "family", "小孩": "family", "一家人": "family",
    "好打理": "easy to clean", "好清洁": "easy to clean",
    "北欧": "scandinavian", "日式": "japandi", "侘寂": "japandi",
    "极简": "minimalist", "简约": "minimalist",
    "中古": "mid-century", "复古": "mid-century",
    "工业": "industrial", "工业风": "industrial",
    "海岸": "coastal", "波西米亚": "boho",
    "橡木": "oak", "胡桃木": "walnut", "白蜡木": "ash", "实木": "solid oak",
    "真皮": "leather", "牛皮": "leather", "皮": "leather",
    "布": "fabric", "绒": "velvet", "羊羔绒": "boucle",
    "藤": "rattan", "藤编": "rattan", "大理石": "marble", "玻璃": "glass",
    "客厅": "living room", "卧室": "bedroom", "餐厅": "dining room",
    "书房": "home office", "玄关": "hallway", "走廊": "hallway",
}

CATEGORY_ZH = {
    "sofa": "沙发", "armchair": "单人扶手椅", "coffee_table": "茶几",
    "dining_table": "餐桌", "dining_chair": "餐椅", "bed": "床架",
    "wardrobe": "衣柜", "bookshelf": "书架", "desk": "书桌",
    "floor_lamp": "落地灯", "table_lamp": "台灯", "rug": "地毯",
    "storage": "收纳柜", "outdoor": "户外家具",
}

ROOM_ZH = {
    "living_room": "客厅", "bedroom": "卧室", "dining_room": "餐厅",
    "home_office": "书房", "outdoor": "阳台 / 庭院", "hallway": "玄关",
}

# 软条件放宽顺序（都不满足时才逐级丢）
SOFT_ORDER = ["max_width", "material", "style", "tags"]


def tokenize(text: str):
    """中英混合分词：拉丁词 + CJK 单字 + CJK 二元组。"""
    text = (text or "").lower()
    out = []
    for w in re.findall(r"[a-z0-9]+", text):
        if len(w) > 1:
            out.append(w)
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        out.extend(list(run))
        out.extend(run[i:i + 2] for i in range(len(run) - 1))
    return out


def expand_aliases(query: str) -> str:
    """把中文口语映射成目录里的英文属性值，追加到查询串上。"""
    q = (query or "").lower()
    extra = [en for zh, en in ALIASES.items() if zh in q]
    return q + " " + " ".join(extra)


class Catalog:
    def __init__(self, path=DATA):
        self.products = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        self.by_sku = {p["sku"]: p for p in self.products}
        self._idx = {}
        df = Counter()
        for p in self.products:
            title = " ".join([p["name"]["en"], p["name"]["zh"],
                              p["category_en"], p["category_zh"]])
            body = " ".join([p["description"]["en"], p["description"]["zh"],
                             p["style"], p["material"], p["material_accent"],
                             p["color"], p["room"], " ".join(p["tags"])])
            tc, bc = Counter(tokenize(title)), Counter(tokenize(body))
            self._idx[p["sku"]] = (tc, bc)
            for t in set(tc) | set(bc):
                df[t] += 1
        n = len(self.products)
        self._default_idf = math.log(1 + n)
        self.idf = {t: math.log(1 + n / (1 + c)) for t, c in df.items()}

    # ------------------------------------------------------------ 过滤
    @staticmethod
    def _passes(p, f) -> bool:
        if f.get("category") and p["category"] not in f["category"]:
            return False
        if f.get("room") and p["room"] not in f["room"]:
            return False
        if f.get("price_min") is not None and p["price"] < f["price_min"]:
            return False
        if f.get("price_max") is not None and p["price"] > f["price_max"]:
            return False
        if f.get("style") and p["style"] not in f["style"]:
            return False
        if f.get("material") and p["material"] not in f["material"]:
            return False
        if f.get("max_width") is not None and p["dimensions"]["w"] > f["max_width"]:
            return False
        if f.get("max_depth") is not None and p["dimensions"]["d"] > f["max_depth"]:
            return False
        if f.get("seats_min") is not None and (p["seats"] or 0) < f["seats_min"]:
            return False
        if f.get("tags"):
            if not set(f["tags"]) & set(p["tags"]):
                return False
        if f.get("in_stock", True) and p["stock"] <= 0:
            return False
        return True

    # ------------------------------------------------------------ 打分
    def _score(self, p, qset) -> float:
        tc, bc = self._idx[p["sku"]]
        s = 0.0
        for t in qset:
            w = self.idf.get(t, self._default_idf)
            if t in tc:
                s += 3.0 * w
            elif t in bc:
                s += 1.0 * w
        # 质量与可得性的轻微加权（不让它压过相关性）
        s += 0.05 * p["rating"] + 0.15 * math.log1p(p["review_count"])
        if p["stock"] > 0:
            s += 0.30
        return s

    # ------------------------------------------------------------ 检索
    def search(self, query="", filters=None, limit=6, semantic=None):
        """返回 (results, meta)。meta 里说明是否放宽了条件、放宽了哪些。"""
        f = {k: v for k, v in (filters or {}).items() if v not in (None, [], "")}
        qset = set(tokenize(expand_aliases(query)))
        relaxed = []
        matched = 0

        for _ in range(len(SOFT_ORDER) + 1):
            hits = [p for p in self.products if self._passes(p, f)]
            matched = len(hits)
            if hits or not any(k in f for k in SOFT_ORDER):
                break
            # 逐级放宽：丢掉当前最"软"的一个条件
            for k in SOFT_ORDER:
                if k in f:
                    f.pop(k)
                    relaxed.append(k)
                    break

        scored = [(self._score(p, qset), p) for p in hits]
        if semantic:
            for i, (s, p) in enumerate(scored):
                scored[i] = (s + 2.0 * semantic(query, p), p)
        if qset:
            # 近似同分时用 SKU 兜底，保证同一输入永远得到同一顺序（可复现，便于评测）
            scored.sort(key=lambda x: (-x[0], x[1]["sku"]))
        else:
            scored.sort(key=lambda x: (-(x[1]["rating"] * math.log1p(x[1]["review_count"])),
                                       x[1]["sku"]))

        # 纯词法模式下，得分过低视为不相关，避免"硬凑"
        if qset:
            top = scored[0][0] if scored else 0.0
            scored = [(s, p) for s, p in scored if s > top * 0.45]

        return [p for _, p in scored[:limit]], {
            "matched": matched,
            "relaxed": relaxed,
            "query_tokens": sorted(qset)[:40],
        }

    def category_avg_price(self, cat: str) -> float:
        xs = [p["price"] for p in self.products if p["category"] == cat]
        return sum(xs) / len(xs) if xs else 500.0


_DEFAULT = None


def get_catalog() -> Catalog:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Catalog()
    return _DEFAULT
