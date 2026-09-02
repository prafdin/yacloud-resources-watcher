from typing import Any
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings.sources import EnvSettingsSource


class CommaSeparatedListEnvSource(EnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field, field_value, value_is_complex: bool
    ) -> Any:
        if field_name == "telegram_allowed_user_ids" and isinstance(field_value, str):
            return [int(uid.strip()) for uid in field_value.split(",") if uid.strip()]
        return super().prepare_field_value(
            field_name, field, field_value, value_is_complex
        )


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_allowed_user_ids: list[int]

    yc_service_account_key_file: str
    yc_folder_id: str

    schedule_time: str
    schedule_timezone: ZoneInfo

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings,
        file_secret_settings
    ):
        return (
            init_settings,
            CommaSeparatedListEnvSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

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
