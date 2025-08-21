"""
Fear & Greed (Crypto) — /korku komutu
- alternative.me API'den son değeri çeker
- Metin + gauge görseli gönderir
"""

from __future__ import annotations
import time
import requests

API_URL = "https://api.alternative.me/fng/"
IMG_URL = "https://alternative.me/crypto/fear-and-greed-index.png"

session = requests.Session()
session.headers.update({"User-Agent": "PrimeCryptoBot/1.0"})

def _classify(value: int):
    # Sınırlar: alternative.me mantığına yakın
    if value <= 25:
        return "Aşırı Korku", "😱", "Dip arayan alıcılar için fırsat olabilir"
    if value <= 45:
        return "Korku", "😰", "Temkinli olmakta fayda var"
    if value <= 55:
        return "Nötr", "😐", "Denge hâli – net sinyal yok"
    if value <= 75:
        return "Açgözlülük", "🤑", "Risk artıyor, kâr realizasyonu gelebilir"
    return "Aşırı Açgözlülük", "🚀", "Aşırı ısınma, geri çekilme riski yüksek"

def _fetch_latest():
    try:
        r = session.get(API_URL, params={"limit": 1}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data or "data" not in data or not data["data"]:
            return None
        item = data["data"][0]
        val = int(item.get("value", 0))
        ts = int(item.get("timestamp", time.time()))
        return {"value": val, "timestamp": ts}
    except Exception as e:
        print(f"Fear&Greed fetch error: {e}")
        return None

def register_fng_commands(bot):
    @bot.message_handler(commands=["korku"])
    def cmd_korku(message):
        chat_id = message.chat.id
        bot.send_chat_action(chat_id, "typing")

        info = _fetch_latest()
        if not info:
            bot.send_message(chat_id, "❌ Fear & Greed verisi alınamadı, biraz sonra tekrar dene.")
            return

        value = info["value"]
        label, emoji, tip = _classify(value)

        text = (
            f"📊 *Fear & Greed Index*\n\n"
            f"Değer: *{value}/100* {emoji}\n"
            f"Durum: *{label}*\n"
            f"💡 {tip}"
        )
        try:
            # Görseli cache kırmak için timestamp paramıyla yolla
            img_url = f"{IMG_URL}?t={int(time.time())}"
            bot.send_photo(chat_id, img_url, caption=text, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, text, parse_mode="Markdown")
