"""Compiled graph executor. Runs the DAG via BFS level-order traversal."""

from copy import copy
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence, Any
import uuid
import time

from justgraph.models import State, FieldUpdate, Step, Node, Context


NodeName = str
BranchID = str
SourceKey = tuple[NodeName, BranchID]
QueueEntry = tuple[NodeName, NodeName | None, BranchID]


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
    """Executor produced by Graph.compile(). Runs the graph via BFS level-order traversal."""

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

    def invoke(
        self,
        initial_states: Sequence[State],
        ctx_config: dict[str, Any] | None = None,
    ) -> list[State]:
        """Execute the graph and return the final states.

        Traverses the graph in BFS level-order. All nodes at the same
        depth run in parallel (via ThreadPoolExecutor); their updates
        are merged into the shared state before the next level begins.
        This guarantees fan-in synchronisation: a downstream node sees
        updates from all upstream branches.

        Args:
            initial_states: One instance per registered State type, in any
                order. Must include every type declared in Graph(state_types=...).
            ctx_config: Optional user-defined dict accessible via ctx.config
                inside node functions.

        Returns:
            A list of mutated state instances in the same order/types as
            registered in Graph(state_types=...).

        Raises:
            ValueError: If any registered state type is missing from
                initial_states, or if traversal exceeds max_depth.
        """
        state_map: dict[type[State], State] = {
            type(s): copy(s) for s in initial_states
        }
        missing = self._state_types - state_map.keys()
        if missing:
            names = ", ".join(t.__name__ for t in missing)
            raise ValueError(f"Missing required state(s): {names}")

        invoke_id = str(uuid.uuid7())
        start_time = time.time()
        config = ctx_config or {}

        # BFS queue: (node_name, last_node, branch_id)
        queue: list[QueueEntry] = [
            (self._entry_point, None, invoke_id),
        ]
        depth = 0

        while queue:
            if depth > self._max_depth:
                raise ValueError(
                    f"Depth {depth} exceeds max_depth {self._max_depth}"
                )

            # Run all nodes in this band
            def run_node(
                name: NodeName, prev_node: NodeName | None, branch: BranchID
            ) -> list[Step]:
                if name not in self._nodes:
                    source = f" (targeted by '{prev_node}')" if prev_node else ""
                    raise ValueError(
                        f"Node '{name}' not found{source}"
                    )
                node = self._nodes[name]
                try:
                    ctx = Context(
                        node_name=name,
                        last_node=prev_node,
                        depth=depth,
                        max_depth=self._max_depth,
                        invoke_id=invoke_id,
                        start_time=start_time,
                        branch_id=branch,
                        config=config,
                    )
                    args = [
                        ctx if dep.annotation is Context else state_map[dep.annotation]
                        for dep in node.dependencies
                    ]
                    return node.fn(*args) or []
                except Exception as e:
                    raise type(e)(
                        f"[node '{name}'] {e}"
                    ) from e

            if len(queue) == 1:
                steps_batch = [run_node(*queue[0])]
            else:
                with ThreadPoolExecutor() as ex:
                    futures = [ex.submit(run_node, *item) for item in queue]
                    steps_batch = [f.result() for f in futures]

            # Collect updates and next targets from all nodes in this band
            level_updates: list[FieldUpdate] = []

            # Track (target → set of (source_name, branch_id)) to distinguish
            # fan-out (same source, run multiple) from fan-in (different sources, dedup)
            target_sources: dict[NodeName, set[SourceKey]] = {}
            target_counts: dict[NodeName, int] = {}
            target_order: dict[NodeName, int] = {}
            idx = 0

            for (name, _, branch), steps in zip(queue, steps_batch):
                for step in steps:
                    if step.updates:
                        level_updates.extend(step.updates)
                    if step.target is not None:
                        if step.target not in target_sources:
                            target_order[step.target] = idx
                            idx += 1
                        target_sources.setdefault(step.target, set()).add((name, branch))
                        target_counts[step.target] = target_counts.get(step.target, 0) + 1

            # Apply all updates to the shared state_map
            try:
                _apply_updates(state_map, level_updates)
            except Exception as e:
                band_nodes = ", ".join(name for name, _, _ in queue)
                raise type(e)(
                    f"[band: {band_nodes}] {e}"
                ) from e

            # Build next band: preserve multiplicity from same source,
            # deduplicate across different sources (fan-in)
            next_queue: list[QueueEntry] = []
            for target in sorted(target_sources, key=lambda t: target_order[t]):
                sources = target_sources[target]
                if len(sources) == 1:
                    source_name = next(iter(sources))[0]
                    for _ in range(target_counts[target]):
                        next_queue.append((target, source_name, str(uuid.uuid7())))
                else:
                    next_queue.append((target, None, str(uuid.uuid7())))

            # Prepare next band
            queue = next_queue
            depth += 1

        return list(state_map.values())
