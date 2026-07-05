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

    To use, add a ctx: Context parameter to your node function.
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
    """Abstract base for field update logic.

    Subclass and implement apply() to define how a field transitions
    from its old value to a new one. Reducers are applied deterministically
    and must be commutative/associative for parallel correctness.

    Example:
        class Multiply(Reducer[int]):
            def __init__(self, factor: int):
                self.factor = factor
            def apply(self, old: int) -> int:
                return old * self.factor
    """

    @abstractmethod
    def apply(self, old: T) -> T: ...

@dataclass
class FieldUpdate:
    """Declares a mutation on a single field of a state type.

    The mutation is not applied immediately - it is collected by the runtime
    and applied via the reducer after the node (or parallel band) completes.

    Attributes:
        state: The State subclass this update targets.
        field: The field name on that state (must exist in annotations).
        reducer: A Reducer instance defining how to transform the old value.

    Example:
        FieldUpdate(ChatState, "messages", Extend(["hello"]))
    """

    state: type
    field: str
    reducer: Reducer

    def __post_init__(self):
        if self.field not in self.state.__annotations__:
            raise ValueError(f"Field '{self.field}' not found in '{self.state.__name__}'")


@dataclass
class Step:
    """A routing + mutation command yielded by a node function.

    Each Step tells the runtime: route execution to target (or terminate
    if None), carrying these updates to apply to the shared state.

    Attributes:
        target: The next node to execute, or None to terminate this branch.
        updates: Optional list of FieldUpdates to apply before routing.

    Example:
        Step("process", updates=[FieldUpdate(ChatState, "counter", Increment(1))])
    """

    target: str | None
    updates: list[FieldUpdate] | None = None

@dataclass_transform()
class StateMeta(type):
    """Applies @dataclass automatically to any State subclass."""
    def __new__(mcs, name, bases, namespace, **kwargs):
        return dataclass(super().__new__(mcs, name, bases, namespace)) # type: ignore

@dataclass_transform()
class State(metaclass=StateMeta):
    """Base class for all state types.

    Subclass and annotate fields - @dataclass is applied automatically
    by StateMeta, so you do not need to add it manually.

    Example:
        class ChatState(State):
            messages: list[str]
            counter: int = 0
    """

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
