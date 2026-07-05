# justgraph

A lightweight graph-based state machine.

## Install
With `pip`
```bash
pip install justgraph
```

With `uv`
```bash
uv add justgraph
```

```python
from justgraph import State, FieldUpdate, Step, Graph
from justgraph.reducers import Extend, Increment


class ChatState(State):
    messages: list[str]
    counter: int


graph = Graph([ChatState])

@graph.node("greet", is_entry_point=True)
def greet(state: ChatState) -> list[Step]:
    return [Step("log", [
        FieldUpdate(ChatState, "messages", Extend(["hello"])),
        FieldUpdate(ChatState, "counter", Increment(1)),
    ])]

@graph.node("log")
def log(state: ChatState) -> list[Step]:
    print(state.messages)
    return []

app = graph.compile()
app.invoke([ChatState(messages=[], counter=0)])
# ['hello']
```

## Step API

No explicit edges. Each node returns `list[Step]` — each Step carries a target and optional updates:

```python
Step("next_node")                          # route only
Step("next_node", updates=[...])           # route + mutate
Step(None)                                 # terminate this branch
Step(None, updates=[...])                  # mutate then terminate
```

Returning multiple Steps fans out in parallel:

```python
@graph.node("split")
def split(state: ChatState) -> list[Step]:
    return [
        Step("slow_a", updates=[...]),
        Step("slow_b", updates=[...]),
        Step("slow_c", updates=[...]),
    ]
```

All three branches run concurrently via `ThreadPoolExecutor`. Updates are merged to the shared state before the next BFS level.

## Context

Every node can optionally receive a `Context` parameter:

```python
from justgraph import Context

@graph.node("chat", is_entry_point=True)
def chat(state: ChatState, ctx: Context) -> list[Step]:
    print(f"  node={ctx.node_name}, depth={ctx.depth}")
    print(f"  branch={ctx.branch_id}, config={ctx.config}")
    return [Step(None)]
```

Fields: `node_name`, `last_node`, `depth`, `max_depth`, `invoke_id`, `start_time`, `branch_id`, `config` (a dict passed via `invoke(…, ctx_config={...})`).

## Custom Reducers

Subclass `Reducer[T]` and implement `apply(old: T) -> T`:

```python
from justgraph import Reducer, FieldUpdate

class Multiply(Reducer[int]):
    def __init__(self, factor: int):
        self._factor = factor
    def apply(self, old: int) -> int:
        return old * self._factor

FieldUpdate(ChatState, "counter", Multiply(3))
```

## Features

- **No edges** — all routing is implicit in return values
- **Parallel fan-out** — multiple Steps run branches concurrently
- **Fan-in synchronisation** — BFS level-order guarantees downstream nodes see all branch updates
- **Depth limit** — `graph.set_max_depth(n)` prevents infinite loops (default 25)
- **Reducers** — `Extend`, `Increment`, `Assign`, `Merge`, or custom
- **Multiple states** — nodes can depend on different state types
- **Runtime context** — inspect node name, depth, branch id, and pass config
- **State not required** — a node with no state parameters only receives `Context`

## Examples

```bash
uv run examples/chat.py
uv run examples/conditional.py
```

## Tests

```bash
uv run pytest
```
