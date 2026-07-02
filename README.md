# justgraph

A lightweight graph-based state machine.

```python
from dataclasses import dataclass
from justgraph import State, FieldUpdate, Graph
from justgraph.reducers import ExtendList, Increment


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int


graph = Graph([ChatState])

@graph.node("greet")
def greet(state: ChatState) -> list[FieldUpdate]:
    return [
        FieldUpdate(ChatState, "messages", ExtendList(["hello"])),
        FieldUpdate(ChatState, "counter", Increment(1)),
    ]

@graph.node("log")
def log(state: ChatState) -> list[FieldUpdate]:
    print(state.messages)
    return []

graph.set_entry_point("greet").add_edge("greet", "log")
app = graph.compile()
app.invoke([ChatState(messages=[], counter=0)])
# ['hello']
```

## Custom Reducers

Subclass `Reducer[T]` and implement `apply(old: T) -> T`:

```python
from justgraph import Reducer, FieldUpdate

class Multiply(Reducer[int]):
    def __init__(self, factor: int):
        self._factor = factor
    def apply(self, old: int) -> int:
        return old * self._factor

# Use it like any built-in reducer
FieldUpdate(ChatState, "counter", Multiply(3))
```

## Features

- **Nodes** — functions that receive state and return `FieldUpdate`s
- **Edges** — wire nodes into a directed graph
- **Conditional edges** — route based on state
- **Parallel fan-out** — branches run concurrently via `ThreadPoolExecutor`
- **Reducers** — `ExtendList`, `Increment`, `Replace`, or custom
- **Multiple states** — nodes can depend on different state types

## Examples

```bash
uv run examples/chat.py
uv run examples/fan_out.py
uv run examples/conditional.py
```

## Tests

```bash
uv run pytest
```
