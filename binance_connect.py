import time
import requests
from urllib.parse import urlencode
import hmac
import hashlib

class BinanceHMACClient:
    def __init__(self, api_key, secret_key, base_url="https://api.binance.com"):
        """
        :param api_key: La API key que Binance te proporcionó.
        :param secret_key: La Secret Key que Binance te proporcionó.
        :param base_url: Endpoint principal de Binance (por defecto, el de producción).
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url

    def get_margin_account_info(self):
        endpoint = "/sapi/v1/margin/account"
        return self.send_signed_request("GET", endpoint)

    def get_symbol_price(self, symbol):
        endpoint = "/api/v3/ticker/price"
        params = {"symbol": symbol}
        response = requests.get(self.base_url + endpoint, params=params)
        if response.status_code == 200:
            price = float(response.json()['price'])
            return price
        else:
            print("Error al obtener precio del símbolo:", response.text)
            return None

    def get_timestamp(self):
        return int(time.time() * 1000)

    def sign_payload(self, payload: str) -> str:
        """
        Genera la firma HMAC-SHA256 del payload usando la secret key.
        Devuelve la firma en formato hexadecimal.
        """
        return hmac.new(self.secret_key.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()

    def send_signed_request(self, http_method, endpoint, params=None):
        """
        Envía una solicitud firmada a Binance usando HMAC-SHA256.
        """
        if params is None:
            params = {}
        # Agrega timestamp y recvWindow
        params['timestamp'] = self.get_timestamp()
        params['recvWindow'] = 5000

        # Generar el query string y la firma
        query_string = urlencode(params)
        signature = self.sign_payload(query_string)
        query_string += f"&signature={signature}"

        # Construir la URL completa
        url = self.base_url + endpoint + "?" + query_string

        headers = {
            "X-MBX-APIKEY": self.api_key
        }

        if http_method == "GET":
            r = requests.get(url, headers=headers)
        elif http_method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            r = requests.post(url, headers=headers)
        elif http_method == "DELETE":
            r = requests.delete(url, headers=headers)
        else:
            raise ValueError("Método HTTP no soportado.")

        if r.status_code != 200:
            print("Error en petición:", r.text)
            return None

        return r.json()

    def create_order(self, symbol, side, order_type, quantity):
        """
        Envía una orden de mercado en spot.
        """
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity
        }
        return self.send_signed_request("POST", endpoint, params)

    def create_margin_order(self, symbol, side, order_type, quantity, isIsolated="FALSE", sideEffectType="AUTO_REPAY"):
        """
        Envía una orden de mercado en margen usando el endpoint de margen.
        Parámetros adicionales como isIsolated y sideEffectType se pueden ajustar según la documentación de Binance.
        """
        endpoint = "/sapi/v1/margin/order"
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "isIsolated": isIsolated,
            "sideEffectType": sideEffectType
        }
        return self.send_signed_request("POST", endpoint, params)

    def get_account_info(self):
        """
        Obtiene la información de la cuenta (wallet) en spot.
        """
        endpoint = "/api/v3/account"
        return self.send_signed_request("GET", endpoint)
