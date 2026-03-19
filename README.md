# GraphGlot

![CI](https://github.com/averdeny/graphglot/actions/workflows/release.yml/badge.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Parse, validate, transpile, and analyze graph query languages.**

GraphGlot is a pure-Python toolkit for GQL (ISO/IEC 39075:2024) and Neo4j Cypher. It lets you parse queries into ASTs, transpile between dialects, validate syntax and feature compatibility, and analyze data lineage without requiring a database.

GraphGlot is pre-v1 and evolving quickly. APIs and behavior may still change as coverage and semantics expand.

## Why GraphGlot?

- **GQL parser** — parses the GQL language defined by ISO/IEC 39075:2024, including the core language and many optional language features
- **Standards-aligned feature flagging** — reports which optional GQL features a query uses, following the GQL Flagger model in the standard
- **Validate queries** — check syntax, feature compatibility, and semantic rules before hitting the database
- **Transpile between dialects** — parse Neo4j Cypher and generate standard GQL, or vice versa
- **100% openCypher TCK parse rate** — parses all 3,897 tracked conformance scenarios
- **Track data lineage** — understand how data flows from MATCH patterns to RETURN outputs
- **Build tooling** — power linters, formatters, migration tools, and IDE integrations with a complete AST


## Playground

Try it online: graphglot.com/playground

## Validation

Check if a query is valid for a specific dialect and see which GQL features it requires:

```python
from graphglot.dialect import Dialect

neo4j = Dialect.get_or_raise("neo4j")
result = neo4j.validate("MATCH (n:Person) RETURN n.name")

print(result.success)      # True
print(result.features)     # Set of required GQL features
print(result.diagnostics)  # Semantic warnings/errors
```

## Transpilation

Parse a query with one dialect, generate it in another:

```python
from graphglot.dialect import Dialect

neo4j = Dialect.get_or_raise("neo4j")
gql = Dialect.get_or_raise("fullgql")  # standard GQL

# Parse Cypher, generate GQL
ast = neo4j.parse("UNWIND [1, 2, 3] AS x RETURN x")
print(gql.generate(ast[0]))
# FOR x IN [1, 2, 3] RETURN x

ast = neo4j.parse("MATCH (n)-[r:KNOWS*1..3]->(m) RETURN n, m")
print(gql.generate(ast[0]))
# MATCH (n) -[r :KNOWS]-> {1,3} (m) RETURN n, m

ast = neo4j.parse("MATCH (n) WHERE n.score ^ 2 > 100 RETURN n")
print(gql.generate(ast[0]))
# MATCH (n) WHERE POWER(n.score, 2) > 100 RETURN n
```

Cypher-specific syntax is automatically converted to GQL equivalents: `UNWIND` becomes `FOR...IN`, variable-length paths `[*1..3]` become quantifiers `{1,3}`, `^` becomes `POWER()`, and more.


## Data Lineage

Track how data flows through a query — which patterns introduce which variables, what each output depends on:

```python
from graphglot.dialect import Dialect
from graphglot.lineage import LineageAnalyzer

query = "MATCH (n:Person)-[r:KNOWS]->(m:Person) WHERE n.age > 21 RETURN n.name AS person, m.name AS friend"

neo4j = Dialect.get_or_raise("neo4j")
ast = neo4j.parse(query)

analyzer = LineageAnalyzer()
result = analyzer.analyze(ast[0], query_text=query)

for b in result.bindings.values():
    print(f"{b.name}: {b.kind.value} label_expression={b.label_expression}")
# n: node label_expression=Person
# r: edge label_expression=KNOWS
# m: node label_expression=Person

for o in result.outputs.values():
    print(f"{o.alias}: {o.id}")
# person: o_0
# friend: o_1
```

Export lineage as JSON or upstream summary:

```bash
gg lineage "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name" -o json
gg lineage "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name" -o upstream
```

## CLI

GraphGlot ships with the `gg` command-line tool:

```bash
# Parse and visualize the AST
gg tree "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name, m.name"

# Validate against a dialect
gg validate --dialect neo4j "MATCH (n:Person) RETURN n.name"

# Tokenize
gg tokenize "MATCH (n:Person) RETURN n"

# Lineage analysis
gg lineage "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name"

# Transpile between dialects
gg transpile -r neo4j -w fullgql "MATCH (n) WITH n.age AS age RETURN age"

# Parse and display the raw AST (JSON)
gg parse "MATCH (n) RETURN n"

# Infer types
gg type "MATCH (n:Person) RETURN n.name"

# List available dialects and features
gg dialects
gg features --dialect neo4j
```

## Supported Dialects

| Dialect | Description |
|---------|-------------|
| `fullgql` | Full GQL — all extension and optional features enabled |
| `coregql` | Core GQL — mandatory extension features only, no optional features |
| `neo4j` | Neo4j Cypher 2025+ — GQL subset plus Cypher extensions |

The dialect system is extensible. To add a new dialect (e.g., Memgraph, Amazon Neptune), subclass `Dialect` or `CypherDialect` and declare your supported features:

```python
from graphglot.dialect.base import Dialect
from graphglot.features import ALL_FEATURES, G002

class MyDialect(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {G002}
    KEYWORD_OVERRIDES = {"OFFSET": "SKIP"}
```

## Installation

```bash
pip install graphglot
```

For development:

```bash
pip install -e ".[dev]"
```

## Documentation

- [Getting Started](docs/getting-started.md) — first query, CLI tour
- [Dialect Guide](docs/guide/dialects.md) — the dialect system and feature validation
- [Lineage Analysis](docs/guide/lineage.md) — data flow tracking and export formats
- [AST Overview](docs/guide/ast.md) — working with the abstract syntax tree
- [GQL Features](docs/gql_features.md) — reference for GQL features and optional feature coverage
- [Architecture](docs/architecture/README.md) — module structure and design patterns
- [TCK Conformance](docs/tck.md) — openCypher compatibility status

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We use:

```bash
make test      # unit tests (pytest)
make pre       # linter/formatter (ruff + pre-commit)
make type      # type checking (mypy)
make neo4j     # integration tests (requires Neo4j)
make tck       # openCypher TCK conformance
```

## Acknowledgments

GraphGlot is inspired by [SQLGlot](https://github.com/tobymao/sqlglot), the excellent SQL parser and transpiler. SQLGlot demonstrated that a pure-Python, dialect-aware parser with AST-based transpilation is a powerful and practical approach. GraphGlot applies the same philosophy to graph query languages.

## License

Apache 2.0, see [LICENSE](https://github.com/averdeny/graphglot/blob/main/LICENSE).
