"""
Views for screener application.

This module provides API endpoints for market data, analysis, and price alerts.
"""
import json
import math
import logging
from datetime import datetime

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from screener.services.bybit_api import BybitAPI
from screener.services.price_analyzer import PriceAnalyzer
from screener.services.intrinsic_chart_service import intrinsic_chart_service
from .models import PriceAlert
from .forms import PriceAlertForm

logger = logging.getLogger(__name__)

# Global services
api = BybitAPI(testnet=False)
analyzer = PriceAnalyzer()


class RealtimeView(View):
    """
    Главная страница скринера в реальном времени.

    Предоставляет веб-интерфейс для мониторинга рынка с графиками и аналитикой.
    """

    def get(self, request):
        """
        Отображает страницу реального времени скринера.

        Returns:
            HttpResponse: HTML страница с интерфейсом скринера
        """
        return render(request, 'screener/realtime.html')


class DataAPIView(View):
    """
    API для получения текущих рыночных данных и технического анализа.

    Предоставляет актуальные цены, анализ собственного движения и рыночные сценарии.
    """

    @swagger_auto_schema(
        operation_description="""
        Получение текущих рыночных данных и технического анализа.

        Этот endpoint возвращает:
        - Текущие цены спот и фьючерсов для ETH и BTC
        - Технический анализ собственного движения
        - Рыночные сценарии и влияние BTC
        - Информацию о построенных моделях

        Для анализа используется линейная регрессия на исторических данных.
        """,
        manual_parameters=[
            openapi.Parameter(
                'training_days',
                openapi.IN_QUERY,
                description="Количество дней исторических данных для анализа (1-30)",
                type=openapi.TYPE_INTEGER,
                default=7
            ),
            openapi.Parameter(
                'analysis_type',
                openapi.IN_QUERY,
                description="Тип анализа: только спот или с фьючерсами",
                type=openapi.TYPE_STRING,
                enum=['spot', 'futures'],
                default='spot'
            ),
            openapi.Parameter(
                'futures_type',
                openapi.IN_QUERY,
                description="Тип фьючерсных контрактов",
                type=openapi.TYPE_STRING,
                enum=['linear', 'inverse'],
                default='linear'
            )
        ],
        responses={
            200: openapi.Response(
                description="Успешный ответ с рыночными данными",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "prices": {
                                "eth_spot": 3500.50,
                                "btc_spot": 65000.75,
                                "eth_futures": 3501.25,
                                "btc_futures": 65002.10
                            },
                            "technical_analysis": {
                                "spot_intrinsic": 0.5,
                                "futures_intrinsic": 0.3,
                                "spot_btc_influence": 60.2,
                                "spot_eth_own": 39.8
                            },
                            "market_scenario": {
                                "eth_strength": 15.5,
                                "market_scenario": "slightly_bullish_eth",
                                "explanation": "ETH немного опережает BTC (+0.5%)"
                            }
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Ошибка в параметрах запроса",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Invalid training_days parameter"
                    }
                }
            ),
            500: openapi.Response(
                description="Внутренняя ошибка сервера",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Data source unavailable"
                    }
                }
            )
        },
        tags=['Market Data']
    )
    def get(self, request):
        """
        Обрабатывает GET запрос для получения рыночных данных.

        Args:
            request: HTTP запрос с параметрами:
                training_days (int): дни для анализа
                analysis_type (str): тип анализа
                futures_type (str): тип фьючерсов

        Returns:
            JsonResponse: JSON с рыночными данными или ошибкой
        """
        try:
            training_days = int(request.GET.get('training_days', 7))
            analysis_type = request.GET.get('analysis_type', 'spot')
            futures_type = request.GET.get('futures_type', 'linear')

            # Убираем режим "both", оставляем только spot и futures
            if analysis_type == 'both':
                analysis_type = 'spot'

            analyzer.set_training_period(training_days)
            self._load_historical_data(training_days, analysis_type, futures_type)

            # Получаем цены в зависимости от типа анализа
            prices = self._get_prices_by_analysis_type(analysis_type, futures_type)

            # Строим модели если не готовы
            if not analyzer.spot_coef:
                analyzer._build_regression_models()

            # Анализируем движение
            analysis = analyzer.analyze_movement(prices)
            market_scenario = analyzer.get_market_scenario(analysis)
            analysis_info = analyzer.get_analysis_info()

            analysis_info.update({
                'analysis_type': analysis_type,
                'futures_type': futures_type
            })

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
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def _get_prices_by_analysis_type(self, analysis_type, futures_type):
        """
        Получает цены в зависимости от типа анализа.

        Args:
            analysis_type (str): spot или futures
            futures_type (str): linear или inverse

        Returns:
            dict: словарь с ценами
        """
        prices = {}
        spot_prices = api.get_correct_prices()

        if analysis_type == 'spot':
            return {
                'eth_spot': spot_prices.get('eth_spot'),
                'btc_spot': spot_prices.get('btc_spot'),
                'eth_futures': None,
                'btc_futures': None
            }
        else:  # futures
            return {
                'eth_spot': spot_prices.get('eth_spot'),
                'btc_spot': spot_prices.get('btc_spot'),
                'eth_futures': spot_prices.get('eth_futures'),
                'btc_futures': spot_prices.get('btc_futures')
            }

    def _load_historical_data(self, training_days: int, analysis_type: str, futures_type: str):
        """
        Загружает исторические данные для анализа.

        Args:
            training_days (int): количество дней для загрузки
            analysis_type (str): тип анализа
            futures_type (str): тип фьючерсов
        """
        try:
            # Для spot анализа загружаем только спотовые данные
            if analysis_type == 'spot':
                eth_klines = api.get_historical_data("ETHUSDT", "spot", "15m", training_days)
                btc_klines = api.get_historical_data("BTCUSDT", "spot", "15m", training_days)

                if eth_klines and btc_klines:
                    eth_prices = [kline['close'] for kline in eth_klines]
                    btc_prices = [kline['close'] for kline in btc_klines]

                    analyzer.historical_data['eth_spot'] = []
                    analyzer.historical_data['btc_spot'] = []
                    analyzer.historical_data['eth_futures'] = []
                    analyzer.historical_data['btc_futures'] = []

                    analyzer.add_historical_data(eth_prices, btc_prices, [], [])

            # Для futures анализа загружаем фьючерсные данные
            else:
                eth_klines = api.get_historical_data("ETHUSDT", futures_type, "15m", training_days)
                btc_klines = api.get_historical_data("BTCUSDT", futures_type, "15m", training_days)

                if eth_klines and btc_klines:
                    eth_prices = [kline['close'] for kline in eth_klines]
                    btc_prices = [kline['close'] for kline in btc_klines]

                    analyzer.historical_data['eth_spot'] = []
                    analyzer.historical_data['btc_spot'] = []
                    analyzer.historical_data['eth_futures'] = []
                    analyzer.historical_data['btc_futures'] = []

                    analyzer.add_historical_data([], [], eth_prices, btc_prices)

            # Сбрасываем модели для перестроения
            analyzer.spot_coef = None
            analyzer.spot_intercept = None
            analyzer.futures_coef = None
            analyzer.futures_intercept = None

            logger.info(f"Загружены данные для {analysis_type} анализа ({futures_type})")

        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных: {e}")


class HistoryAPIView(View):
    """
    API для получения исторических данных по конкретному символу.

    Предоставляет свечные данные для построения графиков.
    """

    @swagger_auto_schema(
        operation_description="""
        Получение исторических свечных данных.

        Возвращает OHLCV данные для указанного символа и таймфрейма.
        Максимальный лимит - 1000 свечей.
        """,
        manual_parameters=[
            openapi.Parameter(
                'symbol',
                openapi.IN_QUERY,
                description="Торговый символ",
                type=openapi.TYPE_STRING,
                enum=['ETHUSDT', 'BTCUSDT'],
                default='ETHUSDT'
            ),
            openapi.Parameter(
                'timeframe',
                openapi.IN_QUERY,
                description="Таймфрейм данных",
                type=openapi.TYPE_STRING,
                enum=['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w'],
                default='1h'
            ),
            openapi.Parameter(
                'days',
                openapi.IN_QUERY,
                description="Количество дней истории",
                type=openapi.TYPE_INTEGER,
                default=3
            )
        ],
        responses={
            200: openapi.Response(
                description="Успешный ответ с историческими данными",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "symbol": "ETHUSDT",
                            "timeframe": "1h",
                            "candles_count": 72,
                            "candles": [
                                {
                                    "timestamp": 1672531200000,
                                    "open": 3500.50,
                                    "high": 3520.75,
                                    "low": 3495.25,
                                    "close": 3510.80,
                                    "volume": 12500.45
                                }
                            ]
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Неверные параметры запроса",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Invalid symbol"
                    }
                }
            )
        },
        tags=['Historical Data']
    )
    def get(self, request):
        """
        Обрабатывает GET запрос для получения исторических данных.

        Args:
            request: HTTP запрос с параметрами symbol, timeframe, days

        Returns:
            JsonResponse: JSON с историческими данными
        """
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
    """
    API для получения данных для построения графиков.

    Оптимизирован для фронтенд-чартов с поддержкой различных таймфреймов.
    """

    @swagger_auto_schema(
        operation_description="""
        Получение данных для построения свечных графиков.

        Специализированный endpoint для фронтенд-библиотек графиков.
        Автоматически оптимизирует таймфрейм в зависимости от лимита.
        """,
        manual_parameters=[
            openapi.Parameter(
                'symbol',
                openapi.IN_QUERY,
                description="Торговый символ",
                type=openapi.TYPE_STRING,
                enum=['ETHUSDT', 'BTCUSDT'],
                default='ETHUSDT'
            ),
            openapi.Parameter(
                'timeframe',
                openapi.IN_QUERY,
                description="Таймфрейм данных",
                type=openapi.TYPE_STRING,
                enum=['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '1d', '1w'],
                default='1h'
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Лимит свечей (макс. 1000)",
                type=openapi.TYPE_INTEGER,
                default=100
            ),
            openapi.Parameter(
                'data_type',
                openapi.IN_QUERY,
                description="Тип данных: spot или futures",
                type=openapi.TYPE_STRING,
                enum=['spot', 'futures'],
                default='spot'
            )
        ],
        responses={
            200: openapi.Response(
                description="Данные для графика",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "candles": [
                                {
                                    "time": 1672531200,
                                    "open": 3500.50,
                                    "high": 3520.75,
                                    "low": 3495.25,
                                    "close": 3510.80,
                                    "volume": 12500.45
                                }
                            ],
                            "current_price": 3512.30,
                            "symbol": "ETHUSDT",
                            "timeframe": "1h",
                            "candles_count": 100
                        }
                    }
                }
            )
        },
        tags=['Charts']
    )
    def get(self, request):
        """
        Обрабатывает GET запрос для данных графиков.

        Args:
            request: HTTP запрос с параметрами symbol, timeframe, limit, data_type

        Returns:
            JsonResponse: JSON с данными для графика
        """
        try:
            symbol = request.GET.get('symbol', 'ETHUSDT')
            timeframe = request.GET.get('timeframe', '1h')
            limit = int(request.GET.get('limit', 100))
            data_type = request.GET.get('data_type', 'spot')

            # Определяем категорию для API запроса
            category = "spot" if data_type == "spot" else request.GET.get('futures_type', 'linear')

            # Для маленьких таймфреймов используем другой подход
            if timeframe in ['1m', '3m', '5m', '15m', '30m']:
                klines = self._get_small_timeframe_data(symbol, category, timeframe, limit)
            else:
                days = self._calculate_days_needed(timeframe, limit)
                klines = api.get_historical_data(symbol, category, timeframe, days)

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
                'category': category,
                'last_update': datetime.now().isoformat(),
                'candles_count': len(klines)
            }

            return JsonResponse({'success': True, 'data': chart_data})

        except Exception as e:
            logger.error(f"Chart data error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def _get_small_timeframe_data(self, symbol, category, timeframe, limit):
        """Получает данные для маленьких таймфреймов."""
        try:
            actual_limit = min(limit, 1000)

            timeframe_mapping = {
                '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30'
            }

            interval = timeframe_mapping.get(timeframe, '1')
            klines = api.get_klines(symbol, category, interval, actual_limit)

            if klines:
                klines.sort(key=lambda x: x['timestamp'])

            return klines

        except Exception as e:
            logger.error(f"Small timeframe data error: {e}")
            return []

    def _calculate_days_needed(self, timeframe, limit):
        """Рассчитывает необходимое количество дней для указанного лимита свечей."""
        candles_per_day = {
            '1m': 1440, '3m': 480, '5m': 288, '15m': 96, '30m': 48,
            '1h': 24, '2h': 12, '4h': 6, '6h': 4, '12h': 2,
            '1d': 1, '1w': 0.14, '1M': 0.03
        }

        days_needed = (limit / candles_per_day.get(timeframe, 24)) + 1
        return min(math.ceil(days_needed), 60)

    def _get_current_price_for_symbol(self, prices, symbol):
        """Получает текущую цену для символа."""
        symbol_map = {
            'ETHUSDT': 'eth_spot',
            'BTCUSDT': 'btc_spot'
        }
        price_key = symbol_map.get(symbol)
        return prices.get(price_key) if price_key else None

    def _format_klines(self, klines):
        """Форматирует свечи для фронтенда."""
        formatted = []
        for kline in klines:
            formatted.append({
                'time': kline['timestamp'] // 1000,
                'open': float(kline['open']),
                'high': float(kline['high']),
                'low': float(kline['low']),
                'close': float(kline['close']),
                'volume': float(kline.get('volume', 0))
            })
        return formatted


class IntrinsicMovementAPIView(View):
    """
    API для анализа собственного движения активов.

    Специализированный анализ независимого движения ETH от влияния BTC.
    """

    @swagger_auto_schema(
        operation_description="""
        Глубокий анализ собственного движения ETH относительно BTC.

        Строит модель линейной регрессии для определения "истинного" движения ETH,
        исключая влияние общего рыночного тренда BTC.

        Возвращает данные для построения графика собственного движения.
        """,
        manual_parameters=[
            openapi.Parameter(
                'days',
                openapi.IN_QUERY,
                description="Период анализа в днях (1-90)",
                type=openapi.TYPE_INTEGER,
                default=7
            ),
            openapi.Parameter(
                'timeframe',
                openapi.IN_QUERY,
                description="Таймфрейм для анализа",
                type=openapi.TYPE_STRING,
                enum=['15m', '1h', '4h', '1d'],
                default='1h'
            ),
            openapi.Parameter(
                'data_type',
                openapi.IN_QUERY,
                description="Тип данных для анализа",
                type=openapi.TYPE_STRING,
                enum=['spot', 'futures'],
                default='spot'
            )
        ],
        responses={
            200: openapi.Response(
                description="Данные для анализа собственного движения",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "intrinsic_data": [
                                {
                                    "timestamp": 1672531200000,
                                    "time": 1672531200,
                                    "intrinsic_movement": 0.5,
                                    "eth_price": 3500.50,
                                    "btc_price": 65000.75,
                                    "influence_btc": 60.2,
                                    "eth_own_power": 39.8
                                }
                            ],
                            "summary": {
                                "total_points": 168,
                                "avg_movement": 0.3,
                                "positive_points": 95,
                                "negative_points": 73
                            }
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Недостаточно данных для анализа",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Недостаточно данных для анализа. Нужно минимум 2 точки, получено: 1"
                    }
                }
            )
        },
        tags=['Advanced Analysis']
    )
    def get(self, request):
        """
        Обрабатывает GET запрос для анализа собственного движения.

        Args:
            request: HTTP запрос с параметрами days, timeframe, data_type

        Returns:
            JsonResponse: JSON с данными анализа
        """
        try:
            days = int(request.GET.get('days', 7))
            timeframe = request.GET.get('timeframe', '1h')
            data_type = request.GET.get('data_type', 'spot')

            logger.info(f"Начало загрузки графика, days={days}, timeframe={timeframe}, data_type={data_type}")

            # Оптимизация таймфрейма
            optimized_timeframe = self._get_optimized_timeframe(days)
            if optimized_timeframe != timeframe:
                timeframe = optimized_timeframe

            # Определяем категорию данных
            category = "spot" if data_type == "spot" else request.GET.get('futures_type', 'linear')

            logger.info(f"Загрузка данных с таймфреймом {timeframe}, категория: {category}")

            # Загрузка данных
            eth_klines = api.get_historical_data("ETHUSDT", category, timeframe, days)
            btc_klines = api.get_historical_data("BTCUSDT", category, timeframe, days)

            logger.info(f"Данные загружены - ETH: {len(eth_klines)}, BTC: {len(btc_klines)}")

            if not eth_klines or not btc_klines:
                logger.error(f"Нет данных! ETH: {len(eth_klines)}, BTC: {len(btc_klines)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Не удалось загрузить исторические данные. ETH: {len(eth_klines)}, BTC: {len(btc_klines)}'
                })

            # Ограничиваем количество точек
            max_points = 200
            if len(eth_klines) > max_points:
                step = max(1, len(eth_klines) // max_points)
                eth_klines = eth_klines[::step]
                btc_klines = btc_klines[::step]
                logger.info(f"Данные сокращены до {len(eth_klines)} точек")

            # Проверяем достаточность данных
            if len(eth_klines) < 2:
                logger.error(f"Недостаточно данных для анализа! Всего точек: {len(eth_klines)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Недостаточно данных для анализа. Нужно минимум 2 точки, получено: {len(eth_klines)}'
                })

            logger.info("Начинаем построение графика...")
            intrinsic_data = intrinsic_chart_service.build_intrinsic_chart_data(
                eth_klines, btc_klines
            )

            logger.info(f"График построен. Получено точек: {len(intrinsic_data)}")

            if not intrinsic_data:
                logger.error("IntrinsicChartService вернул пустой результат!")
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
                    'category': category,
                    'data_points': len(intrinsic_data)
                }
            }

            return JsonResponse({
                'success': True,
                'data': result_data
            })

        except Exception as e:
            logger.error(f"IntrinsicMovementAPIView error: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})

    def _get_optimized_timeframe(self, days):
        """Оптимизирует таймфрейм в зависимости от количества дней."""
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


# АЛЕРТЫ - ИСПРАВЛЕННЫЕ ВЕРСИИ

@method_decorator(login_required, name='dispatch')
class AlertCreateAPIView(View):
    """
    API для создания ценовых алертов.

    Требует аутентификации. Создает алерт для отслеживания ценовых уровней.
    """

    @swagger_auto_schema(
        operation_description="""
        Создание нового ценового алерта.

        Алерт будет отслеживать достижение целевой цены для указанного символа.
        При создании сразу проверяется текущая цена - если условие уже выполнено,
        алерт мгновенно срабатывает.

        ### Условия:
        - **above**: цена выше или равна целевой
        - **below**: цена ниже или равна целевой

        Требуется аутентификация JWT токеном.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'symbol', 'condition', 'target_price'],
            properties={
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Название алерта (например: "ETH достиг 4000")',
                    maxLength=100
                ),
                'symbol': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['ETHUSDT', 'BTCUSDT'],
                    description='Торговый символ'
                ),
                'condition': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['above', 'below'],
                    description='Условие срабатывания'
                ),
                'target_price': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    format='float',
                    description='Целевая цена (должна быть положительной)',
                    minimum=0.01
                )
            },
            example={
                "name": "ETH выше 4000",
                "symbol": "ETHUSDT",
                "condition": "above",
                "target_price": 4000.00
            }
        ),
        responses={
            201: openapi.Response(
                description="Алерт успешно создан",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Алерт успешно создан (Сразу сработал!)",
                        "alert": {
                            "id": 1,
                            "name": "ETH выше 4000",
                            "symbol": "ETHUSDT",
                            "condition": "above",
                            "target_price": 4000.00,
                            "status": "triggered",
                            "created_at": "25.10.2024 14:30"
                        },
                        "immediate_trigger": True
                    }
                }
            ),
            400: openapi.Response(
                description="Ошибка валидации данных",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Введите название алерта"
                    }
                }
            ),
            401: openapi.Response(
                description="Не авторизован",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Требуется аутентификация для создания алертов"
                    }
                }
            )
        },
        security=[{'Bearer': []}],
        tags=['Alerts']
    )
    def post(self, request):
        """
        Обрабатывает POST запрос для создания алерта.

        Args:
            request: HTTP запрос с JSON телом

        Returns:
            JsonResponse: результат создания алерта
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется аутентификация для создания алертов'
                }, status=401)

            data = json.loads(request.body)

            # Валидация данных
            name = data.get('name', '').strip()
            symbol = data.get('symbol')
            condition = data.get('condition')
            target_price = data.get('target_price')

            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'Введите название алерта'
                }, status=400)

            if not symbol or symbol not in ['ETHUSDT', 'BTCUSDT']:
                return JsonResponse({
                    'success': False,
                    'error': 'Выберите корректный символ'
                }, status=400)

            if not condition or condition not in ['above', 'below']:
                return JsonResponse({
                    'success': False,
                    'error': 'Выберите корректное условие'
                }, status=400)

            try:
                target_price = float(target_price)
                if target_price <= 0:
                    raise ValueError("Цена должна быть положительной")
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'error': 'Введите корректную цену'
                }, status=400)

            # Создаем алерт
            alert = PriceAlert(
                user=request.user,
                name=name,
                symbol=symbol,
                condition=condition,
                target_price=target_price
            )
            alert.save()

            # МГНОВЕННАЯ ПРОВЕРКА ПРИ СОЗДАНИИ
            current_prices = api.get_correct_prices()
            current_price = None

            if symbol == 'ETHUSDT':
                current_price = current_prices.get('eth_spot')
            elif symbol == 'BTCUSDT':
                current_price = current_prices.get('btc_spot')

            # Если цена уже достигла цели - сразу срабатываем
            if current_price and alert.check_condition(current_price):
                alert.trigger(current_price)
                show_immediate_alert = True
            else:
                show_immediate_alert = False

            return JsonResponse({
                'success': True,
                'message': 'Алерт успешно создан' + (' (Сразу сработал!)' if show_immediate_alert else ''),
                'alert': {
                    'id': alert.id,
                    'name': alert.name,
                    'symbol': alert.symbol,
                    'condition': alert.condition,
                    'target_price': alert.target_price,
                    'status': alert.status,
                    'created_at': alert.created_at.strftime('%d.%m.%Y %H:%M'),
                    'triggered_at': alert.triggered_at.strftime('%d.%m.%Y %H:%M') if alert.triggered_at else None,
                    'current_price_when_triggered': alert.current_price_when_triggered,
                },
                'immediate_trigger': show_immediate_alert
            }, status=201)

        except Exception as e:
            logger.error(f"Alert creation error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(login_required, name='dispatch')
class AlertListAPIView(View):
    """
    API для получения списка алертов пользователя.

    Возвращает все алерты текущего аутентифицированного пользователя.
    """

    @swagger_auto_schema(
        operation_description="""
        Получение списка всех алертов текущего пользователя.

        Возвращает алерты отсортированные по дате создания (новые first).
        Показывает все статусы: активные, сработавшие и отмененные.

        Требуется аутентификация JWT токеном.
        """,
        responses={
            200: openapi.Response(
                description="Список алертов пользователя",
                examples={
                    "application/json": {
                        "success": True,
                        "alerts": [
                            {
                                "id": 1,
                                "name": "ETH выше 4000",
                                "symbol": "ETHUSDT",
                                "condition": "above",
                                "target_price": 4000.00,
                                "status": "active",
                                "created_at": "25.10.2024 14:30",
                                "triggered_at": None
                            }
                        ]
                    }
                }
            ),
            401: openapi.Response(
                description="Не авторизован"
            )
        },
        security=[{'Bearer': []}],
        tags=['Alerts']
    )
    def get(self, request):
        """
        Обрабатывает GET запрос для получения списка алертов.

        Returns:
            JsonResponse: список алертов пользователя
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется аутентификация'
                }, status=401)

            alerts = PriceAlert.objects.filter(user=request.user).order_by('-created_at')
            alerts_data = []

            for alert in alerts:
                alerts_data.append({
                    'id': alert.id,
                    'name': alert.name,
                    'symbol': alert.symbol,
                    'condition': alert.condition,
                    'target_price': alert.target_price,
                    'status': alert.status,
                    'created_at': alert.created_at.strftime('%d.%m.%Y %H:%M'),
                    'triggered_at': alert.triggered_at.strftime('%d.%m.%Y %H:%M') if alert.triggered_at else None,
                    'current_price_when_triggered': alert.current_price_when_triggered,
                })

            return JsonResponse({
                'success': True,
                'alerts': alerts_data
            })

        except Exception as e:
            logger.error(f"Alert list error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(login_required, name='dispatch')
class AlertDeleteAPIView(View):
    """
    API для удаления алертов.

    Позволяет пользователю удалить свои алерты.
    """

    @swagger_auto_schema(
        operation_description="""
        Удаление алерта по ID.

        Пользователь может удалять только свои собственные алерты.
        При успешном удалении возвращается подтверждение.

        Требуется аутентификация JWT токеном.
        """,
        responses={
            200: openapi.Response(
                description="Алерт успешно удален",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Алерт удален"
                    }
                }
            ),
            404: openapi.Response(
                description="Алерт не найден",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Алерт не найден"
                    }
                }
            )
        },
        security=[{'Bearer': []}],
        tags=['Alerts']
    )
    def delete(self, request, alert_id):
        """
        Обрабатывает DELETE запрос для удаления алерта.

        Args:
            request: HTTP запрос
            alert_id (int): ID алерта для удаления

        Returns:
            JsonResponse: результат удаления
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется аутентификация'
                }, status=401)

            alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
            alert.delete()

            return JsonResponse({
                'success': True,
                'message': 'Алерт удален'
            })

        except Exception as e:
            logger.error(f"Alert deletion error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(login_required, name='dispatch')
class CheckAlertsView(View):
    """
    API для проверки срабатывания алертов.

    Проверяет все активные алерты пользователя на соответствие текущим ценам.
    """

    @swagger_auto_schema(
        operation_description="""
        Проверка активных алертов на срабатывание.

        Принимает текущие цены и проверяет все активные алерты пользователя.
        Возвращает список сработавших алертов.

        ### Мгновенное срабатывание:
        Алерты срабатывают сразу при достижении целевой цены, без задержек.

        Требуется аутентификация JWT токеном.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['prices'],
            properties={
                'prices': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='Текущие рыночные цены',
                    properties={
                        'eth_spot': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'btc_spot': openapi.Schema(type=openapi.TYPE_NUMBER)
                    }
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Результат проверки алертов",
                examples={
                    "application/json": {
                        "success": True,
                        "triggered_alerts": [
                            {
                                "id": 1,
                                "name": "ETH выше 4000",
                                "symbol": "ETHUSDT",
                                "condition": "above",
                                "target_price": 4000.00,
                                "current_price": 4010.50,
                                "trigger_message": "ETHUSDT превысила $4000.00. Текущая цена: $4010.50"
                            }
                        ],
                        "checked_count": 5,
                        "triggered_count": 1
                    }
                }
            )
        },
        security=[{'Bearer': []}],
        tags=['Alerts']
    )
    def post(self, request):
        """
        Обрабатывает POST запрос для проверки алертов.

        Args:
            request: HTTP запрос с JSON телом содержащим текущие цены

        Returns:
            JsonResponse: результат проверки алертов
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется аутентификация'
                }, status=401)

            data = json.loads(request.body)
            current_prices = data.get('prices', {})

            triggered_alerts = []

            # Получаем только активные алерты текущего пользователя
            active_alerts = PriceAlert.objects.filter(
                user=request.user,
                status='active'
            )

            for alert in active_alerts:
                current_price = None
                if alert.symbol == 'ETHUSDT':
                    current_price = current_prices.get('eth_spot')
                elif alert.symbol == 'BTCUSDT':
                    current_price = current_prices.get('btc_spot')

                # МГНОВЕННАЯ ПРОВЕРКА - если цена достигла цели
                if current_price and alert.check_condition(current_price):
                    # Алерт сработал МГНОВЕННО
                    if alert.trigger(current_price):
                        triggered_alerts.append({
                            'id': alert.id,
                            'name': alert.name,
                            'symbol': alert.symbol,
                            'condition': alert.condition,
                            'target_price': alert.target_price,
                            'current_price': current_price,
                            'trigger_message': alert.get_trigger_message(),
                            'triggered_at': alert.triggered_at.strftime(
                                '%d.%m.%Y %H:%M') if alert.triggered_at else None
                        })

            logger.info(f"Проверка алертов: {len(active_alerts)} активных, {len(triggered_alerts)} сработало")

            return JsonResponse({
                'success': True,
                'triggered_alerts': triggered_alerts,
                'checked_count': len(active_alerts),
                'triggered_count': len(triggered_alerts)
            })

        except Exception as e:
            logger.error(f"Alert check error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


# Дополнительный endpoint для ручной проверки алертов
@method_decorator(login_required, name='dispatch')
class ManualCheckAlertsView(View):
    """
    API для ручной проверки алертов с текущими рыночными ценами.

    Самостоятельно получает текущие цены и проверяет алерты.
    """

    @swagger_auto_schema(
        operation_description="""
        Ручная проверка всех активных алертов.

        Самостоятельно получает текущие рыночные цены и проверяет все активные алерты.
        Удобно для разовых проверок без передачи цен с клиента.

        Требуется аутентификация JWT токеном.
        """,
        responses={
            200: openapi.Response(
                description="Результат ручной проверки",
                examples={
                    "application/json": {
                        "success": True,
                        "triggered_alerts": [
                            {
                                "id": 1,
                                "name": "ETH выше 4000",
                                "message": "ETHUSDT превысила $4000.00. Текущая цена: $4010.50"
                            }
                        ],
                        "message": "Проверено 5 алертов, сработало: 1"
                    }
                }
            )
        },
        security=[{'Bearer': []}],
        tags=['Alerts']
    )
    def get(self, request):
        """
        Обрабатывает GET запрос для ручной проверки алертов.

        Returns:
            JsonResponse: результат проверки
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется аутентификация'
                }, status=401)

            # Получаем текущие цены
            current_prices = api.get_correct_prices()

            triggered_alerts = []
            active_alerts = PriceAlert.objects.filter(
                user=request.user,
                status='active'
            )

            for alert in active_alerts:
                current_price = None
                if alert.symbol == 'ETHUSDT':
                    current_price = current_prices.get('eth_spot')
                elif alert.symbol == 'BTCUSDT':
                    current_price = current_prices.get('btc_spot')

                if current_price and alert.check_condition(current_price):
                    if alert.trigger(current_price):
                        triggered_alerts.append({
                            'id': alert.id,
                            'name': alert.name,
                            'message': alert.get_trigger_message()
                        })

            return JsonResponse({
                'success': True,
                'triggered_alerts': triggered_alerts,
                'message': f'Проверено {len(active_alerts)} алертов, сработало: {len(triggered_alerts)}'
            })

        except Exception as e:
            logger.error(f"Manual alert check error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)