# daily/morning.py
"""
朝のルーティン(毎日 09:00 JST 実行)
- 市場データ取得・ファクトチェック・シグナル判断・ペーパー発注
- 全滅チェック・フェーズ移行アラート
- 12 月: 損出し候補リスト出力
- 毎月 1 日: 法規制チェック
"""

import json
import os
import sys
from datetime import datetime
import pytz

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from tools.market_data import get_etf_signal, detect_ai_overreaction, get_tax_loss_candidates
from tools.zaif_api import get_btc_ticker, paper_order as zaif_paper_order
from tools.oanda_api import get_usdjpy_price, get_fx_signal, paper_order as fx_paper_order
from tools.tax_calculator import get_net_profit_overview
from tools.fact_check import fact_check_news
from tools.regulation_check import run_monthly_check
from tools.wipeout import execute_wipeout_protocol

JST = pytz.timezone("Asia/Tokyo")
STATE_DIR = os.path.join(os.path.dirname(__file__), "../state")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

# 全滅閾値(元手比率)
WIPEOUT_THRESHOLD_RATIO = 0.10  # 元手の 10%


def load_portfolio() -> dict:
    path = os.path.join(STATE_DIR, "portfolio.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_report(data: dict, prefix: str = "morning"):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    date_str = datetime.now(JST).strftime("%Y%m%d")
    path = os.path.join(REPORTS_DIR, f"{prefix}_{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート保存: {path}")


def check_wipeout(portfolio: dict) -> bool:
    """全滅条件チェック。該当すればプロトコルを実行して True を返す"""
    total_value = portfolio.get("total_value", portfolio.get("total_capital", 1000000))
    initial = portfolio.get("total_capital", 1000000)
    threshold = initial * WIPEOUT_THRESHOLD_RATIO

    # wipeout_acknowledged が True なら通常動作を継続
    if portfolio.get("wipeout_acknowledged", False):
        return False

    if total_value <= threshold:
        execute_wipeout_protocol(portfolio)
        return True
    return False


def check_phase_transition(portfolio: dict) -> list[str]:
    """現在フェーズの次の閾値のみチェックしてアラートを返す(累積アラート防止)"""
    total_value = portfolio.get("total_value", 0)
    current_phase = portfolio.get("current_phase", "Seed")

    # 現在フェーズの「次の移行」だけを監視する
    next_map = {
        "Seed":   ("Seed→Growth",  3_000_000),
        "Growth": ("Growth→Scale", 10_000_000),
        "Scale":  ("Scale→Mature", 30_000_000),
        "Mature": (None, None),
    }
    transition_name, threshold = next_map.get(current_phase, (None, None))

    if transition_name and threshold and total_value >= threshold:
        return [
            f"🎯 フェーズ移行アラート: {transition_name} の閾値 {threshold:,.0f} 円に到達！"
            f" portfolio.json の current_phase を更新後、"
            f"state/phase_config.md を確認してください"
        ]
    return []


def run():
    now = datetime.now(JST)
    print(f"\n{'='*60}")
    print(f"🌅 朝のルーティン開始: {now.strftime('%Y-%m-%d %H:%M JST')}")
    print(f"{'='*60}")

    portfolio = load_portfolio()
    mode = portfolio.get("mode", "PAPER")
    print(f"🔧 運用モード: {mode}")

    # ── 全滅チェック(最優先) ──
    if check_wipeout(portfolio):
        print("🚨 全滅プロトコルを実行しました。morning.py を終了します。")
        return

    report = {
        "date": now.isoformat(),
        "mode": mode,
        "signals": {},
        "orders": [],
        "alerts": [],
    }

    # ── フェーズ移行チェック ──
    phase_alerts = check_phase_transition(portfolio)
    for a in phase_alerts:
        print(f"\n{a}")
        report["alerts"].append(a)

    # ── ETF シグナル ──
    print("\n📈 ETF シグナル確認...")
    for symbol in ["SPY", "QQQ"]:
        sig = get_etf_signal(symbol)
        report["signals"][symbol] = sig
        print(f"  {symbol}: {sig['signal']} (close={sig.get('close')}, MA20={sig.get('ma20')})")

        overreact = detect_ai_overreaction(symbol)
        if overreact.get("detected"):
            alert = (
                f"⚡ {symbol}: AI 過剰反応疑い"
                f" ({overreact['last_5min_return_pct']:+.2f}%) → 逆張り検討"
            )
            print(f"  {alert}")
            report["alerts"].append(alert)

    # ── FX シグナル ──
    print("\n💱 FX シグナル確認...")
    fx_sig = get_fx_signal()
    report["signals"]["USD_JPY"] = fx_sig
    print(f"  USD/JPY: {fx_sig['signal']} (RSI={fx_sig.get('rsi')}, MACD={fx_sig.get('macd')})")

    # ── 暗号資産 ──
    print("\n₿ 暗号資産確認...")
    btc = get_btc_ticker()
    report["signals"]["BTC_JPY"] = btc
    if "error" not in btc:
        print(f"  BTC/JPY: {btc.get('last'):,} 円")

    # ── 税務アラート ──
    print("\n📊 税務状況確認...")
    tax_overview = get_net_profit_overview()
    report["tax_overview"] = tax_overview
    if tax_overview.get("approaching_threshold"):
        alert = "⚠️ 年間利益が 20 万円ラインの 80% に到達。ポジション縮小を検討。"
        report["alerts"].append(alert)

    # ── 12 月: 損出し候補リスト ──
    if now.month == 12:
        print("\n🍂 12 月: 損出し候補をチェック中...")
        candidates = get_tax_loss_candidates(portfolio)
        if candidates:
            date_label = now.strftime("%m%d")
            cand_path = os.path.join(REPORTS_DIR, f"tax_loss_{date_label}.json")
            os.makedirs(REPORTS_DIR, exist_ok=True)
            with open(cand_path, "w", encoding="utf-8") as f:
                json.dump(candidates, f, ensure_ascii=False, indent=2)
            print(f"  💡 損出し候補 {len(candidates)} 件 → {cand_path}")
            report["alerts"].append(f"損出し候補 {len(candidates)} 件あり。tax_loss_{date_label}.json を確認してください。")
        else:
            print("  損出し候補なし(含み損ポジションなし)")

    # ── 月初: 法規制チェック ──
    if now.day == 1:
        print("\n📋 月初: 法規制チェック実行...")
        reg_result = run_monthly_check()
        report["regulation_check"] = reg_result

    # ── ペーパー発注(BUY シグナルのみ) ──
    if mode == "PAPER":
        for symbol in ["SPY", "QQQ"]:
            if report["signals"].get(symbol, {}).get("signal") == "BUY":
                order = {
                    "type": "PAPER", "symbol": symbol,
                    "action": "BUY", "note": "MA20 シグナルによるペーパー発注",
                }
                report["orders"].append(order)
                print(f"  📝 ペーパー発注: {symbol} BUY")

    # ── サマリー ──
    print(f"\n{'='*60}")
    print("✅ 朝のルーティン完了")
    if report["alerts"]:
        print(f"⚠️ アラート {len(report['alerts'])} 件:")
        for a in report["alerts"]:
            print(f"   {a}")

    save_report(report, prefix="morning")
    return report


if __name__ == "__main__":
    run()
