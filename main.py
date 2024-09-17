import telebot

from connect import session
from models import Base, User

from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
from service import parse_and_save_offer

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    # Пример сохранения пользователя в базу данных
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь не найден, создайте нового
    if user is None:
        user = User(telegram_id=message.from_user.id, username=message.from_user.username)
        session.add(user)


@bot.message_handler(content_types=['document'])
def handle_document(message):
    # Проверка MIME-типа файла (должен быть 'application/xml' или 'text/xml')
    if message.document.mime_type in ['application/xml', 'text/xml']:
        file_info = bot.get_file(message.document.file_id)

        # Загружаем файл
        downloaded_file = bot.download_file(file_info.file_path)

        try:
            # Парсим XML-файл
            root = ET.fromstring(downloaded_file)
            # parse_and_save_offer(root)
            print(root)

            # Пример: выводим корневой элемент
            bot.reply_to(message, f"Файл XML получен! Корневой элемент: {root.tag}")
        except ET.ParseError:
            bot.reply_to(message, "Ошибка при чтении XML файла. Возможно, это невалидный XML.")
    else:
        bot.reply_to(message, "Этот файл не является XML.")



if __name__ == "__main__":
    bot.polling()
