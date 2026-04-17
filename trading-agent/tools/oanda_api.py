# tools/oanda_api.py
"""OANDA API ラッパー(USD/JPY ペーパー・実弾対応)"""

import os
import json
import requests
from datetime import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")

# デフォルトはデモ口座。LIVE 化時に .env で本番 URL に変更
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com/v3")
ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
API_TOKEN = os.getenv("OANDA_API_TOKEN", "")


def _get_headers() -> dict:
    """リクエストごとに .env の最新値を参照する"""
    token = os.getenv("OANDA_API_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get(path: str) -> dict:
    base = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com/v3")
    url = f"{base}{path}"
    resp = requests.get(url, headers=_get_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_usdjpy_price() -> dict:
    """USD/JPY の現在価格を取得する"""
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    try:
        data = _get(f"/accounts/{account_id}/pricing?instruments=USD_JPY")
        price = data["prices"][0]
        bid = float(price["bids"][0]["price"])
        ask = float(price["asks"][0]["price"])
        return {
            "exchange": "oanda",
            "pair": "USD_JPY",
            "bid": bid,
            "ask": ask,
            "mid": round((bid + ask) / 2, 4),
            "timestamp": datetime.now(JST).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "exchange": "oanda"}


def get_usdjpy_candles(granularity: str = "D", count: int = 30) -> list[dict]:
    """USD/JPY のローソク足を取得する"""
    try:
        path = f"/instruments/USD_JPY/candles?granularity={granularity}&count={count}"
        data = _get(path)
        candles = []
        for c in data.get("candles", []):
            if c.get("complete"):
                candles.append({
                    "time": c["time"],
                    "open": float(c["mid"]["o"]),
                    "high": float(c["mid"]["h"]),
                    "low": float(c["mid"]["l"]),
                    "close": float(c["mid"]["c"]),
                    "volume": c.get("volume", 0),
                })
        return candles
    except Exception as e:
        return [{"error": str(e)}]


def get_fx_signal() -> dict:
    """RSI(14) + MACD ベースのシグナルを計算する"""
    candles = get_usdjpy_candles(granularity="H4", count=50)
    if not candles or "error" in candles[0]:
        return {"signal": "NO_DATA", "reason": "ローソク足取得失敗"}

    closes = [c["close"] for c in candles if "close" in c]
    if len(closes) < 26:
        return {"signal": "NO_DATA", "reason": "データ不足(26 本未満)"}

    # RSI(14)
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    rsi = 100 - (100 / (1 + avg_gain / (avg_loss + 1e-10)))

    # MACD(簡易: EMA12 を直近値、EMA26 を単純平均で近似)
    ema26 = sum(closes[-26:]) / 26
    macd = closes[-1] - ema26

    if rsi > 50 and macd > 0:
        signal = "BUY"
    elif rsi < 45 or macd < -0.1:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "pair": "USD_JPY",
        "signal": signal,
        "rsi": round(rsi, 2),
        "macd": round(macd, 4),
        "current_price": closes[-1],
        "timestamp": datetime.now(JST).isoformat(),
    }


def paper_order(side: str, units: int) -> dict:
    """ペーパートレード発注(実際には発注しない)"""
    mode = os.getenv("TRADING_MODE", "PAPER")
    if mode != "PAPER":
        raise RuntimeError("paper_order は PAPER モード専用です")

    price_data = get_usdjpy_price()
    result = {
        "mode": "PAPER",
        "exchange": "oanda",
        "pair": "USD_JPY",
        "side": side,
        "units": units,
        "price": price_data.get("mid"),
        "status": "PAPER_FILLED",
        "timestamp": datetime.now(JST).isoformat(),
    }
    print(f"[PAPER ORDER] {json.dumps(result, ensure_ascii=False)}")
    return result


def live_order(side: str, units: int) -> dict:
    """実弾発注(LIVE モード専用)"""
    mode = os.getenv("TRADING_MODE", "PAPER")
    if mode != "LIVE":
        raise RuntimeError("live_order は LIVE モード専用です。現在: " + mode)

    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    base = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com/v3")
    order_body = {
        "order": {
            "type": "MARKET",
            "instrument": "USD_JPY",
            "units": str(units if side == "BUY" else -units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
        }
    }
    resp = requests.post(
        f"{base}/accounts/{account_id}/orders",
        headers=_get_headers(),
        data=json.dumps(order_body),
        timeout=15,
    )
    return resp.json()
