import telebot
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from models import Base, User

# Инициализация бота
API_TOKEN = "YOUR_BOT_API_KEY"
bot = telebot.TeleBot(API_TOKEN)

# # Настройка подключения к базе данных PostgreSQL через SQLAlchemy
# DATABASE_URL = "postgresql://botuser:@localhost/botdatabase"
# engine = create_engine(DATABASE_URL)
# Session = sessionmaker(bind=engine)
# session = Session()


# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    res = bot.get_me()
    print(res)
    bot.reply_to(message, "Привет! Добро пожаловать в нашего бота.")

    # # Пример сохранения пользователя в базу данных
    # user = User(telegram_id=message.from_user.id, username=message.from_user.username)
    # session.add(user)
    # session.commit()


if __name__ == "__main__":
    bot.polling()
