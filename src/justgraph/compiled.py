"""Compiled graph executor. Runs the DAG via Step-based traversal."""

from copy import copy
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

from justgraph.models import State, FieldUpdate, Step, Node


def _apply_updates(
    state_map: dict[type[State], State], updates: list[FieldUpdate] | None
) -> None:
    """Apply a list of FieldUpdates to the given state map."""
    if not updates:
        return
    for u in updates:
        state = state_map.get(u.state)
        if state is None:
            raise ValueError(f"State {u.state.__name__} not found")
        if not hasattr(state, u.field):
            raise ValueError(f"State {u.state.__name__} has no field '{u.field}'")
        old = getattr(state, u.field)
        setattr(state, u.field, u.reducer.apply(old))


class CompiledGraph:
    """Executor produced by ``Graph.compile()``. Runs the graph via Step-based traversal."""

    def __init__(
        self,
        nodes: dict[str, Node],
        entry_point: str,
        state_types: set[type[State]],
        max_depth: int = 25,
    ):
        self._nodes = nodes
        self._entry_point = entry_point
        self._state_types = state_types
        self._max_depth = max_depth

    def invoke(self, initial_states: Sequence[State]) -> list[State]:
        """Execute the graph with the given initial states and return the final states."""
        state_map: dict[type[State], State] = {
            type(s): copy(s) for s in initial_states
        }
        missing = self._state_types - state_map.keys()
        if missing:
            names = ", ".join(t.__name__ for t in missing)
            raise ValueError(f"Missing required state(s): {names}")

        updates = self._traverse(self._entry_point, state_map, 0)
        _apply_updates(state_map, updates)
        return list(state_map.values())

    def _traverse(
        self,
        current: str,
        state_map: dict[type[State], State],
        depth: int,
    ) -> list[FieldUpdate]:
        """Recursively walk the graph, collecting FieldUpdates from all branches."""
        if depth > self._max_depth:
            raise ValueError(
                f"Recursion depth exceeded ({depth} > {self._max_depth})"
            )

        node = self._nodes[current]
        args = [state_map[dep.annotation] for dep in node.dependencies]
        steps = node.fn(*args) or []

        if not steps:
            return []

        if len(steps) == 1:
            step = steps[0]
            if step.target is None:
                return step.updates or []
            if not step.updates:
                return self._traverse(step.target, state_map, depth + 1)
            branch_map = {t: copy(s) for t, s in state_map.items()}
            _apply_updates(branch_map, step.updates)
            deeper = self._traverse(step.target, branch_map, depth + 1)
            return step.updates + deeper

        def process_step(step: Step) -> list[FieldUpdate]:
            if step.target is None:
                return step.updates or []
            branch_map = {t: copy(s) for t, s in state_map.items()}
            _apply_updates(branch_map, step.updates)
            deeper = self._traverse(step.target, branch_map, depth + 1)
            return (step.updates or []) + deeper

        with ThreadPoolExecutor() as ex:
            futures = [ex.submit(process_step, s) for s in steps]
            results = [f.result() for f in futures]

        return [u for r in results for u in r]
