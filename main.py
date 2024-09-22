import datetime
import re

import telebot
from sqlalchemy import distinct
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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

        # Получение уникальных значений поля 'sleeps' из таблицы Offer
        unique_sleeps = session.query(distinct(Offer.sleeps)).all()
        unique_sleeps = [sleep[0] for sleep in unique_sleeps if sleep[0]]  # Извлекаем значения и фильтруем None

        # Создание клавиатуры с уникальными значениями 'sleeps'
        markup = InlineKeyboardMarkup(row_width=2)
        for sleep in unique_sleeps:
            markup.add(InlineKeyboardButton(sleep, callback_data=sleep))

        # Отправка сообщения с клавиатурой
        bot.send_message(message.chat.id, "Выберите количество раздельных спальных мест:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число.")
        bot.register_next_step_handler(message, ask_guest)


@bot.callback_query_handler(func=lambda call: re.match(r'^\d+(\+\d+)*$', call.data))
def handle_bedrooms_selection(call):
    chat_id = call.message.chat.id
    bedrooms = call.data

    # Сохраняем выбранное количество спальных мест
    user_data[chat_id]['bedrooms'] = bedrooms

    # Редактируем предыдущее сообщение, чтобы отразить выбор пользователя
    bot.edit_message_text(f"Вы выбрали {bedrooms} раздельных спальных мест.",
                          chat_id,
                          call.message.message_id)

    # Отправляем сообщение с собранными данными
    bot.send_message(chat_id, "Спасибо! Вот ваши данные:")
    bot.send_message(chat_id, f"Город: {user_data[chat_id].get('city', 'Не указано')}\n"
                              f"Даты: {user_data[chat_id].get('start_date', 'Не указано')} - {user_data[chat_id].get('end_date', 'Не указано')}\n"
                              f"Количество гостей: {user_data[chat_id].get('guest', 'Не указано')}\n"
                              f"Спальных мест: {user_data[chat_id].get('bedrooms', 'Не указано')}")

    # Получаем значения для поиска предложений
    city = user_data[chat_id].get('city')
    start_date = user_data[chat_id].get('start_date')
    end_date = user_data[chat_id].get('end_date')
    guest_count = user_data[chat_id].get('guest')

    # Проверка на наличие всех обязательных данных для поиска предложений
    if city and start_date and end_date and guest_count:
        amenities = ['wi_fi', 'air_conditioner']

        # Получение предложений с помощью функции find_offers
        offers = find_offers(city, start_date, end_date, guest_count, bedrooms, amenities)

        # Если предложения найдены, отправляем их пользователю
        if offers:
            for offer in offers:
                # Получаем главное фото (если есть)
                main_photo = next((photo.url for photo in offer.photos if photo.is_main), None)

                # Формируем строку с удобствами
                amenities = []
                if offer.washing_machine:
                    amenities.append("Стиральная машина")
                if offer.wi_fi:
                    amenities.append("Wi-Fi")
                if offer.tv:
                    amenities.append("Телевизор")
                if offer.air_conditioner:
                    amenities.append("Кондиционер")
                if offer.kids_friendly:
                    amenities.append("Дружественно для детей")
                if offer.party:
                    amenities.append("Разрешены вечеринки")
                if offer.refrigerator:
                    amenities.append("Холодильник")
                if offer.phone:
                    amenities.append("Телефон")
                if offer.stove:
                    amenities.append("Плита")
                if offer.dishwasher:
                    amenities.append("Посудомоечная машина")
                if offer.music_center:
                    amenities.append("Музыкальный центр")
                if offer.microwave:
                    amenities.append("Микроволновка")
                if offer.iron:
                    amenities.append("Утюг")
                if offer.concierge:
                    amenities.append("Консьерж")
                if offer.parking:
                    amenities.append("Парковка")
                if offer.safe:
                    amenities.append("Сейф")
                if offer.water_heater:
                    amenities.append("Водонагреватель")
                if offer.television:
                    amenities.append("Телевидение")
                if offer.bathroom:
                    amenities.append("Ванная комната")
                if offer.pet_friendly:
                    amenities.append("Можно с животными")
                if offer.smoke:
                    amenities.append("Можно курить")
                if offer.romantic:
                    amenities.append("Романтическая атмосфера")
                if offer.jacuzzi:
                    amenities.append("Джакузи")
                if offer.balcony:
                    amenities.append("Балкон")
                if offer.elevator:
                    amenities.append("Лифт")

                # Преобразуем список удобств в строку
                amenities_str = ", ".join(amenities) if amenities else "Удобства не указаны"

                # Отправляем главное фото, если оно есть
                if main_photo:
                    bot.send_photo(chat_id, main_photo)

                # Отправляем информацию о предложении
                bot.send_message(chat_id,
                                 f"Предложение: \n"
                                 f"Цена: {offer.price.value} {offer.price.currency}\n"
                                 f"Удобства: {amenities_str}")
        else:
            bot.send_message(chat_id, "К сожалению, нет доступных предложений по вашему запросу.")
    else:
        # Если каких-то данных не хватает, сообщаем пользователю об этом
        bot.send_message(chat_id,
                         "Не хватает данных для поиска предложений. Пожалуйста, проверьте правильность введённой информации.")


if __name__ == "__main__":
    bot.polling()
