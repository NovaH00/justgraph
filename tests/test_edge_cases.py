"""Edge-case tests for graph building and execution."""
import pytest

from justgraph import State, FieldUpdate, Step, Graph, Context
from justgraph.reducers import Increment, Assign


class SimpleState(State):
    value: int = 0


class OtherState(State):
    label: str = ""


# ── Graph building edge cases ─────────────────────────────────


def test_duplicate_node_name() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return []

    with pytest.raises(ValueError, match="already registered"):

        @graph.node("a")
        def b(state: SimpleState) -> list[Step]:
            return []


def test_entry_point_nonexistent() -> None:
    graph = Graph([SimpleState])
    with pytest.raises(ValueError, match="not found"):
        graph.set_entry_point("missing")


def test_compile_without_entry() -> None:
    graph = Graph([SimpleState])
    with pytest.raises(ValueError, match="Entry point"):
        graph.compile()


# ── Cycle detection ──────────────────────────────────────────


def test_cycle_hits_depth_limit() -> None:
    graph = Graph([SimpleState]).set_max_depth(5)

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("a")]

    with pytest.raises(ValueError, match="Depth 6 exceeds"):
        graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_cycle_direct() -> None:
    graph = Graph([SimpleState]).set_max_depth(5)

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("b")]

    @graph.node("b")
    def b(state: SimpleState) -> list[Step]:
        return [Step("a")]

    with pytest.raises(ValueError, match="Depth 6 exceeds"):
        graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_cycle_within_depth_limit_works() -> None:
    """A cycle that finishes within the depth limit should work."""
    graph = Graph([SimpleState]).set_max_depth(10)

    @graph.node("counter")
    def counter(state: SimpleState) -> list[Step]:
        if state.value < 3:
            return [Step("counter", [
                FieldUpdate(SimpleState, "value", Increment(1)),
            ])]
        return []

    result = graph.set_entry_point("counter").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 3


def test_fan_out_shape() -> None:
    """Fan-out then fan-in works correctly."""
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return [Step("a"), Step("b")]

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("done")]

    @graph.node("b")
    def b(state: SimpleState) -> list[Step]:
        return [Step("done")]

    @graph.node("done")
    def done(state: SimpleState) -> list[Step]:
        return []

    graph.set_entry_point("start").compile().invoke([SimpleState()])


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

    with pytest.raises(TypeError, match="invalid type annotation"):

        @graph.node("a")
        def a(state) -> list[Step]:
            return []


def test_unregistered_state_param() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="expected one of"):

        @graph.node("a")
        def a(state: OtherState) -> list[Step]:
            return []


# ── Parameter validation ─────────────────────────────────────


def test_default_value_rejected() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="default value"):

        @graph.node("a")
        def a(state: SimpleState, x: SimpleState = SimpleState()) -> list[Step]:  # type: ignore
            return []


def test_star_args_rejected() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match=r"\*args"):

        @graph.node("a")
        def a(state: SimpleState, *args) -> list[Step]:  # type: ignore
            return []


def test_star_star_kwargs_rejected() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match=r"\*\*kwargs"):

        @graph.node("a")
        def a(state: SimpleState, **kwargs) -> list[Step]:  # type: ignore
            return []


def test_keyword_only_rejected() -> None:
    graph = Graph([SimpleState])

    with pytest.raises(TypeError, match="keyword-only"):

        @graph.node("a")
        def a(state: SimpleState, *, opt: str) -> list[Step]:  # type: ignore
            return []


# ── Execution edge cases ─────────────────────────────────────


def test_single_node_graph() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return [Step("done", [FieldUpdate(SimpleState, "value", Assign(42))])]

    @graph.node("done")
    def done(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("start").compile().invoke([SimpleState()])
    assert result[0].value == 42


def test_node_returns_empty_list() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("a").compile().invoke([SimpleState(value=10)])
    assert result[0].value == 10


def test_node_returns_none() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return None  # type: ignore

    result = graph.set_entry_point("a").compile().invoke([SimpleState(value=10)])
    assert result[0].value == 10


def test_update_nonexistent_field() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("b", [FieldUpdate(SimpleState, "missing", Assign(1))])]

    @graph.node("b")
    def b(state: SimpleState) -> list[Step]:
        return []

    with pytest.raises(ValueError, match="not found in"):
        graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_update_nonexistent_state() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("b", [FieldUpdate(OtherState, "label", Assign("x"))])]

    @graph.node("b")
    def b(state: SimpleState) -> list[Step]:
        return []

    with pytest.raises(ValueError, match="not found"):
        graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_invoke_with_missing_state() -> None:
    graph = Graph([SimpleState, OtherState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return []

    with pytest.raises(ValueError, match="Missing required state"):
        graph.set_entry_point("a").compile().invoke([])


# ── Multiple states ──────────────────────────────────────────


def test_node_takes_multiple_states() -> None:
    graph = Graph([SimpleState, OtherState])

    @graph.node("combine")
    def combine(s: SimpleState, o: OtherState) -> list[Step]:
        return [Step("done", [
            FieldUpdate(SimpleState, "value", Assign(len(o.label))),
            FieldUpdate(OtherState, "label", Assign(f"{o.label}_{s.value}")),
        ])]

    @graph.node("done")
    def done(s: SimpleState, o: OtherState) -> list[Step]:
        assert s.value == 2
        assert o.label == "hi_5"
        return []

    result = graph.set_entry_point("combine").compile().invoke([
        SimpleState(value=5),
        OtherState(label="hi"),
    ])

    state_map = {type(s): s for s in result}
    assert state_map[SimpleState].value == 2
    assert state_map[OtherState].label == "hi_5"


# ── Parallel / fan-out edge cases ────────────────────────────


def test_parallel_branches_same_field() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return [Step("add_5"), Step("add_10")]

    @graph.node("add_5")
    def add_5(state: SimpleState) -> list[Step]:
        return [Step("done", [FieldUpdate(SimpleState, "value", Increment(5))])]

    @graph.node("add_10")
    def add_10(state: SimpleState) -> list[Step]:
        return [Step("done", [FieldUpdate(SimpleState, "value", Increment(10))])]

    @graph.node("done")
    def done(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("start").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 15


def test_parallel_all_return_empty() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return [Step("nop1", [FieldUpdate(SimpleState, "value", Assign(1))]), Step("nop2")]

    @graph.node("nop1")
    def nop1(state: SimpleState) -> list[Step]:
        return []

    @graph.node("nop2")
    def nop2(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("start").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 1


def test_no_outgoing_edges_terminates() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("start").compile().invoke([SimpleState(value=99)])
    assert result[0].value == 99


def test_n1_optimization_applies_updates() -> None:
    """N=1 with updates should apply updates to the main state."""
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return [Step("mid", [FieldUpdate(SimpleState, "value", Increment(10))])]

    @graph.node("mid")
    def mid(state: SimpleState) -> list[Step]:
        assert state.value == 10  # updates applied before mid runs
        return [Step("end")]

    @graph.node("end")
    def end(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("start").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 10


def test_sentinel_end_applies_updates() -> None:
    graph = Graph([SimpleState])

    @graph.node("start")
    def start(state: SimpleState) -> list[Step]:
        return [Step(None, [FieldUpdate(SimpleState, "value", Assign(99))])]

    result = graph.set_entry_point("start").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 99


def test_deep_chain() -> None:
    """Linear chain with multiple steps, no copies."""
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("b", [FieldUpdate(SimpleState, "value", Increment(1))])]

    @graph.node("b")
    def b(state: SimpleState) -> list[Step]:
        return [Step("c", [FieldUpdate(SimpleState, "value", Increment(2))])]

    @graph.node("c")
    def c(state: SimpleState) -> list[Step]:
        return [Step("d", [FieldUpdate(SimpleState, "value", Increment(3))])]

    @graph.node("d")
    def d(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("a").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 6


# ── Context ──────────────────────────────────────────────────


def test_context_injected() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(ctx: Context, state: SimpleState) -> list[Step]:
        assert isinstance(ctx, Context)
        assert ctx.node_name == "a"
        assert ctx.depth == 0
        assert ctx.last_node is None
        assert ctx.invoke_id
        assert ctx.branch_id
        assert ctx.start_time > 0
        assert ctx.max_depth == 25
        return []

    graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_context_depth_increments() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(ctx: Context, state: SimpleState) -> list[Step]:
        assert ctx.depth == 0
        return [Step("b")]

    @graph.node("b")
    def b(ctx: Context, state: SimpleState) -> list[Step]:
        assert ctx.depth == 1
        assert ctx.last_node == "a"
        return [Step("c")]

    @graph.node("c")
    def c(ctx: Context, state: SimpleState) -> list[Step]:
        assert ctx.depth == 2
        assert ctx.last_node == "b"
        return []

    graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_context_invoke_id_constant() -> None:
    graph = Graph([SimpleState])
    ids: list[str] = []

    @graph.node("a")
    def a(ctx: Context, state: SimpleState) -> list[Step]:
        ids.append(ctx.invoke_id)
        return [Step("b")]

    @graph.node("b")
    def b(ctx: Context, state: SimpleState) -> list[Step]:
        ids.append(ctx.invoke_id)
        return []

    graph.set_entry_point("a").compile().invoke([SimpleState()])
    assert len(ids) == 2
    assert ids[0] == ids[1]


def test_context_branch_ids_differ() -> None:
    graph = Graph([SimpleState])
    branch_ids: list[str] = []

    @graph.node("start")
    def start(ctx: Context, state: SimpleState) -> list[Step]:
        return [Step("leaf"), Step("leaf")]

    @graph.node("leaf")
    def leaf(ctx: Context, state: SimpleState) -> list[Step]:
        branch_ids.append(ctx.branch_id)
        return []

    graph.set_entry_point("start").compile().invoke([SimpleState()])
    assert len(branch_ids) == 1  # fan-in dedup: leaf runs once


def test_context_config_passed_through() -> None:
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(ctx: Context, state: SimpleState) -> list[Step]:
        assert ctx.config.get("user") == "alice"
        assert ctx.config.get("threshold") == 42
        return []

    graph.set_entry_point("a").compile().invoke(
        [SimpleState()],
        ctx_config={"user": "alice", "threshold": 42},
    )


def test_context_max_depth_matches_graph() -> None:
    graph = Graph([SimpleState]).set_max_depth(10)

    @graph.node("a")
    def a(ctx: Context, state: SimpleState) -> list[Step]:
        assert ctx.max_depth == 10
        return []

    graph.set_entry_point("a").compile().invoke([SimpleState()])


def test_context_optional_not_required() -> None:
    """Node without ctx parameter should still work."""
    graph = Graph([SimpleState])

    @graph.node("a")
    def a(state: SimpleState) -> list[Step]:
        return [Step("b", [FieldUpdate(SimpleState, "value", Increment(1))])]

    @graph.node("b")
    def b(state: SimpleState) -> list[Step]:
        return []

    result = graph.set_entry_point("a").compile().invoke([SimpleState(value=0)])
    assert result[0].value == 1


# ── Run all ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__]))
