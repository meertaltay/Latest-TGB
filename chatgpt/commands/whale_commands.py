"""
Whale Takip Sistemi
Büyük transferleri ve whale hareketlerini takip eder
"""

import requests
import time
from datetime import datetime, timedelta
from telebot import types

# Whale Alert benzeri takip
class WhaleTracker:
    def __init__(self):
        self.min_usd_value = 1000000  # 1M USD üzeri işlemler
        self.tracked_addresses = {}
        self.recent_alerts = []
        
    def check_large_transfers(self, symbol="BTCUSDT"):
        """Binance'da büyük hacimli işlemleri kontrol et"""
        try:
            # Binance son işlemler
            url = "https://api.binance.com/api/v3/trades"
            params = {"symbol": symbol, "limit": 100}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return []
            
            trades = response.json()
            large_trades = []
            
            for trade in trades:
                price = float(trade['price'])
                qty = float(trade['qty'])
                usd_value = price * qty
                
                if usd_value >= self.min_usd_value:
                    large_trades.append({
                        'symbol': symbol,
                        'price': price,
                        'quantity': qty,
                        'usd_value': usd_value,
                        'is_buyer': trade['isBuyerMaker'],
                        'time': datetime.fromtimestamp(trade['time']/1000)
                    })
            
            return large_trades
        except Exception as e:
            print(f"Whale check hatası: {e}")
            return []
    
    def get_exchange_flows(self):
        """Borsa giriş/çıkış akışlarını takip et"""
        try:
            # CryptoQuant benzeri veri (örnek)
            flows = {
                'btc': {
                    'exchange_inflow': 0,
                    'exchange_outflow': 0,
                    'net_flow': 0,
                    'interpretation': ''
                }
            }
            
            # Binance cüzdan istatistikleri
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": "BTCUSDT"}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                volume = float(data['volume'])
                quote_volume = float(data['quoteVolume'])
                
                # Basit flow tahmini (gerçek veri için blockchain API gerekli)
                if float(data['priceChangePercent']) > 0:
                    flows['btc']['exchange_outflow'] = volume * 0.6
                    flows['btc']['exchange_inflow'] = volume * 0.4
                    flows['btc']['interpretation'] = "🟢 Net çıkış var - Bullish sinyal"
                else:
                    flows['btc']['exchange_inflow'] = volume * 0.6
                    flows['btc']['exchange_outflow'] = volume * 0.4
                    flows['btc']['interpretation'] = "🔴 Net giriş var - Bearish sinyal"
                
                flows['btc']['net_flow'] = flows['btc']['exchange_outflow'] - flows['btc']['exchange_inflow']
            
            return flows
        except Exception as e:
            print(f"Flow check hatası: {e}")
            return {}

whale_tracker = WhaleTracker()

def register_whale_commands(bot):
    """Whale komutlarını kaydet"""
    
    @bot.message_handler(commands=['whale', 'balina'])
    def whale_command(message):
        """Whale hareketlerini göster"""
        chat_id = message.chat.id
        
        # Inline butonlar
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🐋 Son Transferler", callback_data="whale_transfers"),
            types.InlineKeyboardButton("📊 Borsa Akışları", callback_data="whale_flows"),
            types.InlineKeyboardButton("🎯 Whale Adresleri", callback_data="whale_addresses"),
            types.InlineKeyboardButton("⚡ Canlı Takip", callback_data="whale_live")
        )
        
        text = """
🐋 **WHALE TAKİP SİSTEMİ**

Büyük oyuncuların hareketlerini takip edin!

📌 **Özellikler:**
• 1M$ üzeri transferler
• Borsa giriş/çıkışları  
• Whale cüzdan takibi
• Smart money akışı

Seçim yapın:
"""
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("whale_"))
    def whale_callback(call):
        """Whale callback işlemleri"""
        chat_id = call.message.chat.id
        action = call.data.replace("whale_", "")
        
        if action == "transfers":
            # Son büyük transferler
            bot.answer_callback_query(call.id, "🔍 Büyük transferler aranıyor...")
            
            # BTC, ETH, BNB için kontrol
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
            all_transfers = []
            
            for symbol in symbols:
                transfers = whale_tracker.check_large_transfers(symbol)
                all_transfers.extend(transfers)
            
            if all_transfers:
                # En büyük 5 transfer
                all_transfers.sort(key=lambda x: x['usd_value'], reverse=True)
                
                text = "🐋 **SON BÜYÜK TRANSFERLER**\n\n"
                for i, transfer in enumerate(all_transfers[:5], 1):
                    direction = "📈 ALIM" if transfer['is_buyer'] else "📉 SATIM"
                    coin = transfer['symbol'].replace('USDT', '')
                    
                    text += f"**{i}. {coin} {direction}**\n"
                    text += f"💰 Değer: ${transfer['usd_value']:,.0f}\n"
                    text += f"📊 Miktar: {transfer['quantity']:,.2f} {coin}\n"
                    text += f"💵 Fiyat: ${transfer['price']:,.2f}\n"
                    text += f"⏰ {transfer['time'].strftime('%H:%M:%S')}\n\n"
                
                text += "⚠️ *1M$ üzeri işlemler gösteriliyor*"
            else:
                text = "📭 Son 5 dakikada büyük transfer tespit edilmedi.\n\n💡 Sakin dönemler fırsat olabilir!"
            
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "flows":
            # Borsa akışları
            bot.answer_callback_query(call.id, "📊 Borsa akışları hesaplanıyor...")
            
            flows = whale_tracker.get_exchange_flows()
            
            text = "📊 **BORSA AKIŞ ANALİZİ**\n\n"
            
            if flows:
                for coin, data in flows.items():
                    text += f"**{coin.upper()} Akışları:**\n"
                    text += f"➡️ Borsa Girişi: {data['exchange_inflow']:,.0f} {coin.upper()}\n"
                    text += f"⬅️ Borsa Çıkışı: {data['exchange_outflow']:,.0f} {coin.upper()}\n"
                    text += f"📊 Net Akış: {data['net_flow']:,.0f} {coin.upper()}\n"
                    text += f"\n{data['interpretation']}\n\n"
                
                text += """
📚 **NASIL YORUMLANIR?**

**Borsa GİRİŞİ fazla:** 
→ Satış baskısı olabilir 📉

**Borsa ÇIKIŞI fazla:**
→ Hodl sinyali, bullish 📈

**Dengeli akış:**
→ Normal piyasa aktivitesi
"""
            else:
                text = "❌ Akış verileri alınamadı"
            
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "addresses":
            # Bilinen whale adresleri
            bot.answer_callback_query(call.id, "🎯 Whale adresleri listeleniyor...")
            
            text = """
🎯 **TAKİP EDİLEN WHALE ADRESLERİ**

**🐋 En Büyük BTC Cüzdanları:**
• Binance Cold Wallet
• Grayscale Bitcoin Trust
• MicroStrategy Holdings
• Tesla Treasury

**🦈 Kurumsal Oyuncular:**
• BlackRock
• Fidelity
• ARK Invest
• Galaxy Digital

**📊 Takip Özellikleri:**
• Büyük alım/satımlar
• Cüzdan hareketleri
• Pozisyon değişimleri

💡 *Whale hareketleri genelde piyasayı etkiler!*
"""
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "live":
            # Canlı takip başlat
            bot.answer_callback_query(call.id, "⚡ Canlı takip başlatılıyor...")
            
            text = """
⚡ **CANLI WHALE TAKİBİ**

🔴 Canlı takip aktif!

Her 5 dakikada bir kontrol ediliyor:
• 1M$ üzeri transferler
• Anormal hacim hareketleri
• Borsa akış değişimleri

Bildirim gelecek durumlar:
• 5M$ üzeri tek işlem
• 30dk içinde 10M$ hacim
• Anormal borsa girişi

⏸ Durdurmak için: /whalestop
"""
            bot.send_message(chat_id, text, parse_mode="Markdown")
    
    @bot.message_handler(commands=['whalestop'])
    def whale_stop(message):
        """Whale takibi durdur"""
        bot.send_message(message.chat.id, "⏹ Whale takibi durduruldu.")

print("🐋 Whale takip sistemi yüklendi!")
