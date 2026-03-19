# GQL Query Composition and Materialization

This document summarizes the mechanisms available in GQL (ISO/IEC 39075:2024) for combining,
composing, and nesting queries, as well as the options for materializing graph data for reuse.

## Table of Contents

- [GQL Query Composition and Materialization](#gql-query-composition-and-materialization)
  - [Table of Contents](#table-of-contents)
  - [Query Composition](#query-composition)
    - [1. Set Operations](#1-set-operations)
    - [2. NEXT Statement](#2-next-statement)
    - [3. CALL Inline Subqueries](#3-call-inline-subqueries)
    - [4. VALUE and EXISTS Subqueries](#4-value-and-exists-subqueries)
      - [VALUE (Scalar Subquery)](#value-scalar-subquery)
      - [EXISTS (Predicate Subquery)](#exists-predicate-subquery)
    - [5. FOR with TABLE Subqueries](#5-for-with-table-subqueries)
  - [How NEXT Works](#how-next-works)
    - [The Two Data Channels](#the-two-data-channels)
      - [What each statement does to these channels](#what-each-statement-does-to-these-channels)
    - [Binding Variable Propagation](#binding-variable-propagation)
      - [Within a single linear query (chained MATCHes): bindings accumulate](#within-a-single-linear-query-chained-matches-bindings-accumulate)
      - [Across NEXT boundaries: only what RETURN projects](#across-next-boundaries-only-what-return-projects)
  - [Graph Expressions and Their Limitations](#graph-expressions-and-their-limitations)
  - [Materialization Approaches](#materialization-approaches)
    - [1. Graph Variable Definition](#1-graph-variable-definition)
    - [2. Session Parameters](#2-session-parameters)
    - [3. CREATE GRAPH](#3-create-graph)
    - [4. Named Procedures](#4-named-procedures)
    - [Populating a Graph from a Query](#populating-a-graph-from-a-query)
  - [Summary](#summary)

---

## Query Composition

GQL provides five primary mechanisms for combining and composing queries. Each operates at a
different level: statement-level, expression-level, or predicate-level.

### 1. Set Operations

**UNION / INTERSECT / EXCEPT / OTHERWISE**

The most SQL-like composition. Combines the result binding tables of two independent queries.

The `OTHERWISE` operator is GQL-specific: it returns the left side's results unless they are empty, in
which case it falls back to the right side.

```sql
-- Combine results from two patterns
MATCH (n:Person) RETURN n.name
  UNION ALL
MATCH (m:Company) RETURN m.name

-- Deduplicated union (default is DISTINCT when quantifier omitted)
MATCH (n:Person) RETURN n.name
  UNION
MATCH (m:Company) RETURN m.name

-- Set difference
MATCH (n:Person) RETURN n.name
  EXCEPT DISTINCT
MATCH (n:Person)-[:WORKS_AT]->(:Company {name: 'Acme'}) RETURN n.name

-- Intersection
MATCH (n:Person)-[:LIVES_IN]->(:City {name: 'London'}) RETURN n.name
  INTERSECT
MATCH (n:Person)-[:WORKS_AT]->(:Company {name: 'Acme'}) RETURN n.name

-- Fallback if left side is empty
MATCH (n:Person {name: 'Alice'}) RETURN n
  OTHERWISE
MATCH (n:Person) RETURN n LIMIT 1
```

**AST type:** `CompositeQueryExpression` with `QueryConjunction`.

**Standard reference:** ISO/IEC 39075:2024, §14.1–§14.2.

**Feature IDs:** GQ02 (OTHERWISE), GQ03 (UNION), GQ04–GQ07 (EXCEPT/INTERSECT variants).

---

### 2. NEXT Statement

**Pipeline chaining across statement boundaries.**

NEXT is GQL's primary mechanism for multi-stage pipelines. It takes the binding table result from
the previous statement and feeds it as the working table of the next statement.

```sql
-- Two-stage pipeline: aggregate, then filter
MATCH (p:Person)-[:WORKS_AT]->(c:Company)
RETURN c, count(p) AS employee_count
NEXT
FILTER employee_count > 100
RETURN c, employee_count

-- Chain MATCH results forward
MATCH (n:Person) RETURN n
NEXT
MATCH (n)-[:KNOWS]->(m:Person)
RETURN n, m
```

In the second example, `n` is a column in the working table from the first stage. The second
MATCH performs a natural join with the graph pattern, using `n` as a join point.

> **Important:** NEXT creates a scope boundary. Only variables explicitly named in the preceding
> RETURN survive into the next stage. See [How NEXT Works](#how-next-works) for details.

**AST type:** `NextStatement` within a `StatementBlock`.

**Standard reference:** ISO/IEC 39075:2024, §9.2.

**Feature ID:** GQ20.

---

### 3. CALL Inline Subqueries

**Correlated subqueries — the inner query runs once per row of the outer query.**

CALL with an inline procedure body (`{ ... }`) is the closest analogue to SQL's correlated subqueries.
The variable scope clause `(vars)` declares which outer bindings are visible inside.

```sql
-- For each person, count their outgoing edges in a subquery
MATCH (s:Person)
CALL (s) {
    MATCH (s)-[e]->()
    RETURN count(e) AS total
}
RETURN s.name, total

-- Without explicit scope (all outer variables implicitly visible)
MATCH (n:Person)
CALL {
    MATCH (n)-[:KNOWS]->(m:Person)
    RETURN count(m) AS friend_count
}
RETURN n.name, friend_count

-- Named procedure call (procedure must exist in catalog)
CALL my_schema.find_influencers(100)
YIELD person, score
RETURN person.name, score
```

**AST types:** `CallProcedureStatement`, `InlineProcedureCall`, `NamedProcedureCall`.

**Standard reference:** ISO/IEC 39075:2024, §15.1–§15.3.

**Feature IDs:** GP01 (inline procedure), GP02 (implicit variable scope), GP03 (explicit variable
scope), GP04 (named procedure calls).

---

### 4. VALUE and EXISTS Subqueries

**Expression-level and predicate-level nesting — embed queries inside expressions.**

#### VALUE (Scalar Subquery)

Returns a single scalar value from a nested query. Can appear anywhere a value expression is
expected.

```sql
MATCH (n:Person)
RETURN n.name, VALUE {
    MATCH (n)-[:WORKS_AT]->(c:Company)
    RETURN c.name
}
```

**AST type:** `ValueQueryExpression`.

**Feature ID:** GQ18.

#### EXISTS (Predicate Subquery)

Returns a boolean indicating whether the nested pattern or query produces any results. Used in
WHERE/FILTER clauses.

```sql
-- Pattern form
MATCH (n:Person)
WHERE EXISTS { (n)-[:KNOWS]->(:Person {name: 'Bob'}) }
RETURN n.name

-- Full MATCH form
MATCH (n:Person)
WHERE EXISTS { MATCH (n)-[:KNOWS]->(m:Person) MATCH (m)-[:LIVES_IN]->(:City {name: 'London'}) }
RETURN n.name
```

**AST type:** `ExistsPredicate`.

**Standard reference:** ISO/IEC 39075:2024, §20.15.

**Feature ID:** GQ22 (multiple MATCH form).

---

### 5. FOR with TABLE Subqueries

**Iterate over a binding table produced by a nested query.**

The FOR statement iterates over a list or a binding table. Combined with `TABLE { ... }`, it lets
you use a query's result as an iterable data source.

```sql
-- Iterate over query results
FOR x IN TABLE { MATCH (n:Person) RETURN n.name AS name }
MATCH (m:Company {ceo: x.name})
RETURN m, x.name

-- Iterate over a list with ordinal tracking
FOR x IN [1, 2, 3] WITH ORDINALITY idx
MATCH (n {id: x})
RETURN n, idx

-- Iterate with offset tracking
FOR x IN TABLE { MATCH (n) RETURN n } WITH OFFSET i
RETURN x, i
```

**AST types:** `ForStatement`, `BindingTableReferenceValueExpression`.

**Standard reference:** ISO/IEC 39075:2024, §14.8.

**Feature IDs:** GQ10 (list values), GQ11 (WITH ORDINALITY), GQ23 (binding table support),
GQ24 (WITH OFFSET).

---

## How NEXT Works

### The Two Data Channels

Every GQL execution context carries two separate data channels
(ISO/IEC 39075:2024, §4.10.3):

| Channel | What it holds | How bindings work |
|---------|---------------|-------------------|
| **Working record** | A single record | Fixed variables — each bound to exactly one value |
| **Working table** | A binding table (collection of records) | Iterated variables — bound once per record during iteration |

The two are always **field name-disjoint**: no binding variable name appears in both.

#### What each statement does to these channels

| Statement | Working record | Working table |
|-----------|---------------|---------------|
| **MATCH** | Amends with pattern variables that overlap the record | Replaces with pattern match results (natural join with existing table) |
| **RETURN** | Passes through unchanged | Replaces with projected columns; sets execution outcome to the new table |
| **NEXT** | Passes through from previous statement (§9.2 Syntax Rule 12a) | Set to the binding table result from the execution outcome (§9.2 General Rule 3a) |
| **FILTER** | Passes through unchanged | Replaces with filtered subset |
| **INSERT** | Passes through unchanged | Amends with new element bindings |

The key insight: **RETURN sets the working table and the execution outcome. NEXT then moves
the execution outcome into the working table of the next stage. The working record passes
through NEXT unchanged.**

### Binding Variable Propagation

#### Within a single linear query (chained MATCHes): bindings accumulate

Each MATCH amends the working table with new columns from its pattern. Shared variable names
act as natural join points:

```sql
MATCH (a:Person)              -- working table: {a}
MATCH (a)-[r]->(b:Company)    -- working table: {a, r, b}  (natural join on a)
MATCH (b)-[s]->(c:Office)     -- working table: {a, r, b, s, c}  (natural join on b)
RETURN a, b, c                -- all bindings from all three MATCHes available
```

**Standard reference:** ISO/IEC 39075:2024, §14.3 Syntax Rule 5.

#### Across NEXT boundaries: only what RETURN projects

NEXT creates a scope boundary. Only the columns named in the preceding RETURN survive:

```sql
MATCH (a:Person) RETURN a           -- outcome: {a}
NEXT                                 -- working table: {a}
MATCH (a)-[r]->(b) RETURN b         -- outcome: {b}  (a and r are gone)
NEXT                                 -- working table: {b}
MATCH (c) RETURN b, c               -- a is NOT available here
```

To carry bindings across multiple NEXT boundaries, each RETURN must explicitly include them:

```sql
MATCH (a:Person) RETURN a
NEXT
MATCH (a)-[r]->(b) RETURN a, b      -- keep a
NEXT
MATCH (b)-[s]->(c) RETURN a, b, c   -- a is still available
```

---

## Graph Expressions and Their Limitations

A `<graph expression>` (§11.1) resolves to a **graph reference value** — a pointer to an existing,
whole graph. It can be:

1. A **catalog graph reference**: `/my_schema/my_graph`
2. **CURRENT_GRAPH**: the session's working graph
3. A **binding variable** holding a graph reference value type (feature GV60)

There is **no** graph expression form that accepts a subquery, a pattern, or a filter. A graph
expression always points to a pre-existing, complete graph.

This creates a fundamental asymmetry:

| Object | Can be derived from a query? | Can be used as MATCH input? |
|--------|------------------------------|----------------------------|
| **Binding table** | Yes (every RETURN produces one) | No (it's rows, not a graph) |
| **Graph** | No (only catalog/session references) | Yes (via USE) |

**GQL has no concept of graph views, graph projections, or graph-returning subqueries.** You
cannot define a subgraph from a pattern and then use the result as a graph for further MATCH
operations within the same query.

---

## Materialization Approaches

### 1. Graph Variable Definition

**Scope:** procedure body (statement block only).

Binds a graph reference to a variable in the working record. The variable exists only for the
duration of the enclosing procedure body.

```sql
GRAPH myGraph = /my_schema/some_graph
USE myGraph MATCH (n) RETURN n
```

The graph expression on the right-hand side can only reference existing catalog graphs or
CURRENT_GRAPH — it cannot define a subgraph from a query.

**Standard reference:** ISO/IEC 39075:2024, §10.1.

**Feature IDs:** GP11, GP12, GP13.

### 2. Session Parameters

**Scope:** session (persists across requests within a session).

Store a graph reference, a binding table, or a value in a session parameter accessible via
`$name` syntax.

```sql
-- Store a graph reference for the session
SESSION SET GRAPH $myGraph = /my_schema/some_graph

-- Later, in another request within the same session
USE $myGraph MATCH (n) RETURN n

-- Store a binding table from a query result
SESSION SET TABLE $cachedResults = { MATCH (n:Person) RETURN n.name }

-- Store a scalar value
SESSION SET VALUE $threshold = 100
```

Session parameters survive across GQL-requests but not across sessions.

**Standard reference:** ISO/IEC 39075:2024, §7.1.

**Feature IDs:** GS01 (graph params), GS02 (binding table params), GS03 (value params).

### 3. CREATE GRAPH

**Scope:** catalog (persistent).

Creates a named graph in the GQL-catalog. This is the only way to persistently materialize
graph data.

```sql
-- Create an empty graph with open type
CREATE GRAPH /my_schema/new_graph TYPED ANY GRAPH

-- Create with a named graph type (enforces schema)
CREATE GRAPH /my_schema/new_graph TYPED my_graph_type

-- Create with inline type specification
CREATE GRAPH /my_schema/new_graph (
    :Person { name STRING, age INT },
    :Person -[:KNOWS]-> :Person
)

-- Copy an entire existing graph (snapshot)
CREATE GRAPH /my_schema/snapshot AS COPY OF CURRENT_GRAPH

-- Copy with type inferred from source
CREATE GRAPH /my_schema/typed_copy LIKE source_graph AS COPY OF source_graph

-- Idempotent creation
CREATE GRAPH IF NOT EXISTS /my_schema/new_graph TYPED ANY GRAPH

-- Replace existing
CREATE OR REPLACE GRAPH /my_schema/new_graph TYPED ANY GRAPH
```

`AS COPY OF` copies **all** nodes and edges. Each copied element receives a new global object
identifier. There is no filtering or projection — it is a full snapshot.

**Standard reference:** ISO/IEC 39075:2024, §12.4.

**Feature IDs:** GC04 (graph management), GC05 (IF NOT EXISTS), GG01–GG05 (type/source
variants).

### 4. Named Procedures

**Scope:** catalog (persistent, reusable logic).

Named procedures are catalog objects that encapsulate reusable query logic.

```sql
-- Calling a named query procedure
CALL /my_schema/find_influencers(100) YIELD person, score
RETURN person.name, score
```

The standard defines the procedure descriptor (parameters, result type, side-effect
classification) but **does not define** a `CREATE PROCEDURE` statement. The mechanism for
creating named procedures is implementation-defined.

**Standard reference:** ISO/IEC 39075:2024, §4.10.2, §15.3.

**Feature ID:** GP04.

### Populating a Graph from a Query

There is no `CREATE GRAPH AS (SELECT ...)` in GQL. To create a graph from query results,
you need a multi-step approach using CREATE + CALL + INSERT:

```sql
-- Step 1: Create the empty target graph
CREATE GRAPH /my_schema/friends TYPED ANY GRAPH
NEXT
-- Step 2: Read from the current graph via CALL, then insert into the new graph
CALL {
    MATCH (a:Person)-[:KNOWS]->(b:Person)
    RETURN a, b
}
USE /my_schema/friends
INSERT (x:Person {name: a.name})-[:KNOWS]->(y:Person {name: b.name})
```

This requires feature GP18 ("Catalog and data statement mixing") to combine CREATE GRAPH
and INSERT in the same transaction.

**Key limitation:** The nodes and edges in the new graph are **new objects** with new identifiers.
They are copies, not references to the originals. There is no foreign-key or link back to the
source graph.

---

## Summary

| Mechanism | Level | Scope | Passes graphs? | Passes binding tables? |
|-----------|-------|-------|---------------|----------------------|
| Set operations | Statement | Within query | No | Yes (combined results) |
| NEXT | Statement | Within procedure body | No | Yes (via execution outcome) |
| CALL { } | Statement | Correlated subquery | No | Yes (joined with outer) |
| VALUE { } | Expression | Scalar subquery | No | No (single value) |
| EXISTS { } | Predicate | Boolean subquery | No | No (boolean) |
| FOR + TABLE { } | Statement | Iteration | No | Yes (iterated) |
| Graph variable | Declaration | Procedure body | Yes (reference only) | No |
| Session parameter | Session | Across requests | Yes (reference only) | Yes |
| CREATE GRAPH | Catalog | Persistent | Yes (snapshot copy) | No |
| Named procedure | Catalog | Persistent | No | Yes (via YIELD) |

The fundamental design point of GQL: **binding tables are the universal data exchange format
between query stages. Graphs are opaque, persistent objects that can be referenced but not
derived from queries.** There is no mechanism for graph views, graph-returning subqueries, or
graph projections in ISO/IEC 39075:2024.
