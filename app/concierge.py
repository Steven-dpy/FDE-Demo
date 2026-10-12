# -*- coding: utf-8 -*-
"""Nook · 对话编排层（Concierge）

用户的一句话 → 槽位 → 澄清问题 / 检索 → 带理由的推荐 / 场景组包

三条产品原则（写进代码，因为它们是设计决定，不是实现细节）：

1. **最多连问两个问题，然后必须先给一版推荐。**
   导购不是问卷。用户说"我想弄个看书的地方"，你连问三个问题，他就走了。
2. **推荐必须给理由。**
   导购和搜索框的区别就在这里——搜索给列表，导购说"为什么这个适合你"。
3. **没有结果就说没有，放宽了什么要说清。**
   绝不硬凑一个不相关的商品充数。
"""
from __future__ import annotations

import re

import money
from catalog import CATEGORY_ZH, ROOM_ZH, get_catalog

# ------------------------------------------------------------------ 展示用翻译
STYLE_ZH = {"scandinavian": "北欧", "japandi": "日式北欧", "mid_century": "中古",
            "minimalist": "极简", "industrial": "工业", "coastal": "海岸",
            "boho": "波西米亚", "modern": "现代"}
MAT_ZH = {"oak": "实木橡木", "walnut": "胡桃木", "ash": "白蜡木", "birch": "桦木多层板",
          "metal": "粉末喷涂钢", "linen": "水洗亚麻", "boucle": "羊羔绒", "velvet": "天鹅绒",
          "leather": "头层牛皮", "fabric": "混纺面料", "rattan": "天然藤编",
          "wool": "手工羊毛", "marble": "哑光大理石", "ceramic": "釉面陶瓷", "glass": "钢化玻璃"}
TAG_ZH = {"small_space": "占地紧凑，小空间放得下", "family": "加固结构，适合有孩子的家庭",
          "reading": "为长时间窝着看书设计", "wfh": "按整天办公的强度设计",
          "pet_friendly": "表面一擦就净，宠物友好", "low_maintenance": "日常打理只需一块湿布",
          "statement_piece": "能撑起整个空间", "storage_heavy": "收纳量大",
          "outdoor_safe": "耐晒耐雨", "easy_assembly": "免工具，二十分钟能装好"}

RELAX_ZH = {"max_width": "尺寸上限", "material": "材质", "style": "风格", "tags": "特殊需求"}
RELAX_EN = {"max_width": "size limit", "material": "material", "style": "style", "tags": "special requirement"}

# ------------------------------------------------------------------ 抽取规则
CATEGORY_PATTERNS = [
    ("armchair",     ["单人沙发", "单人椅", "扶手椅", "休闲椅", "armchair", "accent chair"]),
    ("sofa",         ["三人沙发", "沙发", "sofa", "couch"]),
    ("coffee_table", ["茶几", "边几", "coffee table", "side table"]),
    ("dining_table", ["餐桌", "饭桌", "dining table"]),
    ("dining_chair", ["餐椅", "dining chair"]),
    ("wardrobe",     ["衣柜", "衣橱", "wardrobe"]),
    ("bookshelf",    ["书架", "书柜", "置物架", "bookshelf", "bookcase"]),
    ("desk",         ["书桌", "办公桌", "工作台", "desk"]),
    ("floor_lamp",   ["落地灯", "floor lamp"]),
    ("table_lamp",   ["台灯", "table lamp"]),
    ("rug",          ["地毯", "地垫", "rug", "carpet"]),
    ("storage",      ["收纳柜", "储物柜", "边柜", "床头柜", "storage", "cabinet", "sideboard"]),
    ("outdoor",      ["户外家具", "patio", "outdoor furniture"]),
    ("bed",          ["床架", "双人床", "床", "bed frame", "bed"]),
]
ROOM_PATTERNS = [
    ("living_room", ["客厅", "起居室", "living room", "lounge"]),
    ("bedroom",     ["卧室", "睡房", "bedroom"]),
    ("dining_room", ["餐厅", "dining room"]),
    ("home_office", ["书房", "home office", "study", "work from home", "远程办公"]),
    ("outdoor",     ["阳台", "庭院", "露台", "balcony", "patio"]),
    ("hallway",     ["玄关", "走廊", "hallway", "entryway"]),
]
STYLE_PATTERNS = [
    ("scandinavian", ["北欧", "scandinavian"]),
    ("japandi",      ["日式", "侘寂", "japandi"]),
    ("mid_century",  ["中古", "复古", "mid-century", "mid century"]),
    ("minimalist",   ["极简", "简约", "minimalist"]),
    ("industrial",   ["工业", "industrial"]),
    ("coastal",      ["海岸", "coastal"]),
    ("boho",         ["波西米亚", "boho"]),
]
MATERIAL_PATTERNS = [
    ("oak",     ["橡木", "oak"]), ("walnut", ["胡桃木", "walnut"]),
    ("ash",     ["白蜡木", "ash"]), ("leather", ["真皮", "牛皮", "leather"]),
    ("velvet",  ["天鹅绒", "velvet"]), ("boucle", ["羊羔绒", "boucle"]),
    ("fabric",  ["布艺", "fabric"]), ("rattan", ["藤编", "藤", "rattan"]),
    ("marble",  ["大理石", "marble"]), ("metal", ["金属", "metal"]),
]
TAG_PATTERNS = [
    ("small_space",  ["小户型", "小空间", "地方小", "空间不大", "租房", "small apartment", "studio", "tight space"]),
    ("pet_friendly", ["宠物", "猫", "狗", "pet"]),
    ("family",       ["孩子", "小孩", "一家人", "家庭", "family", "kids"]),
    ("wfh",          ["居家办公", "在家办公", "work from home", "wfh"]),
    ("storage_heavy", ["收纳", "储物", "storage"]),
    ("easy_assembly", ["免安装", "好装", "easy to assemble"]),
]

BUDGET_RES = [
    re.compile(r"(?:预算|budget|不超过|under|below|within|less than|以内|左右|大概)\D{0,8}(\d[\d,]*)\s*(?:元|块|美金|美元|usd|dollars)?"),
    re.compile(r"[$￥¥]\s*(\d[\d,]*)\s*(?:usd|dollars)?"),
    re.compile(r"(\d[\d,]*)\s*(?:元|块|usd|dollars)\s*(?:以内|以下|左右)?"),
    re.compile(r"(\d[\d,]*)\s*(?:元|块|美金|美元|usd|dollars)"),
    re.compile(r"(\d[\d,]*)\s*(?:元|块)?\s*的?\s*(?:预算|budget)"),   # 「3000 的预算」
]
WIDTH_RES = [
    re.compile(r"(?:宽度?|width|不超过|不宽于|no wider than)\D{0,8}(\d{2,3})\s*(?:cm|厘米|公分)?"),
    re.compile(r"(\d{2,3})\s*(?:cm|厘米|公分)\s*(?:以内|以下|宽)"),
]
SEATS_RE = re.compile(r"(\d)\s*(?:人|座|seater|seat)")

OUT_OF_SCOPE = ["手机", "电脑", "笔记本", "耳机", "衣服", "鞋", "食品", "化妆品",
                "iphone", "laptop", "headphone", "clothes", "shoes", "grocery"]

# 中文数字：用户会说「预算两千五」，而不是「预算 2500」
CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}
CN_CHARS = "".join(CN_DIGITS) + "".join(CN_UNITS)

CN_BUDGET_RES = [
    # 注意 \D{0,4}? 必须惰性：贪婪会把「三万」整个吃掉，只剩一个「万」
    re.compile(r"(?:预算|大概|差不多|不超过|最多)\D{0,4}?([%s]{1,8})" % CN_CHARS),
    re.compile(r"([%s]{1,8})\s*(?:元|块钱|块)" % CN_CHARS),
    re.compile(r"([%s]{1,8})\s*(?:左右|以内|以下|上下)" % CN_CHARS),
    re.compile(r"([%s]{1,8})\s*(?:元|块)?\s*的?\s*(?:预算)" % CN_CHARS),   # 「三万的预算」
]


def cn2num(s: str):
    """把「两千五」→2500、「一千二」→1200、「三百五」→350、「一万五」→15000。

    规则：结尾若是裸数字，取上一个单位的 1/10（中文口语的省略读法）。
    """
    if not s:
        return None
    total = section = number = last_unit = 0
    for ch in s:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
        elif ch in CN_UNITS:
            u = CN_UNITS[ch]
            if u == 10000:
                section = (section + number) * u
                total += section
                section = 0
            else:
                section += (number or 1) * u
            number = 0
            last_unit = u
        else:
            return None
    if number:
        section += number * (last_unit // 10) if last_unit >= 10 else number
    return total + section

# ------------------------------------------------------------------ 场景组包
# 「用户没有明确目标」的真正解法：不是找一个商品，是给一个成套的方案。
LOOKS = {
    "reading_corner": {
        "kw": ["阅读角", "看书", "读书", "窝着", "读书角", "reading nook", "reading corner",
               "book corner", "curl up", "read", "reading", "cozy corner", "cosy corner"],
        "cats": ["armchair", "floor_lamp", "coffee_table", "rug"],
        "title": {"en": "a reading corner", "zh": "一个阅读角"},
        "why": {
            "en": "A reading corner only works as a set: somewhere you can sit for an hour, "
                  "light coming over your shoulder, and a surface to put a cup down.",
            "zh": "阅读角是成套才成立的：一把能坐一小时的椅子、一盏从肩后照过来的灯，"
                  "再加一个能放下杯子的台面。",
        },
    },
    "home_office": {
        "kw": ["居家办公", "在家办公", "书房", "工作区", "work from home", "home office", "remote work"],
        "cats": ["desk", "bookshelf", "table_lamp"],
        "title": {"en": "a home office", "zh": "一个居家办公区"},
        "why": {
            "en": "A desk is only half of it. You need somewhere for the reference books and "
                  "light that does not reflect off the screen.",
            "zh": "光有桌子只算一半。你还需要放参考资料的地方，以及不反光的照明。",
        },
    },
    "family_living": {
        "kw": ["一家人", "有孩子", "小孩", "家庭", "family", "kids", "有娃"],
        "cats": ["sofa", "rug", "storage"],
        "title": {"en": "a family living room", "zh": "一个有孩子的客厅"},
        "why": {
            "en": "With kids in the house the priorities change: things that survive daily use, "
                  "a floor that is soft to fall on, and storage you can reach in one motion.",
            "zh": "家里有孩子，优先级就变了：经得起天天折腾的家具、摔一下不疼的地面，"
                  "还有一伸手就能收东西的柜子。",
        },
    },
    "small_apartment": {
        "kw": ["小户型", "小空间", "地方小", "空间不大", "租房", "small apartment", "studio", "tiny"],
        "cats": ["sofa", "coffee_table", "storage"],
        "tags": ["small_space"],
        "title": {"en": "a small apartment", "zh": "小户型"},
        "why": {
            "en": "In a small flat, footprint matters more than anything else on the spec sheet.",
            "zh": "小户型里，占地比任何参数都重要。",
        },
    },
    "balcony": {
        "kw": ["阳台", "露台", "庭院", "balcony", "patio", "outdoor space"],
        "cats": ["outdoor", "floor_lamp", "rug"],
        "title": {"en": "a balcony setup", "zh": "一个阳台角落"},
        "why": {
            "en": "Outdoor pieces have to survive weather first; comfort is the second question.",
            "zh": "户外家具先得扛得住天气，舒适度是第二个问题。",
        },
    },
}


# ------------------------------------------------------------------ 抽取
def _match(text, patterns):
    t = text.lower()
    return [key for key, kws in patterns if any(k in t for k in kws)]


def _num(s):
    return int(s.replace(",", ""))


def extract(text: str) -> dict:
    """从一句话里抽槽位。规则实现，不依赖 LLM，因此永远可用。"""
    t = text.lower()
    slots = {}

    cats = _match(t, CATEGORY_PATTERNS)
    if cats:
        slots["category"] = cats

    rooms = _match(t, ROOM_PATTERNS)
    # "办公" 单独出现时算 home_office
    if not rooms and re.search(r"办公|工作", t):
        rooms = ["home_office"]
    if rooms:
        slots["room"] = rooms

    st = _match(t, STYLE_PATTERNS)
    if st:
        slots["style"] = st
    mt = _match(t, MATERIAL_PATTERNS)
    if mt:
        slots["material"] = mt
    tg = _match(t, TAG_PATTERNS)
    if tg:
        slots["tags"] = tg

    for rx in BUDGET_RES:
        m = rx.search(t)
        if m:
            v = _num(m.group(1))
            if 20 <= v <= 200000:
                slots["price_max"] = v
                break
    if "price_max" not in slots:                 # 「两千五」这类中文数字
        for rx in CN_BUDGET_RES:
            m = rx.search(t)
            if m:
                v = cn2num(m.group(1))
                if v and 20 <= v <= 200000:
                    slots["price_max"] = v
                    break
    for rx in WIDTH_RES:
        m = rx.search(t)
        if m:
            v = _num(m.group(1))
            if 30 <= v <= 400:
                slots["max_width"] = v
                break
    m = SEATS_RE.search(t)
    if m:
        slots["seats_min"] = int(m.group(1))

    return slots


def detect_look(text: str):
    """场景识别。拉丁关键词按词边界匹配（避免 read 命中 already/spread），CJK 用子串。"""
    t = text.lower()
    for key, cfg in LOOKS.items():
        for k in cfg["kw"]:
            if k.isascii():
                if re.search(r"\b" + re.escape(k) + r"\b", t):
                    return key
            elif k in t:
                return key
    return None


# ------------------------------------------------------------------ 会话
class Session:
    def __init__(self, lang="zh", catalog=None):
        self.lang = lang if lang in ("zh", "en") else "zh"
        self.cat = catalog or get_catalog()
        self.slots: dict = {}
        self.asked: set = set()
        self.turns = 0
        self.history: list = []
        self.budget_raw = None            # 用户原话里的金额（他自己的币种）

    # ---------------- 内部工具
    def _merge(self, new: dict):
        for k, v in new.items():
            if isinstance(v, list):
                cur = set(self.slots.get(k, []))
                self.slots[k] = sorted(cur | set(v))
            elif k in ("price_max", "max_width"):
                old = self.slots.get(k)
                self.slots[k] = v if old is None else min(old, v)
            elif k == "seats_min":
                self.slots[k] = max(self.slots.get(k, 0), v)

    def _filters(self, extra=None):
        s = self.slots
        f = {
            "category": s.get("category"),
            "room": s.get("room"),
            "style": s.get("style"),
            "material": s.get("material"),
            "tags": s.get("tags"),
            "price_max": s.get("price_max"),
            "max_width": s.get("max_width"),
            "seats_min": s.get("seats_min"),
            "in_stock": True,
        }
        if extra:
            f.update(extra)
        return f

    def _budget_label(self, lang=None) -> str:
        """预算显示用**用户自己说的那个数**，而不是 USD 换算回去的近似值。

        否则用户说「预算一万」，回显成「¥9,994」——看起来像系统算错了。
        """
        lang = lang or self.lang
        if self.budget_raw is not None:
            return f"¥{self.budget_raw:,}" if lang == "zh" else f"US${self.budget_raw:,}"
        return money.fmt_short(self.slots.get("price_max") or 0, lang)

    def _reason(self, p, lang=None):
        """推荐理由：导购和搜索框的区别就在这里。价格由卡片单独展示，这里不重复。"""
        lang = lang or self.lang
        if lang == "en":
            bits = [f"{p['style'].replace('_', '-')} style", f"{p['material']} body"]
            if p["tags"]:
                bits.append(p["tags"][0].replace("_", " "))
            s = ", ".join(bits) + "."
            s += f" Ships in {p['lead_time_days']} days, {p['stock']} in stock."
            if self.slots.get("price_max"):
                s += f" Within your {self._budget_label(lang)} budget."
            return s
        bits = [f"{STYLE_ZH.get(p['style'], p['style'])}风格",
                f"{MAT_ZH.get(p['material'], p['material'])}主体"]
        s = "、".join(bits)
        if p["tags"]:
            s += f"；{TAG_ZH.get(p['tags'][0], p['tags'][0])}"
        s += f"。{p['stock']} 件现货，{p['lead_time_days']} 天可发"
        if self.slots.get("price_max"):
            s += f"，在你 {self._budget_label(lang)} 的预算内"
        return s + "。"

    def _slim(self, p, lang=None):
        lang = lang or self.lang
        return {
            "sku": p["sku"],
            "name": p["name"][lang],
            "category": p["category"],
            "category_label": p["category_zh"] if lang == "zh" else p["category_en"],
            "price": p["price"],
            "currency": p["currency"],
            "price_display": money.fmt(p["price"], lang),
            "price_local": money.fmt_short(p["price"], lang),
            "image": p["image"],
            "dimensions": p["dimensions"],
            "rating": p["rating"],
            "review_count": p["review_count"],
            "stock": p["stock"],
            "lead_time_days": p["lead_time_days"],
            "reason": self._reason(p, lang),
        }

    def _reply(self, text, products=None, bundle=None, ask=None, meta=None):
        r = {"text": text, "products": products or [], "bundle": bundle,
             "ask": ask, "meta": meta or {}}
        self.history.append(("nook", text))
        return r

    # ---------------- 场景组包
    def _bundle(self, look_key):
        cfg = LOOKS[look_key]
        cats = cfg["cats"][:3]
        budget = self.slots.get("price_max")
        base = {k: v for k, v in self._filters().items()
                if k not in ("category", "price_max")}
        if cfg.get("tags"):
            base["tags"] = sorted(set(base.get("tags") or []) | set(cfg["tags"]))

        picks, used = [], 0
        if budget:
            avgs = {c: self.cat.category_avg_price(c) for c in cats}
            tot = sum(avgs.values()) or 1
            for c in cats:
                share = max(60, int((budget - used) * avgs[c] / tot))
                res, _ = self.cat.search("", {**base, "category": [c], "price_max": share}, limit=1)
                if res:
                    picks.append(res[0])
                    used += res[0]["price"]
        else:
            for c in cats:
                res, _ = self.cat.search("", {**base, "category": [c]}, limit=1)
                if res:
                    picks.append(res[0])

        if not picks:
            return None, None
        total = used if budget else sum(p["price"] for p in picks)
        return picks, {
            "key": look_key,
            "title": cfg["title"][self.lang],
            "why": cfg["why"][self.lang],
            "total": total,
            "total_display": money.fmt(total, self.lang),
        }

    # ---------------- 主入口
    def respond(self, text: str) -> dict:
        self.turns += 1
        self.history.append(("user", text))
        new = extract(text)
        if "price_max" in new:          # 中文界面下用户说的「一万」是人民币，换算成基准货币
            self.budget_raw = new["price_max"]
            new["price_max"] = max(1, int(money.to_usd(new["price_max"], self.lang)))
        self._merge(new)

        look = detect_look(text) or self.slots.get("look")
        if look:
            self.slots["look"] = look

        # --- 超出经营范围，直接说清（不硬凑） ---
        if any(k in text.lower() for k in OUT_OF_SCOPE):
            msg = ("I can only help with what Fern & Oak actually sells — sofas, tables, "
                   "storage, lighting, rugs and outdoor pieces. I can't help with that one."
                   if self.lang == "en" else
                   "我只能帮你从 Fern & Oak 的商品里挑家具——沙发、桌子、收纳、灯具、地毯和户外家具。"
                   "这个我确实帮不上，就不乱推荐了。")
            return self._reply(msg, meta={"intent": "out_of_scope"})

        anchor = self.slots.get("category") or self.slots.get("look") or self.slots.get("room")

        # --- 信息不足：最多问两个问题 ---
        if not anchor:
            if "room" not in self.asked and self.turns <= 2:
                self.asked.add("room")
                q = ("Which room are you furnishing?" if self.lang == "en"
                     else "你想布置哪个空间？（客厅 / 卧室 / 餐厅 / 书房 / 阳台）")
                head = ("Sure — let's narrow it down." if self.lang == "en"
                        else "好的，先缩小一下范围。")
                return self._reply(head, ask=q, meta={"intent": "clarify_room"})
            msg = ("I couldn't find anything in the catalogue that matches. "
                   "Tell me the room or the kind of piece, and I'll try again."
                   if self.lang == "en" else
                   "按这个我没在商品里找到对应的东西。你说一下是哪个空间、或者想要哪一类家具，我再找一次。")
            return self._reply(msg, meta={"intent": "no_anchor"})

        # --- 场景组包优先 ---
        if self.slots.get("look"):
            picks, b = self._bundle(self.slots["look"])
            if picks:
                prods = [self._slim(p) for p in picks]
                total = money.fmt(b["total"], self.lang) if b["total"] else ""
                if self.lang == "en":
                    head = (f"Then you're building {b['title']}. {b['why']} "
                            f"Here's a set that works together")
                    head += f" — about {total} total." if total else "."
                else:
                    head = f"那你要的是{b['title']}。{b['why']}下面这套是配得上的"
                    head += f"，合计约 {total}。" if total else "。"
                ask = None
                if not self.slots.get("price_max") and "budget" not in self.asked:
                    self.asked.add("budget")
                    ask = ("What's your budget for the set?" if self.lang == "en"
                           else "这套你大概想花多少？说人民币就行，我按预算重新配。")
                    head += " " + ask
                return self._reply(head, prods, bundle=b, ask=ask,
                                   meta={"intent": "bundle", "look": self.slots["look"]})

        # --- 常规检索 ---
        q = text
        results, meta = self.cat.search(q, self._filters(), limit=5)
        if not results:
            results, meta = self.cat.search("", self._filters(), limit=5)
        if not results:
            msg = ("Nothing in the catalogue fits those conditions. Which one matters most — "
                   "price, size, or style? I'll re-search."
                   if self.lang == "en" else
                   "按这些条件，商品里没有合适的。你最在意哪一条——价格、尺寸还是风格？我重新找。")
            return self._reply(msg, meta={"intent": "no_result"})

        prods = [self._slim(p) for p in results]
        if self.lang == "en":
            head = f"Here are {len(prods)} that fit."
        else:
            head = f"找到 {len(prods)} 件合适的。"
        if meta.get("relaxed"):
            names = ", ".join(RELAX_EN[k] for k in meta["relaxed"]) if self.lang == "en" \
                else "、".join(RELAX_ZH[k] for k in meta["relaxed"])
            head += (f" I had to relax your {names} to find them." if self.lang == "en"
                     else f"为了有结果，我放宽了「{names}」。")

        ask = None
        if not self.slots.get("price_max") and "budget" not in self.asked and self.turns <= 3:
            self.asked.add("budget")
            ask = ("What's your budget?" if self.lang == "en"
                   else "预算大概多少？人民币就行，我按预算再筛一遍。")
            head += " " + ask

        return self._reply(head, prods, ask=ask,
                           meta={"intent": "recommend", "matched": meta.get("matched"),
                                 "relaxed": meta.get("relaxed")})
