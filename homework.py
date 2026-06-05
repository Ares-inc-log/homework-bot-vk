import os
import request
import vk_api
import json
import logging

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from datetime import time
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

keyboard = {
    "one_time": False,
    "buttons": [[
            {
                "action": {"type": "text", "label": "Какой статус домашки?"},
                "color": "positive"
            },
    ]]
}
keyboard_json = json.dumps(keyboard, ensure_ascii=False)


def check_tokens():
    return all([
        PRACTICUM_TOKEN,
        VK_TOKEN,
        VK_USER_ID,
        VK_GROUP_ID
    ])


def send_message(vk, message):
    vk.messages.send(
    message=message,
    keyboard=keyboard_json,
    random_id=0
)


def get_api_answer(timestamp):
    response = request.get(ENDPOINT, headers=HEADERS, params=timestamp)
    return response.json()


def check_response(response):
    if response['homework']['current_date']:
        return



def parse_status(homework):

        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Создаем сессию для бота
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)
    timestamp = int(time.time())

    while True:
        try:

            ...

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        ...


if __name__ == '__main__':
    main()
