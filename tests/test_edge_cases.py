"""Edge-case tests for graph building and execution."""
from dataclasses import dataclass
import pytest

from justgraph import State, FieldUpdate, Graph
from justgraph.reducers import Increment, Replace


@dataclass
class SimpleState(State):
    value: int = 0


@dataclass
class OtherState(State):
    label: str = ""


# ── Graph building edge cases ─────────────────────────────────


def test_duplicate_node_name() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    with pytest.raises(ValueError, match="already registered"):
        @graph.node("a")
        def b(state: SimpleState) -> list[FieldUpdate]:
            return []


def test_edge_to_nonexistent_node() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    with pytest.raises(ValueError, match="not found"):
        graph.add_edge("a", "missing")


def test_edge_from_nonexistent_node() -> None:
    graph = Graph([SimpleState])
    with pytest.raises(ValueError, match="not found"):
        graph.add_edge("missing", "a")


def test_conditional_edge_to_nonexistent_node() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    def router(state: SimpleState) -> str:
        return "x"

    with pytest.raises(ValueError, match="not found"):
        graph.add_conditional_edge("a", router, {"x": "missing"})


def test_entry_point_nonexistent() -> None:
    graph = Graph([SimpleState])
    with pytest.raises(ValueError, match="not found"):
        graph.set_entry_point("missing")


def test_compile_without_entry() -> None:
    graph = Graph([SimpleState])
    with pytest.raises(ValueError, match="Entry point"):
        graph.compile()


def test_dangling_edge_target() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("b")
    def b(state: SimpleState) -> list[FieldUpdate]:
        return []

    graph.set_entry_point("a")
    graph._edges["a"] = ["nonexistent"]  # bypass validation to force dangling edge

    with pytest.raises(ValueError, match="not found in nodes"):
        graph.compile()


def test_dangling_conditional_target() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    graph.set_entry_point("a")
    graph._conditional_edges["a"] = (lambda s: "x", {"x": "missing"})

    with pytest.raises(ValueError, match="not found in nodes"):
        graph.compile()


# ── Cycle detection ──────────────────────────────────────────


def test_self_loop() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    with pytest.raises(ValueError, match="Cycle"):
        graph.set_entry_point("a").add_edge("a", "a").compile()


def test_direct_cycle() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("b")
    def b(state: SimpleState) -> list[FieldUpdate]:
        return []

    with pytest.raises(ValueError, match="Cycle"):
        graph.set_entry_point("a").add_edge("a", "b").add_edge("b", "a").compile()


def test_indirect_cycle() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("b")
    def b(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("c")
    def c(state: SimpleState) -> list[FieldUpdate]:
        return []

    with pytest.raises(ValueError, match="Cycle"):
        (
            graph
            .set_entry_point("a")
            .add_edge("a", "b")
            .add_edge("b", "c")
            .add_edge("c", "a")
            .compile()
        )


def test_conditional_cycle_detected() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("b")
    def b(state: SimpleState) -> list[FieldUpdate]:
        return []

    def router(state: SimpleState) -> str:
        return "loop"

    with pytest.raises(ValueError, match="Cycle"):
        (
            graph
            .set_entry_point("a")
            .add_edge("a", "b")
            .add_conditional_edge("b", router, {"loop": "a"})
            .compile()
        )


# ── Decorator validation ─────────────────────────────────────


def test_missing_return_annotation() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="return type annotation"):

        @graph.node("a")
        def a(state: SimpleState):
            return []


def test_wrong_return_type() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="must return a list"):

        @graph.node("a")
        def a(state: SimpleState) -> int:
            return 0


def test_missing_param_annotation() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="type annotation"):

        @graph.node("a")
        def a(state) -> list[FieldUpdate]:
            return []


def test_unregistered_state_param() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="not a registered state type"):

        @graph.node("a")
        def a(state: OtherState) -> list[FieldUpdate]:
            return []


# ── Execution edge cases ─────────────────────────────────────


def test_single_node_graph() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "value", Replace(42))]

    result = graph.set_entry_point("start").compile().invoke([SimpleState()])
    assert result[0].value == 42


def test_node_returns_empty_list() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    result = graph.set_entry_point("a").compile().invoke([SimpleState(value=10)])
    assert result[0].value == 10


def test_node_returns_none() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return None  # type: ignore

    result = graph.set_entry_point("a").compile().invoke([SimpleState(value=10)])
    assert result[0].value == 10


def test_update_nonexistent_field() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "missing", Replace(1))]

    with pytest.raises(ValueError, match="has no field"):
        graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_update_nonexistent_state() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(OtherState, "label", Replace("x"))]

    with pytest.raises(ValueError, match="not found"):
        graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_invoke_with_missing_state() -> None:
    graph = Graph([SimpleState, OtherState])

    @graph.node("a")
    def a(state: SimpleState) -> list[FieldUpdate]:
        return []

    with pytest.raises(KeyError):
        graph.set_entry_point("a").compile().invoke([])


# ── Multiple states ──────────────────────────────────────────


def test_node_takes_multiple_states() -> None:
    graph = Graph([SimpleState, OtherState])

    @graph.node("combine")
    def combine(s: SimpleState, o: OtherState) -> list[FieldUpdate]:
        return [
            FieldUpdate(SimpleState, "value", Replace(len(o.label))),
            FieldUpdate(OtherState, "label", Replace(f"{o.label}_{s.value}")),
        ]

    result = graph.set_entry_point("combine").compile().invoke([
        SimpleState(value=5),
        OtherState(label="hi"),
    ])

    state_map = {type(s): s for s in result}
    assert state_map[SimpleState].value == 2  # len("hi")
    assert state_map[OtherState].label == "hi_5"


# ── Parallel edge cases ──────────────────────────────────────


def test_parallel_branches_same_field() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "value", Increment(0))]

    @graph.node("add_5")
    def add_5(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "value", Increment(5))]

    @graph.node("add_10")
    def add_10(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "value", Increment(10))]

    @graph.node("collect")
    def collect(state: SimpleState) -> list[FieldUpdate]:
        return []

    (
        graph
        .set_entry_point("start")
        .add_edge("start", "add_5")
        .add_edge("start", "add_10")
        .add_edge("add_5", "collect")
        .add_edge("add_10", "collect")
    )

    result = graph.compile().invoke([SimpleState(value=0)])
    assert result[0].value == 15  # 0 + 5 + 10


def test_parallel_all_return_empty() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "value", Replace(1))]

    @graph.node("nop1")
    def nop1(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("nop2")
    def nop2(state: SimpleState) -> list[FieldUpdate]:
        return []

    @graph.node("end")
    def end(state: SimpleState) -> list[FieldUpdate]:
        return []

    (
        graph
        .set_entry_point("start")
        .add_edge("start", "nop1")
        .add_edge("start", "nop2")
        .add_edge("nop1", "end")
        .add_edge("nop2", "end")
    )

    result = graph.compile().invoke([SimpleState(value=0)])
    assert result[0].value == 1


def test_no_outgoing_edges_terminates() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[FieldUpdate]:
        return [FieldUpdate(SimpleState, "value", Replace(99))]

    result = graph.set_entry_point("start").compile().invoke([SimpleState()])
    assert result[0].value == 99


# ── Run all ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__]))
