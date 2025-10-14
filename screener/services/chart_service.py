import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class ChartService:
    """
    Сервис для создания свечных графиков с разными таймфреймами
    """

    def __init__(self):
        self.timeframes = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h',
            '1d': '1d', '1w': '1w', '1M': '1M'
        }

        self.colors = {
            'green': '#00C853',
            'red': '#FF5252',
            'blue': '#2196F3',
            'orange': '#FF9800'
        }

    def create_candlestick_chart(self, klines: List[Dict], symbol: str,
                                 timeframe: str = '1h', height: int = 600) -> go.Figure:
        """
        Создание свечного графика из данных свечей
        """
        if not klines:
            return self._create_empty_chart(f"Нет данных для {symbol}")

        # Преобразуем данные
        df = self._klines_to_dataframe(klines)

        # Создаем свечной график
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df['datetime'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color=self.colors['green'],
            decreasing_line_color=self.colors['red']
        ))

        # Добавляем объемы (если есть)
        if 'volume' in df.columns and df['volume'].sum() > 0:
            fig.add_trace(go.Bar(
                x=df['datetime'],
                y=df['volume'],
                name='Volume',
                marker_color='rgba(100, 100, 100, 0.3)',
                yaxis='y2'
            ))

            # Настраиваем второй Y-axis для объемов
            fig.update_layout(
                yaxis2=dict(
                    title="Volume",
                    overlaying='y',
                    side='right',
                    showgrid=False
                )
            )

        # Настройки графика
        title = f"{symbol} - Свечной график ({timeframe})"
        fig.update_layout(
            title=title,
            xaxis_title="Время",
            yaxis_title="Цена (USDT)",
            height=height,
            template="plotly_white",
            xaxis_rangeslider_visible=False
        )

        return fig

    def create_multiple_charts(self, klines_data: Dict[str, List[Dict]],
                               timeframe: str = '1h') -> go.Figure:
        """
        Создание нескольких графиков на одном полотне
        """
        symbols = list(klines_data.keys())

        if not symbols:
            return self._create_empty_chart("Нет данных для графиков")

        if len(symbols) == 1:
            return self.create_candlestick_chart(
                klines_data[symbols[0]], symbols[0], timeframe, height=600
            )

        # Создаем subplots для нескольких символов
        fig = make_subplots(
            rows=len(symbols), cols=1,
            subplot_titles=[f"{sym} ({timeframe})" for sym in symbols],
            vertical_spacing=0.05
        )

        for i, symbol in enumerate(symbols):
            klines = klines_data[symbol]
            if not klines:
                # Добавляем пустой subplot с сообщением
                fig.add_annotation(
                    text=f"Нет данных для {symbol}",
                    xref=f"x{i + 1}", yref=f"y{i + 1}",
                    x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(size=14),
                    row=i + 1, col=1
                )
                continue

            df = self._klines_to_dataframe(klines)

            fig.add_trace(go.Candlestick(
                x=df['datetime'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=symbol,
                increasing_line_color=self.colors['green'],
                decreasing_line_color=self.colors['red']
            ), row=i + 1, col=1)

        # Настройки
        fig.update_layout(
            title=f"Сравнение активов",
            height=300 * len(symbols),
            template="plotly_white",
            showlegend=False,
            xaxis_rangeslider_visible=False
        )

        return fig

    def _klines_to_dataframe(self, klines: List[Dict]) -> pd.DataFrame:
        """Конвертация свечных данных в DataFrame"""
        if not klines:
            return pd.DataFrame()

        data = []
        for kline in klines:
            data.append({
                'timestamp': kline['timestamp'],
                'datetime': datetime.fromtimestamp(kline['timestamp'] / 1000),
                'open': kline['open'],
                'high': kline['high'],
                'low': kline['low'],
                'close': kline['close'],
                'volume': kline.get('volume', 0)
            })

        df = pd.DataFrame(data)
        df = df.sort_values('datetime')
        return df

    def _create_empty_chart(self, message: str) -> go.Figure:
        """Создание пустого графика с сообщением"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title=message,
            height=400,
            template="plotly_white"
        )
        return fig

    def show_chart(self, fig: go.Figure):
        """Показать график в браузере"""
        try:
            fig.show()
        except Exception as e:
            logger.error(f"Ошибка отображения графика: {e}")

    def save_chart(self, fig: go.Figure, filename: str):
        """Сохранить график в HTML файл"""
        try:
            import os
            os.makedirs("charts", exist_ok=True)
            fig.write_html(f"charts/{filename}.html")
            logger.info(f"График сохранен: charts/{filename}.html")
        except Exception as e:
            logger.error(f"Ошибка сохранения графика: {e}")