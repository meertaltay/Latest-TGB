"""
Crypto Telegram Bot - Configuration File
Token'lar ve temel ayarlar
"""

# =============================================================================
# BOT TOKEN'LARI (BURAYA KENDİ TOKEN'LARINIZI YAZIN!)
# =============================================================================
TELEGRAM_TOKEN = "7642428368:AAHExzUQS3T8Ox93RW2etfX-WYyXJ1QHbU4"
OPENAI_API_KEY = "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"

# =============================================================================
# API AYARLARI
# =============================================================================
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
YAHOO_FINANCE_BASE_URL = "https://query1.finance.yahoo.com/v8/finance"

# =============================================================================
# BOT AYARLARI
# =============================================================================
# Alarm ayarları
ALARM_CHECK_INTERVAL = 30  # Saniye (60 = 1 dakika)
MAX_ALARMS_PER_USER = 10   # Kullanıcı başına maksimum alarm
PRICE_TOLERANCE = 0.001    # Fiyat toleransı (%0.001)

# Analiz – "Basitçe" metninde seviyeleri biraz yakınlaştırma oranı
# 0.003 = %0.3 (direnç biraz aşağı, destek biraz yukarı gösterilir)
SIMPLE_TEXT_LEVEL_OFFSET = 0.003

# Grafik ayarları
CHART_WIDTH = 18
CHART_HEIGHT = 10
CHART_DPI = 200

# API timeout'ları
API_TIMEOUT = 15  # Saniye
BINANCE_TIMEOUT = 10
COINGECKO_TIMEOUT = 10

# =============================================================================
# HABER SİSTEMİ KANAL AYARLARI
# =============================================================================
# Botun post alacağı kanal. ID daha güvenilir; username opsiyonel.
# NOT: ID negatif olabilir ve tırnaksız sayı olarak bırakılmalıdır.
CHANNEL_ID = -1001514453193
CHANNEL_USERNAME = "primecrypto_tr"  # '@' işareti olmadan

# =============================================================================
# DESTEKLENEN COİN LİSTESİ (İLK ETAPTA)
# =============================================================================
POPULAR_COINS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "doge": "dogecoin",
    "ada": "cardano",
    "matic": "matic-network",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ltc": "litecoin",
    "avax": "avalanche-2",
    "link": "chainlink",
    "uni": "uniswap",
    "shib": "shiba-inu",
    "pepe": "pepe"
}

# =============================================================================
# MESAJ SABITLERI - SADELEŞTİRİLMİŞ
# =============================================================================
WELCOME_MESSAGE = """
🚀 **Kripto Bot'a Hoş Geldin!**

💎 **Ana Komutlar:**
📊 /fiyat btc - Bitcoin fiyatı
📈 /analiz eth - Ethereum analizi  
💧 /likidite sol - Solana likidite haritası
⏰ /alarm doge - Dogecoin alarmı

🔥 **Hızlı Başlangıç:**
- /top10 - En büyük coinler
- /trending - Trend coinler
- /korku - Piyasa korkusu

📋 Tüm komutlar için: /yardim
"""

ERROR_MESSAGES = {
    "coin_not_found": "❌ Coin bulunamadı! Popüler coinler: BTC, ETH, SOL, DOGE",
    "api_error": "❌ API hatası! Biraz sonra tekrar dene.",
    "invalid_price": "❌ Geçerli bir fiyat gir! (Örnek: 50000)",
    "no_data": "❌ Veri alınamadı! Internet bağlantını kontrol et."
}

# =============================================================================
# DEBUGGING (GELİŞTİRME SIRASINDA)
# =============================================================================
DEBUG_MODE = True  # False yap production'da
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

print("✅ Config dosyası yüklendi!")

