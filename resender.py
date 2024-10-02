import requests
from dotenv import load_dotenv
import os
from loguru import logger
load_dotenv()

# Инициализация бота
SECOND_BOT_TOKEN = os.environ.get('SECOND_BOT_TOKEN')

# URL для отправки сообщения второму боту
SEND_MESSAGE_URL = f'https://api.telegram.org/bot{SECOND_BOT_TOKEN}/sendMessage'


def escape_markdown(text):
    """
    Экранирует специальные символы для MarkdownV2
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])


def resend_message(bot, message, target_chat_id, text):
    # URL для отправки сообщения через API второго бота
    send_message_url = f'https://api.telegram.org/bot{SECOND_BOT_TOKEN}/sendMessage'

    # Экранируем текст
    escaped_text = escape_markdown(text)

    # Данные для отправки сообщения второму боту
    data = {
        'chat_id': target_chat_id,
        'text': escaped_text,
        'parse_mode': 'MarkdownV2'
    }

    # Отправляем сообщение второму боту через API
    response = requests.post(send_message_url, data=data)

    if response.status_code == 200:
        print("Сообщение успешно отправлено второму боту!")
        return True
    else:
        print(f"Ошибка при отправке сообщения: {response.status_code}")
        print(f"Ответ: {response.text}")
        return False
