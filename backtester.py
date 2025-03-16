# backtester.py
import pandas as pd
import time
from db_manager import DBManager
from strategy import ScalpingStrategy
from config import (
    SYMBOL, 
    INITIAL_CAPITAL, FEE_RATE,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    MAX_HOLD_MINUTES
)

class Backtester:
    def __init__(self, strategy=None):
        self.db = DBManager()
        self.strategy = strategy if strategy else ScalpingStrategy()
        self.initial_capital = INITIAL_CAPITAL
        self.fee_rate = FEE_RATE
        self.stop_loss_pct = STOP_LOSS_PCT
        self.take_profit_pct = TAKE_PROFIT_PCT
        self.max_hold_bars = MAX_HOLD_MINUTES  # si timeframe=1m, equivalen a 30 velas

    def run_backtest(self):
        df = self.db.fetch_ohlcv_data()  # leemos toda la tabla ohlcv
        if df.empty:
            print("No hay datos en ohlcv.")
            return self.initial_capital, []

        df = self.strategy.compute_indicators(df)

        capital = self.initial_capital
        position_open = False
        side = None
        open_price = 0
        open_index = 0
        quantity = 0
        open_time_str = None

        trades_summary = []

        for i in range(len(df)):
            if i < 1:
                continue

            row = df.iloc[i]
            current_time = row['timestamp']
            current_price = row['close']

            signal = self.strategy.generate_signal(df.iloc[:i+1])

            if not position_open:
                # Apertura
                if signal == 1:
                    side = 'long'
                    open_price = current_price
                    open_index = i
                    quantity = (capital * 0.1) / current_price
                    position_open = True
                    open_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

                elif signal == -1:
                    side = 'short'
                    open_price = current_price
                    open_index = i
                    quantity = (capital * 0.1) / current_price
                    position_open = True
                    open_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

            else:
                # Checkear SL, TP, o max_hold_bars
                bars_held = i - open_index
                stop_price = open_price * (1 - self.stop_loss_pct)
                take_price = open_price * (1 + self.take_profit_pct)
                close_position = False
                reason = None

                if side == 'long':
                    # SL
                    if current_price <= stop_price:
                        reason = "StopLoss"
                        close_position = True
                    # TP
                    elif current_price >= take_price:
                        reason = "TakeProfit"
                        close_position = True
                    # max tiempo
                    elif bars_held >= self.max_hold_bars:
                        reason = "TimeOut"
                        close_position = True

                    if close_position:
                        close_price = current_price
                        pnl_gross = (close_price - open_price) * quantity
                        fee = abs(pnl_gross) * self.fee_rate
                        pnl_net = pnl_gross - fee
                        capital += pnl_net

                        close_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

                        self.db.insert_trade(
                            symbol=SYMBOL,
                            strategy='Scalping_Breakout',
                            side='long',
                            quantity=quantity,
                            open_time=open_time_str,
                            open_price=open_price,
                            close_time=close_time_str,
                            close_price=close_price,
                            fees=fee,
                            pnl=pnl_net,
                            reason=reason
                        )

                        trades_summary.append({
                            'open_time': open_time_str,
                            'close_time': close_time_str,
                            'side': side,
                            'pnl': pnl_net,
                            'reason': reason
                        })

                        position_open = False

                elif side == 'short':
                    inv_stop = open_price * (1 + self.stop_loss_pct)
                    inv_take = open_price * (1 - self.take_profit_pct)
                    if current_price >= inv_stop:
                        reason = "StopLoss"
                        close_position = True
                    elif current_price <= inv_take:
                        reason = "TakeProfit"
                        close_position = True
                    elif bars_held >= self.max_hold_bars:
                        reason = "TimeOut"
                        close_position = True

                    if close_position:
                        close_price = current_price
                        pnl_gross = (open_price - close_price) * quantity
                        fee = abs(pnl_gross) * self.fee_rate
                        pnl_net = pnl_gross - fee
                        capital += pnl_net

                        close_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

                        self.db.insert_trade(
                            symbol=SYMBOL,
                            strategy='Scalping_Breakout',
                            side='short',
                            quantity=quantity,
                            open_time=open_time_str,
                            open_price=open_price,
                            close_time=close_time_str,
                            close_price=close_price,
                            fees=fee,
                            pnl=pnl_net,
                            reason=reason
                        )

                        trades_summary.append({
                            'open_time': open_time_str,
                            'close_time': close_time_str,
                            'side': side,
                            'pnl': pnl_net,
                            'reason': reason
                        })

                        position_open = False

        return capital, trades_summary
