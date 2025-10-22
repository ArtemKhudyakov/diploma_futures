from django.urls import path
from . import views

app_name = 'screener'

urlpatterns = [
    path('', views.RealtimeView.as_view(), name='realtime'),
    path('api/data/', views.DataAPIView.as_view(), name='api_data'),
    path('api/history/', views.HistoryAPIView.as_view(), name='api_history'),
    path('api/chart-data/', views.ChartDataAPIView.as_view(), name='api_chart_data'),
    path('api/intrinsic-movement/', views.IntrinsicMovementAPIView.as_view(), name='api_intrinsic_movement'),
    path('api/alerts/', views.AlertAPIView.as_view(), name='api_alerts'),
    path('api/alerts/<int:alert_id>/', views.AlertAPIView.as_view(), name='api_alert_detail'),
    path('api/check-alerts/', views.CheckAlertsView.as_view(), name='api_check_alerts'),
]
