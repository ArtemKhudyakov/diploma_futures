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
        """Построение моделей линейной регрессии"""
        eth_spot = self.historical_data['eth_spot']
        btc_spot = self.historical_data['btc_spot']
        eth_futures = self.historical_data['eth_futures']
        btc_futures = self.historical_data['btc_futures']

        # Модель для спота
        if len(eth_spot) >= 60 and len(btc_spot) >= 60:
            eth_array = np.array(eth_spot)
            btc_array = np.array(btc_spot)

            X = np.column_stack([np.ones(len(btc_array)), btc_array])
            coefficients = np.linalg.lstsq(X, eth_array, rcond=None)[0]

            self.spot_intercept = coefficients[0]
            self.spot_coef = coefficients[1]

            logger.info(
                f"Спот модель ({len(eth_spot)} точек): ETH = {self.spot_intercept:.2f} + {self.spot_coef:.6f}×BTC")

        # Модель для фьючерсов
        if len(eth_futures) >= 60 and len(btc_futures) >= 60:
            eth_array = np.array(eth_futures)
            btc_array = np.array(btc_futures)

            X = np.column_stack([np.ones(len(btc_array)), btc_array])
            coefficients = np.linalg.lstsq(X, eth_array, rcond=None)[0]

            self.futures_intercept = coefficients[0]
            self.futures_coef = coefficients[1]

            logger.info(
                f"Фьючерс модель ({len(eth_futures)} точек): ETH = {self.futures_intercept:.2f} + {self.futures_coef:.6f}×BTC")

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
        Полный анализ движения цен
        Возвращает словарь с результатами анализа
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

        # Расчет собственного движения если модели готовы
        if (self.spot_coef is not None and
                current_prices.get('eth_spot') and
                current_prices.get('btc_spot')):

            # Предсказанная цена по модели
            predicted_eth_spot = self.spot_intercept + self.spot_coef * current_prices['btc_spot']

            # Собственное движение
            actual_eth_spot = current_prices['eth_spot']
            result['spot_intrinsic'] = ((actual_eth_spot - predicted_eth_spot) / predicted_eth_spot) * 100

            # Влияние BTC и собственное движение ETH (если есть исторические данные)
            eth_history = self.historical_data['eth_spot']
            btc_history = self.historical_data['btc_spot']

            if len(eth_history) >= 2:
                # Ожидаемое движение (по модели)
                last_btc_price = btc_history[-1] if btc_history else current_prices['btc_spot']
                predicted_previous_eth = self.spot_intercept + self.spot_coef * last_btc_price
                last_eth_price = eth_history[-1] if eth_history else current_prices['eth_spot']

                expected_move = ((predicted_eth_spot - predicted_previous_eth) / predicted_previous_eth) * 100
                actual_total_move = ((actual_eth_spot - last_eth_price) / last_eth_price) * 100

                # Распределение влияния
                if actual_total_move != 0:
                    result['spot_btc_influence'] = (expected_move / actual_total_move) * 100
                    result['spot_eth_own'] = (result['spot_intrinsic'] / actual_total_move) * 100

        # Аналогично для фьючерсов
        if (self.futures_coef is not None and
                current_prices.get('eth_futures') and
                current_prices.get('btc_futures')):
            predicted_eth_futures = self.futures_intercept + self.futures_coef * current_prices['btc_futures']
            actual_eth_futures = current_prices['eth_futures']
            result['futures_intrinsic'] = ((actual_eth_futures - predicted_eth_futures) / predicted_eth_futures) * 100

        result['models_ready'] = self.spot_coef is not None

        return result

    def get_analysis_report(self, current_prices: Dict) -> str:
        """
        Формирование текстового отчета анализа
        """
        analysis = self.analyze_movement(current_prices)

        report = []
        report.append("📊 АНАЛИЗ ДВИЖЕНИЯ ЦЕН")
        report.append("=" * 50)

        # Базис
        report.append(f"📈 БАЗИС (Futures - Spot):")
        report.append(f"   ETH: {analysis['basis_eth']:+.3f}%")
        report.append(f"   BTC: {analysis['basis_btc']:+.3f}%")

        if analysis['models_ready']:
            report.append(f"\n🎯 СОБСТВЕННОЕ ДВИЖЕНИЕ ETH:")
            report.append(f"   Spot: {analysis['spot_intrinsic']:+.3f}%")
            report.append(f"   Futures: {analysis['futures_intrinsic']:+.3f}%")

            if analysis['spot_btc_influence'] != 0:
                report.append(f"\n📊 РАСПРЕДЕЛЕНИЕ ВЛИЯНИЯ (Spot):")
                report.append(f"   За счет BTC: {analysis['spot_btc_influence']:.1f}%")
                report.append(f"   Собственное движение ETH: {analysis['spot_eth_own']:.1f}%")

                # Простое объяснение
                if analysis['spot_intrinsic'] > 1.0:
                    report.append(f"   🚀 ETH растет самостоятельно!")
                elif analysis['spot_intrinsic'] < -1.0:
                    report.append(f"   🔻 ETH падает самостоятельно!")
                else:
                    report.append(f"   🔗 Движение ETH соответствует BTC")

        else:
            report.append(f"\n🔄 Модели в процессе обучения...")

        report.append("=" * 50)
        return "\n".join(report)

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