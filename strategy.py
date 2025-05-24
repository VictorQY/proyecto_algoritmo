# strategy.py optimizado con integración OpenAI usando múltiples marcos temporales
import pandas as pd
import numpy as np
from openai import OpenAI
from config import (
    BREAKOUT_BARS, VOL_LOOKBACK, VWAP_PERIOD,
    RSI_PERIOD, EMA_PERIOD, OPENAI_API_KEY )

client = OpenAI(api_key=OPENAI_API_KEY)

class ScalpingStrategy:
    def __init__(self):
        pass

    def compute_indicators(self, df):
        df = df.copy()
        df['high_n'] = df['high'].rolling(BREAKOUT_BARS).max().shift(1)
        df['low_n'] = df['low'].rolling(BREAKOUT_BARS).min().shift(1)
        df['vol_avg'] = df['volume'].rolling(VOL_LOOKBACK).mean().shift(1)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = ((typical_price * df['volume']).rolling(VWAP_PERIOD).sum() /
                      df['volume'].rolling(VWAP_PERIOD).sum()).shift(1)
        df['rsi'] = self.compute_rsi(df['close'], RSI_PERIOD)
        df['ema'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()
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

    def generate_signal_openai(self, df_1m, df_5m, df_15m):
        df_1m = self.compute_indicators(df_1m)
        df_5m = self.compute_indicators(df_5m)
        df_15m = self.compute_indicators(df_15m)

        messages = [
            {"role": "system", "content": """
            Eres un trader experto en scalping del par DOGE/USDT.
            
            Recibirás datos técnicos de los marcos temporales de 1, 5 y 15 minutos.
            
            Debes responder exactamente en este formato (sin añadir explicaciones, comentarios ni variaciones en el formato):
            
            Dirección inmediata: LONG | SHORT | NO_OP
            STOP LOSS (%): valor%
            TAKE PROFIT (%): valor%
            
            Ejemplo respuesta válida:
            Dirección inmediata: LONG
            STOP LOSS (%): 0.15%
            TAKE PROFIT (%): 0.30%
            
            Usa un punto (.) como separador decimal. No uses paréntesis ni caracteres adicionales.
            """},
            {"role": "user", "content": f"""
            Indicadores técnicos última vela:

            Marco Temporal: 1 minuto:
            {df_1m.iloc[-1].to_dict()}

            Marco Temporal: 5 minutos:
            {df_5m.iloc[-1].to_dict()}

            Marco Temporal: 15 minutos:
            {df_15m.iloc[-1].to_dict()}

            Responde ahora con tu decisión.
            """}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=messages,
            temperature=0.0
        )

        action_text = response.choices[0].message.content.strip()
        print("[DEBUG] Respuesta OpenAI:", action_text)

        lines = action_text.split('\n')

        action_map = {'LONG': 1, 'SHORT': -1, 'NO_OP': 0}

        action = 0
        stop_loss_pct = 0.002
        take_profit_pct = 0.003

        for line in lines:
            if "Dirección inmediata" in line:
                direction = line.split(":")[-1].strip()
                action = action_map.get(direction, 0)
            elif "STOP LOSS (%)" in line:
                sl_value = line.split(":")[-1].strip().replace('%', '')
                stop_loss_pct = float(sl_value) / 100
            elif "TAKE PROFIT (%)" in line:
                tp_value = line.split(":")[-1].strip().replace('%', '')
                take_profit_pct = float(tp_value) / 100

        return action, stop_loss_pct, take_profit_pct

    def generate_signal(self, df_1m, df_5m, df_15m):
        signal, sl_pct, tp_pct = self.generate_signal_openai(df_1m, df_5m, df_15m)
        print("[DEBUG] Señal OpenAI:", signal, "SL:", sl_pct, "TP:", tp_pct)
        return signal, sl_pct, tp_pct