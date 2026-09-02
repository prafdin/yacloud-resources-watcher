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
