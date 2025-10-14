# import numpy as np
# from collections import deque
# from typing import Optional, Dict
# import logging
# from datetime import datetime
#
# logger = logging.getLogger(__name__)
#
#
# class PriceAnalyzer:
#     def __init__(self, window_size: int = 1440, use_database: bool = True):
#         self.window_size = window_size
#         self.use_database = use_database
#
#         # Данные для анализа
#         self.eth_spot_prices = deque(maxlen=window_size)
#         self.eth_futures_prices = deque(maxlen=window_size)
#         self.btc_spot_prices = deque(maxlen=window_size)
#         self.btc_futures_prices = deque(maxlen=window_size)
#
#         # Модели регрессии
#         self.spot_regression_coef = None
#         self.spot_regression_intercept = None
#         self.futures_regression_coef = None
#         self.futures_regression_intercept = None
#
#         # Если используем БД - загружаем исторические данные
#         if use_database:
#             self._load_historical_data()
#
#     def _load_historical_data(self):
#         """
#         Загрузка исторических данных из БД при инициализации
#         """
#         try:
#             from screener.services.history_service import HistoryService
#
#             history_service = HistoryService()
#
#             # Загружаем последние данные для каждого инструмента
#             eth_spot = history_service.get_latest_prices('ETHUSDT', 'spot', self.window_size)
#             btc_spot = history_service.get_latest_prices('BTCUSDT', 'spot', self.window_size)
#             eth_futures = history_service.get_latest_prices('ETHUSDT', 'linear', self.window_size)
#             btc_futures = history_service.get_latest_prices('BTCUSDT', 'linear', self.window_size)
#
#             # Заполняем очереди
#             for price in eth_spot:
#                 self.eth_spot_prices.append(price)
#             for price in btc_spot:
#                 self.btc_spot_prices.append(price)
#             for price in eth_futures:
#                 self.eth_futures_prices.append(price)
#             for price in btc_futures:
#                 self.btc_futures_prices.append(price)
#
#             # Сразу обновляем модели если данных достаточно
#             if len(self.eth_spot_prices) >= 60:
#                 self.update_regression_models()
#
#             logger.info(f"Загружено исторических данных: "
#                         f"ETH Spot: {len(self.eth_spot_prices)}, "
#                         f"BTC Spot: {len(self.btc_spot_prices)}, "
#                         f"ETH Futures: {len(self.eth_futures_prices)}, "
#                         f"BTC Futures: {len(self.btc_futures_prices)}")
#
#         except Exception as e:
#             logger.error(f"Ошибка загрузки исторических данных: {e}")
#
#     def update_data(self, prices: Dict[str, float]):
#         """Обновление данных готовыми ценами из BybitClient"""
#         if prices.get('eth_spot'):
#             self.eth_spot_prices.append(prices['eth_spot'])
#         if prices.get('eth_futures'):
#             self.eth_futures_prices.append(prices['eth_futures'])
#         if prices.get('btc_spot'):
#             self.btc_spot_prices.append(prices['btc_spot'])
#         if prices.get('btc_futures'):
#             self.btc_futures_prices.append(prices['btc_futures'])
#
#     def update_regression_models(self):
#         """Обновление моделей линейной регрессии"""
#         # Модель для спотовых цен
#         if len(self.eth_spot_prices) >= 60 and len(self.btc_spot_prices) >= 60:
#             eth_spot_array = np.array(self.eth_spot_prices)
#             btc_spot_array = np.array(self.btc_spot_prices)
#
#             X_spot = np.column_stack([np.ones(len(btc_spot_array)), btc_spot_array])
#             coefficients_spot = np.linalg.lstsq(X_spot, eth_spot_array, rcond=None)[0]
#
#             self.spot_regression_intercept = coefficients_spot[0]
#             self.spot_regression_coef = coefficients_spot[1]
#
#             logger.info(
#                 f"Spot модель: ETH = {self.spot_regression_intercept:.2f} + {self.spot_regression_coef:.4f} * BTC")
#
#         # Модель для фьючерсных цен
#         if len(self.eth_futures_prices) >= 60 and len(self.btc_futures_prices) >= 60:
#             eth_futures_array = np.array(self.eth_futures_prices)
#             btc_futures_array = np.array(self.btc_futures_prices)
#
#             X_futures = np.column_stack([np.ones(len(btc_futures_array)), btc_futures_array])
#             coefficients_futures = np.linalg.lstsq(X_futures, eth_futures_array, rcond=None)[0]
#
#             self.futures_regression_intercept = coefficients_futures[0]
#             self.futures_regression_coef = coefficients_futures[1]
#
#             logger.info(
#                 f"Futures модель: ETH = {self.futures_regression_intercept:.2f} + {self.futures_regression_coef:.4f} * BTC")
#
#     def calculate_intrinsic_movement(self, current_prices: Dict[str, float]) -> Dict[str, float]:
#         """Расчет собственного движения для спота и фьючерсов"""
#         result = {}
#
#         # Собственное движение спота
#         if (self.spot_regression_coef is not None and
#                 current_prices.get('eth_spot') and
#                 current_prices.get('btc_spot')):
#             predicted_eth_spot = (self.spot_regression_intercept +
#                                   self.spot_regression_coef * current_prices['btc_spot'])
#             spot_intrinsic = ((current_prices['eth_spot'] - predicted_eth_spot) / predicted_eth_spot) * 100
#             result['spot_intrinsic'] = spot_intrinsic
#
#         # Собственное движение фьючерсов
#         if (self.futures_regression_coef is not None and
#                 current_prices.get('eth_futures') and
#                 current_prices.get('btc_futures')):
#             predicted_eth_futures = (self.futures_regression_intercept +
#                                      self.futures_regression_coef * current_prices['btc_futures'])
#             futures_intrinsic = ((current_prices['eth_futures'] - predicted_eth_futures) / predicted_eth_futures) * 100
#             result['futures_intrinsic'] = futures_intrinsic
#
#         return result
#
#     def check_price_changes(self) -> Dict[str, Optional[dict]]:
#         """Проверка изменений цен за 60 минут"""
#         alerts = {}
#
#         # Проверка спотовых цен ETH
#         if len(self.eth_spot_prices) >= 60:
#             current_spot = self.eth_spot_prices[-1]
#             spot_60min_ago = self.eth_spot_prices[-60]
#             spot_change = ((current_spot - spot_60min_ago) / spot_60min_ago) * 100
#
#             if abs(spot_change) >= 1.0:
#                 alerts['eth_spot'] = {
#                     'change_pct': spot_change,
#                     'current_price': current_spot,
#                     'price_60min_ago': spot_60min_ago,
#                     'type': 'spot'
#                 }
#
#         # Проверка фьючерсных цен ETH
#         if len(self.eth_futures_prices) >= 60:
#             current_futures = self.eth_futures_prices[-1]
#             futures_60min_ago = self.eth_futures_prices[-60]
#             futures_change = ((current_futures - futures_60min_ago) / futures_60min_ago) * 100
#
#             if abs(futures_change) >= 1.0:
#                 alerts['eth_futures'] = {
#                     'change_pct': futures_change,
#                     'current_price': current_futures,
#                     'price_60min_ago': futures_60min_ago,
#                     'type': 'futures'
#                 }
#
#         return alerts


import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PriceAnalyzer:
    """
    Анализатор для расчета базиса и собственного движения
    """

    def __init__(self):
        self.spot_coef = None
        self.spot_intercept = None
        self.futures_coef = None
        self.futures_intercept = None

        # Исторические данные для регрессии
        self.eth_spot_history = []
        self.btc_spot_history = []
        self.eth_futures_history = []
        self.btc_futures_history = []

    def add_historical_data(self, eth_spot: list, btc_spot: list,
                            eth_futures: list, btc_futures: list):
        """
        Добавление исторических данных для построения моделей
        """
        self.eth_spot_history = eth_spot
        self.btc_spot_history = btc_spot
        self.eth_futures_history = eth_futures
        self.btc_futures_history = btc_futures

        # Строим модели регрессии
        self._build_regression_models()

    def _build_regression_models(self):
        """Построение моделей линейной регрессии"""
        # Модель для спота
        if len(self.eth_spot_history) >= 60 and len(self.btc_spot_history) >= 60:
            eth_array = np.array(self.eth_spot_history)
            btc_array = np.array(self.btc_spot_history)

            X = np.column_stack([np.ones(len(btc_array)), btc_array])
            coefficients = np.linalg.lstsq(X, eth_array, rcond=None)[0]

            self.spot_intercept = coefficients[0]
            self.spot_coef = coefficients[1]

            logger.info(f"Спот модель: ETH = {self.spot_intercept:.2f} + {self.spot_coef:.6f}×BTC")

        # Модель для фьючерсов
        if len(self.eth_futures_history) >= 60 and len(self.btc_futures_history) >= 60:
            eth_array = np.array(self.eth_futures_history)
            btc_array = np.array(self.btc_futures_history)

            X = np.column_stack([np.ones(len(btc_array)), btc_array])
            coefficients = np.linalg.lstsq(X, eth_array, rcond=None)[0]

            self.futures_intercept = coefficients[0]
            self.futures_coef = coefficients[1]

            logger.info(f"Фьючерс модель: ETH = {self.futures_intercept:.2f} + {self.futures_coef:.6f}×BTC")

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

            # Влияние BTC (ожидаемое движение)
            expected_move = ((predicted_eth_spot - self.eth_spot_history[-1]) / self.eth_spot_history[-1]) * 100
            actual_total_move = ((actual_eth_spot - self.eth_spot_history[-1]) / self.eth_spot_history[-1]) * 100

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
                    report.append(f"   💚 ETH растет самостоятельно!")
                elif analysis['spot_intrinsic'] < -1.0:
                    report.append(f"   💔 ETH падает самостоятельно!")
                else:
                    report.append(f"   💙 Движение ETH соответствует BTC")

        else:
            report.append(f"\n⏳ Модели в процессе обучения...")

        report.append("=" * 50)
        return "\n".join(report)