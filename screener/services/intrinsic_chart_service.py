import logging
from typing import List, Dict
from screener.services.price_analyzer import PriceAnalyzer

logger = logging.getLogger(__name__)


class IntrinsicChartService:
    """
    Сервис для построения графика исторического собственного движения
    """

    def __init__(self, window_size: int = 24):
        self.window_size = window_size
        self.analyzer = PriceAnalyzer()

    def build_intrinsic_chart_data(self,
                                   eth_klines: List[Dict],
                                   btc_klines: List[Dict]) -> List[Dict]:
        """
        Построение данных для графика собственного движения
        """
        logger.info(f"🔍 НАЧАЛО ПОСТРОЕНИЯ ГРАФИКА. ETH свечей: {len(eth_klines)}, BTC свечей: {len(btc_klines)}")

        if not eth_klines or not btc_klines:
            logger.error("❌ Нет данных для построения графика")
            return []

        if len(eth_klines) != len(btc_klines):
            logger.error(f"❌ Количество свечей не совпадает: ETH={len(eth_klines)}, BTC={len(btc_klines)}")
            # Попробуем обрезать до минимальной длины
            min_length = min(len(eth_klines), len(btc_klines))
            eth_klines = eth_klines[:min_length]
            btc_klines = btc_klines[:min_length]
            logger.info(f"📏 Обрезано до {min_length} точек")

        # Проверяем, что есть достаточно данных для анализа
        if len(eth_klines) < 2:
            logger.error(f"❌ Недостаточно данных. Нужно минимум 2 точки, есть {len(eth_klines)}")
            return []

        # Упрощенный подход: используем одну модель для всех данных
        logger.info("🔄 Используем упрощенный подход с одной моделью")

        try:
            # Получаем цены закрытия
            all_eth_prices = [kline['close'] for kline in eth_klines]
            all_btc_prices = [kline['close'] for kline in btc_klines]

            if all_eth_prices and all_btc_prices:
                # Проверяем, что цены не нулевые и не аномальные
                if min(all_eth_prices) <= 0 or min(all_btc_prices) <= 0:
                    logger.error("❌ Обнаружены нулевые или отрицательные цены")
                    return []

                if max(all_eth_prices) / min(all_eth_prices) > 1000 or max(all_btc_prices) / min(
                        all_btc_prices) > 1000:
                    logger.warning("⚠️ Большой разброс цен - возможны аномалии")

            logger.info(f"📊 Диапазон цен ETH: {min(all_eth_prices):.2f} - {max(all_eth_prices):.2f}")
            logger.info(f"📊 Диапазон цен BTC: {min(all_btc_prices):.2f} - {max(all_btc_prices):.2f}")

            # Очищаем предыдущие данные и обучаем модель
            self.analyzer.historical_data['eth_spot'] = []
            self.analyzer.historical_data['btc_spot'] = []
            self.analyzer.historical_data['eth_futures'] = []
            self.analyzer.historical_data['btc_futures'] = []

            self.analyzer.add_historical_data(all_eth_prices, all_btc_prices, all_eth_prices, all_btc_prices)

            if self.analyzer.spot_coef is None:
                logger.error("❌ Не удалось обучить модель линейной регрессии")
                # Попробуем принудительно построить модель
                self.analyzer._build_regression_models()
                if self.analyzer.spot_coef is None:
                    logger.error("❌ Модель всё равно не построена")
                    return []

            logger.info(
                f"✅ Модель обучена: ETH = {self.analyzer.spot_intercept:.2f} + {self.analyzer.spot_coef:.6f}×BTC")

            # Рассчитываем собственное движение для каждой точки
            intrinsic_data = []
            successful_calculations = 0

            for i in range(len(eth_klines)):
                try:
                    current_prices = {
                        'eth_spot': eth_klines[i]['close'],
                        'btc_spot': btc_klines[i]['close']
                    }

                    analysis = self.analyzer.analyze_movement(current_prices)

                    point_data = {
                        'timestamp': eth_klines[i]['timestamp'],
                        'time': eth_klines[i]['timestamp'] // 1000,
                        'intrinsic_movement': analysis.get('spot_intrinsic', 0),
                        'eth_price': eth_klines[i]['close'],
                        'btc_price': btc_klines[i]['close'],
                        'influence_btc': analysis.get('spot_btc_influence', 0),
                        'eth_own_power': analysis.get('spot_eth_own', 0),
                        'models_ready': True
                    }

                    intrinsic_data.append(point_data)
                    successful_calculations += 1

                except Exception as e:
                    logger.warning(f"Ошибка расчета для точки {i}: {e}")
                    continue

            logger.info(f"✅ Успешно рассчитано {successful_calculations} точек")
            return intrinsic_data

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в build_intrinsic_chart_data: {e}")
            return []

    def get_chart_summary(self, intrinsic_data: List[Dict]) -> Dict:
        """Получение статистики по данным графика"""
        if not intrinsic_data:
            return {}

        movements = [point['intrinsic_movement'] for point in intrinsic_data]

        # Базовая статистика
        summary = {
            'total_points': len(intrinsic_data),
            'avg_movement': sum(movements) / len(movements) if movements else 0,
            'max_movement': max(movements) if movements else 0,
            'min_movement': min(movements) if movements else 0,
            'positive_points': len([m for m in movements if m > 0]),
            'negative_points': len([m for m in movements if m < 0]),
            'strong_positive': len([m for m in movements if m > 2.0]),  # > 2%
            'strong_negative': len([m for m in movements if m < -2.0])  # < -2%
        }

        # Процентное соотношение
        if summary['total_points'] > 0:
            summary['positive_percent'] = (summary['positive_points'] / summary['total_points']) * 100
            summary['negative_percent'] = (summary['negative_points'] / summary['total_points']) * 100
        else:
            summary['positive_percent'] = 0
            summary['negative_percent'] = 0

        logger.info(f"📊 Статистика графика: {summary['positive_points']}+ / {summary['negative_points']}- точек")

        return summary


# Глобальный экземпляр сервиса
intrinsic_chart_service = IntrinsicChartService(window_size=24)