"""
Crypto Telegram Bot - MAIN
Komutlar + otomatik haber forward (özel & grup).
"""

import os
import sys
import time
import atexit
import subprocess
from datetime import datetime
from html import escape as h

import telebot
import requests

# ==========================
# CONFIG
# ==========================
try:
    from config import TELEGRAM_TOKEN, COINGECKO_BASE_URL, COINGECKO_TIMEOUT, DEBUG_MODE
except ImportError:
    print("❌ config.py bulunamadı!")
    sys.exit(1)

if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
    print("❌ TELEGRAM_TOKEN boş!")
    sys.exit(1)

# ==========================
# Tek instance (bot.lock)
# ==========================
LOCK_FILE = "bot.lock"

def _pid_running(pid: int) -> bool:
    try:
        if os.name == "nt":
            out = subprocess.check_output(["tasklist"], creationflags=0x08000000).decode(errors="ignore")
            return f" {pid} " in out
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def _read_lock():
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
    except Exception:
        pass
    return None

def _write_lock():
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

def _remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

def ensure_single_instance():
    if "--force" in sys.argv:
        print("⚠️  --force: bot.lock temizleniyor.")
        _remove_lock(); _write_lock(); return
    old = _read_lock()
    if old is None:
        _write_lock(); return
    if _pid_running(old):
        print("❌ Bot zaten çalışıyor (bot.lock)."); sys.exit(1)
    print(f"🧹 Eski lock bulundu (PID={old}) ama süreç yok; temizlendi.")
    _remove_lock(); _write_lock()

atexit.register(_remove_lock)
ensure_single_instance()

# ==========================
# BOT
# ==========================
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")

try:
    print("🔧 Webhook temizleniyor…")
    bot.remove_webhook()
    time.sleep(1)
except Exception as e:
    print("⚠️ remove_webhook:", e)

# ==========================
# Komut modülleri
# ==========================
try:
    from commands.price_commands import register_price_commands
    from commands.alarm_commands import register_alarm_commands
    from commands.analysis_commands import register_analysis_commands
    from commands.fng_commands import register_fng_commands
    from commands.whale_commands import register_whale_commands
    from commands.moneyflow_commands import register_moneyflow_commands
    from commands.social_commands import register_social_commands
    from utils.liquidity_heatmap import add_liquidity_command_to_bot
    from utils.news_system import (
        register_news_forwarding,
        add_active_user,
        add_active_group,
        get_news_stats,
    )
    print("📁 Komut paketleri import OK")
except Exception as e:
    print("❌ Komut paketleri import hatası:", e)
    sys.exit(1)

# Kayıt
try: register_price_commands(bot);      print("💰 price_commands ✓")
except Exception as e: print("❌ price_commands:", e)

try: register_alarm_commands(bot);      print("⏰ alarm_commands ✓")
except Exception as e: print("❌ alarm_commands:", e)

try: register_analysis_commands(bot);   print("🎯 analysis_commands ✓")
except Exception as e: print("❌ analysis_commands:", e)

try: add_liquidity_command_to_bot(bot); print("💧 liquidity_heatmap ✓")
except Exception as e: print("❌ liquidity_heatmap:", e)

try: register_fng_commands(bot);        print("📊 fng_commands ✓")
except Exception as e: print("❌ fng_commands:", e)

try: register_news_forwarding(bot);     print("📰 news_system forwarding ✓")
except Exception as e: print("❌ news_system:", e)

try: register_whale_commands(bot);      print("🐋 whale_commands ✓")
except Exception as e: print("❌ whale_commands:", e)

try: register_moneyflow_commands(bot);  print("💰 moneyflow_commands ✓")
except Exception as e: print("❌ moneyflow_commands:", e)

try: register_social_commands(bot);     print("📱 social_commands ✓")
except Exception as e: print("❌ social_commands:", e)

# ==========================
# Kısa /start karşılama
# ==========================
http = requests.Session()
http.headers.update({"User-Agent": "PrimeCryptoBot/1.0"})

def _fmt_money(v: float) -> str:
    if v >= 1_000_000_000_000: return f"${v/1_000_000_000_000:.2f}T"
    if v >= 1_000_000_000:     return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:         return f"${v/1_000_000:.2f}M"
    return f"${v:,.2f}"

def _fmt_price(v: float) -> str:
    if v >= 1: return f"${v:,.2f}"
    if v >= 0.01: return f"${v:.6f}"
    return f"${v:.8f}"

def _market_overview():
    data = {"btc_p": None, "btc_ch": None, "eth_p": None, "eth_ch": None}
    try:
        r = http.get(
            f"{COINGECKO_BASE_URL}/coins/markets",
            params={"vs_currency": "usd", "ids": "bitcoin,ethereum"},
            timeout=COINGECKO_TIMEOUT,
        )
        if r.status_code == 200:
            for it in r.json():
                if it["id"] == "bitcoin":
                    data["btc_p"] = float(it.get("current_price") or 0)
                    data["btc_ch"] = float(it.get("price_change_percentage_24h") or 0)
                elif it["id"] == "ethereum":
                    data["eth_p"] = float(it.get("current_price") or 0)
                    data["eth_ch"] = float(it.get("price_change_percentage_24h") or 0)
    except Exception as e:
        if DEBUG_MODE: print("market_overview:", e)
    return data

@bot.message_handler(commands=["start", "yardim"])
def send_welcome(message):
    # otomatik abonelik (komutlardan da ekleyelim)
    try:
        if message.chat.type == "private":
            add_active_user(message.chat.id)
        elif message.chat.type in ("group", "supergroup"):
            add_active_group(message.chat.id)
    except Exception:
        pass

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(telebot.types.KeyboardButton("/analiz btc"),
           telebot.types.KeyboardButton("/analiz eth"))
    kb.add(telebot.types.KeyboardButton("/fiyat btc"),
           telebot.types.KeyboardButton("/fiyat eth"))
    kb.add(telebot.types.KeyboardButton("/likidite btc"),
           telebot.types.KeyboardButton("/korku"))
    kb.add(telebot.types.KeyboardButton("/alarmlist"),
           telebot.types.KeyboardButton("/top10"))

    mk = _market_overview()
    arrow = lambda ch: "📈" if (ch or 0) >= 0 else "📉"
    today = datetime.now().strftime("%d.%m.%Y")
    text = (
        f"👋 Selam <b>{h(message.from_user.first_name or 'Trader')}</b>, PrimeXAI botuna hoş geldin.\n\n"
        f"🗓️ <b>Piyasa Özeti</b> — {h(today)}\n\n"
        f"BTC: {_fmt_price(mk['btc_p'])} | {arrow(mk['btc_ch'])} %{(mk['btc_ch'] or 0):.2f}\n"
        f"ETH: {_fmt_price(mk['eth_p'])} | {arrow(mk['eth_ch'])} %{(mk['eth_ch'] or 0):.2f}\n\n"
        f"@primecrypto_tr ile güncel haberler. Aşağıdan istediğini seç 👇"
    )
    bot.send_message(message.chat.id, text, reply_markup=kb)

# ==========================
# Komut olmayan metinlerde otomatik kayıt (özel & grup)
# ==========================
@bot.message_handler(
    content_types=["text"],
    func=lambda m: (m.text is not None) and (not m.text.strip().startswith("/"))
)
def track_users_and_groups(message):
    try:
        if message.chat.type == "private":
            add_active_user(message.chat.id)
        elif message.chat.type in ("group", "supergroup"):
            add_active_group(message.chat.id)
    except Exception as e:
        if DEBUG_MODE: print("track_users_and_groups:", e)

# ==========================
# /habertest
# ==========================
@bot.message_handler(commands=["habertest"])
def habertest(message):
    try:
        st = get_news_stats()
        msg = (
            "<b>📰 HABER SİSTEMİ</b>\n\n"
            f"👥 Kullanıcı: {st.get('active_users', 0)}\n"
            f"💬 Grup: {st.get('active_groups', 0)}\n"
        )
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Durum alınamadı: {h(str(e))}")

# ==========================
# Çalıştır
# ==========================
print("✅ Bot başlatılıyor...")

delay = 2
while True:
    try:
        bot.infinity_polling(
            skip_pending=True,
            long_polling_timeout=10,  # DİKKAT: doğru isim
            timeout=20,
            allowed_updates=[
                "message",        # komut/mesaj
                "callback_query", # butonlar
                "channel_post",   # kanal postları
                "my_chat_member"  # bot gruba eklendi/çıkarıldı
            ],
        )
    except Exception as e:
        print(f"❌ Polling hata: {e}. {delay}s sonra tekrar…")
        time.sleep(delay)
        delay = min(delay * 2, 60)
        continue
    break
