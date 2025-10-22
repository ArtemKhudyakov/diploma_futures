from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

class PriceHistory(models.Model):
    CATEGORY_CHOICES = [
        ('spot', 'Spot'),
        ('linear', 'Futures Linear'),
        ('inverse', 'Futures Inverse'),
    ]

    SYMBOL_CHOICES = [
        ('ETHUSDT', 'ETHUSDT'),
        ('BTCUSDT', 'BTCUSDT'),
    ]

    symbol = models.CharField(max_length=20, choices=SYMBOL_CHOICES)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    timestamp = models.DateTimeField()  # Время свечи
    open_price = models.FloatField()
    high_price = models.FloatField()
    low_price = models.FloatField()
    close_price = models.FloatField()
    volume = models.FloatField()

    class Meta:
        db_table = 'price_history'
        indexes = [
            models.Index(fields=['symbol', 'category', 'timestamp']),
        ]
        ordering = ['symbol', 'category', 'timestamp']

    def __str__(self):
        return f"{self.symbol} {self.category} {self.timestamp}"


class AnalysisSession(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    data_points_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class AnalysisResult(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    eth_spot_price = models.FloatField()
    btc_spot_price = models.FloatField()
    spot_intrinsic_move = models.FloatField()  # Собственное движение в %
    eth_futures_price = models.FloatField()
    btc_futures_price = models.FloatField()
    futures_intrinsic_move = models.FloatField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Analysis {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class PriceAlert(models.Model):
    ALERT_TYPES = [
        ('price', 'Цена'),
        ('intrinsic', 'Собственное движение'),
        ('basis', 'Базис'),
        ('volume', 'Объем'),
    ]

    CONDITIONS = [
        ('above', 'Выше'),
        ('below', 'Ниже'),
        ('cross_above', 'Пересекает сверху'),
        ('cross_below', 'Пересекает снизу'),
    ]

    STATUS = [
        ('active', 'Активен'),
        ('triggered', 'Сработал'),
        ('cancelled', 'Отменен'),
    ]

    # Используем settings.AUTH_USER_MODEL вместо прямого импорта User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    name = models.CharField(max_length=100, verbose_name="Название алерта")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name="Тип алерта")
    symbol = models.CharField(max_length=20, verbose_name="Символ")
    condition = models.CharField(max_length=20, choices=CONDITIONS, verbose_name="Условие")
    value = models.FloatField(verbose_name="Значение")

    # Дополнительные параметры для разных типов алертов
    timeframe = models.CharField(max_length=10, default='1h', verbose_name="Таймфрейм")
    data_type = models.CharField(max_length=10, default='spot', verbose_name="Тип данных")

    status = models.CharField(max_length=20, choices=STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Алерт'
        verbose_name_plural = 'Алерты'

    def __str__(self):
        return f"{self.name} ({self.symbol} {self.alert_type})"

    def get_condition_text(self):
        condition_text = {
            'above': '>',
            'below': '<',
            'cross_above': 'пересекает сверху',
            'cross_below': 'пересекает снизу'
        }
        return condition_text.get(self.condition, self.condition)

    def get_alert_type_display_name(self):
        names = {
            'price': 'Цена',
            'intrinsic': 'Собственное движение',
            'basis': 'Базис',
            'volume': 'Объем'
        }
        return names.get(self.alert_type, self.alert_type)