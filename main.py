import telebot

from connect import session
from models import Base, User
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os


load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)


# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    # Получаем данные о реферале из команды, если она есть
    command_params = message.text.split()

    referer_id = None
    if len(command_params) > 1:
        try:
            referer_id = int(command_params[1])
        except ValueError:
            bot.reply_to(message, "Некорректный реферальный код.")

    # Поиск пользователя по telegram_id
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь не найден, создаем нового без агентства
    if user is None:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
            is_client=False,
            referer_id=referer_id
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
            agency_id = parse_and_save_offer(xml_data)

            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

            if user:
                user.agency_id = agency_id
                session.commit()
                print(f"Пользователь {user.id} связан с агентством {agency_id}.")
            else:
                print("Пользователь не найден.")

            # Пример: выводим корневой элемент
            soup = BeautifulSoup(xml_data, 'xml')
            bot.reply_to(message, f"Файл XML получен! Корневой элемент: {soup.find().name}")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при чтении XML файла: {str(e)}.")
    else:
        bot.reply_to(message, "Этот файл не является XML.")


if __name__ == "__main__":
    bot.polling()
