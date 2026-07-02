"""Basic linear graph: chat node -> log node."""
from dataclasses import dataclass

from justgraph import State, FieldUpdate, Graph
from justgraph.reducers import ExtendList, Increment


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int


def main() -> None:
    graph = Graph([ChatState])

    @graph.node("chat")
    def chat(state: ChatState) -> list[FieldUpdate]:
        return [
            FieldUpdate(ChatState, "messages", ExtendList(["world"])),
            FieldUpdate(ChatState, "counter", Increment(20)),
        ]

    @graph.node("log")
    def log(state: ChatState) -> list[FieldUpdate]:
        print(state.messages)
        print(state.counter)
        return []

    graph.set_entry_point("chat").add_edge("chat", "log")
    app = graph.compile()
    app.invoke([ChatState(messages=["hello"], counter=0)])


if __name__ == "__main__":
    main()
