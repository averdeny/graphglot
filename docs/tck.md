# openCypher TCK Integration

GraphGlot integrates the [openCypher Technology Compatibility Kit (TCK)](https://github.com/opencypher/openCypher/tree/master/tck) — the industry-standard conformance suite for Cypher implementations.

Since GraphGlot is a **parser/generator** (not a database), the TCK tests focus on three aspects:

1. **Parse tests** — Can the Neo4j dialect parse each TCK query?
2. **Round-trip tests** — Does parse → generate → re-parse produce equivalent ASTs?
3. **Error tests** — Do compile-time error scenarios produce parse errors?

## Test Suite Summary

| Metric | Value |
|--------|-------|
| Feature files | 192 (of 220; 28 are empty placeholders) |
| Total scenarios | 3,897 |
| Positive scenarios | 3,202 |
| Compile-time error scenarios | 600 |
| Runtime error scenarios | 77 |
| Any-time error scenarios | 18 |

### Current Results (2026-03-16)

| Test File | Passed | xFailed | Skipped | Rate |
|-----------|--------|---------|---------|------|
| `test_tck_parse.py` | 3,897 | 0 | — | **100%** |
| `test_tck_roundtrip.py` | 3,279 | 0 | 0 | **100%** |
| `test_tck_errors.py` | 540 | 60 | — | **90.0%** |

**Parse pass rate: 100%** (3,897 / 3,897). All openCypher TCK scenarios parse successfully through the Cypher dialect extension layer.

**Round-trip rate: 100%** (3,279 / 3,279). All parseable scenarios round-trip successfully (0 xfails, 0 skipped).

The error detection rate is 90.0% (540 / 600). The 60 xfails are queries that SHOULD fail but the parser accepts — these require deeper semantic analysis (function signatures, pattern scope).

## openCypher vs GQL vs Neo4j

Understanding the relationship between these three is key to interpreting the TCK results.

### History

[Neo4j](https://neo4j.com/) created the Cypher query language and later open-sourced its specification as [openCypher](https://opencypher.org/). The openCypher TCK was built by Neo4j to test any Cypher implementation for conformance. Neo4j itself is the **reference implementation** — it covers essentially all openCypher syntax, since it defined the language.

In parallel, the ISO standardization effort produced **GQL (ISO/IEC 39075:2024)**, which adopted much of Cypher's query construction semantics (the `MATCH`/`RETURN` pattern) but introduced its own syntax choices and dropped or renamed several Cypher-specific constructs.

### Neo4j's Transition to GQL

As of 2025, Neo4j supports [two Cypher versions](https://neo4j.com/blog/developer/cypher-versioning/):

- **Cypher 5** — frozen classic openCypher syntax, maintained for backward compatibility
- **Cypher 25** — evolving, aligns with GQL, adds features like `DIFFERENT RELATIONSHIPS`, `FILTER`, `LET`, `WHEN`/`ELSE`

Neo4j's [GQL conformance documentation](https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/) states that *"Cypher supports the majority of mandatory GQL features"* and that *"users should expect minimal differences between crafting queries in Cypher and GQL."*

### Syntax Differences: openCypher vs GQL

Many of the TCK failures are not missing features — they reflect genuine **syntax differences** between the two languages:

| openCypher | GQL | Notes |
|------------|-----|-------|
| `-->`, `<--` | `->`, `<-` | Directed edge arrows |
| `--` (undirected) | `~` | Undirected edge connector |
| `^` | `POWER()` | Exponentiation |
| `%` | `MOD()` | Modulus |
| `all(x IN list WHERE ...)` | No direct equivalent | Quantifier predicate functions |
| `[x IN list \| expr]` | No direct equivalent | List comprehension |
| `date({year: 2024})` | `DATE '2024-01-01'` | Temporal constructors use map vs literal |
| `toBoolean()`, `toInteger()` | `CAST(x AS BOOLEAN)` | Type conversion |
| `size(list)` | `CARDINALITY(list)` | Collection length (both supported) |
| `nodes(path)` | `ELEMENTS(path)` | Path decomposition (both supported) |

### What This Means for GraphGlot

GraphGlot's parser targets GQL (the **destination** Neo4j is moving toward), while the TCK tests openCypher (the **origin**). As of 2026-02-23, the Cypher dialect extension layer achieves **100% parse coverage** of all 3,897 TCK scenarios.

This was achieved through a layered approach: the GQL core parser handles ~70% of Cypher syntax natively (MATCH/RETURN, property access, functions, etc.), while the `CypherDialect` extension layer adds ~30% of Cypher-specific syntax (arrows `-->`, `^` power, `%` modulus, `NOT NOT`, multi-label `:A:B:C`, variable-length `[*N..M]`, UNWIND, WITH, MERGE, list comprehensions, temporal constructors, etc.).

As Neo4j continues adopting GQL (Cypher 25+), the gap between what GraphGlot's GQL parser handles and what Neo4j accepts will naturally shrink. Features that are openCypher-only (like `-->` arrows) will eventually be superseded by their GQL equivalents (`->`), which GraphGlot already supports.

## Vendored Feature Files

The TCK `.feature` files are vendored from [openCypher](https://github.com/opencypher/openCypher) at a pinned commit (recorded in `tests/graphglot/tck/loader.py`). This ensures reproducible tests with no network dependency.

To update to a newer TCK version:

```bash
# Update to latest master
scripts/update-tck.sh

# Update to a specific commit or tag
scripts/update-tck.sh ecbde675
```

The script clones the upstream repo, copies `tck/features/`, and updates the commit reference in `loader.py`. After updating, run `make tck` to verify nothing broke and update `xfails.py` as needed.

## Running TCK Tests

```bash
# Run all TCK tests
make tck
```
