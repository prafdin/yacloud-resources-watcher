from yacloud_watcher.cloud.models import Resource


def test_resource_creation():
    resource = Resource(
        name="vm-1",
        resource_type="compute",
        status="RUNNING",
        zone="ru-central1-a"
    )

    assert resource.name == "vm-1"
    assert resource.resource_type == "compute"
    assert resource.status == "RUNNING"
    assert resource.zone == "ru-central1-a"


def test_resource_formatting():
    resource = Resource(
        name="vm-1",
        resource_type="compute",
        status="RUNNING",
        zone="ru-central1-a"
    )

    formatted = resource.format()
    assert "vm-1" in formatted
    assert "RUNNING" in formatted
