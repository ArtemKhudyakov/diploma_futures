from pybit.unified_trading import HTTP
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

import os


class BybitClient:
    """Клиент для Bybit с использованием pybit"""

    def __init__(self, testnet: bool = False, api_key: str = os.getenv('BYBIT_API_KEY'),
                 api_secret: str = 'BYBIT_API_SECRET'):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        self.testnet = testnet

    def get_current_price(self, symbol: str, category: str = "spot") -> Optional[float]:
        """Получение текущей цены"""
        try:
            response = self.session.get_tickers(
                category=category,
                symbol=symbol
            )

            if response['retCode'] == 0 and response['result']['list']:
                return float(response['result']['list'][0]['lastPrice'])

        except Exception as e:
            logger.error(f"Ошибка получения цены {symbol}: {e}")

        return None

    def get_klines(self, symbol: str, category: str = "spot", interval: int = 60, limit: int = 1000) -> List[dict]:
        """Получение исторических данных"""
        try:
            response = self.session.get_kline(
                category=category,
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            if response['retCode'] == 0:
                klines = []
                for item in response['result']['list']:
                    klines.append({
                        'timestamp': int(item[0]),
                        'open': float(item[1]),
                        'high': float(item[2]),
                        'low': float(item[3]),
                        'close': float(item[4]),
                        'volume': float(item[5]),
                        'turnover': float(item[6]) if len(item) > 6 else 0
                    })
                return klines

        except Exception as e:
            logger.error(f"Ошибка получения K-line {symbol}: {e}")

        return []

    def get_eth_btc_prices(self) -> Tuple[Optional[float], Optional[float]]:
        """Получение текущих цен ETH и BTC"""
        eth_price = self.get_current_price("ETHUSDT", "linear")
        btc_price = self.get_current_price("BTCUSDT", "linear")
        return eth_price, btc_price


# Пример использования
if __name__ == "__main__":
    # Без API ключей - для получения цен
    client = BybitClient(testnet=False)

    eth, btc = client.get_eth_btc_prices()
    print(f"ETH: ${eth}, BTC: ${btc}")

    # Получение исторических данных
    klines = client.get_klines("ETHUSDT", "linear", interval=60, limit=100)
    print(f"Получено {len(klines)} свечей")
