from django.core.management.base import BaseCommand
from screener.services.bybit_api import BybitClient
from screener.services.price_analyzer import PriceAnalyzer


class Command(BaseCommand):
    help = 'Запуск анализатора с историческими данными'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Запуск анализатора с историческими данными...")

        # Анализатор автоматически загрузит исторические данные из БД
        analyzer = PriceAnalyzer(use_database=True)
        client = BybitClient(testnet=True)

        self.stdout.write("✅ Анализатор готов к работе!")
        # Дальше основной цикл как раньше...