"""Service Account authentication and IAM token management."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import jwt

logger = logging.getLogger(__name__)

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
JWT_TTL_SECONDS = 3600
IAM_TOKEN_TTL = timedelta(hours=12)
REFRESH_MARGIN = timedelta(hours=1)


def load_sa_key(key_path: str) -> dict:
    """Load a Service Account authorized key from JSON file."""
    path = Path(key_path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def generate_jwt_token(sa_key: dict) -> str:
    """Generate a PS256 JWT for IAM token exchange."""
    now = int(time.time())
    payload = {
        "iss": sa_key["service_account_id"],
        "aud": IAM_URL,
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }
    headers = {"kid": sa_key["id"], "typ": "JWT"}
    return jwt.encode(
        payload,
        sa_key["private_key"],
        algorithm="PS256",
        headers=headers,
    )


class IAMAuth:
    """Create, cache and refresh Yandex Cloud IAM tokens."""

    def __init__(self, key_path: str) -> None:
        self.key_path = key_path
        self._sa_key: dict | None = None
        self._iam_token: str | None = None
        self._expires_at: datetime | None = None

    def load_key(self) -> dict:
        """Load and cache the service account key."""
        if self._sa_key is None:
            self._sa_key = load_sa_key(self.key_path)
        return self._sa_key

    def generate_jwt(self) -> str:
        """Generate a JWT signed with the service account key."""
        return generate_jwt_token(self.load_key())

    def is_token_valid(self) -> bool:
        """Return True if a cached token exists and is not near expiry."""
        if not self._iam_token or self._expires_at is None:
            return False
        return datetime.now(timezone.utc) < (self._expires_at - REFRESH_MARGIN)

    async def get_iam_token(self) -> str:
        """Return a cached IAM token or refresh it."""
        if self.is_token_valid() and self._iam_token:
            return self._iam_token
        return await self.refresh_token()

    async def refresh_token(self) -> str:
        """Exchange JWT for a new IAM token and cache it."""
        jwt_token = self.generate_jwt()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    IAM_URL,
                    json={"jwt": jwt_token},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            logger.error("Failed to exchange JWT for IAM token: %s", exc)
            raise

        token = data.get("iamToken")
        if not token:
            raise ValueError("IAM API response does not contain iamToken")

        self._iam_token = token
        expires_at = data.get("expiresAt")
        if expires_at:
            self._expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        else:
            self._expires_at = datetime.now(timezone.utc) + IAM_TOKEN_TTL
        logger.info("IAM token refreshed, expires at %s", self._expires_at)
        return token


async def generate_iam_token(key_path: str) -> str:
    """Generate an IAM token from a service account key path."""
    auth = IAMAuth(key_path)
    return await auth.get_iam_token()
