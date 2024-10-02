from celery import Celery
import os
import os
from loguru import logger

broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

logger.info(f'Broker URL: {broker_url}')
logger.info(f'Result Backend: {result_backend}')

# Настройки Celery
app = Celery('telegram_bot', broker=broker_url, backend=result_backend)

app.conf.timezone = 'Asia/Tashkent'

# Пример расписания задач (если нужно)
app.conf.beat_schedule = {
    'send_daily_report': {
        'task': 'tasks.send_daily_report',
        'schedule': 60.0,  # Задача будет выполняться каждые 60 секунд
    },
}
