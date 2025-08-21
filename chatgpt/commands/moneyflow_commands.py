"""
Money Flow Takip Sistemi
Para akışını ve sektör rotasyonunu takip eder
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from telebot import types

class MoneyFlowTracker:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_top_gainers(self, limit=10):
        """Son 24 saatin en çok kazandıranları"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            # USDT paritelerini filtrele ve sırala
            usdt_pairs = [
                {
                    'symbol': item['symbol'],
                    'price': float(item['lastPrice']),
                    'change_percent': float(item['priceChangePercent']),
                    'volume': float(item['quoteVolume']),
                    'count': int(item['count'])
                }
                for item in data 
                if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 1000000
            ]
            
            # Değişime göre sırala
            usdt_pairs.sort(key=lambda x: x['change_percent'], reverse=True)
            
            return usdt_pairs[:limit]
        except Exception as e:
            print(f"Top gainers hatası: {e}")
            return []
    
    def get_top_losers(self, limit=10):
        """Son 24 saatin en çok kaybedenler"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            # USDT paritelerini filtrele ve sırala
            usdt_pairs = [
                {
                    'symbol': item['symbol'],
                    'price': float(item['lastPrice']),
                    'change_percent': float(item['priceChangePercent']),
                    'volume': float(item['quoteVolume']),
                    'count': int(item['count'])
                }
                for item in data 
                if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 1000000
            ]
            
            # Değişime göre sırala (en düşük)
            usdt_pairs.sort(key=lambda x: x['change_percent'])
            
            return usdt_pairs[:limit]
        except Exception as e:
            print(f"Top losers hatası: {e}")
            return []
    
    def get_volume_leaders(self, limit=10):
        """En yüksek hacimli coinler"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            # USDT paritelerini filtrele ve hacme göre sırala
            usdt_pairs = [
                {
                    'symbol': item['symbol'],
                    'price': float(item['lastPrice']),
                    'change_percent': float(item['priceChangePercent']),
                    'volume': float(item['quoteVolume']),
                    'count': int(item['count'])
                }
                for item in data 
                if item['symbol'].endswith('USDT')
            ]
            
            # Hacme göre sırala
            usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
            
            return usdt_pairs[:limit]
        except Exception as e:
            print(f"Volume leaders hatası: {e}")
            return []
    
    def calculate_sector_rotation(self):
        """Sektör rotasyonu analizi"""
        try:
            sectors = {
                'DeFi': ['UNIUSDT', 'AAVEUSDT', 'SUSHIUSDT', 'COMPUSDT', 'MKRUSDT'],
                'Layer1': ['ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT'],
                'Layer2': ['MATICUSDT', 'ARBUSDT', 'OPUSDT', 'IMXUSDT'],
                'Meme': ['DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT'],
                'Gaming': ['AXSUSDT', 'SANDUSDT', 'MANAUSDT', 'ENJUSDT'],
                'AI': ['FETUSDT', 'AGIXUSDT', 'OCEANUSDT', 'RNDR USDT'],
                'Exchange': ['BNBUSDT', 'OKBUSDT', 'HTUSDT', 'FTTUSDT']
            }
            
            url = f"{self.base_url}/ticker/24hr"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return {}
            
            data = response.json()
            price_data = {item['symbol']: float(item['priceChangePercent']) for item in data}
            
            sector_performance = {}
            for sector, coins in sectors.items():
                changes = []
                for coin in coins:
                    if coin in price_data:
                        changes.append(price_data[coin])
                
                if changes:
                    avg_change = sum(changes) / len(changes)
                    sector_performance[sector] = {
                        'avg_change': avg_change,
                        'coin_count': len(changes),
                        'interpretation': self._interpret_sector(avg_change)
                    }
            
            # Sıralama
            sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1]['avg_change'], reverse=True)
            
            return sorted_sectors
        except Exception as e:
            print(f"Sector rotation hatası: {e}")
            return []
    
    def _interpret_sector(self, change):
        """Sektör performansını yorumla"""
        if change > 10:
            return "🔥 Aşırı Güçlü"
        elif change > 5:
            return "🚀 Güçlü"
        elif change > 2:
            return "📈 Pozitif"
        elif change > -2:
            return "➡️ Nötr"
        elif change > -5:
            return "📉 Negatif"
        else:
            return "💀 Çok Zayıf"
    
    def get_unusual_volume(self):
        """Anormal hacim artışı olan coinler"""
        try:
            # Bu örnek bir implementasyon
            # Gerçek kullanımda historical volume datası gerekli
            url = f"{self.base_url}/ticker/24hr"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            unusual = []
            for item in data:
                if not item['symbol'].endswith('USDT'):
                    continue
                
                volume = float(item['quoteVolume'])
                count = int(item['count'])
                
                # Basit anormal hacim tespiti
                # Gerçekte: (bugünkü hacim / ortalama hacim) > 2
                if count > 100000 and volume > 10000000:  # Yüksek işlem sayısı ve hacim
                    unusual.append({
                        'symbol': item['symbol'],
                        'volume': volume,
                        'count': count,
                        'change': float(item['priceChangePercent']),
                        'alert': '🔔 Yüksek aktivite!'
                    })
            
            # Hacme göre sırala
            unusual.sort(key=lambda x: x['volume'], reverse=True)
            
            return unusual[:10]
        except Exception as e:
            print(f"Unusual volume hatası: {e}")
            return []

flow_tracker = MoneyFlowTracker()

def register_moneyflow_commands(bot):
    """Money flow komutlarını kaydet"""
    
    @bot.message_handler(commands=['flow', 'moneyflow', 'paraakisi'])
    def moneyflow_command(message):
        """Para akışı ana menüsü"""
        chat_id = message.chat.id
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚀 En Çok Artan", callback_data="flow_gainers"),
            types.InlineKeyboardButton("💀 En Çok Düşen", callback_data="flow_losers"),
            types.InlineKeyboardButton("📊 Hacim Liderleri", callback_data="flow_volume"),
            types.InlineKeyboardButton("🔄 Sektör Rotasyonu", callback_data="flow_sectors"),
            types.InlineKeyboardButton("⚡ Anormal Hacim", callback_data="flow_unusual"),
            types.InlineKeyboardButton("🎯 Para Nereye?", callback_data="flow_where")
        )
        
        text = """
💰 **PARA AKIŞ TAKİP SİSTEMİ**

Paranın nereye aktığını görün!

🔍 **Özellikler:**
• En çok artan/düşenler
• Hacim liderleri
• Sektör rotasyonu
• Anormal hareketler
• Smart money takibi

Seçim yapın:
"""
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("flow_"))
    def flow_callback(call):
        """Flow callback işlemleri"""
        chat_id = call.message.chat.id
        action = call.data.replace("flow_", "")
        
        if action == "gainers":
            bot.answer_callback_query(call.id, "🚀 En çok artanlar yükleniyor...")
            
            gainers = flow_tracker.get_top_gainers(10)
            
            text = "🚀 **EN ÇOK ARTAN 10 COİN**\n"
            text += "_Son 24 saat_\n\n"
            
            for i, coin in enumerate(gainers, 1):
                symbol = coin['symbol'].replace('USDT', '')
                emoji = "🔥" if coin['change_percent'] > 20 else "🚀" if coin['change_percent'] > 10 else "📈"
                
                text += f"**{i}. {symbol}** {emoji}\n"
                text += f"   📈 Değişim: %{coin['change_percent']:.2f}\n"
                text += f"   💰 Fiyat: ${coin['price']:.6f}\n"
                text += f"   📊 Hacim: ${coin['volume']/1000000:.1f}M\n\n"
            
            text += "💡 _Para bu coinlere akıyor!_"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "losers":
            bot.answer_callback_query(call.id, "💀 En çok düşenler yükleniyor...")
            
            losers = flow_tracker.get_top_losers(10)
            
            text = "💀 **EN ÇOK DÜŞEN 10 COİN**\n"
            text += "_Son 24 saat_\n\n"
            
            for i, coin in enumerate(losers, 1):
                symbol = coin['symbol'].replace('USDT', '')
                emoji = "💀" if coin['change_percent'] < -20 else "🩸" if coin['change_percent'] < -10 else "📉"
                
                text += f"**{i}. {symbol}** {emoji}\n"
                text += f"   📉 Değişim: %{coin['change_percent']:.2f}\n"
                text += f"   💰 Fiyat: ${coin['price']:.6f}\n"
                text += f"   📊 Hacim: ${coin['volume']/1000000:.1f}M\n\n"
            
            text += "⚠️ _Bu coinlerden para çıkıyor!_"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "volume":
            bot.answer_callback_query(call.id, "📊 Hacim liderleri yükleniyor...")
            
            leaders = flow_tracker.get_volume_leaders(10)
            
            text = "📊 **HACİM LİDERLERİ**\n"
            text += "_Son 24 saatlik işlem hacmi_\n\n"
            
            total_volume = sum(coin['volume'] for coin in leaders)
            
            for i, coin in enumerate(leaders, 1):
                symbol = coin['symbol'].replace('USDT', '')
                percent_of_total = (coin['volume'] / total_volume) * 100
                
                text += f"**{i}. {symbol}**\n"
                text += f"   💸 Hacim: ${coin['volume']/1000000000:.2f}B\n"
                text += f"   📊 Oran: %{percent_of_total:.1f}\n"
                text += f"   📈 Değişim: %{coin['change_percent']:.2f}\n\n"
            
            text += f"💰 *Toplam: ${total_volume/1000000000:.2f}B*"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "sectors":
            bot.answer_callback_query(call.id, "🔄 Sektör analizi yapılıyor...")
            
            sectors = flow_tracker.calculate_sector_rotation()
            
            text = "🔄 **SEKTÖR ROTASYONU**\n"
            text += "_Hangi sektöre para akıyor?_\n\n"
            
            for sector, data in sectors:
                text += f"**{sector}** {data['interpretation']}\n"
                text += f"   📊 Ortalama: %{data['avg_change']:.2f}\n"
                text += f"   🪙 Coin sayısı: {data['coin_count']}\n\n"
            
            text += "💡 _En üstteki sektöre para akıyor!_"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "unusual":
            bot.answer_callback_query(call.id, "⚡ Anormal hareketler taranıyor...")
            
            unusual = flow_tracker.get_unusual_volume()
            
            text = "⚡ **ANORMAL HACİM**\n"
            text += "_Olağandışı aktivite gösteren coinler_\n\n"
            
            if unusual:
                for i, coin in enumerate(unusual[:5], 1):
                    symbol = coin['symbol'].replace('USDT', '')
                    
                    text += f"**{i}. {symbol}** {coin['alert']}\n"
                    text += f"   📊 Hacim: ${coin['volume']/1000000:.1f}M\n"
                    text += f"   📈 İşlem: {coin['count']:,}\n"
                    text += f"   💹 Değişim: %{coin['change']:.2f}\n\n"
                
                text += "🔍 _Büyük hareket olabilir!_"
            else:
                text += "✅ Şu an anormal hareket yok"
            
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "where":
            bot.answer_callback_query(call.id, "🎯 Para akışı analiz ediliyor...")
            
            # Özet analiz
            gainers = flow_tracker.get_top_gainers(3)
            sectors = flow_tracker.calculate_sector_rotation()
            volume = flow_tracker.get_volume_leaders(3)
            
            text = "🎯 **PARA NEREYE AKIYOR?**\n\n"
            
            text += "**📍 ŞU AN PARA:**\n\n"
            
            if gainers:
                top_coins = [g['symbol'].replace('USDT', '') for g in gainers[:3]]
                text += f"🔥 **{', '.join(top_coins)}** coinlerine\n\n"
            
            if sectors:
                top_sector = sectors[0][0]
                text += f"🏆 **{top_sector}** sektörüne\n\n"
            
            if volume:
                high_vol = [v['symbol'].replace('USDT', '') for v in volume[:3]]
                text += f"📊 **{', '.join(high_vol)}** yüksek hacimli\n\n"
            
            text += """
💡 **TAVSİYE:**
• Artan coinlere FOMO yapmayın
• Sektör rotasyonunu takip edin
• Hacim artışı = ilgi artışı
• Risk yönetimi unutmayın!
"""
            bot.send_message(chat_id, text, parse_mode="Markdown")

print("💰 Money flow sistemi yüklendi!")
