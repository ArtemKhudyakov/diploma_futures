import logging
from typing import Callable, Optional
import websocket
import json
import threading

logger = logging.getLogger(__name__)


class BybitWebSocket:
    """
    Упрощенный WebSocket клиент для Bybit
    """

    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.ws_url = "wss://stream.bybit.com/v5/public/spot" if not testnet else "wss://stream-testnet.bybit.com/v5/public/spot"
        self.ws = None
        self.is_connected = False
        self.callbacks = {}

    def connect(self):
        """Подключение к WebSocket"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # Запускаем в отдельном потоке
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()

            self.is_connected = True
            logger.info("WebSocket подключен")

        except Exception as e:
            logger.error(f"Ошибка подключения WebSocket: {e}")
            self.is_connected = False

    def _on_open(self, ws):
        """Обработчик открытия соединения"""
        logger.info("WebSocket соединение установлено")

    def _on_message(self, ws, message):
        """Обработчик входящих сообщений"""
        try:
            data = json.loads(message)
            logger.debug(f"Получено сообщение: {data}")

            # Обрабатываем разные типы сообщений
            if 'topic' in data:
                topic = data['topic']
                if topic in self.callbacks:
                    self.callbacks[topic](data)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

    def _on_error(self, ws, error):
        """Обработчик ошибок"""
        logger.error(f"WebSocket ошибка: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Обработчик закрытия соединения"""
        logger.info("WebSocket соединение закрыто")
        self.is_connected = False

    def subscribe_kline(self, symbol: str, interval: str, callback: Callable):
        """
        Подписка на свечные данные
        """
        try:
            if not self.is_connected or not self.ws:
                self.connect()
                import time
                time.sleep(1)  # Даем время на подключение

            topic = f"kline.{interval}.{symbol}"
            self.callbacks[topic] = callback

            subscribe_msg = {
                "op": "subscribe",
                "args": [topic]
            }

            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(json.dumps(subscribe_msg))
                logger.info(f"Подписка на {topic}")
            else:
                logger.error("WebSocket не подключен для подписки")

        except Exception as e:
            logger.error(f"Ошибка подписки на свечи {symbol}: {e}")

    def disconnect(self):
        """Отключение WebSocket"""
        try:
            if self.ws:
                self.ws.close()
            self.is_connected = False
            logger.info("WebSocket отключен")
        except Exception as e:
            logger.error(f"Ошибка отключения WebSocket: {e}")