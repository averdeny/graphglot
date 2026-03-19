# Getting Started

## Installation

Install GraphGlot from source (editable mode with dev dependencies):

```bash
pip install -e .[dev]
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install -e .[dev]
```

## Your First Query

```python
from graphglot.dialect import Dialect

dialect = Dialect.get_or_raise("fullgql")

# Parse and inspect the AST
ast_nodes = dialect.parse("MATCH (n:Person) RETURN n.name")
print(type(ast_nodes[0]).__name__)  # GqlProgram

# Transpile between dialects
neo4j = Dialect.get_or_raise("neo4j")
results = neo4j.transpile("MATCH (n:Person) RETURN n.name")
print(results[0])  # MATCH (n:Person) RETURN n.name
```

## CLI Tour

GraphGlot ships with the `gg` command-line tool. Run `gg --help` to see all available commands:

```
$ gg --help
Usage: gg [OPTIONS] COMMAND [ARGS]...

  GraphGlot - A Graph Query Language Toolkit.

Commands:
  ast (tree)      Visualize the AST tree structure of a query.
  dialects (d)    List available dialects and their feature counts.
  features (f)    List GQL features, optionally filtered by...
  lineage (l)     Analyze variable lineage and data flow in a query.
  parse (p)       Check whether a query parses successfully (pass/fail).
  tokenize (t)    Tokenize a query or file and print tokens.
  transpile (tp)  Transpile a query from one dialect to another.
  type (ty)       Run type inference and display inferred types for RETURN...
  validate (v)    Validate a query and report required GQL features.
```

Run `gg <command> --help` for details on any command.

### Examples

```bash
# Tokenize a query
gg tokenize "MATCH (n:Person) RETURN n.name"

# Visualize the AST (limit depth, JSON output)
gg tree "MATCH (n:Person) RETURN n.name"
gg tree --depth 3 "MATCH (n:Person) RETURN n.name"
gg tree -o json "MATCH (n:Person) RETURN n.name"

# Validate against a dialect
gg validate --dialect neo4j "MATCH (n:Person) RETURN n.name"

# Transpile between dialects
gg transpile -r neo4j -w fullgql "MATCH (n) WITH n.age AS age RETURN age"

# Lineage analysis (pretty, JSON, or upstream)
gg lineage "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name"
gg lineage -o upstream "MATCH (n)-[r]->(m) RETURN n.name"

# Infer types for RETURN expressions
gg type "MATCH (n:Person) RETURN n.name, n.age"

# List dialects and features
gg dialects
gg features --dialect neo4j

# Pipe from stdin
echo "MATCH (n) RETURN n" | gg parse
```

## Next Steps

- [Dialects](guide/dialects.md) — understand the dialect system and feature validation
- [CLI Reference](guide/cli.md) — full command reference
- [Lineage Analysis](guide/lineage.md) — deep dive into data flow tracking
- [AST Overview](guide/ast.md) — working with the abstract syntax tree
