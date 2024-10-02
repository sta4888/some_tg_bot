# tasks.py

from loguru import logger
import os
import telebot

from celery_app import celery

# Получение токена из переменной окружения
API_TOKEN = os.environ.get('BOT_TOKEN')

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)


# Пример задачи: отправка ежедневного сообщения
@logger.catch
@celery.task
def send_daily_report():
    logger.info("Отправляем ежедневное сообщение...")

    # users = [...]  # Здесь вы получаете список пользователей, которым нужно отправить сообщение
    # for user in users:
    #     try:
    #         bot.send_message(user.chat_id, "Это ваше ежедневное сообщение!")
    #         logger.info(f"Сообщение отправлено пользователю {user.chat_id}")
    #     except Exception as e:
    #         logger.error(f"Ошибка при отправке сообщения пользователю {user.chat_id}: {e}")
