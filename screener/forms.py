from django import forms
from .models import PriceAlert


class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ['name', 'alert_type', 'symbol', 'condition', 'value', 'timeframe', 'data_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Рост ETH выше 4000'
            }),
            'alert_type': forms.Select(attrs={'class': 'form-control'}),
            'symbol': forms.Select(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'placeholder': '0.00'
            }),
            'timeframe': forms.Select(attrs={'class': 'form-control'}),
            'data_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Динамически обновляем опции символов в зависимости от data_type
        if 'data_type' in self.data:
            data_type = self.data['data_type']
            self.fields['symbol'].choices = self.get_symbol_choices(data_type)

    def get_symbol_choices(self, data_type):
        if data_type == 'spot':
            return [
                ('ETHUSDT', 'ETH/USDT'),
                ('BTCUSDT', 'BTC/USDT')
            ]
        elif data_type == 'linear':
            return [
                ('ETHUSDT', 'ETH/USDT Futures'),
                ('BTCUSDT', 'BTC/USDT Futures')
            ]
        elif data_type == 'inverse':
            return [
                ('ETHUSD', 'ETH/USD Futures'),
                ('BTCUSD', 'BTC/USD Futures')
            ]
        return []