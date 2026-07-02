from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Callable, Sequence, Any, TypedDict, get_type_hints, get_origin, get_args
from dataclasses import is_dataclass, dataclass
from inspect import Signature, signature, Parameter

class Reducer[T](ABC):
    @abstractmethod
    def apply(self, old: T) -> T: ...

@dataclass
class FieldUpdate:
    state: type
    field: str
    reducer: Reducer


class State:
    pass

@dataclass
class Dependency:
    name: str
    annotation: type[Any]

class Node:
    def __init__(
        self,
        name: str,
        fn: Callable[..., list[FieldUpdate]],
        dependencies: list[Dependency],
    ):
        self.name = name
        self.fn = fn
        self.dependencies = dependencies

class Graph:
    def __init__(self, initial_states: Sequence[State]):
        self._states: dict[type[State], State] = {
            type(state): state
            for state in initial_states
        }
        self._nodes: dict[str, Node] = {}

    def _resolve_dep(self, dep: Dependency) -> State:
        typ = dep.annotation

        return self._states[typ]

    def _build_args(self, node: Node) -> list[State]:
        return [self._resolve_dep(dep) for dep in node.dependencies]

    def _execute_node(self, node_name: str) -> list[FieldUpdate]:
        node = self._nodes.get(node_name)
        if node is None:
            raise ValueError(f"Node {node_name} not found")

        args = self._build_args(node)

        result = node.fn(*args)
        if result is None:
            raise ValueError(f"Node '{node_name}' doesnt perform any updates. Use 'return []' for no-update")

        return result

    def run_node(self, node_name: str) -> Graph:
        field_updates = self._execute_node(node_name)

        for update in field_updates:
            state = self._states.get(update.state)
            if state is None:
                raise ValueError(f"State {update.state.__name__} does not exist for update")

            if not hasattr(state, update.field):
                raise ValueError(f"State {update.state.__name__} does not contain the field '{update.field}'")

            old = getattr(state, update.field)
            new = update.reducer.apply(old)
            setattr(state, update.field, new)

        return self

    def node(self, name: str):
        if name in self._nodes:
            raise ValueError(f"'{name}' already registered")

        def wrapper(fn):
            sig = signature(fn)
            hints = get_type_hints(fn)
            return_type = hints.get("return")
            if return_type is None:
                raise TypeError(
                    f"Function '{fn.__name__}' must have a return type annotation."
                )

            if get_origin(return_type) is not list:
                raise TypeError(f"Node {name} must return a list of FieldUpdate")
            else:
                for inner_type in get_args(return_type):
                    if inner_type is not FieldUpdate:
                        raise TypeError(f"Node {name} must return a list of FieldUpdate")

            dependencies = []
            for param in sig.parameters.values():
                annotation = hints.get(param.name)
                if annotation is None:
                    raise TypeError(f"Parameter '{param.name}' must have a type annotation.")

                if not isinstance(annotation, type):
                    raise TypeError(
                        f"Parameter '{param.name}' must be annotated with a class."
                    )

                if annotation not in self._states:
                    raise TypeError(f"{annotation} is not registered in the graph")

                dependencies.append(
                    Dependency(
                        name=param.name,
                        annotation=annotation,
                    )
                )

            self._nodes[name] = Node(name, fn, dependencies)

            return fn
        return wrapper

    def compile(self) -> CompiledGraph:
        return CompiledGraph()

class CompiledGraph:
    pass

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

@dataclass
class ChatState(State):
    messages: list[str]
    counter: int


chat_state = ChatState(messages=["hello"], counter=0)
graph = Graph([chat_state])

@graph.node("chat")
def chat(state: ChatState) -> list[FieldUpdate]:
    return [
        FieldUpdate(ChatState, "messages", ExtendList(["world"])),
        FieldUpdate(ChatState, "counter", Increment(20))
    ]

@graph.node("log")
def log(state: ChatState) -> list[FieldUpdate]:
    print(state.messages)
    print(state.counter)
    return []

graph.run_node("chat").run_node("log")
