# -*- coding: utf-8 -*-
"""Nook · 命令行演示

跑法：
  python cli_demo.py          # 预置对话（中英各一段）
  python cli_demo.py zh       # 只跑中文
  python cli_demo.py en       # 只跑英文
  python cli_demo.py -i       # 交互模式
"""
from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from concierge import Session

USER = {"zh": "👤", "en": "🧑"}
BOT = "🛋️"
LINE = "─" * 74

SCRIPTS = {
    "zh": [
        "我想弄个能窝着看书的地方",
        "预算一万左右",
        "客厅用的，最好北欧风，宽一点没关系",
        "我要买个手机",
    ],
    "en": [
        "I want a corner where I can curl up and read",
        "budget around 1400",
        "for the living room, scandinavian style please",
        "do you also sell laptops?",
    ],
}


def show(res, lang):
    print(f"{BOT} {res['text']}")
    if res.get("bundle"):
        b = res["bundle"]
        print(f"   ↳ 成套装：{b['title']}  合计 {b.get('total_display') or b['total']}")
    for i, p in enumerate(res["products"], 1):
        d = p["dimensions"]
        print(f"\n   [{i}] {p['name']}   {p.get('price_display') or p['price']}")
        print(f"       {p['reason']}")
        print(f"       {d['w']}×{d['d']}×{d['h']}cm · ★{p['rating']} ({p['review_count']}) "
              f"· {p['sku']} · 库存 {p['stock']}")
    if not res["products"]:
        print("   （无推荐）")
    if res["meta"].get("intent"):
        print(f"   ·intent={res['meta']['intent']}"
              + (f" relaxed={res['meta']['relaxed']}" if res["meta"].get("relaxed") else ""))
    print()


def run_script(lang):
    print(f"\n{'=' * 74}\n  预置对话 · {'中文' if lang == 'zh' else 'English'}\n{'=' * 74}\n")
    s = Session(lang=lang)
    for turn in SCRIPTS[lang]:
        print(f"{USER[lang]} {turn}")
        show(s.respond(turn), lang)


def run_interactive(lang):
    print(f"\n{LINE}\n  交互模式（输入 q 退出）· 语言={lang}\n{LINE}\n")
    s = Session(lang=lang)
    while True:
        try:
            text = input(f"{USER[lang]} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in ("q", "quit", "exit", ""):
            break
        show(s.respond(text), lang)


def main():
    args = [a for a in sys.argv[1:]]
    if "-i" in args:
        lang = "en" if "en" in args else "zh"
        run_interactive(lang)
        return
    langs = [a for a in args if a in ("zh", "en")] or ["zh", "en"]
    for lg in langs:
        run_script(lg)


if __name__ == "__main__":
    main()
