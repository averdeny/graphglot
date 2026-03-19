# CLI Reference

GraphGlot provides the `gg` command-line tool for working with graph queries. All commands share a common input interface.

## Input Methods

Every command accepts query input in four ways (in order of precedence):

1. **`--query` / `-q`** — inline query string
2. **`--file` / `-f`** — path to a file containing the query
3. **Positional argument** — treated as a file path if it exists, otherwise as a literal query
4. **stdin** — piped input

```bash
# All equivalent:
gg tree --query "MATCH (n) RETURN n"
gg tree "MATCH (n) RETURN n"
echo "MATCH (n) RETURN n" | gg tree
gg tree -f query.gql
```

## Commands

### `gg tokenize` (alias: `t`)

Tokenize a query and display the token stream.

```bash
gg tokenize "MATCH (n:Person) RETURN n.name"
gg tokenize -o json "MATCH (n:Person) RETURN n.name"
gg tokenize --no-color "MATCH (n:Person) RETURN n.name"
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | GQL dialect to use (default: fullgql) |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |
| `--no-color` | Disable colored output |

### `gg ast` (alias: `tree`)

Parse a query and visualize the abstract syntax tree.

```bash
gg tree "MATCH (n:Person) RETURN n.name"
gg tree --depth 3 "MATCH (n:Person) RETURN n.name"
gg tree -o json "MATCH (n:Person) RETURN n.name"
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | GQL dialect to use (default: fullgql) |
| `--depth` | Maximum tree depth to display |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |

### `gg validate` (alias: `v`)

Validate a query against a dialect and report required GQL features.

```bash
gg validate --dialect neo4j "MATCH (n:Person) RETURN n.name"
gg validate -o json "MATCH (n:Person) RETURN n.name"
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | GQL dialect to use (default: fullgql) |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |

The command exits with code 1 if validation fails.

**Pretty output** shows:

- Pass/fail status with the stage that failed (lex, parse, or analyze)
- Error details and semantic diagnostics
- Table of required GQL features with descriptions

**JSON output** includes:

```json
{
  "success": true,
  "stage": "analyze",
  "error": null,
  "features": ["G004", "G005"],
  "diagnostics": []
}
```

### `gg lineage` (alias: `l`)

Analyze variable lineage and data flow in a query.

```bash
gg lineage "MATCH (n:Person)-[r:KNOWS]->(m) RETURN n.name, m.name"
gg lineage -o json "MATCH (n) RETURN n"
gg lineage -o upstream "MATCH (n)-[r]->(m) RETURN n.name"
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | GQL dialect to use (default: fullgql) |
| `-o` / `--output` | Output format: `pretty` (default), `json`, or `upstream` |

The command exits with code 1 if analysis produces errors.

**Output formats:**

| Format | Use case |
|--------|----------|
| `pretty` | Human-readable tables (patterns, bindings, outputs, predicates, edges) |
| `json` | Tooling integration |
| `upstream` | Upstream dependency analysis |

### `gg transpile` (alias: `tp`)

Transpile a query from one dialect to another.

```bash
# GQL → Neo4j
gg transpile -r fullgql -w neo4j "MATCH (n:Person) RETURN n.name"

# Neo4j Cypher → standard GQL
gg transpile -r neo4j -w fullgql "MATCH (n) WITH n.age AS age RETURN age"

# Same-dialect roundtrip (--write defaults to --read)
gg transpile -r neo4j "MATCH (n) RETURN n"

# Pretty-print output
gg transpile -r neo4j -p "MATCH (n) RETURN n"
```

| Option | Description |
|--------|-------------|
| `-r` / `--read` | Source dialect for parsing (default: fullgql) |
| `-w` / `--write` | Target dialect for generation (defaults to read dialect) |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |
| `-p` / `--pretty` | Format output with clause-level line breaks |

### `gg parse` (alias: `p`)

Check whether a query parses successfully (pass/fail).

```bash
gg parse "MATCH (n:Person) RETURN n.name"
gg parse --dialect neo4j "MATCH (n) RETURN n"
gg parse -o json "INVALID QUERY %%"
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | GQL dialect to use (default: fullgql) |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |

Exits with code 1 if the query is invalid.

### `gg type` (alias: `ty`)

Run type inference and display inferred types for RETURN expressions.

```bash
gg type "MATCH (n:Person) RETURN n.name, n.age"
gg type --dialect neo4j "MATCH (n) RETURN n"
gg type -o json "MATCH (n) RETURN n.name"
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | GQL dialect to use (default: fullgql) |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |

### `gg dialects` (alias: `d`)

List available dialects and their feature counts.

```bash
gg dialects
gg dialects -o json
```

| Option | Description |
|--------|-------------|
| `-o` / `--output` | Output format: `pretty` (default) or `json` |

### `gg features` (alias: `f`)

List GQL features, optionally filtered by dialect, category, or kind.

```bash
gg features
gg features --dialect neo4j
gg features --kind optional --search "path"
gg features -c "Graph Pattern" -o json
```

| Option | Description |
|--------|-------------|
| `-d` / `--dialect` | Filter to features supported by a dialect |
| `-c` / `--category` | Case-insensitive substring match on feature category |
| `-k` / `--kind` | Filter by feature kind: `extension` or `optional` |
| `-s` / `--search` | Case-insensitive substring search in feature ID or description |
| `-o` / `--output` | Output format: `pretty` (default) or `json` |
