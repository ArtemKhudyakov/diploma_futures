from django.core.management.base import BaseCommand
from screener.services.bybit_api import BybitAPI
from screener.services.price_analyzer import PriceAnalyzer
from screener.services.chart_service import ChartService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тест упрощенной системы анализа'

    def add_arguments(self, parser):
        parser.add_argument('--timeframe', default='1h', help='Таймфрейм для графиков')
        parser.add_argument('--days', type=int, default=1, help='Количество дней данных')
        parser.add_argument('--mainnet', action='store_true', help='Использовать mainnet вместо testnet')

    def handle(self, *args, **options):
        timeframe = options['timeframe']
        days = options['days']
        use_mainnet = options['mainnet']

        self.stdout.write("🚀 Тест упрощенной системы анализа")
        self.stdout.write("=" * 60)

        # 1. Инициализация (используем mainnet для реальных цен)
        api = BybitAPI(testnet=not use_mainnet)
        analyzer = PriceAnalyzer()
        chart_service = ChartService()

        # 2. Получение корректных текущих цен
        self.stdout.write("💰 Получение текущих цен...")
        current_prices = api.get_correct_prices()

        if not all(current_prices.values()):
            self.stdout.write(self.style.ERROR("❌ Не удалось получить все текущие цены"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Текущие цены:\n"
                f"  ETH Spot: ${current_prices['eth_spot']:.2f}\n"
                f"  BTC Spot: ${current_prices['btc_spot']:.2f}\n"
                f"  ETH Futures: ${current_prices['eth_futures']:.2f}\n"
                f"  BTC Futures: ${current_prices['btc_futures']:.2f}"
            )
        )

        # 3. Проверяем цены на адекватность
        if current_prices['btc_spot'] > 200000 or current_prices['eth_spot'] > 20000:
            self.stdout.write(
                self.style.WARNING("⚠️  Цены выглядят подозрительно высокими! Используйте --mainnet для реальных цен")
            )

        # 4. Получение исторических данных
        self.stdout.write(f"\n📥 Загрузка исторических данных (таймфрейм: {timeframe}, дней: {days})...")

        eth_spot_klines = api.get_historical_data("ETHUSDT", "spot", timeframe, days)
        btc_spot_klines = api.get_historical_data("BTCUSDT", "spot", timeframe, days)

        if not eth_spot_klines or not btc_spot_klines:
            self.stdout.write(self.style.ERROR("❌ Не удалось загрузить исторические данные"))
            self.stdout.write("💡 Попробуйте другие параметры: --timeframe=1d --days=1 --mainnet")
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Загружено:\n"
                f"  ETH Spot: {len(eth_spot_klines)} свечей\n"
                f"  BTC Spot: {len(btc_spot_klines)} свечей"
            )
        )

        # 5. Настройка анализатора
        eth_spot_prices = [kline['close'] for kline in eth_spot_klines]
        btc_spot_prices = [kline['close'] for kline in btc_spot_klines]

        analyzer.add_historical_data(
            eth_spot_prices, btc_spot_prices,
            eth_spot_prices, btc_spot_prices  # Для простоты используем те же данные для фьючерсов
        )

        # 6. Анализ
        report = analyzer.get_analysis_report(current_prices)
        self.stdout.write(f"\n{report}")

        # 7. Графики
        self.stdout.write("\n📊 Создание графиков...")

        # Одиночные графики
        fig_eth = chart_service.create_candlestick_chart(
            eth_spot_klines, "ETHUSDT Spot", timeframe
        )
        chart_service.show_chart(fig_eth)
        chart_service.save_chart(fig_eth, f"eth_spot_{timeframe}")

        fig_btc = chart_service.create_candlestick_chart(
            btc_spot_klines, "BTCUSDT Spot", timeframe
        )
        chart_service.show_chart(fig_btc)
        chart_service.save_chart(fig_btc, f"btc_spot_{timeframe}")

        # Сравнительный график
        klines_data = {
            'ETHUSDT Spot': eth_spot_klines,
            'BTCUSDT Spot': btc_spot_klines
        }
        fig_compare = chart_service.create_multiple_charts(klines_data, timeframe)
        chart_service.show_chart(fig_compare)
        chart_service.save_chart(fig_compare, f"comparison_{timeframe}")

        self.stdout.write(self.style.SUCCESS("✅ Тест завершен! Графики открыты в браузере."))