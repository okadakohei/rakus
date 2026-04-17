# tools/zaif_api.py
"""ZAIF API ラッパー(BTC/JPY ペーパー・実弾対応)"""

import os
import hashlib
import hmac as hmac_module
import time
import json
import requests
from datetime import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")
ZAIF_TRADE_URL = "https://api.zaif.jp/tapi"
ZAIF_PUBLIC_URL = "https://api.zaif.jp/api/1"

EXCHANGE = os.getenv("CRYPTO_EXCHANGE", "zaif")


def _zaif_sign(params: dict, secret: str) -> tuple[str, str]:
    """ZAIF の HMAC-SHA512 署名を生成する"""
    params["nonce"] = str(time.time())
    encoded = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sig = hmac_module.new(
        secret.encode("utf-8"),
        encoded.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()
    return encoded, sig


def get_btc_ticker() -> dict:
    """BTC/JPY の現在価格を取得する"""
    url = f"{ZAIF_PUBLIC_URL}/ticker/btc_jpy"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "exchange": "zaif",
            "pair": "btc_jpy",
            "last": data.get("last"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "timestamp": datetime.now(JST).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "exchange": "zaif"}


def get_btc_ohlcv() -> list[dict]:
    """BTC/JPY の簡易 OHLCV を返す(ticker ベース)"""
    return [get_btc_ticker()]


def paper_order(side: str, amount_jpy: float, price: float = None) -> dict:
    """ペーパートレード発注(実際には発注しない)"""
    mode = os.getenv("TRADING_MODE", "PAPER")
    if mode != "PAPER":
        raise RuntimeError(
            "paper_order は PAPER モード専用です。実弾発注には live_order を使用してください。"
        )
    result = {
        "mode": "PAPER",
        "exchange": "zaif",
        "pair": "btc_jpy",
        "side": side,
        "amount_jpy": amount_jpy,
        "price": price or get_btc_ticker().get("last"),
        "status": "PAPER_FILLED",
        "timestamp": datetime.now(JST).isoformat(),
    }
    print(f"[PAPER ORDER] {json.dumps(result, ensure_ascii=False)}")
    return result


def live_order(side: str, amount: float, price: float = None) -> dict:
    """実弾発注(LIVE モード専用)"""
    mode = os.getenv("TRADING_MODE", "PAPER")
    if mode != "LIVE":
        raise RuntimeError("live_order は LIVE モード専用です。現在のモード: " + mode)

    api_key = os.getenv("ZAIF_API_KEY")
    api_secret = os.getenv("ZAIF_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("ZAIF_API_KEY / ZAIF_API_SECRET が設定されていません")

    params = {
        "method": "trade",
        "currency_pair": "btc_jpy",
        "action": "bid" if side == "BUY" else "ask",
        "amount": amount,
        "price": price or 0,
    }
    body, sig = _zaif_sign(params, api_secret)
    headers = {"key": api_key, "sign": sig}
    resp = requests.post(ZAIF_TRADE_URL, data=body, headers=headers, timeout=15)
    return resp.json()
