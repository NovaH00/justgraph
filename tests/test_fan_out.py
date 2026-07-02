import time
from dataclasses import dataclass

from justgraph import State, FieldUpdate, Graph
from justgraph.reducers import ExtendList, Increment, Replace


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int
    flag: str


def test_basic_fan_out() -> None:
    graph = Graph([ChatState])

    @graph.node("entry")
    def entry(state: ChatState) -> list[FieldUpdate]:
        return [
            FieldUpdate(ChatState, "messages", ExtendList(["start"])),
            FieldUpdate(ChatState, "counter", Increment(1)),
        ]

    @graph.node("append_a")
    def append_a(state: ChatState) -> list[FieldUpdate]:
        time.sleep(0.2)
        return [FieldUpdate(ChatState, "messages", ExtendList(["a"]))]

    @graph.node("inc_counter")
    def inc_counter(state: ChatState) -> list[FieldUpdate]:
        time.sleep(0.2)
        return [FieldUpdate(ChatState, "counter", Increment(10))]

    @graph.node("set_flag")
    def set_flag(state: ChatState) -> list[FieldUpdate]:
        time.sleep(0.2)
        return [FieldUpdate(ChatState, "flag", Replace("done"))]

    @graph.node("collect")
    def collect(state: ChatState) -> list[FieldUpdate]:
        return []

    (
        graph
        .set_entry_point("entry")
        .add_edge("entry", "append_a")
        .add_edge("entry", "inc_counter")
        .add_edge("entry", "set_flag")
        .add_edge("append_a", "collect")
        .add_edge("inc_counter", "collect")
        .add_edge("set_flag", "collect")
    )

    app = graph.compile()

    start = time.perf_counter()
    result = app.invoke([ChatState(messages=[], counter=0, flag="")])
    elapsed = time.perf_counter() - start

    state = result[0]
    assert state.messages == ["start", "a"], f"expected [start, a], got {state.messages}"
    assert state.counter == 11, f"expected 11, got {state.counter}"
    assert state.flag == "done", f"expected done, got {state.flag}"
    assert elapsed < 0.35, f"parallel too slow: {elapsed:.3f}s"

    print("[PASS] test_basic_fan_out (elapsed={:.3f}s)".format(elapsed))


def test_linear_no_fan_out() -> None:
    graph = Graph([ChatState])

    @graph.node("step1")
    def step1(state: ChatState) -> list[FieldUpdate]:
        return [FieldUpdate(ChatState, "counter", Increment(1))]

    @graph.node("step2")
    def step2(state: ChatState) -> list[FieldUpdate]:
        return [FieldUpdate(ChatState, "counter", Increment(2))]

    @graph.node("step3")
    def step3(state: ChatState) -> list[FieldUpdate]:
        return [FieldUpdate(ChatState, "counter", Increment(3))]

    (
        graph
        .set_entry_point("step1")
        .add_edge("step1", "step2")
        .add_edge("step2", "step3")
    )

    result = graph.compile().invoke([ChatState(messages=[], counter=0, flag="")])
    assert result[0].counter == 6, f"expected 6, got {result[0].counter}"
    print("[PASS] test_linear_no_fan_out")


if __name__ == "__main__":
    test_linear_no_fan_out()
    test_basic_fan_out()
    print("\nAll tests passed.")
