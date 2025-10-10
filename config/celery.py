import os

from celery import Celery

# Устанавливаем настройки Django для Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Используем конфиг из settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автопоиск задач во всех приложениях
app.autodiscover_tasks()


# Простая задача для тестирования
@app.task(bind=True)
def debug_task(self):
    return f"Request: {self.request.id}"
