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
    order_mgr = OrderManager()  # OrderManager usa ahora BinanceHMACClient internamente

    print("[DEBUG] Obteniendo datos históricos iniciales...")
    df_history = fetcher.fetch_ohlcv(limit=100)
    df_history = strat.compute_indicators(df_history)
    print(f"[DEBUG] DataFrame inicial con {len(df_history)} filas.")

    # Variables de posición
    open_position = False
    side = None
    open_time = None
    open_price = 0
    quantity = 0

    # CONTROL DE RIESGO
    daily_pnl = 0.0       
    daily_loss_limit = -5.0  

    start_time = time.time()  # para controlar la duración de la prueba

    while True:
        try:
            elapsed_time = time.time() - start_time
            print(f"[DEBUG] Ciclo activo. Tiempo transcurrido: {elapsed_time:.0f} segundos.")

            if daily_pnl <= daily_loss_limit:
                print(f"[RISK ALERT] Pérdida diaria {daily_pnl} <= {daily_loss_limit}. Se detiene apertura de nuevas posiciones.")

            # Obtención de la vela más reciente
            candle = fetcher.fetch_latest_candle()
            if candle:
                # Actualizar el DataFrame con la nueva vela
                nueva_fila = pd.DataFrame([{
                    'timestamp': candle['timestamp'],
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume']
                }])
                df_history = pd.concat([df_history, nueva_fila], ignore_index=True)
                df_indicadores = strat.compute_indicators(df_history)
                
                # Obtener libro de órdenes para análisis de microestructura
                order_book = fetcher.fetch_order_book()
                
                # Generar la señal utilizando los indicadores técnicos y el order flow
                signal = strat.generate_signal(df_indicadores, order_book)
                
                print(f"[DEBUG] DataFrame actualizado. Total filas: {len(df_history)}")
                print(f"[DEBUG] Señal generada: {signal}")
                
                current_price = candle['close']
                current_time = candle['timestamp']
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')


                # Apertura de posición
                if not open_position and daily_pnl > daily_loss_limit:
                    if signal == 1:
                        side = 'long'
                        open_time = current_time
                        open_price = current_price
                        quantity = order_mgr.calculate_position_size(current_price)
                        order_mgr.create_market_order('buy', quantity)
                        open_position = True
                        print(f"[OPEN LONG] time={current_time_str}, price={open_price}, qty={quantity}")
                    elif signal == -1:
                        side = 'short'
                        open_time = current_time
                        open_price = current_price
                        quantity = order_mgr.calculate_position_size(current_price)
                        order_mgr.create_market_order('sell', quantity)
                        open_position = True
                        print(f"[OPEN SHORT] time={current_time_str}, price={open_price}, qty={quantity}")
                else:
                    if open_time:
                        elapsed_minutes = (current_time - open_time).total_seconds() / 60.0
                    else:
                        elapsed_minutes = 0
                    print(f"[DEBUG] Posición abierta hace {elapsed_minutes:.2f} minutos.")
                    close_position = False
                    reason = None

                    if side == 'long':
                        stop_price = open_price * (1 - STOP_LOSS_PCT)
                        take_price = open_price * (1 + TAKE_PROFIT_PCT)
                        if current_price <= stop_price:
                            reason = "StopLoss"
                            close_position = True
                        elif current_price >= take_price:
                            reason = "TakeProfit"
                            close_position = True
                        elif elapsed_minutes >= MAX_HOLD_MINUTES:
                            reason = "TimeOut"
                            close_position = True

                        if close_position:
                            order_mgr.create_market_order('sell', quantity)
                            close_price = current_price
                            pnl_gross = (close_price - open_price) * quantity
                            fee = abs(pnl_gross) * 0.0004  
                            pnl_net = pnl_gross - fee
                            db.insert_trade(
                                symbol=SYMBOL,
                                strategy='Scalping_Breakout',
                                side='long',
                                quantity=quantity,
                                open_time=open_time.strftime('%Y-%m-%d %H:%M:%S'),
                                open_price=open_price,
                                close_time=current_time_str,
                                close_price=close_price,
                                fees=fee,
                                pnl=pnl_net,
                                reason=reason
                            )
                            open_position = False
                            print(f"[CLOSE LONG] time={current_time_str}, price={close_price}, PnL={pnl_net:.2f}, reason={reason}")

                    elif side == 'short':
                        inv_stop = open_price * (1 + STOP_LOSS_PCT)
                        inv_take = open_price * (1 - TAKE_PROFIT_PCT)
                        if current_price >= inv_stop:
                            reason = "StopLoss"
                            close_position = True
                        elif current_price <= inv_take:
                            reason = "TakeProfit"
                            close_position = True
                        elif elapsed_minutes >= MAX_HOLD_MINUTES:
                            reason = "TimeOut"
                            close_position = True

                        if close_position:
                            order_mgr.create_market_order('buy', quantity)
                            close_price = current_price
                            pnl_gross = (open_price - close_price) * quantity
                            fee = abs(pnl_gross) * 0.0004  
                            pnl_net = pnl_gross - fee
                            db.insert_trade(
                                symbol=SYMBOL,
                                strategy='Scalping_Breakout',
                                side='short',
                                quantity=quantity,
                                open_time=open_time.strftime('%Y-%m-%d %H:%M:%S'),
                                open_price=open_price,
                                close_time=current_time_str,
                                close_price=close_price,
                                fees=fee,
                                pnl=pnl_net,
                                reason=reason
                            )
                            open_position = False
                            print(f"[CLOSE SHORT] time={current_time_str}, price={close_price}, PnL={pnl_net:.2f}, reason={reason}")
            else:
                print("[DEBUG] No se recibió vela nueva.")

            print("[DEBUG] Durmiendo 60 segundos hasta la próxima iteración...")
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
