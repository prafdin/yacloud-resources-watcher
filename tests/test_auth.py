"""Tests for Yandex Cloud authentication."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from aiohttp import ClientError
from aioresponses import aioresponses

from yandex_cloud.auth import IAM_URL, IAMAuth, generate_jwt_token, load_sa_key


def test_generate_jwt_token(sample_sa_key):
    """Test JWT token generation with SA key."""
    token = generate_jwt_token(sample_sa_key)
    decoded = jwt.decode(
        token,
        sample_sa_key["public_key"],
        algorithms=["PS256"],
        audience=IAM_URL,
    )
    header = jwt.get_unverified_header(token)
    assert header["kid"] == sample_sa_key["id"]
    assert header["alg"] == "PS256"
    assert decoded["iss"] == sample_sa_key["service_account_id"]
    assert decoded["aud"] == IAM_URL
    assert decoded["exp"] - decoded["iat"] == 3600


def test_load_sa_key(sa_key_path, sample_sa_key):
    """Test loading SA key from disk."""
    loaded = load_sa_key(sa_key_path)
    assert loaded["id"] == sample_sa_key["id"]
    assert loaded["service_account_id"] == sample_sa_key["service_account_id"]


async def test_exchange_jwt_for_iam_token(sa_key_path):
    """Test JWT to IAM token exchange."""
    auth = IAMAuth(sa_key_path)
    expires = (datetime.now(timezone.utc) + timedelta(hours=12)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    with aioresponses() as mocked:
        mocked.post(IAM_URL, payload={"iamToken": "iam-test-token", "expiresAt": expires})
        token = await auth.refresh_token()
    assert token == "iam-test-token"
    assert auth._iam_token == "iam-test-token"
    assert auth._expires_at is not None


async def test_cache_iam_token(sa_key_path):
    """Test IAM token caching."""
    auth = IAMAuth(sa_key_path)
    auth._iam_token = "cached-token"
    auth._expires_at = datetime.now(timezone.utc) + timedelta(hours=11)
    with patch.object(auth, "refresh_token", new_callable=AsyncMock) as refresh:
        token = await auth.get_iam_token()
    assert token == "cached-token"
    refresh.assert_not_called()


async def test_refresh_expired_token(sa_key_path):
    """Test token refresh before expiry."""
    auth = IAMAuth(sa_key_path)
    auth._iam_token = "old-token"
    auth._expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    with aioresponses() as mocked:
        mocked.post(IAM_URL, payload={"iamToken": "new-token"})
        token = await auth.get_iam_token()
    assert token == "new-token"
    assert auth._iam_token == "new-token"


async def test_handle_auth_error(sa_key_path):
    """Test handling of authentication errors."""
    auth = IAMAuth(sa_key_path)
    with aioresponses() as mocked:
        mocked.post(IAM_URL, exception=ClientError("boom"))
        with pytest.raises(ClientError):
            await auth.refresh_token()


async def test_handle_auth_http_error(sa_key_path):
    """Test handling of non-200 IAM responses."""
    auth = IAMAuth(sa_key_path)
    with aioresponses() as mocked:
        mocked.post(IAM_URL, status=401, payload={"error": "unauthorized"})
        with pytest.raises(Exception):
            await auth.refresh_token()


def test_is_token_valid_without_cache(sa_key_path):
    """Token is invalid when cache is empty."""
    auth = IAMAuth(sa_key_path)
    assert auth.is_token_valid() is False
