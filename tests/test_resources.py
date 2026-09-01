"""Tests for resource fetching and message formatting."""

from unittest.mock import AsyncMock, MagicMock

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
from yandex_cloud.resources import (
    fetch_all_resources,
    fetch_api_gateways,
    fetch_buckets,
    fetch_clickhouse_clusters,
    fetch_compute_instances,
    fetch_containers,
    fetch_dns_zones,
    fetch_functions,
    fetch_load_balancers,
    fetch_mongodb_clusters,
    fetch_mysql_clusters,
    fetch_networks,
    fetch_postgresql_clusters,
    fetch_registries,
    fetch_security_groups,
    fetch_subnets,
    format_resources_message,
)


def _client_with(method_name: str, payload: dict) -> MagicMock:
    client = MagicMock()
    setattr(client, method_name, AsyncMock(return_value=payload))
    return client


async def test_fetch_compute_instances(sample_compute_instances):
    """Test fetching compute instances."""
    client = _client_with("get_compute_instances", sample_compute_instances)
    resources = await fetch_compute_instances(client, "b1g_test")
    assert len(resources) == 2
    assert resources[0].name == "vm-1"
    assert resources[0].status == "RUNNING"
    assert resources[0].cores == 2
    assert resources[0].public_ip == "51.250.1.1"
    assert resources[1].name == "vm-2"
    assert resources[1].status == "STOPPED"
    assert resources[1].public_ip is None


async def test_fetch_compute_instances_string_memory(sample_compute_instances):
    """Test string memory value is parsed correctly."""
    payload = {"instances": [
        {**sample_compute_instances["instances"][0],
         "resources": {**sample_compute_instances["instances"][0]["resources"],
                       "memory": "4294967296"}}
    ]}
    client = _client_with("get_compute_instances", payload)
    resources = await fetch_compute_instances(client, "b1g_test")
    assert len(resources) == 1
    assert resources[0].memory_gb == 4.0


async def test_fetch_compute_instances_bad_record_keeps_rest(sample_compute_instances):
    """Test a single bad record does not crash the whole list."""
    instances = sample_compute_instances["instances"]
    bad = {
        **instances[0],
        "id": "bad",
        "resources": {**instances[0]["resources"], "memory": "not-a-number"},
    }
    payload = {"instances": [bad, instances[0]]}
    client = _client_with("get_compute_instances", payload)
    resources = await fetch_compute_instances(client, "b1g_test")
    assert len(resources) == 2
    assert resources[0].id == "bad"
    assert resources[0].memory_gb is None
    assert resources[1].id == "fhm_test1"
    assert resources[1].memory_gb == 4.0


async def test_fetch_compute_instances_empty():
    """Test when no instances exist."""
    client = _client_with("get_compute_instances", {"instances": []})
    resources = await fetch_compute_instances(client, "b1g_test")
    assert resources == []


async def test_fetch_compute_instances_api_error():
    """Test handling of API errors."""
    client = MagicMock()
    client.get_compute_instances = AsyncMock(side_effect=RuntimeError("api down"))
    resources = await fetch_compute_instances(client, "b1g_test")
    assert resources == []


async def test_fetch_postgresql_clusters(sample_postgresql_clusters):
    """Test fetching PostgreSQL clusters."""
    client = _client_with("get_postgresql_clusters", sample_postgresql_clusters)
    resources = await fetch_postgresql_clusters(client, "b1g_test")
    assert len(resources) == 1
    assert resources[0].name == "postgres-cluster"
    assert resources[0].version == "15"
    assert resources[0].preset == "s2.micro"


async def test_fetch_all_resources(mock_config, sample_compute_instances):
    """Test fetching all resource types."""
    client = MagicMock()
    client.ensure_token = AsyncMock()
    client.get_compute_instances = AsyncMock(return_value=sample_compute_instances)
    for method in (
        "get_postgresql_clusters",
        "get_mysql_clusters",
        "get_mongodb_clusters",
        "get_clickhouse_clusters",
        "get_buckets",
        "get_networks",
        "get_subnets",
        "get_security_groups",
        "get_load_balancers",
        "get_registries",
        "get_functions",
        "get_containers",
        "get_dns_zones",
        "get_api_gateways",
    ):
        getattr(client, method)
        setattr(client, method, AsyncMock(return_value={}))

    resources = await fetch_all_resources(mock_config, client=client)
    assert len(resources.compute_instances) == 2
    assert resources.total_count == 2


async def test_fetch_all_resources_partial_failure(mock_config):
    """Test that one failing fetcher does not break the rest."""
    client = MagicMock()
    client.ensure_token = AsyncMock()
    client.get_compute_instances = AsyncMock(
        return_value={"instances": [{"id": "1", "name": "vm", "status": "RUNNING"}]}
    )
    client.get_postgresql_clusters = AsyncMock(side_effect=RuntimeError("fail"))
    for method in (
        "get_mysql_clusters",
        "get_mongodb_clusters",
        "get_clickhouse_clusters",
        "get_buckets",
        "get_networks",
        "get_subnets",
        "get_security_groups",
        "get_load_balancers",
        "get_registries",
        "get_functions",
        "get_containers",
        "get_dns_zones",
        "get_api_gateways",
    ):
        setattr(client, method, AsyncMock(return_value={}))

    resources = await fetch_all_resources(mock_config, client=client)
    assert len(resources.compute_instances) == 1
    assert resources.postgresql_clusters == []


def test_format_resources_message():
    """Test message formatting."""
    resources = AllResources(
        compute_instances=[
            ComputeInstance(
                id="1",
                name="vm-1",
                status="RUNNING",
                cores=2,
                memory_gb=4,
                public_ip="51.250.1.1",
            ),
            ComputeInstance(id="2", name="vm-2", status="STOPPED"),
        ],
        postgresql_clusters=[
            DatabaseCluster(
                id="3",
                name="postgres-cluster",
                status="RUNNING",
                db_type="postgresql",
                version="15",
                preset="s2.micro",
            )
        ],
        buckets=[StorageBucket(name="my-bucket-1")],
    )
    message = format_resources_message(resources)
    assert "📊 Yandex Cloud Resources Report" in message
    assert "🖥️ Compute Instances (2):" in message
    assert "vm-1: RUNNING (CPU: 2, RAM: 4GB, IP: 51.250.1.1)" in message
    assert "vm-2: STOPPED" in message
    assert "postgres-cluster: RUNNING (v15, s2.micro)" in message
    assert "my-bucket-1" in message
    assert "Total: 4 resources (2 running/active, 1 stopped, 1 other)" in message
    assert "Reply OK to acknowledge" in message


def test_format_resources_message_empty():
    """Test formatting when no resources."""
    message = format_resources_message(AllResources())
    assert "No resources found." in message
    assert "Reply OK to acknowledge" in message
    assert "Total:" not in message


def test_format_resources_message_all_sections():
    """Test formatting of remaining resource types."""
    resources = AllResources(
        networks=[Network(id="n1", name="default-network")],
        subnets=[
            Subnet(
                id="s1",
                name="default-subnet-a",
                zone_id="ru-central1-a",
                cidr="10.0.0.0/24",
            )
        ],
        security_groups=[
            SecurityGroup(id="g1", name="default-security-group", rules_count=5)
        ],
        load_balancers=[
            LoadBalancer(
                id="l1",
                name="my-load-balancer",
                status="ACTIVE",
                address="51.250.2.1",
                port=80,
            )
        ],
        registries=[ContainerRegistry(id="r1", name="my-registry")],
        functions=[
            ServerlessFunction(
                id="f1",
                name="my-function-1",
                status="ACTIVE",
                runtime="python311",
                memory=128,
            )
        ],
        containers=[
            ServerlessContainer(
                id="c1", name="my-container", status="ACTIVE", cores=1, memory=128
            )
        ],
        dns_zones=[
            DNSZone(id="d1", name="my-zone", zone="example.com.", public=True)
        ],
        api_gateways=[
            APIGateway(
                id="a1",
                name="my-api-gateway",
                status="ACTIVE",
                domain="b1g.apigw.yandexcloud.net",
            )
        ],
        mysql_clusters=[
            DatabaseCluster(id="m1", name="mysql-cluster", status="STOPPED", db_type="mysql")
        ],
    )
    message = format_resources_message(resources)
    assert "default-network" in message
    assert "default-subnet-a (ru-central1-a, 10.0.0.0/24)" in message
    assert "default-security-group (5 rules)" in message
    assert "my-load-balancer: ACTIVE (51.250.2.1:80)" in message
    assert "my-registry" in message
    assert "my-function-1: ACTIVE (python311, 128MB)" in message
    assert "my-container: ACTIVE (1 CPU, 128MB)" in message
    assert "example.com (public)" in message
    assert "my-api-gateway: ACTIVE (b1g.apigw.yandexcloud.net)" in message
    assert "mysql-cluster: STOPPED" in message


async def test_fetch_other_resource_types():
    """Test remaining fetchers parse API payloads."""
    assert len(await fetch_mysql_clusters(_client_with("get_mysql_clusters", {"clusters": [{"id": "1", "name": "mysql", "status": "RUNNING", "config": {}}]}), "f")) == 1
    assert len(await fetch_mongodb_clusters(_client_with("get_mongodb_clusters", {"clusters": [{"id": "1", "name": "mongo", "status": "RUNNING", "config": {}}]}), "f")) == 1
    assert len(await fetch_clickhouse_clusters(_client_with("get_clickhouse_clusters", {"clusters": [{"id": "1", "name": "ch", "status": "RUNNING", "config": {}}]}), "f")) == 1
    assert (await fetch_buckets(_client_with("get_buckets", {"buckets": [{"name": "b1"}]}), "f"))[0].name == "b1"
    assert (await fetch_networks(_client_with("get_networks", {"networks": [{"id": "n", "name": "net"}]}), "f"))[0].name == "net"
    assert (await fetch_subnets(_client_with("get_subnets", {"subnets": [{"id": "s", "name": "sub", "zoneId": "z", "v4CidrBlocks": ["10.0.0.0/24"]}]}), "f"))[0].cidr == "10.0.0.0/24"
    groups = await fetch_security_groups(_client_with("get_security_groups", {"securityGroups": [{"id": "g", "name": "sg", "rules": [1, 2]}]}), "f")
    assert groups[0].rules_count == 2
    lbs = await fetch_load_balancers(_client_with("get_load_balancers", {"networkLoadBalancers": [{"id": "l", "name": "lb", "status": "ACTIVE", "listeners": [{"address": "1.1.1.1", "port": 80}]}]}), "f")
    assert lbs[0].port == 80
    assert (await fetch_registries(_client_with("get_registries", {"registries": [{"id": "r", "name": "reg"}]}), "f"))[0].name == "reg"
    assert (await fetch_functions(_client_with("get_functions", {"functions": [{"id": "f", "name": "fn", "status": "ACTIVE", "runtime": "python311", "memory": 128}]}), "f"))[0].runtime == "python311"
    assert (await fetch_containers(_client_with("get_containers", {"containers": [{"id": "c", "name": "ctr", "status": "ACTIVE", "cores": 1, "memory": 128}]}), "f"))[0].cores == 1
    assert (await fetch_dns_zones(_client_with("get_dns_zones", {"dnsZones": [{"id": "d", "name": "z", "zone": "ex.com.", "publicVisibility": True}]}), "f"))[0].public is True
    assert (await fetch_api_gateways(_client_with("get_api_gateways", {"apiGateways": [{"id": "a", "name": "gw", "status": "ACTIVE", "domain": "d"}]}), "f"))[0].domain == "d"


async def test_fetchers_return_empty_on_error():
    """Test fetchers swallow API errors."""
    client = MagicMock()
    client.get_buckets = AsyncMock(side_effect=RuntimeError("fail"))
    assert await fetch_buckets(client, "f") == []

