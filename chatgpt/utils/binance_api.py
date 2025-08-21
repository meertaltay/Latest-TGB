"""
Binance API Utils (fixed)
- Case-insensitive coin eşleştirme
- USDT paritelerini önbelleğe alma
- Güvenli OHLC (kline) veri dönüşümü
"""

from __future__ import annotations
import time
import requests
import pandas as pd
from typing import Dict, Optional, List
from config import *

# -------------------------------------------------------------------
# Global state
# -------------------------------------------------------------------
BINANCE_SYMBOLS: Dict[str, str] = {}   # base_lower -> SYMBOL (e.g. "btc" -> "BTCUSDT")
BINANCE_SESSION = requests.Session()
BINANCE_SESSION.headers.update({"User-Agent": "PrimeCryptoBot/1.0"})

EXCHANGE_INFO_URL = f"{BINANCE_BASE_URL}/exchangeInfo"
KLINES_URL = f"{BINANCE_BASE_URL}/klines"
TICKER_24H_URL = f"{BINANCE_BASE_URL}/ticker/24hr"
SYMBOL_PRICE_URL = f"{BINANCE_BASE_URL}/ticker/price"

# Desteklenen interval map
INTERVAL_MAP = {
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


def _safe_request(url: str, params: dict | None = None, timeout: int = 15) -> Optional[requests.Response]:
    try:
        resp = BINANCE_SESSION.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp
        if DEBUG_MODE:
            print(f"Binance API status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        if DEBUG_MODE:
            print(f"Binance API request error: {e}")
    return None


# -------------------------------------------------------------------
# Sembol listesi
# -------------------------------------------------------------------
def load_all_binance_symbols(force: bool = False) -> Dict[str, str]:
    """
    Binance'dan tüm USDT paritelerini yükle ve küçük harf map oluştur.
    base_lower -> SYMBOL
    """
    global BINANCE_SYMBOLS
    if BINANCE_SYMBOLS and not force:
        return BINANCE_SYMBOLS

    try:
        if DEBUG_MODE:
            print("🔄 Binance'dan coin listesi yükleniyor...")

        resp = _safe_request(EXCHANGE_INFO_URL)
        if not resp:
            if DEBUG_MODE:
                print("❌ exchangeInfo alınamadı.")
            return BINANCE_SYMBOLS

        data = resp.json()
        symbols = data.get("symbols", [])
        mapping: Dict[str, str] = {}

        for s in symbols:
            try:
                if s.get("quoteAsset") != "USDT":
                    continue
                if s.get("status") != "TRADING":
                    continue
                base = (s.get("baseAsset") or "").strip()
                sym = (s.get("symbol") or "").strip()
                if not base or not sym:
                    continue
                mapping[base.lower()] = sym  # örn: "btc" -> "BTCUSDT"
            except Exception:
                continue

        # Yaygın kısaltmalar için fallback (varsa override etmez)
        for alias, canonical in {
            "btc": mapping.get("btc", "BTCUSDT"),
            "eth": mapping.get("eth", "ETHUSDT"),
            "sol": mapping.get("sol", "SOLUSDT"),
            "doge": mapping.get("doge", "DOGEUSDT"),
            "ada": mapping.get("ada", "ADAUSDT"),
        }.items():
            if alias not in mapping and canonical:
                mapping[alias] = canonical

        BINANCE_SYMBOLS = mapping

        if DEBUG_MODE:
            print(f"✅ {len(BINANCE_SYMBOLS)} USDT paritesi yüklendi.")
        return BINANCE_SYMBOLS

    except Exception as e:
        print(f"Binance sembol yükleme hatası: {e}")
        return BINANCE_SYMBOLS


def _normalize_coin_input(coin_input: str) -> str:
    """
    Kullanıcı girdisini normalize et:
    - '$btc' -> 'btc'
    - 'BTC/USDT' -> 'btc'
    - boşlukları kırp
    """
    x = (coin_input or "").strip().lower()
    if x.startswith("$"):
        x = x[1:]
    # 'btc/usdt' veya 'btc-usdt' gibi formatlar
    for sep in ["/", "-", "_"]:
        if sep in x:
            x = x.split(sep)[0]
            break
    return x


def find_binance_symbol(coin_input: str) -> Optional[str]:
    """
    Case-insensitive base asset'ten SYMBOL döndür.
    Örn: 'btc' -> 'BTCUSDT'
    """
    if not BINANCE_SYMBOLS:
        load_all_binance_symbols(force=False)

    key = _normalize_coin_input(coin_input)
    if not key:
        return None

    # Doğrudan base eşleşmesi
    sym = BINANCE_SYMBOLS.get(key)
    if sym:
        return sym

    # Bazen kullanıcı direkt 'btcusdt' yazabilir
    u = key.upper()
    if u in BINANCE_SYMBOLS.values():
        return u

    # Son çare: yakın eşleşme (baş harf aynı olanlar)
    for base_lower, symbol in BINANCE_SYMBOLS.items():
        if base_lower == key:
            return symbol

    return None


# -------------------------------------------------------------------
# OHLC (Kline) verisi
# -------------------------------------------------------------------
def get_binance_ohlc(symbol: str, interval: str = "1h", limit: int = 200) -> Optional[pd.DataFrame]:
    """
    Kline verisi al ve DataFrame döndür.
    Kolonlar: open_time, open, high, low, close, volume, close_time
    Index: pandas datetime (close_time)
    """
    try:
        if interval not in INTERVAL_MAP:
            interval = "1h"

        params = {
            "symbol": symbol.upper(),
            "interval": INTERVAL_MAP[interval],
            "limit": max(10, min(int(limit or 200), 1000)),
        }

        resp = _safe_request(KLINES_URL, params=params, timeout=20)
        if not resp:
            return None

        klines = resp.json()
        if not isinstance(klines, list) or not klines:
            return None

        cols = ["open_time","open","high","low","close","volume","close_time","qav","num_trades","taker_base","taker_quote","ignore"]
        rows: List[List] = []
        for k in klines:
            # k = [ open_time, open, high, low, close, volume, close_time, ... ]
            try:
                rows.append([
                    int(k[0]),
                    float(k[1]),
                    float(k[2]),
                    float(k[3]),
                    float(k[4]),
                    float(k[5]),
                    int(k[6]),
                    float(k[7]),
                    int(k[8]),
                    float(k[9]),
                    float(k[10]),
                    float(k[11]) if len(k) > 11 else 0.0
                ])
            except Exception:
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=cols)
        # datetime index (close_time)
        df["dt"] = pd.to_datetime(df["close_time"], unit="ms")
        df.set_index("dt", inplace=True)
        return df[["open","high","low","close","volume","open_time","close_time"]]

    except Exception as e:
        print(f"OHLC veri hatası ({symbol}, {interval}): {e}")
        return None


# -------------------------------------------------------------------
# Fiyat/İstatistik yardımcıları (opsiyonel ama faydalı)
# -------------------------------------------------------------------
def get_symbol_price(symbol: str) -> Optional[float]:
    try:
        resp = _safe_request(SYMBOL_PRICE_URL, params={"symbol": symbol.upper()}, timeout=10)
        if not resp:
            return None
        data = resp.json()
        return float(data.get("price"))
    except Exception as e:
        if DEBUG_MODE:
            print(f"Symbol price hatası: {e}")
        return None


def get_24h_stats(symbol: str) -> Optional[dict]:
    """
    24s istatistikler: lastPrice, priceChangePercent, volume, highPrice, lowPrice
    """
    try:
        resp = _safe_request(TICKER_24H_URL, params={"symbol": symbol.upper()}, timeout=10)
        if not resp:
            return None
        data = resp.json()
        return {
            "price": float(data.get("lastPrice", 0) or 0),
            "change_24h": float(data.get("priceChangePercent", 0) or 0),
            "volume_24h": float(data.get("volume", 0) or 0),
            "high_24h": float(data.get("highPrice", 0) or 0),
            "low_24h": float(data.get("lowPrice", 0) or 0),
        }
    except Exception as e:
        if DEBUG_MODE:
            print(f"24h stats hatası: {e}")
        return None


# -------------------------------------------------------------------
# Modül yüklendiğinde sembolleri preload et (sessiz başarısız olabilir)
# -------------------------------------------------------------------
try:
    load_all_binance_symbols(force=False)
except Exception as e:
    if DEBUG_MODE:
        print(f"Sembol preload hatası: {e}")

if DEBUG_MODE:
    print("🔧 Binance API utils yüklendi!")
