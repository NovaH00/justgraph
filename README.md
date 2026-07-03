# justgraph

A lightweight graph-based state machine inspired by LangGraph.

```python
from dataclasses import dataclass
from justgraph import State, FieldUpdate, Step, Graph
from justgraph.reducers import Extend, Increment


@dataclass
class ChatState(State):
    messages: list[str]
    counter: int


graph = Graph([ChatState])

@graph.node("greet")
def greet(state: ChatState) -> list[Step]:
    return [Step("log", [
        FieldUpdate(ChatState, "messages", Extend(["hello"])),
        FieldUpdate(ChatState, "counter", Increment(1)),
    ])]

@graph.node("log")
def log(state: ChatState) -> list[Step]:
    print(state.messages)
    return []

graph.set_entry_point("greet")
app = graph.compile()
app.invoke([ChatState(messages=[], counter=0)])
# ['hello']
```

## Features

- **Nodes** — functions that receive state and return `list[Step]`
- **`Step(target, updates)`** — encapsulate routing and data mutations together
- **No edges** — all routing is implicit in return values (no `add_edge()`)
- **Parallel fan-out** — return multiple `Step`s and branches run concurrently
- **N=1 optimization** — single `Step` with no updates reuses state directly (no copy)
- **Depth limit** — configurable `max_depth` prevents infinite loops in cyclic graphs
- **Reducers** — `Extend`, `Increment`, `Assign`, or custom
- **Multiple states** — nodes can depend on different state types

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

## Examples

```bash
uv run examples/chat.py
uv run examples/conditional.py
```

## Tests

```bash
uv run pytest
```
