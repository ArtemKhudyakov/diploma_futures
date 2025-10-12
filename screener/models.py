from django.db import models


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
        ('price_change', 'Изменение цены'),
        ('intrinsic_move', 'Собственное движение'),
        ('basis_change', 'Изменение базиса'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    symbol = models.CharField(max_length=20)
    message = models.TextField()
    value = models.FloatField()  # Значение которое вызвало алерт
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']