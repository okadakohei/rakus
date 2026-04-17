# tools/tax_calculator.py
"""税計算モジュール"""

import json
import os
from datetime import datetime

STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")
TAX_TRACKER_PATH = os.path.join(STATE_DIR, "tax_tracker.json")


def load_tax_tracker() -> dict:
    with open(TAX_TRACKER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tax_tracker(data: dict):
    data["updated_at"] = datetime.now().isoformat()
    with open(TAX_TRACKER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_trade_result(market: str, gain_loss: float):
    """取引結果を記録する(gain_loss: プラスで利益、マイナスで損失)"""
    tracker = load_tax_tracker()
    section = tracker.get(market, {})
    if gain_loss >= 0:
        section["realized_gain"] = section.get("realized_gain", 0) + gain_loss
    else:
        section["realized_loss"] = section.get("realized_loss", 0) + abs(gain_loss)
    tracker[market] = section
    save_tax_tracker(tracker)


def get_net_profit_overview() -> dict:
    """現在の損益サマリーを返す"""
    tracker = load_tax_tracker()
    threshold = tracker.get("tax_free_threshold", 200000)

    summary = {}
    total_taxable = 0

    for market in ["etf", "fx"]:
        sec = tracker.get(market, {})
        gain = sec.get("realized_gain", 0)
        loss = sec.get("realized_loss", 0)
        carryover = sec.get("loss_carryover_from_prev_years", 0)
        net = gain - loss - carryover
        summary[market] = {"net": net, "gain": gain, "loss": loss, "carryover": carryover}
        total_taxable += net

    crypto = tracker.get("crypto", {})
    crypto_net = crypto.get("realized_gain", 0) - crypto.get("realized_loss", 0)
    summary["crypto"] = {"net": crypto_net, "note": "総合課税・ETF/FX と損益通算不可"}

    summary["total_申告分離_net"] = total_taxable
    summary["tax_free_threshold"] = threshold
    summary["approaching_threshold"] = total_taxable > threshold * 0.8

    if summary["approaching_threshold"]:
        print(
            f"⚠️ 警告: 年間利益 {total_taxable:,.0f} 円が"
            f" 20 万円ラインの 80% に到達。ポジション縮小を検討してください。"
        )
    return summary


def year_end_reset(carry_over_losses: dict = None):
    """翌年 1 月に呼び出す。損失繰越を引き継いで tracker をリセット。
    あわせて portfolio.json の wipeout_acknowledged を False にリセットする。
    """
    tracker = load_tax_tracker()
    new_year = tracker["year"] + 1
    co = carry_over_losses or {}

    new_tracker = {
        "year": new_year,
        "updated_at": datetime.now().isoformat(),
        "etf": {
            "realized_gain": 0,
            "realized_loss": 0,
            "loss_carryover_from_prev_years": co.get("etf", 0),
        },
        "fx": {
            "realized_gain": 0,
            "realized_loss": 0,
            "loss_carryover_from_prev_years": co.get("fx", 0),
        },
        "crypto": {
            "realized_gain": 0,
            "realized_loss": 0,
            "note": "総合課税・損失繰越不可",
        },
        "tax_free_threshold": 200000,
        "notes": [f"{new_year - 1} 年分から繰越"],
    }
    save_tax_tracker(new_tracker)
    print(f"✅ tax_tracker.json を {new_year} 年版にリセットしました")

    # portfolio.json の wipeout_acknowledged を年次リセット
    portfolio_path = os.path.join(STATE_DIR, "portfolio.json")
    try:
        with open(portfolio_path, "r", encoding="utf-8") as f:
            portfolio = json.load(f)
        portfolio["wipeout_acknowledged"] = False
        with open(portfolio_path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        print("✅ portfolio.json の wipeout_acknowledged を False にリセットしました")
    except Exception as e:
        print(f"⚠️ portfolio.json のリセットに失敗しました: {e}")
