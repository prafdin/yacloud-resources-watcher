"""Tests for Yandex Cloud HTTP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from yandex_cloud.client import YCClient


class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status = status
        self._payload = payload or {}

    async def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
            )

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _client(mock_config) -> YCClient:
    client = YCClient(mock_config.yandex_cloud)
    client.session = MagicMock()
    client.auth.get_iam_token = AsyncMock(return_value="iam-token")
    client.auth.refresh_token = AsyncMock(return_value="iam-token")
    client.auth._iam_token = "iam-token"
    return client


async def test_get_compute_instances_success(mock_config):
    """Test successful compute instances request."""
    client = _client(mock_config)
    client.session.request.return_value = FakeResponse(200, {"instances": [{"id": "1"}]})
    result = await client.get_compute_instances("b1g_test")
    assert result["instances"][0]["id"] == "1"


async def test_404_returns_empty(mock_config):
    """Test 404 returns an empty dict."""
    client = _client(mock_config)
    client.session.request.return_value = FakeResponse(404)
    assert await client.get_compute_instances("b1g_test") == {}


async def test_403_returns_empty(mock_config):
    """Test 403 returns an empty dict."""
    client = _client(mock_config)
    client.session.request.return_value = FakeResponse(403)
    assert await client.get_networks("b1g_test") == {}


async def test_401_refreshes_token(mock_config):
    """Test 401 triggers token refresh and retry."""
    client = _client(mock_config)
    client.session.request.side_effect = [
        FakeResponse(401),
        FakeResponse(200, {"instances": []}),
    ]
    result = await client.get_compute_instances("b1g_test")
    assert result == {"instances": []}
    client.auth.refresh_token.assert_awaited()


async def test_retry_on_server_error(mock_config):
    """Test 500 retries then succeeds."""
    client = _client(mock_config)
    client.session.request.side_effect = [
        FakeResponse(500),
        FakeResponse(200, {"buckets": []}),
    ]
    with patch("yandex_cloud.client.asyncio.sleep", AsyncMock()):
        result = await client.get_buckets("b1g_test")
    assert result == {"buckets": []}


async def test_network_error_returns_empty(mock_config):
    """Test connection errors are retried then swallowed."""
    client = _client(mock_config)
    client.session.request.side_effect = aiohttp.ClientError("down")
    with patch("yandex_cloud.client.asyncio.sleep", AsyncMock()):
        result = await client.get_functions("b1g_test")
    assert result == {}


async def test_context_manager(mock_config):
    """Test session lifecycle."""
    client = YCClient(mock_config.yandex_cloud)
    with patch("yandex_cloud.client.aiohttp.ClientSession") as session_cls:
        session = AsyncMock()
        session_cls.return_value = session
        async with client as opened:
            assert opened.session is session
        session.close.assert_awaited()


def test_headers_property(mock_config):
    """Test cached authorization header."""
    client = YCClient(mock_config.yandex_cloud)
    client.auth._iam_token = "abc"
    assert client.headers["Authorization"] == "Bearer abc"


async def test_request_requires_context(mock_config):
    """Test requests fail without an open session."""
    client = YCClient(mock_config.yandex_cloud)
    with pytest.raises(RuntimeError):
        await client.get_compute_instances("b1g_test")
