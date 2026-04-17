# daily/reflection.py
"""
夕方の反省ルーティン(毎日 22:00 JST 実行)
- 1 日の振り返りスコアリング(A/B/C 各 1〜5 点)
- 連敗カウント更新・強制反省モード管理
- reflection_method.md の改訂チェック(3 日連続 3 点以下)
- AI 行動パターンへの知見追記
"""

import json
import os
import sys
from datetime import datetime, timedelta
import pytz

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

JST = pytz.timezone("Asia/Tokyo")
STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_todays_morning_report() -> dict:
    date_str = datetime.now(JST).strftime("%Y%m%d")
    path = os.path.join(REPORTS_DIR, f"morning_{date_str}.json")
    return load_json(path) if os.path.exists(path) else {}


def interactive_scoring() -> dict:
    """CLI でスコアを入力する"""
    print("\n📝 本日の反省スコアを入力してください(各 1〜5 点)")
    print("  A: 予測精度  B: リスク管理(15%ルール遵守)  C: 情報源の質")
    scores = {}
    for key, label in [("A", "予測精度"), ("B", "リスク管理"), ("C", "情報源の質")]:
        while True:
            try:
                val = int(input(f"  {label} [{key}] (1-5): "))
                if 1 <= val <= 5:
                    scores[key] = val
                    break
            except ValueError:
                pass
            print("  1〜5 の整数を入力してください")
    memo = input("  自由メモ(空 Enter でスキップ): ").strip()
    avg = sum(scores.values()) / 3
    return {**scores, "average": round(avg, 2), "memo": memo}


def append_ai_behavior_log(entry: str):
    path = os.path.join(STATE_DIR, "ai_behavior_log.md")
    with open(path, "a", encoding="utf-8") as f:
        date_str = datetime.now(JST).strftime("%Y-%m-%d")
        f.write(f"\n### {date_str} の観察\n{entry}\n")


def run():
    now = datetime.now(JST)
    print(f"\n{'='*60}")
    print(f"🌙 夕方の反省ルーティン: {now.strftime('%Y-%m-%d %H:%M JST')}")
    print(f"{'='*60}")

    portfolio_path = os.path.join(STATE_DIR, "portfolio.json")
    portfolio = load_json(portfolio_path)

    morning_report = get_todays_morning_report()
    print(f"\n📊 本日のシグナル数: {len(morning_report.get('signals', {}))}")
    print(f"   アラート: {len(morning_report.get('alerts', []))} 件")

    scores = interactive_scoring()
    avg = scores["average"]

    # 連敗管理: 指標 B が 2 点以下 = リスク管理失敗 = 損失とみなす
    if scores.get("B", 5) <= 2:
        portfolio["consecutive_losses"] = portfolio.get("consecutive_losses", 0) + 1
    else:
        portfolio["consecutive_losses"] = 0

    if portfolio["consecutive_losses"] >= 5:
        portfolio["forced_reflection_mode"] = True
        print("\n🚨 連敗 5 回！強制反省モードに移行します")
        print("   取引は継続可能ですが、必ず原因分析を行ってください")

    save_json(portfolio_path, portfolio)

    # スコア記録
    entry = {
        "date": now.strftime("%Y-%m-%d"),
        "score_A": scores["A"],
        "score_B": scores["B"],
        "score_C": scores["C"],
        "average": avg,
        "memo": scores.get("memo", ""),
        "consecutive_losses": portfolio["consecutive_losses"],
    }
    os.makedirs(REPORTS_DIR, exist_ok=True)
    save_json(os.path.join(REPORTS_DIR, f"reflection_{now.strftime('%Y%m%d')}.json"), entry)

    # AI 行動ログへの追記
    if scores.get("memo"):
        append_ai_behavior_log(scores["memo"])

    # reflection_method.md の改訂チェック(3 日連続 3 点以下)
    past_scores = []
    for i in range(1, 4):
        past = (now - timedelta(days=i)).strftime("%Y%m%d")
        p = os.path.join(REPORTS_DIR, f"reflection_{past}.json")
        if os.path.exists(p):
            past_entry = load_json(p)
            past_scores.append(past_entry.get("average", 5.0))

    if len(past_scores) == 3 and all(s <= 3.0 for s in past_scores):
        print("\n⚠️ 反省スコアが 3 日連続 3 点以下です。")
        print("   → state/reflection_method.md の改訂を検討してください")

    print(f"\n✅ 反省完了: スコア平均 {avg:.1f} 点")
    return entry


if __name__ == "__main__":
    run()
