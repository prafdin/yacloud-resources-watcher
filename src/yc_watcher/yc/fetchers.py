"""Catalogue of the Yandex Cloud resource types the bot reports.

Every supported type differs only in which service stub to open, which request
message to send and which repeated field holds the results, so each is a small
``FetcherSpec`` record and one shared ``fetch`` routine drives them all.
"""

from dataclasses import dataclass
from typing import Any, Callable

from yandex.cloud.compute.v1.disk_service_pb2 import ListDisksRequest
from yandex.cloud.compute.v1.disk_service_pb2_grpc import DiskServiceStub
from yandex.cloud.compute.v1.instance_pb2 import Instance
from yandex.cloud.compute.v1.instance_service_pb2 import ListInstancesRequest
from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
from yandex.cloud.mdb.clickhouse.v1.cluster_service_pb2 import (
    ListClustersRequest as ListClickhouseClustersRequest,
)
from yandex.cloud.mdb.clickhouse.v1.cluster_service_pb2_grpc import (
    ClusterServiceStub as ClickhouseClusterServiceStub,
)
from yandex.cloud.mdb.mongodb.v1.cluster_service_pb2 import (
    ListClustersRequest as ListMongodbClustersRequest,
)
from yandex.cloud.mdb.mongodb.v1.cluster_service_pb2_grpc import (
    ClusterServiceStub as MongodbClusterServiceStub,
)
from yandex.cloud.mdb.mysql.v1.cluster_service_pb2 import (
    ListClustersRequest as ListMysqlClustersRequest,
)
from yandex.cloud.mdb.mysql.v1.cluster_service_pb2_grpc import (
    ClusterServiceStub as MysqlClusterServiceStub,
)
from yandex.cloud.mdb.postgresql.v1.cluster_service_pb2 import (
    ListClustersRequest as ListPostgresqlClustersRequest,
)
from yandex.cloud.mdb.postgresql.v1.cluster_service_pb2_grpc import (
    ClusterServiceStub as PostgresqlClusterServiceStub,
)
from yandex.cloud.serverless.containers.v1.container_service_pb2 import (
    ListContainersRequest,
)
from yandex.cloud.serverless.containers.v1.container_service_pb2_grpc import (
    ContainerServiceStub,
)
from yandex.cloud.serverless.functions.v1.function_service_pb2 import ListFunctionsRequest
from yandex.cloud.serverless.functions.v1.function_service_pb2_grpc import (
    FunctionServiceStub,
)
from yandex.cloud.storage.v1.bucket_service_pb2 import ListBucketsRequest
from yandex.cloud.storage.v1.bucket_service_pb2_grpc import BucketServiceStub
from yandex.cloud.vpc.v1.network_service_pb2 import ListNetworksRequest
from yandex.cloud.vpc.v1.network_service_pb2_grpc import NetworkServiceStub
from yandex.cloud.vpc.v1.subnet_service_pb2 import ListSubnetsRequest
from yandex.cloud.vpc.v1.subnet_service_pb2_grpc import SubnetServiceStub

from yc_watcher.models import Resource
from yc_watcher.yc.pagination import list_all


def _instance_status(item: Any) -> str:
    try:
        name = Instance.Status.Name(item.status)
    except ValueError:
        return "unknown"
    return "unknown" if name == "STATUS_UNSPECIFIED" else name.lower()


PAGE_SIZE = 1000


@dataclass(frozen=True)
class FetcherSpec:
    key: str
    title: str
    stub_ctor: Callable[[Any], Any]
    request_cls: Callable[..., Any]
    items_attr: str
    status_of: Callable[[Any], str] | None = None

    def fetch(self, client) -> list[Resource]:
        stub = client.stub(self.stub_ctor)
        items = list_all(
            stub.List,
            lambda token: self.request_cls(
                folder_id=client.folder_id, page_size=PAGE_SIZE, page_token=token or ""
            ),
            lambda response: getattr(response, self.items_attr),
        )
        return [
            Resource(
                id=item.id or item.name,
                name=item.name or item.id,
                status=self.status_of(item) if self.status_of else None,
            )
            for item in items
        ]


FETCHERS: tuple[FetcherSpec, ...] = (
    FetcherSpec("compute_instances", "🖥 Compute instances", InstanceServiceStub, ListInstancesRequest, "instances", status_of=_instance_status),
    FetcherSpec("disks", "💾 Disks", DiskServiceStub, ListDisksRequest, "disks"),
    FetcherSpec("vpc_networks", "🌐 VPC networks", NetworkServiceStub, ListNetworksRequest, "networks"),
    FetcherSpec("vpc_subnets", "🧩 VPC subnets", SubnetServiceStub, ListSubnetsRequest, "subnets"),
    FetcherSpec("storage_buckets", "🪣 Object Storage buckets", BucketServiceStub, ListBucketsRequest, "buckets"),
    FetcherSpec("mdb_postgresql", "🐘 PostgreSQL clusters", PostgresqlClusterServiceStub, ListPostgresqlClustersRequest, "clusters"),
    FetcherSpec("mdb_mysql", "🐬 MySQL clusters", MysqlClusterServiceStub, ListMysqlClustersRequest, "clusters"),
    FetcherSpec("mdb_clickhouse", "🟡 ClickHouse clusters", ClickhouseClusterServiceStub, ListClickhouseClustersRequest, "clusters"),
    FetcherSpec("mdb_mongodb", "🍃 MongoDB clusters", MongodbClusterServiceStub, ListMongodbClustersRequest, "clusters"),
    FetcherSpec("serverless_functions", "⚡ Serverless functions", FunctionServiceStub, ListFunctionsRequest, "functions"),
    FetcherSpec("serverless_containers", "📦 Serverless containers", ContainerServiceStub, ListContainersRequest, "containers"),
)
