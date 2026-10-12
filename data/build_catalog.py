# -*- coding: utf-8 -*-
"""Nook · 商品目录生成器

为虚拟客户「Fern & Oak」（家居独立站）生成 240 个真实感 SKU。
- 双语（en / zh），同一套商品库，界面可切换
- 带结构化属性（尺寸 / 材质 / 风格 / 房间 / 座位数 / 标签），供 AI 导购做属性过滤 + 语义检索
- 固定随机种子，可复现

用法：  python build_catalog.py
产出：  products.json
"""
from __future__ import annotations

import json
import random
import pathlib

SEED = 20260814
OUT = pathlib.Path(__file__).with_name("products.json")

# ---------------------------------------------------------------- 命名池
NORSE = [
    "Halden", "Fjord", "Bergen", "Lom", "Vik", "Aure", "Sogne", "Trysil", "Rana",
    "Elva", "Kvit", "Stein", "Norra", "Alva", "Bjorli", "Dovre", "Eide", "Foss",
    "Gaula", "Hemsedal", "Jotun", "Kongs", "Lier", "Mysa", "Nore", "Odda",
    "Rjukan", "Selje", "Tinde", "Usta", "Voss", "Ytre", "Aal", "Brumund",
    "Driva", "Eggedal", "Femund", "Gjende", "Halling", "Innvik", "Jølster",
    "Kragerø", "Lofot", "Molde", "Namsos", "Oppdal", "Røros", "Sirdal",
]

# 单名不够 240 个时，用「地名 + 自然词」组合补足
NATURE = [
    "Fjell", "Vik", "Elv", "Skog", "Berg", "Dal", "Sjø", "Lind", "Bjørk",
    "Stein", "Mose", "Furu", "Gran", "Vidde", "Strand", "Holm", "Odde",
    "Nes", "Sund", "Bø", "Haug", "Li", "Moen", "Rud", "Ødegård",
]

# ---------------------------------------------------------------- 翻译表
STYLE = {
    "scandinavian": ("Scandinavian", "北欧"),
    "japandi": ("Japandi", "日式北欧"),
    "mid_century": ("mid-century", "中古"),
    "minimalist": ("minimalist", "极简"),
    "industrial": ("industrial", "工业风"),
    "coastal": ("coastal", "海岸风"),
    "boho": ("boho", "波西米亚"),
    "modern": ("modern", "现代"),
}

MATERIAL = {
    "oak": ("solid oak", "实木橡木"),
    "walnut": ("American walnut", "美国胡桃木"),
    "ash": ("ash wood", "白蜡木"),
    "birch": ("birch plywood", "桦木多层板"),
    "metal": ("powder-coated steel", "粉末喷涂钢"),
    "linen": ("washed linen", "水洗亚麻"),
    "boucle": ("bouclé", "羊羔绒"),
    "velvet": ("cotton velvet", "棉天鹅绒"),
    "leather": ("full-grain leather", "头层牛皮"),
    "fabric": ("woven fabric", "混纺面料"),
    "rattan": ("natural rattan", "天然藤编"),
    "wool": ("hand-tufted wool", "手工簇绒羊毛"),
    "marble": ("honed marble", "哑光大理石"),
    "ceramic": ("glazed ceramic", "釉面陶瓷"),
    "glass": ("tempered glass", "钢化玻璃"),
}

COLOR = {
    "oatmeal": ("Oatmeal", "燕麦色"),
    "charcoal": ("Charcoal", "炭灰色"),
    "sage": ("Sage Green", "鼠尾草绿"),
    "rust": ("Rust", "铁锈红"),
    "navy": ("Navy", "藏青"),
    "cream": ("Cream", "奶油白"),
    "walnut": ("Walnut", "胡桃色"),
    "black": ("Matte Black", "哑光黑"),
    "white": ("Chalk White", "粉笔白"),
    "terracotta": ("Terracotta", "赤陶色"),
    "forest": ("Forest Green", "森林绿"),
    "sand": ("Sand", "沙色"),
}

ROOM = {
    "living_room": ("living room", "客厅"),
    "bedroom": ("bedroom", "卧室"),
    "dining_room": ("dining room", "餐厅"),
    "home_office": ("home office", "书房"),
    "outdoor": ("balcony or patio", "阳台或庭院"),
    "hallway": ("hallway or entryway", "玄关或走廊"),
}

TAG = {
    "small_space": ("small-space friendly", "小户型友好"),
    "family": ("family friendly", "适合有孩子的家庭"),
    "reading": ("reading nook", "适合阅读角"),
    "wfh": ("work from home", "居家办公"),
    "pet_friendly": ("pet friendly", "宠物友好"),
    "low_maintenance": ("easy to clean", "易打理"),
    "statement_piece": ("statement piece", "空间焦点"),
    "storage_heavy": ("generous storage", "收纳量大"),
    "outdoor_safe": ("weather resistant", "耐候"),
    "easy_assembly": ("tool-free assembly", "免工具安装"),
}

# ---------------------------------------------------------------- 品类定义
# dims: 宽/深/高 的取值区间（cm）; price: 美元区间; mats: 主材池
CATEGORIES = {
    "sofa": dict(
        en="Sofa", zh="沙发", qty=24, img="sofa",
        dims=dict(w=(140, 280), d=(85, 100), h=(72, 92)),
        price=(699, 2899), seats=(2, 4),
        mats=["fabric", "boucle", "velvet", "leather", "linen"],
        accents=["oak", "walnut", "ash", "metal"],
        styles=["scandinavian", "japandi", "mid_century", "minimalist", "modern"],
        rooms=["living_room"], tags=["family", "statement_piece"],
    ),
    "armchair": dict(
        en="Armchair", zh="单人扶手椅", qty=20, img="armchair",
        dims=dict(w=(62, 92), d=(68, 90), h=(68, 96)),
        price=(229, 1099),
        mats=["boucle", "fabric", "leather", "velvet", "rattan"],
        accents=["oak", "walnut", "metal", "ash"],
        styles=["scandinavian", "japandi", "mid_century", "boho", "modern"],
        rooms=["living_room", "bedroom"], tags=["reading", "statement_piece"],
    ),
    "coffee_table": dict(
        en="Coffee Table", zh="茶几", qty=20, img="coffee,table",
        dims=dict(w=(78, 160), d=(45, 82), h=(34, 46)),
        price=(139, 749),
        mats=["oak", "walnut", "marble", "glass", "ash"],
        accents=["metal", "black"],
        styles=["scandinavian", "japandi", "mid_century", "minimalist", "industrial"],
        rooms=["living_room"], tags=["small_space"],
    ),
    "dining_table": dict(
        en="Dining Table", zh="餐桌", qty=16, img="dining,table",
        dims=dict(w=(110, 240), d=(72, 100), h=(74, 78)),
        price=(379, 1999), seats=(4, 8),
        mats=["oak", "walnut", "ash", "marble"],
        accents=["metal", "black", "birch"],
        styles=["scandinavian", "japandi", "mid_century", "industrial", "modern"],
        rooms=["dining_room"], tags=["family", "statement_piece"],
    ),
    "dining_chair": dict(
        en="Dining Chair", zh="餐椅", qty=18, img="chair",
        dims=dict(w=(43, 58), d=(48, 60), h=(76, 90)),
        price=(69, 329),
        mats=["oak", "ash", "fabric", "leather", "rattan"],
        accents=["metal", "black", "walnut"],
        styles=["scandinavian", "japandi", "mid_century", "minimalist", "industrial"],
        rooms=["dining_room"], tags=["family", "easy_assembly"],
    ),
    "bed": dict(
        en="Bed Frame", zh="床架", qty=18, img="bed",
        dims=dict(w=(95, 185), d=(195, 215), h=(88, 122)),
        price=(499, 2299), seats=(1, 2),
        mats=["oak", "walnut", "ash", "fabric", "birch"],
        accents=["metal", "black"],
        styles=["scandinavian", "japandi", "mid_century", "minimalist", "modern"],
        rooms=["bedroom"], tags=["storage_heavy", "family"],
    ),
    "wardrobe": dict(
        en="Wardrobe", zh="衣柜", qty=14, img="wardrobe",
        dims=dict(w=(100, 200), d=(52, 66), h=(180, 220)),
        price=(449, 1899),
        mats=["oak", "walnut", "ash", "birch"],
        accents=["metal", "black", "white"],
        styles=["scandinavian", "japandi", "minimalist", "modern"],
        rooms=["bedroom"], tags=["storage_heavy"],
    ),
    "bookshelf": dict(
        en="Bookcase", zh="书架", qty=18, img="bookshelf",
        dims=dict(w=(58, 180), d=(26, 42), h=(88, 205)),
        price=(119, 749),
        mats=["oak", "ash", "birch", "metal", "walnut"],
        accents=["black", "white"],
        styles=["scandinavian", "japandi", "minimalist", "industrial", "mid_century"],
        rooms=["living_room", "home_office"], tags=["wfh", "storage_heavy", "small_space"],
    ),
    "desk": dict(
        en="Desk", zh="书桌", qty=16, img="desk",
        dims=dict(w=(98, 180), d=(48, 72), h=(72, 77)),
        price=(179, 949),
        mats=["oak", "walnut", "ash", "birch", "metal"],
        accents=["black", "white"],
        styles=["scandinavian", "japandi", "minimalist", "industrial", "modern"],
        rooms=["home_office"], tags=["wfh", "small_space"],
    ),
    "floor_lamp": dict(
        en="Floor Lamp", zh="落地灯", qty=14, img="floor,lamp",
        dims=dict(w=(24, 46), d=(24, 46), h=(138, 182)),
        price=(59, 429),
        mats=["metal", "oak", "ash", "ceramic"],
        accents=["linen", "rattan"],
        styles=["scandinavian", "japandi", "minimalist", "mid_century", "industrial"],
        rooms=["living_room", "bedroom", "home_office"], tags=["reading", "wfh"],
    ),
    "table_lamp": dict(
        en="Table Lamp", zh="台灯", qty=14, img="table,lamp",
        dims=dict(w=(16, 32), d=(16, 32), h=(32, 62)),
        price=(35, 229),
        mats=["ceramic", "metal", "glass", "rattan"],
        accents=["linen", "oak"],
        styles=["scandinavian", "japandi", "boho", "mid_century", "minimalist"],
        rooms=["bedroom", "living_room", "home_office"], tags=["reading", "wfh"],
    ),
    "rug": dict(
        en="Rug", zh="地毯", qty=18, img="rug",
        dims=dict(w=(118, 300), d=(78, 250), h=(1, 3)),
        price=(89, 899),
        mats=["wool", "rattan", "fabric"],
        accents=["cream", "sand"],
        styles=["scandinavian", "boho", "japandi", "mid_century", "coastal"],
        rooms=["living_room", "bedroom", "dining_room"], tags=["pet_friendly", "small_space"],
    ),
    "storage": dict(
        en="Storage Cabinet", zh="收纳柜", qty=14, img="cabinet",
        dims=dict(w=(38, 122), d=(32, 52), h=(56, 182)),
        price=(79, 599),
        mats=["oak", "ash", "birch", "metal", "rattan"],
        accents=["black", "white"],
        styles=["scandinavian", "japandi", "minimalist", "boho", "industrial"],
        rooms=["hallway", "living_room", "bedroom"], tags=["storage_heavy", "small_space"],
    ),
    "outdoor": dict(
        en="Outdoor Furniture", zh="户外家具", qty=16, img="patio,furniture",
        dims=dict(w=(56, 200), d=(56, 100), h=(38, 92)),
        price=(129, 1099),
        mats=["rattan", "metal", "ash", "fabric"],
        accents=["oak", "black"],
        styles=["coastal", "boho", "minimalist", "modern", "scandinavian"],
        rooms=["outdoor"], tags=["outdoor_safe", "low_maintenance"],
    ),
}


def _art(word: str) -> str:
    """英文不定冠词：元音开头用 an。"""
    return "an" if word[:1].lower() in "aeiou" else "a"


def _pick(rng, pool, k):
    k = min(k, len(pool))
    return rng.sample(pool, k)


# SKU 前缀（不能靠 cat[:3] 自动截断，dining_table / dining_chair 会撞车）
SKU_CODE = {
    "sofa": "SOF", "armchair": "ARM", "coffee_table": "CTB", "dining_table": "DTB",
    "dining_chair": "DCH", "bed": "BED", "wardrobe": "WDR", "bookshelf": "BSH",
    "desk": "DSK", "floor_lamp": "FLP", "table_lamp": "TLP", "rug": "RUG",
    "storage": "STG", "outdoor": "OUT",
}


def _make_bases(rng, needed):
    """生成 needed 个全局唯一的产品名基（地名，必要时用「地名+自然词」补足）。"""
    singles = list(NORSE)
    rng.shuffle(singles)
    bases = singles[:needed]
    if len(bases) < needed:
        combos = [f"{a} {b}" for a in NORSE for b in NATURE if a != b]
        rng.shuffle(combos)
        bases.extend(combos[: needed - len(bases)])
    assert len(bases) == len(set(bases)) == needed
    return bases


def build():
    rng = random.Random(SEED)
    total = sum(c["qty"] for c in CATEGORIES.values())
    bases = _make_bases(rng, total)
    bi = 0
    products = []
    counter = 0

    for cat, cfg in CATEGORIES.items():
        for i in range(cfg["qty"]):
            counter += 1
            base = bases[bi]
            bi += 1
            name_en = f"{base} {cfg['en']}"
            name_zh = f"{base} {cfg['zh']}"

            # --- 属性 ---
            style = rng.choice(cfg["styles"])
            mat = rng.choice(cfg["mats"])
            acc = rng.choice(cfg["accents"])
            color = rng.choice(list(COLOR.keys()))
            room = rng.choice(cfg["rooms"])

            w = rng.randrange(cfg["dims"]["w"][0], cfg["dims"]["w"][1] + 1, 2)
            d = rng.randrange(cfg["dims"]["d"][0], cfg["dims"]["d"][1] + 1, 2)
            h = rng.randrange(cfg["dims"]["h"][0], cfg["dims"]["h"][1] + 1)

            # 价格与尺寸轻微相关：越大越贵
            lo, hi = cfg["price"]
            span = (w - cfg["dims"]["w"][0]) / max(1, cfg["dims"]["w"][1] - cfg["dims"]["w"][0])
            price = int(lo + (hi - lo) * (0.35 * span + 0.65 * rng.random()))
            price = max(lo, min(hi, price))

            # --- 标签 ---
            tags = set(_pick(rng, cfg["tags"], rng.randint(1, min(2, len(cfg["tags"])))))
            if w <= cfg["dims"]["w"][0] + (cfg["dims"]["w"][1] - cfg["dims"]["w"][0]) * 0.35:
                tags.add("small_space")
            if mat in ("leather", "metal", "glass", "marble"):
                tags.add("low_maintenance")
            if mat in ("leather", "wool"):
                tags.add("pet_friendly")
            if price <= lo + (hi - lo) * 0.3:
                tags.add("easy_assembly")
            tags = sorted(tags)

            seats = rng.randint(*cfg["seats"]) if "seats" in cfg else None

            # --- 双语描述 ---
            st_en, st_zh = STYLE[style]
            m_en, m_zh = MATERIAL[mat]
            a_en, a_zh = MATERIAL.get(acc) or COLOR[acc]   # accents 池含材质与颜色两类
            r_en, r_zh = ROOM[room]
            c_en, c_zh = COLOR[color]

            feat_en = {
                "small_space": "Its compact footprint keeps tight rooms usable.",
                "family": "Built with reinforced joints to survive daily family use.",
                "reading": "Shaped to sit in for a long chapter, not just a photo.",
                "wfh": "Designed around a full working day, not a quick email.",
                "pet_friendly": "The surface wipes clean, so claws and spills are not a crisis.",
                "low_maintenance": "A damp cloth is the entire care routine.",
                "statement_piece": "It anchors the room rather than filling a corner.",
                "storage_heavy": "Storage is the point here, not an afterthought.",
                "outdoor_safe": "Rated for sun and rain, and it will grey gracefully.",
                "easy_assembly": "Assembles with the supplied key in under twenty minutes.",
            }
            feat_zh = {
                "small_space": "占地紧凑，小空间也能摆得下。",
                "family": "关键连接处做了加固，经得起一家人日常使用。",
                "reading": "为长时间窝着看书设计，不是为了拍照好看。",
                "wfh": "按整天办公的强度设计，不是回封邮件就起身。",
                "pet_friendly": "表面一擦就净，抓痕和泼洒都不算事故。",
                "low_maintenance": "日常打理只需要一块微湿的布。",
                "statement_piece": "它是空间的锚点，不是填角落的家具。",
                "storage_heavy": "收纳是它的主线，不是顺带的功能。",
                "outdoor_safe": "耐晒耐雨，用旧了也会自然地变成灰色。",
                "easy_assembly": "附赠工具，二十分钟内可自行装好。",
            }
            pick_tag = rng.choice(tags)
            f_en, f_zh = feat_en[pick_tag], feat_zh[pick_tag]

            desc_en = (
                f"The {name_en} pairs {m_en} with {_art(a_en)} {a_en} base in a {st_en} silhouette, "
                f"finished in {c_en.lower()}. {f_en} Made for the {r_en}."
            )
            desc_zh = (
                f"{name_zh}以{m_zh}为主体，搭配{a_zh}底座，{st_zh}造型，{c_zh}配色。"
                f"{f_zh}适合{r_zh}。"
            )

            products.append({
                "sku": f"FO-{SKU_CODE[cat]}-{i + 1:03d}",
                "category": cat,
                "category_en": cfg["en"],
                "category_zh": cfg["zh"],
                "name": {"en": name_en, "zh": name_zh},
                "description": {"en": desc_en, "zh": desc_zh},
                "price": price,
                "currency": "USD",
                "dimensions": {"w": w, "d": d, "h": h, "unit": "cm"},
                "seats": seats,
                "material": mat,
                "material_accent": acc,
                "color": color,
                "style": style,
                "room": room,
                "tags": tags,
                "stock": rng.randint(0, 60),
                "rating": round(rng.uniform(3.9, 4.9), 1),
                "review_count": rng.randint(4, 480),
                "lead_time_days": rng.choice([2, 3, 5, 7, 10, 14]),
                "image": f"https://loremflickr.com/640/640/{cfg['img']}?lock={counter}",
            })

    return products


def main():
    products = build()
    OUT.write_text(
        json.dumps(products, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    # ---- 统计 ----
    by_cat = {}
    for p in products:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
    prices = [p["price"] for p in products]
    tags = {}
    for p in products:
        for t in p["tags"]:
            tags[t] = tags.get(t, 0) + 1

    print(f"written: {OUT.name}  ({OUT.stat().st_size / 1024:.1f} KB)")
    print(f"sku_total: {len(products)}")
    print(f"categories: {len(by_cat)}")
    for c, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"   {c:<14} {n}")
    print(f"price_usd: min {min(prices)}  max {max(prices)}  avg {sum(prices) // len(prices)}")
    print(f"tags: {len(tags)}  ->  " + ", ".join(f"{k}:{v}" for k, v in sorted(tags.items(), key=lambda x: -x[1])))
    skus = [p["sku"] for p in products]
    assert len(skus) == len(set(skus)), "duplicate sku"
    names = [p["name"]["en"] for p in products]
    assert len(names) == len(set(names)), "duplicate name"
    for p in products:
        assert p["description"]["en"] and p["description"]["zh"]
        assert p["name"]["zh"] and p["name"]["en"]
    print("integrity: OK (unique sku, unique name, bilingual complete)")


if __name__ == "__main__":
    main()
