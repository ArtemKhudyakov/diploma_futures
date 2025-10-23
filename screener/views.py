from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views import View
import logging
from screener.services.bybit_api import BybitAPI
from screener.services.price_analyzer import PriceAnalyzer
import math
from datetime import datetime, timezone
from screener.services.intrinsic_chart_service import intrinsic_chart_service
from django.core.cache import cache

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import PriceAlert
from .forms import PriceAlertForm
import json

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
            return JsonResponse({'success': False, 'error': str(e)})

    def _get_prices_by_analysis_type(self, analysis_type, futures_type):
        """Получает цены в зависимости от типа анализа"""
        prices = {}

        # Всегда получаем спотовые цены для базового анализа
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
        """Загрузка исторических данных с учетом типа анализа"""
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
        """Получает данные для маленьких таймфреймов"""
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
        """Рассчитывает сколько дней истории нужно для указанного количества свечей"""
        candles_per_day = {
            '1m': 1440, '3m': 480, '5m': 288, '15m': 96, '30m': 48,
            '1h': 24, '2h': 12, '4h': 6, '6h': 4, '12h': 2,
            '1d': 1, '1w': 0.14, '1M': 0.03
        }

        days_needed = (limit / candles_per_day.get(timeframe, 24)) + 1
        return min(math.ceil(days_needed), 60)

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
                'time': kline['timestamp'] // 1000,
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
            data_type = request.GET.get('data_type', 'spot')

            logger.info(f"📌 DEBUG: Начало загрузки графика, days={days}, timeframe={timeframe}, data_type={data_type}")

            # Оптимизация таймфрейма
            optimized_timeframe = self._get_optimized_timeframe(days)
            if optimized_timeframe != timeframe:
                timeframe = optimized_timeframe

            # Определяем категорию для данных
            category = "spot" if data_type == "spot" else request.GET.get('futures_type', 'linear')

            logger.info(f"📌 DEBUG: Загрузка данных с таймфреймом {timeframe}, категория: {category}")

            # Загрузка данных
            eth_klines = api.get_historical_data("ETHUSDT", category, timeframe, days)
            btc_klines = api.get_historical_data("BTCUSDT", category, timeframe, days)

            logger.info(f"📌 DEBUG: Данные загружены - ETH: {len(eth_klines)}, BTC: {len(btc_klines)}")

            if not eth_klines or not btc_klines:
                logger.error(f"📌 DEBUG: Нет данных! ETH: {len(eth_klines)}, BTC: {len(btc_klines)}")
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
                logger.info(f"📌 DEBUG: Данные сокращены до {len(eth_klines)} точек")

            # Проверяем, что есть достаточно данных для анализа
            if len(eth_klines) < 2:
                logger.error(f"📌 DEBUG: Недостаточно данных для анализа! Всего точек: {len(eth_klines)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Недостаточно данных для анализа. Нужно минимум 2 точки, получено: {len(eth_klines)}'
                })

            logger.info("📌 DEBUG: Начинаем построение графика...")
            intrinsic_data = intrinsic_chart_service.build_intrinsic_chart_data(
                eth_klines, btc_klines
            )

            logger.info(f"📌 DEBUG: График построен. Получено точек: {len(intrinsic_data)}")

            if not intrinsic_data:
                logger.error("📌 DEBUG: IntrinsicChartService вернул пустой результат!")
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
            logger.error(f"📌 DEBUG: IntrinsicMovementAPIView error: {e}", exc_info=True)
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


# АЛЕРТЫ - ИСПРАВЛЕННЫЕ ВЕРСИИ
@method_decorator(login_required, name='dispatch')
class AlertCreateAPIView(View):
    def post(self, request):
        """Создание нового алерта"""
        try:
            # Проверяем авторизацию
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется авторизация для создания алертов'
                })

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
                })

            if not symbol or symbol not in ['ETHUSDT', 'BTCUSDT']:
                return JsonResponse({
                    'success': False,
                    'error': 'Выберите корректный символ'
                })

            if not condition or condition not in ['above', 'below']:
                return JsonResponse({
                    'success': False,
                    'error': 'Выберите корректное условие'
                })

            try:
                target_price = float(target_price)
                if target_price <= 0:
                    raise ValueError("Цена должна быть положительной")
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'error': 'Введите корректную цену'
                })

            # Создаем алерт
            alert = PriceAlert(
                user=request.user,
                name=name,
                symbol=symbol,
                condition=condition,
                target_price=target_price
            )
            alert.save()

            # ПРОВЕРЯЕМ МГНОВЕННОЕ СРАБАТЫВАНИЕ ПРИ СОЗДАНИИ
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
                'message': 'Алерт успешно создан' + (' (сразу сработал!)' if show_immediate_alert else ''),
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
            })

        except Exception as e:
            logger.error(f"Alert creation error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(login_required, name='dispatch')
class AlertListAPIView(View):
    def get(self, request):
        """Получение списка алертов пользователя"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется авторизация'
                })

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
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(login_required, name='dispatch')
class AlertDeleteAPIView(View):
    def delete(self, request, alert_id):
        """Удаление алерта"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется авторизация'
                })

            alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
            alert.delete()

            return JsonResponse({
                'success': True,
                'message': 'Алерт удален'
            })

        except Exception as e:
            logger.error(f"Alert deletion error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(login_required, name='dispatch')
class CheckAlertsView(View):
    def post(self, request):
        """Проверка срабатывания алертов - МГНОВЕННОЕ срабатывание при достижении цены"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется авторизация'
                })

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

            logger.info(f"🔔 Проверка алертов: {len(active_alerts)} активных, {len(triggered_alerts)} сработало")

            return JsonResponse({
                'success': True,
                'triggered_alerts': triggered_alerts,
                'checked_count': len(active_alerts),
                'triggered_count': len(triggered_alerts)
            })

        except Exception as e:
            logger.error(f"Alert check error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


# Дополнительный endpoint для ручной проверки алертов
@method_decorator(login_required, name='dispatch')
class ManualCheckAlertsView(View):
    def get(self, request):
        """Ручная проверка всех алертов пользователя"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Требуется авторизация'
                })

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
            return JsonResponse({'success': False, 'error': str(e)})