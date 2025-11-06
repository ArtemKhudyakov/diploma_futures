from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone


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
    timestamp = models.DateTimeField()
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
    spot_intrinsic_move = models.FloatField()
    eth_futures_price = models.FloatField()
    btc_futures_price = models.FloatField()
    futures_intrinsic_move = models.FloatField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Analysis {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class PriceAlert(models.Model):
    CONDITIONS = [
        ('above', 'Выше'),
        ('below', 'Ниже'),
    ]

    STATUS = [
        ('active', 'Активен'),
        ('triggered', 'Сработал'),
        ('cancelled', 'Отменен'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="Название алерта")
    symbol = models.CharField(max_length=20, verbose_name="Символ")
    condition = models.CharField(max_length=20, choices=CONDITIONS, verbose_name="Условие")
    target_price = models.FloatField(verbose_name="Целевая цена")

    status = models.CharField(max_length=20, choices=STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    current_price_when_triggered = models.FloatField(null=True, blank=True, verbose_name="Цена при срабатывании")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.symbol} {self.condition} ${self.target_price})"

    def check_condition(self, current_price):
        """Проверка условия алерта - МГНОВЕННОЕ срабатывание при достижении цены"""
        if not current_price:
            return False

        if self.condition == 'above':
            return current_price >= self.target_price
        else:  # below
            return current_price <= self.target_price

    def trigger(self, current_price):
        """Мгновенное срабатывание алерта"""
        if self.status == 'active':
            self.status = 'triggered'
            self.triggered_at = timezone.now()
            self.current_price_when_triggered = current_price
            self.save()
            return True
        return False

    def get_trigger_message(self):
        """Сообщение для уведомления о срабатывании"""
        condition_text = "превысила" if self.condition == 'above' else "опустилась ниже"
        return f"{self.symbol} {condition_text} ${self.target_price}. Текущая цена: ${self.current_price_when_triggered:.2f}"