from typing import TYPE_CHECKING

from yandex.cloud.compute.v1.instance_service_pb2 import ListInstancesRequest

from yacloud_watcher.cloud.models import Resource

if TYPE_CHECKING:
    from yacloud_watcher.cloud.client import YCClient


def get_compute_instances(client: "YCClient") -> list[Resource]:
    service = client.instance_service()
    response = service.List(ListInstancesRequest(folder_id=client.folder_id))

    return [
        Resource(
            name=instance.name,
            resource_type="compute",
            status=instance.DESCRIPTOR.fields_by_name["status"].enum_type.values_by_number[instance.status].name,
            zone=instance.zone_id,
        )
        for instance in response.instances
    ]


def get_all_resources(client: "YCClient") -> list[Resource]:
    resources: list[Resource] = []
    resources.extend(get_compute_instances(client))
    return resources
