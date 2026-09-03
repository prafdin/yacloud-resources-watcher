"""Thin wrapper around ``yandexcloud.SDK``.

Owns the authenticated SDK instance, remembers the folder every fetcher scopes
its queries to, and hands out per-service gRPC stubs. Kept minimal so tests can
drop in a fake SDK.
"""

import json
from pathlib import Path
from typing import Any, Callable, TypeVar

import yandexcloud

StubT = TypeVar("StubT")


class YcClient:
    def __init__(self, sa_key: dict[str, Any], folder_id: str, sdk: Any | None = None) -> None:
        self.folder_id = folder_id
        self._sdk = sdk or yandexcloud.SDK(service_account_key=sa_key)

    @classmethod
    def from_key_file(cls, path: Path, folder_id: str) -> "YcClient":
        sa_key = json.loads(Path(path).read_text())
        return cls(sa_key=sa_key, folder_id=folder_id)

    def stub(self, stub_ctor: Callable[[Any], StubT]) -> StubT:
        return self._sdk.client(stub_ctor)

    def warm_up(self) -> None:
        from yandex.cloud.resourcemanager.v1.folder_service_pb2_grpc import (
            FolderServiceStub,
        )

        self.stub(FolderServiceStub)
