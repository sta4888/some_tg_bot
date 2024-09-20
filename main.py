import telebot
from connect import session
from models import User, Offer  # Обновленные модели
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from service import parse_and_save_offer

load_dotenv()

API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Временное хранилище данных, пока пользователь вводит ссылки
user_offer_data = {}


# Обработчик команды /start с приветствием для хоста
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    # Поиск пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь не зарегистрирован, добавляем его
    if user is None:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
            is_client=False  # По умолчанию не хост
        )
        session.add(user)
        session.commit()

    # Приветствие для хостов
    if user.is_client:  # Или используйте другой флаг для хоста
        bot.reply_to(message, "Привет! Вы зарегистрированы как пользователь.")
    else:
        bot.reply_to(message, "Добро пожаловать, хост! Пожалуйста, загрузите XML-файл.")


# Обработка загрузки XML-файла
# Словарь для хранения состояния пользователей
user_states = {}


# Обработка загрузки XML-файла
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if message.document.mime_type in ['application/xml', 'text/xml']:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        try:
            xml_data = downloaded_file.decode('utf-8')
            internal_ids = parse_and_save_offer(xml_data, bot, message)

            # Запросим у пользователя ссылки для каждого internal_id
            if internal_ids:
                user_states[message.from_user.id] = internal_ids
                bot.reply_to(message,
                             f"Пожалуйста, введите URL для предложений с internal_id: {', '.join(internal_ids)}")

        except Exception as e:
            bot.reply_to(message, f"Ошибка при обработке XML файла: {str(e)}.")
    else:
        bot.reply_to(message, "Этот файл не является XML.")


# Обработка текстовых сообщений от пользователей
@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def handle_url_input(message):
    user_id = message.from_user.id
    internal_ids = user_states[user_id]

    # Получаем ссылку от пользователя
    url_to = message.text.strip()

    # Обновляем значение url_to для соответствующего internal_id
    if internal_ids:
        internal_id = internal_ids.pop(0)  # Получаем первый internal_id
        offer = session.query(Offer).filter_by(internal_id=internal_id).first()

        if offer:
            offer.url_to = url_to
            session.commit()
            bot.reply_to(message, f"Ссылка для internal_id {internal_id} обновлена на: {url_to}")

            # Если все internal_ids обработаны, удаляем пользователя из состояния
            if not internal_ids:
                del user_states[user_id]
        else:
            bot.reply_to(message, f"Предложение с internal_id {internal_id} не найдено.")
    else:
        bot.reply_to(message, "Произошла ошибка, попробуйте снова.")


if __name__ == "__main__":
    bot.polling()
