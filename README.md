# To Ze Moon 🚀

Профессиональная система мониторинга и анализа криптовалютных рынков с акцентом на фьючерсы и собственное движение активов.

## 🌟 Основные возможности

### 📊 Анализ рынка
- **Реальное время**: Текущие цены спот и фьючерсов ETH/BTC
- **Собственное движение**: Анализ независимого движения ETH от влияния BTC
- **Технический анализ**: Линейная регрессия и модели прогнозирования
- **Исторические данные**: Свечные графики с различными таймфреймами

### ⚠️ Система алертов
- **Ценовые алерты**: Уведомления при достижении целевых цен
- **Мгновенное срабатывание**: Алгоритм проверки в реальном времени
- **Персональные настройки**: Индивидуальные условия для каждого пользователя

### 🔐 Безопасность и управление
- **JWT аутентификация**: Современная система авторизации
- **Ролевая модель**: Пользователи и менеджеры
- **Telegram уведомления**: Интеграция с мессенджером

## 🛠 Технологический стек

### Backend
- **Django 5.2** - основной фреймворк
- **Django REST Framework** - API
- **Celery** - асинхронные задачи
- **Redis** - кэширование и брокер сообщений
- **PostgreSQL** - база данных

### Внешние API
- **Bybit API** - рыночные данные
- **Telegram Bot API** - уведомления

### Дополнительные компоненты
- **Plotly** - построение графиков
- **Pandas & NumPy** - анализ данных
- **JWT** - аутентификация
- **CORS** - кросс-доменные запросы

## 🚀 Быстрый старт

### Предварительные требования
- Docker & Docker Compose
- Python 3.13 (для локальной разработки)
- Аккаунты: Bybit, Telegram Bot

### Запуск через Docker (рекомендуется)

1. **Клонируйте репозиторий**
   ```bash
   git clone <your-repo>
   cd diploma_futures
Настройте переменные окружения

bash
cp .env.docker .env
# Отредактируйте .env файл с вашими ключами
Запустите приложение

bash
docker-compose up -d
Проверьте статус

bash
docker-compose ps
Откройте в браузере

Главная: http://localhost:8000

API Docs: http://localhost:8000/swagger/

Админка: http://localhost:8000/admin/

Локальная разработка
Установите зависимости

bash
poetry install
Настройте базу данных

bash
python manage.py migrate
python manage.py create_superuser
Запустите сервер

bash
python manage.py runserver
📡 API Endpoints
Рыночные данные
GET /screener/api/data/ - текущие цены и анализ

GET /screener/api/history/ - исторические данные

GET /screener/api/chart-data/ - данные для графиков

GET /screener/api/intrinsic-movement/ - анализ собственного движения

Управление алертами
POST /screener/api/alerts/create/ - создание алерта

GET /screener/api/alerts/list/ - список алертов

DELETE /screener/api/alerts/delete/{id}/ - удаление алерта

POST /screener/api/alerts/check/ - проверка срабатывания

Пользователи и аутентификация
POST /users/api/login/ - JWT аутентификация

POST /users/api/register/ - регистрация

GET /users/api/my-profile/ - профиль пользователя

🔧 Конфигурация
Ключевые переменные окружения
env
# Безопасность
DJANGO_SECRET_KEY=your-secret-key
DEBUG=False

# База данных
DB_POSTGRES_NAME=diploma_futures
POSTGRES_USER=postgres
DB_POSTGRES_PASSWORD=secure-password

# Внешние API
BYBIT_API_KEY=your-bybit-key
BYBIT_API_SECRET=your-bybit-secret
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Email (опционально)
EMAIL_HOST=smtp.yandex.ru
EMAIL_HOST_USER=your-email@yandex.ru
EMAIL_HOST_PASSWORD=your-email-password

# Администратор
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
Docker сервисы
web - основное приложение (порт 8000)

db - PostgreSQL база данных (порт 5432)

redis - Redis кэш и брокер (порт 6379)

celery - воркеры для асинхронных задач

celery-beat - планировщик периодических задач

📈 Архитектура анализа
Модель собственного движения
python
# Линейная регрессия: ETH = α + β × BTC
predicted_eth = intercept + coefficient * btc_price
intrinsic_movement = ((actual_eth - predicted_eth) / predicted_eth) * 100
Поддерживаемые символы
ETHUSDT - Ethereum

BTCUSDT - Bitcoin

Категории данных
spot - спотовые цены

linear - линейные фьючерсы

inverse - обратные фьючерсы

🐳 Docker команды
Управление контейнерами
bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f web
Администрирование
bash
# Миграции
docker-compose exec web python manage.py migrate

# Суперпользователь
docker-compose exec web python manage.py create_superuser

# Статические файлы
docker-compose exec web python manage.py collectstatic --noinput
Makefile команды (опционально)
bash
make setup    # Полная установка
make logs     # Просмотр логов
make shell    # Django shell
make clean    # Очистка
🔍 Мониторинг и отладка
Проверка здоровья сервисов
bash
# База данных
docker-compose exec db pg_isready

# Redis
docker-compose exec redis redis-cli ping

# Приложение
curl http://localhost:8000/api/health/
Полезные команды
bash
# Резервное копирование БД
docker-compose exec db pg_dump -U postgres diploma_futures > backup.sql

# Мониторинг Celery
docker-compose logs -f celery

# Дисковое пространство
docker system df
🤝 Разработка
Code style
bash
# Форматирование
black .
isort .
flake8

# Типы
mypy .
Тестирование
bash
# Запуск тестов
python manage.py test

# С покрытием
coverage run manage.py test
coverage report
Миграции
bash
# Создание миграций
python manage.py makemigrations

# Применение
python manage.py migrate
📊 Производительность
Оптимизации
Кэширование: Redis для часто запрашиваемых данных

Асинхронность: Celery для фоновых задач

Пагинация: Эффективная работа с большими наборами данных

Индексы: Оптимизированные запросы к БД

Мониторинг
Логирование: Детальные логи всех операций

Метрики: Время ответа API, ошибки, использование ресурсов

🆘 Поиск и устранение неисправностей
Частые проблемы
Ошибки подключения к Bybit

Проверьте API ключи

Убедитесь в доступности API

Проблемы с базой данных

bash
docker-compose restart db
docker-compose exec web python manage.py migrate
Ошибки Celery

bash
docker-compose restart celery celery-beat
Статические файлы

bash
docker-compose exec web python manage.py collectstatic --noinput
Логи
bash
# Все логи
docker-compose logs

# Конкретный сервис
docker-compose logs -f web
docker-compose logs -f celery
📄 Лицензия
Этот проект разработан в учебных целях.

👥 Авторы
[Ваше имя] - Разработчик

"To Ze Moon" - профессиональный инструмент для трейдеров и аналитиков криптовалютных рынков. 🎯

