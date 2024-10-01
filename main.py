import asyncio
import datetime
import re

import httpx
import telebot
from sqlalchemy import distinct
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from dotenv import load_dotenv
import os

from connect import session, Session
from models import Location, Offer, User, Subscription
from resender import resend_message
from service import find_offers, parse_ical, random_with_N_digits

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
    # Найдем пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь новый, создаем его
    if user is None:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
            is_client=True,  # По умолчанию не хост
        )

        session.add(user)
        session.commit()

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


from telebot import types

# Удобства с эмодзи
AMENITIES_EMOJI = {
    "Стиральная машина": "🧺",
    "Wi-Fi": "📶",
    "Телевизор": "📺",
    "Кондиционер": "❄️",
    "Дружественно для детей": "👶",
    "Разрешены вечеринки": "🎉",
    "Холодильник": "🧊",
    "Телефон": "📞",
    "Плита": "🍳",
    "Посудомоечная машина": "🍽️",
    "Музыкальный центр": "🎵",
    "Микроволновка": "🍲",
    "Утюг": "🧼",
    "Консьерж": "👨‍✈️",
    "Парковка": "🚗",
    "Сейф": "🔒",
    "Водонагреватель": "💧",
    "Телевидение": "📡",
    "Ванная комната": "🛁",
    "Можно с животными": "🐕",
    "Можно курить": "🚬",
    "Романтическая атмосфера": "💖",
    "Джакузи": "🛀",
    "Балкон": "🏞️",
    "Лифт": "🛗"
}


@bot.callback_query_handler(func=lambda call: re.match(r'^\d+(\+\d+)*$', call.data))
def handle_bedrooms_selection(call):
    chat_id = call.message.chat.id

    if chat_id not in user_data:
        user_data[chat_id] = {}

    bedrooms = call.data
    user_data[chat_id]['bedrooms'] = bedrooms

    bot.edit_message_text(f"Вы выбрали {bedrooms} раздельных спальных мест.",
                          chat_id,
                          call.message.message_id)

    bot.send_message(chat_id, "Спасибо! Вот ваши данные:")
    bot.send_message(chat_id, f"Город: {user_data[chat_id].get('city', 'Не указано')}\n"
                              f"Даты: {user_data[chat_id].get('start_date', 'Не указано')} - {user_data[chat_id].get('end_date', 'Не указано')}\n"
                              f"Количество гостей: {user_data[chat_id].get('guest', 'Не указано')}\n"
                              f"Спальных мест: {user_data[chat_id].get('bedrooms', 'Не указано')}")

    city = user_data[chat_id].get('city')
    start_date = user_data[chat_id].get('start_date')
    end_date = user_data[chat_id].get('end_date')
    guest_count = user_data[chat_id].get('guest')

    if city and start_date and end_date and guest_count:
        amenities = ['wi_fi', 'air_conditioner']

        offers = find_offers(city, start_date, end_date, guest_count, bedrooms, amenities)

        if offers:
            # Сохраняем предложения в user_data
            user_data[chat_id]['offers'] = offers
            user_data[chat_id]['current_offer_index'] = 0
            send_offer_message(chat_id)
        else:
            bot.send_message(chat_id, "Извините, нет доступных предложений на указанные даты.")
    else:
        bot.send_message(chat_id, "Пожалуйста, предоставьте все необходимые данные.")


# Отправляем текущее предложение
async def check_url(client, url):
    try:
        response = await client.get(url)
        return response.status_code >= 200 and response.status_code < 300
    except Exception as e:
        print(f"Ошибка при проверке URL {url}: {e}")
        return False


async def check_media_links(urls):
    valid_urls = []
    async with httpx.AsyncClient() as client:
        tasks = [check_url(client, url) for url in urls]
        results = await asyncio.gather(*tasks)
        print(f"--results {results}")
        valid_urls = [url for url, is_valid in zip(urls, results) if is_valid]
    return valid_urls


################################################################################################
# Отправляем текущее предложение и сохраняем message_id
def send_offer_message(chat_id):
    current_offer_index = user_data[chat_id]['current_offer_index']
    offers = user_data[chat_id]['offers']
    offer = offers[current_offer_index]

    main_photo = next((photo.url for photo in offer.photos if photo.is_main),
                      offer.photos[0].url if offer.photos else None)

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

    amenities = [f"{AMENITIES_EMOJI.get(name)} {name}" for name, condition in amenities_dict.items() if condition]
    amenities_str = ", \n".join(amenities)

    total_offers = len(offers)
    current_offer_number = current_offer_index + 1  # Номер предложения (1-индексация)

    offer_message = f"Предложение: \n" \
                    f"{offer.location.region}, {offer.location.locality_name}\n" \
                    f"Адрес: {offer.location.address}\n" \
                    f"Цена: {offer.price.value} {offer.price.currency}\n\n" \
                    f"Удобства: {amenities_str}\n\n" \
                    f"Депозит: {offer.price.deposit} {offer.price.deposit_currency}\n\n" \
                    f"Найдено {total_offers} | {current_offer_number}"

    markup = types.InlineKeyboardMarkup()
    next_button = types.InlineKeyboardButton("Далее", callback_data="next_offer")
    back_button = types.InlineKeyboardButton("Назад", callback_data="previous_offer")
    details_button = types.InlineKeyboardButton("Подробнее", callback_data="offer_details")

    # Добавляем кнопку для связи с хостом с ссылкой
    contact_host_button = types.InlineKeyboardButton("Связь с хостом", callback_data="contact_host")

    markup.add(back_button, next_button, details_button)
    markup.add(contact_host_button)

    if main_photo:
        try:
            print(f"Отправка фото: {main_photo}")  # Добавьте это для отладки
            message = bot.send_photo(chat_id, main_photo, caption=offer_message, reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as tg_exception:
            print(f"--tg_exception {tg_exception}")
            message = bot.send_message(chat_id, offer_message, reply_markup=markup)
    else:
        message = bot.send_message(chat_id, offer_message, reply_markup=markup)

    # Сохраняем message_id в user_data
    user_data[chat_id]['message_id'] = message.message_id


@bot.callback_query_handler(func=lambda call: call.data == 'contact_host')
def contact_host(call):
    chat_id = call.message.chat.id
    current_offer_index = user_data[chat_id]['current_offer_index']
    offer = user_data[chat_id]['offers'][current_offer_index]

    # Получаем пользователя, который создал оффер
    host = session.query(User).get(offer.created_by)

    # Получаем текущего пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=call.from_user.id).first()

    print(f"--user {user}")
    print(f"--host {host}")

    markup = types.InlineKeyboardMarkup()

    # Если у хоста есть username в Telegram, то используем его
    if host.username:
        host_chat_link = f"tg://resolve?domain={host.username}"
    else:
        # Иначе используем chat_id для перехода в личный чат
        host_chat_link = f"tg://user?id={host.telegram_id}"

    # Добавляем кнопку для связи с хостом с ссылкой
    contact_host_button = types.InlineKeyboardButton("Чат с хостом 💬", url=host_chat_link)
    markup.add(contact_host_button)

    # Генерация уникального request_id
    request_id = None
    while True:
        request_id = random_with_N_digits(8)
        subscription = session.query(Subscription).filter_by(unique_digits_id=str(request_id)).first()
        if not subscription:  # Убедитесь, что подписка с этим ID не существует
            break

    new_subscription = Subscription(
        user_id=user.id,  # Передаем user.id, а не объект user
        start_date=user_data[chat_id].get('start_date', 'Не указано'),
        end_date=user_data[chat_id].get('end_date', 'Не указано'),
        offer_id=offer.id,
        unique_digits_id=request_id
    )

    # Отправляем сообщение пользователю с ссылкой на чат с хостом
    bot.send_message(chat_id, f"Ваша заявка: `{request_id}`", reply_markup=markup, parse_mode='MarkdownV2')

    # Отправляем хосту сообщение с оффером
    offer_message = f"Пользователь интересуется вашим предложением: \n" \
                    f"У вас новый запрос от пользователя {'@' + call.from_user.username if call.from_user.username else call.from_user.first_name}\n" \
                    f"Даты: {user_data[chat_id].get('start_date', 'Не указано')} - {user_data[chat_id].get('end_date', 'Не указано')}\n" \
                    f"Количество гостей: {user_data[chat_id].get('guest', 'Не указано')}\n" \
                    f"ID Заявки: `{request_id}`\n" \
                    f"{offer.location.region}, {offer.location.locality_name}\n" \
                    f"Адрес: {offer.location.address}\n" \
                    f"Цена: {offer.price.value} {offer.price.currency}\n\n"

    resend_message(bot, call.message, host.chat_id, offer_message)

    # Добавьте новую подписку в сессию
    session.add(new_subscription)

    # Зафиксируйте изменения
    session.commit()

    # Очищаем данные пользователя
    user_data.pop(chat_id, None)


# Обработчик кнопки "Назад"
@bot.callback_query_handler(func=lambda call: call.data == "previous_offer")
def handle_previous_offer(call):
    chat_id = call.message.chat.id
    current_offer_index = user_data[chat_id]['current_offer_index']

    if current_offer_index - 1 >= 0:
        user_data[chat_id]['current_offer_index'] -= 1
        send_offer_message(chat_id)
        bot.delete_message(chat_id, call.message.message_id)  # Удаляем старое сообщение
    else:
        bot.send_message(chat_id, "Это было первое предложение.")


# Обработчик кнопки "Далее"
@bot.callback_query_handler(func=lambda call: call.data == "next_offer")
def handle_next_offer(call):
    chat_id = call.message.chat.id
    current_offer_index = user_data[chat_id]['current_offer_index']

    if current_offer_index + 1 < len(user_data[chat_id]['offers']):
        user_data[chat_id]['current_offer_index'] += 1
        send_offer_message(chat_id)
        bot.delete_message(chat_id, call.message.message_id)  # Удаляем старое сообщение
    else:
        bot.send_message(chat_id, "Это было последнее предложение.")


# Обработчик кнопки "Подробнее"
@bot.callback_query_handler(func=lambda call: call.data == "offer_details")
def handle_offer_details(call):
    chat_id = call.message.chat.id
    current_offer_index = user_data[chat_id]['current_offer_index']
    offer = user_data[chat_id]['offers'][current_offer_index]

    # Удаляем предыдущее сообщение с предложением
    bot.delete_message(chat_id, call.message.message_id)

    # 1. Отправляем медиагруппу с фотографиями
    media_group = []
    urls_to_check = [photo.url for photo in offer.photos if str(photo.url).startswith('http')]
    valid_urls = asyncio.run(check_media_links(urls_to_check))

    for url in valid_urls[:10]:
        media_group.append(InputMediaPhoto(media=url))

    if media_group:
        media_messages = bot.send_media_group(chat_id, media_group)
        # Сохраняем ID сообщений с медиафайлами
        user_data[chat_id]['last_media_messages'] = [msg.message_id for msg in media_messages]

    # 2. Отправляем сообщение с удобствами
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

    amenities = [f"{AMENITIES_EMOJI.get(name)} {name}" for name, condition in amenities_dict.items() if condition]
    amenities_str = ", ".join(amenities)

    # 3. Отправляем сообщение с описанием
    description_message = f"Описание: {offer.description}"
    description_msg = bot.send_message(chat_id, description_message)

    # 4. Отправляем сообщение с локацией
    location_message = f"Локация: {offer.location.region}, {offer.location.locality_name}\nАдрес: {offer.location.address}"

    amenities_message = f"Удобства: {amenities_str}\n {location_message}"
    amenities_msg = bot.send_message(chat_id, amenities_message)
    location_msg = bot.send_location(chat_id, offer.location.latitude, offer.location.longitude)

    # Сохраняем ID сообщений для последующего удаления
    user_data[chat_id]['last_details_messages'] = [
        amenities_msg.message_id,
        description_msg.message_id,
        location_msg.message_id
    ]

    # Добавляем кнопку для возврата к просмотру
    markup = types.InlineKeyboardMarkup()
    return_button = types.InlineKeyboardButton("Вернуться к просмотру", callback_data="back_to_offers")
    markup.add(return_button)

    # Отправляем сообщение с кнопками
    buttons_message = bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
    user_data[chat_id]['last_buttons_message'] = buttons_message.message_id


# Обработчик кнопки "Вернуться к просмотру"
@bot.callback_query_handler(func=lambda call: call.data == "back_to_offers")
def handle_back_to_offers(call):
    chat_id = call.message.chat.id

    # Удаляем сообщение с кнопками
    bot.delete_message(chat_id, user_data[chat_id]['last_buttons_message'])

    # Удаляем все сообщения с медиафайлами
    for msg_id in user_data[chat_id]['last_media_messages']:
        bot.delete_message(chat_id, msg_id)

    # Удаляем сообщения с удобствами, описанием и локацией
    for msg_id in user_data[chat_id]['last_details_messages']:
        bot.delete_message(chat_id, msg_id)

    # Возвращаемся к просмотру текущего предложения
    send_offer_message(chat_id)


################################################################################################
# Обработчик кнопки "Вернуться к просмотру"
@bot.callback_query_handler(func=lambda call: call.data == "back_to_offers")
def handle_back_to_offers(call):
    chat_id = call.message.chat.id
    # Возвращаемся к просмотру текущего оффера
    send_offer_message(chat_id)
    bot.delete_message(chat_id, call.message.message_id)  # Удаляем сообщение с подробностями


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


# qr_generate("example.com", "guest.pdf")


if __name__ == '__main__':
    check_calendars()
    bot.infinity_polling()
