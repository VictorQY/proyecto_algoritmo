# data_fetcher.py actualizado claramente
import ccxt
import pandas as pd
from config import SYMBOL

class DataFetcher:
    def __init__(self):
        self.exchange = ccxt.binance({'enableRateLimit': True})

    def fetch_ohlcv(self, timeframe='1m', limit=200):
        ohlcvs = self.exchange.fetch_ohlcv(SYMBOL, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcvs, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def fetch_latest_candle(self, timeframe='1m'):
        ohlcvs = self.exchange.fetch_ohlcv(SYMBOL, timeframe=timeframe, limit=1)
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

    def fetch_order_book(self):
        return self.exchange.fetch_order_book(SYMBOL)
