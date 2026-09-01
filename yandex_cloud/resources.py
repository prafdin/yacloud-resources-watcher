"""Fetch and format Yandex Cloud resources."""

from __future__ import annotations

import asyncio
import logging
from config.settings import Config
from storage.models import (
    APIGateway,
    AllResources,
    ComputeInstance,
    ContainerRegistry,
    DatabaseCluster,
    DNSZone,
    LoadBalancer,
    Network,
    SecurityGroup,
    ServerlessContainer,
    ServerlessFunction,
    StorageBucket,
    Subnet,
)
from yandex_cloud.client import YCClient

logger = logging.getLogger(__name__)

RUNNING_STATUSES = {"RUNNING", "ACTIVE", "REVISION_ACTIVE"}
STOPPED_STATUSES = {"STOPPED", "INACTIVE"}


def _bytes_to_gb(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return int(value) / (1024**3)
    except (TypeError, ValueError):
        return None


def _format_memory_gb(memory_gb: float | None) -> str | None:
    if memory_gb is None:
        return None
    if abs(memory_gb - round(memory_gb)) < 0.05:
        return f"{int(round(memory_gb))}GB"
    return f"{memory_gb:.1f}GB"


def _extract_public_ip(instance: dict) -> str | None:
    for iface in instance.get("networkInterfaces") or []:
        primary = iface.get("primaryV4Address") or {}
        nat = primary.get("oneToOneNat") or {}
        address = nat.get("address")
        if address:
            return address
    return None


def _parse_db_cluster(raw: dict, db_type: str) -> DatabaseCluster:
    config = raw.get("config") or {}
    resources = config.get("resources") or {}
    return DatabaseCluster(
        id=raw.get("id", ""),
        name=raw.get("name", raw.get("id", "unknown")),
        status=raw.get("status", "UNKNOWN"),
        db_type=db_type,
        version=config.get("version"),
        preset=resources.get("resourcePresetId"),
    )


async def fetch_compute_instances(
    client: YCClient, folder_id: str
) -> list[ComputeInstance]:
    """Fetch compute instances."""
    try:
        response = await client.get_compute_instances(folder_id)
        instances: list[ComputeInstance] = []
        for raw in response.get("instances", []):
            resources = raw.get("resources") or {}
            instances.append(
                ComputeInstance(
                    id=raw.get("id", ""),
                    name=raw.get("name", raw.get("id", "unknown")),
                    status=raw.get("status", "UNKNOWN"),
                    cores=resources.get("cores"),
                    memory_gb=_bytes_to_gb(resources.get("memory")),
                    public_ip=_extract_public_ip(raw),
                )
            )
        return instances
    except Exception as exc:
        logger.error("Failed to fetch compute instances: %s", exc)
        return []


async def fetch_postgresql_clusters(
    client: YCClient, folder_id: str
) -> list[DatabaseCluster]:
    """Fetch Managed PostgreSQL clusters."""
    try:
        response = await client.get_postgresql_clusters(folder_id)
        return [
            _parse_db_cluster(raw, "postgresql")
            for raw in response.get("clusters", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch PostgreSQL clusters: %s", exc)
        return []


async def fetch_mysql_clusters(
    client: YCClient, folder_id: str
) -> list[DatabaseCluster]:
    """Fetch Managed MySQL clusters."""
    try:
        response = await client.get_mysql_clusters(folder_id)
        return [_parse_db_cluster(raw, "mysql") for raw in response.get("clusters", [])]
    except Exception as exc:
        logger.error("Failed to fetch MySQL clusters: %s", exc)
        return []


async def fetch_mongodb_clusters(
    client: YCClient, folder_id: str
) -> list[DatabaseCluster]:
    """Fetch Managed MongoDB clusters."""
    try:
        response = await client.get_mongodb_clusters(folder_id)
        return [
            _parse_db_cluster(raw, "mongodb") for raw in response.get("clusters", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch MongoDB clusters: %s", exc)
        return []


async def fetch_clickhouse_clusters(
    client: YCClient, folder_id: str
) -> list[DatabaseCluster]:
    """Fetch Managed ClickHouse clusters."""
    try:
        response = await client.get_clickhouse_clusters(folder_id)
        return [
            _parse_db_cluster(raw, "clickhouse")
            for raw in response.get("clusters", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch ClickHouse clusters: %s", exc)
        return []


async def fetch_buckets(client: YCClient, folder_id: str) -> list[StorageBucket]:
    """Fetch Object Storage buckets."""
    try:
        response = await client.get_buckets(folder_id)
        return [
            StorageBucket(name=raw.get("name", "unknown"), region=raw.get("region"))
            for raw in response.get("buckets", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch buckets: %s", exc)
        return []


async def fetch_networks(client: YCClient, folder_id: str) -> list[Network]:
    """Fetch VPC networks."""
    try:
        response = await client.get_networks(folder_id)
        return [
            Network(id=raw.get("id", ""), name=raw.get("name", raw.get("id", "unknown")))
            for raw in response.get("networks", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch networks: %s", exc)
        return []


async def fetch_subnets(client: YCClient, folder_id: str) -> list[Subnet]:
    """Fetch VPC subnets."""
    try:
        response = await client.get_subnets(folder_id)
        subnets: list[Subnet] = []
        for raw in response.get("subnets", []):
            cidrs = raw.get("v4CidrBlocks") or []
            subnets.append(
                Subnet(
                    id=raw.get("id", ""),
                    name=raw.get("name", raw.get("id", "unknown")),
                    zone_id=raw.get("zoneId"),
                    cidr=cidrs[0] if cidrs else None,
                )
            )
        return subnets
    except Exception as exc:
        logger.error("Failed to fetch subnets: %s", exc)
        return []


async def fetch_security_groups(
    client: YCClient, folder_id: str
) -> list[SecurityGroup]:
    """Fetch VPC security groups."""
    try:
        response = await client.get_security_groups(folder_id)
        groups: list[SecurityGroup] = []
        for raw in response.get("securityGroups", []):
            rules_count = raw.get("rulesCount")
            if rules_count is None:
                rules_count = len(raw.get("rules") or [])
            groups.append(
                SecurityGroup(
                    id=raw.get("id", ""),
                    name=raw.get("name", raw.get("id", "unknown")),
                    rules_count=int(rules_count),
                )
            )
        return groups
    except Exception as exc:
        logger.error("Failed to fetch security groups: %s", exc)
        return []


async def fetch_load_balancers(client: YCClient, folder_id: str) -> list[LoadBalancer]:
    """Fetch network load balancers."""
    try:
        response = await client.get_load_balancers(folder_id)
        balancers: list[LoadBalancer] = []
        for raw in response.get("networkLoadBalancers", []):
            listeners = raw.get("listeners") or []
            address = None
            port = None
            if listeners:
                address = listeners[0].get("address")
                port = listeners[0].get("port")
            balancers.append(
                LoadBalancer(
                    id=raw.get("id", ""),
                    name=raw.get("name", raw.get("id", "unknown")),
                    status=raw.get("status", "UNKNOWN"),
                    address=address,
                    port=port,
                )
            )
        return balancers
    except Exception as exc:
        logger.error("Failed to fetch load balancers: %s", exc)
        return []


async def fetch_registries(client: YCClient, folder_id: str) -> list[ContainerRegistry]:
    """Fetch container registries."""
    try:
        response = await client.get_registries(folder_id)
        return [
            ContainerRegistry(
                id=raw.get("id", ""),
                name=raw.get("name", raw.get("id", "unknown")),
                status=raw.get("status", "ACTIVE"),
            )
            for raw in response.get("registries", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch registries: %s", exc)
        return []


async def fetch_functions(client: YCClient, folder_id: str) -> list[ServerlessFunction]:
    """Fetch serverless functions."""
    try:
        response = await client.get_functions(folder_id)
        functions: list[ServerlessFunction] = []
        for raw in response.get("functions", []):
            memory = raw.get("memory")
            functions.append(
                ServerlessFunction(
                    id=raw.get("id", ""),
                    name=raw.get("name", raw.get("id", "unknown")),
                    status=raw.get("status", "UNKNOWN"),
                    runtime=raw.get("runtime"),
                    memory=int(memory) if memory is not None else None,
                )
            )
        return functions
    except Exception as exc:
        logger.error("Failed to fetch functions: %s", exc)
        return []


async def fetch_containers(
    client: YCClient, folder_id: str
) -> list[ServerlessContainer]:
    """Fetch serverless containers."""
    try:
        response = await client.get_containers(folder_id)
        containers: list[ServerlessContainer] = []
        for raw in response.get("containers", []):
            containers.append(
                ServerlessContainer(
                    id=raw.get("id", ""),
                    name=raw.get("name", raw.get("id", "unknown")),
                    status=raw.get("status", "UNKNOWN"),
                    cores=raw.get("cores"),
                    memory=raw.get("memory"),
                )
            )
        return containers
    except Exception as exc:
        logger.error("Failed to fetch containers: %s", exc)
        return []


async def fetch_dns_zones(client: YCClient, folder_id: str) -> list[DNSZone]:
    """Fetch DNS zones."""
    try:
        response = await client.get_dns_zones(folder_id)
        return [
            DNSZone(
                id=raw.get("id", ""),
                name=raw.get("name", raw.get("id", "unknown")),
                zone=raw.get("zone", raw.get("name", "unknown")),
                public=bool(raw.get("publicVisibility")),
            )
            for raw in response.get("dnsZones", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch DNS zones: %s", exc)
        return []


async def fetch_api_gateways(client: YCClient, folder_id: str) -> list[APIGateway]:
    """Fetch API gateways."""
    try:
        response = await client.get_api_gateways(folder_id)
        return [
            APIGateway(
                id=raw.get("id", ""),
                name=raw.get("name", raw.get("id", "unknown")),
                status=raw.get("status", "UNKNOWN"),
                domain=raw.get("domain"),
            )
            for raw in response.get("apiGateways", [])
        ]
    except Exception as exc:
        logger.error("Failed to fetch API gateways: %s", exc)
        return []


async def fetch_all_resources(
    config: Config, client: YCClient | None = None
) -> AllResources:
    """Fetch all supported resource types concurrently."""
    folder_id = config.yandex_cloud.folder_id

    async def _gather(active_client: YCClient) -> AllResources:
        await active_client.ensure_token()
        results = await asyncio.gather(
            fetch_compute_instances(active_client, folder_id),
            fetch_postgresql_clusters(active_client, folder_id),
            fetch_mysql_clusters(active_client, folder_id),
            fetch_mongodb_clusters(active_client, folder_id),
            fetch_clickhouse_clusters(active_client, folder_id),
            fetch_buckets(active_client, folder_id),
            fetch_networks(active_client, folder_id),
            fetch_subnets(active_client, folder_id),
            fetch_security_groups(active_client, folder_id),
            fetch_load_balancers(active_client, folder_id),
            fetch_registries(active_client, folder_id),
            fetch_functions(active_client, folder_id),
            fetch_containers(active_client, folder_id),
            fetch_dns_zones(active_client, folder_id),
            fetch_api_gateways(active_client, folder_id),
            return_exceptions=True,
        )
        cleaned: list = []
        labels = [
            "compute",
            "postgresql",
            "mysql",
            "mongodb",
            "clickhouse",
            "buckets",
            "networks",
            "subnets",
            "security_groups",
            "load_balancers",
            "registries",
            "functions",
            "containers",
            "dns_zones",
            "api_gateways",
        ]
        for label, result in zip(labels, results):
            if isinstance(result, Exception):
                logger.error("Failed to fetch %s: %s", label, result)
                cleaned.append([])
            else:
                cleaned.append(result)
        return AllResources(
            compute_instances=cleaned[0],
            postgresql_clusters=cleaned[1],
            mysql_clusters=cleaned[2],
            mongodb_clusters=cleaned[3],
            clickhouse_clusters=cleaned[4],
            buckets=cleaned[5],
            networks=cleaned[6],
            subnets=cleaned[7],
            security_groups=cleaned[8],
            load_balancers=cleaned[9],
            registries=cleaned[10],
            functions=cleaned[11],
            containers=cleaned[12],
            dns_zones=cleaned[13],
            api_gateways=cleaned[14],
        )

    if client is not None:
        return await _gather(client)
    async with YCClient(config.yandex_cloud) as owned_client:
        return await _gather(owned_client)


def _status_counts(resources: AllResources) -> tuple[int, int, int]:
    running = 0
    stopped = 0
    other = 0
    statused = len(resources.iter_statused())
    unstatused = resources.total_count - statused
    for status in resources.iter_statused():
        upper = status.upper()
        if upper in RUNNING_STATUSES:
            running += 1
        elif upper in STOPPED_STATUSES:
            stopped += 1
        else:
            other += 1
    other += unstatused
    return running, stopped, other


def format_resources_message(resources: AllResources) -> str:
    """Format resources into a Telegram report message."""
    sections: list[str] = ["📊 Yandex Cloud Resources Report"]

    if resources.compute_instances:
        section = f"🖥️ Compute Instances ({len(resources.compute_instances)}):"
        for instance in resources.compute_instances:
            line = f"  • {instance.name}: {instance.status}"
            if instance.status.upper() in RUNNING_STATUSES:
                details: list[str] = []
                if instance.cores is not None:
                    details.append(f"CPU: {instance.cores}")
                memory = _format_memory_gb(instance.memory_gb)
                if memory:
                    details.append(f"RAM: {memory}")
                if instance.public_ip:
                    details.append(f"IP: {instance.public_ip}")
                if details:
                    line += f" ({', '.join(details)})"
            section += f"\n{line}"
        sections.append(section)

    databases = resources.databases
    if databases:
        section = f"🗄️ Databases ({len(databases)}):"
        for cluster in databases:
            line = f"  • {cluster.name}: {cluster.status}"
            if cluster.status.upper() in RUNNING_STATUSES:
                details = []
                if cluster.version:
                    details.append(f"v{cluster.version}")
                if cluster.preset:
                    details.append(cluster.preset)
                if details:
                    line += f" ({', '.join(details)})"
            section += f"\n{line}"
        sections.append(section)

    if resources.buckets:
        section = f"📦 Storage Buckets ({len(resources.buckets)}):"
        for bucket in resources.buckets:
            section += f"\n  • {bucket.name}"
        sections.append(section)

    if resources.networks:
        section = f"🌐 Networks ({len(resources.networks)}):"
        for network in resources.networks:
            section += f"\n  • {network.name}"
        sections.append(section)

    if resources.subnets:
        section = f"🔗 Subnets ({len(resources.subnets)}):"
        for subnet in resources.subnets:
            extras = [item for item in (subnet.zone_id, subnet.cidr) if item]
            extra = f" ({', '.join(extras)})" if extras else ""
            section += f"\n  • {subnet.name}{extra}"
        sections.append(section)

    if resources.security_groups:
        section = f"🔒 Security Groups ({len(resources.security_groups)}):"
        for group in resources.security_groups:
            section += f"\n  • {group.name} ({group.rules_count} rules)"
        sections.append(section)

    if resources.load_balancers:
        section = f"⚖️ Load Balancers ({len(resources.load_balancers)}):"
        for balancer in resources.load_balancers:
            line = f"  • {balancer.name}: {balancer.status}"
            if balancer.address and balancer.port:
                line += f" ({balancer.address}:{balancer.port})"
            elif balancer.address:
                line += f" ({balancer.address})"
            section += f"\n{line}"
        sections.append(section)

    if resources.registries:
        section = f"📦 Container Registries ({len(resources.registries)}):"
        for registry in resources.registries:
            section += f"\n  • {registry.name}"
        sections.append(section)

    if resources.functions:
        section = f"⚡ Serverless Functions ({len(resources.functions)}):"
        for function in resources.functions:
            line = f"  • {function.name}: {function.status}"
            details = []
            if function.runtime:
                details.append(function.runtime)
            if function.memory is not None:
                details.append(f"{function.memory}MB")
            if details:
                line += f" ({', '.join(details)})"
            section += f"\n{line}"
        sections.append(section)

    if resources.containers:
        section = f"📦 Serverless Containers ({len(resources.containers)}):"
        for container in resources.containers:
            line = f"  • {container.name}: {container.status}"
            details = []
            if container.cores is not None:
                details.append(f"{container.cores} CPU")
            if container.memory is not None:
                details.append(f"{container.memory}MB")
            if details:
                line += f" ({', '.join(details)})"
            section += f"\n{line}"
        sections.append(section)

    if resources.dns_zones:
        section = f"🌍 DNS Zones ({len(resources.dns_zones)}):"
        for zone in resources.dns_zones:
            visibility = "public" if zone.public else "private"
            label = zone.zone.rstrip(".")
            section += f"\n  • {label} ({visibility})"
        sections.append(section)

    if resources.api_gateways:
        section = f"🚪 API Gateways ({len(resources.api_gateways)}):"
        for gateway in resources.api_gateways:
            line = f"  • {gateway.name}: {gateway.status}"
            if gateway.domain:
                line += f" ({gateway.domain})"
            section += f"\n{line}"
        sections.append(section)

    if resources.total_count == 0:
        sections.append("No resources found.")
    else:
        running, stopped, other = _status_counts(resources)
        sections.append(
            f"Total: {resources.total_count} resources "
            f"({running} running/active, {stopped} stopped, {other} other)"
        )

    sections.append("Reply OK to acknowledge")
    return "\n\n".join(sections)
