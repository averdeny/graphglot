# AST Overview

The AST (Abstract Syntax Tree) module contains ~500 expression types generated from the GQL grammar. Every parsed query produces a tree of `Expression` nodes that can be traversed, searched, and converted back to query text.

## Expression Base Class

All AST nodes inherit from `Expression`, which is a Pydantic `BaseModel` with tree traversal capabilities:

```python
from graphglot.ast import Expression

# Given a parsed program:
program = ast_nodes[0]

# Depth-first traversal
for node in program.dfs():
    print(type(node).__name__)

# Breadth-first traversal
for node in program.bfs():
    print(type(node).__name__)

# Find specific node types
from graphglot.ast import MatchStatement
matches = program.find_all(MatchStatement)

# Find first occurrence
first_match = program.find_first(MatchStatement)
```

### Key Methods

| Method | Description |
|--------|-------------|
| `dfs()` | Depth-first iterator over all descendant nodes |
| `bfs()` | Breadth-first iterator over all descendant nodes |
| `find_all(type_)` | Find all descendants of a given type |
| `find_first(type_)` | Find the first descendant of a given type |
| `children()` | Iterator over immediate child expressions |
| `is_leaf()` | True if this node has no child expressions |
| `to_gql(dialect=)` | Convert this subtree back to a query string |

## AST Hierarchy

The top-level structure follows the GQL grammar:

```
GqlProgram
+-- ProgramActivity
    +-- SessionActivity / TransactionActivity
+-- Statement
    +-- QueryStatement
    |   +-- MatchStatement
    |   +-- ReturnStatement
    |   +-- FilterStatement (WHERE)
    +-- DataModifyingStatement
        +-- InsertStatement
        +-- SetStatement
        +-- DeleteStatement
```

### Common Node Types

| Node | Description |
|------|-------------|
| `GqlProgram` | Root node — always the first parse result |
| `MatchStatement` | `MATCH <pattern> [WHERE <condition>]` |
| `ReturnStatement` | `RETURN <items> [ORDER BY ...] [LIMIT ...]` |
| `WhereClause` | `WHERE <condition>` |
| `Identifier` | Variable or label name |
| `GraphPattern` | Pattern in a MATCH clause |
| `NodePattern` | `(n:Label {prop: value})` |
| `EdgePattern` | `-[r:TYPE]->` |

## Source Spans

Parsed AST nodes track their position in the original query text:

```python
node = program.find_first(MatchStatement)
span = node.source_span  # (start_offset, end_offset) or None

if span:
    start, end = span
    print(f"MATCH clause: {query_text[start:end]}")
```

Source spans are set automatically by the `@parses` decorator. They are preserved through `model_copy(deep=True)`.

## Converting Back to Text

Any AST subtree can be converted back to a query string:

```python
# Default (IR) dialect
text = program.to_gql()

# Specific dialect
text = program.to_gql(dialect="neo4j")
```

This uses the generator pipeline internally — the output is always syntactically valid for the target dialect.

## Parent Tracking

Each node maintains a reference to its parent in the tree:

```python
match = program.find_first(MatchStatement)
print(match._parent)  # The containing statement
print(match._arg_key)  # Field name in the parent
```

!!! note
    Parent references (`_parent`, `_arg_key`, `_index`) are private attributes set during parsing. They are available on parsed trees but not on manually constructed AST nodes.

## Constructing AST Nodes

AST nodes are Pydantic models and can be constructed directly:

```python
from graphglot.ast import Identifier, MatchStatement, GraphPattern

ident = Identifier(identifier="n")
```

Most nodes have required and optional fields matching the GQL grammar. Refer to the [API Reference](../../reference/ast.md) for field documentation on specific types.

## Type Aliases

Many GQL grammar productions are modeled as `Union` type aliases rather than distinct classes:

```python
# These are Union types, not classes:
# GeneralLiteral = CharacterStringLiteral | ByteStringLiteral | ...
# UnsignedLiteral = UnsignedNumericLiteral | GeneralLiteral
```

Use `isinstance()` on the concrete types when checking node types.

## See Also

- [Architecture Overview](../architecture/README.md) — module structure and design patterns
- [API Reference](../../reference/dialect.md) — complete class documentation
