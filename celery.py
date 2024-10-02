from celery import Celery
import os

# Настройки Celery
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

app = Celery('telegram_bot', broker_pool_limit=1, broker=broker_url,
             result_backend=result_backend)

# Пример расписания задач (если нужно)
app.conf.beat_schedule = {
    'send_daily_report': {
        'task': 'tasks.send_daily_report',
        'schedule': 60.0,  # Задача будет выполняться каждые 60 секунд
    },
}

# Укажите правильный часовой пояс
app.conf.timezone = 'Asia/Tashkent'
