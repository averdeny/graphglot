# Lineage Analysis

The lineage module tracks how data flows through a GQL query -- from pattern matching through filtering to output. It answers questions like "which MATCH pattern does this output depend on?" and "what properties are used in filtering vs. output?"

## Quick Start

```python
from graphglot.dialect import Dialect
from graphglot.lineage import LineageAnalyzer, LineageEdgeKind

query = "MATCH (n:Person)-[r:KNOWS]->(m:Person) WHERE n.age > 21 RETURN n.name, m.name"

neo4j = Dialect.get_or_raise("neo4j")
ast = neo4j.parse(query)

analyzer = LineageAnalyzer()
result = analyzer.analyze(ast[0], query_text=query)

# Inspect the graph
graph = result.graph
for b in graph.bindings.values():
    print(f"{b.name}: {b.kind.value} {b.label_expression}")
# n: node Person
# r: edge KNOWS
# m: node Person

for o in graph.outputs.values():
    deps = graph.targets(o.id, LineageEdgeKind.DEPENDS_ON)
    print(f"{o.alias or graph.source_text(o)}: depends on {deps}")
```

## Lineage Graph

The analyzer produces a `LineageGraph` containing interconnected entities:

| Entity | Description |
|--------|-------------|
| **Graph** | A graph referenced in the query (via USE clause or implicit default) |
| **Pattern** | A graph pattern from MATCH -- tracks which bindings it introduces |
| **Binding** | Variable bound in a pattern -- kind (NODE/EDGE/PATH), labels, direction |
| **PropertyRef** | Property access on a binding (e.g., `n.name`) |
| **OutputField** | RETURN clause item -- alias, position, aggregation info |
| **Filter** | Filter condition from WHERE or inline element predicate |
| **LineageEdge** | A typed relationship between entities |

### Edges

Edges connect entities to express relationships:

| Kind | Meaning |
|------|---------|
| `DEPENDS_ON` | Output depends on a binding or property |
| `ORDERED_BY` | Output ordering depends on a binding or property |
| `CONSTRAINS` | Filter constrains a binding |
| `AGGREGATES` | Aggregation relationship |
| `PROPAGATES_TO` | Scope propagation across NEXT/YIELD boundaries |
| `BELONGS_TO` | Entity belongs to a graph |
| `IN_PATTERN` | Binding belongs to a pattern |

### Querying Edges

`LineageGraph` provides `targets()` and `sources()` for traversing edges:

```python
# Find what an output depends on
dep_ids = graph.targets(output.id, LineageEdgeKind.DEPENDS_ON)

# Find what depends on a binding
dependents = graph.sources(binding.id, LineageEdgeKind.DEPENDS_ON)
```

## Export Formats

```python
from graphglot.lineage.exporter import LineageExporter

exporter = LineageExporter(result.graph)

# JSON for tooling
json_str = exporter.to_json()

# Python dict
data = exporter.to_dict()
```

## Impact Analysis

The `ImpactAnalyzer` answers reachability queries: "if this binding changes, what outputs are affected?"

```python
from graphglot.lineage import ImpactAnalyzer

impact = ImpactAnalyzer(result.graph)

# Upstream dependencies for an output
output = next(iter(result.graph.outputs.values()))
summary = impact.upstream(output)

# All upstream summaries
all_summaries = impact.upstream_all()

# Output names
names = impact.output_names()

# Upstream as a graph (nodes + relationships)
ug = impact.upstream_graph(output)
```

## External Context

When analyzing queries that reference variables from an outer scope (e.g., after a `NEXT` pipeline), supply an `ExternalContext`:

```python
from graphglot.lineage import LineageAnalyzer, ExternalContext, BindingKind

ctx = ExternalContext(bindings={"p": BindingKind.NODE})
result = analyzer.analyze(ast[0], external_context=ctx)
# 'p' won't be flagged as unbound
```

## CLI Usage

```bash
# Pretty tables
gg lineage "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name"

# JSON output
gg lineage -o json "MATCH (n)-[r]->(m) RETURN n.name"
```

## See Also

- [Architecture Overview](../architecture/README.md) -- module dependencies and data flow
- [CLI Reference](cli.md) -- `gg lineage` command options
