from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
import logging
from screener.services.bybit_api import BybitAPI
from screener.services.price_analyzer import PriceAnalyzer
import math
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Глобальные сервисы
api = BybitAPI(testnet=False)
analyzer = PriceAnalyzer()


class RealtimeView(View):
    def get(self, request):
        return render(request, 'screener/realtime.html')


class DataAPIView(View):
    def get(self, request):
        try:
            logger.info("DataAPIView called")

            prices = api.get_correct_prices()
            logger.info(f"Prices from API: {prices}")

            # Загружаем исторические данные для анализа если нужно
            if not analyzer.spot_coef:
                self._load_historical_data()

            analysis = analyzer.analyze_movement(prices)
            logger.info(f"Analysis result: {analysis}")

            return JsonResponse({
                'success': True,
                'data': {
                    'prices': prices,
                    'analysis': analysis,
                    'last_update': datetime.now().isoformat()
                }
            })

        except Exception as e:
            logger.error(f"DataAPIView error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def _load_historical_data(self):
        try:
            eth_klines = api.get_historical_data("ETHUSDT", "spot", "15m", 2)
            btc_klines = api.get_historical_data("BTCUSDT", "spot", "15m", 2)

            if eth_klines and btc_klines:
                eth_prices = [kline['close'] for kline in eth_klines]
                btc_prices = [kline['close'] for kline in btc_klines]
                analyzer.add_historical_data(eth_prices, btc_prices, eth_prices, btc_prices)

        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных: {e}")


class HistoryAPIView(View):
    def get(self, request):
        try:
            symbol = request.GET.get('symbol', 'ETHUSDT')
            timeframe = request.GET.get('timeframe', '1h')
            days = int(request.GET.get('days', 3))

            klines = api.get_historical_data(symbol, "spot", timeframe, days)

            if not klines:
                return JsonResponse({
                    'success': False,
                    'error': f'Нет данных для {symbol} {timeframe}'
                })

            candles = []
            for kline in klines:
                candles.append({
                    'timestamp': kline['timestamp'],
                    'open': kline['open'],
                    'high': kline['high'],
                    'low': kline['low'],
                    'close': kline['close'],
                    'volume': kline.get('volume', 0)
                })

            return JsonResponse({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'candles': candles,
                    'candles_count': len(candles)
                }
            })

        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


class ChartDataAPIView(View):
    def get(self, request):
        try:
            symbol = request.GET.get('symbol', 'ETHUSDT')
            timeframe = request.GET.get('timeframe', '1h')
            limit = int(request.GET.get('limit', 100))

            # Для малых таймфреймов используем другой подход
            if timeframe in ['1m', '3m', '5m', '15m', '30m']:
                klines = self._get_small_timeframe_data(symbol, timeframe, limit)
            else:
                # Для больших таймфреймов используем существующую логику
                days = self._calculate_days_needed(timeframe, limit)
                klines = api.get_historical_data(symbol, "spot", timeframe, days)

            if not klines:
                return JsonResponse({'success': False, 'error': 'No data available'})

            # Получаем текущие цены для актуальной информации
            current_prices = api.get_correct_prices()
            current_price = self._get_current_price_for_symbol(current_prices, symbol)

            # Форматируем данные для графика
            chart_data = {
                'candles': self._format_klines(klines),
                'current_price': current_price,
                'symbol': symbol,
                'timeframe': timeframe,
                'last_update': datetime.now().isoformat(),
                'candles_count': len(klines)
            }

            return JsonResponse({'success': True, 'data': chart_data})

        except Exception as e:
            logger.error(f"Chart data error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def _get_small_timeframe_data(self, symbol, timeframe, limit):
        """Получает данные для малых таймфреймов"""
        try:
            # Для малых таймфреймов загружаем больше данных через API
            # Bybit API позволяет до 1000 свечей за раз
            actual_limit = min(limit, 1000)

            # Получаем данные напрямую через API
            timeframe_mapping = {
                '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30'
            }

            interval = timeframe_mapping.get(timeframe, '1')
            klines = api.get_klines(symbol, "spot", interval, actual_limit)

            # Сортируем по времени (от старых к новым)
            if klines:
                klines.sort(key=lambda x: x['timestamp'])

            return klines

        except Exception as e:
            logger.error(f"Small timeframe data error: {e}")
            return []

    def _calculate_days_needed(self, timeframe, limit):
        """Рассчитывает сколько дней истории нужно для указанного количества свечей"""
        candles_per_day = {
            '1m': 1440, '3m': 480, '5m': 288, '15m': 96, '30m': 48,
            '1h': 24, '2h': 12, '4h': 6, '6h': 4, '12h': 2,
            '1d': 1, '1w': 0.14, '1M': 0.03
        }

        days_needed = (limit / candles_per_day.get(timeframe, 24)) + 1
        return min(math.ceil(days_needed), 60)  # максимум 60 дней для больших таймфреймов

    def _get_current_price_for_symbol(self, prices, symbol):
        """Получает текущую цену для символа"""
        symbol_map = {
            'ETHUSDT': 'eth_spot',
            'BTCUSDT': 'btc_spot'
        }
        price_key = symbol_map.get(symbol)
        return prices.get(price_key) if price_key else None

    def _format_klines(self, klines):
        """Форматирует свечи для фронтенда"""
        formatted = []
        for kline in klines:
            formatted.append({
                'time': kline['timestamp'] // 1000,  # конвертируем в секунды для Plotly
                'open': float(kline['open']),
                'high': float(kline['high']),
                'low': float(kline['low']),
                'close': float(kline['close']),
                'volume': float(kline.get('volume', 0))
            })
        return formatted

    def _calculate_days_needed(self, timeframe, limit):
        """Рассчитывает сколько дней истории нужно для указанного количества свечей"""
        candles_per_day = {
            '1m': 1440, '5m': 288, '15m': 96, '30m': 48,
            '1h': 24, '2h': 12, '4h': 6, '6h': 4, '12h': 2,
            '1d': 1, '1w': 0.14, '1M': 0.03
        }

        days_needed = (limit / candles_per_day.get(timeframe, 24)) + 1
        return min(math.ceil(days_needed), 30)  # максимум 30 дней

    def _get_current_price_for_symbol(self, prices, symbol):
        """Получает текущую цену для символа"""
        symbol_map = {
            'ETHUSDT': 'eth_spot',
            'BTCUSDT': 'btc_spot'
        }
        price_key = symbol_map.get(symbol)
        return prices.get(price_key) if price_key else None

    def _format_klines(self, klines):
        """Форматирует свечи для фронтенда"""
        formatted = []
        for kline in klines:
            formatted.append({
                'time': kline['timestamp'] // 1000,  # конвертируем в секунды для Plotly
                'open': float(kline['open']),
                'high': float(kline['high']),
                'low': float(kline['low']),
                'close': float(kline['close']),
                'volume': float(kline.get('volume', 0))
            })
        return formatted