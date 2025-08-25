"""
Enhanced /analiz komutu - Çoklu timeframe, AI yorum, risk analizi
"""

from __future__ import annotations
from telebot import types
import pandas as pd
import numpy as np
from datetime import datetime
import requests

try:
    from config import SIMPLE_TEXT_LEVEL_OFFSET, OPENAI_API_KEY
except Exception:
    SIMPLE_TEXT_LEVEL_OFFSET = 0.003
    OPENAI_API_KEY = None

from utils.binance_api import find_binance_symbol, get_binance_ohlc, get_24h_stats
from utils.modern_charts import create_ultra_modern_chart  # Modern chart kullan
from utils.technical_analysis import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands,
    calculate_sma, calculate_ema, calculate_volume_analysis, generate_trading_signals
)

# ---------- Yardımcı Fonksiyonlar ----------
def _split_command(text: str):
    parts = (text or "").strip().split()
    if not parts:
        return []
    parts[0] = parts[0].split("@")[0]
    return parts

def _fmt_price(v: float) -> str:
    try:
        if v < 0.01: return f"${v:.8f}"
        if v < 1:    return f"${v:.6f}"
        return f"${v:,.2f}"
    except Exception:
        return str(v)

def calculate_analysis_score(rsi: float, macd_data, bb_data, volume_data, current_price: float, sma_20: float) -> tuple:
    """Gelişmiş skor hesaplama"""
    score = 5.0
    signals = []
    
    # RSI Analizi
    if rsi < 30:
        score += 2.5
        signals.append("RSI aşırı satım ✅")
    elif rsi < 40:
        score += 1.5
        signals.append("RSI düşük")
    elif rsi > 70:
        score -= 2.5
        signals.append("RSI aşırı alım ⚠️")
    elif rsi > 60:
        score -= 1.5
        signals.append("RSI yüksek")
    
    # MACD Analizi
    try:
        macd_current = macd_data['macd'].iloc[-1]
        macd_signal = macd_data['signal'].iloc[-1]
        macd_prev = macd_data['macd'].iloc[-2]
        signal_prev = macd_data['signal'].iloc[-2]
        
        if macd_current > macd_signal:
            score += 1.5
            if macd_prev <= signal_prev:  # Crossover
                score += 1
                signals.append("MACD pozitif kesişim 🎯")
            else:
                signals.append("MACD pozitif")
        else:
            score -= 1.5
            if macd_prev >= signal_prev:  # Crossunder
                score -= 1
                signals.append("MACD negatif kesişim ⚠️")
            else:
                signals.append("MACD negatif")
    except:
        pass
    
    # Bollinger Bands
    try:
        upper = bb_data['upper'].iloc[-1]
        lower = bb_data['lower'].iloc[-1]
        
        if current_price <= lower:
            score += 2
            signals.append("Bollinger alt bandında 🎯")
        elif current_price >= upper:
            score -= 2
            signals.append("Bollinger üst bandında ⚠️")
    except:
        pass
    
    # SMA Trend
    if current_price > sma_20:
        score += 1
        signals.append("SMA20 üzerinde")
    else:
        score -= 1
        signals.append("SMA20 altında")
    
    # Volume Analizi
    if volume_data.get('volume_ratio', 1) > 1.5:
        signals.append("Yüksek hacim 📊")
        score += 0.5
    elif volume_data.get('volume_ratio', 1) < 0.5:
        signals.append("Düşük hacim ⚠️")
        score -= 0.5
    
    # Skoru 0-10 aralığına sınırla
    score = max(0, min(10, score))
    
    return score, signals

def get_multi_timeframe_analysis(symbol: str) -> dict:
    """Çoklu timeframe analizi"""
    timeframes = {
        '1h': {'limit': 100, 'weight': 0.3},
        '4h': {'limit': 100, 'weight': 0.3},
        '1d': {'limit': 100, 'weight': 0.25},
        '1w': {'limit': 52, 'weight': 0.15}
    }
    
    results = {}
    
    for tf, config in timeframes.items():
        try:
            df = get_binance_ohlc(symbol, interval=tf, limit=config['limit'])
            if df is None or df.empty:
                continue
            
            # Temel hesaplamalar
            current_price = float(df['close'].iloc[-1])
            rsi = float(calculate_rsi(df['close']).iloc[-1])
            macd = calculate_macd(df['close'])
            bb = calculate_bollinger_bands(df['close'])
            sma20 = float(calculate_sma(df['close'], 20).iloc[-1])
            volume_data = calculate_volume_analysis(df)
            
            # Skor hesapla
            score, signals = calculate_analysis_score(rsi, macd, bb, volume_data, current_price, sma20)
            
            # MACD durumu
            macd_status = "↑" if macd['macd'].iloc[-1] > macd['signal'].iloc[-1] else "↓"
            
            results[tf] = {
                'score': score,
                'rsi': rsi,
                'macd_status': macd_status,
                'signals': signals[:2],  # İlk 2 sinyal
                'price': current_price,
                'volume_ratio': volume_data.get('volume_ratio', 1)
            }
        except Exception as e:
            print(f"Timeframe {tf} analiz hatası: {e}")
            continue
    
    return results

def calculate_risk_metrics(df: pd.DataFrame, current_price: float) -> dict:
    """Risk metriklerini hesapla"""
    try:
        # Volatilite hesapla (ATR benzeri)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        # Volatilite yüzdesi
        volatility_pct = (atr / current_price) * 100
        
        # Risk skoru (0-10)
        if volatility_pct < 2:
            risk_score = 3
            risk_level = "Düşük"
        elif volatility_pct < 3:
            risk_score = 5
            risk_level = "Orta"
        elif volatility_pct < 5:
            risk_score = 7
            risk_level = "Yüksek"
        else:
            risk_score = 9
            risk_level = "Çok Yüksek"
        
        # Önerilen pozisyon boyutu
        if risk_score <= 3:
            position_size = "Max %10"
        elif risk_score <= 5:
            position_size = "Max %5-7"
        elif risk_score <= 7:
            position_size = "Max %3-5"
        else:
            position_size = "Max %1-3"
        
        return {
            'volatility_pct': volatility_pct,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'position_size': position_size,
            'atr': atr
        }
    except Exception as e:
        print(f"Risk hesaplama hatası: {e}")
        return {
            'volatility_pct': 0,
            'risk_score': 5,
            'risk_level': "Orta",
            'position_size': "Max %5",
            'atr': 0
        }

def calculate_support_resistance(df: pd.DataFrame, current_price: float) -> dict:
    """Gelişmiş destek/direnç hesaplama"""
    try:
        # Fibonacci seviyeleri
        high = df['high'].tail(50).max()
        low = df['low'].tail(50).min()
        diff = high - low
        
        fib_levels = {
            '0%': high,
            '23.6%': high - diff * 0.236,
            '38.2%': high - diff * 0.382,
            '50%': high - diff * 0.5,
            '61.8%': high - diff * 0.618,
            '100%': low
        }
        
        # En yakın destek ve dirençleri bul
        support = None
        resistance = None
        
        for level, price in fib_levels.items():
            if price < current_price and (support is None or price > support):
                support = price
            elif price > current_price and (resistance is None or price < resistance):
                resistance = price
        
        # Pivot noktaları
        pivot = (df['high'].iloc[-1] + df['low'].iloc[-1] + df['close'].iloc[-1]) / 3
        r1 = 2 * pivot - df['low'].iloc[-1]
        s1 = 2 * pivot - df['high'].iloc[-1]
        
        return {
            'strong_support': support or s1,
            'strong_resistance': resistance or r1,
            'pivot': pivot,
            'fib_levels': fib_levels
        }
    except Exception as e:
        print(f"S/R hesaplama hatası: {e}")
        return {
            'strong_support': current_price * 0.95,
            'strong_resistance': current_price * 1.05,
            'pivot': current_price,
            'fib_levels': {}
        }

def generate_ai_comment(symbol: str, multi_tf_results: dict, risk_metrics: dict, sr_levels: dict) -> str:
    """AI benzeri akıllı yorum üret - geliştirilmiş hedeflerle"""
    
    # Genel skor hesapla
    total_score = 0
    total_weight = 0
    
    for tf, data in multi_tf_results.items():
        weight = {'1h': 0.3, '4h': 0.3, '1d': 0.25, '1w': 0.15}.get(tf, 0.1)
        total_score += data['score'] * weight
        total_weight += weight
    
    if total_weight > 0:
        final_score = total_score / total_weight
    else:
        final_score = 5
    
    # Trend belirleme
    if final_score >= 7:
        trend = "güçlü yükseliş"
        action = "ALIM 🟢"
        emoji = "🚀"
    elif final_score >= 5.5:
        trend = "yükseliş"
        action = "DİKKATLİ ALIM 🟡"
        emoji = "📈"
    elif final_score >= 4.5:
        trend = "yatay"
        action = "BEKLE ⏳"
        emoji = "⚖️"
    elif final_score >= 3:
        trend = "düşüş"
        action = "DİKKATLİ SATIM 🟡"
        emoji = "📉"
    else:
        trend = "güçlü düşüş"
        action = "SATIM 🔴"
        emoji = "🔻"
    
    # Kısa vadeli durum
    h1_score = multi_tf_results.get('1h', {}).get('score', 5)
    if h1_score >= 7:
        short_term = "Kısa vadede güçlü alım sinyalleri var. Momentum pozitif"
    elif h1_score >= 5:
        short_term = "Kısa vadede kararsız, yön arayışında"
    else:
        short_term = "Kısa vadede satış baskısı hakim"
    
    # Risk değerlendirmesi
    risk_comment = f"Volatilite %{risk_metrics['volatility_pct']:.1f} seviyesinde"
    
    # Entry/Exit önerileri - DETAYLI
    current_price = list(multi_tf_results.values())[0]['price'] if multi_tf_results else 0
    
    if final_score >= 7:  # GÜÇLÜ ALIM
        entry = f"🎯 <b>Entry Bölgesi:</b> ${current_price * 0.99:,.0f} - ${current_price:,.0f}"
        tp1 = current_price * 1.02
        tp2 = current_price * 1.05
        tp3 = current_price * 1.10
        sl = sr_levels['strong_support'] * 0.98 if sr_levels['strong_support'] < current_price else current_price * 0.98
        
        targets = f"""
📍 <b>Hedefler:</b>
   • TP1: ${tp1:,.0f} (+%2.0) ✅
   • TP2: ${tp2:,.0f} (+%5.0) 🎯
   • TP3: ${tp3:,.0f} (+%10.0) 🚀"""
        
        stop = f"🛑 <b>Stop Loss:</b> ${sl:,.0f} (-%{((current_price - sl)/current_price)*100:.1f})"
        
        # Risk/Reward hesapla
        risk = current_price - sl
        reward = tp2 - current_price
        rr_ratio = reward / risk if risk > 0 else 0
        risk_reward = f"📊 <b>Risk/Reward:</b> 1:{rr_ratio:.1f}"
        
    elif final_score >= 5.5:  # ALIM
        entry = f"🎯 <b>Entry Bölgesi:</b> ${current_price * 0.995:,.0f} - ${current_price:,.0f}"
        tp1 = current_price * 1.015
        tp2 = current_price * 1.03
        sl = current_price * 0.98
        
        targets = f"""
📍 <b>Hedefler:</b>
   • TP1: ${tp1:,.0f} (+%1.5) ✅
   • TP2: ${tp2:,.0f} (+%3.0) 🎯"""
        
        stop = f"🛑 <b>Stop Loss:</b> ${sl:,.0f} (-%2.0)"
        risk_reward = "📊 <b>Risk/Reward:</b> 1:1.5"
        
    elif final_score <= 3:  # GÜÇLÜ SATIM
        entry = f"🎯 <b>Short Entry:</b> ${current_price:,.0f} - ${current_price * 1.01:,.0f}"
        tp1 = current_price * 0.98
        tp2 = current_price * 0.95
        tp3 = current_price * 0.90
        sl = sr_levels['strong_resistance'] * 1.02 if sr_levels['strong_resistance'] > current_price else current_price * 1.02
        
        targets = f"""
📍 <b>Hedefler (Short):</b>
   • TP1: ${tp1:,.0f} (-%2.0) ✅
   • TP2: ${tp2:,.0f} (-%5.0) 🎯
   • TP3: ${tp3:,.0f} (-%10.0) 🔻"""
        
        stop = f"🛑 <b>Stop Loss:</b> ${sl:,.0f} (+%{((sl - current_price)/current_price)*100:.1f})"
        
        risk = sl - current_price
        reward = current_price - tp2
        rr_ratio = reward / risk if risk > 0 else 0
        risk_reward = f"📊 <b>Risk/Reward:</b> 1:{rr_ratio:.1f}"
        
    else:  # BEKLE
        entry = "⏳ <b>Entry:</b> Net sinyal bekleyin"
        targets = f"""
📍 <b>İzlenecek Seviyeler:</b>
   • Üst: ${sr_levels['strong_resistance']:,.0f}
   • Alt: ${sr_levels['strong_support']:,.0f}"""
        stop = "🛑 <b>Stop:</b> Pozisyon açmayın"
        risk_reward = "📊 <b>Risk/Reward:</b> —"
    
    # AI yorumu oluştur
    ai_comment = f"""🤖 <b>AI ANALİZİ</b> {emoji}

<b>📈 Piyasa Durumu:</b>
{trend.upper()} trendi. {short_term}. {risk_comment}.

<b>📊 Teknik Durum:</b>
• Güçlü Destek: ${sr_levels['strong_support']:,.0f}
• Pivot Nokta: ${sr_levels.get('pivot', current_price):,.0f}  
• Güçlü Direnç: ${sr_levels['strong_resistance']:,.0f}

<b>💡 Strateji:</b> {action}
{entry}
{targets}
{stop}
{risk_reward}

<b>⚠️ Risk Yönetimi:</b>
• Pozisyon Boyutu: {risk_metrics['position_size']}
• Risk Seviyesi: {risk_metrics['risk_level']} ({risk_metrics['risk_score']}/10)
• ATR: ${risk_metrics.get('atr', 0):.2f}"""
    
    return ai_comment

def get_market_sentiment() -> dict:
    """Fear & Greed ve diğer sentiment verileri"""
    try:
        # Fear & Greed Index
        response = requests.get("https://api.alternative.me/fng/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            fg_value = int(data['data'][0]['value'])
            fg_text = data['data'][0]['value_classification']
        else:
            fg_value = 50
            fg_text = "Neutral"
    except:
        fg_value = 50
        fg_text = "Neutral"
    
    return {
        'fear_greed': fg_value,
        'fear_greed_text': fg_text
    }

# ---------- Ana Komut Handler ----------
def register_analysis_commands(bot):

    @bot.message_handler(commands=['analiz'])
    def analiz_cmd(message):
        parts = _split_command(message.text)
        if len(parts) < 2:
            bot.send_message(
                message.chat.id,
                "📊 <b>Kripto Analiz</b>\n\n"
                "🔹 <b>Kullanım:</b> /analiz COIN\n\n"
                "Örnekler:\n"
                "• /analiz btc\n• /analiz eth\n• /analiz sol\n\n"
                "📈 Coin seçtikten sonra analiz tipi seçin!",
                parse_mode="HTML"
            )
            return

        coin_input = parts[1].lower()
        symbol = find_binance_symbol(coin_input)
        if not symbol:
            bot.send_message(
                message.chat.id,
                f"❌ <b>'{coin_input.upper()}' Binance'da bulunamadı!</b>\n\n"
                "💡 <b>Popüler:</b> BTC, ETH, SOL, DOGE, ADA",
                parse_mode="HTML"
            )
            return

        # Gelişmiş seçim menüsü
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        # Timeframe butonları
        markup.add(
            types.InlineKeyboardButton("⚡ 1 Saat", callback_data=f"tf_1h_{coin_input}"),
            types.InlineKeyboardButton("📊 4 Saat", callback_data=f"tf_4h_{coin_input}"),
            types.InlineKeyboardButton("📈 1 Gün", callback_data=f"tf_1d_{coin_input}")
        )
        markup.add(
            types.InlineKeyboardButton("📅 1 Hafta", callback_data=f"tf_1w_{coin_input}"),
            types.InlineKeyboardButton("🔥 DETAYLI ANALİZ", callback_data=f"tf_full_{coin_input}")
        )

        coin_name = symbol.replace('USDT','').upper()
        bot.send_message(
            message.chat.id,
            f"🎯 <b>{coin_name} Analizi</b>\n\n"
            "⏰ <b>Analiz türünü seçin:</b>\n\n"
            "• <b>Tekli Zaman:</b> Klasik analiz\n"
            "• <b>🔥 DETAYLI:</b> Çoklu timeframe + AI yorum + Risk analizi",
            reply_markup=markup, parse_mode="HTML"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("tf_"))
    def on_tf(call):
        try:
            _, tf, coin_input = call.data.split("_", 2)
        except Exception:
            bot.answer_callback_query(call.id, "⚠️ Geçersiz seçim")
            return

        symbol = find_binance_symbol(coin_input)
        if not symbol:
            bot.answer_callback_query(call.id, "⚠️ Coin bulunamadı")
            return

        # Mesajı sil
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        if tf == "full":
            # DETAYLI ANALİZ
            bot.answer_callback_query(call.id, "🔥 Detaylı analiz hazırlanıyor...")
            bot.send_message(
                call.message.chat.id,
                f"⏳ <b>{symbol} - Detaylı Analiz</b>\n\n"
                "📊 Çoklu timeframe analizi...\n"
                "🤖 AI yorumu hazırlanıyor...\n"
                "⚠️ Risk metrikleri hesaplanıyor...\n\n"
                "⚡ Bu işlem 10-15 saniye sürebilir.",
                parse_mode="HTML"
            )
            _perform_full_analysis(bot, call.message.chat.id, symbol, coin_input)
        else:
            # TEKLİ ZAMAN ANALİZİ
            names = {"1h":"1 Saat","4h":"4 Saat","1d":"1 Gün","1w":"1 Hafta"}
            tf_name = names.get(tf, tf)
            bot.answer_callback_query(call.id, f"🎯 {tf_name} analiz başlıyor...")
            bot.send_message(
                call.message.chat.id,
                f"⏳ <b>{symbol} - {tf_name} Analiz</b>\n\n"
                "📊 Veriler alınıyor...\n📈 Grafik oluşturuluyor...\n\n"
                "⚡ Bu işlem 5-10 saniye sürebilir.",
                parse_mode="HTML"
            )
            _perform_single_analysis(bot, call.message.chat.id, symbol, coin_input, tf, tf_name)

# ---------- Detaylı Analiz ----------
def _perform_full_analysis(bot, chat_id: int, symbol: str, coin_input: str):
    try:
        # 1. Çoklu timeframe analizi
        multi_tf_results = get_multi_timeframe_analysis(symbol)
        
        if not multi_tf_results:
            bot.send_message(chat_id, f"❌ {symbol} veri alınamadı!")
            return
        
        # 2. Risk metrikleri (1d verisi üzerinden)
        df_daily = get_binance_ohlc(symbol, interval='1d', limit=100)
        if df_daily is not None and not df_daily.empty:
            current_price = float(df_daily['close'].iloc[-1])
            risk_metrics = calculate_risk_metrics(df_daily, current_price)
            sr_levels = calculate_support_resistance(df_daily, current_price)
        else:
            current_price = list(multi_tf_results.values())[0]['price']
            risk_metrics = {'volatility_pct': 0, 'risk_score': 5, 'risk_level': 'Orta', 'position_size': 'Max %5'}
            sr_levels = {'strong_support': current_price * 0.95, 'strong_resistance': current_price * 1.05, 'pivot': current_price}
        
        # 3. Market sentiment
        sentiment = get_market_sentiment()
        
        # 4. 24h istatistikler
        stats_24h = get_24h_stats(symbol)
        
        # 5. AI yorumu oluştur
        ai_comment = generate_ai_comment(symbol, multi_tf_results, risk_metrics, sr_levels)
        
        # 6. Grafik oluştur (opsiyonel - 1d grafiği)
        try:
            analysis_data = {
                'price': current_price,
                'rsi': multi_tf_results.get('1d', {}).get('rsi', 50),
                'overall_score': sum(d['score'] for d in multi_tf_results.values()) / len(multi_tf_results) if multi_tf_results else 5,
                'signals': []
            }
            
            if df_daily is not None and not df_daily.empty:
                # Grafik için ek hesaplamalar
                analysis_data['macd_data'] = calculate_macd(df_daily['close'])
                analysis_data['bb_data'] = calculate_bollinger_bands(df_daily['close'])
                analysis_data['fib_levels'] = sr_levels.get('fib_levels', {})
                
                chart_img = create_ultra_modern_chart(df_daily, symbol, analysis_data, '1d')
                if chart_img:
                    bot.send_photo(chat_id, chart_img)
        except Exception as e:
            print(f"Grafik hatası: {e}")
        
        # 7. Detaylı mesaj oluştur
        text = f"🔥 <b>{coin_input.upper()} - DETAYLI ANALİZ</b>\n\n"
        text += f"💰 <b>Fiyat:</b> {_fmt_price(current_price)}\n"
        
        if stats_24h:
            text += f"📊 <b>24h Değişim:</b> {stats_24h.get('change_24h', 0):+.2f}%\n"
            text += f"📈 <b>24h Hacim:</b> ${stats_24h.get('volume_24h', 0)/1e6:.1f}M\n\n"
        else:
            text += "\n"
        
        # Çoklu timeframe özet
        text += "📊 <b>ÇOKLU ZAMAN ANALİZİ:</b>\n"
        text += "━━━━━━━━━━━━━━━━━\n"
        
        for tf in ['1h', '4h', '1d', '1w']:
            if tf in multi_tf_results:
                data = multi_tf_results[tf]
                score = data['score']
                
                # Emoji ve durum
                if score >= 7:
                    emoji = "🟢"
                    status = "ALIM"
                elif score >= 5.5:
                    emoji = "🟡"
                    status = "YÜKSEL"
                elif score >= 4.5:
                    emoji = "⚪"
                    status = "NÖTR"
                elif score >= 3:
                    emoji = "🟡"
                    status = "DÜŞÜŞ"
                else:
                    emoji = "🔴"
                    status = "SATIM"
                
                tf_name = {'1h': '1 Saat', '4h': '4 Saat', '1d': '1 Gün', '1w': '1 Hafta'}.get(tf, tf)
                text += f"{emoji} <b>{tf_name:8}</b> {status:6} ({score:.1f}/10) RSI:{int(data['rsi'])} MACD:{data['macd_status']}\n"
        
        # Genel skor
        avg_score = sum(d['score'] for d in multi_tf_results.values()) / len(multi_tf_results) if multi_tf_results else 5
        
        text += "━━━━━━━━━━━━━━━━━\n"
        text += f"💎 <b>Genel Skor:</b> {avg_score:.1f}/10 "
        
        if avg_score >= 7:
            text += "(GÜÇLÜ ALIM 🚀)\n\n"
        elif avg_score >= 5.5:
            text += "(ALIM 📈)\n\n"
        elif avg_score >= 4.5:
            text += "(BEKLE ⚖️)\n\n"
        elif avg_score >= 3:
            text += "(SATIM 📉)\n\n"
        else:
            text += "(GÜÇLÜ SATIM 🔻)\n\n"
        
        # Risk Analizi
        text += "⚠️ <b>RİSK ANALİZİ:</b>\n"
        text += f"• Volatilite: %{risk_metrics['volatility_pct']:.1f}\n"
        text += f"• Risk Seviyesi: {risk_metrics['risk_level']} ({risk_metrics['risk_score']}/10)\n"
        text += f"• Önerilen Pozisyon: {risk_metrics['position_size']}\n\n"
        
        # Destek/Direnç
        text += "📏 <b>ÖNEMLİ SEVİYELER:</b>\n"
        text += f"🔴 Direnç: {_fmt_price(sr_levels['strong_resistance'])}\n"
        text += f"⚪ Pivot: {_fmt_price(sr_levels['pivot'])}\n"
        text += f"🟢 Destek: {_fmt_price(sr_levels['strong_support'])}\n\n"
        
        # Market Sentiment
        text += "😱 <b>PİYASA DUYGUSU:</b>\n"
        text += f"Fear & Greed: {sentiment['fear_greed']}/100 ({sentiment['fear_greed_text']})\n\n"
        
        # AI Yorumu
        text += ai_comment + "\n\n"
        
        # Uyarı
        text += "⚠️ <i>Bu analiz yatırım tavsiyesi değildir!</i>"
        
        bot.send_message(chat_id, text, parse_mode="HTML")
        
    except Exception as e:
        print(f"Detaylı analiz hatası: {e}")
        bot.send_message(chat_id, f"❌ Analiz tamamlanamadı: {str(e)}")

# ---------- Tekli Analiz (Geliştirilmiş) ----------
def _perform_single_analysis(bot, chat_id: int, symbol: str, coin_input: str, timeframe: str, tf_name: str):
    limit_map = {'1h':168, '4h':168, '1d':100, '1w':52}
    limit = limit_map.get(timeframe, 100)
    df = get_binance_ohlc(symbol, interval=timeframe, limit=limit)
    
    if df is None or df.empty:
        bot.send_message(chat_id, f"❌ {symbol} veri alınamadı!")
        return

    cur = float(df['close'].iloc[-1])
    prev = float(df['close'].iloc[-2]) if len(df)>1 else cur
    chg = ((cur - prev)/prev)*100 if prev else 0.0

    rsi = float(calculate_rsi(df['close']).iloc[-1])
    macd = calculate_macd(df['close'])
    bb = calculate_bollinger_bands(df['close'])
    sma20 = float(calculate_sma(df['close'],20).iloc[-1])
    sma50 = float(calculate_sma(df['close'],50).iloc[-1]) if len(df)>50 else 0.0
    vol = calculate_volume_analysis(df)
    signals = generate_trading_signals(df)

    # Destek/Direnç ve Risk
    sr_levels = calculate_support_resistance(df, cur)
    risk_metrics = calculate_risk_metrics(df, cur)
    
    # Skor hesapla
    score, score_signals = calculate_analysis_score(rsi, macd, bb, vol, cur, sma20)

    # Grafik
    try:
        analysis_data = {
            'price': cur,
            'rsi': rsi,
            'macd_data': macd,
            'bb_data': bb,
            'signals': signals,
            'overall_score': score,
            'fib_levels': sr_levels.get('fib_levels', {})
        }
        
        chart_img = create_ultra_modern_chart(df, symbol, analysis_data, timeframe)
        if chart_img:
            bot.send_photo(chat_id, chart_img)
    except Exception as e:
        print(f"Grafik hatası: {e}")

    # AI YORUM - TEKLİ ANALİZ İÇİN
    ai_comment = generate_single_ai_comment(score, rsi, macd, cur, sr_levels, risk_metrics, vol, score_signals)

    # Mesaj oluştur
    price_str = _fmt_price(cur)
    change_emoji = "📈" if chg > 0 else "📉"
    
    text = f"📊 <b>{coin_input.upper()} - {tf_name} Analiz</b>\n\n"
    text += f"💰 <b>Güncel Fiyat:</b> {price_str}\n"
    text += f"{change_emoji} <b>Değişim:</b> %{chg:+.2f}\n"
    text += f"📈 <b>RSI:</b> {int(rsi)}\n"
    text += f"📊 <b>Hacim:</b> {vol.get('volume_analysis','—')}\n\n"

    # AI YORUM EKLE
    text += ai_comment + "\n\n"

    # Seviyeler
    text += "📏 <b>ÖNEMLİ SEVİYELER:</b>\n"
    text += f"🔴 Direnç: {_fmt_price(sr_levels['strong_resistance'])}\n"
    text += f"🟢 Destek: {_fmt_price(sr_levels['strong_support'])}\n\n"

    # Aktif sinyaller (kısa)
    if signals:
        text += "⚡ <b>SİNYALLER:</b> "
        buy_count = len([s for s in signals if s.get('type')=='BUY'])
        sell_count = len([s for s in signals if s.get('type')=='SELL'])
        if buy_count > sell_count:
            text += f"{buy_count} ALIM sinyali 🟢\n\n"
        elif sell_count > buy_count:
            text += f"{sell_count} SATIM sinyali 🔴\n\n"
        else:
            text += "Karışık sinyaller ⚖️\n\n"

    text += f"🔧 ⏰ /alarm {coin_input}   |   💧 /likidite {coin_input}\n"
    text += "⚠️ <i>Bu analiz yatırım tavsiyesi değildir!</i>"

    bot.send_message(chat_id, text, parse_mode="HTML")

def generate_single_ai_comment(score, rsi, macd_data, current_price, sr_levels, risk_metrics, vol, signals):
    """Tekli analiz için profesyonel AI yorumu"""
    
    # Ana trend analizi
    if score >= 7:
        trend = "güçlü yükseliş"
        momentum = "pozitif"
        outlook = "iyimser"
    elif score >= 5.5:
        trend = "yükseliş"
        momentum = "kararsız"
        outlook = "temkinli iyimser"
    elif score >= 4.5:
        trend = "yatay"
        momentum = "nötr"
        outlook = "belirsiz"
    elif score >= 3:
        trend = "düşüş"
        momentum = "negatif"
        outlook = "temkinli kötümser"
    else:
        trend = "güçlü düşüş"
        momentum = "çok negatif"
        outlook = "kötümser"
    
    # RSI durumu
    if rsi < 25:
        rsi_status = "aşırı satım bölgesinin derinlerinde"
        rsi_signal = "Teknik tepki potansiyeli çok yüksek"
    elif rsi < 30:
        rsi_status = "aşırı satım bölgesinde"
        rsi_signal = "Toparlanma yakın olabilir"
    elif rsi < 40:
        rsi_status = "satış baskısı altında"
        rsi_signal = "Düşüş devam edebilir"
    elif rsi > 75:
        rsi_status = "aşırı alım bölgesinin zirvesinde"
        rsi_signal = "Kar realizasyonu riski yüksek"
    elif rsi > 70:
        rsi_status = "aşırı alım bölgesinde"
        rsi_signal = "Geri çekilme beklenebilir"
    elif rsi > 60:
        rsi_status = "alım bölgesinde"
        rsi_signal = "Momentum güçlü"
    else:
        rsi_status = "nötr bölgede"
        rsi_signal = "Yön arayışında"
    
    # MACD analizi
    try:
        macd_current = macd_data['macd'].iloc[-1]
        macd_signal_line = macd_data['signal'].iloc[-1]
        macd_prev = macd_data['macd'].iloc[-2]
        signal_prev = macd_data['signal'].iloc[-2]
        
        if macd_current > macd_signal_line:
            if macd_prev <= signal_prev:
                macd_status = "pozitif kesişim gerçekleşti"
                macd_implication = "Yükseliş momentumu başlıyor"
            else:
                macd_status = "pozitif bölgede"
                macd_implication = "Alıcılar kontrolde"
        else:
            if macd_prev >= signal_prev:
                macd_status = "negatif kesişim gerçekleşti"
                macd_implication = "Satış baskısı artıyor"
            else:
                macd_status = "negatif bölgede"
                macd_implication = "Satıcılar hakim"
    except:
        macd_status = "belirsiz"
        macd_implication = ""
    
    # Volume analizi
    vol_ratio = vol.get('volume_ratio', 1)
    if vol_ratio > 2:
        vol_status = "çok yüksek hacimle işlem görüyor"
        vol_implication = "Kurumsal ilgi var, hareket güvenilir"
    elif vol_ratio > 1.5:
        vol_status = "ortalamanın üzerinde hacim"
        vol_implication = "Hareket güç kazanıyor"
    elif vol_ratio > 1:
        vol_status = "normal hacimde"
        vol_implication = "Standart işlem aktivitesi"
    elif vol_ratio > 0.5:
        vol_status = "düşük hacimle işlem görüyor"
        vol_implication = "İlgi azalmış, dikkatli olun"
    else:
        vol_status = "çok düşük hacim"
        vol_implication = "Likidite riski var, sahte hareket olabilir"
    
    # Kritik seviyeler
    support = sr_levels['strong_support']
    resistance = sr_levels['strong_resistance']
    pivot = sr_levels.get('pivot', current_price)
    
    # Fiyat pozisyonu
    if current_price > resistance * 0.99:
        price_position = f"${resistance:,.0f} direncine yaklaşmış durumda"
        price_action = "Kırılım için hacim artışı gerekli"
    elif current_price < support * 1.01:
        price_position = f"${support:,.0f} desteğini test ediyor"
        price_action = "Burası tutmazsa düşüş hızlanabilir"
    elif abs(current_price - pivot) / pivot < 0.01:
        price_position = f"pivot noktası ${pivot:,.0f} civarında"
        price_action = "Yön belirleme aşamasında"
    else:
        if current_price > pivot:
            price_position = f"${support:,.0f} - ${resistance:,.0f} aralığının üst bölgesinde"
            price_action = "Direnç testine hazırlanıyor olabilir"
        else:
            price_position = f"${support:,.0f} - ${resistance:,.0f} aralığının alt bölgesinde"
            price_action = "Destek testi görebiliriz"
    
    # Risk durumu
    volatility = risk_metrics['volatility_pct']
    if volatility > 5:
        risk_assessment = f"Volatilite %{volatility:.1f} ile çok yüksek seviyelerde"
        risk_advice = "Küçük pozisyonlarla işlem yapın, stop-loss şart"
    elif volatility > 3:
        risk_assessment = f"Volatilite %{volatility:.1f} ile yüksek"
        risk_advice = "Normal risk yönetimi uygulayın"
    elif volatility > 2:
        risk_assessment = f"Volatilite %{volatility:.1f} ile orta seviyede"
        risk_advice = "Standart pozisyon boyutu uygun"
    else:
        risk_assessment = f"Volatilite %{volatility:.1f} ile düşük"
        risk_advice = "Sakin piyasa, büyük hareket beklemeyin"
    
    # Strateji önerisi
    if score >= 7:
        if current_price < resistance:
            strategy = f"${current_price:,.0f} - ${current_price * 0.99:,.0f} aralığından alım yapılabilir. İlk hedef ${resistance:,.0f}, aşılırsa ${resistance * 1.03:,.0f} ve ${resistance * 1.05:,.0f} hedeflenebilir. Stop-loss ${support:,.0f} altına konulmalı"
        else:
            strategy = f"Direnç kırılmış, geri test bekleyin. ${resistance:,.0f} üzerinde tutunursa ${current_price * 1.05:,.0f} hedeflenebilir. Stop ${resistance * 0.98:,.0f}"
    elif score >= 5.5:
        strategy = f"Kademeli alım stratejisi uygun. ${current_price * 0.99:,.0f} ve ${support:,.0f} seviyelerinden alım yapılabilir. Hedef ${resistance:,.0f}, stop ${support * 0.98:,.0f}"
    elif score >= 4.5:
        strategy = f"Beklemek en iyisi. ${resistance:,.0f} üstü alım, ${support:,.0f} altı satım sinyali olarak değerlendirilebilir. Mevcut aralıkta işlem yapmayın"
    elif score >= 3:
        strategy = f"Elinizde varsa ${resistance:,.0f} civarından çıkış düşünün. Short pozisyon için ${resistance:,.0f} direnci test edilebilir, hedef ${support:,.0f}, stop ${resistance * 1.02:,.0f}"
    else:
        if current_price > support:
            strategy = f"Satış baskısı güçlü. ${support:,.0f} kırılırsa ${support * 0.95:,.0f} ve ${support * 0.92:,.0f} hedeflenebilir. Alım için aceleci olmayın"
        else:
            strategy = f"Destek kırılmış, düşüş devam edebilir. Toparlanma için ${support:,.0f} üstüne çıkması gerekli. Risk almayın"
    
    # Timeframe önerisi
    if risk_metrics['volatility_pct'] > 4:
        timeframe_advice = "Yüksek volatilite nedeniyle kısa vadeli işlemler riskli. Orta-uzun vade düşünün"
    elif score >= 7 or score <= 3:
        timeframe_advice = "Güçlü sinyal var, kısa-orta vadeli pozisyon alınabilir"
    else:
        timeframe_advice = "Kararsız piyasa, günlük takip edin, büyük pozisyon almayın"
    
    # Final AI yorumu - profesyonel ve detaylı
    ai_text = f"""🤖 <b>AI ANALİZİ:</b>

"{trend.capitalize()} trendinde, RSI {rsi} seviyesinde {rsi_status}. {rsi_signal}. MACD {macd_status}, {macd_implication if macd_implication else 'trend devam ediyor'}. Fiyat {price_position}. {price_action}. 

{vol_status.capitalize()}, {vol_implication}. {risk_assessment}, {risk_advice}.

<b>Strateji:</b> {strategy}.

{timeframe_advice}. Momentum {momentum}, genel görünüm {outlook}."

<b>⚠️ Risk Notu:</b> Piyasa koşulları hızla değişebilir. Stop-loss kullanmayı unutmayın."""
    
    return ai_text
