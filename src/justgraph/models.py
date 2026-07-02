"""Core types: state containers, reducers, field updates, and node definitions."""

from typing import Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass

class Reducer[T](ABC):
    """A deterministic function that computes a new field value from the old one."""
    @abstractmethod
    def apply(self, old: T) -> T: ...

@dataclass
class FieldUpdate:
    state: type
    field: str
    reducer: Reducer

class State:
    """Base class for all state types. Subclass with @dataclass to define fields."""

@dataclass
class Dependency:
    name: str
    annotation: type[Any]

class Node:
    """A registered graph node with its function and state dependencies."""

    def __init__(
        self,
        name: str,
        fn: Callable[..., list[FieldUpdate]],
        dependencies: list[Dependency],
    ):
        self.name = name
        self.fn = fn
        self.dependencies = dependencies
