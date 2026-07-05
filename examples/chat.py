"""Basic linear graph: chat node -> log node."""
from justgraph import State, FieldUpdate, Step, Graph, Context
from justgraph.reducers import Extend, Increment


class ChatState(State):
    messages: list[str]
    counter: int


graph = Graph([ChatState])

@graph.node("chat", is_entry_point=True)
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

app = graph.compile()
app.invoke([ChatState(messages=["hello"], counter=0)], ctx_config={"user": "alice"})
