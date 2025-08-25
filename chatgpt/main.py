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
    from commands.alarm_commands import register_alarm_commands, price_alarms
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
# Helper Functions
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

# ==========================
# YENİ MİNİMAL /start KOMUTU
# ==========================
@bot.message_handler(commands=["start"])
def send_welcome(message):
    # otomatik abonelik
    try:
        if message.chat.type == "private":
            add_active_user(message.chat.id)
        elif message.chat.type in ("group", "supergroup"):
            add_active_group(message.chat.id)
    except Exception:
        pass

    # Kullanıcı bilgisi
    user_name = message.from_user.first_name or 'Trader'
    user_id = message.from_user.id
    
    # Admin kontrolü
    is_admin = user_id == 5481899729
    admin_tag = " | <b>Admin</b>" if is_admin else ""
    
    # Piyasa verileri
    mk = _market_overview()
    btc_price = mk.get('btc_p')
    btc_change = mk.get('btc_ch', 0)
    eth_price = mk.get('eth_p')
    eth_change = mk.get('eth_ch', 0)
    
    # Emoji
    btc_arrow = "📈" if btc_change >= 0 else "📉"
    eth_arrow = "📈" if eth_change >= 0 else "📉"
    
    # Tarih
    today = datetime.now().strftime("%d.%m.%Y")
    
    # Fiyat formatı
    btc_price_str = _fmt_price(btc_price) if btc_price else "—"
    eth_price_str = _fmt_price(eth_price) if eth_price else "—"
    
    # Minimal hoşgeldin mesajı
    text = (
        f"👋 Selam <b>{h(user_name)}</b>{admin_tag}, PrimeXAI bot'una hoş geldin.\n\n"
        f"📊 <b>Piyasa Özeti</b> — {today}\n\n"
        f"BTC: {btc_price_str} | {btc_arrow} %{btc_change:+.2f}\n"
        f"ETH: {eth_price_str} | {eth_arrow} %{eth_change:+.2f}\n\n"
        f"@primecrypto_tr ile güncel haberleri takip etmeyi unutma!"
    )
    
    # Inline keyboard - mesaja yapışık buton
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("❓ Nasıl Çalışır?", callback_data="show_help"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ==========================
# Inline button callback handler
# ==========================
@bot.callback_query_handler(func=lambda call: call.data == "show_help")
def callback_show_help(call):
    help_text = """
📚 <b>NASIL ÇALIŞIR?</b>

<b>💰 Fiyat Komutları:</b>
• <code>/fiyat btc</code> - Bitcoin anlık fiyat
• <code>/fiyat eth</code> - Ethereum anlık fiyat
• <code>/fiyat sol</code> - Solana anlık fiyat

<b>📊 Teknik Analiz:</b>
• <code>/analiz btc</code> - Bitcoin teknik analizi
• <code>/analiz eth</code> - Ethereum teknik analizi
➜ Zaman dilimi seçin (1h, 4h, 1d, 1w)
➜ RSI, MACD, Bollinger Bands dahil

<b>💧 Likidite Haritası:</b>
• <code>/likidite btc</code> - Bitcoin likidite
• <code>/likidite eth</code> - Ethereum likidite
➜ Yüksek likidite bölgelerini gösterir

<b>😱 Korku Endeksi:</b>
• <code>/korku</code> - Fear & Greed Index
➜ Piyasa duygu analizi

<b>⏰ Fiyat Alarmları:</b>
• <code>/alarm btc</code> - Bitcoin alarmı kur
• <code>/alarm eth 5000</code> - Direkt hedef belirt
• <code>/alarmlist</code> - Aktif alarmları gör
• <code>/alarmstop</code> - Tüm alarmları sil

<b>🐋 Ekstra Özellikler:</b>
• <code>/whale</code> - Balina hareketleri
• <code>/moneyflow</code> - Para akışı analizi
• <code>/social</code> - Sosyal medya analizi

<b>📰 Otomatik Haberler:</b>
@primecrypto_tr kanalından anlık haberler otomatik iletilir.

<b>💡 İpuçları:</b>
• Coin sembollerini kısa yazın (btc, eth, sol)
• Komutları / ile başlatın
• Destek için @primecrypto_tr

<b>📌 Örnekler:</b>
<code>/fiyat btc</code>
<code>/analiz eth</code>
<code>/alarm sol 250</code>
<code>/likidite doge</code>
"""
    
    bot.answer_callback_query(call.id, "📚 Komutlar yükleniyor...")
    bot.send_message(call.message.chat.id, help_text, parse_mode="HTML")

# ==========================
# Eski "Nasıl Çalışır?" handler'ı kaldırıldı
# ==========================

# ==========================
# /help ve /yardim komutları
# ==========================
@bot.message_handler(commands=["help", "yardim", "komutlar"])
def send_help(message):
    help_text = """
📚 <b>NASIL ÇALIŞIR?</b>

<b>💰 Fiyat Komutları:</b>
• <code>/fiyat btc</code> - Bitcoin anlık fiyat
• <code>/fiyat eth</code> - Ethereum anlık fiyat
• <code>/fiyat sol</code> - Solana anlık fiyat

<b>📊 Teknik Analiz:</b>
• <code>/analiz btc</code> - Bitcoin teknik analizi
• <code>/analiz eth</code> - Ethereum teknik analizi
➜ Zaman dilimi seçin (1h, 4h, 1d, 1w)
➜ RSI, MACD, Bollinger Bands dahil

<b>💧 Likidite Haritası:</b>
• <code>/likidite btc</code> - Bitcoin likidite
• <code>/likidite eth</code> - Ethereum likidite
➜ Yüksek likidite bölgelerini gösterir

<b>😱 Korku Endeksi:</b>
• <code>/korku</code> - Fear & Greed Index
➜ Piyasa duygu analizi

<b>⏰ Fiyat Alarmları:</b>
• <code>/alarm btc</code> - Bitcoin alarmı kur
• <code>/alarm eth 5000</code> - Direkt hedef belirt
• <code>/alarmlist</code> - Aktif alarmları gör
• <code>/alarmstop</code> - Tüm alarmları sil

<b>🐋 Ekstra Özellikler:</b>
• <code>/whale</code> - Balina hareketleri
• <code>/moneyflow</code> - Para akışı analizi
• <code>/social</code> - Sosyal medya analizi

<b>📰 Otomatik Haberler:</b>
@primecrypto_tr kanalından anlık haberler otomatik iletilir.

<b>💡 İpuçları:</b>
• Coin sembollerini kısa yazın (btc, eth, sol)
• Komutları / ile başlatın
• Destek için @primecrypto_tr

<b>📌 Örnekler:</b>
<code>/fiyat btc</code>
<code>/analiz eth</code>
<code>/alarm sol 250</code>
<code>/likidite doge</code>
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

# ==========================
# /stats komutu - Admin için
# ==========================
@bot.message_handler(commands=["stats"])
def send_stats(message):
    ADMIN_IDS = [5481899729]
    
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Bu komut sadece adminler içindir!")
        return
    
    try:
        news_stats = get_news_stats()
        
        stats_text = f"""
📊 <b>BOT İSTATİSTİKLERİ</b>

👥 <b>Kullanıcılar:</b>
• Aktif kullanıcı: {news_stats.get('active_users', 0)}
• Aktif grup: {news_stats.get('active_groups', 0)}

⏰ <b>Alarmlar:</b>
• Toplam alarm: {sum(len(alarms) for alarms in price_alarms.values())}
• Kullanıcı sayısı: {len(price_alarms)}

🤖 <b>Sistem:</b>
• Bot versiyonu: 2.0
• Uptime: Aktif
• Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📰 <b>Haber Sistemi:</b>
• Kanal: @primecrypto_tr
• Durum: ✅ Aktif
"""
        
        bot.send_message(message.chat.id, stats_text, parse_mode="HTML")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ İstatistik alınamadı: {str(e)}")

# ==========================
# /myid komutu
# ==========================
@bot.message_handler(commands=["myid"])
def send_user_id(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    text = f"""
🆔 <b>ID Bilgilerin:</b>

👤 User ID: <code>{user_id}</code>
💬 Chat ID: <code>{chat_id}</code>
"""
    
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# ==========================
# Otomatik kayıt - Komut olmayan metinler
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
            long_polling_timeout=10,
            timeout=20,
            allowed_updates=[
                "message",
                "callback_query",
                "channel_post",
                "my_chat_member"
            ],
        )
    except Exception as e:
        print(f"❌ Polling hata: {e}. {delay}s sonra tekrar…")
        time.sleep(delay)
        delay = min(delay * 2, 60)
        continue
    break
