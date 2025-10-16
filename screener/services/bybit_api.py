# from pybit.unified_trading import HTTP
# import logging
# from typing import Optional, Tuple, Dict, List
# import time
#
# logger = logging.getLogger(__name__)
#
# import os
#
#
# class BybitClient:
#     """Клиент для Bybit с поддержкой спота и фьючерсов"""
#
#     def __init__(self, testnet: bool = False, api_key: str = os.getenv('BYBIT_API_KEY'),
#                  api_secret: str = 'BYBIT_API_SECRET'):
#         self.session = HTTP(
#             testnet=testnet,
#             api_key=api_key,
#             api_secret=api_secret
#         )
#         self.testnet = testnet
#         self.mode = "TESTNET" if testnet else "MAINNET"
#         logger.info(f"BybitClient инициализирован в режиме: {self.mode}")
#
#     def get_price(self, symbol: str, category: str) -> Optional[float]:
#         """Получение цены для указанной категории"""
#         try:
#             response = self.session.get_tickers(
#                 category=category,
#                 symbol=symbol
#             )
#
#             if response['retCode'] == 0 and response['result']['list']:
#                 price = float(response['result']['list'][0]['lastPrice'])
#                 logger.debug(f"{self.mode} {symbol} {category}: ${price:.2f}")
#                 return price
#             else:
#                 logger.error(f"Ошибка API {category} {symbol}: {response['retMsg']}")
#
#         except Exception as e:
#             logger.error(f"Ошибка получения цены {symbol} {category}: {e}")
#
#         return None
#
#     def get_klines(self, symbol: str, category: str = "spot", interval: int = 60, limit: int = 1000) -> List[dict]:
#         """Получение исторических данных"""
#         try:
#             response = self.session.get_kline(
#                 category=category,
#                 symbol=symbol,
#                 interval=interval,
#                 limit=limit
#             )
#
#             if response['retCode'] == 0:
#                 klines = []
#                 for item in response['result']['list']:
#                     klines.append({
#                         'timestamp': int(item[0]),
#                         'open': float(item[1]),
#                         'high': float(item[2]),
#                         'low': float(item[3]),
#                         'close': float(item[4]),
#                         'volume': float(item[5]),
#                         'turnover': float(item[6]) if len(item) > 6 else 0
#                     })
#                 return klines
#
#         except Exception as e:
#             logger.error(f"Ошибка получения K-line {symbol}: {e}")
#
#         return []
#
#     def get_spot_prices(self) -> Dict[str, Optional[float]]:
#         """Получение спотовых цен"""
#         return {
#             'eth_spot': self.get_price("ETHUSDT", "spot"),
#             'btc_spot': self.get_price("BTCUSDT", "spot")
#         }
#
#     def get_futures_prices(self) -> Dict[str, Optional[float]]:
#         """Получение фьючерсных цен (linear)"""
#         return {
#             'eth_futures': self.get_price("ETHUSDT", "linear"),
#             'btc_futures': self.get_price("BTCUSDT", "linear")
#         }
#
#     def get_all_prices(self) -> Dict[str, Optional[float]]:
#         """Получение всех цен: спот и фьючерсы"""
#         spot_prices = self.get_spot_prices()
#         futures_prices = self.get_futures_prices()
#         return {**spot_prices, **futures_prices}
#
#     # @staticmethod
#     def calculate_basis(self, spot_price: float, futures_price: float) -> float:
#         """Расчет базиса (разница между фьючерсом и спотом)"""
#         if spot_price and futures_price:
#             return ((futures_price - spot_price) / spot_price) * 100
#         return 0.0
#
#
#
#
#
# if __name__ == "__main__":
#     def test_prices():
#         client = BybitClient(testnet=False)
#
#         print("💰 ПОЛУЧЕНИЕ СПОТОВЫХ И ФЬЮЧЕРСНЫХ ЦЕН")
#         print("=" * 60)
#
#         while True:
#             try:
#                 prices = client.get_all_prices()
#
#                 if all(prices.values()):
#                     # Расчет базиса
#                     eth_basis = client.calculate_basis(prices['eth_spot'], prices['eth_futures'])
#                     btc_basis = client.calculate_basis(prices['btc_spot'], prices['btc_futures'])
#
#                     print(f"[{time.strftime('%H:%M:%S')}] "
#                           f"ETH: Spot=${prices['eth_spot']:7.2f} | "
#                           f"Futures=${prices['eth_futures']:7.2f} | "
#                           f"Basis={eth_basis:+.3f}%")
#
#                     print(f"{' ':28}"
#                           f"BTC: Spot=${prices['btc_spot']:8.2f} | "
#                           f"Futures=${prices['btc_futures']:8.2f} | "
#                           f"Basis={btc_basis:+.3f}%")
#                     print("-" * 60)
#
#                 time.sleep(10)  # Обновление каждые 10 секунд для теста
#
#             except KeyboardInterrupt:
#                 print("\n⏹️ Тест остановлен")
#                 break
#     test_prices()


from pybit.unified_trading import HTTP
import logging
from typing import Optional, Dict, List
import time
import os

logger = logging.getLogger(__name__)


class BybitAPI:
    """Клиент для работы с Bybit API"""

    def __init__(self, testnet: bool = True, api_key: str = os.getenv('BYBIT_API_KEY'),
                 api_secret: str = os.getenv('BYBIT_API_SECRET')):
        self.session = HTTP(testnet=testnet, api_key=api_key, api_secret=api_secret)
        self.testnet = testnet
        self.mode = "TESTNET" if testnet else "MAINNET"
        logger.info(f"BybitAPI инициализирован (testnet: {testnet})")

        self.timeframes = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M'
        }

        logger.info(f"BybitAPI инициализирован (testnet: {testnet})")


    def get_current_price(self, symbol: str, category: str = "spot") -> Optional[float]:
        """
        Получение текущей цены
        symbol: "ETHUSDT", "BTCUSDT"
        category: "spot", "linear"
        """
        try:
            response = self.session.get_tickers(
                category=category,
                symbol=symbol
            )

            if response['retCode'] == 0 and response['result']['list']:
                price = float(response['result']['list'][0]['lastPrice'])
                logger.debug(f"Текущая цена {symbol} {category}: ${price:.2f}")
                return price

        except Exception as e:
            logger.error(f"Ошибка получения цены {symbol}: {e}")

        return None


    def get_klines(self, symbol: str, category: str = "spot",
                   interval: str = "60", limit: int = 200) -> List[Dict]:
        """
        Получение исторических свечных данных
        interval: "1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"
        limit: количество свечей (макс. 1000)
        """
        try:
            response = self.session.get_kline(
                category=category,
                symbol=symbol,
                interval=interval,
                limit=min(limit, 1000)
            )

            if response['retCode'] == 0:
                klines = response['result']['list']
                logger.info(f"Получено {len(klines)} свечей {symbol} {category} таймфрейм {interval}")
                return self._parse_klines(klines)
            else:
                logger.error(f"Ошибка API {symbol}: {response['retMsg']}")

        except Exception as e:
            logger.error(f"Ошибка получения свечей {symbol}: {e}")

        return []


    def _parse_klines(self, klines: List) -> List[Dict]:
        """Парсинг сырых свечных данных в удобный формат"""
        parsed = []
        for kline in klines:
            parsed.append({
                'timestamp': int(kline[0]),  # Время открытия свечи (ms)
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5]),
                'turnover': float(kline[6]) if len(kline) > 6 else 0
            })
        return parsed


    def get_all_current_prices(self) -> Dict[str, Optional[float]]:
        """
        Получение всех текущих цен одним запросом
        """
        return {
            'eth_spot': self.get_current_price("ETHUSDT", "spot"),
            'btc_spot': self.get_current_price("BTCUSDT", "spot"),
            'eth_futures': self.get_current_price("ETHUSDT", "linear"),
            'btc_futures': self.get_current_price("BTCUSDT", "linear")
        }

    def get_historical_data(self, symbol: str, category: str = "spot",
                            timeframe: str = '1h', days: int = 1) -> List[Dict]:
        """
        Получение исторических данных за несколько дней
        timeframe: '1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w', '1M'
        """
        # Правильный маппинг таймфреймов для Bybit API
        timeframe_mapping = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M'
        }

        interval = timeframe_mapping.get(timeframe, '60')  # по умолчанию 1 час

        # Определяем сколько свечей нужно
        intervals_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 1440, '1w': 10080, '1M': 43200
        }

        minutes_per_candle = intervals_minutes.get(timeframe, 60)
        total_candles_needed = (days * 24 * 60) // minutes_per_candle
        total_candles_needed = min(total_candles_needed, 1000)  # Ограничиваем 1000 свечей

        logger.info(f"Загрузка {total_candles_needed} свечей {symbol} {category} {timeframe} за {days} дней")

        # Получаем данные одним запросом
        klines = self.get_klines(symbol, category, interval, total_candles_needed)

        if klines:
            logger.info(f"Успешно загружено {len(klines)} свечей")
        else:
            logger.error(f"Не удалось загрузить данные для {symbol}")

        return klines


    def get_correct_prices(self) -> Dict[str, Optional[float]]:
        """
        Получение корректных цен с проверкой аномалий
        """
        prices = self.get_all_current_prices()

        # Проверяем на аномальные значения (testnet иногда выдает странные цены)
        if prices['btc_spot'] and prices['btc_spot'] > 200000:
            logger.warning(f"Подозрительная цена BTC: ${prices['btc_spot']:.2f}")
            # Пробуем получить еще раз
            prices['btc_spot'] = self.get_current_price("BTCUSDT", "spot")
            prices['btc_futures'] = self.get_current_price("BTCUSDT", "linear")

        if prices['eth_spot'] and prices['eth_spot'] > 10000:
            logger.warning(f"Подозрительная цена ETH: ${prices['eth_spot']:.2f}")
            prices['eth_spot'] = self.get_current_price("ETHUSDT", "spot")
            prices['eth_futures'] = self.get_current_price("ETHUSDT", "linear")

        return prices


if __name__ == "__main__":
    def test_prices():
        client = BybitAPI(testnet=False)

        print("💰 ПОЛУЧЕНИЕ СПОТОВЫХ И ФЬЮЧЕРСНЫХ ЦЕН")
        print("=" * 60)

        while True:
            try:
                prices = client.get_all_current_prices()

                if all(prices.values()):

                    print(f"[{time.strftime('%H:%M:%S')}] "
                          f"ETH: Spot=${prices['eth_spot']:7.2f} | "
                          f"Futures=${prices['eth_futures']:7.2f} | ")

                    print(f"{' ':28}"
                          f"BTC: Spot=${prices['btc_spot']:8.2f} | "
                          f"Futures=${prices['btc_futures']:8.2f} | ")
                    print("-" * 60)

                time.sleep(10)  # Обновление каждые 10 секунд для теста

            except KeyboardInterrupt:
                print("\n⏹️ Тест остановлен")
                break
    test_prices()