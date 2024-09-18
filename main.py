import datetime

import telebot

from connect import session
from models import Base, User
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Простой обработчик команды /start
user_data = {}


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Давайте начнем. Какой город вы выбираете?")
    user_data[message.chat.id] = {}
    bot.register_next_step_handler(message, ask_city)


def ask_city(message):
    user_data[message.chat.id]['city'] = message.text
    calendar, step = DetailedTelegramCalendar().build()
    bot.send_message(message.chat.id,
                     f"Select {LSTEP[step]}",
                     reply_markup=calendar)
    bot.send_message(message.chat.id, "Отлично! Пожалуйста, введите дату начала (формат: YYYY-MM-DD):")
    bot.register_next_step_handler(message, ask_start_date)


def ask_start_date(message):
    try:
        start_date = datetime.strptime(message.text, '%Y-%m-%d')
        user_data[message.chat.id]['start_date'] = start_date.strftime('%Y-%m-%d')

        # Предложим дату окончания
        end_date = start_date + datetime.timedelta(days=1)
        user_data[message.chat.id]['end_date'] = end_date.strftime('%Y-%m-%d')

        bot.send_message(message.chat.id, f"Вы выбрали дату заезда: {user_data[message.chat.id]['start_date']}.")
        bot.send_message(message.chat.id,
                         f"Предлагаем дату выезда: {user_data[message.chat.id]['end_date']}. Если хотите изменить, введите новую дату выезда (формат: YYYY-MM-DD), иначе просто напишите 'ОК'.")
        bot.register_next_step_handler(message, ask_end_date)
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат даты. Пожалуйста, введите дату в формате YYYY-MM-DD.")
        bot.register_next_step_handler(message, ask_start_date)


def ask_end_date(message):
    if message.text.lower() == 'ок':
        pass
    else:
        try:
            end_date = datetime.strptime(message.text, '%Y-%m-%d')
            user_data[message.chat.id]['end_date'] = end_date.strftime('%Y-%m-%d')
        except ValueError:
            bot.send_message(message.chat.id, "Неверный формат даты. Пожалуйста, введите дату в формате YYYY-MM-DD.")
            bot.register_next_step_handler(message, ask_end_date)
            return

    bot.send_message(message.chat.id,
                     f"Даты заезда: {user_data[message.chat.id]['start_date']}, выезда: {user_data[message.chat.id]['end_date']}.")
    bot.send_message(message.chat.id, "Сколько спальных мест вам нужно?")
    bot.register_next_step_handler(message, ask_bedrooms)


def ask_bedrooms(message):
    user_data[message.chat.id]['bedrooms'] = message.text
    bot.send_message(message.chat.id, "Спасибо! Вот ваши данные:")
    bot.send_message(message.chat.id, f"Город: {user_data[message.chat.id]['city']}\n"
                                      f"Даты: {user_data[message.chat.id]['start_date']} - {user_data[message.chat.id]['end_date']}\n"
                                      f"Спальных мест: {user_data[message.chat.id]['bedrooms']}")


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c):
    result, key, step = DetailedTelegramCalendar().process(c.data)
    if not result and key:
        bot.edit_message_text(f"Select {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"You selected {result}",
                              c.message.chat.id,
                              c.message.message_id)


if __name__ == "__main__":
    bot.polling()
