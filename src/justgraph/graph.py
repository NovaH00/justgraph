"""Graph blueprint builder. Register nodes, compile into an executor."""

from typing import Sequence, get_args, get_origin, get_type_hints
from inspect import signature

from justgraph.models import State, Node, Step, Dependency, Context
from justgraph.compiled import CompiledGraph


class Graph:
    """Blueprint builder. Register nodes, set entry point, compile into an executor.

    Example:
        graph = Graph([ChatState])

        @graph.node("start", is_entry_point=True)
        def start(ctx: Context) -> list[Step]:
            return [Step("end")]

        app = graph.compile()
        result = app.invoke([ChatState()])
    """

    def __init__(self, state_types: Sequence[type[State]]):
        """Initialise a graph blueprint.

        Args:
            state_types: One or more State subclasses that nodes
                can depend on. Every state type used across all nodes
                must be listed here.
        """
        self._state_types = set(state_types)
        self._nodes: dict[str, Node] = {}
        self._entry_point: str | None = None
        self._max_depth: int = 25

    def set_max_depth(self, depth: int) -> Graph:
        """Limit graph traversal depth as a cycle safety net (default 25).

        Args:
            depth: Maximum number of BFS levels before invoke() raises.
        """
        self._max_depth = depth
        return self

    def set_entry_point(self, name: str) -> Graph:
        """Set the starting node for graph execution.

        Equivalent to passing `is_entry_point=True` to the node()
        decorator. Last call wins if both are used.

        Args:
            name: The node name (as passed to node()) where execution begins.
        """
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        self._entry_point = name
        return self

    def _fmt_states(self) -> str:
        return ", ".join(sorted(t.__name__ for t in self._state_types))

    def node(self, name: str, *, is_entry_point: bool = False):
        """Register a graph node via decorator.

        The decorated function must:
        - Have a return annotation of list[Step]
        - Only accept positional parameters (no defaults, *args, **kwargs,
          or keyword-only params)
        - Annotate each parameter with either a registered State subclass
          or Context

        Args:
            name: Unique node name used in set_entry_point() and Step targets.
            is_entry_point: If True, set this node as the entry point
                (equivalent to calling set_entry_point(name) afterwards).
                Last call wins if set multiple times.

        Example:
            @graph.node("greet", is_entry_point=True)
            def greet(state: ChatState, ctx: Context) -> list[Step]:
                return [Step("log", updates=[...])]
        """

        if name in self._nodes:
            raise ValueError(f"'{name}' already registered")

        if is_entry_point:
            self._entry_point = name

        def wrapper(fn):
            sig = signature(fn)
            hints = get_type_hints(fn)
            return_type = hints.get("return")
            if return_type is None:
                raise TypeError(
                    f"Function '{fn.__name__}' must have a return type annotation of `list[Step]`."
                )

            if get_origin(return_type) is not list:
                raise TypeError(f"Node {name} must return a list of Step, got {return_type.__name__}")
            args = get_args(return_type)
            if args and args[0] is not Step:
                raise TypeError(f"Node {name} must return a list of Step, not list[{args[0].__name__}]")

            dependencies = []
            for param in sig.parameters.values():
                if param.default is not param.empty:
                    raise TypeError(
                        f"Parameter '{param.name}' of node '{name}' has a default value, "
                        f"which is not allowed"
                    )
                if param.kind in (
                    param.VAR_POSITIONAL,
                    param.VAR_KEYWORD,
                    param.KEYWORD_ONLY,
                ):
                    kind_str = {
                        param.VAR_POSITIONAL: "*args",
                        param.VAR_KEYWORD: "**kwargs",
                        param.KEYWORD_ONLY: "keyword-only",
                    }[param.kind]
                    raise TypeError(
                        f"Parameter '{param.name}' of node '{name}' is {kind_str}, "
                        f"expected a positional parameter"
                    )

                annotation = hints.get(param.name)
                if annotation is None or not isinstance(annotation, type):
                    raise TypeError(
                        f"Parameter '{param.name}' is missing or has an invalid type annotation"
                    )
                if annotation is Context:
                    dependencies.append(
                        Dependency(name=param.name, annotation=annotation)
                    )
                    continue
                if annotation not in self._state_types:
                    raise TypeError(
                        f"Parameter '{param.name}' has type '{annotation.__name__}', "
                        f"expected one of: justgraph.Context, {self._fmt_states()}"
                    )

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
        """Validate the graph and produce an executable CompiledGraph.

        Raises:
            ValueError: If no entry point has been set via set_entry_point().
        """
        if self._entry_point is None:
            raise ValueError("Entry point not set. Call set_entry_point() first.")

        return CompiledGraph(
            nodes=self._nodes,
            entry_point=self._entry_point,
            state_types=self._state_types,
            max_depth=self._max_depth,
        )
