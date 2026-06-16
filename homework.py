import logging
import sys
import time
import requests
import vk_api

from http import HTTPStatus

from .Exceptions import NotTokens


# Переменные окружения
VK_TOKEN = ('vk1.a.oFp-9yTHjnEOR6AVUmxLIySZDtz_I3ze1IFQbWyrvmGYaSq1NOTKLjdoE_'
    'xGw8bwso4ZgVrCEzbH4KHNAFt0UwqwDPcmLSA9DEYGW3ZIS-ngPvyPuiEi1umykPe'
    'QEBmQIEjSioUaHSS05AZrFI4afMx6oryU-fxt55lRqAXGjBsW7CGiG3RiTPcfEQkZ'
    'j1_aA5gUi12S2G_nw4L5MbXJow'
)
VK_GROUP_ID = 239244542
VK_USER_ID = 554046097
PRACTICUM_TOKEN = 'y0__wgBENqPxZMIGJG5GCCPvvHmFygCV5pMK0ir17SIEHrIPzN2EcRGfwI'

# Константы проекта
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
RETRY_PERIOD = 600

# 1. Создаем логгер и задаем уровень (например, DEBUG)
logger = logging.getLogger('my_app_logger')
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
    vk.messages.send(
        user_id=VK_USER_ID,
        message=str(message),
        random_id=int(time.time() * 1000)
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
            f'Параметры: {payload}'
            f'Код ответа: {response.status_code}'
            f'Тело ответа: {response}'
        )

    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    homeworks = response.get('homeworks')
    actual_type = type(homeworks).__name__
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API должен быть словарем'
            f'получен тип данных: {actual_type}'
            f'фактическое значение: {repr(homeworks)}'
        )

    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ "homeworks"')

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
    return all((VK_TOKEN, VK_GROUP_ID, VK_USER_ID, PRACTICUM_TOKEN,))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения!')
        sys.exit('Критическая ошибка: отсутствуют токены окружения.')

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()

    unix_24_hours_by_sec = 86400
    current_timestamp = int(time.time()) - unix_24_hours_by_sec
    last_status = ''  

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
 
            # Если работ нет — сразу обновляем время,
            # спим и идем на следующий круг.
            if not homeworks:
                logger.debug('В ответе нет новых домашних работ.')
                current_timestamp = response.get('current_date', current_timestamp)
                time.sleep(RETRY_PERIOD)
                continue

            message = parse_status(homeworks[0])

            if message == last_status:
                logger.debug('Статус домашней работы не изменился.')
                current_timestamp = response.get('current_date', current_timestamp)
                time.sleep(RETRY_PERIOD)
                continue
 
            # Ошибка отправки теперь перехватывается
            # общим внешним блоком except.
            send_message(vk, message)
            logger.debug(f'Сообщение успешно отправлено в VK: {message}')

            last_status = message
            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)

            if not send_message(vk, message):
                logger.error(
                    'Уведомление в VK не было доставлено '
                    '(функция вернула False/None)'
                )

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
