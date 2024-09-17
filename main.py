import telebot

from connect import session
from models import Base, User
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

from service import parse_and_save_offer

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    command_params = message.text.split()

    # По умолчанию реферер отсутствует
    referer_id = None

    if len(command_params) > 1:  # Если есть реферальный ID
        try:
            referer_id = int(command_params[1])
        except ValueError:
            bot.reply_to(message, "Некорректный реферальный код.")

    # Ищем пользователя в базе данных
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь не найден, создаем нового
    if user is None:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,  # Поправил на message.chat.id
            is_client=False,
            referer_id=referer_id  # Устанавливаем реферера, если он есть
        )
        session.add(user)
        session.commit()
        bot.reply_to(message, "Новый пользователь добавлен.")
    else:
        bot.reply_to(message, "Вы уже зарегистрированы.")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    # Проверка MIME-типа файла (должен быть 'application/xml' или 'text/xml')
    if message.document.mime_type in ['application/xml', 'text/xml']:
        file_info = bot.get_file(message.document.file_id)

        # Загружаем файл
        downloaded_file = bot.download_file(file_info.file_path)

        try:
            # Декодируем байты в строку
            xml_data = downloaded_file.decode('utf-8')

            # Парсим XML-файл и сохраняем данные с помощью BeautifulSoup
            parse_and_save_offer(xml_data)

            # Пример: выводим корневой элемент
            soup = BeautifulSoup(xml_data, 'xml')
            bot.reply_to(message, f"Файл XML получен! Корневой элемент: {soup.find().name}")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при чтении XML файла: {str(e)}.")
    else:
        bot.reply_to(message, "Этот файл не является XML.")


if __name__ == "__main__":
    bot.polling()
