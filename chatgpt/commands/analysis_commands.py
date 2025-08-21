"""
/analiz komutu (grup uyumlu, @mention destekli)
- Binance OHLC
- Teknik indikatörler
- Grafik
- Destek/direnç: Fibonacci tabanlı (1h/4h: 23.6, 1d: 38.2, 1w: en yakın üst/alt)
- "Basitçe" metni: seviyeleri küçük yakınlaştırma + akıllı kıskaç (destek < fiyat < direnç)
- Yüzdelik etiketler metinden kaldırıldı
"""

from __future__ import annotations
from telebot import types
import pandas as pd

try:
    from config import SIMPLE_TEXT_LEVEL_OFFSET
except Exception:
    SIMPLE_TEXT_LEVEL_OFFSET = 0.003

from utils.binance_api import find_binance_symbol, get_binance_ohlc
from utils.chart_generator import create_advanced_chart
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

# ---------- komut kayıt ----------
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
                "📈 Coin seçtikten sonra zaman dilimi seçin!",
                parse_mode="HTML"
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

        markup = types.InlineKeyboardMarkup(row_width=2)
        for key, label in (("1h","⚡ 1 Saat"), ("4h","📊 4 Saat"), ("1d","📈 1 Gün"), ("1w","📅 1 Hafta")):
            markup.add(types.InlineKeyboardButton(label, callback_data=f"tf_{key}_{coin_input}"))

        coin_name = symbol.replace('USDT','').upper()
        bot.send_message(
            message.chat.id,
            f"🎯 <b>{coin_name} Analizi</b>\n\n⏰ <b>Hangi sürede analiz yapalım?</b>",
            reply_markup=markup, parse_mode="HTML"
        )

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

            bot.send_message(
                call.message.chat.id,
                f"⏳ <b>{symbol} - {tf_name} Analiz</b>\n\n"
                "📊 Veriler alınıyor...\n📈 Grafik oluşturuluyor...\n\n"
                "⚡ Bu işlem 5-10 saniye sürebilir.",
                parse_mode="HTML"
            )
            _perform_analysis(bot, call.message.chat.id, symbol, coin_input, tf, tf_name)
        except Exception as e:
            print(f"/analiz error: {e}")
            bot.send_message(call.message.chat.id, "❌ Analiz tamamlanamadı!")

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

    rsi = float(calculate_rsi(df['close']).iloc[-1])
    macd = calculate_macd(df['close'])
    bb = calculate_bollinger_bands(df['close'])
    sma20 = float(calculate_sma(df['close'],20).iloc[-1])
    sma50 = float(calculate_sma(df['close'],50).iloc[-1]) if len(df)>50 else 0.0
    vol = calculate_volume_analysis(df)
    signals = generate_trading_signals(df)

    hi = float(df['high'].tail(50).max()); lo = float(df['low'].tail(50).min())
    fibs = _calc_fibs(hi, lo)

    score = _overall_score(rsi, macd, cur, sma20)

    try:
        chart_img = create_advanced_chart(df, symbol, {
            'price':cur,'rsi':rsi,'macd_data':macd,'bb_data':bb,
            'signals':signals,'overall_score':score,'fib_levels':fibs
        }, timeframe)
        if chart_img:
            bot.send_photo(chat_id, chart_img, caption=f"📊 <b>{symbol} - {tf_name} Teknik Grafik</b>", parse_mode="HTML")
    except Exception as e:
        print(f"chart error: {e}")

    price_str = _fmt_price(cur)
    change_emoji = "📈" if chg>0 else "📉"
    text = (
        f"📊 <b>{coin_input.upper()} - {tf_name} Analiz</b>\n\n"
        f"💰 <b>Güncel Fiyat:</b> {price_str}\n"
        f"{change_emoji} <b>Değişim:</b> %{chg:+.2f}\n"
        f"📈 <b>RSI:</b> {int(rsi)}\n"
        f"📊 <b>Hacim:</b> {vol.get('volume_analysis','—')}\n\n"
    )

    try:
        m = macd['macd'].iloc[-1]; ms = macd['signal'].iloc[-1]
        bu = bb['upper'].iloc[-1]; bl = bb['lower'].iloc[-1]
        ai = []
        ai.append("RSI aşırı satım, tepki gelebilir." if rsi<30 else ("RSI aşırı alım, kâr satışı riski." if rsi>70 else "RSI nötr, momentum dengeli."))
        ai.append("MACD pozitif kesişim, yükseliş momentumu." if m>ms else "MACD negatif, baskı sürebilir.")
        if cur>bu: ai.append("Üst banda taşmış, aşırı alım.")
        elif cur<bl: ai.append("Alt bantta, tepki olası.")
        vr = vol.get('volume_ratio',1)
        if vr>1.5: ai.append("Hacim ortalamanın üzerinde, hareket güçlü.")
        elif vr<0.5: ai.append("Hacim zayıf, temkinli olun.")
        text += "🤖 <b>AI ANALİZİ</b>\n" + " ".join(ai) + "\n\n"
    except Exception as e:
        print(f"ai summary error: {e}")

    sup_pair, res_pair = _pick_fib_levels_by_timeframe(timeframe, cur, fibs)

    def _pair_line(title, pair):
        if not pair: return ""
        return f"{title}: {_fmt_price(pair[1])}\n"

    text += "📏 <b>Fibonacci Seviyeleri (son 50 mum)</b>\n"
    text += _pair_line("🟢 Yakın Destek", sup_pair)
    text += _pair_line("🔴 Yakın Direnç", res_pair)

    text += "\n" + _build_simple_paragraph(cur, sup_pair, res_pair, SIMPLE_TEXT_LEVEL_OFFSET) + "\n"

    if signals:
        buys = [s for s in signals if s.get('type')=='BUY']
        sells= [s for s in signals if s.get('type')=='SELL']
        if buys or sells:
            text += "\n⚡ <b>AKTİF SİNYALLER</b>\n"
            if buys:
                text += "🟢 <b>ALIM:</b>\n" + "".join(f"• {s.get('reason','')} ({s.get('strength','')})\n" for s in buys[:2])
            if sells:
                text += "🔴 <b>SATIM:</b>\n" + "".join(f"• {s.get('reason','')} ({s.get('strength','')})\n" for s in sells[:2])

    if score >= 7: reco = "🟢 <b>AL</b> — Güçlü alım sinyalleri"
    elif score >= 5: reco = "🟡 <b>BEKLE</b> — Kararsız piyasa"
    else: reco = "🔴 <b>SAT</b> — Satış baskısı var"
    text += f"\n🎯 <b>ÖNERİ:</b> {reco}\n\n"

    text += f"🔧 ⏰ /alarm {coin_input}   |   💧 /likidite {coin_input}\n"
    text += "⚠️ <i>Bu analiz yatırım tavsiyesi değildir!</i>"

    bot.send_message(chat_id, text, parse_mode="HTML")
