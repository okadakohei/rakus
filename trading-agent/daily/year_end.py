# daily/year_end.py
"""
年末処理(12 月 31 日に実行)
- 年次レポート生成(annual_report_YYYY.json)
- 損失繰越計算
- 翌年用 tax_tracker リセット
"""

import json
import os
import sys
from datetime import datetime
import pytz

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from tools.tax_calculator import get_net_profit_overview, year_end_reset

JST = pytz.timezone("Asia/Tokyo")
STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def generate_annual_report(year: int) -> dict:
    """annual_report_YYYY.json を生成する"""
    tax_overview = get_net_profit_overview()

    with open(os.path.join(STATE_DIR, "portfolio.json"), "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    report = {
        "year": year,
        "generated_at": datetime.now(JST).isoformat(),
        "portfolio_snapshot": portfolio,
        "tax_summary": tax_overview,
        "total_capital": portfolio.get("total_capital", 0),
        "total_value": portfolio.get("total_value", 0),
        "total_trades": portfolio.get("total_trades", 0),
        "notes": [
            "この年次レポートは自動生成されたものです。",
            "確定申告時は各取引所の公式レポートと照合してください。",
            "損失繰越は来年の tax_tracker.json に引き継がれます。",
        ],
    }

    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"annual_report_{year}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 年次レポート生成: {path}")
    return report


def run():
    now = datetime.now(JST)
    year = now.year
    print(f"\n{'='*60}")
    print(f"🎊 年末処理: {year} 年")
    print(f"{'='*60}")

    report = generate_annual_report(year)
    tax = report["tax_summary"]

    etf_net = tax.get("etf", {}).get("net", 0)
    fx_net = tax.get("fx", {}).get("net", 0)
    crypto_net = tax.get("crypto", {}).get("net", 0)

    carry_etf = abs(etf_net) if etf_net < 0 else 0
    carry_fx = abs(fx_net) if fx_net < 0 else 0

    print(f"\n📊 {year} 年損益サマリー:")
    print(f"  ETF 申告分離 net: {etf_net:,.0f} 円")
    print(f"  FX  申告分離 net: {fx_net:,.0f} 円")
    print(f"  暗号資産 net:     {crypto_net:,.0f} 円")

    if carry_etf > 0 or carry_fx > 0:
        print(f"\n💡 損失繰越: ETF={carry_etf:,.0f} 円, FX={carry_fx:,.0f} 円 を {year + 1} 年に引き継ぎます")

    year_end_reset(carry_over_losses={"etf": carry_etf, "fx": carry_fx})

    print(f"\n✅ 年末処理完了。{year + 1} 年の準備ができました。")
    print("   【確認事項】")
    print("   1. 各取引所の年間取引報告書をダウンロード")
    print("   2. annual_report と照合して確定申告の準備を開始")
    print("   3. state/annual_human_review.md を更新してください")


if __name__ == "__main__":
    run()
