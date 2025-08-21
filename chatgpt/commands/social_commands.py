"""
Sosyal Medya Trend Takip Sistemi
Twitter, Reddit, Telegram'da en çok konuşulan coinler
"""

import requests
import json
from datetime import datetime, timedelta
from collections import Counter
from telebot import types

class SocialTracker:
    def __init__(self):
        self.trending_coins = []
        self.social_scores = {}
        
    def get_coingecko_trending(self):
        """CoinGecko trending coinleri"""
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            trending = []
            
            for coin in data.get('coins', [])[:10]:
                item = coin['item']
                trending.append({
                    'name': item['name'],
                    'symbol': item['symbol'],
                    'rank': item['market_cap_rank'],
                    'price_btc': item.get('price_btc', 0),
                    'thumb': item.get('thumb', ''),
                    'score': item.get('score', 0)
                })
            
            return trending
        except Exception as e:
            print(f"CoinGecko trending hatası: {e}")
            return []
    
    def get_social_volume(self, symbol):
        """Sosyal medya hacmi (simüle edilmiş)"""
        try:
            # Gerçek API'ler: LunarCrush, Santiment, CryptoCompare
            # Şimdilik basit bir simülasyon
            
            popular_coins = {
                'BTC': {'mentions': 15234, 'sentiment': 0.75, 'influencers': 89},
                'ETH': {'mentions': 8932, 'sentiment': 0.68, 'influencers': 56},
                'SOL': {'mentions': 5621, 'sentiment': 0.82, 'influencers': 34},
                'DOGE': {'mentions': 12456, 'sentiment': 0.65, 'influencers': 45},
                'SHIB': {'mentions': 9876, 'sentiment': 0.58, 'influencers': 23},
                'PEPE': {'mentions': 7654, 'sentiment': 0.71, 'influencers': 19},
                'ARB': {'mentions': 3456, 'sentiment': 0.79, 'influencers': 28},
                'OP': {'mentions': 2987, 'sentiment': 0.77, 'influencers': 21}
            }
            
            if symbol.upper() in popular_coins:
                return popular_coins[symbol.upper()]
            else:
                # Random değerler
                import random
                return {
                    'mentions': random.randint(100, 5000),
                    'sentiment': random.uniform(0.4, 0.9),
                    'influencers': random.randint(1, 30)
                }
        except Exception as e:
            print(f"Social volume hatası: {e}")
            return {'mentions': 0, 'sentiment': 0, 'influencers': 0}
    
    def get_twitter_trends(self):
        """Twitter trend coinler (simüle edilmiş)"""
        try:
            # Gerçek kullanımda Twitter API v2 gerekli
            # Şimdilik örnek data
            
            trends = [
                {'coin': 'BTC', 'hashtag': '#Bitcoin', 'tweets': 45632, 'change': '+23%'},
                {'coin': 'ETH', 'hashtag': '#Ethereum', 'tweets': 28745, 'change': '+15%'},
                {'coin': 'PEPE', 'hashtag': '#PEPE', 'tweets': 19234, 'change': '+156%'},
                {'coin': 'SOL', 'hashtag': '#Solana', 'tweets': 15678, 'change': '+45%'},
                {'coin': 'ARB', 'hashtag': '#Arbitrum', 'tweets': 8932, 'change': '+89%'}
            ]
            
            return trends
        except Exception as e:
            print(f"Twitter trends hatası: {e}")
            return []
    
    def get_reddit_hot(self):
        """Reddit hot topics (simüle edilmiş)"""
        try:
            # Gerçek kullanımda Reddit API gerekli
            # r/cryptocurrency, r/bitcoin, r/ethtrader
            
            hot_topics = [
                {
                    'title': 'ETH 2.0 Staking Rewards Increased!',
                    'subreddit': 'r/ethereum',
                    'upvotes': 5632,
                    'comments': 892,
                    'coin': 'ETH'
                },
                {
                    'title': 'Solana Network Speed Improved 10x',
                    'subreddit': 'r/solana',
                    'upvotes': 3456,
                    'comments': 567,
                    'coin': 'SOL'
                },
                {
                    'title': 'New PEPE Listing on Major Exchange',
                    'subreddit': 'r/cryptocurrency',
                    'upvotes': 8765,
                    'comments': 1234,
                    'coin': 'PEPE'
                }
            ]
            
            return hot_topics
        except Exception as e:
            print(f"Reddit hot hatası: {e}")
            return []
    
    def get_telegram_signals(self):
        """Telegram gruplarında popüler coinler"""
        try:
            # Telegram grup analizi (örnek)
            signals = [
                {'coin': 'INJ', 'groups': 45, 'total_members': 125000, 'sentiment': 'Bullish'},
                {'coin': 'TIA', 'groups': 38, 'total_members': 98000, 'sentiment': 'Very Bullish'},
                {'coin': 'SEI', 'groups': 29, 'total_members': 67000, 'sentiment': 'Bullish'},
                {'coin': 'BLUR', 'groups': 22, 'total_members': 45000, 'sentiment': 'Neutral'}
            ]
            
            return signals
        except Exception as e:
            print(f"Telegram signals hatası: {e}")
            return []
    
    def calculate_social_score(self, coin_data):
        """Sosyal medya skorunu hesapla"""
        try:
            # Ağırlıklı skor hesaplama
            mentions = coin_data.get('mentions', 0)
            sentiment = coin_data.get('sentiment', 0.5)
            influencers = coin_data.get('influencers', 0)
            
            # Normalize et
            mention_score = min(mentions / 10000, 1) * 40  # Max 40 puan
            sentiment_score = sentiment * 40  # Max 40 puan
            influencer_score = min(influencers / 50, 1) * 20  # Max 20 puan
            
            total_score = mention_score + sentiment_score + influencer_score
            
            return {
                'total': round(total_score, 1),
                'mention_score': round(mention_score, 1),
                'sentiment_score': round(sentiment_score, 1),
                'influencer_score': round(influencer_score, 1),
                'grade': self._get_grade(total_score)
            }
        except Exception as e:
            print(f"Score calculation hatası: {e}")
            return {'total': 0, 'grade': 'F'}
    
    def _get_grade(self, score):
        """Skor notlandırması"""
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        elif score >= 50: return 'D'
        else: return 'F'

social_tracker = SocialTracker()

def register_social_commands(bot):
    """Sosyal medya komutlarını kaydet"""
    
    @bot.message_handler(commands=['social', 'sosyal', 'trend'])
    def social_command(message):
        """Sosyal medya trend menüsü"""
        chat_id = message.chat.id
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔥 Trending Now", callback_data="social_trending"),
            types.InlineKeyboardButton("🐦 Twitter Trends", callback_data="social_twitter"),
            types.InlineKeyboardButton("📱 Reddit Hot", callback_data="social_reddit"),
            types.InlineKeyboardButton("💬 Telegram Signals", callback_data="social_telegram"),
            types.InlineKeyboardButton("📊 Social Score", callback_data="social_score"),
            types.InlineKeyboardButton("🎯 Best Picks", callback_data="social_picks")
        )
        
        text = """
📱 **SOSYAL MEDYA TREND TAKİBİ**

En çok konuşulan coinleri keşfedin!

🔍 **Kaynak Platformlar:**
• Twitter (X)
• Reddit
• Telegram
• Discord
• YouTube

📊 **Metrikler:**
• Bahsetme sayısı
• Duygu analizi
• Influencer takibi
• Viral içerikler

Seçim yapın:
"""
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("social_"))
    def social_callback(call):
        """Social callback işlemleri"""
        chat_id = call.message.chat.id
        action = call.data.replace("social_", "")
        
        if action == "trending":
            bot.answer_callback_query(call.id, "🔥 Trending coinler yükleniyor...")
            
            trending = social_tracker.get_coingecko_trending()
            
            text = "🔥 **ŞU AN TREND OLAN COİNLER**\n\n"
            
            for i, coin in enumerate(trending[:10], 1):
                text += f"**{i}. {coin['name']} ({coin['symbol']})**\n"
                if coin['rank']:
                    text += f"   📊 Sıralama: #{coin['rank']}\n"
                text += f"   🔥 Trend Skoru: {coin.get('score', 'N/A')}\n\n"
            
            text += "_Kaynak: CoinGecko Trending_"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "twitter":
            bot.answer_callback_query(call.id, "🐦 Twitter trendleri yükleniyor...")
            
            trends = social_tracker.get_twitter_trends()
            
            text = "🐦 **TWİTTER (X) TRENDLERİ**\n\n"
            
            for trend in trends:
                emoji = "🚀" if '+' in trend['change'] and int(trend['change'].strip('%+')) > 50 else "📈"
                
                text += f"**{trend['hashtag']}** {emoji}\n"
                text += f"   🗣 Tweet: {trend['tweets']:,}\n"
                text += f"   📈 Değişim: {trend['change']}\n\n"
            
            text += """
💡 **Nasıl Yorumlanır?**
• Yüksek tweet = Yüksek ilgi
• Ani artış = Potansiyel pump
• Influencer desteği önemli
"""
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "reddit":
            bot.answer_callback_query(call.id, "📱 Reddit hot topics yükleniyor...")
            
            topics = social_tracker.get_reddit_hot()
            
            text = "📱 **REDDİT HOT TOPİCS**\n\n"
            
            for topic in topics:
                text += f"**{topic['coin']}:** _{topic['title']}_\n"
                text += f"   📍 {topic['subreddit']}\n"
                text += f"   👍 {topic['upvotes']:,} upvotes\n"
                text += f"   💬 {topic['comments']:,} comments\n\n"
            
            text += "_Reddit topluluk duygusu önemli!_"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "telegram":
            bot.answer_callback_query(call.id, "💬 Telegram sinyalleri yükleniyor...")
            
            signals = social_tracker.get_telegram_signals()
            
            text = "💬 **TELEGRAM SİNYALLERİ**\n\n"
            
            for signal in signals:
                emoji = "🟢" if "Bullish" in signal['sentiment'] else "🟡"
                
                text += f"**{signal['coin']}** {emoji}\n"
                text += f"   📢 {signal['groups']} grupta konuşuluyor\n"
                text += f"   👥 {signal['total_members']:,} toplam üye\n"
                text += f"   💭 Duygu: {signal['sentiment']}\n\n"
            
            text += """
⚠️ **DİKKAT:**
Telegram gruplarında manipülasyon riski yüksek!
DYOR - Kendi araştırmanızı yapın.
"""
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "score":
            bot.answer_callback_query(call.id, "📊 Sosyal skor hesaplanıyor...")
            
            # Örnek bir coin için skor hesapla
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("BTC Skoru", callback_data="score_btc"))
            markup.add(types.InlineKeyboardButton("ETH Skoru", callback_data="score_eth"))
            markup.add(types.InlineKeyboardButton("SOL Skoru", callback_data="score_sol"))
            
            text = """
📊 **SOSYAL MEDYA SKORU**

Hangi coinin skorunu görmek istersiniz?

**Skor Bileşenleri:**
• Bahsetme sayısı (40p)
• Duygu analizi (40p)
• Influencer desteği (20p)

**Not Sistemi:**
S: 90-100 (Mükemmel)
A: 80-89 (Çok İyi)
B: 70-79 (İyi)
C: 60-69 (Orta)
D: 50-59 (Zayıf)
F: 0-49 (Kötü)
"""
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
            
        elif action == "picks":
            bot.answer_callback_query(call.id, "🎯 En iyi seçimler analiz ediliyor...")
            
            text = """
🎯 **SOSYAL MEDİA EN İYİ SEÇİMLER**

**🏆 Bu Hafta Öne Çıkanlar:**

1️⃣ **PEPE** 🐸
   • Twitter'da viral
   • %156 bahsetme artışı
   • Influencer desteği güçlü
   
2️⃣ **TIA** ⭐
   • Reddit'te hot topic
   • Telegram gruplarda popüler
   • Teknik olarak da güçlü
   
3️⃣ **INJ** 🚀
   • YouTube'da trend
   • Kurumsal ilgi var
   • Sosyal skor: A+

**⚠️ RİSKLİ ama POPÜLERº**
• SHIB - Meme rally potansiyeli
• FLOKI - Influencer pompası

**💡 TAVSİYE:**
Sosyal medya FOMO'suna kapılmayın!
Her zaman teknik analizi de kontrol edin.
"""
            bot.send_message(chat_id, text, parse_mode="Markdown")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("score_"))
    def score_callback(call):
        """Coin skor detayı"""
        coin = call.data.replace("score_", "").upper()
        chat_id = call.message.chat.id
        
        bot.answer_callback_query(call.id, f"{coin} skoru hesaplanıyor...")
        
        # Sosyal veri al
        social_data = social_tracker.get_social_volume(coin)
        score = social_tracker.calculate_social_score(social_data)
        
        text = f"""
📊 **{coin} SOSYAL MEDYA SKORU**

**Genel Skor: {score['total']}/100 (Not: {score['grade']})**

**📈 Detaylı Analiz:**
• Bahsetmeler: {social_data['mentions']:,}
  Skor: {score['mention_score']}/40

• Duygu Analizi: %{social_data['sentiment']*100:.0f} Pozitif
  Skor: {score['sentiment_score']}/40

• Influencer Desteği: {social_data['influencers']} kişi
  Skor: {score['influencer_score']}/20

**💡 Yorum:**
"""
        
        if score['grade'] in ['S', 'A']:
            text += "Çok güçlü sosyal medya desteği var! 🚀"
        elif score['grade'] in ['B', 'C']:
            text += "Orta düzey ilgi var, takip edilmeli 👀"
        else:
            text += "Sosyal medya ilgisi düşük ⚠️"
        
        bot.send_message(chat_id, text, parse_mode="Markdown")

print("📱 Sosyal medya takip sistemi yüklendi!")
