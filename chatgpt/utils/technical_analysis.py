"""
Technical Analysis Utils
RSI, MACD, Bollinger Bands ve diğer teknik indikatörler
"""

import pandas as pd
import numpy as np
from config import *

def calculate_rsi(prices, window=14):
    """RSI (Relative Strength Index) hesapla"""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        print(f"RSI hesaplama hatası: {e}")
        return pd.Series(index=prices.index, dtype=float)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence) hesapla"""
    try:
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    except Exception as e:
        print(f"MACD hesaplama hatası: {e}")
        return {
            'macd': pd.Series(index=prices.index, dtype=float),
            'signal': pd.Series(index=prices.index, dtype=float),
            'histogram': pd.Series(index=prices.index, dtype=float)
        }

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """Bollinger Bands hesapla"""
    try:
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    except Exception as e:
        print(f"Bollinger Bands hesaplama hatası: {e}")
        return {
            'upper': pd.Series(index=prices.index, dtype=float),
            'middle': pd.Series(index=prices.index, dtype=float),
            'lower': pd.Series(index=prices.index, dtype=float)
        }

def calculate_sma(prices, window):
    """Simple Moving Average hesapla"""
    try:
        return prices.rolling(window=window).mean()
    except Exception as e:
        print(f"SMA hesaplama hatası: {e}")
        return pd.Series(index=prices.index, dtype=float)

def calculate_ema(prices, window):
    """Exponential Moving Average hesapla"""
    try:
        return prices.ewm(span=window).mean()
    except Exception as e:
        print(f"EMA hesaplama hatası: {e}")
        return pd.Series(index=prices.index, dtype=float)

def find_support_resistance(df, window=5):
    """Destek ve direnç seviyelerini bul"""
    try:
        highs = []
        lows = []
        
        # Pivot noktalarını bul
        for i in range(window, len(df) - window):
            # Yerel maksimum
            if all(df['high'].iloc[i] >= df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] >= df['high'].iloc[i+j] for j in range(1, window+1)):
                highs.append(df['high'].iloc[i])
            
            # Yerel minimum
            if all(df['low'].iloc[i] <= df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] <= df['low'].iloc[i+j] for j in range(1, window+1)):
                lows.append(df['low'].iloc[i])
        
        return {
            'resistance_levels': sorted(highs, reverse=True)[:3],  # En yüksek 3 direnç
            'support_levels': sorted(lows)[:3]  # En düşük 3 destek
        }
    except Exception as e:
        print(f"Destek/direnç hesaplama hatası: {e}")
        return {
            'resistance_levels': [],
            'support_levels': []
        }

def calculate_volume_analysis(df, window=20):
    """Volume analizi yap"""
    try:
        avg_volume = df['volume'].rolling(window=window).mean()
        current_volume = df['volume'].iloc[-1]
        avg_volume_value = avg_volume.iloc[-1]
        
        volume_ratio = current_volume / avg_volume_value if avg_volume_value > 0 else 1
        
        # Volume trend
        recent_volume_trend = df['volume'].tail(5).mean() / df['volume'].tail(10).mean()
        
        return {
            'current_volume': current_volume,
            'average_volume': avg_volume_value,
            'volume_ratio': volume_ratio,
            'volume_trend': recent_volume_trend,
            'volume_analysis': get_volume_interpretation(volume_ratio)
        }
    except Exception as e:
        print(f"Volume analizi hatası: {e}")
        return {
            'current_volume': 0,
            'average_volume': 0,
            'volume_ratio': 1,
            'volume_trend': 1,
            'volume_analysis': 'Belirsiz'
        }

def get_volume_interpretation(volume_ratio):
    """Volume oranını yorumla"""
    if volume_ratio > 2:
        return "Çok Yüksek Hacim"
    elif volume_ratio > 1.5:
        return "Yüksek Hacim"
    elif volume_ratio > 1.2:
        return "Ortalamanın Üzerinde"
    elif volume_ratio > 0.8:
        return "Normal Hacim"
    elif volume_ratio > 0.5:
        return "Düşük Hacim"
    else:
        return "Çok Düşük Hacim"

def calculate_trend_strength(df):
    """Trend gücünü hesapla"""
    try:
        # SMA'ları hesapla
        sma_20 = calculate_sma(df['close'], 20)
        sma_50 = calculate_sma(df['close'], 50)
        sma_200 = calculate_sma(df['close'], 200)
        
        current_price = df['close'].iloc[-1]
        
        trend_score = 0
        trend_signals = []
        
        # Fiyat - SMA karşılaştırmaları
        if current_price > sma_20.iloc[-1]:
            trend_score += 1
            trend_signals.append("Fiyat 20 SMA üzerinde")
        
        if current_price > sma_50.iloc[-1]:
            trend_score += 1
            trend_signals.append("Fiyat 50 SMA üzerinde")
        
        if current_price > sma_200.iloc[-1]:
            trend_score += 1
            trend_signals.append("Fiyat 200 SMA üzerinde")
        
        # SMA sıralaması
        if sma_20.iloc[-1] > sma_50.iloc[-1]:
            trend_score += 1
            trend_signals.append("20 SMA > 50 SMA")
        
        if sma_50.iloc[-1] > sma_200.iloc[-1]:
            trend_score += 1
            trend_signals.append("50 SMA > 200 SMA")
        
        # Trend yönü
        if trend_score >= 4:
            trend_direction = "Güçlü Yükseliş"
        elif trend_score >= 3:
            trend_direction = "Yükseliş"
        elif trend_score >= 2:
            trend_direction = "Zayıf Yükseliş"
        elif trend_score == 1:
            trend_direction = "Belirsiz"
        else:
            trend_direction = "Düşüş"
        
        return {
            'trend_score': trend_score,
            'trend_direction': trend_direction,
            'trend_signals': trend_signals,
            'sma_20': sma_20.iloc[-1],
            'sma_50': sma_50.iloc[-1],
            'sma_200': sma_200.iloc[-1]
        }
    except Exception as e:
        print(f"Trend analizi hatası: {e}")
        return {
            'trend_score': 0,
            'trend_direction': 'Belirsiz',
            'trend_signals': [],
            'sma_20': 0,
            'sma_50': 0,
            'sma_200': 0
        }

def generate_trading_signals(df):
    """Trading sinyalleri üret"""
    try:
        signals = []
        
        # RSI sinyalleri
        rsi = calculate_rsi(df['close'])
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < 30:
            signals.append({"type": "BUY", "reason": "RSI aşırı satım", "strength": "Orta"})
        elif current_rsi > 70:
            signals.append({"type": "SELL", "reason": "RSI aşırı alım", "strength": "Orta"})
        
        # MACD sinyalleri
        macd_data = calculate_macd(df['close'])
        if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1] and \
           macd_data['macd'].iloc[-2] <= macd_data['signal'].iloc[-2]:
            signals.append({"type": "BUY", "reason": "MACD pozitif kesişim", "strength": "Güçlü"})
        elif macd_data['macd'].iloc[-1] < macd_data['signal'].iloc[-1] and \
             macd_data['macd'].iloc[-2] >= macd_data['signal'].iloc[-2]:
            signals.append({"type": "SELL", "reason": "MACD negatif kesişim", "strength": "Güçlü"})
        
        # Bollinger Bands sinyalleri
        bb = calculate_bollinger_bands(df['close'])
        current_price = df['close'].iloc[-1]
        
        if current_price < bb['lower'].iloc[-1]:
            signals.append({"type": "BUY", "reason": "Bollinger alt band altında", "strength": "Orta"})
        elif current_price > bb['upper'].iloc[-1]:
            signals.append({"type": "SELL", "reason": "Bollinger üst band üzerinde", "strength": "Orta"})
        
        return signals
    except Exception as e:
        print(f"Sinyal üretme hatası: {e}")
        return []

if DEBUG_MODE:
    print("📈 Technical analysis utils yüklendi!")

