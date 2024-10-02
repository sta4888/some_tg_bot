import os

from celery import Celery
from dotenv import load_dotenv
from loguru import logger

from connect import Session
from models import Offer
from service import parse_ical

load_dotenv()

broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')


def make_celery():
    celery = Celery('guests_bot', broker=broker_url, backend=result_backend)
    return celery


celery = make_celery()


@celery.task
@logger.catch
def addi(x, y):
    return x + y


# Пример задачи: отправка ежедневного сообщения

@celery.task
@logger.catch
def send_daily_report():
    logger.info("Отправляем ежедневное сообщение...")


@celery.task(name="check_calendars")
@logger.catch
def check_calendars():
    session = Session()
    offers = session.query(Offer).all()
    for offer in offers:
        if offer.url_to.startswith("http"):
            # Логика для проверки и обновления событий календаря url_to
            parse_ical(offer)
        else:
            continue
    session.close()


celery.conf.timezone = 'Asia/Tashkent'

# Пример расписания задач (если нужно)
celery.conf.beat_schedule = {
    'send_daily_report': {
        'task': 'tasks.check_calendars',
        'schedule': 360.0,  # Задача будет выполняться каждые 60 секунд
    },
}
