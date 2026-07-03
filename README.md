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
- **No edges** — all routing is implicit in return values
- **Parallel fan-out** — multiple `Step`s run branches concurrently
- **N=1 optimization** — linear chains reuse state directly (no copy)
- **Depth limit** — configurable `max_depth` prevents infinite loops
- **Reducers** — `Extend`, `Increment`, `Assign`, `Merge`, or custom
- **Multiple states** — nodes can depend on different state types
- **`Context`** — inspect node name, depth, branch id, and pass runtime config

## Context

Every node can optionally receive a `Context` parameter for introspection:

```python
from justgraph import Context

@graph.node("chat")
def chat(state: ChatState, ctx: Context) -> list[Step]:
    print(f"  node={ctx.node_name}, depth={ctx.depth}")
    print(f"  branch={ctx.branch_id}, config={ctx.config}")
    return [Step("log")]
```

The `Context` object provides: `node_name`, `last_node`, `depth`, `max_depth`, `invoke_id`, `start_time`, `branch_id`, and `config` (a dict passed via `invoke(…, ctx_config={...})`).

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
