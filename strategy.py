# strategy.py
import pandas as pd
import numpy as np
# Se importan los parámetros necesarios desde config.py
from config import (
    BREAKOUT_BARS, VOL_LOOKBACK, VWAP_PERIOD,
    RSI_PERIOD, EMA_PERIOD, BB_PERIOD, BB_STD_DEV
)

class ScalpingStrategy:
    def __init__(self):
        pass

    def compute_indicators(self, df):
        df = df.copy()
        # Indicadores basados en breakout
        df['high_n'] = df['high'].rolling(BREAKOUT_BARS).max().shift(1)
        df['low_n'] = df['low'].rolling(BREAKOUT_BARS).min().shift(1)
        df['vol_avg'] = df['volume'].rolling(VOL_LOOKBACK).mean().shift(1)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = ((typical_price * df['volume']).rolling(VWAP_PERIOD).sum() /
                      df['volume'].rolling(VWAP_PERIOD).sum()).shift(1)
        
        # Indicadores adicionales
        df['rsi'] = self.compute_rsi(df['close'], RSI_PERIOD)
        df['ema'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()
        df['bb_mid'] = df['close'].rolling(window=BB_PERIOD).mean()
        df['bb_std'] = df['close'].rolling(window=BB_PERIOD).std()
        df['bb_upper'] = df['bb_mid'] + (BB_STD_DEV * df['bb_std'])
        df['bb_lower'] = df['bb_mid'] - (BB_STD_DEV * df['bb_std'])
        # ATR para medir la volatilidad
        df['atr'] = self.compute_atr(df)
        
        return df

    def compute_rsi(self, series, period):
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def compute_atr(self, df, period=14):
        df = df.copy()
        df['tr'] = df.apply(lambda row: max(
            row['high'] - row['low'],
            abs(row['high'] - row['close']),
            abs(row['low'] - row['close'])
        ), axis=1)
        atr = df['tr'].rolling(period).mean()
        return atr

    def compute_order_flow_imbalance(self, order_book):
        bids = order_book['bids']
        asks = order_book['asks']
        bid_volume = sum([bid[1] for bid in bids])
        ask_volume = sum([ask[1] for ask in asks])
        if bid_volume + ask_volume == 0:
            return 0
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        return imbalance

    def generate_signal(self, df, order_book=None):
        row = df.iloc[-1]
        required_cols = ['high_n', 'low_n', 'vol_avg', 'vwap', 'rsi', 'ema', 'bb_upper', 'bb_lower', 'atr']
        for col in required_cols:
            if pd.isna(row[col]):
                print(f"[DEBUG] Indicador {col} incompleto en la última vela.")
                return 0

        current_close = row['close']
        recent_high = row['high_n']
        recent_low = row['low_n']
        current_vol = row['volume']
        avg_vol = row['vol_avg']
        vwap = row['vwap']
        rsi = row['rsi']
        ema = row['ema']

        # Señal inicial basada en indicadores técnicos
        indicator_signal = 0
        # Condición para entrada LONG
        if (current_close > recent_high and
            current_vol > avg_vol and
            current_close > vwap and
            current_close > ema and
            50 < rsi < 70):
            indicator_signal = 1
        # Condición para entrada SHORT
        elif (current_close < recent_low and
              current_vol > avg_vol and
              current_close < vwap and
              current_close < ema and
              30 < rsi < 50):
            indicator_signal = -1

        print("[DEBUG] Señal de indicadores:", indicator_signal)

        # Incorporar análisis de Order Flow si se dispone del libro de órdenes
        if order_book is not None:
            imbalance = self.compute_order_flow_imbalance(order_book)
            print("[DEBUG] Order Flow Imbalance:", imbalance)
            # Se requiere que la presión del mercado respalde la señal
            if indicator_signal == 1 and imbalance < 0.3:
                print("[DEBUG] Order Flow no confirma señal LONG")
                indicator_signal = 0
            elif indicator_signal == -1 and imbalance > -0.3:
                print("[DEBUG] Order Flow no confirma señal SHORT")
                indicator_signal = 0

        # La señal final se basará únicamente en los indicadores técnicos y el order flow
        final_signal = indicator_signal
        print("[DEBUG] Señal final combinada (sin ML):", final_signal)
        return final_signal
