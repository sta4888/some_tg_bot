import datetime
import telebot
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from dotenv import load_dotenv
import os

from connect import session
from models import Location, Offer
from service import find_offers

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

user_data = {}

# Словарь для дней недели и месяцев на русском
days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
months_of_year = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, """Добро пожаловать! 👋Это ВГОСТИбот. 

Я найду для Вас квартиру или апартаменты. 🏠

Напишите мне город, ✈️даты заезда и выезда🚘,  количество гостей🛍🛍🛍 и количество раздельных спальных мест. 😴

Посмотрим,🧑‍💻 что у меня для Вас есть?""")
    user_data[message.chat.id] = {}
    bot.register_next_step_handler(message, ask_city)


def ask_city(message):
    user_data[message.chat.id]['city'] = message.text
    ask_start_date(message)


def ask_start_date(message):
    calendar, step = DetailedTelegramCalendar(min_date=datetime.date.today(), locale='ru').build()
    bot.send_message(message.chat.id, f"Выберите дату заезда:", reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def handle_start_date(c):
    result, key, step = DetailedTelegramCalendar(min_date=datetime.date.today(), locale='ru').process(c.data)
    if not result and key:
        bot.edit_message_text(f"Выберите дату {LSTEP[step]}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=key)
    elif result:
        if user_data[c.message.chat.id].get('start_date') is None:
            user_data[c.message.chat.id]['start_date'] = result.strftime('%Y-%m-%d')
            bot.edit_message_text(f"Вы выбрали дату заезда: {user_data[c.message.chat.id]['start_date']}.\n"
                                  f"Теперь выберите дату выезда:",
                                  c.message.chat.id,
                                  c.message.message_id)
            ask_end_date(c)
        else:
            end_date = result.strftime('%Y-%m-%d')
            start_date = user_data[c.message.chat.id].get('start_date')
            if end_date <= start_date:
                bot.send_message(c.message.chat.id,
                                 "Дата выезда не может быть меньше или равна дате заезда. Пожалуйста, выберите другую дату.")
                ask_end_date(c)
            else:
                user_data[c.message.chat.id]['end_date'] = end_date
                bot.edit_message_text(
                    f"Вы выбрали даты:\nЗаезд: {user_data[c.message.chat.id]['start_date']}\nВыезд: {user_data[c.message.chat.id]['end_date']}.",
                    c.message.chat.id,
                    c.message.message_id)
                bot.send_message(c.message.chat.id, "Сколько гостей?")
                bot.register_next_step_handler(c.message, ask_guest)


def ask_end_date(c):
    start_date = datetime.datetime.strptime(user_data[c.message.chat.id]['start_date'], '%Y-%m-%d').date()
    calendar, step = DetailedTelegramCalendar(min_date=start_date + datetime.timedelta(days=1), locale='ru').build()
    bot.send_message(c.message.chat.id, f"Выберите дату выезда:", reply_markup=calendar)


def ask_guest(message):
    if message.text.isdigit():
        user_data[message.chat.id]['guest'] = int(message.text)
        bot.send_message(message.chat.id, "Сколько раздельных спальных мест вам нужно?")
        bot.register_next_step_handler(message, ask_bedrooms)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число.")
        bot.register_next_step_handler(message, ask_guest)


def ask_bedrooms(message):
    user_data[message.chat.id]['bedrooms'] = message.text
    bot.send_message(message.chat.id, "Спасибо! Вот ваши данные:")
    bot.send_message(message.chat.id, f"Город: {user_data[message.chat.id]['city']}\n"
                                      f"Даты: {user_data[message.chat.id]['start_date']} - {user_data[message.chat.id]['end_date']}\n"
                                      f"Сколько гостей: {user_data[message.chat.id]['guest']}\n"
                                      f"Спальных мест: {user_data[message.chat.id]['bedrooms']}")
    chat_id = message.chat.id
    city = user_data[chat_id]['city']
    start_date = user_data[chat_id]['start_date']
    end_date = user_data[chat_id]['end_date']
    guest_count = user_data[chat_id]['guest']
    bedrooms = user_data[chat_id]['bedrooms']

    offers = find_offers(city, start_date, end_date, guest_count, bedrooms)

    if offers:
        # Отправляем список предложений пользователю
        for offer in offers:
            bot.send_message(chat_id,
                             f"Предложение: {offer.description}\nЦена: {offer.price.value} {offer.price.currency}")
    else:
        bot.send_message(chat_id, "К сожалению, нет доступных предложений по вашему запросу.")


if __name__ == "__main__":
    bot.polling()
