"""Configuration loading and validation."""

from __future__ import annotations

import os
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class TelegramConfig(BaseModel):
    """Telegram bot settings."""

    bot_token: str
    allowed_user_id: int


class SchedulerConfig(BaseModel):
    """Scheduler settings."""

    daily_report_time: str = "21:00"
    timezone: str = "Europe/Moscow"
    reminder_hours: int = 2

    @field_validator("daily_report_time")
    @classmethod
    def validate_daily_report_time(cls, value: str) -> str:
        """Validate HH:MM 24-hour time."""
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("daily_report_time must be in HH:MM format")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("daily_report_time must be a valid 24-hour time")
        return f"{hour:02d}:{minute:02d}"

    @field_validator("reminder_hours")
    @classmethod
    def validate_reminder_hours(cls, value: int) -> int:
        """Ensure reminder delay is positive."""
        if value < 1:
            raise ValueError("reminder_hours must be >= 1")
        return value


class YandexCloudConfig(BaseModel):
    """Yandex Cloud connection settings."""

    folder_id: str
    cloud_id: str
    service_account_key_path: str


class StorageConfig(BaseModel):
    """Local storage settings."""

    database_path: str = "/app/data/bot.db"


class LoggingConfig(BaseModel):
    """Logging settings."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        """Normalize and validate log level."""
        level = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"logging.level must be one of {sorted(allowed)}")
        return level


class Config(BaseModel):
    """Root application configuration."""

    telegram: TelegramConfig
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    yandex_cloud: YandexCloudConfig
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def replace_env_vars(obj: Any) -> Any:
    """Replace ${VAR} placeholders with environment variables."""
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        var_name = obj[2:-1]
        return os.getenv(var_name, "")
    if isinstance(obj, dict):
        return {key: replace_env_vars(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [replace_env_vars(item) for item in obj]
    return obj


def _resolve_config_path(config_path: str | None) -> str:
    if config_path:
        return config_path
    env_path = os.getenv("CONFIG_PATH")
    if env_path:
        return env_path
    for candidate in ("config/config.yaml", "config.yaml"):
        if os.path.isfile(candidate):
            return candidate
    return "config/config.yaml"


def load_config(config_path: str | None = None) -> Config:
    """Load and validate configuration from YAML and environment."""
    load_dotenv()
    path = _resolve_config_path(config_path)
    with open(path, "r", encoding="utf-8") as handle:
        raw_config = yaml.safe_load(handle) or {}
    raw_config = replace_env_vars(raw_config)
    return Config(**raw_config)
