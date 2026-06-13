import logging
import os
import sys
import time
import requests
import vk_api

from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()

# Переменные окружения
# VK_TOKEN = os.getenv('VK_TOKEN')
# VK_GROUP_ID = os.getenv('VK_GROUP_ID')
# VK_USER_ID = os.getenv('VK_USER_ID')
# PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

# Константы проекта
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {os.getenv('PRACTICUM_TOKEN')}'}
RETRY_PERIOD = 600

# 1. Создаем логгер и задаем уровень (например, DEBUG)
logger = logging.getLogger("my_app_logger")
logger.setLevel(logging.DEBUG)

# 2. Создаем обработчик для вывода в sys.stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

# 3. Задаем формат вывода логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 4. Добавляем обработчик к логгеру
logger.addHandler(handler)


# Словарь со статусами
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(vk, message):
    """Отправка сообщения пользователю."""
    try:
        vk.messages.send(
            user_id=os.getenv('VK_USER_ID'),
            message=str(message),
            random_id=int(time.time() * 1000)
        )
        logger.debug(f'Сообщение успешно отправлено в VK: {message}')
    except Exception as error:
        logger.error(f'Ошибка отправки сообщения в VK {error}', exc_info=True)


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
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError(
            'В словаре homework отсутствует ключ "homework_name"'
        )

    if 'status' not in homework:
        raise KeyError(
            'В словаре homework отсутствует ключ "status"'
        )

    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Обнаружен неизвестный статус работы: {homework_status}'
        )

    verdict = HOMEWORK_VERDICTS[homework_status]

    return (
        f'Изменился статус проверки работы "{homework_name}". '
        f'{verdict}'
    )


def check_tokens():
    """Проверяет доступность переменных окружения."""
    # return all([VK_TOKEN, VK_GROUP_ID, VK_USER_ID, PRACTICUM_TOKEN])
    return all([
    os.getenv('VK_TOKEN'),
    os.getenv('VK_GROUP_ID'),
    os.getenv('VK_USER_ID'),
    os.getenv('PRACTICUM_TOKEN')
])


def main():
    """Основная логика работы бота."""
    # Если check_tokens() вернул False (какого-то токена нет)
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения!')
        raise Exception('Критическая ошибка: отсутствуют токены окружения.')

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    # Инициализируем timestamp за последние 24 часа
    current_timestamp = int(time.time()) - 86400
    last_status = ''  # Чтобы не спамить одним и тем же статусом

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
                # Проверяем, изменился ли статус с момента последней проверки
                if message != last_status:
                    send_message(vk, message)
                    last_status = message
                else:
                    logger.debug('Статус домашней работы не изменился.')
            else:
                logger.debug('В ответе нет новых домашних работ.')

            current_timestamp = response.get('current_date', int(time.time()))

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(vk, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
