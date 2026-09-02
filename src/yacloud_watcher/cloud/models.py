from dataclasses import dataclass


@dataclass
class Resource:
    name: str
    resource_type: str
    status: str | None = None
    zone: str | None = None

    def format(self) -> str:
        if self.status:
            return f"  - {self.name} ({self.status})"
        return f"  - {self.name}"
