import logging
from datetime import datetime, timedelta
from django.utils import timezone
from screener.models import PriceHistory, AnalysisSession
from screener.services.history_loader import HistoryLoader

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Сервис для работы с историческими данными в БД
    """

    def __init__(self, testnet: bool = False):
        self.loader = HistoryLoader(testnet=testnet)

    def load_and_save_history(self, days: int = 7, symbols: list = None):
        """
        Загрузка и сохранение исторических данных в БД
        """
        if symbols is None:
            symbols = ['ETHUSDT', 'BTCUSDT']

        categories = ['spot', 'linear']

        # Создаем сессию анализа
        session = AnalysisSession.objects.create(
            name=f"History Load {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            start_date=timezone.now() - timedelta(days=days),
            end_date=timezone.now()
        )

        total_points = 0

        for symbol in symbols:
            for category in categories:
                logger.info(f"Загрузка {symbol} {category} за {days} дней...")

                # Получаем исторические данные
                klines = self.loader.get_historical_klines(
                    symbol=symbol,
                    category=category,
                    days=days
                )

                # Сохраняем в БД
                saved_count = self._save_klines_to_db(klines, symbol, category)
                total_points += saved_count

                logger.info(f"Сохранено {saved_count} записей для {symbol} {category}")

        # Обновляем счетчик в сессии
        session.data_points_count = total_points
        session.save()

        logger.info(f"Загрузка завершена. Всего сохранено {total_points} точек данных")
        return total_points

    def _save_klines_to_db(self, klines: list, symbol: str, category: str) -> int:
        """
        Сохранение свечных данных в БД
        """
        saved_count = 0

        for kline in klines:
            try:
                # Парсим данные свечи
                # Формат: [timestamp, open, high, low, close, volume, turnover]
                timestamp = datetime.fromtimestamp(int(kline[0]) / 1000)
                open_price = float(kline[1])
                high_price = float(kline[2])
                low_price = float(kline[3])
                close_price = float(kline[4])
                volume = float(kline[5])

                # Создаем или обновляем запись
                PriceHistory.objects.update_or_create(
                    symbol=symbol,
                    category=category,
                    timestamp=timestamp,
                    defaults={
                        'open_price': open_price,
                        'high_price': high_price,
                        'low_price': low_price,
                        'close_price': close_price,
                        'volume': volume,
                    }
                )
                saved_count += 1

            except Exception as e:
                logger.error(f"Ошибка сохранения свечи {symbol} {category}: {e}")
                continue

        return saved_count

    def get_price_data(self, symbol: str, category: str,
                       start_date: datetime = None, end_date: datetime = None) -> list:
        """
        Получение ценовых данных из БД
        """
        if start_date is None:
            start_date = timezone.now() - timedelta(days=7)
        if end_date is None:
            end_date = timezone.now()

        prices = PriceHistory.objects.filter(
            symbol=symbol,
            category=category,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')

        return list(prices.values_list('close_price', flat=True))

    def get_latest_prices(self, symbol: str, category: str, limit: int = 1440) -> list:
        """
        Получение последних N цен из БД
        """
        prices = PriceHistory.objects.filter(
            symbol=symbol,
            category=category
        ).order_by('-timestamp')[:limit]

        return list(prices.values_list('close_price', flat=True))[
               ::-1]  # реверсируем чтобы были в хронологическом порядке