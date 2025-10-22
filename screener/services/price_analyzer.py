import numpy as np
from typing import Dict, Optional
import logging
import math

logger = logging.getLogger(__name__)


class PriceAnalyzer:
    """
    Анализатор для расчета собственного движения с настраиваемой базой
    """

    def __init__(self):
        self.spot_coef = None
        self.spot_intercept = None
        self.futures_coef = None
        self.futures_intercept = None

        # Храним все исторические данные
        self.historical_data = {
            'eth_spot': [],
            'btc_spot': [],
            'eth_futures': [],
            'btc_futures': []
        }

        # Настройки по умолчанию
        self.training_days = 7  # дней для анализа

    def set_training_period(self, days: int):
        """Установка периода для анализа"""
        self.training_days = days
        logger.info(f"Установлен период анализа: {days} дней")

    def add_historical_data(self, eth_spot: list, btc_spot: list,
                            eth_futures: list, btc_futures: list):
        """
        Добавление исторических данных
        """
        self.historical_data['eth_spot'] = eth_spot
        self.historical_data['btc_spot'] = btc_spot
        self.historical_data['eth_futures'] = eth_futures
        self.historical_data['btc_futures'] = btc_futures

        self._build_regression_models()

    def _build_regression_models(self):
        """Построение моделей линейной регрессии с улучшенной обработкой ошибок"""
        eth_spot = self.historical_data['eth_spot']
        btc_spot = self.historical_data['btc_spot']
        eth_futures = self.historical_data['eth_futures']
        btc_futures = self.historical_data['btc_futures']

        logger.info(f"🔧 ПОСТРОЕНИЕ МОДЕЛЕЙ: ETH spot={len(eth_spot)}, BTC spot={len(btc_spot)}")

        # Модель для спота
        if len(eth_spot) >= 2 and len(btc_spot) >= 2:  # Минимум 2 точки для регрессии
            try:
                eth_array = np.array(eth_spot)
                btc_array = np.array(btc_spot)

                # Проверяем, что все значения конечные
                if not np.all(np.isfinite(eth_array)) or not np.all(np.isfinite(btc_array)):
                    logger.error("❌ В данных есть бесконечные или NaN значения")
                    return

                # Проверяем, что массивы не пустые
                if len(eth_array) == 0 or len(btc_array) == 0:
                    logger.error("❌ Пустые массивы данных")
                    return

                # Создаем матрицу признаков [1, btc_price] для каждой точки
                X = np.column_stack([np.ones(len(btc_array)), btc_array])

                # Используем метод наименьших квадратов с обработкой ошибок
                coefficients, residuals, rank, s = np.linalg.lstsq(X, eth_array, rcond=None)

                if len(coefficients) >= 2:
                    self.spot_intercept = coefficients[0]
                    self.spot_coef = coefficients[1]
                    logger.info(
                        f"✅ Спот модель ({len(eth_spot)} точек): ETH = {self.spot_intercept:.2f} + {self.spot_coef:.6f}×BTC"
                    )
                else:
                    logger.error("❌ Не удалось вычислить коэффициенты регрессии")

            except Exception as e:
                logger.error(f"❌ Ошибка построения спот модели: {e}")
                # Пробуем альтернативный метод
                self._build_simple_regression(eth_spot, btc_spot, 'spot')

        # Модель для фьючерсов (аналогично)
        if len(eth_futures) >= 2 and len(btc_futures) >= 2:
            try:
                eth_array = np.array(eth_futures)
                btc_array = np.array(btc_futures)

                if not np.all(np.isfinite(eth_array)) or not np.all(np.isfinite(btc_array)):
                    logger.error("❌ В фьючерсных данных есть бесконечные или NaN значения")
                    return

                X = np.column_stack([np.ones(len(btc_array)), btc_array])
                coefficients, residuals, rank, s = np.linalg.lstsq(X, eth_array, rcond=None)

                if len(coefficients) >= 2:
                    self.futures_intercept = coefficients[0]
                    self.futures_coef = coefficients[1]
                    logger.info(
                        f"✅ Фьючерс модель ({len(eth_futures)} точек): ETH = {self.futures_intercept:.2f} + {self.futures_coef:.6f}×BTC"
                    )

            except Exception as e:
                logger.error(f"❌ Ошибка построения фьючерс модели: {e}")
                self._build_simple_regression(eth_futures, btc_futures, 'futures')

    def _build_simple_regression(self, eth_prices, btc_prices, model_type):
        """Упрощенный метод построения регрессии через ковариацию"""
        try:
            if len(eth_prices) < 2:
                return

            eth_array = np.array(eth_prices)
            btc_array = np.array(btc_prices)

            # Простая линейная регрессия: beta = cov(X,Y) / var(X)
            covariance = np.cov(btc_array, eth_array)[0, 1]
            variance = np.var(btc_array)

            if variance == 0:
                logger.error(f"❌ Нулевая дисперсия в данных для {model_type}")
                return

            beta = covariance / variance
            alpha = np.mean(eth_array) - beta * np.mean(btc_array)

            if model_type == 'spot':
                self.spot_intercept = alpha
                self.spot_coef = beta
            else:
                self.futures_intercept = alpha
                self.futures_coef = beta

            logger.info(f"✅ Упрощенная {model_type} модель: ETH = {alpha:.2f} + {beta:.6f}×BTC")

        except Exception as e:
            logger.error(f"❌ Ошибка в упрощенной регрессии для {model_type}: {e}")

    def get_analysis_info(self) -> Dict:
        """Информация о текущих настройках анализа"""
        return {
            'training_days': self.training_days,
            'data_points_spot': len(self.historical_data['eth_spot']),
            'data_points_futures': len(self.historical_data['eth_futures']),
            'spot_model_ready': self.spot_coef is not None,
            'futures_model_ready': self.futures_coef is not None
        }

    def calculate_basis(self, eth_spot: float, eth_futures: float) -> float:
        """
        Расчет базиса (разницы между фьючерсом и спотом)
        """
        if eth_spot and eth_futures:
            basis = ((eth_futures - eth_spot) / eth_spot) * 100
            return basis
        return 0.0

    def analyze_movement(self, current_prices: Dict) -> Dict:
        """
        Полный анализ движения цен для spot и futures
        """
        result = {
            'basis_eth': 0.0,
            'basis_btc': 0.0,
            'spot_intrinsic': 0.0,
            'futures_intrinsic': 0.0,
            'spot_btc_influence': 0.0,
            'futures_btc_influence': 0.0,
            'spot_eth_own': 0.0,
            'futures_eth_own': 0.0,
            'models_ready': False
        }

        # Расчет базиса
        if current_prices.get('eth_spot') and current_prices.get('eth_futures'):
            result['basis_eth'] = self.calculate_basis(
                current_prices['eth_spot'],
                current_prices['eth_futures']
            )

        if current_prices.get('btc_spot') and current_prices.get('btc_futures'):
            result['basis_btc'] = self.calculate_basis(
                current_prices['btc_spot'],
                current_prices['btc_futures']
            )

        # Spot анализ
        if (self.spot_coef is not None and
                current_prices.get('eth_spot') and
                current_prices.get('btc_spot')):

            # Предсказанная цена по модели
            predicted_eth_spot = self.spot_intercept + self.spot_coef * current_prices['btc_spot']
            actual_eth_spot = current_prices['eth_spot']

            # Собственное движение
            result['spot_intrinsic'] = ((actual_eth_spot - predicted_eth_spot) / predicted_eth_spot) * 100

            # Влияние BTC и собственная сила (исправленная логика)
            eth_history = self.historical_data['eth_spot']
            btc_history = self.historical_data['btc_spot']

            if len(eth_history) >= 2 and len(btc_history) >= 2:
                # Предыдущие цены
                last_btc_price = btc_history[-1]
                last_eth_price = eth_history[-1]

                # Предсказанная предыдущая цена
                predicted_previous_eth = self.spot_intercept + self.spot_coef * last_btc_price

                # Фактическое общее движение
                actual_total_move = ((actual_eth_spot - last_eth_price) / last_eth_price) * 100

                # Ожидаемое движение по модели
                expected_move = ((predicted_eth_spot - predicted_previous_eth) / predicted_previous_eth) * 100

                # Собственное движение за период
                intrinsic_move_period = ((actual_eth_spot - last_eth_price) - (
                            predicted_eth_spot - predicted_previous_eth)) / last_eth_price * 100

                # Исправленный расчет влияния (сумма = 100%)
                if abs(actual_total_move) > 0.001:  # Избегаем деления на ноль
                    total_impact = abs(expected_move) + abs(intrinsic_move_period)

                    if total_impact > 0:
                        # Распределяем влияние пропорционально
                        btc_share = (abs(expected_move) / total_impact) * 100
                        eth_share = (abs(intrinsic_move_period) / total_impact) * 100

                        # Сохраняем знаки для направления
                        if expected_move < 0:
                            btc_share = -btc_share
                        if intrinsic_move_period < 0:
                            eth_share = -eth_share

                        result['spot_btc_influence'] = btc_share
                        result['spot_eth_own'] = eth_share
                    else:
                        # Если нет движения - равное распределение
                        result['spot_btc_influence'] = 50
                        result['spot_eth_own'] = 50
                else:
                    # Если движение очень маленькое
                    result['spot_btc_influence'] = 50
                    result['spot_eth_own'] = 50

        # Futures анализ (аналогично spot)
        if (self.futures_coef is not None and
                current_prices.get('eth_futures') and
                current_prices.get('btc_futures')):

            predicted_eth_futures = self.futures_intercept + self.futures_coef * current_prices['btc_futures']
            actual_eth_futures = current_prices['eth_futures']
            result['futures_intrinsic'] = ((actual_eth_futures - predicted_eth_futures) / predicted_eth_futures) * 100

            # Влияние BTC Futures и собственная сила ETH Futures
            eth_futures_history = self.historical_data['eth_futures']
            btc_futures_history = self.historical_data['btc_futures']

            if len(eth_futures_history) >= 2 and len(btc_futures_history) >= 2:
                # Предыдущие цены фьючерсов
                last_btc_futures = btc_futures_history[-1]
                last_eth_futures = eth_futures_history[-1]

                # Предсказанная предыдущая цена фьючерсов
                predicted_previous_eth_futures = self.futures_intercept + self.futures_coef * last_btc_futures

                # Фактическое общее движение фьючерсов
                actual_futures_total_move = ((actual_eth_futures - last_eth_futures) / last_eth_futures) * 100

                # Ожидаемое движение фьючерсов по модели
                expected_futures_move = ((
                                                     predicted_eth_futures - predicted_previous_eth_futures) / predicted_previous_eth_futures) * 100

                # Собственное движение фьючерсов за период
                futures_intrinsic_move_period = ((actual_eth_futures - last_eth_futures) - (
                            predicted_eth_futures - predicted_previous_eth_futures)) / last_eth_futures * 100

                # Исправленный расчет влияния для фьючерсов
                if abs(actual_futures_total_move) > 0.001:
                    futures_total_impact = abs(expected_futures_move) + abs(futures_intrinsic_move_period)

                    if futures_total_impact > 0:
                        futures_btc_share = (abs(expected_futures_move) / futures_total_impact) * 100
                        futures_eth_share = (abs(futures_intrinsic_move_period) / futures_total_impact) * 100

                        if expected_futures_move < 0:
                            futures_btc_share = -futures_btc_share
                        if futures_intrinsic_move_period < 0:
                            futures_eth_share = -futures_eth_share

                        result['futures_btc_influence'] = futures_btc_share
                        result['futures_eth_own'] = futures_eth_share
                    else:
                        result['futures_btc_influence'] = 50
                        result['futures_eth_own'] = 50
                else:
                    result['futures_btc_influence'] = 50
                    result['futures_eth_own'] = 50

        result['models_ready'] = self.spot_coef is not None or self.futures_coef is not None

        return result

    def get_market_scenario(self, analysis: Dict) -> Dict:
        """
        Преобразует технический анализ в понятный рыночный сценарий
        """
        scenario = {
            'eth_strength': 0.0,  # Сила ETH от -100% до +100%
            'market_scenario': 'neutral',
            'eth_performance': 'average',
            'explanation': 'Анализ в процессе...',
            'simple_breakdown': {
                'btc_influence': 50,
                'eth_own_power': 50
            }
        }

        if not analysis.get('models_ready'):
            return scenario

        # Используем существующий spot_intrinsic для определения силы
        intrinsic_move = analysis.get('spot_intrinsic', 0)

        # Нормализуем силу ETH (-100% до +100%)
        strength = max(min(intrinsic_move / 3.0, 100), -100)
        scenario['eth_strength'] = strength

        # Определяем сценарий на основе собственного движения
        if intrinsic_move > 2.0:
            scenario.update({
                'market_scenario': 'bullish_eth',
                'eth_performance': 'excellent',
                'explanation': f'🚀 ETH показывает СИЛУ! Растет на {intrinsic_move:.1f}% лучше чем обычно следует за BTC'
            })
        elif intrinsic_move > 0.5:
            scenario.update({
                'market_scenario': 'slightly_bullish_eth',
                'eth_performance': 'good',
                'explanation': f'📈 ETH немного опережает BTC (+{intrinsic_move:.1f}%)'
            })
        elif intrinsic_move > -0.5:
            scenario.update({
                'market_scenario': 'neutral',
                'eth_performance': 'average',
                'explanation': '⚖️ ETH движется в соответствии с BTC'
            })
        elif intrinsic_move > -2.0:
            scenario.update({
                'market_scenario': 'slightly_bearish_eth',
                'eth_performance': 'weak',
                'explanation': f'📉 ETH немного отстает от BTC ({intrinsic_move:.1f}%)'
            })
        else:
            scenario.update({
                'market_scenario': 'bearish_eth',
                'eth_performance': 'poor',
                'explanation': f'🔻 ETH показывает СЛАБОСТЬ! Отстает на {abs(intrinsic_move):.1f}% от BTC'
            })

        # Упрощенное распределение влияния (всегда в сумме 100%)
        if analysis.get('spot_btc_influence') and analysis.get('spot_eth_own'):
            btc_influence = min(abs(analysis['spot_btc_influence']), 100)  # ← math.min → min
            eth_own = min(abs(analysis['spot_eth_own']), 100)  # ← math.min → min
            total = btc_influence + eth_own

            if total > 0:
                scenario['simple_breakdown'] = {
                    'btc_influence': round((btc_influence / total) * 100),  # ← Math.round → round
                    'eth_own_power': round((eth_own / total) * 100)  # ← Math.round → round
                }

        return scenario