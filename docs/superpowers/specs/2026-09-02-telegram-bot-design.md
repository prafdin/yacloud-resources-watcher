# Telegram Bot для мониторинга ресурсов Yandex Cloud

## Обзор

Telegram-бот для мониторинга используемых ресурсов в Yandex Cloud. Отправляет уведомления по расписанию и по запросу пользователя.

## Технологии

- **Python 3.11+**
- **aiogram 3.x** — асинхронный Telegram фреймворк
- **yandexcloud** — официальный Yandex Cloud SDK
- **pydantic-settings** — валидация конфигурации
- **APScheduler 3.10+** — планировщик для расписания
- **pytest** — тестирование
- **Ruff** — линтер и форматтер
- **Docker** — деплой

## Архитектура

Модульный монолит с разделением на модули:
- `bot/` — Telegram бот (aiogram)
- `cloud/` — работа с Yandex Cloud SDK
- `scheduler/` — планировщик уведомлений

## Структура проекта

```
yacloud-resources-watcher/
├── src/
│   └── yacloud_watcher/
│       ├── __init__.py
│       ├── __main__.py
│       ├── bot/
│       │   ├── __init__.py
│       │   ├── handlers.py
│       │   ├── keyboards.py
│       │   └── router.py
│       ├── cloud/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── resources.py
│       │   └── models.py
│       ├── scheduler/
│       │   ├── __init__.py
│       │   └── jobs.py
│       └── config.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_bot/
│   ├── test_cloud/
│   └── test_scheduler/
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие, список доступных команд |
| `/resources` | Получить текущий список ресурсов по типам |
| `/help` | Справка |

## Безопасность

- Бот отвечает только пользователям из whitelist (`TELEGRAM_ALLOWED_USER_IDS`)
- Остальные пользователи игнорируются, попытка логируется
- Сервисный ключ Yandex Cloud хранится в отдельном файле, путь в конфигурации

## Конфигурация

```env
# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321

# Yandex Cloud
YC_SERVICE_ACCOUNT_KEY_FILE=/path/to/key.json
YC_FOLDER_ID=b1g...

# Scheduler
SCHEDULE_TIME=09:00
SCHEDULE_TIMEZONE=Europe/Moscow
```

- `TELEGRAM_ALLOWED_USER_IDS` — whitelist Telegram user IDs (через запятую)
- `SCHEDULE_TIME` — время ежедневной рассылки в формате HH:MM
- `SCHEDULE_TIMEZONE` — таймзона в формате IANA (например, Europe/Moscow, UTC)

Используется `pydantic-settings` для валидации и `zoneinfo` для работы с таймзонами.

## Работа с Yandex Cloud

Отслеживаемые ресурсы:
- **Compute Cloud**: виртуальные машины, диски, снапшоты, образы
- **Object Storage**: бакеты
- **Managed Services**: базы данных (PostgreSQL, MySQL, MongoDB, ClickHouse, Redis)
- **VPC**: сети, подсети, security groups, публичные IP-адреса
- **Kubernetes**: кластеры
- **Load Balancer**: балансировщики

Формат вывода (группировка по типу сервиса):
```
🖥 Compute Cloud (3):
  - vm-1 (RUNNING)
  - vm-2 (STOPPED)
  - vm-3 (RUNNING)

💾 Object Storage (2):
  - bucket-1
  - bucket-2
```

## Обработка ошибок

- **Yandex Cloud API недоступен**: логирование ошибки, пользователю отправляется сообщение "Не удалось получить ресурсы. Попробуйте позже."
- **Невалидный сервисный ключ**: бот не запускается, ошибка выводится в консоль при старте
- **Пользователь не в whitelist**: команда игнорируется, логирование попытки доступа
- **Сетевые ошибки**: retry с exponential backoff (3 попытки)

## Тестирование

- **pytest** для unit-тестов
- **pytest-asyncio** для асинхронных тестов
- **Моккирование**: `unittest.mock` для Yandex Cloud API и Telegram API
- Покрытие: логика получения ресурсов, обработка команд, фильтрация пользователей

## Зависимости

```toml
[project]
dependencies = [
    "aiogram>=3.0",
    "yandexcloud",
    "pydantic-settings>=2.0",
    "apscheduler>=3.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff",
]
```

## Деплой (Docker)

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ ./src/
CMD ["python", "-m", "yacloud_watcher"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./yc-key.json:/app/yc-key.json:ro
    restart: unless-stopped
```

### Запуск

```bash
docker-compose up -d
```

### .dockerignore

```
.git
.env
*.md
tests/
__pycache__/
.venv/
```
