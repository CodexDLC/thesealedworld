from typing import TypeVar

T = TypeVar("T")


class ServiceMapper:
    def map(self, value: T) -> T:
        return value
