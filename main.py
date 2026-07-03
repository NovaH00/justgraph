from justgraph import Context, Graph, Step

graph = Graph([])

@graph.node("a")
def a(ctx: Context) -> list[Step]:
    print(ctx)
    return []


graph.set_entry_point("a")
compiled = graph.compile()
compiled.invoke([], {"test": 3})
