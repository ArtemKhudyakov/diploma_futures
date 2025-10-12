import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from screener.models import PriceHistory

logger = logging.getLogger(__name__)


class ChartService:
    """
    Сервис для создания свечных графиков и визуализации анализа
    """

    def __init__(self):
        self.colors = {
            'green': '#00C853',
            'red': '#FF5252',
            'blue': '#2196F3',
            'orange': '#FF9800',
            'purple': '#9C27B0'
        }

    def create_candlestick_chart(self, symbol: str, category: str,
                                 days: int = 1, height: int = 600) -> go.Figure:
        """
        Создание свечного графика для указанного символа
        """
        # Получаем данные из БД
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        candles = PriceHistory.objects.filter(
            symbol=symbol,
            category=category,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')

        if not candles:
            logger.warning(f"Нет данных для {symbol} {category} за последние {days} дней")
            return self._create_empty_chart("Нет данных")

        # Подготавливаем данные для графика
        dates = [candle.timestamp for candle in candles]
        opens = [candle.open_price for candle in candles]
        highs = [candle.high_price for candle in candles]
        lows = [candle.low_price for candle in candles]
        closes = [candle.close_price for candle in candles]

        # Создаем свечной график
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name=symbol,
            increasing_line_color=self.colors['green'],
            decreasing_line_color=self.colors['red']
        ))

        # Настройка оформления
        title = f"{symbol} {category.upper()} - Свечной график ({days} день)"
        fig.update_layout(
            title=title,
            xaxis_title="Время",
            yaxis_title="Цена (USDT)",
            height=height,
            template="plotly_white",
            xaxis_rangeslider_visible=False
        )

        return fig

    def create_analysis_dashboard(self, intrinsic_data: Dict,
                                  prices: Dict, days: int = 1) -> go.Figure:
        """
        Создание дашборда с несколькими графиками анализа
        """
        # Создаем subplots: свечи ETH, свечи BTC, собственное движение
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                f"ETHUSDT Spot - Собственное движение: {intrinsic_data.get('spot_intrinsic', 0):.3f}%",
                "BTCUSDT Spot",
                "Собственное движение ETH"
            ),
            vertical_spacing=0.08,
            row_heights=[0.5, 0.3, 0.2]
        )

        # 1. График ETH
        eth_candles = self._get_candle_data('ETHUSDT', 'spot', days)
        if eth_candles:
            fig.add_trace(go.Candlestick(
                x=eth_candles['dates'],
                open=eth_candles['opens'],
                high=eth_candles['highs'],
                low=eth_candles['lows'],
                close=eth_candles['closes'],
                name="ETHUSDT",
                increasing_line_color=self.colors['green'],
                decreasing_line_color=self.colors['red']
            ), row=1, col=1)

        # 2. График BTC
        btc_candles = self._get_candle_data('BTCUSDT', 'spot', days)
        if btc_candles:
            fig.add_trace(go.Candlestick(
                x=btc_candles['dates'],
                open=btc_candles['opens'],
                high=btc_candles['highs'],
                low=btc_candles['lows'],
                close=btc_candles['closes'],
                name="BTCUSDT",
                increasing_line_color=self.colors['blue'],
                decreasing_line_color=self.colors['orange']
            ), row=2, col=1)

        # 3. График собственного движения (если есть исторические данные)
        intrinsic_history = self._get_intrinsic_history(days)
        if intrinsic_history:
            fig.add_trace(go.Scatter(
                x=intrinsic_history['dates'],
                y=intrinsic_history['values'],
                mode='lines',
                name='Собственное движение',
                line=dict(color=self.colors['purple'], width=2)
            ), row=3, col=1)

            # Добавляем горизонтальную линию на уровне 0
            fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)

        # Настройка оформления
        fig.update_layout(
            title="Анализ собственного движения ETH",
            height=900,
            template="plotly_white",
            showlegend=True,
            xaxis_rangeslider_visible=False,
            xaxis2_rangeslider_visible=False
        )

        # Настройка осей
        fig.update_yaxes(title_text="ETH Цена", row=1, col=1)
        fig.update_yaxes(title_text="BTC Цена", row=2, col=1)
        fig.update_yaxes(title_text="Собств. движение %", row=3, col=1)

        return fig

    def create_comparison_chart(self, symbol: str, days: int = 1) -> go.Figure:
        """
        График сравнения спотовой и фьючерсной цены
        """
        # Получаем данные
        spot_data = self._get_price_history('ETHUSDT', 'spot', days)
        futures_data = self._get_price_history('ETHUSDT', 'linear', days)

        if not spot_data or not futures_data:
            return self._create_empty_chart("Нет данных для сравнения")

        fig = go.Figure()

        # Спот цена
        fig.add_trace(go.Scatter(
            x=spot_data['dates'],
            y=spot_data['prices'],
            mode='lines',
            name='ETH Spot',
            line=dict(color=self.colors['blue'], width=2)
        ))

        # Фьючерс цена
        fig.add_trace(go.Scatter(
            x=futures_data['dates'],
            y=futures_data['prices'],
            mode='lines',
            name='ETH Futures',
            line=dict(color=self.colors['orange'], width=2)
        ))

        # Расчет и отображение базиса
        basis_data = self._calculate_basis(spot_data, futures_data)
        if basis_data:
            fig.add_trace(go.Scatter(
                x=basis_data['dates'],
                y=basis_data['basis'],
                mode='lines',
                name='Базис (%)',
                line=dict(color=self.colors['purple'], width=1, dash='dash'),
                yaxis='y2'
            ))

        # Настройка графика
        title = f"Сравнение Spot vs Futures - {symbol}"
        fig.update_layout(
            title=title,
            xaxis_title="Время",
            yaxis_title="Цена (USDT)",
            yaxis2=dict(
                title="Базис %",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            height=500,
            template="plotly_white"
        )

        return fig

    def _get_candle_data(self, symbol: str, category: str, days: int) -> Optional[Dict]:
        """Получение свечных данных для графика"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        candles = PriceHistory.objects.filter(
            symbol=symbol,
            category=category,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')

        if not candles:
            return None

        return {
            'dates': [candle.timestamp for candle in candles],
            'opens': [candle.open_price for candle in candles],
            'highs': [candle.high_price for candle in candles],
            'lows': [candle.low_price for candle in candles],
            'closes': [candle.close_price for candle in candles]
        }

    def _get_price_history(self, symbol: str, category: str, days: int) -> Optional[Dict]:
        """Получение истории цен"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        prices = PriceHistory.objects.filter(
            symbol=symbol,
            category=category,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')

        if not prices:
            return None

        return {
            'dates': [price.timestamp for price in prices],
            'prices': [price.close_price for price in prices]
        }

    def _get_intrinsic_history(self, days: int) -> Optional[Dict]:
        """Получение истории собственного движения (заглушка - нужно реализовать)"""
        # TODO: Реализовать сохранение и загрузку истории собственного движения
        return None

    def _calculate_basis(self, spot_data: Dict, futures_data: Dict) -> Optional[Dict]:
        """Расчет базиса между spot и futures"""
        if not spot_data or not futures_data:
            return None

        # Находим общие временные точки
        common_dates = []
        basis_values = []

        for i, spot_date in enumerate(spot_data['dates']):
            for j, futures_date in enumerate(futures_data['dates']):
                if spot_date == futures_date:
                    spot_price = spot_data['prices'][i]
                    futures_price = futures_data['prices'][j]
                    basis = ((futures_price - spot_price) / spot_price) * 100

                    common_dates.append(spot_date)
                    basis_values.append(basis)
                    break

        return {'dates': common_dates, 'basis': basis_values}

    def _create_empty_chart(self, message: str) -> go.Figure:
        """Создание пустого графика с сообщением"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            title=message,
            height=400,
            template="plotly_white"
        )
        return fig

    def save_chart(self, fig: go.Figure, filename: str):
        """
        Сохранение графика в файл
        """
        try:
            fig.write_html(f"charts/{filename}.html")
            logger.info(f"График сохранен: charts/{filename}.html")
        except Exception as e:
            logger.error(f"Ошибка сохранения графика: {e}")

    def show_chart(self, fig: go.Figure):
        """
        Показ графика в браузере
        """
        try:
            fig.show()
        except Exception as e:
            logger.error(f"Ошибка отображения графика: {e}")