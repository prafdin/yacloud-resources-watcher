from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from yacloud_watcher.cloud.client import YCClient
from yacloud_watcher.cloud.resources import get_all_resources
from yacloud_watcher.config import Settings


def register_handlers(router: Router, settings: Settings) -> None:
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
                folder_id=settings.yc_folder_id,
            )
            resources = get_all_resources(client)

            if not resources:
                await message.answer("Ресурсы не найдены.")
                return

            grouped: dict[str, list] = {}
            for resource in resources:
                grouped.setdefault(resource.resource_type, []).append(resource)

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
