"""HTTP client for Yandex Cloud REST APIs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from config.settings import YandexCloudConfig
from yandex_cloud.auth import IAMAuth

logger = logging.getLogger(__name__)

COMPUTE_INSTANCES_URL = "https://compute.api.cloud.yandex.net/compute/v1/instances"
POSTGRESQL_CLUSTERS_URL = (
    "https://mdb.api.cloud.yandex.net/managed-postgresql/v1/clusters"
)
MYSQL_CLUSTERS_URL = "https://mdb.api.cloud.yandex.net/managed-mysql/v1/clusters"
MONGODB_CLUSTERS_URL = "https://mdb.api.cloud.yandex.net/managed-mongodb/v1/clusters"
CLICKHOUSE_CLUSTERS_URL = (
    "https://mdb.api.cloud.yandex.net/managed-clickhouse/v1/clusters"
)
BUCKETS_URL = "https://storage.api.cloud.yandex.net/storage/v1/buckets"
NETWORKS_URL = "https://vpc.api.cloud.yandex.net/vpc/v1/networks"
SUBNETS_URL = "https://vpc.api.cloud.yandex.net/vpc/v1/subnets"
SECURITY_GROUPS_URL = "https://vpc.api.cloud.yandex.net/vpc/v1/securityGroups"
LOAD_BALANCERS_URL = (
    "https://load-balancer.api.cloud.yandex.net/load-balancer/v1/networkLoadBalancers"
)
REGISTRIES_URL = (
    "https://container-registry.api.cloud.yandex.net/container-registry/v1/registries"
)
FUNCTIONS_URL = "https://serverless-functions.api.cloud.yandex.net/functions/v1/functions"
CONTAINERS_URL = "https://containers.api.cloud.yandex.net/containers/v1/containers"
DNS_ZONES_URL = "https://dns.api.cloud.yandex.net/dns/v1/zones"
API_GATEWAYS_URL = "https://apigateway.api.cloud.yandex.net/apigateway/v1/apigateways"

MAX_RETRIES = 3
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class YCClient:
    """Async Yandex Cloud API client with retries and token refresh."""

    def __init__(self, yc_config: YandexCloudConfig) -> None:
        self.config = yc_config
        self.auth = IAMAuth(yc_config.service_account_key_path)
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> YCClient:
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def ensure_token(self) -> str:
        """Ensure a valid IAM token is available."""
        return await self.auth.get_iam_token()

    async def get_headers(self) -> dict[str, str]:
        """Return authorization headers with a valid IAM token."""
        token = await self.ensure_token()
        return {"Authorization": f"Bearer {token}"}

    @property
    def headers(self) -> dict[str, str]:
        """Last known authorization headers (token must already be loaded)."""
        token = self.auth._iam_token or ""
        return {"Authorization": f"Bearer {token}"}

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        retried_auth: bool = False,
    ) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("YCClient must be used as an async context manager")

        delay = 1.0
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            headers = await self.get_headers()
            try:
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                ) as resp:
                    if resp.status == 401 and not retried_auth:
                        logger.warning("YC API 401, refreshing IAM token")
                        await self.auth.refresh_token()
                        return await self._request(
                            method, url, params=params, retried_auth=True
                        )
                    if resp.status == 403:
                        logger.error("Forbidden when calling %s", url)
                        return {}
                    if resp.status == 404:
                        return {}
                    if resp.status == 429 or resp.status >= 500:
                        logger.warning(
                            "YC API %s returned %s (attempt %s)",
                            url,
                            resp.status,
                            attempt + 1,
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                    if isinstance(data, dict):
                        return data
                    return {}
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                logger.warning("YC API request failed: %s", exc)
                await asyncio.sleep(delay)
                delay *= 2

        if last_error:
            logger.error("YC API request failed after retries: %s", last_error)
        return {}

    async def get(self, url: str, folder_id: str) -> dict[str, Any]:
        """GET a folder-scoped YC collection endpoint."""
        return await self._request("GET", url, params={"folderId": folder_id})

    async def get_compute_instances(self, folder_id: str) -> dict[str, Any]:
        """Fetch compute instances."""
        return await self.get(COMPUTE_INSTANCES_URL, folder_id)

    async def get_postgresql_clusters(self, folder_id: str) -> dict[str, Any]:
        """Fetch Managed PostgreSQL clusters."""
        return await self.get(POSTGRESQL_CLUSTERS_URL, folder_id)

    async def get_mysql_clusters(self, folder_id: str) -> dict[str, Any]:
        """Fetch Managed MySQL clusters."""
        return await self.get(MYSQL_CLUSTERS_URL, folder_id)

    async def get_mongodb_clusters(self, folder_id: str) -> dict[str, Any]:
        """Fetch Managed MongoDB clusters."""
        return await self.get(MONGODB_CLUSTERS_URL, folder_id)

    async def get_clickhouse_clusters(self, folder_id: str) -> dict[str, Any]:
        """Fetch Managed ClickHouse clusters."""
        return await self.get(CLICKHOUSE_CLUSTERS_URL, folder_id)

    async def get_buckets(self, folder_id: str) -> dict[str, Any]:
        """Fetch Object Storage buckets."""
        return await self.get(BUCKETS_URL, folder_id)

    async def get_networks(self, folder_id: str) -> dict[str, Any]:
        """Fetch VPC networks."""
        return await self.get(NETWORKS_URL, folder_id)

    async def get_subnets(self, folder_id: str) -> dict[str, Any]:
        """Fetch VPC subnets."""
        return await self.get(SUBNETS_URL, folder_id)

    async def get_security_groups(self, folder_id: str) -> dict[str, Any]:
        """Fetch VPC security groups."""
        return await self.get(SECURITY_GROUPS_URL, folder_id)

    async def get_load_balancers(self, folder_id: str) -> dict[str, Any]:
        """Fetch network load balancers."""
        return await self.get(LOAD_BALANCERS_URL, folder_id)

    async def get_registries(self, folder_id: str) -> dict[str, Any]:
        """Fetch container registries."""
        return await self.get(REGISTRIES_URL, folder_id)

    async def get_functions(self, folder_id: str) -> dict[str, Any]:
        """Fetch serverless functions."""
        return await self.get(FUNCTIONS_URL, folder_id)

    async def get_containers(self, folder_id: str) -> dict[str, Any]:
        """Fetch serverless containers."""
        return await self.get(CONTAINERS_URL, folder_id)

    async def get_dns_zones(self, folder_id: str) -> dict[str, Any]:
        """Fetch DNS zones."""
        return await self.get(DNS_ZONES_URL, folder_id)

    async def get_api_gateways(self, folder_id: str) -> dict[str, Any]:
        """Fetch API gateways."""
        return await self.get(API_GATEWAYS_URL, folder_id)
