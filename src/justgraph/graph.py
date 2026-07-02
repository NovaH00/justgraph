"""Graph blueprint builder. Register nodes, wire edges, compile into an executor."""

from typing import Sequence, Callable, get_args, get_origin, get_type_hints
from inspect import signature

from justgraph.models import State, Node, FieldUpdate, Dependency
from justgraph.compiled import CompiledGraph

class Graph:
    """Blueprint builder. Register nodes, add edges, compile to a CompiledGraph."""

    def __init__(self, state_types: Sequence[type[State]]):
        self._state_types = set(state_types)
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, list[str]] = {}
        self._conditional_edges: dict[str, tuple[Callable, dict[str, str]]] = {}
        self._entry_point: str | None = None

    def add_edge(self, src: str, dst: str) -> Graph:
        if src not in self._nodes:
            raise ValueError(f"Node '{src}' not found")
        if dst not in self._nodes:
            raise ValueError(f"Node '{dst}' not found")
        self._edges.setdefault(src, []).append(dst)
        return self

    def add_conditional_edge(
        self, src: str, router: Callable, path_map: dict[str, str]
    ) -> Graph:
        if src not in self._nodes:
            raise ValueError(f"Node '{src}' not found")
        for target in path_map.values():
            if target not in self._nodes:
                raise ValueError(f"Conditional target '{target}' not found")
        self._conditional_edges[src] = (router, path_map)
        return self

    def set_entry_point(self, name: str) -> Graph:
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        self._entry_point = name
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
            args = get_args(return_type)
            if args and args[0] is not FieldUpdate:
                raise TypeError(f"Node {name} must return a list of FieldUpdate")

            dependencies = []
            for param in sig.parameters.values():
                annotation = hints.get(param.name)
                if annotation is None:
                    raise TypeError(
                        f"Parameter '{param.name}' must have a type annotation."
                    )
                if not isinstance(annotation, type):
                    raise TypeError(
                        f"Parameter '{param.name}' must be annotated with a class."
                    )
                if annotation not in self._state_types:
                    raise TypeError(f"{annotation} is not a registered state type")

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
        if self._entry_point is None:
            raise ValueError("Entry point not set. Call set_entry_point() first.")

        all_targets = set()
        for targets in self._edges.values():
            all_targets.update(targets)
        for _, path_map in self._conditional_edges.values():
            all_targets.update(path_map.values())
        for target in all_targets:
            if target not in self._nodes:
                raise ValueError(f"Edge target '{target}' not found in nodes")

        visited = set()
        in_stack = set()

        def dfs(name):
            if name in in_stack:
                raise ValueError(f"Cycle detected involving node '{name}'")
            if name in visited:
                return
            visited.add(name)
            in_stack.add(name)

            for target in self._edges.get(name, []):
                dfs(target)
            if name in self._conditional_edges:
                _, path_map = self._conditional_edges[name]
                for target in path_map.values():
                    dfs(target)

            in_stack.remove(name)

        dfs(self._entry_point)

        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            conditional_edges=self._conditional_edges,
            entry_point=self._entry_point,
            state_types=self._state_types,
        )

