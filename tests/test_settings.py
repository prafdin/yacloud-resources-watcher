"""Tests for configuration loading."""


import pytest
import yaml

from config.settings import Config, SchedulerConfig, load_config, replace_env_vars


def test_replace_env_vars(monkeypatch):
    """Replace ${VAR} placeholders with environment values."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    raw = {
        "telegram": {"bot_token": "${TELEGRAM_BOT_TOKEN}", "allowed_user_id": 1},
        "list": ["${TELEGRAM_BOT_TOKEN}"],
        "plain": "value",
    }
    result = replace_env_vars(raw)
    assert result["telegram"]["bot_token"] == "secret-token"
    assert result["list"] == ["secret-token"]
    assert result["plain"] == "value"


def test_scheduler_time_validation():
    """Reject invalid daily report times."""
    with pytest.raises(ValueError):
        SchedulerConfig(daily_report_time="25:00")
    with pytest.raises(ValueError):
        SchedulerConfig(daily_report_time="abc")
    assert SchedulerConfig(daily_report_time="9:05").daily_report_time == "09:05"


def test_load_config(tmp_path, monkeypatch):
    """Load YAML config and substitute env vars."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-from-env")
    config_file = tmp_path / "config.yaml"
    payload = {
        "telegram": {"bot_token": "${TELEGRAM_BOT_TOKEN}", "allowed_user_id": 42},
        "yandex_cloud": {
            "folder_id": "folder",
            "cloud_id": "cloud",
            "service_account_key_path": "/tmp/key.json",
        },
    }
    config_file.write_text(yaml.safe_dump(payload), encoding="utf-8")
    config = load_config(str(config_file))
    assert isinstance(config, Config)
    assert config.telegram.bot_token == "token-from-env"
    assert config.telegram.allowed_user_id == 42
    assert config.scheduler.daily_report_time == "21:00"
