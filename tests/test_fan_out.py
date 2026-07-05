import time

from justgraph import State, FieldUpdate, Step, Graph
from justgraph.reducers import Extend, Increment, Assign


class ChatState(State):
    messages: list[str]
    counter: int
    flag: str


def test_basic_fan_out() -> None:
    graph = Graph([ChatState])

    @graph.node("entry")
    def entry(state: ChatState) -> list[Step]:
        return [Step("append_a"), Step("inc_counter"), Step("set_flag")]

    @graph.node("append_a")
    def append_a(state: ChatState) -> list[Step]:
        time.sleep(0.2)
        return [Step("collect", [
            FieldUpdate(ChatState, "messages", Extend(["a"])),
        ])]

    @graph.node("inc_counter")
    def inc_counter(state: ChatState) -> list[Step]:
        time.sleep(0.2)
        return [Step("collect", [
            FieldUpdate(ChatState, "counter", Increment(10)),
        ])]

    @graph.node("set_flag")
    def set_flag(state: ChatState) -> list[Step]:
        time.sleep(0.2)
        return [Step("collect", [
            FieldUpdate(ChatState, "flag", Assign("done")),
        ])]

    @graph.node("collect")
    def collect(state: ChatState) -> list[Step]:
        return []

    graph.set_entry_point("entry")
    app = graph.compile()

    start = time.perf_counter()
    result = app.invoke([ChatState(messages=["start"], counter=0, flag="")])
    elapsed = time.perf_counter() - start

    state = result[0]
    assert state.messages == ["start", "a"], f"expected [start, a], got {state.messages}"
    assert state.counter == 10, f"expected 10, got {state.counter}"
    assert state.flag == "done", f"expected 'done', got {state.flag}"
    assert elapsed < 0.35, f"parallel too slow: {elapsed:.3f}s"

    print(f"[PASS] test_basic_fan_out (elapsed={elapsed:.3f}s)")


def test_linear_no_fan_out() -> None:
    graph = Graph([ChatState])

    @graph.node("step1")
    def step1(state: ChatState) -> list[Step]:
        return [Step("step2", [
            FieldUpdate(ChatState, "counter", Increment(1)),
        ])]

    @graph.node("step2")
    def step2(state: ChatState) -> list[Step]:
        return [Step("step3", [
            FieldUpdate(ChatState, "counter", Increment(2)),
        ])]

    @graph.node("step3")
    def step3(state: ChatState) -> list[Step]:
        return [Step("done", [
            FieldUpdate(ChatState, "counter", Increment(3)),
        ])]

    @graph.node("done")
    def done(state: ChatState) -> list[Step]:
        return []

    result = graph.set_entry_point("step1").compile().invoke([
        ChatState(messages=[], counter=0, flag=""),
    ])
    assert result[0].counter == 6, f"expected 6, got {result[0].counter}"
    print("[PASS] test_linear_no_fan_out")


if __name__ == "__main__":
    test_linear_no_fan_out()
    test_basic_fan_out()
    print("\nAll tests passed.")
