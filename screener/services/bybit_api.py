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

        # self.last_request_time = 0
        # self.min_request_interval = 0.3  # 300ms между запросами

        self.timeframes = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M'
        }

        logger.info(f"BybitAPI инициализирован (testnet: {testnet})")

    # def _rate_limit(self):
    #     """Ограничение частоты запросов"""
    #     current_time = time.time()
    #     time_since_last = current_time - self.last_request_time
    #     if time_since_last < self.min_request_interval:
    #         sleep_time = self.min_request_interval - time_since_last
    #         time.sleep(sleep_time)
    #     self.last_request_time = time.time()

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
        """
        # Ограничиваем частоту запросов
        # self._rate_limit()

        # Ограничиваем максимальное количество дней
        max_days = self._get_max_days_for_timeframe(timeframe)
        days = min(days, max_days)

        logger.info(f"Загрузка данных {symbol} за {days} дней (таймфрейм: {timeframe})")

        # time.sleep(0.5)

        timeframe_mapping = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M'
        }

        interval = timeframe_mapping.get(timeframe, '60')

        # РАССЧИТЫВАЕМ точное количество свечей
        candles_per_day = {
            '1m': 1440, '3m': 480, '5m': 288, '15m': 96, '30m': 48,
            '1h': 24, '2h': 12, '4h': 6, '6h': 4, '12h': 2,
            '1d': 1, '1w': 0.14, '1M': 0.03
        }

        total_candles_needed = int(candles_per_day.get(timeframe, 24) * days)
        total_candles_needed = min(total_candles_needed, 1000)  # Ограничение API

        logger.info(f"Загрузка {total_candles_needed} свечей {symbol} за {days} дней (таймфрейм: {timeframe})")

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

    def _get_max_days_for_timeframe(self, timeframe):
        """Максимальное количество дней для таймфрейма"""
        limits = {
            '1m': 1,  # 1 день максимум для 1m
            '5m': 2,  # 2 дня максимум для 5m
            '15m': 3,  # 3 дня максимум для 15m
            '30m': 5,  # 5 дней максимум для 30m
            '1h': 30,  # 30 дней максимум для 1h
            '4h': 60,  # 60 дней максимум для 4h
            '1d': 90,  # 90 дней максимум для 1d
        }
        return limits.get(timeframe, 7)

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