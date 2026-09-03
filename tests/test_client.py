import json

import yandexcloud

from yc_watcher.yc.client import YcClient


class FakeSdk:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.requested = []

    def client(self, stub_ctor):
        self.requested.append(stub_ctor)
        return f"stub::{stub_ctor}"


def test_from_key_file_passes_parsed_key_to_the_sdk(tmp_path, monkeypatch):
    created = {}
    monkeypatch.setattr(
        yandexcloud, "SDK", lambda **kwargs: created.setdefault("sdk", FakeSdk(**kwargs))
    )
    key_path = tmp_path / "sa-key.json"
    key_path.write_text(json.dumps({"id": "key1", "service_account_id": "sa1"}))

    YcClient.from_key_file(key_path, "b1gfolder")

    assert created["sdk"].kwargs == {
        "service_account_key": {"id": "key1", "service_account_id": "sa1"}
    }


def test_from_key_file_keeps_the_folder_id(tmp_path, monkeypatch):
    monkeypatch.setattr(yandexcloud, "SDK", lambda **kwargs: FakeSdk(**kwargs))
    key_path = tmp_path / "sa-key.json"
    key_path.write_text("{}")

    client = YcClient.from_key_file(key_path, "b1gfolder")

    assert client.folder_id == "b1gfolder"


def test_stub_is_delegated_to_the_sdk():
    sdk = FakeSdk()
    client = YcClient(sa_key={}, folder_id="b1g", sdk=sdk)

    result = client.stub("InstanceServiceStub")

    assert result == "stub::InstanceServiceStub"
    assert sdk.requested == ["InstanceServiceStub"]
