# Dialects

GraphGlot uses a dialect system to support multiple graph query languages through a single pipeline. Each dialect configures how queries are lexed, parsed, validated, and generated.

## Available Dialects

| Name | Class | Description |
|------|-------|-------------|
| `ir` | `IR` | Default GQL dialect — full ISO/IEC 39075:2024 grammar |
| `fullgql` | `FullGQL` | Full GQL — all extension and optional features enabled |
| `coregql` | `CoreGQL` | Core GQL — mandatory extension features only, no optional features |
| `neo4j` | `Neo4j` | Neo4j Cypher — GQL subset plus Cypher-specific extensions |

## Using Dialects

### Get a Dialect Instance

```python
from graphglot.dialect import Dialect

# By name
ir = Dialect.get_or_raise("ir")
full = Dialect.get_or_raise("fullgql")
core = Dialect.get_or_raise("coregql")
neo4j = Dialect.get_or_raise("neo4j")

# Or via the enum
from graphglot.dialect import Dialects
neo4j = Dialects.NEO4J.value()
```

### Validate a Query

The `validate()` method runs the full pipeline (lex, parse, analyze) and returns a result with success status, required features, and diagnostics:

```python
result = neo4j.validate("MATCH (n:Person) RETURN n.name")
print(result.success)      # True
print(result.features)     # {Feature("G004"), ...}
print(result.diagnostics)  # []
```

### Semantic Analysis

The `analyze()` method parses the query and runs semantic analysis rules:

```python
result = neo4j.analyze("MATCH (n:Person) RETURN n.name")
print(result.diagnostics)  # Semantic warnings/errors
```

### Transpile Between Dialects

Use the `gg transpile` CLI command to parse a query with one dialect and
generate it with another:

```bash
# Neo4j Cypher → standard GQL
gg transpile -r neo4j -w fullgql "MATCH (n) WITH n.age AS age RETURN age"

# Same-dialect roundtrip (--write defaults to --read)
gg transpile -r neo4j "MATCH (n) RETURN n"

# JSON output
gg transpile -r neo4j -w fullgql -o json "MATCH (n) RETURN n"
```

The same functionality is available via the `Dialect.transpile()` Python method:

```python
from graphglot.dialect import Dialect

neo4j = Dialect.get_or_raise("neo4j")
results = neo4j.transpile("MATCH (n) RETURN n")
```

## Feature System

GQL defines 228 optional and extension features. Each dialect declares which features it supports.

### Feature Kinds

| Kind | Description |
|------|-------------|
| **Optional** | Standard GQL features that implementations may support (e.g., `G002` — different-edges match mode) |
| **Extension** | GraphGlot-specific extensions beyond the standard (e.g., `GG:SS01` — SELECT statement) |

### Checking Features

```python
from graphglot.features import get_feature, ALL_FEATURES

feature = get_feature("G002")
print(feature.description)  # "Different-edges match mode"
print(feature.kind)         # FeatureKind.OPTIONAL

# Check dialect support
print(feature in neo4j.SUPPORTED_FEATURES)  # True
```

### Validation Pipeline

When you call `dialect.validate(query)`, the pipeline:

1. **Lexes** the query into tokens (dialect-specific lexer)
2. **Parses** tokens into an AST
3. **Detects features** used by the query
4. **Runs semantic analysis** rules gated by the dialect's feature set
5. **Returns** a `ValidationResult` with success, features, and diagnostics

Features that appear in the query but are **not** in `dialect.SUPPORTED_FEATURES` produce diagnostics.

## Dialect Architecture

### Inheritance

```
Dialect (GQL base)
  +-- IR (full GQL)
  +-- FullGQL (full GQL — all features)
  +-- CoreGQL (core GQL — mandatory features only)
  +-- CypherDialect (shared Cypher syntax — abstract, not in Dialects enum)
        +-- Neo4j
```

`CypherDialect` adds Cypher-specific parsing (STARTS WITH, IN, UNWIND, WITH) shared by all Cypher-compatible databases. Users always pick a concrete vendor dialect.

### Customization Points

Each dialect can override:

| Attribute | Purpose |
|-----------|---------|
| `SUPPORTED_FEATURES` | Set of features this dialect supports |
| `KEYWORD_OVERRIDES` | Map GQL keywords to dialect equivalents (e.g., OFFSET to SKIP) |
| `TOKENS_*` | Token sets for dialect-specific keyword parsing |

### Adding a New Dialect

1. Subclass `Dialect` (or `CypherDialect` for Cypher-compatible databases)
2. Set `SUPPORTED_FEATURES` to declare which GQL features are supported
3. Override `KEYWORD_OVERRIDES` for any keyword differences
4. Add the dialect to the `Dialects` enum in `graphglot/dialect/base.py`

```python
class MyDialect(Dialect):
    SUPPORTED_FEATURES = ALL_FEATURES - {get_feature("G042")}
    KEYWORD_OVERRIDES = {"OFFSET": "SKIP"}
```

For details on the Cypher extension architecture, see the [Architecture Overview](../architecture/README.md).

## See Also

- [GQL Features](../gql_features.md) — complete reference for all 228 features
- [GQL Workflow](../gql_workflow.md) — creating graphs and querying data in GQL
