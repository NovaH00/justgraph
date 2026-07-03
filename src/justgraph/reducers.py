"""Built-in reducers for common field update patterns."""

from typing import Any

from justgraph.models import Reducer

class Append(Reducer[list[Any]]):
    """Append an item to a list field via concatenation."""

    def __init__(self, item: Any):
        self.item = item

    def apply(self, old) -> list[Any]:
        return old + [self.item]

class Extend(Reducer[list[Any]]):
    """Extend a list field by appending new items via concatenation."""

    def __init__(self, new: list[Any]):
        self.new = new

    def apply(self, old) -> list[Any]:
        return old + self.new

class Increment(Reducer[int | float]):
    """Add an integer or float value to a numeric field."""

    def __init__(self, new: int | float):
        self.new = new

    def apply(self, old: int | float) -> int | float:
        return old + self.new


class Assign[T](Reducer[T]):
    """Overwrite a field with a fixed value, ignoring the old value."""

    def __init__(self, value: T):
        self.value = value

    def apply(self, old: T) -> T:
        return self.value

class Merge[T](Reducer[dict[T, Any]]):
    """Merge a dict into a dict field via ``{**old, **data}``."""

    def __init__(self, data: dict[T, Any]):
        self.data = data

    def apply(self, old: dict[T, Any]) -> dict[T, Any]:
        return {**old, **self.data}
