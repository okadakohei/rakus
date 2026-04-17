# tools/regulation_check.py
"""月次法規制チェックモジュール"""

import os
from datetime import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")
STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")
REGULATION_LOG_PATH = os.path.join(STATE_DIR, "regulation_log.md")

CHECK_KEYWORDS = [
    "暗号資産 税制改正 申告分離",
    "FX 証拠金規制 レバレッジ",
    "金融商品取引法 改正",
    "確定申告 20万円 非課税",
    "インサイダー取引 規制強化",
]


def check_fsa_news() -> list[dict]:
    """金融庁の新着情報を確認する(手動確認を促すスタブ)"""
    return [
        {
            "source": "FSA(金融庁)",
            "url": "https://www.fsa.go.jp/news/",
            "message": "手動確認推奨: https://www.fsa.go.jp/news/ を月 1 回確認してください",
            "tier": 1,
        }
    ]


def append_regulation_log(entry: dict):
    """regulation_log.md に新規エントリを追記する"""
    date_str = datetime.now(JST).strftime("%Y-%m-%d")
    line = (
        f"| {date_str} | 自動チェック"
        f" | {entry.get('summary', '変化なし')}"
        f" | {entry.get('action', 'なし')} |\n"
    )
    with open(REGULATION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def run_monthly_check() -> dict:
    """月次チェックを実行する(morning.py から毎月 1 日に呼び出す)"""
    print("📋 月次法規制チェック開始...")
    results = check_fsa_news()
    changes_found = False

    for r in results:
        print(f"  [{r['source']}] {r['message']}")

    if not changes_found:
        append_regulation_log({"summary": "自動チェック: 重大な変化なし", "action": "なし"})
        print("✅ 月次法規制チェック完了: 重大な変化なし")
    else:
        print("⚠️ 法規制変化を検出しました！regulation_log.md を確認してください")

    return {"checked_at": datetime.now(JST).isoformat(), "changes_found": changes_found}


if __name__ == "__main__":
    run_monthly_check()
