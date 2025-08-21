"""
Enhanced TradingView Style Liquidity Heatmap
Detaylı likidite haritası ve analiz
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from io import BytesIO
import requests
from datetime import datetime
from utils.binance_api import get_binance_ohlc

# TradingView renk paleti
COLORS = {
    'bg': '#131722',           # TradingView arka plan
    'bg_secondary': '#1e222d',
    'grid': '#363a45',
    'text': '#b2b5be',
    'text_bright': '#e1e4ea',
    'green': '#26a69a',         # TradingView yeşil
    'red': '#ef5350',           # TradingView kırmızı
    'blue': '#2196f3',
    'yellow': '#ffeb3b',
    'purple': '#ab47bc',
    'orange': '#ff9800',
    'liquidity_high': '#2962ff',  # Yüksek likidite - mavi
    'liquidity_mid': '#00bcd4',   # Orta likidite - cyan
    'liquidity_low': '#1e88e5',   # Düşük likidite - açık mavi
}

class EnhancedLiquidityMap:
    def __init__(self):
        self.session = requests.Session()
        self.liquidity_analysis = {}
        
    def get_binance_depth(self, symbol="BTCUSDT", limit=1000):
        """Binance order book verisi - daha fazla veri"""
        try:
            url = f"https://api.binance.com/api/v3/depth"
            params = {"symbol": symbol, "limit": limit}
            response = self.session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'bids': [(float(price), float(qty)) for price, qty in data.get('bids', [])],
                    'asks': [(float(price), float(qty)) for price, qty in data.get('asks', [])]
                }
        except Exception as e:
            print(f"Depth error: {e}")
        return {'bids': [], 'asks': []}
    
    def get_current_price(self, symbol="BTCUSDT"):
        """Güncel fiyat"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price"
            response = self.session.get(url, params={"symbol": symbol}, timeout=5)
            if response.status_code == 200:
                return float(response.json()['price'])
        except:
            pass
        return None
    
    def calculate_liquidity_levels(self, depth, current_price, price_range_pct=0.05):
        """Geliştirilmiş likidite seviye hesaplama"""
        levels = []
        
        # Daha geniş fiyat aralığı (%5 yukarı/aşağı)
        price_range = current_price * price_range_pct
        min_price = current_price - price_range
        max_price = current_price + price_range
        
        # Daha fazla seviye (50 seviye)
        num_levels = 50
        price_levels = np.linspace(min_price, max_price, num_levels)
        
        # Her seviye için likidite hesapla
        for price_level in price_levels:
            bid_liquidity = 0
            ask_liquidity = 0
            
            # Yakınlık threshold'u
            threshold = price_range / num_levels * 1.5
            
            # Bid likiditesi
            for bid_price, bid_qty in depth['bids']:
                distance = abs(bid_price - price_level)
                if distance < threshold:
                    # Mesafeye göre ağırlıklandır
                    weight = 1 - (distance / threshold)
                    bid_liquidity += bid_qty * weight
            
            # Ask likiditesi
            for ask_price, ask_qty in depth['asks']:
                distance = abs(ask_price - price_level)
                if distance < threshold:
                    weight = 1 - (distance / threshold)
                    ask_liquidity += ask_qty * weight
            
            total_liquidity = bid_liquidity + ask_liquidity
            
            levels.append({
                'price': price_level,
                'liquidity': total_liquidity,
                'bid_liquidity': bid_liquidity,
                'ask_liquidity': ask_liquidity,
                'type': 'support' if price_level < current_price else 'resistance',
                'distance_pct': ((price_level - current_price) / current_price) * 100
            })
        
        # Likiditeye göre sırala
        levels = sorted(levels, key=lambda x: x['liquidity'], reverse=True)
        
        # En güçlü seviyeleri kaydet (analiz için)
        self.liquidity_analysis = {
            'above': [l for l in levels if l['price'] > current_price][:5],
            'below': [l for l in levels if l['price'] < current_price][:5],
            'strongest': levels[0] if levels else None,
            'current_price': current_price
        }
        
        return levels
    
    def get_analysis_text(self):
        """Likidite analiz metni oluştur"""
        if not self.liquidity_analysis:
            return ""
        
        analysis = self.liquidity_analysis
        current_price = analysis['current_price']
        
        # En yüksek likidite değeri (normalizasyon için)
        all_levels = analysis['above'] + analysis['below']
        if not all_levels:
            return ""
        
        max_liquidity = max(l['liquidity'] for l in all_levels)
        
        text = f"💧 **Likidite Analizi**\n\n"
        text += f"💰 **Güncel Fiyat:** ${current_price:,.2f}\n\n"
        
        # Yukarıdaki likidite
        text += "📈 **Yukarıda Yüksek Likidite:**\n"
        for level in analysis['above'][:3]:
            strength = (level['liquidity'] / max_liquidity) * 100
            emoji = "🔥" if strength >= 60 else "⚡" if strength >= 30 else "💫"
            text += f"   {emoji} ${level['price']:,.0f} (+%{abs(level['distance_pct']):.1f}, Güç: %{strength:.0f})\n"
        
        # Aşağıdaki likidite
        text += "\n📉 **Aşağıda Yüksek Likidite:**\n"
        for level in analysis['below'][:3]:
            strength = (level['liquidity'] / max_liquidity) * 100
            emoji = "🔥" if strength >= 60 else "⚡" if strength >= 30 else "💫"
            text += f"   {emoji} ${level['price']:,.0f} (-%{abs(level['distance_pct']):.1f}, Güç: %{strength:.0f})\n"
        
        # En yüksek likidite
        if analysis['strongest']:
            strongest = analysis['strongest']
            direction = "📈 Yukarıda" if strongest['price'] > current_price else "📉 Aşağıda"
            text += f"\n⚡ **En Yüksek Likidite:** ${strongest['price']:,.0f} ({direction})\n"
        
        return text

def create_ultra_modern_liquidity_heatmap(symbol="BTCUSDT", timeframe="1h"):
    """Geliştirilmiş TradingView tarzı likidite haritası"""
    try:
        # Veri hazırlık
        liq = EnhancedLiquidityMap()
        current_price = liq.get_current_price(symbol)
        
        if not current_price:
            return None, None
        
        # OHLC verisi - daha fazla bar
        df = get_binance_ohlc(symbol, interval=timeframe, limit=150)
        if df is None or df.empty:
            return None, None
        
        # Order book - maksimum derinlik
        depth = liq.get_binance_depth(symbol, 1000)
        
        # Likidite seviyeleri - %5 aralık
        liquidity_levels = liq.calculate_liquidity_levels(depth, current_price, 0.05)
        
        # Figure oluştur - TradingView tarzı
        fig = plt.figure(figsize=(18, 10), facecolor=COLORS['bg'])
        
        # Ana grafik
        ax = plt.subplot(111)
        ax.set_facecolor(COLORS['bg'])
        
        # 1. CANDLESTICK GRAFİK
        draw_candlestick_chart(ax, df)
        
        # 2. LİKİDİTE SEVİYELERİ (yatay çizgiler)
        draw_liquidity_levels(ax, liquidity_levels, current_price)
        
        # 3. VOLUME PROFILE (sağ taraf) - geliştirilmiş
        draw_enhanced_volume_profile(ax, df, depth, current_price)
        
        # 4. ORDER BOOK DUVAR GÖSTERGESİ
        draw_order_walls(ax, depth, current_price, len(df))
        
        # 5. MEVCUT FİYAT ÇİZGİSİ
        ax.axhline(y=current_price, color=COLORS['yellow'], 
                  linewidth=2.5, linestyle='-', alpha=1, zorder=10)
        
        # Mevcut fiyat etiketi
        ax.text(len(df) + 0.5, current_price, f'  ${current_price:,.2f}', 
               color=COLORS['yellow'], fontweight='bold', 
               fontsize=11, va='center',
               bbox=dict(boxstyle="round,pad=0.4", 
                        facecolor=COLORS['bg_secondary'], 
                        edgecolor=COLORS['yellow'], alpha=0.95))
        
        # Başlık
        ax.set_title(f'{symbol} - Enhanced Liquidity Map & Volume Profile', 
                    fontsize=15, color=COLORS['text_bright'], 
                    fontweight='bold', pad=20)
        
        # Y ekseni (fiyat)
        ax.set_ylabel('Price (USDT)', color=COLORS['text'], fontsize=12)
        ax.yaxis.set_label_position('right')
        ax.yaxis.tick_right()
        
        # Y ekseni formatı
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x:,.0f}' if x >= 1 else f'{x:.6f}'
        ))
        
        # X ekseni
        ax.set_xlabel('Time', color=COLORS['text'], fontsize=12)
        
        # Grid - TradingView tarzı
        ax.grid(True, color=COLORS['grid'], alpha=0.3, 
               linewidth=0.5, linestyle='-')
        
        # Eksenleri ayarla - daha geniş görünüm
        price_range = current_price * 0.05  # %5 aralık
        ax.set_ylim(current_price - price_range, current_price + price_range)
        ax.set_xlim(-5, len(df) + 15)
        
        # Tick renkleri
        ax.tick_params(colors=COLORS['text'], labelsize=10)
        
        # Kenarlıkları özelleştir
        for spine in ax.spines.values():
            spine.set_color(COLORS['grid'])
            spine.set_linewidth(0.5)
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=COLORS['liquidity_high'], alpha=0.4, label='High Liquidity Zone'),
            Patch(facecolor=COLORS['liquidity_mid'], alpha=0.3, label='Medium Liquidity'),
            Patch(facecolor=COLORS['green'], alpha=0.5, label='Buy Walls'),
            Patch(facecolor=COLORS['red'], alpha=0.5, label='Sell Walls')
        ]
        ax.legend(handles=legend_elements, loc='upper left', 
                 facecolor=COLORS['bg_secondary'], 
                 edgecolor=COLORS['grid'],
                 fontsize=10, framealpha=0.95)
        
        plt.tight_layout()
        
        # Grafik kaydet
        img = BytesIO()
        plt.savefig(img, format='png', dpi=120, 
                   bbox_inches='tight',
                   facecolor=COLORS['bg'], 
                   edgecolor='none')
        img.seek(0)
        plt.close()
        
        # Analiz metni
        analysis_text = liq.get_analysis_text()
        
        return img, analysis_text
        
    except Exception as e:
        print(f"Liquidity heatmap error: {e}")
        plt.close()
        return None, None

def draw_candlestick_chart(ax, df):
    """TradingView tarzı candlestick çiz"""
    for i in range(len(df)):
        row = df.iloc[i]
        
        # Renk belirleme
        if row['close'] >= row['open']:
            body_color = COLORS['green']
            wick_color = COLORS['green']
        else:
            body_color = COLORS['red']
            wick_color = COLORS['red']
        
        # Wick (high-low)
        ax.plot([i, i], [row['low'], row['high']], 
               color=wick_color, linewidth=1, alpha=0.7, zorder=1)
        
        # Body (open-close)
        height = abs(row['close'] - row['open'])
        bottom = min(row['close'], row['open'])
        
        # Body rectangle
        if height > 0:  # Doji değilse
            rect = Rectangle((i - 0.3, bottom), 0.6, height,
                           facecolor=body_color, 
                           edgecolor=body_color,
                           alpha=0.8, 
                           linewidth=0,
                           zorder=2)
            ax.add_patch(rect)

def draw_liquidity_levels(ax, levels, current_price):
    """Geliştirilmiş likidite seviyeleri"""
    
    # En yüksek likidite değeri
    max_liquidity = max(level['liquidity'] for level in levels) if levels else 1
    
    # Her seviye için çizgi çiz (daha fazla seviye)
    for level in levels[:30]:  # En önemli 30 seviye
        price = level['price']
        liquidity = level['liquidity']
        normalized = liquidity / max_liquidity
        
        # Likiditeye göre renk ve kalınlık
        if normalized > 0.7:
            color = COLORS['liquidity_high']
            linewidth = 2.5
            alpha = 0.5
        elif normalized > 0.4:
            color = COLORS['liquidity_mid']
            linewidth = 1.8
            alpha = 0.4
        elif normalized > 0.2:
            color = COLORS['liquidity_low']
            linewidth = 1.2
            alpha = 0.3
        else:
            color = COLORS['liquidity_low']
            linewidth = 0.8
            alpha = 0.2
        
        # Yatay çizgi
        ax.axhline(y=price, color=color, linewidth=linewidth, 
                  alpha=alpha, linestyle='-', zorder=0)
        
        # Önemli seviyelere etiket ekle
        if normalized > 0.5:
            distance_pct = abs((price - current_price) / current_price)
            if distance_pct > 0.003 and distance_pct < 0.05:  # %0.3 - %5 arası
                ax.text(-1, price, f'${price:.0f}', 
                       color=color, fontsize=9, 
                       va='center', ha='right', alpha=0.8,
                       fontweight='bold' if normalized > 0.7 else 'normal')

def draw_enhanced_volume_profile(ax, df, depth, current_price):
    """Geliştirilmiş volume profile - üst ve alt tam kapsama"""
    
    # Daha geniş fiyat aralığı
    price_range = current_price * 0.05  # %5
    min_price = current_price - price_range
    max_price = current_price + price_range
    
    # Daha fazla seviye
    num_levels = 40
    price_levels = np.linspace(min_price, max_price, num_levels)
    
    # Her seviye için volume hesapla
    volume_profile = []
    order_book_profile = []
    
    for price_level in price_levels:
        # Historical volume
        level_volume = 0
        for _, row in df.iterrows():
            if row['low'] <= price_level <= row['high']:
                # Fiyata yakınlığa göre ağırlıklandır
                distance = min(abs(row['high'] - price_level), 
                             abs(row['low'] - price_level),
                             abs(row['close'] - price_level))
                weight = 1 / (1 + distance / 100)
                level_volume += row['volume'] * weight
        
        # Order book volume
        order_volume = 0
        threshold = price_range / num_levels * 2
        
        for bid_price, bid_qty in depth['bids']:
            if abs(bid_price - price_level) < threshold:
                order_volume += bid_qty
        
        for ask_price, ask_qty in depth['asks']:
            if abs(ask_price - price_level) < threshold:
                order_volume += ask_qty
        
        volume_profile.append(level_volume)
        order_book_profile.append(order_volume)
    
    # Normalize
    max_volume = max(volume_profile) if volume_profile else 1
    max_order = max(order_book_profile) if order_book_profile else 1
    
    # Volume barlarını çiz
    bar_start = len(df) + 2
    bar_width = 10
    
    for i, (price_level, volume, order_vol) in enumerate(zip(price_levels, volume_profile, order_book_profile)):
        if volume > 0 or order_vol > 0:
            # Historical volume bar
            if volume > 0:
                normalized = volume / max_volume
                width = normalized * bar_width * 0.6
                
                color = COLORS['green'] if price_level < current_price else COLORS['red']
                
                rect = Rectangle((bar_start, price_level - (price_range/num_levels/2)), 
                               width, price_range/num_levels,
                               facecolor=color, 
                               alpha=0.3,
                               edgecolor=color,
                               linewidth=0.5,
                               zorder=3)
                ax.add_patch(rect)
            
            # Order book bar (overlay)
            if order_vol > 0:
                normalized = order_vol / max_order
                width = normalized * bar_width * 0.4
                
                color = COLORS['blue']
                
                rect = Rectangle((bar_start + (bar_width * 0.6), 
                                price_level - (price_range/num_levels/2)), 
                               width, price_range/num_levels,
                               facecolor=color, 
                               alpha=0.4,
                               edgecolor=color,
                               linewidth=0,
                               zorder=4)
                ax.add_patch(rect)

def draw_order_walls(ax, depth, current_price, x_offset):
    """Büyük order duvarlarını göster"""
    
    # En büyük bid/ask duvarları bul
    if depth['bids'] and depth['asks']:
        bid_walls = sorted(depth['bids'], key=lambda x: x[1], reverse=True)[:5]
        ask_walls = sorted(depth['asks'], key=lambda x: x[1], reverse=True)[:5]
        
        # Duvarları işaretle
        for bid_price, bid_qty in bid_walls:
            if abs(bid_price - current_price) / current_price < 0.05:  # %5 içinde
                # Yeşil ok (destek)
                ax.annotate('', xy=(x_offset-10, bid_price), 
                          xytext=(x_offset-5, bid_price),
                          arrowprops=dict(arrowstyle='->', color=COLORS['green'], 
                                        lw=2, alpha=0.7))
        
        for ask_price, ask_qty in ask_walls:
            if abs(ask_price - current_price) / current_price < 0.05:  # %5 içinde
                # Kırmızı ok (direnç)
                ax.annotate('', xy=(x_offset-10, ask_price), 
                          xytext=(x_offset-5, ask_price),
                          arrowprops=dict(arrowstyle='->', color=COLORS['red'], 
                                        lw=2, alpha=0.7))

def format_liquidity_caption(symbol, analysis_text=None):
    """Geliştirilmiş likidite haritası caption"""
    
    base_caption = f"""
💧 **{symbol} Enhanced Liquidity Analysis**

📊 **Grafik Açıklaması:**
• **Mavi Çizgiler:** Yüksek likidite bölgeleri
• **Cyan Çizgiler:** Orta likidite
• **Sarı Çizgi:** Mevcut fiyat
• **Sağdaki Barlar:** Volume profili + Order book
• **Oklar:** Büyük alım/satım duvarları

🎯 **Kullanım İpuçları:**
• Kalın mavi çizgiler = Güçlü destek/direnç
• Yeşil oklar = Büyük alım emirleri
• Kırmızı oklar = Büyük satım emirleri
"""
    
    if analysis_text:
        return analysis_text + "\n" + base_caption
    
    return base_caption

print("💧 Enhanced TradingView Style Liquidity Map yüklendi!")
