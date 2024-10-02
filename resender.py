import requests
from dotenv import load_dotenv
import os
from loguru import logger
import json

load_dotenv()

# Инициализация бота
SECOND_BOT_TOKEN = os.getenv('SECOND_BOT_TOKEN')

# URL для отправки сообщения через API второго бота
SEND_MESSAGE_URL = f'https://api.telegram.org/bot{SECOND_BOT_TOKEN}/sendMessage'


@logger.catch
def escape_markdown(text):
    """
    Экранирует специальные символы для MarkdownV2
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])


@logger.catch
def resend_message_with_buttons(bot, message, target_chat_id, text):
    # Экранируем текст
    escaped_text = escape_markdown(text)

    # Создаем кнопки
    buttons = [
        [
            {
                "text": "Кнопка 1",
                "callback_data": "button_1_pressed"
            },
            {
                "text": "Кнопка 2",
                "callback_data": "button_2_pressed"
            }
        ]
    ]

    # Создаем reply_markup с кнопками
    reply_markup = {
        "inline_keyboard": buttons
    }

    # Данные для отправки сообщения с кнопками
    data = {
        'chat_id': target_chat_id,
        'text': escaped_text,
        'parse_mode': 'MarkdownV2',
        'reply_markup': json.dumps(reply_markup)  # Нужно передавать JSON строкой
    }

    # Отправляем сообщение через API второго бота
    response = requests.post(SEND_MESSAGE_URL, data=data)

    if response.status_code == 200:
        logger.info("Сообщение с кнопками успешно отправлено!")
        return True
    else:
        logger.error(f"Ошибка при отправке сообщения: {response.status_code}")
        logger.info(f"Ответ: {response.text}")
        return False
