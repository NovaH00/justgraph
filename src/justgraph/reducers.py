"""Built-in reducers for common field update patterns."""

from typing import Any

from justgraph.models import Reducer

class ExtendList(Reducer[list[Any]]):
    def __init__(self, new: list[Any]):
        self.new = new
    def apply(self, old) -> list[Any]:
        return old + self.new


class Increment(Reducer[int]):
    def __init__(self, new: int):
        self.new = new
    def apply(self, old):
        return old + self.new


class Replace[T](Reducer[T]):
    def __init__(self, value: T):
        self._value = value
    def apply(self, old: T) -> T:
        return self._value


