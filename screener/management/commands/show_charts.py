from django.core.management.base import BaseCommand
from screener.services.chart_service import ChartService
from screener.services.bybit_api import BybitClient
from screener.services.price_analyzer import PriceAnalyzer


class Command(BaseCommand):
    help = 'Показ графиков анализа'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, default='dashboard',
                            choices=['dashboard', 'candles', 'comparison', 'all'],
                            help='Тип графика')
        parser.add_argument('--symbol', type=str, default='ETHUSDT')
        parser.add_argument('--days', type=int, default=1)
        parser.add_argument('--save', action='store_true', help='Сохранить в файл')

    def handle(self, *args, **options):
        chart_type = options['type']
        symbol = options['symbol']
        days = options['days']
        save_chart = options['save']

        chart_service = ChartService()

        if chart_type == 'candles' or chart_type == 'all':
            self.stdout.write("📊 Генерация свечных графиков...")

            # График ETH spot
            fig_eth = chart_service.create_candlestick_chart('ETHUSDT', 'spot', days)
            if save_chart:
                chart_service.save_chart(fig_eth, f'eth_spot_{days}days')
            chart_service.show_chart(fig_eth)

            # График BTC spot
            fig_btc = chart_service.create_candlestick_chart('BTCUSDT', 'spot', days)
            if save_chart:
                chart_service.save_chart(fig_btc, f'btc_spot_{days}days')
            chart_service.show_chart(fig_btc)

        if chart_type == 'comparison' or chart_type == 'all':
            self.stdout.write("🔄 Генерация графика сравнения...")
            fig_comp = chart_service.create_comparison_chart('ETHUSDT', days)
            if save_chart:
                chart_service.save_chart(fig_comp, f'comparison_{days}days')
            chart_service.show_chart(fig_comp)

        if chart_type == 'dashboard' or chart_type == 'all':
            self.stdout.write("🎛️  Генерация дашборда анализа...")

            # Получаем текущие данные для анализа
            client = BybitClient(testnet=True)
            analyzer = PriceAnalyzer(use_database=True)

            prices = client.get_all_prices()
            if all(prices.values()):
                analyzer.update_data(prices)
                intrinsic = analyzer.calculate_intrinsic_movement(prices)

                fig_dash = chart_service.create_analysis_dashboard(intrinsic, prices, days)
                if save_chart:
                    chart_service.save_chart(fig_dash, f'dashboard_{days}days')
                chart_service.show_chart(fig_dash)
            else:
                self.stdout.write(self.style.ERROR("❌ Не удалось получить данные для дашборда"))