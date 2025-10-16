from django.urls import path
from . import views

app_name = 'screener'

urlpatterns = [
    path('', views.RealtimeView.as_view(), name='realtime'),
    path('api/data/', views.DataAPIView.as_view(), name='api_data'),
    path('api/history/', views.HistoryAPIView.as_view(), name='api_history'),
    path('api/chart-data/', views.ChartDataAPIView.as_view(), name='api_chart_data'),
]