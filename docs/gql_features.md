# GQL Feature Reference

Complete reference for all 228 optional GQL features in the GraphGlot conformance registry, organized by category.
Each entry includes a short explanation and (for active features) a test query.


## Core (Graph pattern matching)

Pattern matching features for traversing nodes, edges, and paths.

### G002 — Different-edges match mode

Enables the `DIFFERENT EDGES` modifier on `MATCH` to ensure that each edge binding maps to a distinct edge. By default GQL already enforces edge isomorphism, but this makes it explicit.

```gql
MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n
```

### G003 — Explicit REPEATABLE ELEMENTS keyword

Allows `REPEATABLE ELEMENTS` to opt in to non-isomorphic matching where the same node or edge may appear multiple times in a single match.

```gql
MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n
```

### G004 — Path variables

Enables binding a matched path to a variable (`p = ...`) so the entire path can be returned, compared, or passed to path functions like `PATH_LENGTH`.

```gql
MATCH p = (n)-[e]->(m) RETURN p
```

### G005 — Path search prefix in a path pattern

Enables path search prefixes (`ALL`, `ANY`, `SHORTEST`, etc.) on a path pattern to control which paths are returned when multiple matches exist.

```gql
MATCH ALL PATHS (n)-[e]->(m) RETURN n
```

### G006 — Graph pattern KEEP clause: path mode prefix

Adds the `KEEP` clause with a path mode (`WALK`, `TRAIL`, etc.) to preserve a specific traversal mode across the entire graph pattern.

```gql
MATCH (n)-[e]->(m) KEEP WALK RETURN n
```

### G007 — Graph pattern KEEP clause: path search prefix

Adds the `KEEP` clause with a path search prefix (`ALL PATHS`, etc.) to apply a uniform path search strategy to the entire graph pattern.

```gql
MATCH (n)-[e]->(m) KEEP ALL PATHS RETURN n
```

### G010 — Explicit WALK keyword

Allows the explicit `WALK` keyword in path mode positions. A walk permits repeated visits to the same node or edge (the least restrictive path mode).

```gql
MATCH ALL WALK PATHS (n)-[e]->(m) RETURN n
```

### G011 — Advanced path modes: TRAIL

Enables `TRAIL` mode which requires all edges in the path to be distinct, but allows nodes to repeat. Useful for finding unique edge sequences.

```gql
MATCH ALL TRAIL PATHS (n)-[e]->(m) RETURN n
```

### G012 — Advanced path modes: SIMPLE

Enables `SIMPLE` mode which requires all nodes (except possibly the first and last) to be distinct. Prevents cycles within the matched path.

```gql
MATCH ALL SIMPLE PATHS (n)-[e]->(m) RETURN n
```

### G013 — Advanced path modes: ACYCLIC

Enables `ACYCLIC` mode which requires all nodes to be distinct, including the endpoints. Stricter than `SIMPLE` — no node may appear twice.

```gql
MATCH ALL ACYCLIC PATHS (n)-[e]->(m) RETURN n
```

### G014 — Explicit PATH/PATHS keywords

Allows the explicit `PATH` or `PATHS` keyword after a path search prefix for readability (e.g., `ALL PATHS` instead of just `ALL`).

```gql
MATCH ALL PATHS (n)-[e]->(m) RETURN n
```

### G015 — All path search: explicit ALL keyword

Enables the `ALL` path search prefix to request every matching path, rather than an arbitrary single match.

```gql
MATCH ALL SIMPLE PATHS (n)-[e]->(m) RETURN n
```

### G016 — Any path search

Enables the `ANY` path search prefix to request a single arbitrary matching path, which may be more efficient than finding all paths.

```gql
MATCH ANY (n)-[e]->(m) RETURN n
```

### G017 — All shortest path search

Enables `ALL SHORTEST` to find every shortest path between matched endpoints. Returns all paths that tie for the minimum length.

```gql
MATCH ALL SHORTEST (n)-[e]->(m) RETURN n
```

### G018 — Any shortest path search

Enables `ANY SHORTEST` to find a single shortest path between matched endpoints. More efficient than `ALL SHORTEST` when only one path is needed.

```gql
MATCH ANY SHORTEST (n)-[e]->(m) RETURN n
```

### G019 — Counted shortest path search

Enables `SHORTEST k` to find the *k* shortest paths between endpoints, ordered by path length. Provides a bounded set of shortest paths.

```gql
MATCH SHORTEST 5 (n)-[e]->(m) RETURN n
```

### G020 — Counted shortest group search

Enables `SHORTEST k GROUP` to find paths grouped by length, returning the *k* shortest length groups. Each group contains all paths of that length.

```gql
MATCH SHORTEST 3 GROUP (n)-[e]->(m) RETURN n
```

### G030 — Path multiset alternation

Enables the `|+|` operator to combine two path patterns as a multiset alternation. Both branches are tried and all matches from both sides are returned.

```gql
MATCH (a)-[e1]->(b) |+| (c)-[e2]->(d) RETURN a
```

### G031 — Path multiset alternation: variable length path operands

Extends multiset alternation (`|+|`) to support quantified path operands (e.g., `*`, `{1,5}`), enabling alternation between variable-length paths.

```gql
MATCH (a)-[e1]->(b)* |+| (c)-[e2]->(d) RETURN a
```

### G032 — Path pattern union

Enables the `|` operator for path pattern union. Matches either the left or right pattern (like SQL `UNION` but for paths).

```gql
MATCH (a)-[e1]->(b) | (c)-[e2]->(d) RETURN a
```

### G033 — Path pattern union: variable length path operands

Extends path pattern union (`|`) to support quantified path operands, enabling union between variable-length path patterns.

```gql
MATCH (a)-[e1]->(b)* | (c)-[e2]->(d) RETURN a
```

### G035 — Quantified paths

Enables quantifiers (`*`, `+`, `{n,m}`) on a path primary that is not an edge pattern. Without this feature, a quantified path primary must contain an edge pattern.

```gql
MATCH ((a)-[e]->(b))* RETURN a
```

### G036 — Quantified edges

Enables quantifiers (`*`, `+`, `{n,m}`) on a path primary that is an edge pattern. Without this feature, a quantified path primary must not contain an edge pattern.

```gql
MATCH (a)-[e]->{1,5}(b) RETURN a
```

### G037 — Questioned paths

Enables the `?` quantifier on path patterns, making a sub-path optional (zero or one occurrence). Equivalent to `{0,1}`.

```gql
MATCH (a)-[e]->(b)? RETURN a
```

### G038 — Parenthesized path pattern expression

Allows path patterns to be enclosed in parentheses for grouping, without requiring a quantifier. Useful for clarity and composition.

```gql
MATCH ((a)-[e]->(b)) RETURN a
```

### G039 — Simplified path pattern expression: full defaulting

Enables simplified path notation using `~/` and `/~` delimiters with full defaulting of direction (undirected). Compact syntax for label-based traversals.

```gql
MATCH ~/ Person /~ RETURN 1
```

### G041 — Non-local element pattern predicates

Allows predicates inside an edge or node pattern to reference variables from outside that pattern (e.g., `[e WHERE a.age > 5]`). Enables correlated filtering.

```gql
MATCH (a)-[e WHERE a.age > 5]->(b) RETURN a
```

### G043 — Complete full edge patterns

Enables full edge patterns in all directions: left-pointing (`<-[r]-`), undirected (`~[r]~`), and any-direction (`-[r]-`), beyond the default right-pointing pattern.

```gql
MATCH (a)<-[r]-(b) RETURN a
```

### G044 — Basic abbreviated edge patterns

Enables abbreviated edge patterns without a binding variable: `<-` (left), `->` (right), and `-` (any direction). Shorter syntax when edge properties aren't needed.

```gql
MATCH (a)->(b) RETURN a
```

### G045 — Complete abbreviated edge patterns

Extends abbreviated patterns with undirected (`~`), left-or-undirected (`<~`), undirected-or-right (`~>`), and bidirectional (`<->`) forms.

```gql
MATCH (a)~(b) RETURN a
```

### G046 — Relaxed topological consistency: adjacent vertex patterns

Allows two node patterns to appear consecutively without an edge pattern between them (e.g., `(a)(b)`), enabling flexible pattern composition.

```gql
MATCH (a)(b) RETURN a
```

### G047 — Relaxed topological consistency: concise edge patterns

Allows edge patterns without adjacent node patterns on both sides (e.g., `-[r]->`), relaxing the requirement that edges be bounded by node patterns.

```gql
MATCH -[r]-> RETURN a
```

### G048 — Parenthesized path pattern: subpath variable declaration

Allows declaring a subpath variable inside a parenthesized path pattern (e.g., `(p = (a)-[e]->(b))`), enabling named sub-paths within larger patterns.

```gql
MATCH (p = (a)-[e]->(b)) RETURN a
```

### G049 — Parenthesized path pattern: path mode prefix

Allows a path mode prefix (`WALK`, `TRAIL`, etc.) inside a parenthesized path pattern, scoping the mode to just that sub-pattern.

```gql
MATCH (WALK (a)-[e]->(b)) RETURN a
```

### G050 — Parenthesized path pattern: WHERE clause

Allows a `WHERE` clause inside a parenthesized path pattern to filter matches based on the sub-pattern's local bindings.

```gql
MATCH ((a)-[e]->(b) WHERE e.weight > 5) RETURN a
```

### G051 — Parenthesized path pattern: non-local predicates

Extends parenthesized path pattern `WHERE` clauses to reference variables outside the parenthesized scope, enabling correlated sub-pattern filtering.

```gql
MATCH (a)-[e]->((b)-[f]->(c) WHERE a.age > 5) RETURN a
```

### G060 — Bounded graph pattern quantifiers

Enables bounded quantifiers on graph patterns using `{n}` (exact) or `{n,m}` (range) syntax to match a specific number of repetitions.

```gql
MATCH (n:Person){1,5} RETURN n
```

### G061 — Unbounded graph pattern quantifiers

Enables unbounded quantifiers: `*` (zero or more) and `{n,}` (at least *n*). Essential for variable-length path matching without an upper bound.

```gql
MATCH (n:Person)* RETURN n
```

### G074 — Label expression: wildcard label

Enables the `%` wildcard in label expressions to match any label. Useful for writing queries that match nodes/edges regardless of their label.

```gql
MATCH (n:%) RETURN n
```

### G080 — Simplified path pattern expression: basic defaulting

Enables simplified path notation using `-/` and `/-` delimiters with basic direction defaulting (left `<-/`, right `/->`, any `-/`).

```gql
MATCH -/ Person /-> RETURN 1
```

### G081 — Simplified path pattern expression: full overrides

Extends simplified path patterns with full direction overrides using tilde-based syntax (`<~`, `~>`) inside the simplified delimiters.

```gql
MATCH -/ <~ Person /- RETURN 1
```

### G082 — Simplified path pattern expression: basic overrides

Extends simplified path patterns with basic direction overrides using `<` (left) and `-` (any) inside the simplified delimiters.

```gql
MATCH -/ < Person /- RETURN 1
```

### G100 — ELEMENT_ID function

Provides the `ELEMENT_ID()` function to retrieve the implementation-defined unique identifier of a node or edge element.

```gql
MATCH (n) RETURN ELEMENT_ID(n)
```

### G110 — IS DIRECTED predicate

Enables the `IS DIRECTED` predicate to test whether an edge is directed. Useful when working with graphs that contain both directed and undirected edges.

```gql
MATCH (n)-[e]->(m) WHERE e IS DIRECTED RETURN e
```

### G111 — IS LABELED predicate

Enables the `IS LABELED` (or colon shorthand) predicate to test whether an element has a specific label at query time, as opposed to in the pattern.

```gql
MATCH (n:Person) WHERE n:Person RETURN n
```

### G112 — IS SOURCE and IS DESTINATION predicate

Enables `IS SOURCE OF` and `IS DESTINATION OF` predicates to check the topological role of a node relative to an edge.

```gql
MATCH (n)-[e]->(m) WHERE n IS SOURCE OF e RETURN n
```

### G113 — ALL_DIFFERENT predicate

Provides the `ALL_DIFFERENT()` function to verify that all given elements are distinct. Useful for enforcing uniqueness across multiple pattern variables.

```gql
MATCH (a)-[e1]->(b), (c)-[e2]->(d) WHERE ALL_DIFFERENT(a,c) RETURN a
```

### G114 — SAME predicate

Provides the `SAME()` function to test whether two or more element references refer to the same underlying graph element.

```gql
MATCH (a)-[e1]->(b), (c)-[e2]->(d) WHERE SAME(a,c) RETURN a
```

### G115 — PROPERTY_EXISTS predicate

Provides the `PROPERTY_EXISTS()` function to test whether a specific property exists on an element, useful for sparse property graphs.

```gql
MATCH (n:Person) WHERE PROPERTY_EXISTS(n, name) RETURN n
```

## Advanced

Advanced query features for type operations, ordering, and comparisons.

### GA01 — IEEE 754 floating point operations

Specifies that floating-point arithmetic follows IEEE 754 semantics, including handling of NaN, infinity, and signed zero.

*INACTIVE*

### GA03 — Explicit ordering of nulls

Enables `NULLS FIRST` and `NULLS LAST` modifiers in `ORDER BY` to control where null values appear in sorted results.

```gql
MATCH (n) RETURN n ORDER BY n.name NULLS FIRST
```

### GA04 — Universal comparison

When absent, restricts comparisons to type-compatible operands (e.g., string vs. string). When present, allows comparisons between any two values regardless of type.

```gql
MATCH (n) WHERE 'hello' = 1 RETURN n
```

### GA05 — Cast specification

Enables the `CAST(expr AS type)` expression to explicitly convert a value from one type to another (e.g., integer to string).

```gql
MATCH (n) RETURN CAST(n.prop AS STRING)
```

### GA06 — Value type predicate

Enables `IS TYPED` and `IS NOT TYPED` predicates to test whether a value conforms to a specific GQL value type at runtime.

```gql
MATCH (n) WHERE n.age IS TYPED INT32 RETURN n
```

### GA07 — Ordering by discarded binding variables

When absent, prevents `ORDER BY` from referencing binding variables not present in the `RETURN` projection. When present, allows sorting by any matched variable.

```gql
MATCH (n)-[e]->(m) RETURN n ORDER BY m
```

### GA08 — GQL-status objects with diagnostic records

Specifies structured error reporting via GQL-status objects containing diagnostic records with standardized error codes and messages.

*INACTIVE*

### GA09 — Comparison of paths

When absent, prevents path values from being compared with `=`, `<>`, `<`, `>`, etc. When present, allows path equality and ordering comparisons.

```gql
MATCH p = (a)-[e]->(b), q = (c)-[f]->(d) WHERE p = q RETURN p
```

## Basic syntax

Fundamental syntactic features for identifiers and comments.

### GB01 — Long identifiers

Allows identifiers longer than the GQL base limit (128 characters). Implementations without this feature must reject identifiers exceeding 128 characters.

```gql
MATCH (n) RETURN n.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

### GB02 — Double minus sign comments

Enables `--` line comments (SQL-style). Everything from `--` to end of line is treated as a comment and ignored by the parser.

```gql
-- comment
MATCH (n) RETURN n
```

### GB03 — Double solidus comments

Enables `//` line comments (C-style). Everything from `//` to end of line is treated as a comment and ignored by the parser.

```gql
// comment
MATCH (n) RETURN n
```

## Catalog management

Features for managing schemas, graph types, and graphs in the catalog.

### GC01 — Graph schema management

Enables `CREATE SCHEMA` and `DROP SCHEMA` statements to manage named schemas in the catalog. Schemas organize graphs and types.

```gql
CREATE SCHEMA /myschemas/foo
```

### GC02 — Graph schema management: IF [ NOT ] EXISTS

Adds `IF NOT EXISTS` / `IF EXISTS` guards to schema DDL statements, preventing errors when creating an existing schema or dropping a missing one.

```gql
CREATE SCHEMA IF NOT EXISTS /myschemas/bar
```

### GC03 — Graph type: IF [ NOT ] EXISTS

Adds `IF NOT EXISTS` / `IF EXISTS` guards to graph type DDL statements, enabling idempotent graph type creation and deletion.

```gql
DROP GRAPH TYPE IF EXISTS my_type
```

### GC04 — Graph management

Enables `CREATE PROPERTY GRAPH` and `DROP GRAPH` statements to manage named graphs in the catalog.

```gql
CREATE PROPERTY GRAPH my_graph_of_type LIKE CURRENT_GRAPH
```

### GC05 — Graph management: IF [ NOT ] EXISTS

Adds `IF NOT EXISTS` / `IF EXISTS` guards to graph DDL statements, enabling idempotent graph creation and deletion.

```gql
DROP PROPERTY GRAPH IF EXISTS my_graph
```

## DML (Data Manipulation)

Features for modifying graph data: inserts, updates, and deletes.

### GD01 — Updatable graphs

Enables data modification statements (`SET`, `REMOVE`, `DELETE`, `INSERT`) and procedure calls that mutate graph data.

```gql
SET n.prop = 1
```

### GD02 — Graph label set changes

Enables `SET label` and `REMOVE label` to add or remove labels from nodes and edges, allowing dynamic label management.

```gql
MATCH (n:Person) SET n:Employee
```

### GD03 — DELETE statement: subquery support

Allows nested subqueries inside `DELETE` items. Implies GD04.

```gql
DELETE VALUE { MATCH (n:Temp) RETURN n }
```

### GD04 — DELETE statement: simple expression support

Allows `DELETE` items to be arbitrary expressions, not just variable references.

```gql
MATCH (n) DELETE CASE WHEN n.expired THEN n ELSE null END
```

## Expressions

Value expressions beyond basic property access and literals.

### GE01 — Graph reference value expressions

Enables `GRAPH name` expressions to reference a named graph as a first-class value that can be returned or passed.

```gql
RETURN GRAPH my_graph
```

### GE02 — Binding table reference value expressions

Enables `TABLE { ... }` expressions to create binding table values from subqueries, making tables first-class values.

```gql
RETURN TABLE { MATCH (n) RETURN n }
```

### GE03 — Let-binding of variables in expressions

Enables `LET x = expr IN body END` expressions for local variable binding within a value expression, similar to functional `let` constructs.

```gql
RETURN LET x = 1 IN x + 1 END
```

### GE04 — Graph parameters

Allows session parameters of graph type (e.g., `$g`) to be used where a graph reference is expected, such as in `USE $g`.

```gql
USE $g MATCH (n) RETURN n
```

### GE05 — Binding table parameters

Allows session parameters of binding table type (e.g., `$t`) to be used where a table reference is expected.

```gql
MATCH (n) WHERE n.name = $t RETURN n
```

### GE06 — Path value construction

Enables `PATH [...]` to construct path values from element references, and `||` to concatenate two path values.

```gql
RETURN PATH [a] || PATH [b]
```

### GE07 — Boolean XOR

Adds the `XOR` boolean operator (exclusive or). Returns true when exactly one operand is true.

```gql
MATCH (n) WHERE TRUE XOR FALSE RETURN n
```

### GE08 — Reference parameters

Enables `$$name` reference parameters that refer to catalog objects (graphs, tables) rather than scalar values.

```gql
RETURN GRAPH $$my_graph
```

### GE09 — Horizontal aggregation

When present, allows aggregate functions (like `COUNT`, `SUM`) inside list constructors (e.g., `[COUNT(n)]`), enabling aggregation within collection expressions.

```gql
MATCH (n) RETURN [COUNT(n)]
```

## Functions

Built-in functions for numeric operations, string manipulation, path analysis, and aggregation.

### GF01 — Enhanced numeric functions

Provides `ABS()`, `MOD()`, `FLOOR()`, `CEILING()`, and `SQRT()` numeric functions beyond the basic arithmetic operators.

```gql
RETURN ABS(-5)
```

### GF02 — Trigonometric functions

Provides trigonometric functions: `SIN()`, `COS()`, `TAN()`, `ASIN()`, `ACOS()`, `ATAN()`, and `DEGREES()`/`RADIANS()`.

```gql
RETURN SIN(1)
```

### GF03 — Logarithmic functions

Provides `LOG(base, value)`, `LOG10()`, `LN()`, `EXP()`, and `POWER()` functions for logarithmic and exponential operations.

```gql
RETURN LOG10(100)
```

### GF04 — Enhanced path functions

Provides `ELEMENTS(path)` to extract the list of elements in a path, and `PATH_LENGTH(path)` to get the number of edges.

```gql
MATCH p = (a)-[]->(b) RETURN ELEMENTS(p)
```

### GF05 — Multi-character TRIM function

Provides `LTRIM()` and `RTRIM()` convenience functions for trimming whitespace from the left or right side of a string.

```gql
RETURN LTRIM("hello")
```

### GF06 — Explicit TRIM function

Provides the full `TRIM(LEADING|TRAILING|BOTH FROM string)` syntax for precise control over which characters are removed and from which end.

```gql
RETURN TRIM(LEADING FROM "hello")
```

### GF07 — Byte string TRIM function

Extends `TRIM()` to work on byte strings, allowing removal of specific byte values from binary data.

```gql
RETURN TRIM(X'00' FROM X'001122')
```

### GF10 — Advanced aggregate functions: general set functions

Adds `COLLECT_LIST()`, `STDDEV_SAMP()`, and `STDDEV_POP()` aggregate functions for collecting values into lists and computing standard deviations.

```gql
MATCH (n) RETURN COLLECT_LIST(n.name)
```

### GF11 — Advanced aggregate functions: binary set functions

Adds `PERCENTILE_CONT()` and `PERCENTILE_DISC()` binary aggregate functions for computing continuous and discrete percentiles.

```gql
MATCH (n) RETURN PERCENTILE_CONT(n.score, 0.5)
```

### GF12 — CARDINALITY function

Provides `CARDINALITY()` to return the number of elements in a list or the number of entries in a record.

```gql
RETURN CARDINALITY([1, 2, 3])
```

### GF13 — SIZE function

Provides `SIZE()` as an alternative to `CARDINALITY()` for returning the number of elements in a list.

```gql
RETURN SIZE([1, 2, 3])
```

### GF20 — Aggregate functions in sort keys

Allows aggregate function calls (e.g., `COUNT(*)`) to appear in `ORDER BY` sort keys, enabling sorting by aggregated values.

```gql
MATCH (n) RETURN n.name AS name ORDER BY COUNT(*)
```

## Graph types

Features for defining and managing graph type schemas.

### GG01 — Graph with an open graph type

Enables `ANY PROPERTY GRAPH` as a graph type, creating a graph that accepts any node and edge structure without schema constraints.

```gql
CREATE PROPERTY GRAPH my_graph ANY PROPERTY GRAPH
```

### GG02 — Graph with a closed graph type

Enables creating graphs with closed (schema-constrained) graph types, and the `CREATE/DROP GRAPH TYPE` statements for managing named types.

```gql
CREATE PROPERTY GRAPH TYPE my_type LIKE CURRENT_GRAPH
```

### GG03 — Graph type inline specification

Allows defining a graph type inline using `{ ... }` syntax within a `CREATE PROPERTY GRAPH` statement instead of referencing a named type.

```gql
CREATE PROPERTY GRAPH my_graph { (n) }
```

### GG04 — Graph type like a graph

Enables `LIKE graph_ref` to create a graph type by copying the schema of an existing graph.

```gql
CREATE PROPERTY GRAPH my_graph LIKE CURRENT_GRAPH
```

### GG05 — Graph from a graph source

Enables `AS COPY OF graph_ref` to populate a new graph with data copied from an existing graph, combined with a type specification.

```gql
CREATE PROPERTY GRAPH my_graph LIKE CURRENT_GRAPH AS COPY OF CURRENT_GRAPH
```

### GG20 — Explicit element type names

Allows naming node and edge types in graph type definitions (e.g., `NODE TYPE Person`, `EDGE TYPE Knows`) for documentation and referencing.

```gql
CREATE GRAPH TYPE my_type { NODE TYPE Person }
```

### GG21 — Explicit element type key label sets

Enables declaring key label sets on element types using `:Label =>` syntax, which constrains and identifies element types by their labels.

```gql
CREATE GRAPH TYPE my_type { NODE TYPE :Person => }
```

### GG22 — Element type key label set inference

Allows the implementation to automatically infer key label sets for element types based on the graph's data, rather than requiring explicit declaration.

*INACTIVE*

### GG23 — Optional element type key label sets

Makes key label sets optional in element type definitions. Without this, every element type must declare its key labels.

*INACTIVE*

### GG24 — Relaxed structural consistency

Relaxes the requirement that all elements with the same key label set must have the same property set, allowing structural variation within a label.

*INACTIVE*

### GG25 — Relaxed key label set uniqueness for edge types

Allows multiple edge types to share the same key label set within a graph type, relaxing the default uniqueness constraint.

*INACTIVE*

### GG26 — Relaxed property value type consistency

Allows properties with the same name but different value types across element types, relaxing the default type consistency requirement.

*INACTIVE*

## Miscellaneous

Features that don't fit neatly into other categories.

### GH01 — External object references

Enables referencing external objects (e.g., via URI strings) in graph type definitions using `COPY OF 'uri'` syntax.

```gql
CREATE PROPERTY GRAPH TYPE my_type COPY OF 'http://example.com/type'
```

### GH02 — Undirected edge patterns

Enables undirected edge syntax using `~[e]~` in patterns and `UNDIRECTED EDGE TYPE` in graph type definitions. Required for graphs with bidirectional relationships.

```gql
INSERT ()~[e]~()
```

## Literals

Features for numeric, string, and temporal literal formats.

### GL01 — Hexadecimal literals

Allows integer literals in base-16 using `0x` or `0X` prefix (e.g., `0xFF`, `0xDEADBEEF`). Useful for bitwise operations and hash values.

```gql
RETURN 0x1A2B
```

### GL02 — Octal literals

Allows integer literals in base-8 using `0o` or `0O` prefix (e.g., `0o755`). Commonly used for file permission values.

```gql
RETURN 0o755
```

### GL03 — Binary literals

Allows integer literals in base-2 using `0b` or `0B` prefix (e.g., `0b1010`). Useful for bitfield manipulation.

```gql
RETURN 0b1010
```

### GL04 — Exact number in common notation without suffix

Allows decimal numbers with a decimal point but no suffix (e.g., `3.14`). These are exact numeric values, not floating-point approximations.

```gql
RETURN 3.14
```

### GL05 — Exact number in common notation or as decimal integer with suffix

Enables the `m`/`M` suffix on decimal or integer literals (e.g., `123m`, `3.14m`) to explicitly mark them as exact decimal numbers.

```gql
RETURN 123m
```

### GL06 — Exact number in scientific notation with suffix

Enables scientific notation with the `m`/`M` suffix (e.g., `1.23e10m`) for exact decimal values in scientific form.

```gql
RETURN 1.23e10m
```

### GL07 — Approximate number in common notation or as decimal integer with suffix

Enables `f`/`d` suffixes on common-notation or integer literals (e.g., `3.14f`, `123d`) to mark them as floating-point approximations.

```gql
RETURN 3.14f
```

### GL08 — Approximate number in scientific notation with suffix

Enables `f`/`d` suffixes on scientific-notation literals (e.g., `1.23e10f`) to mark them as approximate floating-point values.

```gql
RETURN 1.23e10f
```

### GL09 — Optional float number suffix

Enables the `f`/`F` suffix on numeric literals to explicitly request 32-bit single-precision floating-point representation.

```gql
RETURN 3.14f
```

### GL10 — Optional double number suffix

Enables the `d`/`D` suffix on numeric literals to explicitly request 64-bit double-precision floating-point representation.

```gql
RETURN 3.14d
```

### GL11 — Opt-out character escaping

Enables `@'...'` and `@"..."` string literal syntax where backslash and delimiter-doubling escapes are disabled. The string content is taken literally.

```gql
RETURN @'hello'
```

### GL12 — SQL datetime and interval formats

Enables SQL-style interval literals using `INTERVAL 'value' qualifier` syntax (e.g., `INTERVAL '1' YEAR`, `INTERVAL '1-6' YEAR TO MONTH`).

```gql
RETURN INTERVAL '1' YEAR
```

## Procedures

Features for inline and named procedure calls, variable definitions, and scope control.

### GP01 — Inline procedure

Enables `CALL { ... }` to invoke an anonymous inline procedure within a query. The procedure body is a full query that runs in a nested scope.

```gql
MATCH (n) CALL { MATCH (m) RETURN m } RETURN n
```

### GP02 — Inline procedure with implicit nested variable scope

Allows inline procedures to implicitly access variables from the enclosing query scope. All outer variables are visible inside the procedure body.

```gql
MATCH (n) CALL { MATCH (m) RETURN m } RETURN n
```

### GP03 — Inline procedure with explicit nested variable scope

Enables `CALL (vars) { ... }` syntax to explicitly declare which outer variables are visible inside the procedure body, restricting the scope.

```gql
MATCH (n) CALL (n) { MATCH (n)-[]->(m) RETURN m } RETURN n
```

### GP04 — Named procedure calls

Enables calling pre-registered named procedures with arguments via `CALL name(args) YIELD columns`. Results are projected via `YIELD`.

```gql
CALL my_proc() YIELD result RETURN result
```

### GP05 — Procedure-local value variable definitions

Enables `VALUE x = expr` syntax to define local value variables within a procedure body or query prefix.

```gql
VALUE x = 1 MATCH (n) RETURN n
```

### GP06 — Procedure-local value variable definitions: value variables based on simple expressions

Allows value variables to be initialized from simple expressions (literals, arithmetic, etc.) rather than requiring subqueries.

```gql
VALUE x = 1 MATCH (n) RETURN n
```

### GP07 — Procedure-local value variable definitions: value variable based on subqueries

Allows value variables to be initialized from subqueries via `VALUE { ... }`, enabling derived scalar values from query results.

```gql
VALUE x = VALUE { MATCH (n) RETURN n.prop } MATCH (m) RETURN m
```

### GP08 — Procedure-local binding table variable definitions

Enables `TABLE t = expr` syntax to define local binding table variables that can be queried by subsequent statements.

```gql
TABLE t = { MATCH (n) RETURN n } MATCH (m) RETURN m
```

### GP09 — Procedure-local binding table variable definitions: binding table variables based on simple expressions or references

Allows table variables to be initialized from named table references (e.g., `TABLE t = my_table`).

```gql
TABLE t = my_table MATCH (n) RETURN n
```

### GP10 — Procedure-local binding table variable definitions: binding table variables based on subqueries

Allows table variables to be initialized from subqueries (e.g., `TABLE t = { MATCH ... RETURN ... }`).

```gql
TABLE t = { MATCH (n) RETURN n } MATCH (m) RETURN m
```

### GP11 — Procedure-local graph variable definitions

Enables `GRAPH g = expr` syntax to define local graph variables that subsequent statements can operate on.

```gql
GRAPH g = my_graph MATCH (n) RETURN n
```

### GP12 — Procedure-local graph variable definitions: graph variables based on simple expressions or references

Allows graph variables to be initialized from named graph references or simple expressions.

```gql
GRAPH g = my_graph MATCH (n) RETURN n
```

### GP13 — Procedure-local graph variable definitions: graph variables based on subqueries

Allows graph variables to be initialized from subqueries via `VALUE { ... }`, deriving a graph from query results.

```gql
GRAPH g = VALUE { MATCH (n) RETURN n } MATCH (m) RETURN m
```

### GP14 — Binding tables as procedure arguments

Allows binding table values to be passed as arguments to named procedure calls.

```gql
CALL my_proc(TABLE t)
```

### GP15 — Graphs as procedure arguments

Allows graph values to be passed as arguments to named procedure calls.

```gql
CALL my_proc(GRAPH CURRENT_GRAPH)
```

### GP16 — AT schema clause

Enables the `AT schema_ref` clause inside procedure bodies to direct the procedure to execute against a specific schema.

```gql
CALL { AT /myschemas/foo MATCH (n) RETURN n } RETURN 1
```

### GP17 — Binding variable definition block

Allows variable definition blocks (`VALUE`, `TABLE`, `GRAPH` definitions) inside inline procedure bodies.

```gql
CALL { VALUE x = 1 MATCH (n) RETURN n } RETURN 1
```

### GP18 — Catalog and data statement mixing

Allows mixing catalog-modifying statements (`CREATE SCHEMA`, etc.) with data-modifying statements within a single procedure body via `NEXT`.

```gql
CALL { CREATE SCHEMA /s NEXT SET n.prop = 1 } RETURN 1
```

## Query composition

Features for combining, filtering, and structuring query results.

### GQ01 — USE graph clause

Enables the `USE graph_ref` clause to set the working graph for the subsequent query, overriding the session default.

```gql
USE my_graph MATCH (n) RETURN n
```

### GQ02 — Composite query: OTHERWISE

Enables `OTHERWISE` to combine two queries such that the second runs only if the first produces no results (like `COALESCE` for queries).

```gql
MATCH (n) RETURN n OTHERWISE MATCH (m) RETURN m
```

### GQ03 — Composite query: UNION

Enables `UNION` (default: `DISTINCT`) to combine results from two queries, removing duplicate rows.

```gql
MATCH (n) RETURN n UNION MATCH (m) RETURN m
```

### GQ04 — Composite query: EXCEPT DISTINCT

Enables `EXCEPT` and `EXCEPT DISTINCT` to subtract the second query's results from the first, removing duplicates.

```gql
MATCH (n) RETURN n EXCEPT MATCH (m) RETURN m
```

### GQ05 — Composite query: EXCEPT ALL

Enables `EXCEPT ALL` to subtract results while preserving duplicate counts (multiset subtraction).

```gql
MATCH (n) RETURN n EXCEPT ALL MATCH (m) RETURN m
```

### GQ06 — Composite query: INTERSECT DISTINCT

Enables `INTERSECT` and `INTERSECT DISTINCT` to keep only rows present in both queries, removing duplicates.

```gql
MATCH (n) RETURN n INTERSECT MATCH (m) RETURN m
```

### GQ07 — Composite query: INTERSECT ALL

Enables `INTERSECT ALL` to intersect results while preserving duplicate counts (multiset intersection).

```gql
MATCH (n) RETURN n INTERSECT ALL MATCH (m) RETURN m
```

### GQ08 — FILTER statement

Enables the `FILTER WHERE condition` statement to filter the current binding table without changing its schema, similar to SQL's `HAVING`.

```gql
MATCH (n) FILTER WHERE n.age > 21 RETURN n
```

### GQ09 — LET statement

Enables the `LET x = expr` statement to introduce computed binding variables into the current scope for use in later statements.

```gql
MATCH (n) LET x = n.age RETURN x
```

### GQ10 — FOR statement: list value support

Enables `FOR x IN list_expr` to iterate over a list value, producing one row per list element. GQL's equivalent of `UNWIND`.

```gql
FOR x IN [1, 2, 3] RETURN x
```

### GQ11 — FOR statement: WITH ORDINALITY

Extends `FOR` with `WITH ORDINALITY i` to also bind a 1-based index variable alongside each list element.

```gql
FOR x IN [1, 2, 3] WITH ORDINALITY i RETURN x, i
```

### GQ12 — ORDER BY and page statement: OFFSET clause

Enables the `OFFSET n` clause to skip a specified number of rows from the sorted result, enabling pagination.

```gql
MATCH (n) RETURN n ORDER BY n.name OFFSET 10
```

### GQ13 — ORDER BY and page statement: LIMIT clause

Enables the `LIMIT n` clause to restrict the number of rows returned, enabling pagination and top-N queries.

```gql
MATCH (n) RETURN n ORDER BY n.name LIMIT 10
```

### GQ14 — Complex expressions in sort keys

Allows sort keys in `ORDER BY` to be arbitrary expressions (e.g., `n.name || n.surname`), not just simple column references.

```gql
MATCH (n) RETURN n.name AS name ORDER BY n.name || n.surname
```

### GQ15 — GROUP BY clause

Enables the `GROUP BY` clause to partition results into groups for aggregation, analogous to SQL's `GROUP BY`.

```gql
MATCH (n) RETURN n GROUP BY n
```

### GQ16 — Pre-projection aliases in sort keys

Allows `ORDER BY` to reference aliases defined in the `RETURN` clause (e.g., `ORDER BY alias`), evaluated before projection.

```gql
MATCH (n) RETURN n.name AS alias ORDER BY alias
```

### GQ17 — Element-wise group variable operations

When present, allows accessing properties of non-grouped variables in `RETURN` with `GROUP BY` (element-wise operations). When absent, only grouped variables and aggregates are allowed.

```gql
MATCH (n)-[e]->(m) RETURN n.name, m.age GROUP BY n
```

### GQ18 — Scalar subqueries

Enables `VALUE { ... }` subquery expressions that return a single scalar value, usable anywhere a value expression is expected.

```gql
MATCH (n) RETURN VALUE { MATCH (m) RETURN m.x }
```

### GQ19 — Graph pattern YIELD clause

Enables the `YIELD` clause on graph patterns to explicitly select which binding variables from a match are passed to subsequent statements.

```gql
MATCH (n)-[e]->(m) YIELD n, m RETURN n
```

### GQ20 — Advanced linear composition with NEXT

Enables the `NEXT` keyword between statements to explicitly chain them in a linear pipeline, passing results from one to the next.

```gql
MATCH (n) NEXT RETURN n
```

### GQ21 — OPTIONAL: Multiple MATCH statements

Allows multiple `MATCH` statements within an `OPTIONAL { ... }` block, enabling optional patterns with intermediate processing.

```gql
OPTIONAL { MATCH (n) MATCH (m) } RETURN n, m
```

### GQ22 — EXISTS predicate: multiple MATCH statements

Allows multiple `MATCH` statements within an `EXISTS { ... }` predicate, enabling complex existence checks.

```gql
MATCH (n) WHERE EXISTS { MATCH (n) MATCH (m) } RETURN n
```

### GQ23 — FOR statement: binding table support

Enables `FOR x IN TABLE t` to iterate over a binding table reference, producing one row per table entry.

```gql
FOR x IN TABLE t RETURN x
```

### GQ24 — FOR statement: WITH OFFSET

Extends `FOR` with `WITH OFFSET i` to bind a 0-based index variable alongside each element (contrast with 1-based `ORDINALITY`).

```gql
FOR x IN [1, 2, 3] WITH OFFSET i RETURN x, i
```

## Session

Features for configuring session parameters, schema, graph, and time zone.

### GS01 — SESSION SET command: session-local graph parameters

Enables `SESSION SET GRAPH $name = expr` to bind a graph value to a session parameter for use across multiple queries.

```gql
SESSION SET GRAPH $g = my_graph
```

### GS02 — SESSION SET command: session-local binding table parameters

Enables `SESSION SET TABLE $name = expr` to bind a binding table to a session parameter.

```gql
SESSION SET TABLE $t = my_table
```

### GS03 — SESSION SET command: session-local value parameters

Enables `SESSION SET VALUE $name = expr` to bind a scalar value to a session parameter.

```gql
SESSION SET VALUE $v = 42
```

### GS04 — SESSION RESET command: reset all characteristics

Enables bulk reset forms of `SESSION RESET`: bare `SESSION RESET` (no arguments), `SESSION RESET CHARACTERISTICS`, and `SESSION RESET PARAMETERS`. Without this feature, only targeted resets are allowed (e.g. `SESSION RESET SCHEMA`, `SESSION RESET GRAPH`).

```gql
SESSION RESET
SESSION RESET CHARACTERISTICS
SESSION RESET PARAMETERS
```

### GS05 — SESSION RESET command: reset session schema

Enables `SESSION RESET SCHEMA` to reset the session schema to the default without affecting other session state.

```gql
SESSION RESET SCHEMA
```

### GS06 — SESSION RESET command: reset session graph

Enables `SESSION RESET GRAPH` to reset the session graph to the default without affecting other session state.

```gql
SESSION RESET GRAPH
```

### GS07 — SESSION RESET command: reset time zone displacement

Enables `SESSION RESET TIME ZONE` to reset the session time zone to the server default.

```gql
SESSION RESET TIME ZONE
```

### GS08 — SESSION RESET command: reset all session parameters

Enables `SESSION RESET ALL PARAMETERS` to clear all user-defined session parameters at once.

```gql
SESSION RESET ALL PARAMETERS
```

### GS10 — SESSION SET command: session-local binding table parameters based on subqueries

Extends table parameter setting to accept subqueries: `SESSION SET TABLE $t = { MATCH ... }`.

```gql
SESSION SET TABLE $t = { MATCH (n) RETURN n }
```

### GS11 — SESSION SET command: session-local value parameters based on sub-queries

Extends value parameter setting to accept subqueries: `SESSION SET VALUE $v = VALUE { MATCH ... }`.

```gql
SESSION SET VALUE $v = VALUE { MATCH (n) RETURN n.prop }
```

### GS12 — SESSION SET command: session-local graph parameters based on simple expressions or references

Specifies that graph parameters can be set from simple graph references or expressions (e.g., named graphs), as opposed to only subqueries.

```gql
SESSION SET GRAPH $g = my_graph
```

### GS13 — SESSION SET command: session-local binding table parameters based on simple expressions or references

Specifies that table parameters can be set from simple table references, as opposed to only subqueries.

```gql
SESSION SET TABLE $t = my_table
```

### GS14 — SESSION SET command: session-local value parameters based on simple expressions

Specifies that value parameters can be set from simple scalar expressions (e.g., literals, arithmetic), as opposed to only subqueries.

```gql
SESSION SET VALUE $v = 42
```

### GS15 — SESSION SET command: set time zone displacement

Enables `SESSION SET TIME ZONE 'zone'` to configure the session's time zone displacement for temporal operations.

```gql
SESSION SET TIME ZONE 'UTC'
```

### GS16 — SESSION RESET command: reset individual session parameters

Enables `SESSION RESET PARAMETER $name` to reset a single named session parameter to its default value.

```gql
SESSION RESET PARAMETER $my_param
```

## Transactions

Features for explicit transaction control.

### GT01 — Explicit transaction commands

Enables explicit transaction lifecycle commands: `START TRANSACTION`, `COMMIT`, and `ROLLBACK`.

```gql
START TRANSACTION
```

### GT02 — Specified transaction characteristics

Allows specifying transaction characteristics such as `READ ONLY` or `READ WRITE` when starting a transaction.

```gql
START TRANSACTION READ ONLY
```

### GT03 — Use of multiple graphs in a transaction

Allows a single transaction to span operations across multiple different graphs. Requires transactional coordination across graph boundaries.

*INACTIVE*

## Value types

Features for GQL's type system: integers, floats, strings, bytes, temporal, records, lists, paths, and more.

### GV01 — 8 bit unsigned integer numbers

Adds the `UINT8` (or `UNSIGNED INTEGER8`) value type for 8-bit unsigned integers (0–255).

```gql
MATCH (n) WHERE n.age IS TYPED UINT8 RETURN n
```

### GV02 — 8 bit signed integer numbers

Adds `INT8` / `SIGNED INTEGER8` / `INTEGER8` value types for 8-bit signed integers (-128 to 127).

```gql
MATCH (n) WHERE n.age IS TYPED INT8 RETURN n
```

### GV03 — 16 bit unsigned integer numbers

Adds the `UINT16` (or `UNSIGNED INTEGER16`) value type for 16-bit unsigned integers (0–65535).

```gql
MATCH (n) WHERE n.age IS TYPED UINT16 RETURN n
```

### GV04 — 16 bit signed integer numbers

Adds `INT16` / `SIGNED INTEGER16` / `INTEGER16` value types for 16-bit signed integers.

```gql
MATCH (n) WHERE n.age IS TYPED INT16 RETURN n
```

### GV05 — Small unsigned integer numbers

Adds the `USMALLINT` (or `UNSIGNED SMALL INTEGER`) value type as a named alias for small unsigned integers.

```gql
MATCH (n) WHERE n.age IS TYPED USMALLINT RETURN n
```

### GV06 — 32 bit unsigned integer numbers

Adds the `UINT32` (or `UNSIGNED INTEGER32`) value type for 32-bit unsigned integers.

```gql
MATCH (n) WHERE n.age IS TYPED UINT32 RETURN n
```

### GV07 — 32 bit signed integer numbers

Adds `INT32` / `SIGNED INTEGER32` / `INTEGER32` value types for 32-bit signed integers. The most commonly used integer type.

```gql
MATCH (n) WHERE n.age IS TYPED INT32 RETURN n
```

### GV08 — Regular unsigned integer numbers

Adds `UINT` (or `UNSIGNED INTEGER`) as a named alias for a regular-width unsigned integer type.

```gql
MATCH (n) WHERE n.age IS TYPED UINT RETURN n
```

### GV09 — Specified integer number precision

Allows specifying integer precision via `INT(p)` or `INTEGER(p)`, where *p* is the number of decimal digits.

```gql
MATCH (n) WHERE n.age IS TYPED INT(10) RETURN n
```

### GV10 — Big unsigned integer numbers

Adds `UBIGINT` (or `UNSIGNED BIG INTEGER`) for large unsigned integer values.

```gql
MATCH (n) WHERE n.age IS TYPED UBIGINT RETURN n
```

### GV11 — 64 bit unsigned integer numbers

Adds the `UINT64` (or `UNSIGNED INTEGER64`) value type for 64-bit unsigned integers.

```gql
MATCH (n) WHERE n.age IS TYPED UINT64 RETURN n
```

### GV12 — 64 bit signed integer numbers

Adds `INT64` / `SIGNED INTEGER64` / `INTEGER64` value types for 64-bit signed integers.

```gql
MATCH (n) WHERE n.age IS TYPED INT64 RETURN n
```

### GV13 — 128 bit unsigned integer numbers

Adds the `UINT128` (or `UNSIGNED INTEGER128`) value type for 128-bit unsigned integers.

```gql
MATCH (n) WHERE n.age IS TYPED UINT128 RETURN n
```

### GV14 — 128 bit signed integer numbers

Adds `INT128` / `INTEGER128` value types for 128-bit signed integers.

```gql
MATCH (n) WHERE n.age IS TYPED INT128 RETURN n
```

### GV15 — 256 bit unsigned integer numbers

Adds the `UINT256` (or `UNSIGNED INTEGER256`) value type for 256-bit unsigned integers.

```gql
MATCH (n) WHERE n.age IS TYPED UINT256 RETURN n
```

### GV16 — 256 bit signed integer numbers

Adds `INT256` / `INTEGER256` value types for 256-bit signed integers.

```gql
MATCH (n) WHERE n.age IS TYPED INT256 RETURN n
```

### GV17 — Decimal numbers

Adds `DECIMAL(p)` / `DEC(p)` value types for exact decimal numbers with specified precision.

```gql
MATCH (n) WHERE n.age IS TYPED DECIMAL(10) RETURN n
```

### GV18 — Small signed integer numbers

Adds `SMALLINT` (or `SMALL INTEGER`) as a named alias for small signed integers.

```gql
MATCH (n) WHERE n.age IS TYPED SMALLINT RETURN n
```

### GV19 — Big signed integer numbers

Adds `BIGINT` (or `BIG INTEGER`) as a named alias for large signed integers.

```gql
MATCH (n) WHERE n.age IS TYPED BIGINT RETURN n
```

### GV20 — 16 bit floating point numbers

Adds the `FLOAT16` value type for 16-bit half-precision floating-point numbers.

```gql
MATCH (n) WHERE n.age IS TYPED FLOAT16 RETURN n
```

### GV21 — 32 bit floating point numbers

Adds the `FLOAT32` value type for 32-bit single-precision floating-point numbers.

```gql
MATCH (n) WHERE n.x IS TYPED FLOAT32 RETURN n
```

### GV22 — Specified floating point number precision

Allows specifying floating-point precision via `FLOAT(p)` or `FLOAT(p, s)`, where *p* is precision and *s* is scale.

```gql
MATCH (n) WHERE n.x IS TYPED FLOAT(10) RETURN n
```

### GV23 — Floating point type name synonyms

Adds `REAL`, `DOUBLE`, and `DOUBLE PRECISION` as alternative names for floating-point types, following SQL conventions.

```gql
MATCH (n) WHERE n.x IS TYPED REAL RETURN n
```

### GV24 — 64 bit floating point numbers

Adds the `FLOAT64` value type for 64-bit double-precision floating-point numbers.

```gql
MATCH (n) WHERE n.x IS TYPED FLOAT64 RETURN n
```

### GV25 — 128 bit floating point numbers

Adds the `FLOAT128` value type for 128-bit quad-precision floating-point numbers.

```gql
MATCH (n) WHERE n.x IS TYPED FLOAT128 RETURN n
```

### GV26 — 256 bit floating point numbers

Adds the `FLOAT256` value type for 256-bit extended-precision floating-point numbers.

```gql
MATCH (n) WHERE n.x IS TYPED FLOAT256 RETURN n
```

### GV30 — Specified character string minimum length

Allows specifying a minimum length for character strings via `STRING(min, max)`. Enables constrained string types.

```gql
MATCH (n) WHERE n.x IS TYPED STRING(1, 100) RETURN n
```

### GV31 — Specified character string maximum length

Allows specifying a maximum length for character strings via `STRING(max)` or `VARCHAR(max)`.

```gql
MATCH (n) WHERE n.x IS TYPED STRING(100) RETURN n
```

### GV32 — Specified character string fixed length

Adds `CHAR(n)` for fixed-length character strings, padding shorter values and rejecting longer ones.

```gql
MATCH (n) WHERE n.x IS TYPED CHAR(10) RETURN n
```

### GV35 — Byte string types

Adds the `BYTES` value type for binary data, plus `BYTE_LENGTH()` and `OCTET_LENGTH()` functions.

```gql
MATCH (n) WHERE n.x IS TYPED BYTES RETURN n
```

### GV36 — Specified byte string minimum length

Allows specifying a minimum length for byte strings via `BYTES(min, max)`.

```gql
MATCH (n) WHERE n.x IS TYPED BYTES(1, 100) RETURN n
```

### GV37 — Specified byte string maximum length

Allows specifying a maximum length for byte strings via `BYTES(max)` or `VARBINARY(max)`.

```gql
MATCH (n) WHERE n.x IS TYPED BYTES(100) RETURN n
```

### GV38 — Specified byte string fixed length

Adds `BINARY(n)` for fixed-length byte strings.

```gql
MATCH (n) WHERE n.x IS TYPED BINARY(10) RETURN n
```

### GV39 — Temporal types: date, local datetime and local time support

Adds `DATE`, `LOCAL DATETIME`, and `LOCAL TIME` value types, plus `CURRENT_DATE` function and date literal syntax.

```gql
RETURN DATE '2024-01-01'
```

### GV40 — Temporal types: zoned datetime and zoned time support

Adds `ZONED DATETIME` and `ZONED TIME` value types, plus `CURRENT_TIMESTAMP` and `CURRENT_TIME` functions for timezone-aware operations.

```gql
RETURN CURRENT_TIMESTAMP
```

### GV41 — Temporal types: duration support

Adds the `DURATION(qualifier)` value type and duration literal syntax (e.g., `DURATION 'P1Y2M'`). Qualifiers specify the range, such as `DAY TO SECOND`.

```gql
RETURN DURATION 'P1Y2M'
```

### GV45 — Record types

Adds the `RECORD` value type and record constructor syntax (`{ key: value }` or `RECORD { key: value }`) for structured composite values.

```gql
RETURN { name: 1 }
```

### GV46 — Closed record types

Adds closed record types with explicit field definitions (e.g., `{name STRING}`). Only the declared fields are permitted.

```gql
MATCH (n) WHERE n.x IS TYPED {name STRING} RETURN n
```

### GV47 — Open record types

Adds `ANY RECORD` and bare `RECORD` as open record types that accept any set of fields.

```gql
MATCH (n) WHERE n.x IS TYPED ANY RECORD RETURN n
```

### GV48 — Nested record types

Allows record types and constructors to contain other records as field values, enabling arbitrarily nested structured data.

```gql
RETURN { inner: { name: 1 } }
```

### GV50 — List value types

Adds `LIST<type>` value types, list literals (`[1, 2, 3]`), `LIST[...]` constructors, and list concatenation (`||`).

```gql
RETURN [1, 2, 3]
```

### GV55 — Path value types

Adds the `PATH` value type and path value expressions for representing paths as first-class values that can be stored, returned, and compared. Also required for functions that operate on path values, such as `PATH_LENGTH`.

```gql
MATCH p = (a)-[]->{1,10}(b)
RETURN PATH_LENGTH(p) AS hops
```

### GV60 — Graph reference value types

Adds `ANY GRAPH` and related graph reference value types, plus `GRAPH name` expressions. Enables graphs as first-class values.

```gql
MATCH (n) WHERE n.x IS TYPED ANY GRAPH RETURN n
```

### GV61 — Binding table reference value types

Adds `TABLE {fields}` value types and `TABLE { query }` expressions. Enables binding tables as first-class values.

```gql
MATCH (n) WHERE n.x IS TYPED TABLE {name STRING} RETURN n
```

### GV65 — Dynamic union types

Enables dynamic union types that can hold values of multiple types. Foundation for open and closed dynamic union types.

```gql
MATCH (n) WHERE n.x IS TYPED <INT32 | STRING> RETURN n
```

### GV66 — Open dynamic union types

Adds `ANY` as an open dynamic union type that can hold a value of any type.

```gql
MATCH (n) WHERE n.x IS TYPED ANY RETURN n
```

### GV67 — Closed dynamic union types

Adds `<type1 | type2 | ...>` syntax for closed dynamic union types that restrict values to one of the specified types.

```gql
MATCH (n) WHERE n.x IS TYPED <INT32 | STRING> RETURN n
```

### GV68 — Dynamic property value types

Adds `PROPERTY VALUE` as a dynamic type representing any value that can be stored as a property on a graph element.

```gql
MATCH (n) WHERE n.x IS TYPED PROPERTY VALUE RETURN n
```

### GV70 — Immaterial value types

Enables immaterial types (`NULL`, `NOTHING`) that represent the absence of a value. Foundation for null and empty type features.

```gql
MATCH (n) WHERE n.x IS TYPED NULL RETURN n
```

### GV71 — Immaterial value types: null type support

Adds the `NULL` value type, which contains only the null value. Useful in union types to make fields explicitly nullable.

```gql
MATCH (n) WHERE n.x IS TYPED NULL RETURN n
```

### GV72 — Immaterial value types: empty type support

Adds the `NOTHING` value type, which contains no values at all (the bottom type). Useful as a type-theoretic building block.

```gql
MATCH (n) WHERE n.x IS TYPED NOTHING RETURN n
```

### GV90 — Explicit value type nullability

Enables the `NOT NULL` modifier on value types to declare that a value cannot be null (e.g., `INT32 NOT NULL`).

```gql
MATCH (n) WHERE n.x IS TYPED INT32 NOT NULL RETURN n
```
