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
        bot.reply_to(message, "Добро пожаловать, хост! Пожалуйста, загрузите XML-файл.")
    else:
        bot.reply_to(message, "Привет! Вы зарегистрированы как пользователь.")


# Обработка загрузки XML-файла
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # # Проверяем, является ли пользователь хостом
    # if not user or not user.is_client:
    #     bot.reply_to(message, "Только хосты могут загружать XML-файлы.")
    #     return

    if message.document.mime_type in ['application/xml', 'text/xml']:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        try:
            xml_data = downloaded_file.decode('utf-8')

            # Парсим данные и запускаем генератор
            offers_generator = parse_and_save_offer(xml_data)
            next_offer = next(offers_generator)

            # Сохраняем текущее состояние (данные пользователя и генератора) во временную переменную
            user_offer_data[message.from_user.id] = {
                'generator': offers_generator,
                'current_offer_id': next_offer,
                'file_uploaded': True
            }

            bot.reply_to(message, f"XML файл загружен. Введите ссылку для предложения с internal_id: {next_offer}")

        except Exception as e:
            bot.reply_to(message, f"Ошибка при обработке XML файла: {str(e)}.")
    else:
        bot.reply_to(message, "Этот файл не является XML.")


# Обработка ввода ссылки для предложения
@bot.message_handler(
    func=lambda message: message.from_user.id in user_offer_data and user_offer_data[message.from_user.id][
        'file_uploaded'])
def handle_offer_link(message):
    user_data = user_offer_data[message.from_user.id]

    # Получаем текущий internal_id и ссылку, введённую пользователем
    internal_id = user_data['current_offer_id']
    offer_link = message.text

    # Сохраняем ссылку в базу данных
    offer = session.query(Offer).filter_by(id=internal_id).first()
    if offer:
        offer.link = offer_link  # Обновляем предложение ссылкой
        session.commit()

        bot.reply_to(message, f"Ссылка для предложения {internal_id} сохранена.")

        # Переходим к следующему предложению
        try:
            next_offer = next(user_data['generator'])
            user_data['current_offer_id'] = next_offer
            bot.reply_to(message, f"Введите ссылку для предложения с internal_id: {next_offer}")
        except StopIteration:
            bot.reply_to(message, "Все предложения обработаны.")
            del user_offer_data[message.from_user.id]  # Удаляем данные, когда все предложения обработаны
    else:
        bot.reply_to(message, "Предложение не найдено. Попробуйте снова.")


if __name__ == "__main__":
    bot.polling()
