"""
/analiz komutu (grup uyumlu, @mention destekli)
- Binance OHLC
- Teknik indikatörler
- Ultra modern grafikler
- Destek/direnç: Fibonacci tabanlı
- AI tahminleri ve gelişmiş analiz
"""

from __future__ import annotations
from telebot import types
import pandas as pd

try:
    from config import SIMPLE_TEXT_LEVEL_OFFSET
except Exception:
    SIMPLE_TEXT_LEVEL_OFFSET = 0.003

from utils.binance_api import find_binance_symbol, get_binance_ohlc
from utils.modern_charts import create_ultra_modern_chart  # YENİ MODERN GRAFİK
from utils.technical_analysis import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands,
    calculate_sma, calculate_ema, calculate_volume_analysis, generate_trading_signals
)

# ---------- yardımcılar ----------
def _split_command(text: str):
    parts = (text or "").strip().split()
    if not parts:
        return []
    parts[0] = parts[0].split("@")[0]  # /analiz@BotAdi -> /analiz
    return parts

def _fmt_price(v: float) -> str:
    try:
        if v < 0.01: return f"${v:.8f}"
        if v < 1:    return f"${v:.6f}"
        return f"${v:,.2f}"
    except Exception:
        return str(v)

def _overall_score(rsi: float, macd_data, current_price: float, sma_20: float) -> float:
    score = 5.0
    if rsi < 30: score += 2
    elif rsi > 70: score -= 2
    try:
        if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1]: score += 1.5
        else: score -= 1.5
    except Exception:
        pass
    if current_price > sma_20: score += 1
    else: score -= 1
    return max(0.0, min(10.0, score))

def _calc_fibs(h: float, l: float) -> dict[str, float]:
    diff = max(h - l, 0.0)
    return {
        '0%': h, '23.6%': h - diff*0.236, '38.2%': h - diff*0.382,
        '50%': h - diff*0.5, '61.8%': h - diff*0.618, '100%': l
    }

def _nearest_fibs_around_price(cur: float, fibs: dict[str, float]):
    below = [(k,v) for k,v in fibs.items() if v <= cur]
    above = [(k,v) for k,v in fibs.items() if v >= cur]
    sup = max(below, key=lambda x: x[1]) if below else None
    res = min(above, key=lambda x: x[1]) if above else None
    return sup, res

def _pick_fib_levels_by_timeframe(tf: str, cur: float, fibs: dict[str,float]):
    sup, res = _nearest_fibs_around_price(cur, fibs)
    target = "23.6%" if tf in ("1h","4h") else ("38.2%" if tf=="1d" else None)
    if target:
        tv = fibs.get(target)
        if tv is None: return sup, res
        lows = [(k,v) for k,v in fibs.items() if v <= tv]
        highs= [(k,v) for k,v in fibs.items() if v >= tv]
        sup2 = max(lows, key=lambda x:x[1]) if lows else None
        res2 = min(highs,key=lambda x:x[1]) if highs else None
        return (sup or sup2), (res or res2)
    return sup, res

def _adjust_levels_for_text(cur: float, s_raw: float|None, r_raw: float|None, off: float):
    s_adj, r_adj = s_raw, r_raw
    if r_raw is not None:
        try_val = r_raw * (1 - abs(off))
        r_adj = try_val if try_val > cur else r_raw
    if s_raw is not None:
        try_val = s_raw * (1 + abs(off))
        s_adj = try_val if try_val < cur else s_raw
    return s_adj, r_adj

def _build_simple_paragraph(cur: float, s_pair, r_pair, off: float) -> str:
    base = ("📊 <b>Basitçe ne demek istiyorum?</b>\n"
            "Mevcut seviyelerde fiyat yatay/kararsız bölgede. Net bir kırılım gelmeden büyük pozisyon almak riskli olabilir. ")
    s_adj = r_adj = None
    if s_pair or r_pair:
        s_raw = s_pair[1] if s_pair else None
        r_raw = r_pair[1] if r_pair else None
        s_adj, r_adj = _adjust_levels_for_text(cur, s_raw, r_raw, off)

    if (r_adj is not None) and (s_adj is not None):
        return (base +
                f"<b>{_fmt_price(r_adj)}</b> üzerinde hacimli bir kırılım olursa yükseliş hızlanabilir, "
                f"<b>{_fmt_price(s_adj)}</b> altına inilirse düşüş derinleşebilir. "
                "Kısa vadeli al-sat düşünenler küçük hacimle deneme yapabilir; orta-uzun vade düşünenler net sinyali bekleyebilir. "
                "Her durumda risk yönetimi (stop-loss) ve kademeli işlem önerilir.")
    if r_adj is not None:
        return (base +
                f"Üst tarafta <b>{_fmt_price(r_adj)}</b> bölgesi önemli. "
                "Bu seviyenin üzerinde kapanışlar gelirse momentum güçlenebilir; gelmezse dalgalanma devam edebilir. "
                "Kademeli ilerlemek ve stop belirlemek faydalı olur.")
    if s_adj is not None:
        return (base +
                f"Alt tarafta <b>{_fmt_price(s_adj)}</b> kritik destek. "
                "Bu seviyenin altında kalıcılık olursa satış baskısı artabilir; üstünde tutunursa toparlanma denenebilir. "
                "Kademeli ilerlemek ve stop belirlemek faydalı olur.")
    return base + "Belirgin seviye çıkarılamadı. Hacim artışı ve trend kırılımı görülene kadar temkinli kalmak mantıklı."

def _generate_ai_reason(score: float, rsi: float, macd_data, signals) -> str:
    """AI tahmin nedeni oluştur"""
    reasons = []
    
    if score >= 7:
        if rsi < 30:
            reasons.append("RSI aşırı satımda")
        if macd_data and macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1]:
            reasons.append("MACD pozitif kesişim")
        if signals:
            buy_count = len([s for s in signals if s.get('type') == 'BUY'])
            if buy_count > 2:
                reasons.append(f"{buy_count} güçlü alım sinyali")
    elif score <= 3:
        if rsi > 70:
            reasons.append("RSI aşırı alımda")
        if macd_data and macd_data['macd'].iloc[-1] < macd_data['signal'].iloc[-1]:
            reasons.append("MACD negatif kesişim")
        if signals:
            sell_count = len([s for s in signals if s.get('type') == 'SELL'])
            if sell_count > 2:
                reasons.append(f"{sell_count} satış sinyali")
    else:
        reasons.append("Kararsız piyasa koşulları")
        reasons.append("Net sinyal yok")
    
    return ", ".join(reasons) if reasons else "Teknik göstergeler analiz ediliyor"

# ---------- komut kayıt ----------
def register_analysis_commands(bot):

    @bot.message_handler(commands=['analiz'])
    def analiz_cmd(message):
        parts = _split_command(message.text)
        if len(parts) < 2:
            # Hızlı butonlar ekleyelim
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("₿ BTC", callback_data="quick_btc"),
                types.InlineKeyboardButton("Ξ ETH", callback_data="quick_eth"),
                types.InlineKeyboardButton("◎ SOL", callback_data="quick_sol")
            )
            
            bot.send_message(
                message.chat.id,
                "📊 <b>Kripto Analiz - Ultra Modern Grafikler</b>\n\n"
                "🔹 <b>Kullanım:</b> /analiz COIN\n\n"
                "Örnekler:\n"
                "• /analiz btc\n• /analiz eth\n• /analiz sol\n\n"
                "🚀 Hızlı seçim için butonları kullanın:\n\n"
                "📈 <b>Yenilikler:</b>\n"
                "• TradingView tarzı grafikler\n"
                "• AI tahmin sistemi\n"
                "• Güç göstergesi\n"
                "• Trend analizi",
                parse_mode="HTML",
                reply_markup=markup
            ); return

        coin_input = parts[1].lower()
        symbol = find_binance_symbol(coin_input)
        if not symbol:
            bot.send_message(
                message.chat.id,
                f"❌ <b>'{coin_input.upper()}' Binance'da bulunamadı!</b>\n\n"
                "💡 <b>Popüler:</b> BTC, ETH, SOL, DOGE, ADA",
                parse_mode="HTML"
            ); return

        show_timeframe_menu(bot, message.chat.id, coin_input, symbol)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("quick_"))
    def on_quick_select(call):
        coin_input = call.data.replace("quick_", "")
        symbol = find_binance_symbol(coin_input)
        if symbol:
            bot.answer_callback_query(call.id, f"✅ {coin_input.upper()} seçildi")
            show_timeframe_menu(bot, call.message.chat.id, coin_input, symbol)
        else:
            bot.answer_callback_query(call.id, "❌ Coin bulunamadı")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("tf_"))
    def on_tf(call):
        try:
            _, tf, coin_input = call.data.split("_", 2)
        except Exception:
            bot.answer_callback_query(call.id, "⚠️ Geçersiz seçim"); return

        symbol = find_binance_symbol(coin_input)
        if not symbol:
            bot.answer_callback_query(call.id, "⚠️ Coin bulunamadı"); return

        names = {"1h":"1 Saat","4h":"4 Saat","1d":"1 Gün","1w":"1 Hafta"}
        tf_name = names.get(tf, tf)
        bot.answer_callback_query(call.id, f"🎯 {tf_name} analiz başlıyor...")

        try:
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception: pass

            # Yükleniyor mesajı - daha güzel
            loading_msg = bot.send_message(
                call.message.chat.id,
                f"⏳ <b>{symbol} - {tf_name} Ultra Analiz</b>\n\n"
                "🎨 Modern grafik oluşturuluyor...\n"
                "📊 Teknik indikatörler hesaplanıyor...\n"
                "🤖 AI tahmin yapılıyor...\n\n"
                "⚡ <i>Bu işlem 5-10 saniye sürebilir.</i>",
                parse_mode="HTML"
            )
            
            _perform_analysis(bot, call.message.chat.id, symbol, coin_input, tf, tf_name)
            
            # Yükleniyor mesajını sil
            try: bot.delete_message(call.message.chat.id, loading_msg.message_id)
            except: pass
            
        except Exception as e:
            print(f"/analiz error: {e}")
            bot.send_message(call.message.chat.id, "❌ Analiz tamamlanamadı!")

def show_timeframe_menu(bot, chat_id, coin_input, symbol):
    """Timeframe seçim menüsü"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Timeframe butonları - emoji ekledik
    buttons = [
        ("⚡ 1 Saat", f"tf_1h_{coin_input}"),
        ("📊 4 Saat", f"tf_4h_{coin_input}"),
        ("📈 1 Gün", f"tf_1d_{coin_input}"),
        ("📅 1 Hafta", f"tf_1w_{coin_input}")
    ]
    
    for text, callback in buttons:
        markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    
    coin_name = symbol.replace('USDT','').upper()
    bot.send_message(
        chat_id,
        f"🎯 <b>{coin_name} Analizi</b>\n\n"
        f"⏰ <b>Hangi sürede analiz yapalım?</b>\n\n"
        f"💡 <i>Kısa vadeli: 1H/4H</i>\n"
        f"💡 <i>Uzun vadeli: 1D/1W</i>",
        reply_markup=markup, 
        parse_mode="HTML"
    )

# ---------- analiz motoru ----------
def _perform_analysis(bot, chat_id: int, symbol: str, coin_input: str, timeframe: str, tf_name: str):
    limit_map = {'1h':168, '4h':168, '1d':100, '1w':52}
    limit = limit_map.get(timeframe, 100)
    df: pd.DataFrame|None = get_binance_ohlc(symbol, interval=timeframe, limit=limit)
    if df is None or df.empty:
        bot.send_message(chat_id, f"❌ {symbol} veri alınamadı!"); return

    cur = float(df['close'].iloc[-1])
    prev = float(df['close'].iloc[-2]) if len(df)>1 else cur
    chg = ((cur - prev)/prev)*100 if prev else 0.0

    # Teknik indikatörler
    rsi = float(calculate_rsi(df['close']).iloc[-1])
    macd = calculate_macd(df['close'])
    bb = calculate_bollinger_bands(df['close'])
    sma20 = float(calculate_sma(df['close'],20).iloc[-1])
    sma50 = float(calculate_sma(df['close'],50).iloc[-1]) if len(df)>50 else 0.0
    vol = calculate_volume_analysis(df)
    signals = generate_trading_signals(df)

    # Fibonacci ve skor hesaplama
    hi = float(df['high'].tail(50).max()); lo = float(df['low'].tail(50).min())
    fibs = _calc_fibs(hi, lo)
    score = _overall_score(rsi, macd, cur, sma20)
    
    # Volatilite hesapla
    volatility = ((df['high'].max() - df['low'].min()) / df['close'].mean()) * 100 if df['close'].mean() > 0 else 0

    # AI tahmin nedeni
    ai_reason = _generate_ai_reason(score, rsi, macd, signals)

    # ULTRA MODERN GRAFİK İÇİN VERİ HAZIRLAMA
    analysis_full = {
        'price': cur,
        'rsi': rsi,
        'macd_data': macd,
        'bb_data': bb,
        'signals': signals,
        'overall_score': score,
        'fib_levels': fibs,
        'change_24h': chg,
        'volume_ratio': vol.get('volume_ratio', 1),
        'volatility': volatility,
        'trend_score': score,
        'price_history': df['close'].tolist(),
        'ai_reason': ai_reason,
        'volume_analysis': vol.get('volume_analysis', 'Normal')
    }
    
    # ULTRA MODERN GRAFİK OLUŞTUR
    try:
        chart_img = create_ultra_modern_chart(df, symbol, analysis_full, timeframe)
        if chart_img:
            # Grafik gönder - daha zengin caption
            caption = (
                f"🎨 <b>{symbol} - {tf_name} Ultra Analiz</b>\n\n"
                f"💎 <b>Fiyat:</b> {_fmt_price(cur)} ({change_emoji(chg)} %{chg:+.2f})\n"
                f"📊 <b>RSI:</b> {int(rsi)} {rsi_emoji(rsi)}\n"
                f"📈 <b>Trend:</b> {trend_text(score)}\n"
                f"🤖 <b>AI Tahmin:</b> {ai_prediction(score)}\n\n"
                f"<i>TradingView tarzı profesyonel grafik</i>"
            )
            bot.send_photo(chat_id, chart_img, caption=caption, parse_mode="HTML")
    except Exception as e:
        print(f"chart error: {e}")

    # DETAYLI ANALİZ METNİ
    price_str = _fmt_price(cur)
    change_emoji_val = change_emoji(chg)
    
    text = (
        f"📊 <b>{coin_input.upper()} - {tf_name} Detaylı Analiz</b>\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>GÜNCEL DURUM</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"• Fiyat: {price_str}\n"
        f"• Değişim: {change_emoji_val} %{chg:+.2f}\n"
        f"• RSI: {int(rsi)} {rsi_emoji(rsi)}\n"
        f"• Hacim: {vol.get('volume_analysis','—')}\n"
        f"• Volatilite: %{volatility:.1f}\n\n"
    )

    # AI ANALİZİ - GELİŞTİRİLMİŞ
    try:
        m = macd['macd'].iloc[-1]; ms = macd['signal'].iloc[-1]
        bu = bb['upper'].iloc[-1]; bl = bb['lower'].iloc[-1]
        
        text += "━━━━━━━━━━━━━━━━━\n"
        text += "🤖 <b>AI ANALİZİ</b>\n"
        text += "━━━━━━━━━━━━━━━━━\n"
        
        ai_points = []
        
        # RSI analizi
        if rsi < 30:
            ai_points.append("• ✅ RSI aşırı satımda, tepki potansiyeli yüksek")
        elif rsi > 70:
            ai_points.append("• ⚠️ RSI aşırı alımda, düzeltme gelebilir")
        else:
            ai_points.append("• ⚖️ RSI nötr bölgede, momentum dengeli")
        
        # MACD analizi
        if m > ms:
            ai_points.append("• ✅ MACD pozitif, yükseliş momentumu güçlü")
        else:
            ai_points.append("• ⚠️ MACD negatif, satış baskısı devam edebilir")
        
        # Bollinger analizi
        if cur > bu:
            ai_points.append("• 🔥 Üst bandı aşmış, güçlü rally")
        elif cur < bl:
            ai_points.append("• 💎 Alt banda dokunuş, alım fırsatı olabilir")
        
        # Hacim analizi
        vr = vol.get('volume_ratio', 1)
        if vr > 1.5:
            ai_points.append("• 📊 Hacim ortalamanın üzerinde, hareket güvenilir")
        elif vr < 0.5:
            ai_points.append("• 📉 Hacim zayıf, dikkatli olun")
        
        text += "\n".join(ai_points) + "\n\n"
        
    except Exception as e:
        print(f"ai analysis error: {e}")

    # FİBONACCİ SEVİYELERİ
    sup_pair, res_pair = _pick_fib_levels_by_timeframe(timeframe, cur, fibs)

    text += "━━━━━━━━━━━━━━━━━\n"
    text += "📏 <b>KRİTİK SEVİYELER</b>\n"
    text += "━━━━━━━━━━━━━━━━━\n"
    
    if res_pair:
        text += f"🔴 Direnç: {_fmt_price(res_pair[1])} ({res_pair[0]})\n"
    text += f"💎 Mevcut: {_fmt_price(cur)}\n"
    if sup_pair:
        text += f"🟢 Destek: {_fmt_price(sup_pair[1])} ({sup_pair[0]})\n"

    # BASİTÇE AÇIKLAMA
    text += "\n" + _build_simple_paragraph(cur, sup_pair, res_pair, SIMPLE_TEXT_LEVEL_OFFSET) + "\n\n"

    # AKTİF SİNYALLER - GELİŞTİRİLMİŞ
    if signals:
        buys = [s for s in signals if s.get('type')=='BUY']
        sells= [s for s in signals if s.get('type')=='SELL']
        
        if buys or sells:
            text += "━━━━━━━━━━━━━━━━━\n"
            text += "⚡ <b>AKTİF SİNYALLER</b>\n"
            text += "━━━━━━━━━━━━━━━━━\n"
            
            if buys:
                text += "🟢 <b>ALIM SİNYALLERİ:</b>\n"
                for s in buys[:3]:
                    strength = s.get('strength', '')
                    emoji = "🔥" if 'Güçlü' in str(strength) else "⚡"
                    text += f"  {emoji} {s.get('reason','')}\n"
                text += "\n"
            
            if sells:
                text += "🔴 <b>SATIM SİNYALLERİ:</b>\n"
                for s in sells[:3]:
                    strength = s.get('strength', '')
                    emoji = "⚠️" if 'Güçlü' in str(strength) else "📉"
                    text += f"  {emoji} {s.get('reason','')}\n"
                text += "\n"

    # GENEL ÖNERİ - DAHA DETAYLI
    text += "━━━━━━━━━━━━━━━━━\n"
    text += "🎯 <b>GENEL ÖNERİ</b>\n"
    text += "━━━━━━━━━━━━━━━━━\n"
    
    if score >= 7:
        text += "✅ <b>GÜÇLÜ ALIM</b>\n"
        text += "Pozitif momentum güçlü, alım yapılabilir.\n"
        text += f"• Hedef: {_fmt_price(res_pair[1] if res_pair else cur * 1.05)}\n"
        text += f"• Stop: {_fmt_price(sup_pair[1] if sup_pair else cur * 0.97)}\n"
    elif score >= 5:
        text += "⚖️ <b>BEKLE / İZLE</b>\n"
        text += "Piyasa kararsız, net sinyal bekleyin.\n"
        text += "• Alım sinyali: Direnç kırılımı\n"
        text += "• Satım sinyali: Destek kırılımı\n"
    else:
        text += "⚠️ <b>RİSKLİ / SAT</b>\n"
        text += "Satış baskısı var, pozisyon azaltın.\n"
        text += f"• Destek: {_fmt_price(sup_pair[1] if sup_pair else cur * 0.95)}\n"
        text += "• Toparlanma için hacim artışı gerekli\n"

    # FOOTER - BUTONLAR
    text += "\n━━━━━━━━━━━━━━━━━\n"
    text += "🔧 <b>DİĞER ARAÇLAR</b>\n"
    text += "━━━━━━━━━━━━━━━━━\n"
    text += f"⏰ /alarm {coin_input} - Fiyat alarmı\n"
    text += f"💧 /likidite {coin_input} - Likidite haritası\n"
    text += f"🐋 /whale - Balina takibi\n"
    text += f"💰 /flow - Para akışı\n\n"
    
    text += "⚠️ <i>Bu analiz yatırım tavsiyesi değildir! DYOR</i>"

    bot.send_message(chat_id, text, parse_mode="HTML")

# Yardımcı emoji fonksiyonları
def change_emoji(change: float) -> str:
    if change > 5: return "🚀"
    elif change > 0: return "📈"
    elif change > -5: return "📉"
    else: return "💀"

def rsi_emoji(rsi: float) -> str:
    if rsi < 30: return "🟢"
    elif rsi > 70: return "🔴"
    else: return "⚪"

def trend_text(score: float) -> str:
    if score >= 7: return "Güçlü Yükseliş 🔥"
    elif score >= 5: return "Yükseliş 📈"
    elif score >= 3: return "Yatay ➡️"
    else: return "Düşüş 📉"

def ai_prediction(score: float) -> str:
    if score >= 7: return "AL 🟢"
    elif score >= 4: return "BEKLE 🟡"
    else: return "SAT 🔴"
