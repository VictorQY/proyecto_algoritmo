# data_fetcher.py
import ccxt
import pandas as pd
from config import SYMBOL, TIMEFRAME

class DataFetcher:
    def __init__(self):
        # Para datos públicos, no es necesario pasar API key ni secret
        self.exchange = ccxt.binance({
            'enableRateLimit': True
        })

    def fetch_ohlcv(self, limit=200):
        ohlcvs = self.exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=limit)
        df = pd.DataFrame(ohlcvs, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def fetch_latest_candle(self):
        ohlcvs = self.exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=1)
        if not ohlcvs:
            return None
        ts, o, h, l, c, v = ohlcvs[0]
        return {
            'timestamp': pd.to_datetime(ts, unit='ms'),
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'volume': v
        }
    
    # En data_fetcher.py
    def fetch_order_book(self):
        order_book = self.exchange.fetch_order_book(SYMBOL)
        return order_book

