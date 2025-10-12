from django.core.management.base import BaseCommand
from screener.services.history_service import HistoryService


class Command(BaseCommand):
    help = 'Загрузка исторических данных в БД'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Количество дней для загрузки')
        parser.add_argument('--symbols', type=str, default='ETHUSDT,BTCUSDT', help='Символы через запятую')

    def handle(self, *args, **options):
        days = options['days']
        symbols = options['symbols'].split(',')

        self.stdout.write(f"📥 Загрузка исторических данных за {days} дней...")

        service = HistoryService(testnet=True)
        total_points = service.load_and_save_history(days=days, symbols=symbols)

        self.stdout.write(
            self.style.SUCCESS(f"✅ Загружено {total_points} точек данных")
        )