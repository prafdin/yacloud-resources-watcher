"""Pydantic models for notifications and cloud resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Notification(BaseModel):
    """Pending notification waiting for acknowledgment."""

    id: int
    message_id: int
    chat_id: int
    sent_at: datetime
    acknowledged: bool = False
    reminder_sent: bool = False


class ComputeInstance(BaseModel):
    """Yandex Compute instance."""

    id: str
    name: str
    status: str
    cores: int | None = None
    memory_gb: float | None = None
    public_ip: str | None = None


class DatabaseCluster(BaseModel):
    """Managed database cluster."""

    id: str
    name: str
    status: str
    db_type: str
    version: str | None = None
    preset: str | None = None


class StorageBucket(BaseModel):
    """Object Storage bucket."""

    name: str
    region: str | None = None


class Network(BaseModel):
    """VPC network."""

    id: str
    name: str


class Subnet(BaseModel):
    """VPC subnet."""

    id: str
    name: str
    zone_id: str | None = None
    cidr: str | None = None


class SecurityGroup(BaseModel):
    """VPC security group."""

    id: str
    name: str
    rules_count: int = 0


class LoadBalancer(BaseModel):
    """Network load balancer."""

    id: str
    name: str
    status: str
    address: str | None = None
    port: int | None = None


class ContainerRegistry(BaseModel):
    """Container Registry."""

    id: str
    name: str
    status: str = "ACTIVE"


class ServerlessFunction(BaseModel):
    """Cloud Function."""

    id: str
    name: str
    status: str
    runtime: str | None = None
    memory: int | None = None


class ServerlessContainer(BaseModel):
    """Serverless container."""

    id: str
    name: str
    status: str
    cores: int | None = None
    memory: int | None = None


class DNSZone(BaseModel):
    """Cloud DNS zone."""

    id: str
    name: str
    zone: str
    public: bool = False


class APIGateway(BaseModel):
    """API Gateway."""

    id: str
    name: str
    status: str
    domain: str | None = None


class AllResources(BaseModel):
    """Aggregated snapshot of folder resources."""

    compute_instances: list[ComputeInstance] = Field(default_factory=list)
    postgresql_clusters: list[DatabaseCluster] = Field(default_factory=list)
    mysql_clusters: list[DatabaseCluster] = Field(default_factory=list)
    mongodb_clusters: list[DatabaseCluster] = Field(default_factory=list)
    clickhouse_clusters: list[DatabaseCluster] = Field(default_factory=list)
    buckets: list[StorageBucket] = Field(default_factory=list)
    networks: list[Network] = Field(default_factory=list)
    subnets: list[Subnet] = Field(default_factory=list)
    security_groups: list[SecurityGroup] = Field(default_factory=list)
    load_balancers: list[LoadBalancer] = Field(default_factory=list)
    registries: list[ContainerRegistry] = Field(default_factory=list)
    functions: list[ServerlessFunction] = Field(default_factory=list)
    containers: list[ServerlessContainer] = Field(default_factory=list)
    dns_zones: list[DNSZone] = Field(default_factory=list)
    api_gateways: list[APIGateway] = Field(default_factory=list)

    @property
    def databases(self) -> list[DatabaseCluster]:
        """All managed database clusters."""
        return (
            self.postgresql_clusters
            + self.mysql_clusters
            + self.mongodb_clusters
            + self.clickhouse_clusters
        )

    @property
    def total_count(self) -> int:
        """Total number of resources."""
        return (
            len(self.compute_instances)
            + len(self.databases)
            + len(self.buckets)
            + len(self.networks)
            + len(self.subnets)
            + len(self.security_groups)
            + len(self.load_balancers)
            + len(self.registries)
            + len(self.functions)
            + len(self.containers)
            + len(self.dns_zones)
            + len(self.api_gateways)
        )

    def iter_statused(self) -> list[str]:
        """Return status strings for resources that have a status."""
        statuses: list[str] = []
        statuses.extend(item.status for item in self.compute_instances)
        statuses.extend(item.status for item in self.databases)
        statuses.extend(item.status for item in self.load_balancers)
        statuses.extend(item.status for item in self.registries)
        statuses.extend(item.status for item in self.functions)
        statuses.extend(item.status for item in self.containers)
        statuses.extend(item.status for item in self.api_gateways)
        return statuses
