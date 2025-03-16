# db_manager.py
import sqlite3
import pandas as pd
from config import DB_NAME

class DBManager:
    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        create_ohlcv_table = """
        CREATE TABLE IF NOT EXISTS ohlcv (
            ohlcv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL
        );
        """
        create_trades_table = """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            strategy TEXT,
            side TEXT NOT NULL,      -- 'long'/'short'
            quantity REAL NOT NULL,
            open_time TEXT NOT NULL,
            open_price REAL NOT NULL,
            close_time TEXT,
            close_price REAL,
            fees REAL,
            pnl REAL,
            reason TEXT,
            notes TEXT
        );
        """
        self.conn.execute(create_ohlcv_table)
        self.conn.execute(create_trades_table)
        self.conn.commit()

    def insert_ohlcv(self, data_rows):
        """
        Inserta varias filas en 'ohlcv'.
        data_rows: lista de tuplas (timestamp, open, high, low, close, volume)
        """
        query = """
        INSERT INTO ohlcv (timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.executemany(query, data_rows)
        self.conn.commit()

    def fetch_ohlcv_data(self, limit=None):
        """
        Retorna en un DataFrame los datos de 'ohlcv'. Si limit se especifica,
        trae solo esa cantidad de filas (ordenadas ASC).
        """
        if limit:
            query = "SELECT timestamp, open, high, low, close, volume FROM ohlcv ORDER BY ohlcv_id ASC LIMIT ?"
            rows = self.conn.execute(query, (limit,)).fetchall()
        else:
            query = "SELECT timestamp, open, high, low, close, volume FROM ohlcv ORDER BY ohlcv_id ASC"
            rows = self.conn.execute(query).fetchall()

        df = pd.DataFrame(rows, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def insert_trade(self, symbol, strategy, side, quantity,
                     open_time, open_price,
                     close_time, close_price,
                     fees, pnl, reason, notes=None):
        """
        Inserta un registro en la tabla 'trades'.
        """
        sql = """
        INSERT INTO trades 
        (symbol, strategy, side, quantity, open_time, open_price,
         close_time, close_price, fees, pnl, reason, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(sql, (
            symbol, strategy, side, quantity,
            open_time, open_price,
            close_time, close_price,
            fees, pnl, reason, notes
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()
