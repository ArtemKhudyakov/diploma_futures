import sys
import os
import time
import logging
from datetime import datetime

# Добавляем путь к проекту для абсолютных импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

# Теперь импортируем абсолютными путями
from screener.services.bybit_api import BybitClient
from screener.services.price_analyzer import PriceAnalyzer

logger = logging.getLogger(__name__)


def test_integration():
    """
    Тест интеграции BybitClient и PriceAnalyzer
    Показывает как передавать данные между ними
    """
    print("🔄 ТЕСТ ИНТЕГРАЦИИ: BybitClient -> PriceAnalyzer")
    print("=" * 60)

    # 1. Создаем клиент для получения данных
    client = BybitClient(testnet=True)

    # 2. Создаем анализатор для обработки данных
    analyzer = PriceAnalyzer(window_size=100)

    print("🚀 Запуск сбора и анализа данных...")
    print("Структура данных: BybitClient → получает цены → PriceAnalyzer → анализирует")
    print("-" * 60)

    # 3. Цикл сбора и анализа данных
    for i in range(61):  # Собираем 10 точек для быстрого теста
        try:
            # 4. ПОЛУЧАЕМ данные от BybitClient
            print(f"\n📥 Шаг {i + 1}: Получение данных от BybitClient...")
            prices = client.get_all_prices()

            # 5. Выводим что получили
            if all(prices.values()):
                print(f"   ✅ Данные получены:")
                print(f"      ETH Spot: ${prices['eth_spot']:.2f}")
                print(f"      BTC Spot: ${prices['btc_spot']:.2f}")
                print(f"      ETH Futures: ${prices['eth_futures']:.2f}")
                print(f"      BTC Futures: ${prices['btc_futures']:.2f}")

                # 6. ПЕРЕДАЕМ данные в анализатор
                print(f"   🔄 Передача данных в PriceAnalyzer...")
                analyzer.update_data(prices)

                # 7. Обновляем модели регрессии (каждые 5 шагов)
                if (i + 1) % 5 == 0:
                    print(f"   📊 Обновление моделей регрессии...")
                    analyzer.update_regression_models()

                # 8. Если модели готовы - рассчитываем собственное движение
                if (analyzer.spot_regression_coef is not None and
                        analyzer.futures_regression_coef is not None):

                    print(f"   🧮 Расчет собственного движения...")
                    intrinsic = analyzer.calculate_intrinsic_movement(prices)

                    # 9. Выводим результаты анализа
                    if 'spot_intrinsic' in intrinsic:
                        move = intrinsic['spot_intrinsic']
                        trend = "🟢 ВЫШЕ" if move > 0 else "🔴 НИЖЕ"
                        print(f"      Спот: ETH на {abs(move):.3f}% {trend} ожиданий")

                    if 'futures_intrinsic' in intrinsic:
                        move = intrinsic['futures_intrinsic']
                        trend = "🟢 ВЫШЕ" if move > 0 else "🔴 НИЖЕ"
                        print(f"      Фьючерсы: ETH на {abs(move):.3f}% {trend} ожиданий")

                # 10. Проверяем алерты
                alerts = analyzer.check_price_changes()
                if alerts:
                    print(f"   🔔 Обнаружены алерты!")
                    for alert_type, alert_data in alerts.items():
                        change = alert_data['change_pct']
                        direction = "📈 РОСТ" if change > 0 else "📉 ПАДЕНИЕ"
                        print(f"      {alert_type}: {direction} на {abs(change):.2f}%")

            else:
                missing = [k for k, v in prices.items() if not v]
                print(f"   ❌ Отсутствуют данные: {missing}")

            # 11. Пауза между запросами
            print(f"   ⏳ Ожидание 10 секунд...")
            time.sleep(10)

        except KeyboardInterrupt:
            print(f"\n⏹️ Тест остановлен пользователем")
            break
        except Exception as e:
            print(f"   ❌ Ошибка на шаге {i + 1}: {e}")
            time.sleep(10)

    # 12. Финальная статистика
    print("\n" + "=" * 60)
    print("📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
    print(f"   Собрано точек ETH Spot: {len(analyzer.eth_spot_prices)}")
    print(f"   Собрано точек BTC Spot: {len(analyzer.btc_spot_prices)}")
    print(f"   Собрано точек ETH Futures: {len(analyzer.eth_futures_prices)}")
    print(f"   Собрано точек BTC Futures: {len(analyzer.btc_futures_prices)}")
    print(f"   Модель спота готова: {analyzer.spot_regression_coef is not None}")
    print(f"   Модель фьючерсов готова: {analyzer.futures_regression_coef is not None}")

    if analyzer.spot_regression_coef is not None:
        print(
            f"   Коэф. спот модели: ETH = {analyzer.spot_regression_intercept:.2f} + {analyzer.spot_regression_coef:.6f}×BTC")


if __name__ == "__main__":
    # Настройка логирования для теста
    logging.basicConfig(level=logging.INFO)
    test_integration()