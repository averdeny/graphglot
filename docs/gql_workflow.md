# GQL Workflow: Creating a Graph and Adding Data

A natural GQL workflow for creating a graph, populating it with data, and querying it.

## Step 1: Create a graph

The `CREATE GRAPH` statement always requires a type clause. There are four ways to specify the graph type:

### Open graph type (`TYPED ANY`) -- feature GG01

A schemaless graph with no type constraints. Any node/edge structure is accepted.

```gql
CREATE GRAPH myGraph TYPED ANY
```

### Named graph type reference (`TYPED <name>`) -- feature GG02

Reference a previously created named graph type. The graph enforces the type's schema.

```gql
CREATE GRAPH TYPE SocialNetwork AS {
  NODE TYPE Person,
  DIRECTED EDGE TYPE KNOWS CONNECTING (Person -> Person)
}

CREATE GRAPH myGraph TYPED SocialNetwork
```

### Inline graph type specification (`TYPED { ... }`) -- feature GG03

Define the type inline without creating a named type first.

```gql
CREATE GRAPH myGraph TYPED {
  NODE TYPE Person,
  DIRECTED EDGE TYPE KNOWS CONNECTING (Person -> Person)
}
```

### Like an existing graph (`LIKE <graph>`) -- feature GG04

Copy the graph type from an existing graph.

```gql
CREATE GRAPH myGraph LIKE CURRENT_GRAPH
```

Additional modifiers can be combined with any form:

```gql
CREATE PROPERTY GRAPH myGraph TYPED ANY       // PROPERTY is optional
CREATE GRAPH IF NOT EXISTS myGraph TYPED ANY  // idempotent creation
```

## Step 2: Set the working graph

Use `SESSION SET GRAPH` to set the session working graph (requires optional feature GS01). All subsequent statements operate on this graph.

```gql
SESSION SET GRAPH myGraph
```

Alternatively, the `USE` clause scopes a graph to a single statement without changing the session default:

```gql
USE myGraph MATCH (n) RETURN n
```

## Step 3: Insert data

With the working graph set, insert nodes and edges directly.

```gql
INSERT (:Person {name: 'Alice', age: 30})
INSERT (:Person {name: 'Bob', age: 25})
```

## Step 4: Add relationships

Use `MATCH` + `INSERT` to create edges between existing nodes.

```gql
MATCH (p:Person {name: 'Alice'}), (q:Person {name: 'Bob'})
  INSERT (p)-[:KNOWS {since: 2020}]->(q)
```

## Step 5: Query

```gql
MATCH (n:Person)-[:KNOWS]->(m:Person)
  RETURN n.name, m.name
```

## Full example

```gql
CREATE GRAPH myGraph TYPED ANY
SESSION SET GRAPH myGraph

INSERT (:Person {name: 'Alice', age: 30})
INSERT (:Person {name: 'Bob', age: 25})

MATCH (p:Person {name: 'Alice'}), (q:Person {name: 'Bob'})
  INSERT (p)-[:KNOWS {since: 2020}]->(q)

MATCH (n:Person)-[:KNOWS]->(m:Person)
  RETURN n.name, m.name
```

## Bulk loading

The `INSERT` statement is suitable for small amounts of data. For large graphs (thousands or millions of
nodes/edges), the standard provides two mechanisms:

**Graph source** (feature GG05): populate a new graph by copying from an existing graph at creation time.

```gql
CREATE GRAPH myGraph TYPED ANY AS COPY OF sourceGraph
```

**Binding table parameters** (features GS02, GQ23): set a binding table parameter on the session, then
use `FOR ... IN` to iterate its rows and insert from them. The binding table expression can be a nested
query or a table reference:

```gql
SESSION SET TABLE $people = {MATCH (n:RawPerson) RETURN n.name, n.age}
FOR row IN $people
  INSERT (:Person {name: row.name, age: row.age})
```

Note: binding table parameters hold *tabular* data (rows and columns), which is distinct from value
parameters (scalars, lists, maps) that drivers pass at query execution time. The standard does not
define how binding tables are populated from external sources -- that is implementation-defined.

Beyond these, the GQL standard does not define a bulk import/load mechanism. Implementations
typically provide vendor-specific tools (e.g. Neo4j's `LOAD CSV` / `neo4j-admin import`, Neptune's S3
bulk loader, TigerGraph's `LOAD` statements).

## Notes

- `CREATE GRAPH` always requires a type clause (`TYPED ANY`, `LIKE ...`, or `TYPED <type_name>`)
- `USE <graph_expression>` is a clause prefix, not a standalone statement -- there is no `GRAPH` keyword in it
- `SESSION SET GRAPH` sets the working graph for the session (optional feature GS01)
- `SESSION SET SCHEMA` sets the working schema for the session
- `INSERT` is the GQL keyword for adding data (not `CREATE` -- that is Cypher syntax)
