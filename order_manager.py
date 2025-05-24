# order_manager.py
from config import API_KEY, SECRET_KEY, SYMBOL, INVESTMENT_AMOUNT, ALLOW_CROSS_MARGIN
import numpy as np
from binance_connect import BinanceHMACClient
import math

class OrderManager:
    def __init__(self):
        self.client = BinanceHMACClient(api_key=API_KEY, secret_key=SECRET_KEY)

    def calculate_position_size(self, current_price, side='long'):
        usd_to_invest = 5.0  # <--- ahora mínimo 5 USD para LONG y SHORT

        qty = int(usd_to_invest / current_price)

        # Binance exige mínimo cantidad equivalente a ~5 USDT por trade
        qty = max(qty, int(np.ceil(5.0 / current_price)))

        print(f"[DEBUG] SIDE: {side}, USD to Invest: {usd_to_invest}, Calculated Qty: {qty}")

        return qty


    def create_market_order(self, side, quantity):
        symbol = SYMBOL.replace("/", "")
        base_asset, quote_asset = SYMBOL.split('/')

        if side.lower() in ["buy", "long"]:
            binance_side = "BUY"
            return self.client.create_order(symbol, binance_side, "MARKET", quantity)

        elif side.lower() in ["sell", "short"]:
            binance_side = "SELL"

            # Verifica claramente saldo spot primero
            account_info_spot = self.client.get_account_info()
            spot_balance = next((float(b["free"]) for b in account_info_spot.get("balances", [])
                                 if b["asset"] == base_asset), 0.0)

            if spot_balance >= quantity:
                print("[INFO] Usando saldo Spot suficiente para vender.")
                return self.client.create_order(symbol, binance_side, "MARKET", quantity)

            elif ALLOW_CROSS_MARGIN:
                print("[INFO] Intentando Cross Margin por saldo spot insuficiente.")

                price = self.client.get_symbol_price(symbol)
                if price is None:
                    print("[ERROR] No se obtuvo el precio actual del símbolo.")
                    return None

                required_margin = quantity * price
                margin_info = self.client.get_margin_account_info()
                margin_balance_usdt = next((float(asset["free"]) for asset in margin_info.get("userAssets", [])
                                            if asset["asset"] == quote_asset), 0.0)

                print(f"[DEBUG] Margen disponible (USDT): {margin_balance_usdt}, Margen requerido: {required_margin:.2f} USDT")

                if margin_balance_usdt >= required_margin:
                    return self.client.create_margin_order(symbol, binance_side, "MARKET", quantity, isIsolated="FALSE")
                else:
                    print(f"[ERROR] Margen insuficiente: disponible {margin_balance_usdt} USDT, necesario {required_margin:.2f} USDT.")
                    return None

            else:
                print("[ERROR] Cross Margin desactivado y saldo spot insuficiente.")
                return None

        else:
            raise ValueError(f"Lado de orden inválido: {side}")