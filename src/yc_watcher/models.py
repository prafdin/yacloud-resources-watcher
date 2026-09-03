"""Pure data structures describing a folder's resource inventory.

These carry the result of one polling pass from the Yandex Cloud layer to the
formatting layer; they hold no behaviour beyond simple derived counts and never
touch the SDK or the network.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Resource:
    id: str
    name: str
    status: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceGroup:
    key: str
    title: str
    resources: tuple[Resource, ...] = ()
    error: str | None = None

    @property
    def count(self) -> int:
        return len(self.resources)

    @property
    def failed(self) -> bool:
        return self.error is not None


@dataclass(frozen=True, slots=True)
class InventorySnapshot:
    folder_id: str
    generated_at: datetime
    groups: tuple[ResourceGroup, ...]

    @property
    def total(self) -> int:
        return sum(group.count for group in self.groups)

    @property
    def any_failed(self) -> bool:
        return any(group.failed for group in self.groups)

    @property
    def is_empty(self) -> bool:
        return self.total == 0 and not self.any_failed
