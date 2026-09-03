import pytest
from pydantic import ValidationError

from yc_watcher.config import Settings

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "123:abc",
    "TELEGRAM_ALLOWED_USER_IDS": "111, 222 ,333",
    "TELEGRAM_CHAT_ID": "111",
    "YC_SA_KEY_FILE": "/secrets/sa-key.json",
    "YC_FOLDER_ID": "b1gfolder",
    "SCHEDULE_TIME": "09:30",
    "SCHEDULE_TIMEZONE": "Europe/Amsterdam",
    "LOG_LEVEL": "INFO",
}


def _settings(env, **overrides):
    merged = {**env, **overrides}
    return Settings(_env_file=None, **{k.lower(): v for k, v in merged.items()})


def test_allowed_user_ids_parses_csv_into_frozenset_of_ints():
    settings = _settings(BASE_ENV)
    assert settings.allowed_user_ids == frozenset({111, 222, 333})


def test_schedule_time_splits_into_hour_and_minute():
    settings = _settings(BASE_ENV)
    assert (settings.schedule_hour, settings.schedule_minute) == (9, 30)


def test_bot_token_is_not_exposed_in_repr():
    settings = _settings(BASE_ENV)
    assert "123:abc" not in repr(settings)


def test_invalid_schedule_time_is_rejected():
    with pytest.raises(ValidationError):
        _settings(BASE_ENV, SCHEDULE_TIME="9h30")


def test_out_of_range_schedule_time_is_rejected():
    with pytest.raises(ValidationError):
        _settings(BASE_ENV, SCHEDULE_TIME="24:00")


def test_unknown_timezone_is_rejected():
    with pytest.raises(ValidationError):
        _settings(BASE_ENV, SCHEDULE_TIMEZONE="Mars/Olympus")


def test_missing_required_field_is_rejected():
    env = {k: v for k, v in BASE_ENV.items() if k != "YC_FOLDER_ID"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{k.lower(): v for k, v in env.items()})


def test_non_integer_chat_id_is_rejected():
    with pytest.raises(ValidationError):
        _settings(BASE_ENV, TELEGRAM_CHAT_ID="not-a-number")
