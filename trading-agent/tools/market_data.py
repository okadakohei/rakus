# tools/market_data.py
"""市場データ取得モジュール(yfinance ベース)"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")


def get_etf_data(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """ETF の OHLCV データを取得する"""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    if not df.empty:
        df.index = df.index.tz_convert(JST)
    return df


def get_etf_signal(symbol: str) -> dict:
    """MA20 ベースのシグナルを計算する"""
    df = get_etf_data(symbol, period="3mo")
    if df.empty or len(df) < 21:
        return {"symbol": symbol, "signal": "NO_DATA", "reason": "データ取得失敗または不足"}

    df["MA20"] = df["Close"].rolling(20).mean()
    latest = df.iloc[-1]

    close = float(latest["Close"])
    ma20 = float(latest["MA20"])

    if close > ma20 * 1.005:
        signal = "BUY"
    elif close < ma20 * 0.997:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "symbol": symbol,
        "signal": signal,
        "close": round(close, 4),
        "ma20": round(ma20, 4),
        "deviation_pct": round((close / ma20 - 1) * 100, 2),
        "timestamp": datetime.now(JST).isoformat(),
    }


def detect_ai_overreaction(symbol: str, threshold_pct: float = 3.0) -> dict:
    """直近 5 分足で 3% 超の急変動を検出(AI 過剰反応疑い)"""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1d", interval="5m")
    if df.empty or len(df) < 2:
        return {"detected": False, "symbol": symbol, "reason": "データ不足"}

    last_return = (df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100
    detected = abs(last_return) > threshold_pct

    return {
        "detected": detected,
        "symbol": symbol,
        "last_5min_return_pct": round(last_return, 2),
        "threshold_pct": threshold_pct,
        "suggestion": "逆張り検討" if detected else "通常",
    }


def get_tax_loss_candidates(portfolio: dict) -> list[dict]:
    """
    損出し候補リストを生成する(12 月専用)
    含み損ポジションをリストアップして損出しを促す
    """
    candidates = []
    for market, alloc in portfolio.get("allocations", {}).items():
        for pos in alloc.get("positions", []):
            entry_price = pos.get("entry_price", 0)
            current_price = pos.get("current_price", entry_price)
            if entry_price > 0 and current_price < entry_price:
                unrealized_loss = (current_price - entry_price) * pos.get("quantity", 0)
                candidates.append({
                    "market": market,
                    "symbol": pos.get("symbol"),
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_loss_jpy": round(unrealized_loss, 0),
                    "loss_pct": round((current_price / entry_price - 1) * 100, 2),
                    "recommendation": "損出しを検討してください",
                })
    return sorted(candidates, key=lambda x: x["unrealized_loss_jpy"])
