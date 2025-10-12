from pybit.unified_trading import HTTP
import logging
from typing import Optional, Tuple, Dict, List
import time

logger = logging.getLogger(__name__)

import os


class BybitClient:
    """Клиент для Bybit с поддержкой спота и фьючерсов"""

    def __init__(self, testnet: bool = False, api_key: str = os.getenv('BYBIT_API_KEY'),
                 api_secret: str = 'BYBIT_API_SECRET'):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        self.testnet = testnet
        self.mode = "TESTNET" if testnet else "MAINNET"
        logger.info(f"BybitClient инициализирован в режиме: {self.mode}")

    def get_price(self, symbol: str, category: str) -> Optional[float]:
        """Получение цены для указанной категории"""
        try:
            response = self.session.get_tickers(
                category=category,
                symbol=symbol
            )

            if response['retCode'] == 0 and response['result']['list']:
                price = float(response['result']['list'][0]['lastPrice'])
                logger.debug(f"{self.mode} {symbol} {category}: ${price:.2f}")
                return price
            else:
                logger.error(f"Ошибка API {category} {symbol}: {response['retMsg']}")

        except Exception as e:
            logger.error(f"Ошибка получения цены {symbol} {category}: {e}")

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

    def get_spot_prices(self) -> Dict[str, Optional[float]]:
        """Получение спотовых цен"""
        return {
            'eth_spot': self.get_price("ETHUSDT", "spot"),
            'btc_spot': self.get_price("BTCUSDT", "spot")
        }

    def get_futures_prices(self) -> Dict[str, Optional[float]]:
        """Получение фьючерсных цен (linear)"""
        return {
            'eth_futures': self.get_price("ETHUSDT", "linear"),
            'btc_futures': self.get_price("BTCUSDT", "linear")
        }

    def get_all_prices(self) -> Dict[str, Optional[float]]:
        """Получение всех цен: спот и фьючерсы"""
        spot_prices = self.get_spot_prices()
        futures_prices = self.get_futures_prices()
        return {**spot_prices, **futures_prices}

    # @staticmethod
    def calculate_basis(self, spot_price: float, futures_price: float) -> float:
        """Расчет базиса (разница между фьючерсом и спотом)"""
        if spot_price and futures_price:
            return ((futures_price - spot_price) / spot_price) * 100
        return 0.0





if __name__ == "__main__":
    def test_prices():
        client = BybitClient(testnet=False)

        print("💰 ПОЛУЧЕНИЕ СПОТОВЫХ И ФЬЮЧЕРСНЫХ ЦЕН")
        print("=" * 60)

        while True:
            try:
                prices = client.get_all_prices()

                if all(prices.values()):
                    # Расчет базиса
                    eth_basis = client.calculate_basis(prices['eth_spot'], prices['eth_futures'])
                    btc_basis = client.calculate_basis(prices['btc_spot'], prices['btc_futures'])

                    print(f"[{time.strftime('%H:%M:%S')}] "
                          f"ETH: Spot=${prices['eth_spot']:7.2f} | "
                          f"Futures=${prices['eth_futures']:7.2f} | "
                          f"Basis={eth_basis:+.3f}%")

                    print(f"{' ':28}"
                          f"BTC: Spot=${prices['btc_spot']:8.2f} | "
                          f"Futures=${prices['btc_futures']:8.2f} | "
                          f"Basis={btc_basis:+.3f}%")
                    print("-" * 60)

                time.sleep(10)  # Обновление каждые 10 секунд для теста

            except KeyboardInterrupt:
                print("\n⏹️ Тест остановлен")
                break
    test_prices()
