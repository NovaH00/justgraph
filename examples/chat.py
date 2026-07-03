"""Basic linear graph: chat node -> log node."""
from dataclasses import dataclass

from justgraph import State, FieldUpdate, Step, Graph
from justgraph.reducers import Extend, Increment


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int


graph = Graph([ChatState])

@graph.node("chat")
def chat() -> list[Step]:
    return [Step("log", [
        FieldUpdate(ChatState, "messages", Extend(["world"])),
        FieldUpdate(ChatState, "counter", Increment(20)),
    ])]

@graph.node("log")
def log(state: ChatState) -> list[Step]:
    print(state.messages)
    print(state.counter)
    return []

graph.set_entry_point("chat")
app = graph.compile()
app.invoke([ChatState(messages=["hello"], counter=0)])
