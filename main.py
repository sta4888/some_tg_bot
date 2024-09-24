import telebot

from uuid import UUID
from telebot import types
from connect import session
from models import User, Offer, XML_FEED
from dotenv import load_dotenv
import os
import requests  # Добавим библиотеку для HTTP-запросов
from service import parse_and_save_offer, qr_generate, get_referral_chain

load_dotenv()

API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения состояния пользователей
user_states = {}


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Извлекаем реферальный UUID, если он был передан
    command = message.text.split()
    referrer_uuid = None

    if len(command) > 1:
        try:
            referrer_uuid = UUID(command[1])  # Парсим переданный UUID
        except ValueError:
            bot.send_message(message.chat.id, "Неверная реферальная ссылка.")
            referrer_uuid = None

    # Найдем пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь новый, создаем его
    if user is None:
        referer = None

        # Если есть реферальный UUID, найдем пользователя-реферера
        if referrer_uuid:
            referer = session.query(User).filter_by(uuid=referrer_uuid).first()

        # Создаем нового пользователя с реферальной информацией (если есть)
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
            is_client=False,  # По умолчанию не хост
            referer=referer  # Сохраняем реферера, если он есть
        )

        session.add(user)

        # Если есть реферер, увеличим его счетчик приглашений
        if referer:
            referer.invited_count += 1
            session.add(referer)

        session.commit()

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    ref_link_btn = types.KeyboardButton("СГЕНЕРИРОВАТЬ РЕФЕРАЛЬНУЮ ССЫЛКУ")
    markup.add(ref_link_btn)

    # Отправляем приветственное сообщение с клавиатурой
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в нашего бота.", reply_markup=markup)

    # Логика приветствия для разных типов пользователей
    if user.is_client:
        bot.send_message(message.chat.id, "Привет! Вы зарегистрированы как пользователь.")
    else:
        bot.send_message(message.chat.id, "Добро пожаловать, хост! Пожалуйста, отправьте ссылку на XML-файл.")

    # Инициализируем состояние пользователя для обработки URL
    user_states[message.from_user.id] = {'url_input': True}


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


@bot.message_handler(func=lambda message: 'https://realtycalendar.ru/xml_feed' in message.text)
def handle_url_input(message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    url = message.text.strip()

    if not user:
        bot.reply_to(message, "Пользователь не найден.")
        return

    try:
        # Пытаемся загрузить и обработать XML-файл
        response = requests.get(url)
        response.raise_for_status()
        xml_data = response.content.decode('utf-8')

        # Здесь происходит парсинг и сохранение предложений
        internal_ids = parse_and_save_offer(xml_data, bot, message)
        print(internal_ids)

        if internal_ids:
            # Сохраняем ссылку в таблице XML_FEED
            new_feed = XML_FEED(url=url, user_id=user.id)
            session.add(new_feed)
            session.commit()

            bot.send_message(message.chat.id, f'спасибо! 👌\nДобавлено объектов: {len(internal_ids)}')
            user_states[message.from_user.id] = {'internal_ids': internal_ids, 'current_index': 0}

            first_internal_id = internal_ids[0].get('internal_id')
            first_location_address = internal_ids[0].get('location_address')
            bot.reply_to(message,
                         f"Пожалуйста, введите URL для объекта с internal_id: {first_internal_id}\nадресом: {first_location_address}")
        else:
            bot.reply_to(message, "В загруженном файле нет ни одного нового объекта.")

    except Exception as e:
        session.rollback()  # В случае ошибки откатываем транзакцию
        bot.reply_to(message, f"Ошибка при загрузке файла: {str(e)}.")


# Обработка текстовых сообщений от пользователей для ввода URL
@bot.message_handler(func=lambda message: message.text.startswith(
    "https://realtycalendar.ru/apart") and not message.from_user.id in user_states)
def request_url(message):
    user_states[message.from_user.id] = {'url_input': True}
    bot.reply_to(message, "Пожалуйста, введите ссылку на XML-файл.")


# Обработка ответа на запрос обновления
@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and 'update_existing' in user_states[message.from_user.id])
def handle_update_confirmation(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]

    if message.text.strip().lower() == 'да':
        # Обновляем данные для существующих internal_id
        internal_ids = user_state['internal_ids']
        current_index = user_state['current_index']
        current_internal_id_data = internal_ids[current_index]
        internal_id = current_internal_id_data.get('internal_id')

        offer = session.query(Offer).filter_by(internal_id=internal_id).first()

        if offer and offer.created_by == user_id:
            # Здесь нужно обновить данные предложения
            session.commit()
            bot.reply_to(message, f"Данные для internal_id {internal_id} обновлены.")

            # Переход к следующему internal_id
            current_index += 1
            user_state['current_index'] = current_index

            if current_index < len(internal_ids):
                next_internal_id_data = internal_ids[current_index]
                next_internal_id = next_internal_id_data.get('internal_id')
                bot.reply_to(message,
                             f"Обновите данные для internal_id: {next_internal_id}. Пожалуйста, введите новый URL.")
            else:
                del user_states[user_id]  # Удаляем пользователя из состояния
                bot.reply_to(message, "Все данные успешно обновлены.")
        else:
            bot.reply_to(message, f"Предложение с internal_id {internal_id} не найдено или не принадлежит вам.")
    else:
        # Если пользователь не хочет обновлять, просто удаляем состояние
        del user_states[user_id]
        bot.reply_to(message, "Обновление данных отменено.")


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


# Обработка команды для редактирования оффера
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

    # Инициализируем состояние пользователя, если оно еще не существует
    if message.from_user.id not in user_states:
        user_states[message.from_user.id] = {}

    # Отправляем пользователю список офферов с кнопками
    markup = types.InlineKeyboardMarkup()
    for offer in offers:
        button = types.InlineKeyboardButton(text=f"Оффер {offer.internal_id}",
                                            callback_data=f"edit_offer_{offer.internal_id}")
        markup.add(button)

    bot.send_message(message.chat.id, "Выберите оффер для редактирования:", reply_markup=markup)


# Обработка выбора оффера для редактирования
@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_offer_"))
def handle_offer_selection(call):
    print(call.data)
    internal_id = call.data.split("_")[2]
    print(internal_id)
    offer = session.query(Offer).filter_by(internal_id=str(internal_id)).first()
    print(f"--offer {offer}")
    print(f"--offer {offer.creator.telegram_id == call.from_user.id}")

    if offer and offer.creator.telegram_id == call.from_user.id:
        # Отправляем текущее состояние оффера
        offer_details = f"Текущий оффер:\nID: {offer.internal_id}\nURL: {offer.url_to}\nОписание: {offer.description}"
        bot.send_message(call.message.chat.id, offer_details)

        # Запрашиваем, что именно редактировать
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Изменить URL", "Изменить описание", "Отмена")
        bot.send_message(call.message.chat.id, "Что вы хотите изменить?", reply_markup=markup)

        # Сохраняем оффер для дальнейшего редактирования
        user_states[call.from_user.id]['offer_to_edit'] = offer
    else:
        bot.send_message(call.message.chat.id, "Ошибка: Оффер не найден или не принадлежит вам.")


# Обработка выбора действия редактирования
@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and 'offer_to_edit' in user_states[message.from_user.id])
def handle_edit_choice(message):
    user_id = message.from_user.id
    offer = user_states[user_id]['offer_to_edit']

    if message.text == "Изменить URL":
        bot.send_message(message.chat.id, "Введите новый URL для этого оффера:")
        user_states[user_id]['editing_url'] = True
    elif message.text == "Изменить описание":
        bot.send_message(message.chat.id, "Введите новое описание для этого оффера:")
        user_states[user_id]['editing_description'] = True
    elif message.text == "Отмена":
        del user_states[user_id]  # Удаляем состояние редактирования
        bot.send_message(message.chat.id, "Редактирование отменено.")
    else:
        bot.send_message(message.chat.id, "Неизвестная команда.")


# Обработка нового значения URL
@bot.message_handler(
    func=lambda message: message.from_user.id in user_states and 'editing_url' in user_states[message.from_user.id])
def handle_new_url_input(message):
    user_id = message.from_user.id
    new_url = message.text.strip()
    offer = user_states[user_id]['offer_to_edit']

    # Обновляем URL оффера
    offer.url_to = new_url
    session.commit()  # Сохраняем изменения в базе данных

    bot.send_message(message.chat.id,
                     f"URL для оффера с internal_id {offer.internal_id} успешно обновлен на: {new_url}")

    # Удаляем состояние редактирования
    del user_states[user_id]


# Обработка нового значения описания
@bot.message_handler(func=lambda message: message.from_user.id in user_states and 'editing_description' in user_states[
    message.from_user.id])
def handle_new_description_input(message):
    user_id = message.from_user.id
    new_description = message.text.strip()
    offer = user_states[user_id]['offer_to_edit']

    # Обновляем описание оффера
    offer.description = new_description
    session.commit()  # Сохраняем изменения в базе данных

    bot.send_message(message.chat.id,
                     f"Описание для оффера с internal_id {offer.internal_id} успешно обновлено на: {new_description}")

    # Удаляем состояние редактирования
    del user_states[user_id]


# Обработка текстовых сообщений от пользователей для ввода URL
@bot.message_handler(func=lambda message: message.from_user.id in user_states and 'update_existing' not in user_states[
    message.from_user.id])
def handle_url_input(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]

    url_to = message.text.strip()
    internal_ids = user_state['internal_ids']
    current_index = user_state['current_index']

    current_internal_id_data = internal_ids[current_index]
    internal_id = current_internal_id_data.get('internal_id')

    offer = session.query(Offer).filter_by(internal_id=internal_id).first()

    if offer:
        offer.url_to = url_to
        session.commit()
        bot.reply_to(message, f"Ссылка для internal_id {internal_id} обновлена на: {url_to}")

        current_index += 1
        user_state['current_index'] = current_index

        if current_index < len(internal_ids):
            next_internal_id_data = internal_ids[current_index]
            next_internal_id = next_internal_id_data.get('internal_id')
            bot.reply_to(message, f"Пожалуйста, введите URL для предложения с internal_id: {next_internal_id}")
        else:
            del user_states[user_id]
            bot.reply_to(message, "Все ссылки успешно обновлены.")
    else:
        bot.reply_to(message, f"Предложение с internal_id {internal_id} не найдено.")


if __name__ == "__main__":
    bot.polling()
