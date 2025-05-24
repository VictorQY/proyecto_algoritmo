# main.py
import argparse
import time
import pandas as pd
import datetime

from db_manager import DBManager
from backtester import Backtester
from data_fetcher import DataFetcher
from strategy import ScalpingStrategy
from order_manager import OrderManager
# Importa el cliente HMAC en lugar del RSA
from binance_connect import BinanceHMACClient

from config import (
    DB_NAME,
    SYMBOL, TIMEFRAME,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    MAX_HOLD_MINUTES
)

def run_backtest():
    print("=== Iniciando BACKTEST (Breakout + 30min max hold) ===")
    backtester = Backtester(strategy=ScalpingStrategy())
    final_capital, trades_summary = backtester.run_backtest()
    print("Capital final:", final_capital)
    print("Número de trades:", len(trades_summary))
    if trades_summary:
        print("=== Últimos 5 trades ===")
        for t in trades_summary[-5:]:
            print(t)

def run_live_trading():
    print("=== Iniciando LIVE TRADING con control de riesgo ===")

    db = DBManager(DB_NAME)
    fetcher = DataFetcher()
    strat = ScalpingStrategy()
    order_mgr = OrderManager()

    print("[DEBUG] Obteniendo datos históricos iniciales...")
    df_1m = fetcher.fetch_ohlcv(timeframe='1m', limit=100)
    df_5m = fetcher.fetch_ohlcv(timeframe='5m', limit=100)
    df_15m = fetcher.fetch_ohlcv(timeframe='15m', limit=100)

    open_position = False
    side = None
    open_time = None
    open_price = 0
    quantity = 0
    stop_loss_price = 0
    take_profit_price = 0

    daily_pnl = 0.0       
    daily_loss_limit = -5.0  

    start_time = time.time()

    while True:
        try:
            elapsed_time = time.time() - start_time
            print(f"[DEBUG] Ciclo activo. Tiempo transcurrido: {elapsed_time:.0f} segundos.")

            if daily_pnl <= daily_loss_limit:
                print(f"[RISK ALERT] Pérdida diaria {daily_pnl} <= {daily_loss_limit}. No se abrirán nuevas posiciones.")
                time.sleep(60)
                continue

            candle_1m = fetcher.fetch_latest_candle(timeframe='1m')
            candle_5m = fetcher.fetch_latest_candle(timeframe='5m')
            candle_15m = fetcher.fetch_latest_candle(timeframe='15m')

            if candle_1m and candle_5m and candle_15m:
                df_1m = pd.concat([df_1m, pd.DataFrame([candle_1m])], ignore_index=True)
                df_5m = pd.concat([df_5m, pd.DataFrame([candle_5m])], ignore_index=True)
                df_15m = pd.concat([df_15m, pd.DataFrame([candle_15m])], ignore_index=True)

                signal, sl_pct, tp_pct = strat.generate_signal(df_1m, df_5m, df_15m)

                current_price = candle_1m['close']
                current_time = candle_1m['timestamp']
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

                if not open_position:
                    if signal == 1:
                        side = 'long'
                        open_time = current_time
                        open_price = current_price
                        quantity = order_mgr.calculate_position_size(current_price, side=side)
                        stop_loss_price = open_price * (1 - sl_pct)
                        take_profit_price = open_price * (1 + tp_pct)

                        order_response = order_mgr.create_market_order('buy', quantity)

                        if order_response is not None and 'orderId' in order_response:
                            open_position = True
                            side = 'long'
                            open_time = current_time
                            open_price = current_price
                            print(f"[OPEN LONG] time={current_time_str}, price={open_price}, qty={quantity}, SL={stop_loss_price}, TP={take_profit_price}")
                        else:
                            open_position = False
                            print("[ERROR] No se pudo abrir LONG, orden rechazada.")


                    elif signal == -1:
                        side = 'short'
                        open_time = current_time
                        open_price = current_price
                        quantity = order_mgr.calculate_position_size(current_price, side=side)
                        stop_loss_price = open_price * (1 + sl_pct)
                        take_profit_price = open_price * (1 - tp_pct)

                        order_response = order_mgr.create_market_order('sell', quantity)

                        if order_response is not None and 'orderId' in order_response:
                            open_position = True
                            side = 'short'
                            open_time = current_time
                            open_price = current_price
                            print(f"[OPEN SHORT] time={current_time_str}, price={open_price}, qty={quantity}, SL={stop_loss_price}, TP={take_profit_price}")
                        else:
                            open_position = False
                            print("[ERROR] No se pudo abrir SHORT, orden rechazada.")

                else:
                    elapsed_minutes = (current_time - open_time).total_seconds() / 60.0
                    close_position = False
                    reason = None

                    if side == 'long':
                        if current_price <= stop_loss_price:
                            reason = "StopLoss"
                            close_position = True
                        elif current_price >= take_profit_price:
                            reason = "TakeProfit"
                            close_position = True
                        elif elapsed_minutes >= MAX_HOLD_MINUTES:
                            reason = "TimeOut"
                            close_position = True

                        if close_position:
                            order_mgr.create_market_order('sell', quantity)
                            pnl_gross = (current_price - open_price) * quantity
                            fee = abs(pnl_gross) * 0.0004
                            pnl_net = pnl_gross - fee

                    elif side == 'short':
                        if current_price >= stop_loss_price:
                            reason = "StopLoss"
                            close_position = True
                        elif current_price <= take_profit_price:
                            reason = "TakeProfit"
                            close_position = True
                        elif elapsed_minutes >= MAX_HOLD_MINUTES:
                            reason = "TimeOut"
                            close_position = True

                        if close_position:
                            order_mgr.create_market_order('buy', quantity)
                            pnl_gross = (open_price - current_price) * quantity
                            fee = abs(pnl_gross) * 0.0004
                            pnl_net = pnl_gross - fee

                    if close_position:
                        db.insert_trade(
                            symbol=SYMBOL,
                            strategy='Scalping_OpenAI',
                            side=side,
                            quantity=quantity,
                            open_time=open_time.strftime('%Y-%m-%d %H:%M:%S'),
                            open_price=open_price,
                            close_time=current_time_str,
                            close_price=current_price,
                            fees=fee,
                            pnl=pnl_net,
                            reason=reason
                        )
                        open_position = False
                        print(f"[CLOSE {side.upper()}] time={current_time_str}, price={current_price}, PnL={pnl_net:.2f}, reason={reason}")

            else:
                print("[DEBUG] No se recibió vela nueva.")

            time.sleep(60)

        except Exception as e:
            print(f"Error en el loop principal: {e}")
            time.sleep(10)



def main():
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['backtest','live'], default='backtest')
    args = parser.parse_args()

    if args.mode == 'backtest':
        run_backtest()
    elif args.mode == 'live':
        run_live_trading()
    else:
        print("Modo inválido. Usa --mode backtest o --mode live.")

if __name__ == "__main__":
    main()
