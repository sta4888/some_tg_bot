import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Инициализация бота
SECOND_BOT_TOKEN = os.environ.get('SECOND_BOT_TOKEN')

# URL для отправки сообщения второму боту
SEND_MESSAGE_URL = f'https://api.telegram.org/bot{SECOND_BOT_TOKEN}/sendMessage'


# Обработчик команды /start
def resend_message(bot, message, target_chat_id):
    bot.send_message(message.chat.id, "Сообщение отправлено другому боту!")

    # Сообщение для второго бота
    message_text = 'Привет из первого бота!'

    # Данные для отправки сообщения второму боту
    data = {
        'chat_id': target_chat_id,
        'text': message_text
    }

    # Отправляем сообщение второму боту через API
    response = requests.post(SEND_MESSAGE_URL, data=data)

    if response.status_code == 200:
        print("Сообщение успешно отправлено второму боту!")
    else:
        print(f"Ошибка при отправке сообщения: {response.status_code}")
