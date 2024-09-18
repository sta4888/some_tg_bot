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
                              f"Теперь выберите дату выезда:",
                              c.message.chat.id,
                              c.message.message_id)

        # Переходим к выбору даты выезда
        calendar, step = DetailedTelegramCalendar(min_date=result + datetime.timedelta(days=1)).build()
        bot.send_message(c.message.chat.id, f"Выберите дату выезда:", reply_markup=calendar)


@bot.callback_query_handler(func=lambda c: True)
def cal_end(c):
    if c.message.chat.id not in user_data or 'start_date' not in user_data[c.message.chat.id]:
        return

    # Обработка выбора даты выезда
    result, key, step = DetailedTelegramCalendar(
        min_date=user_data[c.message.chat.id]['start_date'] + datetime.timedelta(days=1)).process(c.data)
    if not result and key:
        bot.edit_message_text(f"Выберите дату {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        user_data[c.message.chat.id]['end_date'] = result.strftime('%Y-%m-%d')

        bot.edit_message_text(
            f"Вы выбрали даты:\nЗаезд: {user_data[c.message.chat.id]['start_date']}\nВыезд: {user_data[c.message.chat.id]['end_date']}.",
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
