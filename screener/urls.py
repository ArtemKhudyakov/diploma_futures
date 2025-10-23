from django.urls import path
from . import views

app_name = 'screener'

urlpatterns = [
    path('', views.RealtimeView.as_view(), name='realtime'),
    path('api/data/', views.DataAPIView.as_view(), name='api_data'),
    path('api/history/', views.HistoryAPIView.as_view(), name='api_history'),
    path('api/chart-data/', views.ChartDataAPIView.as_view(), name='api_chart_data'),
    path('api/intrinsic-movement/', views.IntrinsicMovementAPIView.as_view(), name='api_intrinsic_movement'),

    # Алерты
    path('api/alerts/create/', views.AlertCreateAPIView.as_view(), name='api_alerts_create'),
    path('api/alerts/list/', views.AlertListAPIView.as_view(), name='api_alerts_list'),
    path('api/alerts/delete/<int:alert_id>/', views.AlertDeleteAPIView.as_view(), name='api_alerts_delete'),
    path('api/alerts/check/', views.CheckAlertsView.as_view(), name='api_alerts_check'),
    path('api/alerts/manual-check/', views.ManualCheckAlertsView.as_view(), name='api_alerts_manual_check'),
]