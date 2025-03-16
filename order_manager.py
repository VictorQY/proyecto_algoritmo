# order_manager.py
from config import API_KEY, SECRET_KEY, SYMBOL, INVESTMENT_AMOUNT
from binance_connect import BinanceHMACClient
import math

class OrderManager:
    def __init__(self):
        self.client = BinanceHMACClient(api_key=API_KEY, secret_key=SECRET_KEY)

    def calculate_position_size(self, current_price, usd_to_invest=INVESTMENT_AMOUNT):
        qty_float = usd_to_invest / current_price
        qty = round(qty_float, 2)
        return qty

    def create_market_order(self, side, quantity):
        if side.lower() in ["buy", "long"]:
            binance_side = "BUY"
            symbol = SYMBOL.replace("/", "")
            order_response = self.client.create_order(symbol, binance_side, "MARKET", quantity)
            if order_response is None:
                print("Error al enviar la orden.")
            else:
                print("Orden enviada:", order_response)
            return order_response

        elif side.lower() in ["sell", "short"]:
            binance_side = "SELL"
            symbol = SYMBOL.replace("/", "")
            base_asset = SYMBOL.split('/')[0]
            account_info = self.client.get_account_info()
            spot_balance = 0.0
            if account_info and "balances" in account_info:
                for b in account_info["balances"]:
                    if b["asset"] == base_asset:
                        spot_balance = float(b["free"])
                        break

            if spot_balance < quantity:
                print(f"[INFO] Saldo spot insuficiente ({spot_balance} {base_asset}), usando orden de margen.")
                order_response = self.client.create_margin_order(symbol, binance_side, "MARKET", quantity)
            else:
                order_response = self.client.create_order(symbol, binance_side, "MARKET", quantity)

            if order_response is None:
                print("Error al enviar la orden.")
            else:
                print("Orden enviada:", order_response)
            return order_response

        else:
            raise ValueError(f"Lado de orden inválido: {side}")
