from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
import logging
from screener.services.bybit_api import BybitAPI
from screener.services.price_analyzer import PriceAnalyzer
import math
from datetime import datetime
from screener.services.intrinsic_chart_service import intrinsic_chart_service
from django.core.cache import cache

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
            training_days = int(request.GET.get('training_days', 7))

            # ВСЕГДА обновляем период и перезагружаем данные
            analyzer.set_training_period(training_days)

            # ПРИНУДИТЕЛЬНО загружаем данные с новым периодом
            self._load_historical_data(training_days)

            # Остальной код без изменений...
            prices = api.get_correct_prices()

            # Если модели еще не готовы, пробуем построить их
            if not analyzer.spot_coef:
                analyzer._build_regression_models()

            analysis = analyzer.analyze_movement(prices)
            market_scenario = analyzer.get_market_scenario(analysis)
            analysis_info = analyzer.get_analysis_info()

            return JsonResponse({
                'success': True,
                'data': {
                    'prices': prices,
                    'technical_analysis': analysis,
                    'market_scenario': market_scenario,
                    'analysis_info': analysis_info,
                    'last_update': datetime.now().isoformat()
                }
            })

        except Exception as e:
            logger.error(f"DataAPIView error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def _load_historical_data(self, training_days: int):
        """Загрузка исторических данных с указанным периодом"""
        try:
            # ВСЕГДА загружаем новые данные при смене периода
            eth_klines = api.get_historical_data("ETHUSDT", "spot", "15m", training_days)
            btc_klines = api.get_historical_data("BTCUSDT", "spot", "15m", training_days)

            if eth_klines and btc_klines:
                eth_prices = [kline['close'] for kline in eth_klines]
                btc_prices = [kline['close'] for kline in btc_klines]

                # ОЧИЩАЕМ старые данные перед добавлением новых
                analyzer.historical_data['eth_spot'] = []
                analyzer.historical_data['btc_spot'] = []
                analyzer.historical_data['eth_futures'] = []
                analyzer.historical_data['btc_futures'] = []

                analyzer.add_historical_data(eth_prices, btc_prices, eth_prices, btc_prices)
                logger.info(f"Загружено {len(eth_prices)} точек данных за {training_days} дней")

                # СБРАСЫВАЕМ модели чтобы перестроить их на новых данных
                analyzer.spot_coef = None
                analyzer.spot_intercept = None
                analyzer.futures_coef = None
                analyzer.futures_intercept = None

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


class IntrinsicMovementAPIView(View):
    def get(self, request):
        try:
            days = int(request.GET.get('days', 7))
            timeframe = request.GET.get('timeframe', '1h')

            logger.info(f"🔍 DEBUG: Начало загрузки графика, days={days}, timeframe={timeframe}")

            # ВРЕМЕННО ОТКЛЮЧАЕМ КЭШ ДЛЯ ДЕБАГА
            # cache_key = f"intrinsic_chart_{days}_{timeframe}"
            # cached_data = cache.get(cache_key)
            # if cached_data:
            #     return JsonResponse({'success': True, 'data': cached_data, 'cached': True})

            # Оптимизация таймфрейма
            optimized_timeframe = self._get_optimized_timeframe(days)
            if optimized_timeframe != timeframe:
                timeframe = optimized_timeframe

            logger.info(f"🔍 DEBUG: Загрузка данных с таймфреймом {timeframe}")

            # Загрузка данных
            eth_klines = api.get_historical_data("ETHUSDT", "spot", timeframe, days)
            btc_klines = api.get_historical_data("BTCUSDT", "spot", timeframe, days)

            if eth_klines and btc_klines:
                # Проверяем первые несколько точек
                for i in range(min(3, len(eth_klines))):
                    eth_price = eth_klines[i].get('close')
                    btc_price = btc_klines[i].get('close')
                    if not eth_price or not btc_price or eth_price <= 0 or btc_price <= 0:
                        logger.error(f"❌ Некорректные цены в точке {i}: ETH={eth_price}, BTC={btc_price}")
                        return JsonResponse({
                            'success': False,
                            'error': 'Обнаружены некорректные ценовые данные'
                        })

            logger.info(f"🔍 DEBUG: Данные загружены - ETH: {len(eth_klines)}, BTC: {len(btc_klines)}")

            if not eth_klines or not btc_klines:
                logger.error(f"🔍 DEBUG: Нет данных! ETH: {len(eth_klines)}, BTC: {len(btc_klines)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Не удалось загрузить исторические данные. ETH: {len(eth_klines)}, BTC: {len(btc_klines)}'
                })

            # Проверяем структуру данных
            if eth_klines:
                first_eth = eth_klines[0]
                logger.info(f"🔍 DEBUG: Первая свеча ETH - {first_eth}")
            if btc_klines:
                first_btc = btc_klines[0]
                logger.info(f"🔍 DEBUG: Первая свеча BTC - {first_btc}")

            # Ограничиваем количество точек
            max_points = 200
            if len(eth_klines) > max_points:
                step = max(1, len(eth_klines) // max_points)
                eth_klines = eth_klines[::step]
                btc_klines = btc_klines[::step]
                logger.info(f"🔍 DEBUG: Данные сокращены до {len(eth_klines)} точек")

            # Проверяем, что есть достаточно данных для анализа
            if len(eth_klines) < 2:
                logger.error(f"🔍 DEBUG: Недостаточно данных для анализа! Всего точек: {len(eth_klines)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Недостаточно данных для анализа. Нужно минимум 2 точки, получено: {len(eth_klines)}'
                })

            logger.info("🔍 DEBUG: Начинаем построение графика...")
            if eth_klines and btc_klines:
                sample_eth = eth_klines[0]
                sample_btc = btc_klines[0]
                logger.info(f"🔍 ПРОВЕРКА ДАННЫХ:")
                logger.info(f"   ETH: timestamp={sample_eth.get('timestamp')}, close={sample_eth.get('close')}")
                logger.info(f"   BTC: timestamp={sample_btc.get('timestamp')}, close={sample_btc.get('close')}")

                # Проверяем, что есть поле 'close'
                if 'close' not in sample_eth or 'close' not in sample_btc:
                    logger.error("❌ В данных отсутствует поле 'close'!")
                    return JsonResponse({
                        'success': False,
                        'error': 'Некорректная структура данных: отсутствует поле close'
                    })
            intrinsic_data = intrinsic_chart_service.build_intrinsic_chart_data(
                eth_klines, btc_klines
            )

            logger.info(f"🔍 DEBUG: График построен. Получено точек: {len(intrinsic_data)}")

            if not intrinsic_data:
                logger.error("🔍 DEBUG: IntrinsicChartService вернул пустой результат!")
                return JsonResponse({
                    'success': False,
                    'error': 'Не удалось построить график собственного движения'
                })

            summary = intrinsic_chart_service.get_chart_summary(intrinsic_data)

            result_data = {
                'intrinsic_data': intrinsic_data,
                'summary': summary,
                'metadata': {
                    'period_days': days,
                    'timeframe': timeframe,
                    'data_points': len(intrinsic_data)
                }
            }

            return JsonResponse({
                'success': True,
                'data': result_data,
                'cached': False
            })

        except Exception as e:
            logger.error(f"🔍 DEBUG: IntrinsicMovementAPIView error: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})

    def _get_optimized_timeframe(self, days):
        """Оптимизация таймфрейма в зависимости от количества дней"""
        if days <= 1:
            return '15m'
        elif days <= 3:
            return '1h'
        elif days <= 7:
            return '4h'
        elif days <= 30:
            return '1d'
        else:
            return '1d'
