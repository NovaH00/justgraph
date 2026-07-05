"""Core types: state containers, reducers, field updates, node definitions, and context."""

from typing import Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import dataclass_transform


@dataclass
class Context:
    """Runtime context injected into node functions.

    Provides metadata about the current execution: what node is running,
    how deep in the graph, UUIDv7 identifiers for tracing, and user config.

    To use, add a ``ctx: Context`` parameter to your node function.
    """

    node_name: str = ""
    last_node: str | None = None
    depth: int = 0
    max_depth: int = 25
    invoke_id: str = ""
    start_time: float = 0.0
    branch_id: str = ""
    config: dict[str, Any] = field(default_factory=dict)

class Reducer[T](ABC):
    """A deterministic function that computes a new field value from the old one."""
    @abstractmethod
    def apply(self, old: T) -> T: ...

@dataclass
class FieldUpdate:
    """Describes a single field mutation on a state: which state, which field, and how to reduce."""

    state: type
    field: str
    reducer: Reducer

    def __post_init__(self):
        if self.field not in self.state.__annotations__:
            raise ValueError(f"Field '{self.field}' not found in '{self.state.__name__}'")


@dataclass
class Step:
    """A routing command returned by a node. Send target and optional state payload."""

    target: str | None
    updates: list[FieldUpdate] | None = None

@dataclass_transform()
class StateMeta(type):
    """A simple meta class that apply dataclass to the subclass of State"""
    def __new__(mcs, name, bases, namespace, **kwargs):
        return dataclass(super().__new__(mcs, name, bases, namespace)) # type: ignore

class State(metaclass=StateMeta):
    """Base class for all state types. Subclass to define fields."""

@dataclass
class Dependency:
    name: str
    annotation: type[Any]

class Node:
    """A registered graph node with its function and state dependencies."""

    def __init__(
        self,
        name: str,
        fn: Callable[..., list[Step]],
        dependencies: list[Dependency],
    ):
        self.name = name
        self.fn = fn
        self.dependencies = dependencies
