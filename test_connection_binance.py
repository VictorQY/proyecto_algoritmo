# test_wallet.py
from config import API_KEY, SECRET_KEY
from binance_connect import BinanceHMACClient

def test_wallet():
    client = BinanceHMACClient(api_key=API_KEY, secret_key=SECRET_KEY)
    wallet_info = client.get_account_info()
    if wallet_info is not None:
        print("Información de tu Wallet en Binance:")
        print(wallet_info)
    else:
        print("No se pudo obtener la información de la wallet.")

if __name__ == "__main__":
    test_wallet()
