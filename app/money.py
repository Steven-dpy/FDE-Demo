# -*- coding: utf-8 -*-
"""Nook · 货币与金额显示

商品库的**基准货币是 USD**（数据只有一套，不重复维护两套价格）。

规则：
- 英文界面：只显示 USD
- 中文界面：双币显示（US$1,299 ≈ ¥9,353），
  并且**中文用户输入的预算按人民币理解**——因为他在界面上看到的就是 ¥。

汇率来自环境变量 NOOK_USD_CNY，便于演示时调整。
"""
from __future__ import annotations

import os

USD_CNY = float(os.environ.get("NOOK_USD_CNY", "7.20"))


def to_usd(amount, lang):
    """用户输入的金额 → 商品库基准货币（USD）。"""
    if amount is None:
        return None
    return float(amount) / USD_CNY if lang == "zh" else float(amount)


def from_usd(usd, lang):
    """基准货币 → 用户所在币种。"""
    return float(usd) * USD_CNY if lang == "zh" else float(usd)


def fmt(usd, lang) -> str:
    """完整展示：中文双币，英文单币。"""
    usd = float(usd)
    if lang == "zh":
        return f"US${usd:,.0f} ≈ ¥{round(usd * USD_CNY):,.0f}"
    return f"US${usd:,.0f}"


def fmt_short(usd, lang) -> str:
    """短展示：用于句子里嵌金额。"""
    usd = float(usd)
    if lang == "zh":
        return f"¥{round(usd * USD_CNY):,.0f}"
    return f"US${usd:,.0f}"


def rate_note(lang) -> str:
    return (f"参考汇率 1 美元 ≈ {USD_CNY:.2f} 元人民币，实际以结算为准"
            if lang == "zh" else
            f"Prices in USD. Reference rate: 1 USD ≈ {USD_CNY:.2f} CNY")
