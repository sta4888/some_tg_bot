import datetime
import telebot
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from dotenv import load_dotenv
import os

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_data = {}


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Давайте начнем. Какой город вы выбираете?")
    user_data[message.chat.id] = {}
    bot.register_next_step_handler(message, ask_city)


def ask_city(message):
    user_data[message.chat.id]['city'] = message.text
    calendar, step = DetailedTelegramCalendar(min_date=datetime.date.today()).build()
    bot.send_message(message.chat.id, f"Выберите дату заезда:", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c):
    result, key, step = DetailedTelegramCalendar(min_date=datetime.date.today()).process(c.data)
    if not result and key:
        bot.edit_message_text(f"Выберите дату {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        user_data[c.message.chat.id]['start_date'] = result.strftime('%Y-%m-%d')

        bot.edit_message_text(f"Вы выбрали дату заезда: {user_data[c.message.chat.id]['start_date']}.\n"
                              f"Введите дату выезда (формат: YYYY-MM-DD):",
                              c.message.chat.id,
                              c.message.message_id)

        bot.register_next_step_handler(c.message, ask_end_date)


def ask_end_date(message):
    try:
        end_date = datetime.datetime.strptime(message.text, '%Y-%m-%d')
        start_date = datetime.datetime.strptime(user_data[message.chat.id]['start_date'], '%Y-%m-%d')

        if end_date <= start_date:
            raise ValueError

        user_data[message.chat.id]['end_date'] = end_date.strftime('%Y-%m-%d')

        bot.send_message(message.chat.id,
                         f"Вы выбрали даты:\nЗаезд: {user_data[message.chat.id]['start_date']}\nВыезд: {user_data[message.chat.id]['end_date']}.")
        bot.send_message(message.chat.id, "Сколько спальных мест вам нужно?")
        bot.register_next_step_handler(message, ask_bedrooms)

    except ValueError:
        bot.send_message(message.chat.id,
                         "Неверный формат даты или дата выезда должна быть позже даты заезда. Пожалуйста, введите дату в формате YYYY-MM-DD.")
        bot.register_next_step_handler(message, ask_end_date)


def ask_bedrooms(message):
    user_data[message.chat.id]['bedrooms'] = message.text
    bot.send_message(message.chat.id, "Спасибо! Вот ваши данные:")
    bot.send_message(message.chat.id, f"Город: {user_data[message.chat.id]['city']}\n"
                                      f"Даты: {user_data[message.chat.id]['start_date']} - {user_data[message.chat.id]['end_date']}\n"
                                      f"Спальных мест: {user_data[message.chat.id]['bedrooms']}")


if __name__ == "__main__":
    bot.polling()
