import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')


def make_celery():
    celery = Celery('guests_bot', broker=broker_url, backend=result_backend)
    return celery


celery = make_celery()


@celery.task
def add(x, y):
    return x + y
