"""
Price Commands – /fiyat, /price
- Kaynak: services/market (Binance REST + cache)
- Tek mesaj: İlk çağrıda cache boşsa 2 sn'ye kadar bekler, hazır olunca gönderir.
- Grup desteği: /fiyat@BotAdi ... şeklini de algılar
"""

from __future__ import annotations
import time
import re
from services.market import start as market_start, get_price, get_change, to_binance_symbol

def _pretty_price(v: float) -> str:
    if v is None: return "—"
    if v >= 1:    return f"${v:,.2f}"
    if v >= 0.01: return f"${v:.6f}"
    return f"${v:.8f}"

def _split_command(text: str):
    """
    '/fiyat@PrimeXAI btc' -> ['/_fiyat', 'btc']
    '/fiyat btc' -> ['/fiyat', 'btc']
    Komut kısmındaki '@...' bölümünü atar.
    """
    parts = (text or "").strip().split()
    if not parts:
        return []
    parts[0] = parts[0].split("@")[0]  # /fiyat@BotAdi -> /fiyat
    return parts

def register_price_commands(bot):
    # Market servisini çalışır tut
    market_start()

    @bot.message_handler(commands=["fiyat", "price"])
    def cmd_price(message):
        parts = _split_command(message.text)
        if len(parts) < 2:
            bot.reply_to(message, "Kullanım: /fiyat <coin>\nÖrn: /fiyat btc")
            return

        coin = parts[1]
        symbol = to_binance_symbol(coin)
        if not symbol:
            bot.reply_to(message, f"❌ '{coin.upper()}' bulunamadı!")
            return

        # Tek mesaj politikası: cache boşsa kısa süre bekle
        bot.send_chat_action(message.chat.id, "typing")
        price = get_price(symbol)
        change = get_change(symbol)

        if price is None:
            deadline = time.time() + 2.0   # en fazla 2 sn bekle
            while time.time() < deadline:
                time.sleep(0.25)
                price = get_price(symbol)
                change = get_change(symbol)
                if price is not None:
                    break

        if price is None:
            bot.reply_to(message, "⚠️ Şu an fiyat erişilemedi, lütfen tekrar dener misin?")
            return

        arrow = "🟢" if (change or 0) >= 0 else "🔻"
        emoji = "📈" if (change or 0) >= 0 else "📉"
        ch_txt = f"{arrow} %{(change or 0):.2f} {emoji}"

        text = (
            f"💸 <b>{symbol}</b>\n\n"
            f"Fiyat: <b>{_pretty_price(price)}</b>\n"
            f"24s: {ch_txt}"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML")
