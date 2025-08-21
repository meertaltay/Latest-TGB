"""
services/market.py
- Tek yerden fiyat & değişim ve sembol eşleme
- Binance dynamic mapping (exchangeInfo) + hafıza cache
"""

from __future__ import annotations
import time
import threading
import requests
from typing import Dict, Optional

from config import BINANCE_BASE_URL, COINGECKO_BASE_URL, BINANCE_TIMEOUT, COINGECKO_TIMEOUT

# -------------------- Cache --------------------
_symbol_map_lock = threading.Lock()
_symbol_map: Dict[str, str] = {}      # "ena" -> "ENAUSDT"
_symbol_map_ts: float = 0
_SYMBOL_TTL = 60 * 60  # 1 saat

_price_lock = threading.Lock()
_price_cache: Dict[str, Dict] = {}    # "ENAUSDT" -> {"price": float, "change": float, "ts": time}
_PRICE_TTL = 5  # saniye (çok kısa tutuyoruz)

session = requests.Session()


# -------------------- Helpers --------------------
def _refresh_symbol_map() -> None:
    global _symbol_map, _symbol_map_ts
    with _symbol_map_lock:
        now = time.time()
        if now - _symbol_map_ts < _SYMBOL_TTL and _symbol_map:
            return
        try:
            url = f"{BINANCE_BASE_URL}/exchangeInfo"
            r = session.get(url, timeout=BINANCE_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            mapping: Dict[str, str] = {}
            for s in data.get("symbols", []):
                if s.get("status") != "TRADING":
                    continue
                base = s.get("baseAsset")
                quote = s.get("quoteAsset")
                symbol = s.get("symbol")
                if not base or not quote or not symbol:
                    continue
                if quote != "USDT":
                    continue
                mapping[base.lower()] = symbol  # örn: "ena" -> "ENAUSDT"
                # ayrıca "baseusdt" yazanlara da doğrulama yapabilelim
                mapping[symbol.lower()] = symbol
            _symbol_map = mapping
            _symbol_map_ts = now
            print(f"🔄 Binance symbol map yenilendi ({len(_symbol_map)} kayıt).")
        except Exception as e:
            print(f"⚠️ exchangeInfo çekilemedi: {e}")


def to_binance_symbol(coin: str) -> Optional[str]:
    """
    Kullanıcı girdisini (btc, BTCUSDT, ena, tia ...) Binance USDT sembolüne çevirir.
    Yalnızca Binance'ta listeli pariteler döner. Yoksa None.
    """
    if not coin:
        return None
    _refresh_symbol_map()
    key = coin.strip().lower()
    # 'btc' -> 'BTCUSDT', 'btcusdt' -> 'BTCUSDT'
    if key in _symbol_map:
        return _symbol_map[key]
    # 'btc' yazıp mapte bulamadıysa bir de 'btcusdt' deneyelim (eski map yoksa)
    guess = f"{key.upper()}USDT"
    if guess.lower() in _symbol_map:
        return _symbol_map[guess.lower()]
    return None


# -------------------- Price --------------------
def _fetch_binance_ticker(symbol: str) -> Optional[Dict]:
    try:
        url = f"{BINANCE_BASE_URL}/ticker/24hr"
        r = session.get(url, params={"symbol": symbol}, timeout=BINANCE_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        # Beklenen alanlar yoksa Binance hata dönmüştür
        if "lastPrice" not in j:
            return None
        price = float(j["lastPrice"])
        change = float(j.get("priceChangePercent", 0.0))
        return {"price": price, "change": change}
    except Exception as e:
        print(f"⚠️ Binance ticker hatası ({symbol}): {e}")
        return None


def get_price(symbol: str) -> Optional[float]:
    now = time.time()
    with _price_lock:
        ent = _price_cache.get(symbol)
        if ent and (now - ent["ts"] < _PRICE_TTL):
            return ent["price"]

    data = _fetch_binance_ticker(symbol)
    if not data:
        return None

    with _price_lock:
        _price_cache[symbol] = {"price": data["price"], "change": data["change"], "ts": now}
    return data["price"]


def get_change(symbol: str) -> Optional[float]:
    now = time.time()
    with _price_lock:
        ent = _price_cache.get(symbol)
        if ent and (now - ent["ts"] < _PRICE_TTL):
            return ent["change"]

    data = _fetch_binance_ticker(symbol)
    if not data:
        return None
    with _price_lock:
        _price_cache[symbol] = {"price": data["price"], "change": data["change"], "ts": now}
    return data["change"]


# -------------------- Lifecycle --------------------
def start():
    """Modül başlatıldığında sembol haritasını ısıt."""
    try:
        _refresh_symbol_map()
    except Exception:
        pass
