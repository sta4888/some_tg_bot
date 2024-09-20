import telebot
from connect import session
from models import User, Offer
from dotenv import load_dotenv
import os
import requests  # Добавим библиотеку для HTTP-запросов
from service import parse_and_save_offer

load_dotenv()

API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения состояния пользователей
user_states = {}


# Обработчик команды /start с приветствием для хоста
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    # Найдем пользователя или создадим нового
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if user is None:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
            is_client=False  # По умолчанию не хост
        )
        session.add(user)
        session.commit()

    if user.is_client:
        bot.reply_to(message, "Привет! Вы зарегистрированы как пользователь.")
    else:
        bot.reply_to(message, "Добро пожаловать, хост! Пожалуйста, отправьте ссылку на XML-файл.")

    # Инициализируем состояние пользователя для обработки URL
    user_states[message.from_user.id] = {'url_input': True}


@bot.message_handler(func=lambda message: 'https://realtycalendar.ru/xml_feed' in message.text)
def handle_url_input(message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    url = message.text.strip()

    try:
        # Пытаемся загрузить и обработать XML-файл
        response = requests.get(url)
        response.raise_for_status()
        xml_data = response.content.decode('utf-8')

        internal_ids = parse_and_save_offer(xml_data, bot, message)

        if internal_ids:
            user_states[message.from_user.id]['internal_ids'] = internal_ids
            user_states[message.from_user.id]['current_index'] = 0
            bot.reply_to(message, f"Пожалуйста, введите URL для предложения с internal_id: {internal_ids[0]}")
        else:
            bot.reply_to(message, "В загруженном файле нет ни одного нового объекта.")

    except Exception as e:
        bot.reply_to(message, f"Ошибка при загрузке файла: {str(e)}.")


# Другие обработчики остаются без изменений


# Обработка текстовых сообщений от пользователей для ввода URL
@bot.message_handler(func=lambda message: message.text.startswith(
    "https://realtycalendar.ru/apart") and not message.from_user.id in user_states)
def request_url(message):
    user_states[message.from_user.id] = {'url_input': True}
    bot.reply_to(message, "Пожалуйста, введите ссылку на XML-файл.")


# Остальные обработчики остаются без изменений

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
        internal_id = internal_ids[current_index]
        offer = session.query(Offer).filter_by(internal_id=internal_id).first()

        if offer and offer.created_by == user_id:
            # Здесь нужно обновить данные предложения
            session.commit()
            bot.reply_to(message, f"Данные для internal_id {internal_id} обновлены.")

            # Переход к следующему internal_id
            current_index += 1
            user_state['current_index'] = current_index

            if current_index < len(internal_ids):
                next_internal_id = internal_ids[current_index]
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


# Обработка текстовых сообщений от пользователей для ввода URL
@bot.message_handler(func=lambda message: message.from_user.id in user_states and 'update_existing' not in user_states[
    message.from_user.id])
def handle_url_input(message):
    user_id = message.from_user.id
    user_state = user_states[user_id]

    url_to = message.text.strip()
    internal_ids = user_state['internal_ids']
    current_index = user_state['current_index']

    internal_id = internal_ids[current_index]
    offer = session.query(Offer).filter_by(internal_id=internal_id).first()

    if offer:
        offer.url_to = url_to
        session.commit()
        bot.reply_to(message, f"Ссылка для internal_id {internal_id} обновлена на: {url_to}")

        current_index += 1
        user_state['current_index'] = current_index

        if current_index < len(internal_ids):
            next_internal_id = internal_ids[current_index]
            bot.reply_to(message, f"Пожалуйста, введите URL для предложения с internal_id: {next_internal_id}")
        else:
            del user_states[user_id]
            bot.reply_to(message, "Все ссылки успешно обновлены.")
    else:
        bot.reply_to(message, f"Предложение с internal_id {internal_id} не найдено.")


if __name__ == "__main__":
    bot.polling()
