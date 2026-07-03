"""Basic linear graph: chat node -> log node."""
from dataclasses import dataclass

from justgraph import State, FieldUpdate, Step, Graph, Context
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
def log(state: ChatState, ctx: Context) -> list[Step]:
    print(f"[{ctx.node_name}] depth={ctx.depth} id={ctx.branch_id[:8]}")
    print(f"  messages: {state.messages}")
    print(f"  counter:  {state.counter}")
    return []

graph.set_entry_point("chat")
app = graph.compile()
app.invoke([ChatState(messages=["hello"], counter=0)], ctx_config={"user": "alice"})
