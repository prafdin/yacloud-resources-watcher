import pytest
import yandexcloud


@pytest.fixture(autouse=True)
def _forbid_real_sdk(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("test constructed a real yandexcloud.SDK; patch it")

    monkeypatch.setattr(yandexcloud, "SDK", _boom)
