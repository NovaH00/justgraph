"""Parallel fan-out: entry fans out to three nodes, all converge on collect."""
import time
from dataclasses import dataclass

from justgraph import State, FieldUpdate, Graph
from justgraph.reducers import ExtendList, Increment, Replace


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int
    flag: str


def main() -> None:
    graph = Graph([ChatState])

    @graph.node("entry")
    def entry(state: ChatState) -> list[FieldUpdate]:
        return [
            FieldUpdate(ChatState, "messages", ExtendList(["start"])),
            FieldUpdate(ChatState, "counter", Increment(1)),
        ]

    @graph.node("slow_a")
    def slow_a(state: ChatState) -> list[FieldUpdate]:
        time.sleep(0.2)
        return [FieldUpdate(ChatState, "messages", ExtendList(["a"]))]

    @graph.node("slow_b")
    def slow_b(state: ChatState) -> list[FieldUpdate]:
        time.sleep(0.2)
        return [FieldUpdate(ChatState, "counter", Increment(10))]

    @graph.node("slow_c")
    def slow_c(state: ChatState) -> list[FieldUpdate]:
        time.sleep(0.2)
        return [FieldUpdate(ChatState, "flag", Replace("done"))]

    @graph.node("collect")
    def collect(state: ChatState) -> list[FieldUpdate]:
        print(f"messages: {state.messages}")
        print(f"counter:  {state.counter}")
        print(f"flag:     {state.flag}")
        return []

    (
        graph
        .set_entry_point("entry")
        .add_edge("entry", "slow_a")
        .add_edge("entry", "slow_b")
        .add_edge("entry", "slow_c")
        .add_edge("slow_a", "collect")
        .add_edge("slow_b", "collect")
        .add_edge("slow_c", "collect")
    )

    start = time.perf_counter()
    app = graph.compile()
    app.invoke([ChatState(messages=[], counter=0, flag="")])
    elapsed = time.perf_counter() - start

    print(f"\nElapsed: {elapsed:.3f}s (expected ~0.2s if parallel)")


if __name__ == "__main__":
    main()
