from celery import Celery


def make_celery():
    celery = Celery('my_console_app', broker='redis://localhost:6379/0')
    return celery


celery = make_celery()



@celery.task
def add(x, y):
    return x + y
