"""Compiled graph executor. Runs the DAG with parallel fan-out and state isolation."""

from copy import copy
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence, Callable

from justgraph.models import State, FieldUpdate, Node


class CompiledGraph:
    """Executor produced by Graph.compile(). Runs the DAG with parallel fan-out."""

    def __init__(
        self,
        nodes: dict[str, Node],
        edges: dict[str, list[str]],
        conditional_edges: dict[str, tuple[Callable, dict[str, str]]],
        entry_point: str,
        state_types: set[type[State]],
    ):
        self._nodes = nodes
        self._edges = edges
        self._conditional_edges = conditional_edges
        self._entry_point = entry_point
        self._state_types = state_types

    def invoke(self, initial_states: Sequence[State]) -> list[State]:
        state_map: dict[type[State], State] = {
            type(s): copy(s) for s in initial_states
        }
        missing = self._state_types - state_map.keys()
        if missing:
            names = ", ".join(t.__name__ for t in missing)
            raise ValueError(f"Missing required state(s): {names}")

        active = [self._entry_point]

        while active:
            if len(active) == 1:
                updates = self._run_node(active[0], state_map)
                self._apply_updates(state_map, updates)
            else:
                with ThreadPoolExecutor() as ex:
                    futures = [
                        ex.submit(self._run_node, name, state_map)
                        for name in active
                    ]
                    results = [f.result() for f in futures]
                for updates in results:
                    self._apply_updates(state_map, updates)

            next_active = set()
            for name in active:
                targets = self._resolve_next(state_map, name)
                next_active.update(targets)

            active = list(next_active)

        return list(state_map.values())

    def _run_node(
        self, name: str, state_map: dict[type[State], State]
    ) -> list[FieldUpdate]:
        node = self._nodes[name]
        args = [state_map[dep.annotation] for dep in node.dependencies]
        result = node.fn(*args)
        return [] if result is None else result

    def _apply_updates(
        self, state_map: dict[type[State], State], updates: list[FieldUpdate]
    ) -> None:
        for u in updates:
            state = state_map.get(u.state)
            if state is None:
                raise ValueError(f"State {u.state.__name__} not found")
            if not hasattr(state, u.field):
                raise ValueError(
                    f"State {u.state.__name__} has no field '{u.field}'"
                )
            old = getattr(state, u.field)
            new = u.reducer.apply(old)
            setattr(state, u.field, new)

    def _resolve_next(
        self, state_map: dict[type[State], State], current: str
    ) -> list[str]:
        targets = list(self._edges.get(current, []))
        if current in self._conditional_edges:
            router, path_map = self._conditional_edges[current]
            node = self._nodes[current]
            args = [state_map[dep.annotation] for dep in node.dependencies]
            key = router(*args)
            if key in path_map:
                targets.append(path_map[key])
        seen = set()
        return [t for t in targets if not (t in seen or seen.add(t))]
