import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import vk_api

# Переменные окружения
VK_TOKEN = os.getenv('VK_TOKEN')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')
VK_USER_ID = os.getenv('VK_USER_ID')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

# Константы проекта
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
RETRY_PERIOD = 600

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Словарь со статусами
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(vk, message):
    """Отправляет сообщение в VK пользователю VK_USER_ID."""
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=str(message),
            random_id=int(time.time() * 1000)
        )
        logging.debug(f'Сообщение успешно отправлено в VK: {message}')
    except Exception as error:
        logging.error(
            f'Ошибка отправки сообщения в VK: {error}',
            exc_info=True
        )


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса Практикума."""
    payload = {'from_date': current_timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise ConnectionError(f'Ошибка при запросе к API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise ValueError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа: {response.status_code}'
        )

    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем')

    if 'homeworks' not in response:
        raise ValueError('В ответе API отсутствует ключ "homeworks"')

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError('Под ключом "homeworks" пришел не список')

    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework = homework[0] 
    if 'homework_name' not in homework:
        raise KeyError('В словаре homework отсутствует ключ "homework_name"')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Обнаружен неизвестный статус работы: {homework_status}'
        )

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([VK_TOKEN, VK_GROUP_ID, VK_USER_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствуют обязательные переменные окружения!')
        return

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    timestamp = int(time.time())
    last_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks)
                send_message(vk, message)
            else:
                logging.info('Обновлений по домашним работам нет.')

            timestamp = response.get('current_date', timestamp)
            last_error = ''

            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)

            if message != last_error:
                send_message(vk, message)
                last_error = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
