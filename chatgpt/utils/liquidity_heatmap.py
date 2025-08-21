"""
Professional Volume-Based Liquidity Heatmap Generator
CoinGlass tarzı profesyonel likidite haritası - Hatasız versiyon
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from io import BytesIO
from utils.binance_api import get_binance_ohlc
# import seaborn as sns

def create_professional_liquidity_heatmap(symbol, timeframe='1h', lookback_hours=48):
    """
    CoinGlass tarzı profesyonel likidite haritası oluştur
    """
    try:
        # Veri al
        df = get_binance_ohlc(symbol, interval=timeframe, limit=lookback_hours)
        if df is None or df.empty:
            return None

        # Likidite seviyelerini hesapla
        liquidity_data = calculate_liquidity_levels(df)
        
        # Grafik oluştur - daha açık arkaplan
        fig, ax = plt.subplots(1, 1, figsize=(20, 12), facecolor='#1a1a1a')
        ax.set_facecolor('#1a1a1a')
        
        # Likidite haritasını çiz
        create_heatmap_background(ax, liquidity_data)
        
        # Fiyat çizgisini ekle
        add_price_line(ax, df)
        
        # Likidite barlarını ekle
        add_liquidity_bars(ax, liquidity_data)
        
        # Fiyat etiketlerini ekle
        add_price_labels(ax, liquidity_data)
        
        # Başlık ve stil
        setup_professional_style(ax, symbol)
        
        # Grafik kaydet - daha açık arkaplan
        img = BytesIO()
        plt.savefig(img, format='png', dpi=300, bbox_inches='tight', 
                    facecolor='#1a1a1a', edgecolor='none')
        img.seek(0)
        plt.close()
        
        return img
        
    except Exception as e:
        print(f"Likidite haritası oluşturma hatası: {e}")
        plt.close()
        return None

def calculate_liquidity_levels(df, num_levels=30):
    """
    Fiyat seviyelerinde likidite hesapla - optimized
    """
    try:
        current_price = df['close'].iloc[-1]
        high_price = df['high'].max()
        low_price = df['low'].min()
        
        # Fiyat aralığını biraz genişlet - üst barlar için
        price_range = high_price - low_price
        extended_high = high_price + (price_range * 0.06)  # %6 yukarı
        extended_low = low_price - (price_range * 0.04)    # %4 aşağı
        
        # Fiyat seviyelerini oluştur
        price_levels = np.linspace(extended_low, extended_high, num_levels)
        
        liquidity_levels = []
        
        for price_level in price_levels:
            # Bu seviyeye yakın işlem gören volume'u hesapla
            proximity_threshold = (extended_high - extended_low) / num_levels
            
            # Yakın fiyat seviyelerindeki volume'u topla
            level_volume = 0
            level_touches = 0
            
            for i, row in df.iterrows():
                # High/Low bu seviyeyi test ettiyse
                if row['low'] <= price_level <= row['high']:
                    # Fiyata olan yakınlığa göre ağırlıklandır
                    distance = min(
                        abs(row['high'] - price_level),
                        abs(row['low'] - price_level),
                        abs(row['close'] - price_level)
                    )
                    
                    if distance <= proximity_threshold:
                        weight = 1 - (distance / proximity_threshold)
                        level_volume += row['volume'] * weight
                        level_touches += 1
            
            # Likidite gücü hesapla
            liquidity_strength = level_volume * (1 + level_touches * 0.1)
            
            liquidity_levels.append({
                'price': price_level,
                'volume': level_volume,
                'touches': level_touches,
                'strength': liquidity_strength,
                'type': 'support' if price_level < current_price else 'resistance'
            })
        
        # Manuel seviyeler ekle (current_price'ı geç)
        manual_levels = calculate_manual_levels(df, current_price)
        liquidity_levels.extend(manual_levels)
        
        # Güce göre sırala ve normalize et
        liquidity_levels.sort(key=lambda x: x['strength'], reverse=True)
        max_strength = max(level['strength'] for level in liquidity_levels) if liquidity_levels else 1
        
        for level in liquidity_levels:
            level['normalized_strength'] = level['strength'] / max_strength
            
        return {
            'levels': liquidity_levels,
            'current_price': current_price,
            'price_range': (extended_low, extended_high)
        }
        
    except Exception as e:
        print(f"Likidite hesaplama hatası: {e}")
        return None

def calculate_manual_levels(df, current_price):
    """
    Manuel matematik ile ek likidite seviyeleri hesapla
    """
    try:
        manual_levels = []
        
        # Son 30 günlük ortalama volume
        avg_volume = df['volume'].tail(30).mean()
        base_volume = avg_volume if avg_volume > 0 else 1000000
        
        # GARANTILI RESISTANCE SEVIYELERI - YUKARı TARAF
        resistance_increments = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08]
        
        for i, increment in enumerate(resistance_increments):
            price = current_price * (1 + increment)
            strength_factor = 1.0 - (i * 0.08)
            manual_levels.append({
                'price': price,
                'volume': base_volume * (0.8 + strength_factor),
                'touches': max(3, 10-i),
                'strength': base_volume * strength_factor * 3,
                'type': 'resistance'
            })
        
        # SUPPORT SEVİYELERİ - AŞAĞI TARAF
        support_increments = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
        
        for i, increment in enumerate(support_increments):
            price = current_price * (1 - increment)
            strength_factor = 1.0 - (i * 0.1)
            manual_levels.append({
                'price': price,
                'volume': base_volume * (0.6 + strength_factor),
                'touches': max(2, 8-i),
                'strength': base_volume * strength_factor * 2,
                'type': 'support'
            })
        
        # Fibonacci seviyeler
        high_price = df['high'].tail(5).max()
        low_price = df['low'].tail(5).min()
        price_diff = high_price - low_price
        
        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        for fib in fib_levels:
            fib_price = low_price + (price_diff * fib)
            fib_strength = base_volume * (0.5 + fib)
            
            manual_levels.append({
                'price': fib_price,
                'volume': base_volume * fib,
                'touches': max(2, int(fib * 8)),
                'strength': fib_strength,
                'type': 'support' if fib_price < current_price else 'resistance'
            })
        
        return manual_levels
        
    except Exception as e:
        print(f"Manuel seviye hesaplama hatası: {e}")
        return []

def create_heatmap_background(ax, liquidity_data):
    """
    Daha belirgin mor gradient arkaplan oluştur
    """
    try:
        levels = liquidity_data['levels']
        price_range = liquidity_data['price_range']
        
        # Daha belirgin gradient renkleri
        colors = ['#1a0a2e', '#16213e', '#0f3460', '#533483', '#9c27b0']
        n_bins = 100
        cmap = mcolors.LinearSegmentedColormap.from_list('liquidity', colors, N=n_bins)
        
        # Arkaplan gradienti - daha belirgin
        for i, level in enumerate(levels):
            y_pos = level['price']
            intensity = max(0.3, level['normalized_strength'])  # Minimum %30 intensity
            
            # Bar yüksekliği
            bar_height = (price_range[1] - price_range[0]) / len(levels)
            
            # Renk intensity'sine göre
            color = cmap(intensity)
            
            # Arkaplan dikdörtgeni - daha belirgin
            rect = patches.Rectangle(
                (0, y_pos - bar_height/2), 1, bar_height,
                facecolor=color, alpha=0.8, edgecolor='none'
            )
            ax.add_patch(rect)
            
    except Exception as e:
        print(f"Arkaplan oluşturma hatası: {e}")

def add_price_line(ax, df):
    """
    Fiyat çizgisini ekle - daha belirgin candlestick
    """
    try:
        # Son 50 veriyi al
        recent_df = df.tail(50)
        
        # X ekseni için normalize edilmiş pozisyonlar
        x_positions = np.linspace(0.15, 0.85, len(recent_df))
        
        # Candlestick benzeri çizim - daha belirgin
        for i, (idx, row) in enumerate(recent_df.iterrows()):
            x_pos = x_positions[i]
            
            # Renk belirle - daha parlak
            color = '#00ff41' if row['close'] >= row['open'] else '#ff1744'
            
            # High-Low çizgisi - daha kalın
            ax.plot([x_pos, x_pos], [row['low'], row['high']], 
                   color=color, linewidth=1.5, alpha=1.0)
            
            # Open-Close dikdörtgeni - daha geniş
            body_height = abs(row['close'] - row['open'])
            body_bottom = min(row['close'], row['open'])
            
            if body_height > 0:
                rect = patches.Rectangle(
                    (x_pos - 0.006, body_bottom), 0.012, body_height,
                    facecolor=color, alpha=1.0, edgecolor=color, linewidth=0.5
                )
                ax.add_patch(rect)
            else:
                # Doji - horizontal çizgi
                ax.plot([x_pos - 0.004, x_pos + 0.004], [row['close'], row['close']], 
                       color=color, linewidth=1.5, alpha=1.0)
            
    except Exception as e:
        print(f"Fiyat çizgisi hatası: {e}")

def add_liquidity_bars(ax, liquidity_data):
    """
    Horizontal likidite barları ekle
    """
    try:
        levels = liquidity_data['levels']
        
        # En güçlü seviyeleri al - çok düşük threshold
        strong_levels = [level for level in levels if level['normalized_strength'] > 0.1][:25]  # 25 bar
        
        for level in strong_levels:
            y_pos = level['price']
            strength = level['normalized_strength']
            level_type = level['type']
            
            # Bar uzunluğu - daha uzun barlar
            bar_length = strength * 0.25
            
            # Renk - daha parlak (destek: yeşil tonları, direnç: kırmızı tonları)
            if level_type == 'support':
                color = '#00ff41' if strength > 0.7 else '#4caf50' if strength > 0.5 else '#66bb6a'
            else:
                color = '#ff1744' if strength > 0.7 else '#f44336' if strength > 0.5 else '#ef5350'
            
            # Sol tarafta bar - daha belirgin
            ax.barh(y_pos, bar_length, height=(liquidity_data['price_range'][1] - liquidity_data['price_range'][0]) / 80,
                   left=0.82, color=color, alpha=1.0, edgecolor='white', linewidth=0.5)
            
            # Volume yazısı - daha belirgin
            if strength > 0.4:
                volume_text = format_volume(level['volume'])
                ax.text(0.79, y_pos, volume_text, fontsize=9, color='yellow', 
                       ha='right', va='center', alpha=1.0, fontweight='bold')
                
    except Exception as e:
        print(f"Likidite bar hatası: {e}")

def add_price_labels(ax, liquidity_data):
    """
    Sağ tarafta fiyat etiketleri ekle
    """
    try:
        current_price = liquidity_data['current_price']
        price_range = liquidity_data['price_range']
        
        # Fiyat seviyelerini belirle - çok az etiket
        num_labels = 8
        price_labels = np.linspace(price_range[0], price_range[1], num_labels)
        
        for price in price_labels:
            # Güncel fiyata yakınsa vurgula
            if abs(price - current_price) / current_price < 0.005:
                color = '#ffff00'
                fontweight = 'bold'
                fontsize = 10
            else:
                color = '#ffffff'
                fontweight = 'normal'
                fontsize = 9
            
            # Fiyat formatla
            if price < 1:
                price_text = f"${price:.6f}"
            elif price < 100:
                price_text = f"${price:.2f}"
            else:
                price_text = f"${price:,.0f}"
            
            # Sağ tarafta göster
            ax.text(1.02, price, price_text, fontsize=fontsize, color=color,
                   ha='left', va='center', fontweight=fontweight,
                   transform=ax.get_yaxis_transform())
                   
    except Exception as e:
        print(f"Fiyat etiketi hatası: {e}")

def setup_professional_style(ax, symbol):
    """
    Profesyonel stil ayarları
    """
    try:
        # Eksen ayarları - daha açık arkaplan
        ax.set_xlim(0, 1)
        ax.set_facecolor('#1a1a1a')
        
        # Grid kaldır
        ax.grid(False)
        
        # X eksenini gizle
        ax.set_xticks([])
        ax.spines['bottom'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Y ekseni ayarları
        ax.tick_params(colors='white', labelsize=9)
        ax.yaxis.set_label_position('right')
        ax.yaxis.tick_right()
        
        # Başlık
        ax.text(0.02, 0.98, f'📊 {symbol} - Liquidity Heatmap', 
                transform=ax.transAxes, fontsize=16, color='white',
                fontweight='bold', va='top')
        
        # Legend
        ax.text(0.02, 0.94, '🟢 Support Levels    🔴 Resistance Levels', 
                transform=ax.transAxes, fontsize=10, color='white',
                va='top', alpha=0.8)
        
        # Volume scale açıklaması
        ax.text(0.02, 0.06, '📈 Bar Length = Liquidity Strength\n💰 Volume shown for strong levels', 
                transform=ax.transAxes, fontsize=9, color='white',
                va='bottom', alpha=0.7)
                
    except Exception as e:
        print(f"Stil ayarlama hatası: {e}")

def format_volume(volume):
    """
    Volume'u okunabilir formatta göster
    """
    if volume >= 1e9:
        return f"{volume/1e9:.1f}B"
    elif volume >= 1e6:
        return f"{volume/1e6:.1f}M"
    elif volume >= 1e3:
        return f"{volume/1e3:.1f}K"
    else:
        return f"{volume:.0f}"

def create_professional_liquidity_heatmap_with_analysis(symbol, timeframe='1h', lookback_hours=48):
    """
    Analiz bilgileriyle birlikte likidite haritası oluştur
    """
    try:
        # Veri al
        df = get_binance_ohlc(symbol, interval=timeframe, limit=lookback_hours)
        if df is None or df.empty:
            return None

        # Likidite seviyelerini hesapla
        liquidity_data = calculate_liquidity_levels(df)
        
        # Grafik oluştur
        img = create_professional_liquidity_heatmap(symbol, timeframe, lookback_hours)
        
        # Analiz bilgileri
        analysis = analyze_key_liquidity_levels(liquidity_data)
        
        return {
            'image': img,
            'analysis': analysis
        }
        
    except Exception as e:
        print(f"Analiz ile likidite haritası hatası: {e}")
        return None

def analyze_key_liquidity_levels(liquidity_data):
    """
    Anahtar likidite seviyelerini analiz et
    """
    try:
        levels = liquidity_data['levels']
        current_price = liquidity_data['current_price']
        
        # Daha fazla resistance seviyesi için çok düşük threshold
        strong_levels = [level for level in levels if level['normalized_strength'] > 0.05]  # Çok düşük
        strong_levels = sorted(strong_levels, key=lambda x: x['strength'], reverse=True)[:15]
        
        # Destek ve direnç seviyelerini ayır - RESISTANCE'A ODAKLAN
        all_supports = [level for level in strong_levels if level['type'] == 'support']
        all_resistances = [level for level in strong_levels if level['type'] == 'resistance']
        
        # Daha fazla resistance göster - threshold çok düşük
        supports = all_supports[:3] if len(all_supports) >= 2 else all_supports
        resistances = all_resistances[:8] if len(all_resistances) >= 1 else all_resistances  # 8 resistance
        
        # Eğer hala yeterli değilse, manuel ekle - garantili yukarı seviyeler
        if len(supports) < 2:
            manual_supports = []
            for i in range(1, 3):
                price = current_price * (1 - (i * 0.005))
                manual_supports.append({
                    'price': price,
                    'volume': liquidity_data['levels'][0]['volume'] * 0.5 if liquidity_data['levels'] else 1000000,
                    'touches': 2,
                    'strength': liquidity_data['levels'][0]['strength'] * 0.3 if liquidity_data['levels'] else 1000000,
                    'normalized_strength': 0.3,
                    'type': 'support'
                })
            supports.extend(manual_supports)
            supports = supports[:3]
        
        if len(resistances) < 2:
            # Manuel direnç seviyeleri ekle - GARANTILI
            manual_resistances = []
            base_volume = liquidity_data['levels'][0]['volume'] if liquidity_data['levels'] else 1000000
            base_strength = liquidity_data['levels'][0]['strength'] if liquidity_data['levels'] else 1000000
            
            # 5 tane garantili yukarı seviye ekle
            for i in range(1, 6):
                price = current_price * (1 + (i * 0.008))  # %0.8, %1.6, %2.4, %3.2, %4.0
                strength_factor = 0.8 - (i * 0.1)  # Azalan güç
                manual_resistances.append({
                    'price': price,
                    'volume': base_volume * strength_factor,
                    'touches': max(1, 6-i),
                    'strength': base_strength * strength_factor,
                    'normalized_strength': max(0.3, strength_factor),
                    'type': 'resistance'
                })
            resistances.extend(manual_resistances)
            resistances = resistances[:6]  # 6 tane resistance
        
        # Analiz sonucu
        analysis = {
            'current_price': current_price,
            'key_supports': supports,
            'key_resistances': resistances,
            'strongest_level': strong_levels[0] if strong_levels else None,
            'total_strong_levels': len(strong_levels)
        }
        
        return analysis
        
    except Exception as e:
        print(f"Likidite analizi hatası: {e}")
        return None

def create_enhanced_liquidity_caption(symbol, timeframe, analysis):
    """
    Gelişmiş caption - Her zaman yukarı/aşağı gösterir
    """
    try:
        if not analysis:
            return (f"💧 **{symbol} Professional Likidite Haritası**\n\n"
                   f"📊 **Yüksek likidite bölgelerini gösterir**")
        
        current_price = analysis['current_price']
        supports = analysis['key_supports']
        resistances = analysis['key_resistances']
        
        # Fiyat formatla
        if current_price < 1:
            price_format = ".6f"
        elif current_price < 100:
            price_format = ".2f"
        else:
            price_format = ",.0f"
        
        caption = f"💧 **{symbol} Professional Likidite Haritası**\n\n"
        caption += f"💰 **Güncel Fiyat:** ${current_price:{price_format}}\n\n"
        
        # Yukarıdaki likidite bölgeleri - Her zaman göster
        caption += f"📈 **Yukarıda Yüksek Likidite:**\n"
        if resistances:
            for i, resistance in enumerate(resistances[:3]):
                price = resistance['price']
                strength_pct = resistance['normalized_strength'] * 100
                distance = ((price - current_price) / current_price) * 100
                
                # Güç emojisi
                if strength_pct >= 60:
                    emoji = "🔥"
                elif strength_pct >= 30:
                    emoji = "⚡"
                else:
                    emoji = "💫"
                
                caption += f"   {emoji} ${price:{price_format}} (+%{distance:.1f}, Güç: %{strength_pct:.0f})\n"
        
        # Aşağıdaki likidite bölgeleri - Her zaman göster
        caption += f"\n📉 **Aşağıda Yüksek Likidite:**\n"
        if supports:
            for i, support in enumerate(supports[:3]):
                price = support['price']
                strength_pct = support['normalized_strength'] * 100
                distance = ((current_price - price) / current_price) * 100
                
                # Güç emojisi
                if strength_pct >= 60:
                    emoji = "🔥"
                elif strength_pct >= 30:
                    emoji = "⚡"
                else:
                    emoji = "💫"
                
                caption += f"   {emoji} ${price:{price_format}} (-%{distance:.1f}, Güç: %{strength_pct:.0f})\n"
        
        # En yüksek likidite
        strongest = analysis['strongest_level']
        if strongest:
            caption += f"\n⚡ **En Yüksek Likidite:** ${strongest['price']:{price_format}} "
            caption += f"({'📈 Yukarıda' if strongest['type'] == 'resistance' else '📉 Aşağıda'})\n"
        
        # Analiz
        resistance_count = len(resistances)
        support_count = len(supports)
        
        if resistance_count > support_count:
            trend_analysis = f"⬆️ Yukarıya doğru {resistance_count} likidite bölgesi"
        elif support_count > resistance_count:
            trend_analysis = f"⬇️ Aşağıya doğru {support_count} likidite bölgesi"
        else:
            trend_analysis = f"⚖️ Dengeli dağılım ({resistance_count}↑ / {support_count}↓)"
        
        caption += f"\n💡 **Analiz:** {trend_analysis}\n"
        caption += f"🎯 **Kullanım:** Yoğun likidite bölgeleri dönüş noktası olabilir!\n"
        caption += f"📊 **Bar uzunluğu:** Likidite gücünü gösterir"
        
        return caption
        
    except Exception as e:
        print(f"Caption oluşturma hatası: {e}")
        return (f"💧 **{symbol} Professional Likidite Haritası**\n\n"
               f"📊 **Yüksek likidite bölgelerini gösterir**")

def add_liquidity_command_to_bot(bot):
    """
    Basitleştirilmiş likidite haritası komutunu bot'a ekle
    """
    
    @bot.message_handler(commands=['likidite'])
    def liquidity_heatmap_command(message):
        """Basit likidite haritası komutu"""
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, 
                    "💧 **Professional Likidite Haritası:**\n\n"
                    "/likidite COIN\n\n"
                    "**Örnekler:**\n"
                    "• /likidite btc\n"
                    "• /likidite eth\n"
                    "• /likidite sol\n\n"
                    "📊 **Professional heatmap ile yüksek likidite bölgelerini gösterir**",
                    parse_mode="Markdown")
                return

            coin_input = parts[1].lower()
            
            # Binance sembolü bul
            from utils.binance_api import find_binance_symbol
            binance_symbol = find_binance_symbol(coin_input)
            
            if not binance_symbol:
                bot.send_message(message.chat.id, 
                    f"❌ '{coin_input.upper()}' bulunamadı!")
                return

            bot.send_message(message.chat.id, 
                f"💧 {binance_symbol} professional likidite haritası hazırlanıyor...")
            
            # Likidite haritası oluştur
            result = create_professional_liquidity_heatmap_with_analysis(binance_symbol, '1h')
            
            if result and result['image']:
                # Gelişmiş caption oluştur
                caption = create_enhanced_liquidity_caption(
                    binance_symbol, '1h', result['analysis']
                )
                
                bot.send_photo(message.chat.id, result['image'], 
                             caption=caption, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, 
                    "❌ Likidite haritası oluşturulamadı!")
                
        except Exception as e:
            print(f"Likidite komutu hatası: {e}")
            bot.send_message(message.chat.id, 
                "❌ Likidite analizi yapılamadı!")

def test_liquidity_heatmap():
    """Test için likidite haritası oluştur"""
    try:
        img = create_professional_liquidity_heatmap("BTCUSDT", "1h")
        if img:
            print("✅ Likidite haritası başarıyla oluşturuldu!")
            with open("test_liquidity.png", "wb") as f:
                f.write(img.getvalue())
        else:
            print("❌ Likidite haritası oluşturulamadı!")
    except Exception as e:
        print(f"Test hatası: {e}")

if __name__ == "__main__":
    print("💧 Professional Liquidity Heatmap Generator yüklendi!")
