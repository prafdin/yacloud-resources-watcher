"""Runtime configuration read from environment variables.

Holds every knob the bot needs and fails loudly at startup when a value is
missing or malformed, so a misconfigured deployment never reaches polling.
"""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    telegram_bot_token: SecretStr
    telegram_allowed_user_ids: str
    telegram_chat_id: int
    yc_sa_key_file: Path
    yc_folder_id: str
    schedule_time: str = "09:00"
    schedule_timezone: str = "UTC"
    log_level: str = "INFO"

    @field_validator("schedule_time")
    @classmethod
    def _valid_hhmm(cls, value):
        hours, sep, minutes = value.partition(":")
        if not sep or not hours.isdigit() or not minutes.isdigit():
            raise ValueError("schedule_time must look like HH:MM")
        if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
            raise ValueError("schedule_time is outside 00:00..23:59")
        return value

    @field_validator("schedule_timezone")
    @classmethod
    def _valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"unknown timezone {value!r}") from error
        return value

    @computed_field
    @property
    def allowed_user_ids(self) -> frozenset[int]:
        return frozenset(
            int(part) for part in self.telegram_allowed_user_ids.split(",") if part.strip()
        )

    @property
    def schedule_hour(self) -> int:
        return int(self.schedule_time.split(":")[0])

    @property
    def schedule_minute(self) -> int:
        return int(self.schedule_time.split(":")[1])

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.schedule_timezone)


@lru_cache
def load_settings() -> Settings:
    return Settings()
