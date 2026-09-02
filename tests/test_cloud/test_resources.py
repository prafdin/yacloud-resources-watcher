from unittest.mock import Mock

from yacloud_watcher.cloud.models import Resource
from yacloud_watcher.cloud.resources import get_all_resources
from yandex.cloud.compute.v1.instance_service_pb2 import ListInstancesRequest


def test_get_all_resources():
    mock_client = Mock()
    mock_client.folder_id = "b1g123"

    mock_instance_service = Mock()
    mock_instance_service.List.return_value.instances = []
    mock_client.instance_service.return_value = mock_instance_service

    resources = get_all_resources(mock_client)

    assert isinstance(resources, list)
    assert all(isinstance(r, Resource) for r in resources)
    mock_instance_service.List.assert_called_once()
    call_args = mock_instance_service.List.call_args
    assert len(call_args.args) == 1
    assert isinstance(call_args.args[0], ListInstancesRequest)
    assert call_args.args[0].folder_id == "b1g123"
