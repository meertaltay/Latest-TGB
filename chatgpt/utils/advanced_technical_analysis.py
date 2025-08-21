"""
Advanced Technical Analysis Utils
Gelişmiş teknik indikatörler ve çoklu timeframe analizi
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

# =============================================================================
# YENİ GELİŞMİŞ İNDİKATÖRLER
# =============================================================================

def calculate_stochastic(df, k_period=14, d_period=3):
    """Stochastic Oscillator hesapla"""
    try:
        high_max = df['high'].rolling(window=k_period).max()
        low_min = df['low'].rolling(window=k_period).min()
        
        k_percent = ((df['close'] - low_min) / (high_max - low_min)) * 100
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k_percent': k_percent,
            'd_percent': d_percent
        }
    except Exception as e:
        print(f"Stochastic hesaplama hatası: {e}")
        return {
            'k_percent': pd.Series(index=df.index, dtype=float),
            'd_percent': pd.Series(index=df.index, dtype=float)
        }

def calculate_fibonacci_levels(df, lookback=50):
    """Fibonacci Retracement Levels hesapla"""
    try:
        recent_data = df.tail(lookback)
        high_price = recent_data['high'].max()
        low_price = recent_data['low'].min()
        
        diff = high_price - low_price
        
        fib_levels = {
            '0%': high_price,
            '23.6%': high_price - (diff * 0.236),
            '38.2%': high_price - (diff * 0.382),
            '50%': high_price - (diff * 0.5),
            '61.8%': high_price - (diff * 0.618),
            '78.6%': high_price - (diff * 0.786),
            '100%': low_price
        }
        
        return fib_levels
    except Exception as e:
        print(f"Fibonacci hesaplama hatası: {e}")
        return {}

def calculate_ichimoku(df):
    """Ichimoku Cloud hesapla"""
    try:
        # Conversion Line (Tenkan-sen)
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        conversion_line = (high_9 + low_9) / 2
        
        # Base Line (Kijun-sen)
        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        base_line = (high_26 + low_26) / 2
        
        # Leading Span A (Senkou Span A)
        leading_span_a = ((conversion_line + base_line) / 2).shift(26)
        
        # Leading Span B (Senkou Span B)
        high_52 = df['high'].rolling(window=52).max()
        low_52 = df['low'].rolling(window=52).min()
        leading_span_b = ((high_52 + low_52) / 2).shift(26)
        
        # Lagging Span (Chikou Span)
        lagging_span = df['close'].shift(-26)
        
        return {
            'conversion_line': conversion_line,
            'base_line': base_line,
            'leading_span_a': leading_span_a,
            'leading_span_b': leading_span_b,
            'lagging_span': lagging_span
        }
    except Exception as e:
        print(f"Ichimoku hesaplama hatası: {e}")
        return {}

# =============================================================================
# ÇOKLU TIMEFRAME ANALİZİ
# =============================================================================

def analyze_multiple_timeframes(symbol, timeframes=['1h', '4h', '1d', '1w']):
    """Çoklu timeframe analizi"""
    try:
        from utils.binance_api import get_binance_ohlc
        
        timeframe_results = {}
        
        for tf in timeframes:
            # Limit'i timeframe'e göre ayarla
            if tf == '1h':
                limit = 168  # 1 hafta
            elif tf == '4h':
                limit = 168  # 4 hafta
            elif tf == '1d':
                limit = 100  # 100 gün
            else:  # 1w
                limit = 52   # 1 yıl
            
            df = get_binance_ohlc(symbol, interval=tf, limit=limit)
            if df is not None and not df.empty:
                analysis = perform_single_timeframe_analysis(df)
                timeframe_results[tf] = analysis
        
        return timeframe_results
    except Exception as e:
        print(f"Çoklu timeframe analiz hatası: {e}")
        return {}

def perform_single_timeframe_analysis(df):
    """Tek timeframe için kapsamlı analiz"""
    try:
        current_price = df['close'].iloc[-1]
        
        # Temel indikatörler
        rsi = calculate_rsi(df['close']).iloc[-1]
        macd_data = calculate_macd(df['close'])
        bb_data = calculate_bollinger_bands(df['close'])
        stoch_data = calculate_stochastic(df)
        
        # Trend analizi
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1]
        
        # Sinyal gücü hesaplama
        signals = calculate_signal_strength(df, rsi, macd_data, bb_data, stoch_data)
        
        # Entry/Exit noktaları
        entry_exit = calculate_entry_exit_points(df, current_price, bb_data, signals)
        
        return {
            'price': current_price,
            'rsi': rsi,
            'macd_signal': 'BULLISH' if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1] else 'BEARISH',
            'bb_position': get_bb_position(current_price, bb_data),
            'stoch_signal': get_stochastic_signal(stoch_data),
            'trend': 'BULLISH' if current_price > sma_20 > sma_50 else 'BEARISH' if current_price < sma_20 < sma_50 else 'NEUTRAL',
            'signals': signals,
            'entry_exit': entry_exit,
            'overall_score': calculate_timeframe_score(signals)
        }
    except Exception as e:
        print(f"Timeframe analiz hatası: {e}")
        return {}

# =============================================================================
# SİNYAL GÜCÜ HESAPLAMA
# =============================================================================

def calculate_signal_strength(df, rsi, macd_data, bb_data, stoch_data):
    """Her sinyal için güç skoru (1-10) hesapla"""
    try:
        signals = []
        current_price = df['close'].iloc[-1]
        
        # RSI Sinyali
        if rsi < 30:
            strength = min(10, (30 - rsi) / 3)  # Ne kadar düşükse o kadar güçlü
            signals.append({
                'type': 'BUY',
                'indicator': 'RSI',
                'reason': f'Aşırı satım (RSI: {rsi:.1f})',
                'strength': round(strength),
                'confidence': 'Yüksek' if strength >= 7 else 'Orta' if strength >= 5 else 'Düşük'
            })
        elif rsi > 70:
            strength = min(10, (rsi - 70) / 3)
            signals.append({
                'type': 'SELL',
                'indicator': 'RSI',
                'reason': f'Aşırı alım (RSI: {rsi:.1f})',
                'strength': round(strength),
                'confidence': 'Yüksek' if strength >= 7 else 'Orta' if strength >= 5 else 'Düşük'
            })
        
        # MACD Sinyali
        macd_current = macd_data['macd'].iloc[-1]
        macd_signal = macd_data['signal'].iloc[-1]
        macd_prev = macd_data['macd'].iloc[-2]
        signal_prev = macd_data['signal'].iloc[-2]
        
        # MACD crossover
        if macd_current > macd_signal and macd_prev <= signal_prev:
            strength = min(10, abs(macd_current - macd_signal) * 1000)
            signals.append({
                'type': 'BUY',
                'indicator': 'MACD',
                'reason': 'MACD pozitif kesişim',
                'strength': max(5, round(strength)),
                'confidence': 'Yüksek'
            })
        elif macd_current < macd_signal and macd_prev >= signal_prev:
            strength = min(10, abs(macd_current - macd_signal) * 1000)
            signals.append({
                'type': 'SELL',
                'indicator': 'MACD',
                'reason': 'MACD negatif kesişim',
                'strength': max(5, round(strength)),
                'confidence': 'Yüksek'
            })
        
        # Bollinger Bands Sinyali
        bb_upper = bb_data['upper'].iloc[-1]
        bb_lower = bb_data['lower'].iloc[-1]
        bb_middle = bb_data['middle'].iloc[-1]
        
        if current_price <= bb_lower:
            distance = (bb_middle - current_price) / bb_middle * 100
            strength = min(10, distance * 2)
            signals.append({
                'type': 'BUY',
                'indicator': 'Bollinger',
                'reason': 'Alt band test',
                'strength': max(4, round(strength)),
                'confidence': 'Orta'
            })
        elif current_price >= bb_upper:
            distance = (current_price - bb_middle) / bb_middle * 100
            strength = min(10, distance * 2)
            signals.append({
                'type': 'SELL',
                'indicator': 'Bollinger',
                'reason': 'Üst band test',
                'strength': max(4, round(strength)),
                'confidence': 'Orta'
            })
        
        # Stochastic Sinyali
        if len(stoch_data) > 0:
            k_current = stoch_data['k_percent'].iloc[-1]
            d_current = stoch_data['d_percent'].iloc[-1]
            
            if k_current < 20 and d_current < 20:
                strength = min(10, (20 - min(k_current, d_current)) / 2)
                signals.append({
                    'type': 'BUY',
                    'indicator': 'Stochastic',
                    'reason': f'Aşırı satım bölgesi',
                    'strength': max(3, round(strength)),
                    'confidence': 'Orta'
                })
            elif k_current > 80 and d_current > 80:
                strength = min(10, (min(k_current, d_current) - 80) / 2)
                signals.append({
                    'type': 'SELL',
                    'indicator': 'Stochastic',
                    'reason': f'Aşırı alım bölgesi',
                    'strength': max(3, round(strength)),
                    'confidence': 'Orta'
                })
        
        return signals
    except Exception as e:
        print(f"Sinyal gücü hesaplama hatası: {e}")
        return []

# =============================================================================
# ENTRY/EXIT NOKTALARI
# =============================================================================

def calculate_entry_exit_points(df, current_price, bb_data, signals):
    """Net entry/exit noktaları hesapla"""
    try:
        # Destek/Direnç seviyeleri
        support_levels = find_support_levels(df, current_price)
        resistance_levels = find_resistance_levels(df, current_price)
        
        # Fibonacci seviyeleri
        fib_levels = calculate_fibonacci_levels(df)
        
        # Sinyal bazlı entry/exit
        buy_signals = [s for s in signals if s['type'] == 'BUY']
        sell_signals = [s for s in signals if s['type'] == 'SELL']
        
        buy_strength = sum(s['strength'] for s in buy_signals)
        sell_strength = sum(s['strength'] for s in sell_signals)
        
        entry_exit_points = {
            'current_price': current_price,
            'action': 'BUY' if buy_strength > sell_strength else 'SELL' if sell_strength > buy_strength else 'HOLD',
            'confidence': abs(buy_strength - sell_strength),
            'entry_points': [],
            'exit_points': [],
            'stop_loss': None,
            'take_profit': None
        }
        
        if buy_strength > sell_strength:
            # LONG pozisyon önerileri
            entry_exit_points['entry_points'] = [
                {'price': current_price, 'reason': 'Market fiyatı', 'priority': 'Yüksek'},
                {'price': support_levels[0] if support_levels else current_price * 0.98, 'reason': 'Destek testi', 'priority': 'Orta'},
                {'price': bb_data['lower'].iloc[-1], 'reason': 'Bollinger alt band', 'priority': 'Düşük'}
            ]
            
            entry_exit_points['stop_loss'] = support_levels[1] if len(support_levels) > 1 else current_price * 0.95
            entry_exit_points['take_profit'] = resistance_levels[0] if resistance_levels else current_price * 1.05
            
        elif sell_strength > buy_strength:
            # SHORT pozisyon önerileri
            entry_exit_points['entry_points'] = [
                {'price': current_price, 'reason': 'Market fiyatı', 'priority': 'Yüksek'},
                {'price': resistance_levels[0] if resistance_levels else current_price * 1.02, 'reason': 'Direnç testi', 'priority': 'Orta'},
                {'price': bb_data['upper'].iloc[-1], 'reason': 'Bollinger üst band', 'priority': 'Düşük'}
            ]
            
            entry_exit_points['stop_loss'] = resistance_levels[1] if len(resistance_levels) > 1 else current_price * 1.05
            entry_exit_points['take_profit'] = support_levels[0] if support_levels else current_price * 0.95
        
        return entry_exit_points
    except Exception as e:
        print(f"Entry/Exit hesaplama hatası: {e}")
        return {}

def find_support_levels(df, current_price, window=5):
    """Destek seviyelerini bul"""
    try:
        lows = []
        for i in range(window, len(df) - window):
            if all(df['low'].iloc[i] <= df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] <= df['low'].iloc[i+j] for j in range(1, window+1)):
                if df['low'].iloc[i] < current_price:  # Sadece mevcut fiyatın altındaki destekler
                    lows.append(df['low'].iloc[i])
        
        return sorted(lows, reverse=True)[:3]  # En yakın 3 destek
    except:
        return []

def find_resistance_levels(df, current_price, window=5):
    """Direnç seviyelerini bul"""
    try:
        highs = []
        for i in range(window, len(df) - window):
            if all(df['high'].iloc[i] >= df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] >= df['high'].iloc[i+j] for j in range(1, window+1)):
                if df['high'].iloc[i] > current_price:  # Sadece mevcut fiyatın üstündeki dirençler
                    highs.append(df['high'].iloc[i])
        
        return sorted(highs)[:3]  # En yakın 3 direnç
    except:
        return []

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def get_bb_position(price, bb_data):
    """Bollinger Bands içindeki pozisyonu belirle"""
    try:
        upper = bb_data['upper'].iloc[-1]
        lower = bb_data['lower'].iloc[-1]
        middle = bb_data['middle'].iloc[-1]
        
        if price > upper:
            return "Üst band üzerinde"
        elif price < lower:
            return "Alt band altında"
        elif price > middle:
            return "Orta üst bölgede"
        else:
            return "Orta alt bölgede"
    except:
        return "Belirsiz"

def get_stochastic_signal(stoch_data):
    """Stochastic sinyalini belirle"""
    try:
        k = stoch_data['k_percent'].iloc[-1]
        d = stoch_data['d_percent'].iloc[-1]
        
        if k < 20 and d < 20:
            return "Aşırı satım"
        elif k > 80 and d > 80:
            return "Aşırı alım"
        elif k > d:
            return "Yükseliş momentum"
        else:
            return "Düşüş momentum"
    except:
        return "Belirsiz"

def calculate_timeframe_score(signals):
    """Timeframe için genel skor hesapla"""
    try:
        if not signals:
            return 5
        
        buy_strength = sum(s['strength'] for s in signals if s['type'] == 'BUY')
        sell_strength = sum(s['strength'] for s in signals if s['type'] == 'SELL')
        
        net_strength = buy_strength - sell_strength
        
        # -20 ile +20 arası normalize et, sonra 0-10 skalasına çevir
        normalized = max(-20, min(20, net_strength))
        score = (normalized + 20) / 4  # 0-10 arası
        
        return round(score, 1)
    except:
        return 5

if DEBUG_MODE:
    print("📈 Advanced technical analysis utils yüklendi!")
