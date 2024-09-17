import datetime

import telebot

from connect import session
from models import Base, User
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from telegram_bot_calendar import DetailedTelegramCalendar

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Поиск пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь не найден, создаем нового без агентства
    if user is None:
        bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
        )
        session.add(user)
        session.commit()
        bot.reply_to(message, "Новый пользователь добавлен.")
    else:
        bot.reply_to(message, "Здравствуйте. Введите город")


# выбор города
# первое - выбор даты(в какие даты вам нужно заехать)
# количество спальных мест, комнат


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat, "Привет! Добро пожаловать в нашего бота.")


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def handle_calendar(call):
    result, key, step = DetailedTelegramCalendar().process(call.data)

    if not result and key:
        bot.edit_message_text(f"Выберите {step}",
                              call.message.chat.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Вы выбрали {result}",
                              call.message.chat.id,
                              call.message.message_id)


if __name__ == "__main__":
    bot.polling()
