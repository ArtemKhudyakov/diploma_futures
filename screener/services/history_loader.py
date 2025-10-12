from pybit.unified_trading import HTTP
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class HistoryLoader:
    """
    Загрузчик исторических данных с Bybit
    """

    def __init__(self, testnet: bool = False):
        self.session = HTTP(testnet=testnet)
        self.testnet = testnet

    def get_historical_klines(self, symbol: str, category: str = "spot",
                              interval: int = 1, days: int = 7) -> List[Dict]:
        """
        Получение исторических данных за указанное количество дней
        interval: 1 (1 минута), 3, 5, 15, 30, 60, 120, 240, 360, 720, "D", "W"
        """
        try:
            # Вычисляем временной диапазон
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

            logger.info(f"Загрузка данных {symbol} за {days} дней...")

            all_klines = []
            current_start = start_time

            # Bybit ограничивает 1000 свечей за запрос, поэтому делаем несколько запросов
            while current_start < end_time:
                response = self.session.get_kline(
                    category=category,
                    symbol=symbol,
                    interval=interval,
                    start=current_start,
                    end=end_time,
                    limit=1000
                )

                if response['retCode'] == 0 and response['result']['list']:
                    klines = response['result']['list']
                    all_klines.extend(klines)

                    # Если получили меньше 1000 свечей - значит это последняя партия
                    if len(klines) < 1000:
                        break

                    # Сдвигаем start_time на последний timestamp + 1 минута
                    last_timestamp = int(klines[-1][0])
                    current_start = last_timestamp + 60000  # +1 минута в миллисекундах

                    # Небольшая пауза чтобы не превысить лимиты API
                    time.sleep(0.1)
                else:
                    logger.error(f"Ошибка получения данных: {response.get('retMsg', 'Unknown error')}")
                    break

            logger.info(f"Загружено {len(all_klines)} свечей для {symbol}")
            return all_klines

        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных {symbol}: {e}")
            return []

    def klines_to_prices(self, klines: List, price_type: str = "close") -> List[float]:
        """
        Преобразование свечных данных в список цен
        price_type: "open", "high", "low", "close"
        """
        price_index = {"open": 1, "high": 2, "low": 3, "close": 4}

        if not klines:
            return []

        idx = price_index.get(price_type, 4)  # по умолчанию close price
        return [float(kline[idx]) for kline in klines]