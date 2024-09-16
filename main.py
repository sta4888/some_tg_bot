import telebot

from connect import session
from models import Base, User

from dotenv import load_dotenv
import os

load_dotenv()

# Инициализация бота
API_TOKEN = os.environ.get('BOT_TOKEN')
DATABASE_URL = os.environ.get('DB_URL')
bot = telebot.TeleBot(API_TOKEN)


# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    # Пример сохранения пользователя в базу данных
    user = User(telegram_id=message.from_user.id, username=message.from_user.username)
    session.add(user)
    session.commit()


if __name__ == "__main__":
    bot.polling()
