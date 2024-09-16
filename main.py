import telebot

from connect import session
from models import Base, User

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

    # Пример сохранения пользователя в базу данных
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Если пользователь не найден, создайте нового
    if user is None:
        user = User(telegram_id=message.from_user.id, username=message.from_user.username)
        session.add(user)


if __name__ == "__main__":
    bot.polling()
