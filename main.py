import telebot

from uuid import UUID
from connect import session
from models import User, Offer, XML_FEED, Photo, SalesAgent
from dotenv import load_dotenv
import os
import requests  # Добавим библиотеку для HTTP-запросов
from service import parse_and_save_offer, qr_generate, get_referral_chain

from math import ceil
from telebot import types

load_dotenv()

API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения состояния пользователей
user_states = {}

# Количество кнопок на одной строке и на одной странице
BUTTONS_PER_ROW = 2
ITEMS_PER_PAGE = 9  # 9 кнопок на странице, 3 строки по 3 кнопки

# Пример булевых полей
BOOLEAN_FIELDS = {
    'washing_machine': 'Стиральная машина', 'wi_fi': 'wi-fi', 'tv': 'Телевизор', 'air_conditioner': 'Кондиционер',
    'kids_friendly': 'Дети', 'party': 'Для вечеринок', 'refrigerator': 'Холодильник',
    'phone': 'Телефон', 'stove': 'Плита', 'dishwasher': 'Посудомоечная машина', 'music_center': 'Музыкальный центр',
    'microwave': 'Микроволновая печь', 'iron': 'Утюг', 'concierge': 'Консьерж', 'parking': 'Парковка',
    'safe': 'Сейф', 'water_heater': 'Нагреватель воды', 'pet_friendly': 'Домашние животные', 'smoke': 'Курение',
    'romantic': 'Романтический', 'jacuzzi': 'Джакузи', 'balcony': 'Балкон', 'elevator': 'Лифт'
}


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    command = message.text.split()
    referrer_uuid = None

    if len(command) > 1:
        try:
            referrer_uuid = UUID(command[1])  # Парсим переданный UUID
        except ValueError:
            bot.send_message(message.chat.id, "Неверная реферальная ссылка.\nЗапросите новую")
            referrer_uuid = None

    # Найдем пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    ref_link_btn = types.KeyboardButton("СГЕНЕРИРОВАТЬ РЕФЕРАЛЬНУЮ ССЫЛКУ")
    markup.add(ref_link_btn)

    # Если пользователь новый, создаем его
    if user is None:
        referer = None

        if referrer_uuid:
            referer = session.query(User).filter_by(uuid=referrer_uuid).first()

        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
            is_client=False,  # По умолчанию не хост
            referer=referer  # Сохраняем реферера, если он есть
        )

        session.add(user)

        if referer:
            referer.invited_count += 1
            session.add(referer)

        session.commit()
        bot.send_message(message.chat.id, "Привет Хост! Добро пожаловать в нашего бота.")

    bot.send_message(message.chat.id, "Пожалуйста, отправьте ссылку на XML-файл.", reply_markup=markup)

    # Инициализируем состояние пользователя для обработки URL
    user_states[message.from_user.id] = {'awaiting_feed_url': True}


#####################################################################################################################
# Обработка ссылки на XML-файл
@bot.message_handler(func=lambda message: 'https://realtycalendar.ru/xml_feed' in message.text)
def handle_url_input(message):
    user_id = message.from_user.id
    user = session.query(User).filter_by(telegram_id=user_id).first()

    # Проверяем, на каком этапе находится пользователь
    if user_id in user_states and 'awaiting_object_urls' in user_states[user_id]:
        bot.reply_to(message, "Сначала завершите добавление ссылок на объекты.")
        return

    if not user:
        bot.reply_to(message, "Пользователь не найден.")
        return

    url = message.text.strip()

    try:
        response = requests.get(url)
        response.raise_for_status()
        xml_data = response.content.decode('utf-8')

        internal_ids = parse_and_save_offer(xml_data, bot, message)
        print(internal_ids)

        if internal_ids:
            new_feed = XML_FEED(url=url, user_id=user.id)
            session.add(new_feed)
            session.commit()

            bot.send_message(message.chat.id, f'спасибо! 👌\nДобавлено объектов: {len(internal_ids)}')
            user_states[user_id] = {'internal_ids': internal_ids, 'current_index': 0, 'awaiting_object_urls': True}

            first_internal_id = internal_ids[0].get('internal_id')
            first_location_address = internal_ids[0].get('location_address')
            bot.reply_to(message,
                         f"Пожалуйста, введите URL для объекта с internal_id: {first_internal_id}\nадресом: {first_location_address}")
        else:
            bot.reply_to(message, "В загруженном файле нет ни одного нового объекта.")

    except Exception as e:
        session.rollback()
        bot.reply_to(message, f"Ошибка при загрузке файла: {str(e)}.")


# Обработка ссылок на объекты (apart)
@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and 'awaiting_object_urls' in user_states[
        message.from_user.id])
def handle_object_url(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]

    # Проверяем, не пытается ли пользователь снова отправить ссылку на XML-файл
    if 'https://realtycalendar.ru/xml_feed' in message.text:
        bot.reply_to(message, "Пожалуйста, завершите добавление ссылок на объекты.")
        return

    # Проверяем формат ссылки на объект
    if not message.text.startswith("https://realtycalendar.ru/apart"):
        bot.reply_to(message, "Неверная ссылка. Пожалуйста, введите корректный URL на объект.")
        return

    # Получаем текущий объект и его внутренний ID
    internal_ids = user_state['internal_ids']
    current_index = user_state['current_index']
    current_internal_id_data = internal_ids[current_index]
    internal_id = current_internal_id_data.get('internal_id')

    # Сохраняем URL для текущего объекта
    new_url = message.text.strip()
    offer = session.query(Offer).filter_by(internal_id=internal_id).first()

    if offer:
        offer.url_to = new_url
        session.commit()

        current_index += 1
        user_state['current_index'] = current_index

        if current_index < len(internal_ids):
            next_internal_id_data = internal_ids[current_index]
            next_internal_id = next_internal_id_data.get('internal_id')
            next_location_address = next_internal_id_data.get('location_address')

            bot.reply_to(message,
                         f"Введите URL для объекта с internal_id: {next_internal_id}, адрес: {next_location_address}")
        else:
            del user_states[user_id]
            bot.reply_to(message, "Все ссылки успешно добавлены!")
    else:
        bot.reply_to(message, f"Предложение с internal_id {internal_id} не найдено.")


######################################################################################################################

@bot.message_handler(commands=['edit_offer'])
def edit_offer(message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if not user:
        bot.send_message(message.chat.id, "Вы не зарегистрированы.")
        return

    # Получаем все офферы, созданные пользователем
    offers = session.query(Offer).filter_by(created_by=user.id).all()
    if not offers:
        bot.send_message(message.chat.id, "У вас нет офферов для редактирования.")
        return

    # Инициализируем состояние пользователя для пагинации
    if message.from_user.id not in user_states:
        user_states[message.from_user.id] = {}

    # Устанавливаем текущую страницу в 1, если не указано иное
    user_states[message.from_user.id]['page'] = 1

    # Отправляем список офферов с пагинацией
    markup = paginate_buttons(offers, page=1)
    bot.send_message(message.chat.id, "Выберите оффер для редактирования:", reply_markup=markup)


def paginate_buttons(offers, page=1):
    markup = types.InlineKeyboardMarkup()

    # Определяем стартовый и конечный индексы для текущей страницы
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE

    # Создаем кнопки для офферов на текущей странице
    for offer in offers[start_index:end_index]:
        button = types.InlineKeyboardButton(
            text=f"Объект {offer.internal_id} {offer.location.address}",
            callback_data=f"edit_offer_{offer.internal_id}"
        )
        markup.add(button)

    # Добавляем кнопки "Назад" и "Вперед" для переключения страниц
    total_pages = ceil(len(offers) / ITEMS_PER_PAGE)

    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"prev_page_{page - 1}"
            )
        )
    if page < total_pages:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"next_page_{page + 1}"
            )
        )

    if pagination_buttons:
        markup.add(*pagination_buttons)

    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith(('prev_page_', 'next_page_')))
def handle_pagination(call):
    page = int(call.data.split('_')[-1])  # Определяем номер страницы из callback_data
    user = session.query(User).filter_by(telegram_id=call.from_user.id).first()
    offers = session.query(Offer).filter_by(created_by=user.id).all()

    # Обновляем страницу пользователя в user_states
    user_states[call.from_user.id]['page'] = page

    # Обновляем кнопки с офферами для новой страницы
    markup = paginate_buttons(offers, page=page)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)


# Создайте функцию для создания булевых кнопок
def create_boolean_buttons(offer, page=0):
    markup = types.InlineKeyboardMarkup()

    # Определяем индекс начала и конца кнопок на текущей странице
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    fields_on_page = list(BOOLEAN_FIELDS.items())[start_index:end_index]

    # Создаем кнопки в три колонки
    row = []
    for i, (field, display_name) in enumerate(fields_on_page):
        field_value = getattr(offer, field)
        field_display = f"{display_name} {'✅' if field_value else '❌'}"
        button = types.InlineKeyboardButton(text=field_display, callback_data=f"toggle_{field}_{page}")
        row.append(button)

        if (i + 1) % BUTTONS_PER_ROW == 0 or i == len(fields_on_page) - 1:
            markup.add(*row)
            row = []

    # Добавляем кнопки для пагинации
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
    if end_index < len(BOOLEAN_FIELDS):
        navigation_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page + 1}"))

    if navigation_buttons:
        markup.add(*navigation_buttons)

    return markup


# Функция для обновления кнопок оффера
def update_offer_buttons(call, offer, page=0):
    offer_details = f"Текущий оффер:\nID: {offer.internal_id}\nURL: {offer.url_to}\nАдрес: {offer.location.address}\nОписание: {offer.description[:200]}..."

    markup = create_boolean_buttons(offer, page)
    markup.add(
        types.InlineKeyboardButton(text="URL", callback_data=f"edit_url_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Описание", callback_data=f"edit_description_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Спальных мест", callback_data=f"edit_sleeps_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить цену", callback_data=f"edit_price_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить агента", callback_data=f"edit_sales_agent_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить площадь", callback_data=f"edit_area_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить фото", callback_data=f"edit_photos_{offer.internal_id}"),
        types.InlineKeyboardButton(text="К списку офферов", callback_data="back_to_offers"),
        types.InlineKeyboardButton(text="Отмена", callback_data="cancel_edit"),
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=offer_details + "\n\nЧто вы хотите изменить?",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_offers")
def handle_back_to_offers(call):
    user = session.query(User).filter_by(telegram_id=call.from_user.id).first()
    offers = session.query(Offer).filter_by(created_by=user.id).all()

    # Установим текущую страницу обратно на 1
    user_states[call.from_user.id]['page'] = 1

    # Отправим список офферов с пагинацией
    markup = paginate_buttons(offers, page=1)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Выберите оффер для редактирования:", reply_markup=markup)


# Обработка выбора оффера для редактирования
@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_offer_"))
def handle_offer_selection(call):
    internal_id = call.data.split("_")[2]
    offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()

    if offer and offer.creator.telegram_id == call.from_user.id:
        # Показываем кнопки редактирования
        update_offer_buttons(call, offer)
        user_states[call.from_user.id] = {'offer_to_edit': offer, 'current_page': 0}  # Инициализация текущей страницы
    else:
        bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден или не принадлежит вам.")


# Обработка переключения булевого поля
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def handle_toggle_field(call):
    field, page = call.data.replace('toggle_', '').rsplit('_', 1)
    page = int(page)  # Преобразуем страницу в целое число
    user_id = call.from_user.id
    offer_id = user_states[user_id]['offer_to_edit'].internal_id

    # Загружаем оффер из базы данных
    offer = session.query(Offer).filter_by(internal_id=offer_id).first()

    # Переключаем значение поля
    current_value = getattr(offer, field)
    setattr(offer, field, not current_value)

    # Сохраняем изменения в базе данных
    session.commit()

    # Обновляем кнопки с учетом изменения, оставаясь на той же странице
    update_offer_buttons(call, offer, page)


# Обработка пагинации
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_pagination(call):
    page = int(call.data.split('_')[1])
    user_id = call.from_user.id
    offer_id = user_states[user_id]['offer_to_edit'].internal_id

    # Загружаем оффер из базы данных
    offer = session.query(Offer).filter_by(internal_id=offer_id).first()

    # Показываем кнопки на выбранной странице
    update_offer_buttons(call, offer, page)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_url_"))
def handle_edit_url(call):
    internal_id = call.data.split("_")[2]
    offer = user_states[call.from_user.id]['offer_to_edit']

    if offer and offer.internal_id == internal_id:
        # Запрос нового URL
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Введите новый URL:"
        )
        user_states[call.from_user.id]['editing_field'] = 'url'
    else:
        bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")


@bot.message_handler(
    func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get('editing_field') == 'url')
def process_new_url(message):
    user_id = message.from_user.id
    new_url = message.text
    offer = user_states[user_id]['offer_to_edit']

    # Обновите URL в базе данных
    offer.url_to = new_url
    session.commit()  # Не забудьте сохранить изменения в сессии

    # Отправьте обновленное сообщение об оффере
    offer_details = f"Текущий оффер:\nID: {offer.internal_id}\nURL: {offer.url_to}\nАдрес: {offer.location.address}\nОписание: {offer.description[:200]}..."

    markup = create_boolean_buttons(offer)
    markup.add(
        types.InlineKeyboardButton(text="URL", callback_data=f"edit_url_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Описание", callback_data=f"edit_description_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Спальных мест", callback_data=f"edit_sleeps_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить цену", callback_data=f"edit_price_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить агента", callback_data=f"edit_sales_agent_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить площадь", callback_data=f"edit_area_{offer.internal_id}"),
        types.InlineKeyboardButton(text="Изменить фото", callback_data=f"edit_photos_{offer.internal_id}"),
        types.InlineKeyboardButton(text="К списку офферов", callback_data="back_to_offers"),
        types.InlineKeyboardButton(text="Отмена", callback_data="cancel_edit"),
    )

    bot.send_message(chat_id=message.chat.id, text=offer_details + "\n\nЧто вы хотите изменить?", reply_markup=markup)

    # Очистить состояние редактирования
    user_states[user_id]['editing_field'] = None


####### ---------- JGJHGJHGHJ  -------- #########
@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_description_"))
def handle_edit_description(call):
    internal_id = call.data.split("_")[2]
    offer = user_states[call.from_user.id]['offer_to_edit']

    if offer and offer.internal_id == internal_id:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Введите новое описание:"
        )
        user_states[call.from_user.id]['editing_field'] = 'description'
    else:
        bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sleeps_"))
def handle_edit_sleeps(call):
    internal_id = call.data.split("_")[2]
    offer = user_states[call.from_user.id]['offer_to_edit']

    if offer and offer.internal_id == internal_id:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Введите новое количество спальных мест:"
        )
        user_states[call.from_user.id]['editing_field'] = 'sleeps'
    else:
        bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_price_"))
def handle_edit_price(call):
    internal_id = call.data.split("_")[2]
    offer = user_states[call.from_user.id]['offer_to_edit']

    if offer and offer.internal_id == internal_id:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Введите новую цену:"
        )
        user_states[call.from_user.id]['editing_field'] = 'price'
    else:
        bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sales_agent_"))
def handle_edit_sales_agent(call):
    internal_id = call.data.split("_")[2]
    offer = user_states[call.from_user.id]['offer_to_edit']

    if offer and offer.internal_id == internal_id:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Введите нового агента:"
        )
        user_states[call.from_user.id]['editing_field'] = 'sales_agent'
    else:
        bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_area_"))
def handle_edit_area(call):
    internal_id = call.data.split("_")[2]
    offer = user_states[call.from_user.id]['offer_to_edit']

    if offer and offer.internal_id == internal_id:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Введите новую площадь:"
        )
        user_states[call.from_user.id]['editing_field'] = 'area'
    else:
        bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")


##########
@bot.message_handler(
    func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get('editing_field') in ['url',
                                                                                                                  'description',
                                                                                                                  'sleeps',
                                                                                                                  'price',
                                                                                                                  'sales_agent',
                                                                                                                  'area'])
def process_offer_updates(message):
    user_id = message.from_user.id
    offer = user_states[user_id]['offer_to_edit']
    field = user_states[user_id]['editing_field']

    # Обработчик для каждого поля
    try:
        if field == 'url':
            new_value = message.text
            offer.url_to = new_value
        elif field == 'description':
            new_value = message.text
            offer.description = new_value
        elif field == 'sleeps':
            new_value = message.text
            offer.sleeps = new_value  # предполагаем, что это число
        elif field == 'price':
            new_value = message.text
            offer.price = new_value  # предполагаем, что это число
        elif field == 'sales_agent':
            new_value = message.text
            # Предполагается, что sales_agent - это объект SalesAgent, вам нужно его найти по имени или номеру телефона
            offer.sales_agent = session.query(SalesAgent).filter(SalesAgent.name == new_value).first()
        elif field == 'area':
            new_value = message.text
            offer.area = float(new_value)  # предполагаем, что это число

        # Сохраните изменения в базе данных
        session.commit()

        # Отправьте обновленное сообщение об оффере
        offer_details = f"Текущий оффер:\nID: {offer.internal_id}\nURL: {offer.url_to}\nОписание: {offer.description[:200]}...\nСпальных мест: {offer.sleeps}\nЦена: {offer.price}\nАгент: {offer.sales_agent.name if offer.sales_agent else 'Не указан'}\nПлощадь: {offer.area}"

        markup = create_boolean_buttons(offer)
        markup.add(
            types.InlineKeyboardButton(text="URL", callback_data=f"edit_url_{offer.internal_id}"),
            types.InlineKeyboardButton(text="Описание", callback_data=f"edit_description_{offer.internal_id}"),
            types.InlineKeyboardButton(text="Спальных мест", callback_data=f"edit_sleeps_{offer.internal_id}"),
            types.InlineKeyboardButton(text="Изменить цену", callback_data=f"edit_price_{offer.internal_id}"),
            types.InlineKeyboardButton(text="Изменить агента", callback_data=f"edit_sales_agent_{offer.internal_id}"),
            types.InlineKeyboardButton(text="Изменить площадь", callback_data=f"edit_area_{offer.internal_id}"),
            types.InlineKeyboardButton(text="К списку офферов", callback_data="back_to_offers"),
            types.InlineKeyboardButton(text="Отмена", callback_data="cancel_edit"),
        )

        bot.send_message(chat_id=message.chat.id, text=offer_details + "\n\nЧто вы хотите изменить?",
                         reply_markup=markup)

    except ValueError as e:
        bot.send_message(chat_id=message.chat.id,
                         text=f"Ошибка при обновлении: {str(e)}. Пожалуйста, проверьте введенные данные.")
    except Exception as e:
        bot.send_message(chat_id=message.chat.id, text=f"Произошла ошибка: {str(e)}")

    # Очистить состояние редактирования
    user_states[user_id]['editing_field'] = None


# Обработка отмены
@bot.callback_query_handler(func=lambda call: call.data == "cancel_edit")
def handle_cancel_edit(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Редактирование оффера отменено."
    )
    user_states.pop(call.from_user.id, None)  # Удаляем состояние пользователя


####################################################################################


####################################################################################

# @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_price_"))
# def handle_edit_price(call):
#     internal_id = call.data.split("_")[2]
#     offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
#
#     if offer:
#         bot.send_message(call.message.chat.id,
#                          "Введите новую цену и валюту в формате 'значение валюта' (например, '1000 USD').")
#         user_states[call.from_user.id] = {'offer_to_edit': offer, 'edit_type': 'price'}
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден.")
#
#
# def get_agents():
#     return session.query(SalesAgent).all()
#
#
# # Обработка редактирования агента
# @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sales_agent_"))
# def handle_edit_sales_agent(call):
#     internal_id = call.data.split("_")[2]
#     offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
#
#     if offer:
#         # Предположим, что у вас есть функция для получения списка агентов
#         agents = get_agents()  # Замените на вашу функцию
#         markup = types.InlineKeyboardMarkup()
#         for agent in agents:
#             markup.add(
#                 types.InlineKeyboardButton(text=agent.name, callback_data=f"set_agent_{agent.id}_{offer.internal_id}"))
#         bot.send_message(call.message.chat.id, "Выберите агента:", reply_markup=markup)
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден.")
#
#
# # Обработка редактирования площади
# @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_area_"))
# def handle_edit_area(call):
#     internal_id = call.data.split("_")[2]
#     offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
#
#     if offer:
#         bot.send_message(call.message.chat.id,
#                          "Введите новую площадь в формате 'значение единица' (например, '50 m2').")
#         user_states[call.from_user.id] = {'offer_to_edit': offer, 'edit_type': 'area'}
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден.")
#
#
# # Обработка редактирования фотографий
# @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_photos_"))
# def handle_edit_photos(call):
#     internal_id = call.data.split("_")[2]
#     offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
#
#     if offer:
#         # Предположим, что у вас есть функция для получения списка фотографий
#         markup = types.InlineKeyboardMarkup()
#         for photo in offer.photos:
#             markup.add(types.InlineKeyboardButton(text="Удалить " + photo.url,
#                                                   callback_data=f"delete_photo_{photo.id}_{offer.internal_id}"))
#         markup.add(types.InlineKeyboardButton(text="Добавить фото", callback_data=f"add_photo_{offer.internal_id}"))
#         bot.send_message(call.message.chat.id, "Выберите фото для удаления или добавьте новое:", reply_markup=markup)
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден.")
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_description_"))
# def handle_edit_description(call):
#     internal_id = call.data.split("_")[2]
#     offer = user_states[call.from_user.id]['offer_to_edit']
#
#     if offer and offer.internal_id == internal_id:
#         # Запрос нового описания
#         bot.edit_message_text(
#             chat_id=call.message.chat.id,
#             message_id=call.message.message_id,
#             text="Введите новое описание:"
#         )
#         user_states[call.from_user.id]['editing_field'] = 'description'
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sleeps_"))
# def handle_edit_description(call):
#     internal_id = call.data.split("_")[2]
#     offer = user_states[call.from_user.id]['offer_to_edit']
#
#     if offer and offer.internal_id == internal_id:
#         # Запрос нового описания
#         bot.edit_message_text(
#             chat_id=call.message.chat.id,
#             message_id=call.message.message_id,
#             text="Введите новое количество:"
#         )
#         user_states[call.from_user.id]['editing_field'] = 'sleeps'
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка при редактировании оффера.")
#
#
#
# @bot.message_handler(func=lambda message: message.from_user.id in user_states)
# def handle_text(message):
#     user_id = message.from_user.id
#     offer = user_states[user_id].get('offer_to_edit')
#     edit_type = user_states[user_id].get('edit_type')
#
#     if edit_type == 'price':
#         try:
#             value, currency = message.text.split()
#             value = float(value)
#             offer.price.value = value
#             offer.price.currency = currency
#             session.commit()
#             bot.send_message(user_id, "Цена успешно обновлена.")
#         except Exception as e:
#             bot.send_message(user_id,
#                              "Ошибка при обновлении цены. Убедитесь, что вы ввели данные в правильном формате.")
#         finally:
#             del user_states[user_id]  # Удаляем состояние пользователя после завершения
#
#     elif edit_type == 'area':
#         try:
#             value, unit = message.text.split()
#             value = float(value)
#             offer.area.value = value
#             offer.area.unit = unit
#             session.commit()
#             bot.send_message(user_id, "Площадь успешно обновлена.")
#         except Exception as e:
#             bot.send_message(user_id,
#                              "Ошибка при обновлении площади. Убедитесь, что вы ввели данные в правильном формате.")
#         finally:
#             del user_states[user_id]  # Удаляем состояние пользователя после завершения
#
#
# # Обработка выбора агента
# @bot.callback_query_handler(func=lambda call: call.data.startswith("set_agent_"))
# def handle_set_agent(call):
#     agent_id, internal_id = call.data.split("_")[2:4]
#     offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
#
#     if offer:
#         offer.sales_agent_id = agent_id
#         session.commit()
#         bot.send_message(call.message.chat.id, "Агент успешно обновлён.")
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден.")
#
#
# # Обработка добавления и удаления фотографий
# @bot.callback_query_handler(func=lambda call: call.data.startswith("add_photo_"))
# def handle_add_photo(call):
#     internal_id = call.data.split("_")[2]
#     # Здесь можно реализовать логику для загрузки нового фото (например, через URL или файл)
#     # Необходимо добавить код для обработки загрузки фото
#
#
# @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_photo_"))
# def handle_delete_photo(call):
#     photo_id, internal_id = call.data.split("_")[2:4]
#     offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
#     photo = session.query(Photo).filter_by(id=photo_id).first()
#
#     if offer and photo:
#         session.delete(photo)
#         session.commit()
#         bot.send_message(call.message.chat.id, "Фото успешно удалено.")
#     else:
#         bot.send_message(call.message.chat.id, "Ошибка: Фото не найдено.")
#
#
# @bot.message_handler(
#     func=lambda message: message.from_user.id in user_states and 'editing_field' in user_states[message.from_user.id])
# def handle_new_value(message):
#     user_id = message.from_user.id
#     offer = user_states[user_id]['offer_to_edit']
#     field_to_edit = user_states[user_id]['editing_field']
#     new_value = message.text.strip()
#
#     # Обновляем значение в зависимости от выбранного поля
#     if field_to_edit == 'url':
#         offer.url_to = new_value
#         bot.send_message(message.chat.id, f"URL для оффера {offer.internal_id} обновлен на: {new_value}")
#     elif field_to_edit == 'description':
#         offer.description = new_value
#         bot.send_message(message.chat.id, f"Описание для оффера {offer.internal_id} обновлено на: {new_value}")
#
#     session.commit()  # Сохраняем изменения в базе данных
#     del user_states[user_id]  # Удаляем состояние пользователя после завершения редактирования
#
#
# # Обработка выбора действия редактирования
# @bot.message_handler(
#     func=lambda message: message.from_user.id in user_states and 'offer_to_edit' in user_states[message.from_user.id])
# def handle_edit_choice(message):
#     user_id = message.from_user.id
#     offer = user_states[user_id]['offer_to_edit']
#
#     if message.text == "Изменить URL":
#         bot.send_message(message.chat.id, "Введите новый URL для этого оффера:")
#         user_states[user_id]['editing_url'] = True
#     elif message.text == "Изменить описание":
#         bot.send_message(message.chat.id, "Введите новое описание для этого оффера:")
#         user_states[user_id]['editing_description'] = True
#         # fixme дописать про редактирование спальных мест
#     elif message.text == "Отмена":
#         del user_states[user_id]  # Удаляем состояние редактирования
#         bot.send_message(message.chat.id, "Редактирование отменено.")
#     else:
#         bot.send_message(message.chat.id, "Неизвестная команда.")
#
#
# # Обработка нового значения URL
# @bot.message_handler(
#     func=lambda message: message.from_user.id in user_states and 'editing_url' in user_states[message.from_user.id])
# def handle_new_url_input(message):
#     user_id = message.from_user.id
#     new_url = message.text.strip()
#     offer = user_states[user_id]['offer_to_edit']
#
#     # Обновляем URL оффера
#     offer.url_to = new_url
#     session.commit()  # Сохраняем изменения в базе данных
#
#     bot.send_message(message.chat.id,
#                      f"URL для оффера с internal_id {offer.internal_id} успешно обновлен на: {new_url}")
#
#     # Удаляем состояние редактирования
#     del user_states[user_id]
#
#
# # Обработка нового значения описания
# @bot.message_handler(func=lambda message: message.from_user.id in user_states and 'editing_description' in user_states[
#     message.from_user.id])
# def handle_new_description_input(message):
#     user_id = message.from_user.id
#     new_description = message.text.strip()
#     offer = user_states[user_id]['offer_to_edit']
#
#     # Обновляем описание оффера
#     offer.description = new_description
#     session.commit()  # Сохраняем изменения в базе данных
#
#     bot.send_message(message.chat.id,
#                      f"Описание для оффера с internal_id {offer.internal_id} успешно обновлено на: {new_description}")
#
#     # Удаляем состояние редактирования
#     del user_states[user_id]
#
#
# # Обработка текстовых сообщений от пользователей для ввода URL
# @bot.message_handler(func=lambda message: message.from_user.id in user_states and 'update_existing' not in user_states[
#     message.from_user.id])
# def handle_url_input(message):
#     user_id = message.from_user.id
#     user_state = user_states[user_id]
#
#     url_to = message.text.strip()
#     internal_ids = user_state['internal_ids']
#     current_index = user_state['current_index']
#
#     current_internal_id_data = internal_ids[current_index]
#     internal_id = current_internal_id_data.get('internal_id')
#
#     offer = session.query(Offer).filter_by(internal_id=internal_id).first()
#
#     if offer:
#         offer.url_to = url_to
#         session.commit()
#         bot.reply_to(message, f"Ссылка для internal_id {internal_id} обновлена на: {url_to}")
#
#         current_index += 1
#         user_state['current_index'] = current_index
#
#         if current_index < len(internal_ids):
#             next_internal_id_data = internal_ids[current_index]
#             next_internal_id = next_internal_id_data.get('internal_id')
#             bot.reply_to(message, f"Пожалуйста, введите URL для предложения с internal_id: {next_internal_id}")
#         else:
#             del user_states[user_id]
#             bot.reply_to(message, "Все ссылки успешно обновлены.")
#     else:
#         bot.reply_to(message, f"Предложение с internal_id {internal_id} не найдено.")


#####################################################################################################################
# Обработка нажатия кнопки "СГЕНЕРИРОВАТЬ РЕФЕРАЛЬНУЮ ССЫЛКУ"
@bot.message_handler(func=lambda message: message.text == "СГЕНЕРИРОВАТЬ РЕФЕРАЛЬНУЮ ССЫЛКУ")
def handle_referral_link(message):
    telegram_user_id = message.from_user.id

    # Найдем пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=telegram_user_id).first()

    if user:
        # Генерируем реферальную ссылку с UUID пользователя
        ref_link = f"https://t.me/VgostiBot2_bot?start={user.uuid}"

        # Генерация QR-кода (здесь предполагается, что у вас есть функция qr_generate)
        qr_generate(ref_link, f"{os.getcwd()}/pdfs/host.pdf", f"{user.uuid}")

        # Путь к PDF файлу
        pdf_path = f"{os.getcwd()}/pdfs/created/{user.uuid}.pdf"

        # Проверяем, существует ли файл по указанному пути
        if os.path.exists(pdf_path):
            # Отправляем PDF файл пользователю
            with open(pdf_path, 'rb') as pdf_file:
                bot.send_document(message.chat.id, pdf_file)

            # Отправляем сообщение с реферальной ссылкой
            bot.send_message(message.chat.id, f"Ваша реферальная ссылка: {ref_link}")
        else:
            # Если файл не найден, отправляем сообщение об ошибке
            bot.send_message(message.chat.id, "Не удалось найти PDF файл. Попробуйте позже.")
    else:
        bot.send_message(message.chat.id, "Вы не зарегистрированы.")


# Команда для получения рефералов до 6 уровня
@bot.message_handler(commands=['allrefstats'])
def handle_allrefstats(message):
    telegram_user_id = message.from_user.id

    # Ищем пользователя по telegram_user_id
    user = session.query(User).filter_by(telegram_id=telegram_user_id).first()

    if user:
        # Получаем реферальную цепочку
        all_referrals = get_referral_chain(user)

        # Формируем сообщение с деталями
        if all_referrals:
            message_text = "Рефералы до 6 уровня:\n"
            for referral_info in all_referrals:
                subscription_status = "Подписка активна" if referral_info[
                    "has_active_subscription"] else "Подписка не активна"
                message_text += f"telegram_id: {referral_info['telegram_id']} Имя: {referral_info['first_name']}, Уровень: {referral_info['level']}, {subscription_status}\n"
        else:
            message_text = "У вас нет рефералов."

        bot.send_message(message.chat.id, message_text)
    else:
        bot.send_message(message.chat.id, "Вы не зарегистрированы.")


if __name__ == "__main__":
    bot.polling()
