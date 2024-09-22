import datetime
import re
from pprint import pprint

import telebot
from sqlalchemy import distinct
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from dotenv import load_dotenv
import os

from connect import session, Session
from models import Location, Offer
from service import find_offers, parse_ical

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
    chat_id = c.message.chat.id

    # Проверяем, есть ли данные для пользователя в словаре
    if chat_id not in user_data:
        user_data[chat_id] = {}

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

    # Проверяем, есть ли данные для пользователя в словаре
    if chat_id not in user_data:
        user_data[chat_id] = {}

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
                # Получаем главное фото (если есть) или первое фото, если главное отсутствует
                main_photo = next((photo.url for photo in offer.photos if photo.is_main),
                                  offer.photos[0].url if offer.photos else None)

                # Словарь всех удобств с условием вывода только если значение True
                amenities_dict = {
                    "Стиральная машина": offer.washing_machine,
                    "Wi-Fi": offer.wi_fi,
                    "Телевизор": offer.tv,
                    "Кондиционер": offer.air_conditioner,
                    "Дружественно для детей": offer.kids_friendly,
                    "Разрешены вечеринки": offer.party,
                    "Холодильник": offer.refrigerator,
                    "Телефон": offer.phone,
                    "Плита": offer.stove,
                    "Посудомоечная машина": offer.dishwasher,
                    "Музыкальный центр": offer.music_center,
                    "Микроволновка": offer.microwave,
                    "Утюг": offer.iron,
                    "Консьерж": offer.concierge,
                    "Парковка": offer.parking,
                    "Сейф": offer.safe,
                    "Водонагреватель": offer.water_heater,
                    "Телевидение": offer.television,
                    "Ванная комната": offer.bathroom,
                    "Можно с животными": offer.pet_friendly,
                    "Можно курить": offer.smoke,
                    "Романтическая атмосфера": offer.romantic,
                    "Джакузи": offer.jacuzzi,
                    "Балкон": offer.balcony,
                    "Лифт": offer.elevator
                }

                # Формируем список удобств, только если они True
                amenities = [name for name, condition in amenities_dict.items() if condition]

                # Преобразуем список удобств в строку
                amenities_str = ", \n".join(amenities)

                # Формируем сообщение с информацией о предложении
                offer_message = f"Предложение: \n" \
                                f"Цена: {offer.price.value} {offer.price.currency}\n\n" \
                                f"Удобства: {amenities_str}\n\n" \
                                f"Депозит: {offer.price.deposit} {offer.price.deposit_currency}\n"

                # Если есть главное фото, добавляем его в сообщение
                if main_photo:
                    bot.send_photo(chat_id, main_photo, caption=offer_message)
                else:
                    bot.send_message(chat_id, offer_message)
        else:
            bot.send_message(chat_id, "Извините, нет доступных предложений на указанные даты.")
    else:
        bot.send_message(chat_id, "Пожалуйста, предоставьте все необходимые данные.")


def check_calendars():
    session = Session()
    offers = session.query(Offer).all()
    print(len(offers))
    for offer in offers:
        print(offer.id)
        if offer.url_to.startswith("http"):
            # Логика для проверки и обновления событий календаря url_to
            parse_ical(offer.url_to, offer,
                       session)  # fixme если мы и так передаем объект Offer то зачем мы отдельно отдаем ссылку на календарь офера?
        else:
            continue
    session.close()


if __name__ == '__main__':
    check_calendars()
    bot.infinity_polling()
