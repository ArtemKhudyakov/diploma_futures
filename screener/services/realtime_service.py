import logging
import time
from typing import Dict, List
from screener.services.bybit_api import BybitAPI
from screener.services.websocket_client import BybitWebSocket

logger = logging.getLogger(__name__)


class RealtimeService:
    """
    Упрощенный сервис реального времени с фолбэком на API
    """

    def __init__(self, testnet: bool = False):
        self.testnet = testnet
        self.api = BybitAPI(testnet=testnet)
        self.ws = BybitWebSocket(testnet=testnet)

        # Хранилище данных
        self.kline_data = {
            'ETHUSDT': [],
            'BTCUSDT': []
        }

        # Флаги состояния
        self.is_websocket_connected = False

    def start_realtime_updates(self):
        """Запуск обновлений в реальном времени"""
        try:
            logger.info("Попытка запуска WebSocket...")

            # Подписываемся на данные
            self.ws.subscribe_kline("ETHUSDT", "1", self._handle_eth_kline)
            self.ws.subscribe_kline("BTCUSDT", "1", self._handle_btc_kline)

            self.is_websocket_connected = True
            logger.info("WebSocket обновления запущены")

        except Exception as e:
            logger.error(f"Ошибка запуска WebSocket: {e}")
            self.is_websocket_connected = False
            # Продолжаем работу с API

    def stop_realtime_updates(self):
        """Остановка обновлений"""
        try:
            self.ws.disconnect()
            self.is_websocket_connected = False
            logger.info("WebSocket обновления остановлены")
        except Exception as e:
            logger.error(f"Ошибка остановки WebSocket: {e}")

    def _handle_eth_kline(self, message):
        """Обработчик свечей ETH"""
        try:
            logger.info(f"Получены данные ETH: {message}")
            # Здесь будет обработка данных
        except Exception as e:
            logger.error(f"Ошибка обработки ETH данных: {e}")

    def _handle_btc_kline(self, message):
        """Обработчик свечей BTC"""
        try:
            logger.info(f"Получены данные BTC: {message}")
            # Здесь будет обработка данных
        except Exception as e:
            logger.error(f"Ошибка обработки BTC данных: {e}")

    def get_kline_data(self, symbol: str, timeframe: str = '1h') -> List[Dict]:
        """
        Получение данных свечей (основной метод через API)
        """
        try:
            # Всегда используем API как основной источник
            klines = self.api.get_historical_data(symbol, "spot", timeframe, 1)
            candles = []
            for kline in klines:
                candles.append({
                    'timestamp': kline['timestamp'],
                    'open': kline['open'],
                    'high': kline['high'],
                    'low': kline['low'],
                    'close': kline['close'],
                    'volume': kline.get('volume', 0),
                    'is_complete': True
                })

            return candles

        except Exception as e:
            logger.error(f"Ошибка загрузки данных для {symbol}: {e}")
            return []