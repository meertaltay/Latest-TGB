"""
Simplified Modern Chart Generator
Sadece grafik + AI hedef noktaları
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Modern renk paleti
COLORS = {
    'bg_primary': '#0d1117',
    'bg_secondary': '#161b22',
    'bg_tertiary': '#21262d',
    'green': '#3fb950',
    'red': '#f85149',
    'blue': '#58a6ff',
    'purple': '#bc8cff',
    'yellow': '#f0e68c',
    'orange': '#ff9800',
    'cyan': '#79c0ff',
    'text_primary': '#f0f6fc',
    'text_secondary': '#8b949e',
    'grid': '#30363d',
    'border': '#30363d',
    'target': '#ffd700',  # Altın sarısı hedef için
    'stop': '#ff6b6b'     # Kırmızı stop için
}

def create_ultra_modern_chart(df, symbol, analysis_data, timeframe="1h"):
    """
    Sadeleştirilmiş ultra modern grafik - sadece ana grafik ve indikatörler
    AI hedef noktaları ile
    """
    try:
        # Figure oluştur - koyu tema
        fig = plt.figure(figsize=(16, 10), facecolor=COLORS['bg_primary'])
        
        # Grid layout - sadece grafikler
        gs = GridSpec(4, 1, 
                     height_ratios=[3, 1, 1, 1],  # Ana grafik, RSI, MACD, Volume
                     hspace=0.05)
        
        # 1. ANA FİYAT GRAFİĞİ + HEDEFLER
        ax_main = fig.add_subplot(gs[0])
        create_modern_price_chart_with_targets(ax_main, df, analysis_data, symbol, timeframe)
        
        # 2. RSI
        ax_rsi = fig.add_subplot(gs[1], sharex=ax_main)
        create_modern_rsi(ax_rsi, df, analysis_data)
        
        # 3. MACD
        ax_macd = fig.add_subplot(gs[2], sharex=ax_main)
        create_modern_macd(ax_macd, df, analysis_data)
        
        # 4. VOLUME
        ax_volume = fig.add_subplot(gs[3], sharex=ax_main)
        create_modern_volume(ax_volume, df)
        
        # Genel düzenlemeler
        plt.tight_layout()
        
        # Grafik kaydet
        img = BytesIO()
        plt.savefig(img, format='png', dpi=150, bbox_inches='tight', 
                   facecolor=COLORS['bg_primary'], edgecolor='none')
        img.seek(0)
        plt.close()
        
        return img
        
    except Exception as e:
        print(f"Ultra modern grafik hatası: {e}")
        plt.close()
        return None

def create_modern_price_chart_with_targets(ax, df, analysis_data, symbol, timeframe):
    """Modern fiyat grafiği - Candlestick + AI hedef noktaları"""
    ax.set_facecolor(COLORS['bg_secondary'])
    
    # Candlestick çiz
    for i in range(len(df)):
        row = df.iloc[i]
        color = COLORS['green'] if row['close'] >= row['open'] else COLORS['red']
        
        # High-Low çizgisi (wick)
        ax.plot([i, i], [row['low'], row['high']], 
               color=color, linewidth=1, alpha=0.8)
        
        # Open-Close dikdörtgeni (body)
        height = abs(row['close'] - row['open'])
        bottom = min(row['close'], row['open'])
        
        rect = Rectangle((i-0.3, bottom), 0.6, height,
                        facecolor=color, edgecolor=color, 
                        alpha=0.9 if height > 0 else 0.5)
        ax.add_patch(rect)
    
    # Moving Averages
    if len(df) >= 20:
        sma20 = df['close'].rolling(20).mean()
        ax.plot(range(len(df)), sma20, color=COLORS['yellow'], 
               linewidth=2, alpha=0.8, label='MA20')
    
    if len(df) >= 50:
        sma50 = df['close'].rolling(50).mean()
        ax.plot(range(len(df)), sma50, color=COLORS['purple'], 
               linewidth=2, alpha=0.8, label='MA50')
    
    # Bollinger Bands
    if 'bb_data' in analysis_data:
        bb = analysis_data['bb_data']
        ax.fill_between(range(len(df)), bb['upper'], bb['lower'],
                       color=COLORS['blue'], alpha=0.1)
        ax.plot(range(len(df)), bb['upper'], color=COLORS['blue'], 
               linewidth=1, alpha=0.3, linestyle='--')
        ax.plot(range(len(df)), bb['lower'], color=COLORS['blue'], 
               linewidth=1, alpha=0.3, linestyle='--')
    
    current_price = df['close'].iloc[-1]
    current_x = len(df) - 1
    
    # ⭐ AI HEDEF NOKTALARI HESAPLA VE ÇİZ
    score = analysis_data.get('overall_score', 5)
    
    if score >= 7:  # ALIM sinyali
        # Hedef 1: %2 yukarı
        target1 = current_price * 1.02
        # Hedef 2: %5 yukarı
        target2 = current_price * 1.05
        # Hedef 3: %10 yukarı (optimistik)
        target3 = current_price * 1.10
        # Stop Loss: %2 aşağı
        stop_loss = current_price * 0.98
        
        # Hedefleri çiz
        draw_target_point(ax, current_x + 5, target1, "T1: +2%", COLORS['green'], 'up')
        draw_target_point(ax, current_x + 8, target2, "T2: +5%", COLORS['cyan'], 'up')
        draw_target_point(ax, current_x + 12, target3, "T3: +10%", COLORS['target'], 'up')
        draw_target_point(ax, current_x + 3, stop_loss, "STOP: -2%", COLORS['stop'], 'down')
        
        # Mevcut fiyattan hedeflere ok çiz
        draw_arrow_to_target(ax, current_x, current_price, current_x + 5, target1, COLORS['green'])
        draw_arrow_to_target(ax, current_x, current_price, current_x + 8, target2, COLORS['cyan'])
        
        # AI HEDEF yazısı
        ax.text(current_x + 15, target2, '🎯 AI HEDEF', 
               fontsize=12, color=COLORS['target'], fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['bg_primary'], 
                        edgecolor=COLORS['target'], alpha=0.9))
        
    elif score <= 3:  # SATIM sinyali
        # Hedef 1: %2 aşağı
        target1 = current_price * 0.98
        # Hedef 2: %5 aşağı
        target2 = current_price * 0.95
        # Stop Loss: %2 yukarı
        stop_loss = current_price * 1.02
        
        # Hedefleri çiz
        draw_target_point(ax, current_x + 5, target1, "T1: -2%", COLORS['orange'], 'down')
        draw_target_point(ax, current_x + 8, target2, "T2: -5%", COLORS['red'], 'down')
        draw_target_point(ax, current_x + 3, stop_loss, "STOP: +2%", COLORS['stop'], 'up')
        
        # Mevcut fiyattan hedeflere ok çiz
        draw_arrow_to_target(ax, current_x, current_price, current_x + 5, target1, COLORS['orange'])
        draw_arrow_to_target(ax, current_x, current_price, current_x + 8, target2, COLORS['red'])
        
        # AI HEDEF yazısı
        ax.text(current_x + 15, target2, '📉 AI HEDEF', 
               fontsize=12, color=COLORS['red'], fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['bg_primary'], 
                        edgecolor=COLORS['red'], alpha=0.9))
    
    else:  # BEKLE sinyali
        # Üst direnç
        resistance = current_price * 1.03
        # Alt destek
        support = current_price * 0.97
        
        # Yatay bölge çiz
        ax.fill_between([current_x, current_x + 15], support, resistance,
                       color=COLORS['yellow'], alpha=0.1)
        ax.axhline(y=resistance, xmin=0.9, xmax=1.0, color=COLORS['yellow'], 
                  linestyle='--', linewidth=2, alpha=0.5)
        ax.axhline(y=support, xmin=0.9, xmax=1.0, color=COLORS['yellow'], 
                  linestyle='--', linewidth=2, alpha=0.5)
        
        ax.text(current_x + 10, current_price, '⏳ BEKLE BÖLGESİ', 
               fontsize=11, color=COLORS['yellow'], fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['bg_primary'], 
                        edgecolor=COLORS['yellow'], alpha=0.9))
    
    # Mevcut fiyat vurgula
    ax.plot(current_x, current_price, marker='o', markersize=10, 
           color=COLORS['text_primary'], markeredgecolor=COLORS['cyan'], 
           markeredgewidth=2, zorder=5)
    
    # Fibonacci seviyeleri
    if 'fib_levels' in analysis_data:
        for level, price in analysis_data['fib_levels'].items():
            if '23.6%' in level or '38.2%' in level or '61.8%' in level:
                color = COLORS['green'] if price < current_price else COLORS['red']
                ax.axhline(y=price, color=color, linestyle=':', 
                          linewidth=1, alpha=0.3)
                ax.text(len(df)-1, price, f' Fib {level}', 
                       color=color, fontsize=8, va='center', alpha=0.7)
    
    # Başlık
    title = f"{symbol} - {timeframe.upper()} | "
    if score >= 7:
        title += "🟢 AI: GÜÇLÜ ALIM"
    elif score <= 3:
        title += "🔴 AI: SAT"
    else:
        title += "🟡 AI: BEKLE"
    
    ax.set_title(title, fontsize=14, color=COLORS['text_primary'], fontweight='bold', pad=10)
    
    # Grid ve stil
    ax.grid(True, color=COLORS['grid'], alpha=0.2, linestyle='-', linewidth=0.5)
    ax.set_xlim(-1, len(df) + 20)  # Sağa hedef alanı için boşluk
    
    # Y ekseni etiketleri
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()
    ax.tick_params(colors=COLORS['text_secondary'], labelsize=10)
    
    # X ekseni gizle
    ax.set_xticks([])
    
    # Kenarlıkları kaldır
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Legend
    if ax.get_legend_handles_labels()[0]:
        ax.legend(loc='upper left', facecolor=COLORS['bg_tertiary'], 
                 edgecolor=COLORS['border'], fontsize=9, framealpha=0.9)

def draw_target_point(ax, x, y, label, color, direction='up'):
    """Hedef noktası çiz"""
    # Hedef işareti
    if direction == 'up':
        marker = '^'
        y_offset = -0.01 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    else:
        marker = 'v'
        y_offset = 0.01 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    
    # Hedef noktası
    ax.plot(x, y, marker=marker, markersize=12, color=color, 
           markeredgecolor='white', markeredgewidth=1, zorder=5)
    
    # Hedef çizgisi
    ax.axhline(y=y, xmin=0.85, xmax=1.0, color=color, 
              linestyle='--', linewidth=1.5, alpha=0.7)
    
    # Etiket
    ax.text(x, y + y_offset, label, fontsize=9, color=color, 
           ha='center', va='bottom' if direction == 'up' else 'top',
           fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.2", facecolor=COLORS['bg_primary'], 
                    edgecolor=color, alpha=0.8))

def draw_arrow_to_target(ax, x1, y1, x2, y2, color):
    """Mevcut fiyattan hedefe ok çiz"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           connectionstyle="arc3,rad=0.3",
                           arrowstyle='->,head_width=0.3,head_length=0.4',
                           color=color, alpha=0.5, linewidth=1.5,
                           zorder=3)
    ax.add_patch(arrow)

def create_modern_rsi(ax, df, analysis_data):
    """Modern RSI grafiği"""
    ax.set_facecolor(COLORS['bg_secondary'])
    
    # RSI hesapla
    from utils.technical_analysis import calculate_rsi
    rsi = calculate_rsi(df['close'])
    
    # RSI çizgisi
    x = range(len(rsi))
    ax.plot(x, rsi, color=COLORS['purple'], linewidth=2.5, alpha=0.9)
    
    # Bölgeleri renklendir
    ax.fill_between(x, 70, 100, color=COLORS['red'], alpha=0.1)
    ax.fill_between(x, 0, 30, color=COLORS['green'], alpha=0.1)
    
    # Seviye çizgileri
    ax.axhline(y=70, color=COLORS['red'], linestyle='--', linewidth=1, alpha=0.3)
    ax.axhline(y=50, color=COLORS['text_secondary'], linestyle=':', linewidth=1, alpha=0.2)
    ax.axhline(y=30, color=COLORS['green'], linestyle='--', linewidth=1, alpha=0.3)
    
    # Son değer
    current_rsi = rsi.iloc[-1]
    color = COLORS['red'] if current_rsi > 70 else COLORS['green'] if current_rsi < 30 else COLORS['yellow']
    
    # RSI değerini sağ üst köşeye yaz
    ax.text(0.98, 0.9, f'RSI: {current_rsi:.1f}', 
            transform=ax.transAxes,
            color=color, fontweight='bold', fontsize=11,
            ha='right', va='top',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['bg_primary'], 
                     edgecolor=color, alpha=0.8))
    
    # Stil
    ax.set_xlim(0, len(rsi) + 20)
    ax.set_ylim(0, 100)
    ax.set_ylabel('RSI', color=COLORS['text_secondary'], fontsize=10)
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()
    ax.set_xticks([])
    ax.grid(True, color=COLORS['grid'], alpha=0.2, linestyle='-', linewidth=0.5)
    ax.tick_params(colors=COLORS['text_secondary'], labelsize=9)
    
    for spine in ax.spines.values():
        spine.set_visible(False)

def create_modern_macd(ax, df, analysis_data):
    """Modern MACD grafiği"""
    ax.set_facecolor(COLORS['bg_secondary'])
    
    # MACD hesapla
    from utils.technical_analysis import calculate_macd
    macd_data = calculate_macd(df['close'])
    
    x = range(len(macd_data['macd']))
    
    # MACD ve Signal çizgileri
    ax.plot(x, macd_data['macd'], color=COLORS['blue'], 
           linewidth=2, alpha=0.9, label='MACD')
    ax.plot(x, macd_data['signal'], color=COLORS['orange'], 
           linewidth=2, alpha=0.9, label='Signal')
    
    # Histogram
    colors = [COLORS['green'] if val >= 0 else COLORS['red'] 
             for val in macd_data['histogram']]
    ax.bar(x, macd_data['histogram'], color=colors, alpha=0.5, width=0.8)
    
    # Zero line
    ax.axhline(y=0, color=COLORS['text_secondary'], linewidth=1, alpha=0.3)
    
    # Crossover işaretleri
    for i in range(1, len(macd_data['macd'])):
        if (macd_data['macd'].iloc[i] > macd_data['signal'].iloc[i] and 
            macd_data['macd'].iloc[i-1] <= macd_data['signal'].iloc[i-1]):
            ax.scatter(i, macd_data['macd'].iloc[i], color=COLORS['green'], 
                      s=50, zorder=5, marker='^')
        elif (macd_data['macd'].iloc[i] < macd_data['signal'].iloc[i] and 
              macd_data['macd'].iloc[i-1] >= macd_data['signal'].iloc[i-1]):
            ax.scatter(i, macd_data['macd'].iloc[i], color=COLORS['red'], 
                      s=50, zorder=5, marker='v')
    
    # MACD durumu
    if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1]:
        status = "BULLISH"
        color = COLORS['green']
    else:
        status = "BEARISH"
        color = COLORS['red']
    
    ax.text(0.98, 0.9, f'MACD: {status}', 
            transform=ax.transAxes,
            color=color, fontweight='bold', fontsize=11,
            ha='right', va='top',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['bg_primary'], 
                     edgecolor=color, alpha=0.8))
    
    # Stil
    ax.set_xlim(0, len(macd_data['macd']) + 20)
    ax.set_ylabel('MACD', color=COLORS['text_secondary'], fontsize=10)
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()
    ax.set_xticks([])
    ax.grid(True, color=COLORS['grid'], alpha=0.2, linestyle='-', linewidth=0.5)
    ax.tick_params(colors=COLORS['text_secondary'], labelsize=9)
    
    for spine in ax.spines.values():
        spine.set_visible(False)

def create_modern_volume(ax, df):
    """Modern hacim grafiği"""
    ax.set_facecolor(COLORS['bg_secondary'])
    
    # Renkleri belirle
    colors = []
    for i in range(len(df)):
        if i == 0:
            colors.append(COLORS['blue'])
        else:
            color = COLORS['green'] if df['close'].iloc[i] >= df['close'].iloc[i-1] else COLORS['red']
            colors.append(color)
    
    # Volume barları
    x = range(len(df))
    bars = ax.bar(x, df['volume'], color=colors, alpha=0.7, width=0.8)
    
    # Volume MA
    if len(df) >= 20:
        volume_ma = df['volume'].rolling(20).mean()
        ax.plot(x, volume_ma, color=COLORS['yellow'], 
               linewidth=2, alpha=0.8, label='Vol MA20')
    
    # Anormal hacim işaretle
    avg_volume = df['volume'].mean()
    for i, vol in enumerate(df['volume']):
        if vol > avg_volume * 2:
            ax.scatter(i, vol, color=COLORS['cyan'], s=30, 
                      zorder=5, marker='*', alpha=0.8)
    
    # Volume durumu
    current_vol = df['volume'].iloc[-1]
    vol_ratio = current_vol / avg_volume if avg_volume > 0 else 1
    
    if vol_ratio > 1.5:
        vol_status = f"HIGH VOL ({vol_ratio:.1f}x)"
        color = COLORS['cyan']
    elif vol_ratio < 0.5:
        vol_status = f"LOW VOL ({vol_ratio:.1f}x)"
        color = COLORS['orange']
    else:
        vol_status = f"NORMAL ({vol_ratio:.1f}x)"
        color = COLORS['text_secondary']
    
    ax.text(0.98, 0.9, vol_status, 
            transform=ax.transAxes,
            color=color, fontweight='bold', fontsize=11,
            ha='right', va='top',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['bg_primary'], 
                     edgecolor=color, alpha=0.8))
    
    # Stil
    ax.set_xlim(0, len(df) + 20)
    ax.set_ylabel('Volume', color=COLORS['text_secondary'], fontsize=10)
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()
    ax.set_xlabel('Time', color=COLORS['text_secondary'], fontsize=10)
    ax.grid(True, color=COLORS['grid'], alpha=0.2, axis='y', linewidth=0.5)
    ax.tick_params(colors=COLORS['text_secondary'], labelsize=9)
    
    # Y ekseni formatı
    ax.ticklabel_format(style='plain', axis='y')
    
    for spine in ax.spines.values():
        spine.set_visible(False)

print("🎨 Simplified Modern Chart with AI Targets yüklendi!")
