# celery.py

import os
from celery import Celery

# Установим переменные окружения для подключения к Redis
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

app = Celery('telegram_bot')

# Настройки Celery
app.conf.broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Настройки для Celery Beat (расписание задач)
app.conf.beat_schedule = {
    'send_daily_report': {
        'task': 'tasks.send_daily_report',
        'schedule': 60.0,  # Например, задача будет выполняться каждые 60 секунд
    },
}

# Установка таймзоны
app.conf.timezone = 'Asia/Tashkent'
