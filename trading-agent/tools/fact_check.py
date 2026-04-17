# tools/fact_check.py
"""ファクトチェック・情報源 Tier 判定モジュール"""

import os
import re
from datetime import datetime

STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")

TIER1_DOMAINS = [
    "federalreserve.gov", "boj.or.jp", "fsa.go.jp",
    "sec.gov", "mof.go.jp", "zaif.jp", "oanda.com",
]
TIER2_DOMAINS = [
    "reuters.com", "bloomberg.com", "bloomberg.co.jp",
    "nikkei.com", "wsj.com", "ft.com",
]
TIER3_DOMAINS = ["seekingalpha.com", "zerohedge.com"]


def classify_tier(url: str) -> int:
    """URL から Tier を判定する"""
    domain = re.sub(r"https?://", "", url).split("/")[0].lower()
    for d in TIER1_DOMAINS:
        if d in domain:
            return 1
    for d in TIER2_DOMAINS:
        if d in domain:
            return 2
    for d in TIER3_DOMAINS:
        if d in domain:
            return 3
    return 4


def fact_check_news(news_items: list[dict]) -> list[dict]:
    """
    ニュースリストに Tier 判定・補正コメントを付与する
    news_items: [{"title": str, "url": str, "content": str}]
    """
    results = []
    for item in news_items:
        url = item.get("url", "")
        tier = classify_tier(url)
        if tier == 4:
            correction = "🚫 Tier4 情報: 匿名・SNS。投資判断には使用しない"
        elif tier == 3:
            correction = "⚠️ Tier3 情報: バイアス・誇張を差し引いて事実部分のみ参照"
        else:
            correction = ""
        results.append({
            **item,
            "tier": tier,
            "correction": correction,
            "checked_at": datetime.now().isoformat(),
        })
    return results


def extract_facts(text: str) -> str:
    """テキストから主観的表現を除去して事実部分のみを返す(簡易版)"""
    opinion_patterns = [
        r"〜と思われる", r"〜だろう", r"〜に違いない",
        r"おそらく", r"恐らく", r"きっと",
        r"I think", r"I believe", r"probably", r"likely",
    ]
    result = text
    for pattern in opinion_patterns:
        result = re.sub(pattern, "[意見]", result)
    return result


def should_trust(tier: int, market_condition: str = "normal") -> bool:
    """Tier と市況に基づいて信頼すべきかどうかを返す"""
    if market_condition == "volatile":
        return tier <= 2
    return tier <= 3
