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
    calendar, step = DetailedTelegramCalendar().build()
    bot.send_message(message.chat.id, f"Выберите дату заезда:", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c):
    result, key, step = DetailedTelegramCalendar().process(c.data)
    if not result and key:
        bot.edit_message_text(f"Select {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        user_data[c.message.chat.id]['start_date'] = result.strftime('%Y-%m-%d')
        end_date = result + datetime.timedelta(days=1)
        user_data[c.message.chat.id]['end_date'] = end_date.strftime('%Y-%m-%d')

        bot.edit_message_text(f"Вы выбрали дату заезда: {user_data[c.message.chat.id]['start_date']}.\n"
                              f"Предлагаем дату выезда: {user_data[c.message.chat.id]['end_date']}.",
                              c.message.chat.id,
                              c.message.message_id)

        bot.send_message(c.message.chat.id, "Сколько спальных мест вам нужно?")
        bot.register_next_step_handler(c.message, ask_bedrooms)


def ask_bedrooms(message):
    user_data[message.chat.id]['bedrooms'] = message.text
    bot.send_message(message.chat.id, "Спасибо! Вот ваши данные:")
    bot.send_message(message.chat.id, f"Город: {user_data[message.chat.id]['city']}\n"
                                      f"Даты: {user_data[message.chat.id]['start_date']} - {user_data[message.chat.id]['end_date']}\n"
                                      f"Спальных мест: {user_data[message.chat.id]['bedrooms']}")


if __name__ == "__main__":
    bot.polling()
