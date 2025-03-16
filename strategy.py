# strategy.py
import pandas as pd
import numpy as np
from config import BREAKOUT_BARS, VOL_LOOKBACK, VWAP_PERIOD 

class ScalpingStrategy:
    def __init__(self):
        pass

    def compute_indicators(self, df):
        """
        Calcula los siguientes indicadores:
          - high_n: Máximo de 'high' en las últimas BREAKOUT_BARS velas (sin incluir la vela actual)
          - low_n: Mínimo de 'low' en las últimas BREAKOUT_BARS velas (sin incluir la vela actual)
          - vol_avg: Promedio de 'volume' en las últimas VOL_LOOKBACK velas (sin incluir la vela actual)
          - vwap: VWAP calculado en una ventana de VWAP_PERIOD (sin incluir la vela actual)
        """
        df = df.copy()
        df['high_n'] = df['high'].rolling(BREAKOUT_BARS).max().shift(1)
        df['low_n'] = df['low'].rolling(BREAKOUT_BARS).min().shift(1)
        df['vol_avg'] = df['volume'].rolling(VOL_LOOKBACK).mean().shift(1)
        # Cálculo del VWAP:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = ((typical_price * df['volume']).rolling(VWAP_PERIOD).sum() /
                      df['volume'].rolling(VWAP_PERIOD).sum()).shift(1)
        return df

    def generate_signal(self, df):
        """
        Genera señales basadas en:
          - Señal Long (1) si:
              * El precio de cierre actual supera el máximo (high_n) de las últimas BREAKOUT_BARS velas (sin incluir la vela actual)
              * El volumen actual es mayor que el promedio de volumen (vol_avg)
              * El precio actual está por encima del VWAP
          - Señal Short (-1) si:
              * El precio de cierre actual es menor que el mínimo (low_n) de las últimas BREAKOUT_BARS velas (sin incluir la vela actual)
              * El volumen actual es mayor que el promedio de volumen (vol_avg)
              * El precio actual está por debajo del VWAP
          - Retorna 0 en caso contrario o si no hay suficientes datos.
        Además, imprime la información de los indicadores para depuración.
        """
        row = df.iloc[-1]
        if pd.isna(row['high_n']) or pd.isna(row['low_n']) or pd.isna(row['vol_avg']) or pd.isna(row['vwap']):
            print("[DEBUG] Indicadores incompletos en la última vela.")
            return 0

        current_close = row['close']
        recent_high = row['high_n']
        recent_low = row['low_n']
        current_vol = row['volume']
        avg_vol = row['vol_avg']
        vwap = row['vwap']

        # Imprime los valores de los indicadores
        print("[DEBUG] Indicadores simplificados en la última vela:")
        print(f"  Precio actual: {current_close}")
        print(f"  Maximo  : {recent_high}")
        print(f"  Minimo   : {recent_low}")
        print(f"  Volumen actual : {current_vol}")
        print(f"  Volumen promedio      : {avg_vol}")
        print(f"  VWAP         : {vwap}")

        # Condición para señal LONG
        if current_close > recent_high and current_vol > avg_vol and current_close > vwap:
            print("[DEBUG] Condición para LONG cumplida")
            return 1

        # Condición para señal SHORT
        if current_close < recent_low and current_vol > avg_vol and current_close < vwap:
            print("[DEBUG] Condición para SHORT cumplida")
            return -1

        print("[DEBUG] No se cumplen las condiciones para entrada.")
        return 0
