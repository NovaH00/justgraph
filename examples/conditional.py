"""Conditional edge: route to different nodes based on state."""
from dataclasses import dataclass

from justgraph import State, FieldUpdate, Graph
from justgraph.reducers import Increment


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int


def router(state: ChatState) -> str:
    return "has_msgs" if state.messages else "empty"


def main() -> None:
    graph = Graph([ChatState])

    @graph.node("entry")
    def entry(state: ChatState) -> list[FieldUpdate]:
        return []

    @graph.node("log_msg")
    def log_msg(state: ChatState) -> list[FieldUpdate]:
        print(f"  Messages: {state.messages}")
        return [FieldUpdate(ChatState, "counter", Increment(1))]

    @graph.node("noop")
    def noop(state: ChatState) -> list[FieldUpdate]:
        print("  No messages, nothing to do")
        return []

    (
        graph
        .set_entry_point("entry")
        .add_conditional_edge("entry", router, {
            "has_msgs": "log_msg",
            "empty": "noop",
        })
    )

    app = graph.compile()

    print("--- Invoke with messages ---")
    app.invoke([ChatState(messages=["hello", "world"], counter=0)])

    print("--- Invoke with empty messages ---")
    app.invoke([ChatState(messages=[], counter=0)])


if __name__ == "__main__":
    main()
