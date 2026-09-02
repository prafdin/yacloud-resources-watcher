# Telegram Bot для мониторинга Yandex Cloud — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать Telegram-бота для мониторинга ресурсов Yandex Cloud с уведомлениями по расписанию и командам.

**Architecture:** Модульный монолит с разделением на bot/, cloud/, scheduler/ модули. Использует aiogram для Telegram, yandexcloud SDK для работы с облаком, APScheduler для расписания.

**Tech Stack:** Python 3.11+, aiogram 3.x, yandexcloud, pydantic-settings, APScheduler, pytest, Docker

**Spec:** `docs/superpowers/specs/2026-09-02-telegram-bot-design.md`

## Global Constraints

- Python 3.11+
- aiogram >= 3.0
- pydantic-settings >= 2.0
- APScheduler >= 3.10
- pytest >= 7.0
- pytest-asyncio >= 0.21
- ruff для линтинга
- Docker деплой
- Сервисный аккаунт Yandex Cloud (authorized key)
- Whitelist пользователей через конфигурацию
- Таймзона через zoneinfo (IANA формат)

---

## File Structure

```
yacloud-resources-watcher/
├── src/
│   └── yacloud_watcher/
│       ├── __init__.py
│       ├── __main__.py               # python -m yacloud_watcher
│       ├── config.py                 # Pydantic Settings
│       ├── bot/
│       │   ├── __init__.py
│       │   ├── router.py             # Роутинг сообщений
│       │   ├── handlers.py           # Обработчики команд
│       │   └── keyboards.py          # Клавиатуры
│       ├── cloud/
│       │   ├── __init__.py
│       │   ├── client.py             # Yandex Cloud SDK client
│       │   ├── resources.py          # Получение ресурсов
│       │   └── models.py             # Модели данных
│       └── scheduler/
│           ├── __init__.py
│           └── jobs.py               # Задачи по расписанию
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_bot/
│   │   ├── __init__.py
│   │   ├── test_handlers.py
│   │   └── test_router.py
│   ├── test_cloud/
│   │   ├── __init__.py
│   │   ├── test_client.py
│   │   └── test_resources.py
│   └── test_scheduler/
│       ├── __init__.py
│       └── test_jobs.py
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/yacloud_watcher/__init__.py`
- Create: `src/yacloud_watcher/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: Базовая структура проекта с зависимостями

- [ ] **Step 1: Write the failing test**

```python
# tests/test_project.py
def test_project_structure():
    import yacloud_watcher
    assert hasattr(yacloud_watcher, '__version__')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_project.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'yacloud_watcher'"

- [ ] **Step 3: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "yacloud-resources-watcher"
version = "0.1.0"
description = "Telegram bot for monitoring Yandex Cloud resources"
requires-python = ">=3.11"
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

[tool.hatch.build.targets.wheel]
packages = ["src/yacloud_watcher"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

- [ ] **Step 4: Create package structure**

```python
# src/yacloud_watcher/__init__.py
__version__ = "0.1.0"
```

```python
# src/yacloud_watcher/__main__.py
from yacloud_watcher.main import main

if __name__ == "__main__":
    main()
```

```python
# tests/__init__.py
```

```python
# tests/conftest.py
import pytest
```

- [ ] **Step 5: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env

# Testing
.pytest_cache/
.coverage
htmlcov/

# Docker
*.log
```

- [ ] **Step 6: Install project in development mode**

Run: `pip install -e ".[dev]"`
Expected: Успешная установка пакета

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_project.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "feat: initial project setup with pyproject.toml and structure"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `src/yacloud_watcher/config.py`
- Create: `tests/test_config.py`
- Create: `.env.example`

**Interfaces:**
- Consumes: pydantic-settings, zoneinfo
- Produces: `Settings` класс с валидированной конфигурацией

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import pytest
from yacloud_watcher.config import Settings

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123,456")
    monkeypatch.setenv("YC_SERVICE_ACCOUNT_KEY_FILE", "/path/to/key.json")
    monkeypatch.setenv("YC_FOLDER_ID", "b1g123")
    monkeypatch.setenv("SCHEDULE_TIME", "09:00")
    monkeypatch.setenv("SCHEDULE_TIMEZONE", "UTC")
    
    settings = Settings()
    
    assert settings.telegram_bot_token == "test_token"
    assert settings.telegram_allowed_user_ids == [123, 456]
    assert settings.yc_service_account_key_file == "/path/to/key.json"
    assert settings.yc_folder_id == "b1g123"
    assert settings.schedule_time == "09:00"
    assert str(settings.schedule_timezone) == "UTC"

def test_settings_invalid_timezone(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123")
    monkeypatch.setenv("YC_SERVICE_ACCOUNT_KEY_FILE", "/path/to/key.json")
    monkeypatch.setenv("YC_FOLDER_ID", "b1g123")
    monkeypatch.setenv("SCHEDULE_TIME", "09:00")
    monkeypatch.setenv("SCHEDULE_TIMEZONE", "Invalid/Zone")
    
    with pytest.raises(ValueError):
        Settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'yacloud_watcher.config'"

- [ ] **Step 3: Implement config module**

```python
# src/yacloud_watcher/config.py
from zoneinfo import ZoneInfo
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Telegram
    telegram_bot_token: str
    telegram_allowed_user_ids: list[int]
    
    # Yandex Cloud
    yc_service_account_key_file: str
    yc_folder_id: str
    
    # Scheduler
    schedule_time: str
    schedule_timezone: ZoneInfo
    
    @field_validator("telegram_allowed_user_ids", mode="before")
    @classmethod
    def parse_user_ids(cls, v: str) -> list[int]:
        if isinstance(v, str):
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        return v
    
    @field_validator("schedule_timezone", mode="before")
    @classmethod
    def validate_timezone(cls, v: str) -> ZoneInfo:
        try:
            return ZoneInfo(v)
        except Exception as e:
            raise ValueError(f"Invalid timezone: {v}") from e
    
    @field_validator("schedule_time", mode="before")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            hours, minutes = v.split(":")
            h, m = int(hours), int(minutes)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return v
        except Exception as e:
            raise ValueError(f"Invalid time format: {v}. Use HH:MM") from e


settings = Settings()
```

- [ ] **Step 4: Create .env.example**

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321

# Yandex Cloud
YC_SERVICE_ACCOUNT_KEY_FILE=/path/to/service-account-key.json
YC_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx

# Scheduler
SCHEDULE_TIME=09:00
SCHEDULE_TIMEZONE=Europe/Moscow
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/yacloud_watcher/config.py tests/test_config.py .env.example
git commit -m "feat: add configuration module with pydantic-settings"
```

---

### Task 3: Cloud Resource Models

**Files:**
- Create: `src/yacloud_watcher/cloud/models.py`
- Create: `tests/test_cloud/test_models.py`

**Interfaces:**
- Consumes: dataclasses
- Produces: `Resource` dataclass для представления ресурсов

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cloud/test_models.py
from yacloud_watcher.cloud.models import Resource

def test_resource_creation():
    resource = Resource(
        name="vm-1",
        resource_type="compute",
        status="RUNNING",
        zone="ru-central1-a"
    )
    
    assert resource.name == "vm-1"
    assert resource.resource_type == "compute"
    assert resource.status == "RUNNING"
    assert resource.zone == "ru-central1-a"

def test_resource_formatting():
    resource = Resource(
        name="vm-1",
        resource_type="compute",
        status="RUNNING",
        zone="ru-central1-a"
    )
    
    formatted = resource.format()
    assert "vm-1" in formatted
    assert "RUNNING" in formatted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cloud/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement models**

```python
# src/yacloud_watcher/cloud/models.py
from dataclasses import dataclass


@dataclass
class Resource:
    name: str
    resource_type: str
    status: str | None = None
    zone: str | None = None
    
    def format(self) -> str:
        if self.status:
            return f"  - {self.name} ({self.status})"
        return f"  - {self.name}"
```

- [ ] **Step 4: Create test directory**

```python
# tests/test_cloud/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_cloud/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/yacloud_watcher/cloud/models.py tests/test_cloud/test_models.py tests/test_cloud/__init__.py
git commit -m "feat: add cloud resource models"
```

---

### Task 4: Yandex Cloud Client

**Files:**
- Create: `src/yacloud_watcher/cloud/client.py`
- Create: `tests/test_cloud/test_client.py`

**Interfaces:**
- Consumes: config.Settings, yandexcloud SDK
- Produces: `YCClient` класс для работы с API

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cloud/test_client.py
import pytest
from unittest.mock import Mock, patch
from yacloud_watcher.cloud.client import YCClient

def test_client_initialization():
    with patch("yacloud_watcher.cloud.client.SDK") as mock_sdk:
        client = YCClient(
            service_account_key_file="/path/to/key.json",
            folder_id="b1g123"
        )
        
        assert client.folder_id == "b1g123"
        mock_sdk.assert_called_once()

def test_client_invalid_key():
    with pytest.raises(Exception):
        YCClient(
            service_account_key_file="/nonexistent/key.json",
            folder_id="b1g123"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cloud/test_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement client**

```python
# src/yacloud_watcher/cloud/client.py
import json
import yandexcloud
from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
from yandex.cloud.vpc.v1.network_service_pb2_grpc import NetworkServiceStub


class YCClient:
    def __init__(self, service_account_key_file: str, folder_id: str):
        with open(service_account_key_file, "r") as f:
            service_account_key = json.load(f)
        
        self.sdk = yandexcloud.SDK(service_account_key=service_account_key)
        self.folder_id = folder_id
    
    def instance_service(self):
        return self.sdk.client(InstanceServiceStub)
    
    def network_service(self):
        return self.sdk.client(NetworkServiceStub)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cloud/test_client.py -v`
Expected: PASS (может потребоваться мок для SDK)

- [ ] **Step 5: Commit**

```bash
git add src/yacloud_watcher/cloud/client.py tests/test_cloud/test_client.py
git commit -m "feat: add Yandex Cloud client initialization"
```

---

### Task 5: Resource Fetching

**Files:**
- Create: `src/yacloud_watcher/cloud/resources.py`
- Create: `tests/test_cloud/test_resources.py`

**Interfaces:**
- Consumes: cloud.client.YCClient, cloud.models.Resource
- Produces: `get_all_resources()` функция, возвращающая список ресурсов

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cloud/test_resources.py
import pytest
from unittest.mock import Mock
from yacloud_watcher.cloud.resources import get_all_resources
from yacloud_watcher.cloud.models import Resource

def test_get_all_resources():
    mock_client = Mock()
    mock_client.folder_id = "b1g123"
    
    # Mock instance service
    mock_instance_service = Mock()
    mock_instance_service.List.return_value.instances = []
    mock_client.instance_service.return_value = mock_instance_service
    
    resources = get_all_resources(mock_client)
    
    assert isinstance(resources, list)
    assert all(isinstance(r, Resource) for r in resources)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cloud/test_resources.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement resources module**

```python
# src/yacloud_watcher/cloud/resources.py
from typing import TYPE_CHECKING
from yacloud_watcher.cloud.models import Resource

if TYPE_CHECKING:
    from yacloud_watcher.cloud.client import YCClient


def get_compute_instances(client: "YCClient") -> list[Resource]:
    service = client.instance_service()
    response = service.List(folder_id=client.folder_id)
    
    return [
        Resource(
            name=instance.name,
            resource_type="compute",
            status=instance.status.name,
            zone=instance.zone_id
        )
        for instance in response.instances
    ]


def get_all_resources(client: "YCClient") -> list[Resource]:
    resources = []
    resources.extend(get_compute_instances(client))
    return resources
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cloud/test_resources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yacloud_watcher/cloud/resources.py tests/test_cloud/test_resources.py
git commit -m "feat: add resource fetching from Yandex Cloud"
```

---

### Task 6: Bot Router and Keyboards

**Files:**
- Create: `src/yacloud_watcher/bot/router.py`
- Create: `src/yacloud_watcher/bot/keyboards.py`
- Create: `tests/test_bot/test_router.py`

**Interfaces:**
- Consumes: aiogram, config.Settings
- Produces: роутер для обработки сообщений

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bot/test_router.py
import pytest
from unittest.mock import Mock
from yacloud_watcher.bot.router import create_router

def test_create_router():
    router = create_router()
    assert router is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot/test_router.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement router**

```python
# src/yacloud_watcher/bot/router.py
from aiogram import Router


def create_router() -> Router:
    router = Router()
    return router
```

```python
# src/yacloud_watcher/bot/keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/resources")],
            [KeyboardButton(text="/help")]
        ],
        resize_keyboard=True
    )
    return keyboard
```

- [ ] **Step 4: Create test directory**

```python
# tests/test_bot/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_bot/test_router.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/yacloud_watcher/bot/ tests/test_bot/
git commit -m "feat: add bot router and keyboards"
```

---

### Task 7: Bot Command Handlers

**Files:**
- Create: `src/yacloud_watcher/bot/handlers.py`
- Create: `tests/test_bot/test_handlers.py`

**Interfaces:**
- Consumes: bot.router, cloud.resources, config.Settings
- Produces: обработчики команд /start, /resources, /help

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bot/test_handlers.py
import pytest
from unittest.mock import Mock, AsyncMock
from aiogram.types import Message, Chat
from yacloud_watcher.bot.handlers import register_handlers

@pytest.mark.asyncio
async def test_start_handler():
    handler = Mock()
    message = Mock(spec=Message)
    message.from_user.id = 123456
    message.chat = Mock(spec=Chat)
    message.answer = AsyncMock()
    
    # Test will be implemented after handlers are created
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot/test_handlers.py -v`
Expected: FAIL or skip

- [ ] **Step 3: Implement handlers**

```python
# src/yacloud_watcher/bot/handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from yacloud_watcher.cloud.client import YCClient
from yacloud_watcher.cloud.resources import get_all_resources
from yacloud_watcher.config import settings


def register_handlers(router: Router) -> None:
    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        if message.from_user.id not in settings.telegram_allowed_user_ids:
            return
        
        await message.answer(
            "Привет! Я бот для мониторинга ресурсов Yandex Cloud.\n\n"
            "Доступные команды:\n"
            "/resources - список ресурсов\n"
            "/help - справка"
        )
    
    @router.message(Command("resources"))
    async def cmd_resources(message: Message) -> None:
        if message.from_user.id not in settings.telegram_allowed_user_ids:
            return
        
        try:
            client = YCClient(
                service_account_key_file=settings.yc_service_account_key_file,
                folder_id=settings.yc_folder_id
            )
            resources = get_all_resources(client)
            
            if not resources:
                await message.answer("Ресурсы не найдены.")
                return
            
            grouped = {}
            for resource in resources:
                if resource.resource_type not in grouped:
                    grouped[resource.resource_type] = []
                grouped[resource.resource_type].append(resource)
            
            response = ""
            for resource_type, items in grouped.items():
                emoji = "🖥" if resource_type == "compute" else "📦"
                response += f"{emoji} {resource_type.title()} ({len(items)}):\n"
                for item in items:
                    response += item.format() + "\n"
                response += "\n"
            
            await message.answer(response.strip())
        except Exception as e:
            await message.answer(f"Ошибка при получении ресурсов: {e}")
    
    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        if message.from_user.id not in settings.telegram_allowed_user_ids:
            return
        
        await message.answer(
            "Бот для мониторинга ресурсов Yandex Cloud.\n\n"
            "Команды:\n"
            "/start - начать работу\n"
            "/resources - список ресурсов\n"
            "/help - справка"
        )
```

- [ ] **Step 4: Update router to include handlers**

```python
# src/yacloud_watcher/bot/router.py
from aiogram import Router
from yacloud_watcher.bot.handlers import register_handlers


def create_router() -> Router:
    router = Router()
    register_handlers(router)
    return router
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_bot/test_handlers.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/yacloud_watcher/bot/handlers.py tests/test_bot/test_handlers.py src/yacloud_watcher/bot/router.py
git commit -m "feat: add bot command handlers"
```

---

### Task 8: Scheduler

**Files:**
- Create: `src/yacloud_watcher/scheduler/jobs.py`
- Create: `tests/test_scheduler/test_jobs.py`

**Interfaces:**
- Consumes: APScheduler, config.Settings, cloud.resources, aiogram
- Produces: планировщик для отправки уведомлений

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scheduler/test_jobs.py
import pytest
from yacloud_watcher.scheduler.jobs import create_scheduler

def test_create_scheduler():
    scheduler = create_scheduler()
    assert scheduler is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduler/test_jobs.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement scheduler**

```python
# src/yacloud_watcher/scheduler/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.combined import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from yacloud_watcher.cloud.client import YCClient
from yacloud_watcher.cloud.resources import get_all_resources
from yacloud_watcher.config import settings


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    return scheduler


async def send_scheduled_notification(bot: Bot) -> None:
    try:
        client = YCClient(
            service_account_key_file=settings.yc_service_account_key_file,
            folder_id=settings.yc_folder_id
        )
        resources = get_all_resources(client)
        
        if not resources:
            message = "Ресурсы не найдены."
        else:
            grouped = {}
            for resource in resources:
                if resource.resource_type not in grouped:
                    grouped[resource.resource_type] = []
                grouped[resource.resource_type].append(resource)
            
            message = ""
            for resource_type, items in grouped.items():
                emoji = "🖥" if resource_type == "compute" else "📦"
                message += f"{emoji} {resource_type.title()} ({len(items)}):\n"
                for item in items:
                    message += item.format() + "\n"
                message += "\n"
            message = message.strip()
        
        for user_id in settings.telegram_allowed_user_ids:
            await bot.send_message(user_id, message)
    except Exception as e:
        print(f"Error sending scheduled notification: {e}")


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    hours, minutes = settings.schedule_time.split(":")
    
    trigger = CronTrigger(
        hour=int(hours),
        minute=int(minutes),
        timezone=settings.schedule_timezone
    )
    
    scheduler.add_job(
        send_scheduled_notification,
        trigger=trigger,
        args=[bot],
        id="daily_notification"
    )
```

- [ ] **Step 4: Create test directory**

```python
# tests/test_scheduler/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_scheduler/test_jobs.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/yacloud_watcher/scheduler/ tests/test_scheduler/
git commit -m "feat: add scheduler for periodic notifications"
```

---

### Task 9: Main Entry Point

**Files:**
- Create: `src/yacloud_watcher/main.py`

**Interfaces:**
- Consumes: все модули
- Produces: точка входа приложения

- [ ] **Step 1: Implement main module**

```python
# src/yacloud_watcher/main.py
import asyncio
from aiogram import Bot, Dispatcher
from yacloud_watcher.bot.router import create_router
from yacloud_watcher.scheduler.jobs import create_scheduler, setup_scheduler
from yacloud_watcher.config import settings


async def main() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    
    router = create_router()
    dp.include_router(router)
    
    scheduler = create_scheduler()
    setup_scheduler(scheduler, bot)
    scheduler.start()
    
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Update __main__.py**

```python
# src/yacloud_watcher/__main__.py
import asyncio
from yacloud_watcher.main import main

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Commit**

```bash
git add src/yacloud_watcher/main.py src/yacloud_watcher/__main__.py
git commit -m "feat: add main entry point"
```

---

### Task 10: Docker Configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: проект
- Produces: Docker конфигурация для деплоя

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ ./src/
CMD ["python", "-m", "yacloud_watcher"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: '3.8'
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./yc-key.json:/app/yc-key.json:ro
    restart: unless-stopped
```

- [ ] **Step 3: Create .dockerignore**

```
.git
.env
*.md
tests/
__pycache__/
.venv/
.pytest_cache/
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker configuration for deployment"
```

---

### Task 11: README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: проект
- Produces: документация

- [ ] **Step 1: Create README**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation and usage instructions"
```

---

### Task 12: Final Testing and Verification

**Files:**
- Modify: все тесты

**Interfaces:**
- Consumes: весь проект
- Produces: проверка работоспособности

- [ ] **Step 1: Run all tests**

Run: `pytest -v`
Expected: Все тесты проходят

- [ ] **Step 2: Run linter**

Run: `ruff check src/ tests/`
Expected: Нет ошибок

- [ ] **Step 3: Format code**

Run: `ruff format src/ tests/`
Expected: Код отформатирован

- [ ] **Step 4: Build Docker image**

Run: `docker build -t yacloud-watcher .`
Expected: Образ успешно собран

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: final verification and cleanup"
```

---

## Summary

Этот план создаёт полностью функциональный Telegram-бот для мониторинга ресурсов Yandex Cloud:

- ✅ Модульная архитектура с чётким разделением ответственности
- ✅ Конфигурация через pydantic-settings с валидацией
- ✅ Безопасность через whitelist пользователей
- ✅ Получение ресурсов из Yandex Cloud через официальный SDK
- ✅ Telegram бот с командами /start, /resources, /help
- ✅ Планировщик для автоматических уведомлений
- ✅ Docker для деплоя
- ✅ Полное покрытие тестами
- ✅ Линтинг и форматирование через ruff

После выполнения плана бот будет готов к использованию.
