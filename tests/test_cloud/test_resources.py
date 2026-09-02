from unittest.mock import Mock

from yacloud_watcher.cloud.models import Resource
from yacloud_watcher.cloud.resources import get_all_resources


def test_get_all_resources():
    mock_client = Mock()
    mock_client.folder_id = "b1g123"

    mock_instance_service = Mock()
    mock_instance_service.List.return_value.instances = []
    mock_client.instance_service.return_value = mock_instance_service

    resources = get_all_resources(mock_client)

    assert isinstance(resources, list)
    assert all(isinstance(r, Resource) for r in resources)
