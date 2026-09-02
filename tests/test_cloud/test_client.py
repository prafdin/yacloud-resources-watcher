import json
from unittest.mock import mock_open, patch

import pytest
from yacloud_watcher.cloud.client import YCClient


def test_client_initialization():
    key_data = {"id": "test-key"}
    with (
        patch("builtins.open", mock_open(read_data=json.dumps(key_data))),
        patch("yacloud_watcher.cloud.client.SDK") as mock_sdk,
    ):
        client = YCClient(
            service_account_key_file="/path/to/key.json", folder_id="b1g123"
        )

        assert client.folder_id == "b1g123"
        mock_sdk.assert_called_once_with(service_account_key=key_data)


def test_client_invalid_key():
    with pytest.raises(Exception):
        YCClient(service_account_key_file="/nonexistent/key.json", folder_id="b1g123")
