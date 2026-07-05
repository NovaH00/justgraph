"""Conditional routing: entry decides which node to go to based on state."""
from justgraph import State, FieldUpdate, Step, Graph
from justgraph.reducers import Increment


class ChatState(State):
    messages: list[str]
    counter: int


graph = Graph([ChatState])

@graph.node("entry")
def entry(state: ChatState) -> list[Step]:
    if state.messages:
        return [Step("log_msg")]
    return [Step("noop")]

@graph.node("log_msg")
def log_msg(state: ChatState) -> list[Step]:
    print(f"  Messages: {state.messages}")
    return [Step("increment")]

@graph.node("increment")
def increment(state: ChatState) -> list[Step]:
    print(f"  Counter: {state.counter}")
    return [Step("counter_updated", [
        FieldUpdate(ChatState, "counter", Increment(1)),
    ])]

@graph.node("counter_updated")
def counter_updated(state: ChatState) -> list[Step]:
    print(f"  Counter after: {state.counter}")
    return []

@graph.node("noop")
def noop() -> list[Step]:
    print("  No messages, nothing to do")
    return []

graph.set_entry_point("entry")
app = graph.compile()

print("--- Invoke with messages ---")
app.invoke([ChatState(messages=["hello", "world"], counter=0)])

print("--- Invoke with empty messages ---")
app.invoke([ChatState(messages=[], counter=0)])
