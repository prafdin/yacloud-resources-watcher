# Yandex Cloud Resources Watcher

Telegram-бот для мониторинга ресурсов в Yandex Cloud.

## Возможности

- Получение списка ресурсов по команде `/resources`
- Автоматические уведомления по расписанию
- Поддержка всех основных сервисов Yandex Cloud
- Безопасность: whitelist пользователей

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd yacloud-resources-watcher
```

2. Установите зависимости:
```bash
pip install -e ".[dev]"
```

3. Создайте сервисный аккаунт в Yandex Cloud и скачайте ключ:
```bash
# Сохраните ключ в файл yc-key.json
```

4. Создайте `.env` файл на основе `.env.example`:
```bash
cp .env.example .env
# Отредактируйте .env и укажите ваши значения
```

## Запуск

### Локально

```bash
python -m yacloud_watcher
```

### Docker

```bash
docker-compose up -d
```

## Конфигурация

Создайте файл `.env` со следующими переменными:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321
YC_SERVICE_ACCOUNT_KEY_FILE=/path/to/key.json
YC_FOLDER_ID=b1gxxxxxxxxx
SCHEDULE_TIME=09:00
SCHEDULE_TIMEZONE=Europe/Moscow
```

## Команды бота

- `/start` - начать работу
- `/resources` - список ресурсов
- `/help` - справка

## Разработка

### Запуск тестов

```bash
pytest
```

### Линтинг

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Лицензия

MIT
