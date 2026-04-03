"""Round-trip tests for the GQL generator.

These tests verify that: parse(query) -> generate -> parse again -> ASTs match.
"""

import pytest

from graphglot.lexer import Lexer
from graphglot.parser import Parser


def round_trip(query: str) -> tuple[str, bool, str]:
    """Perform a round-trip test.

    Args:
        query: The GQL query to test.

    Returns:
        A tuple of (generated_query, success, error_message).
    """
    lexer = Lexer()
    parser = Parser()

    try:
        # First parse
        tokens1 = lexer.tokenize(query)
        ast1 = parser.parse(tokens1, query)[0]

        # Generate GQL from AST
        generated = ast1.to_gql()

        # Second parse
        tokens2 = lexer.tokenize(generated)
        ast2 = parser.parse(tokens2, generated)[0]

        # Compare ASTs
        if ast1 == ast2:
            return generated, True, ""
        else:
            return generated, False, f"AST mismatch:\nOriginal AST: {ast1}\nGenerated AST: {ast2}"
    except Exception as e:
        return "", False, str(e)


# Basic pattern queries
BASIC_QUERIES = [
    "MATCH (n) RETURN n",
    "MATCH (n:Person) RETURN n",
    "MATCH (n:Person|Employee) RETURN n",
    "MATCH (a)-[r]->(b) RETURN a, r, b",
    "MATCH (a)-[r:KNOWS]->(b) RETURN a, b",
    "MATCH (a)<-[r]-(b) RETURN a, b",
]

# Property queries
PROPERTY_QUERIES = [
    "MATCH (n {name: 'Alice'}) RETURN n",
    "MATCH (n:Person {age: 30}) RETURN n",
    "MATCH (n) RETURN n.name",
    "MATCH (n) RETURN n.name, n.age",
]

# Clause queries
CLAUSE_QUERIES = [
    "MATCH (n) WHERE n.age > 21 RETURN n",
    "MATCH (n) RETURN n ORDER BY n.name",
    "MATCH (n) RETURN n ORDER BY n.name ASC",
    "MATCH (n) RETURN n ORDER BY n.name DESC",
    "MATCH (n) RETURN n ORDER BY n.name NULLS FIRST",
    "MATCH (n) RETURN n ORDER BY n.name NULLS LAST",
    "MATCH (n) RETURN DISTINCT n",
    "MATCH (n) RETURN n LIMIT 10",
    "MATCH (n) RETURN n OFFSET 5 LIMIT 10",
]

# Expression queries
EXPRESSION_QUERIES = [
    "MATCH (n) RETURN n.age + 1",
    "MATCH (n) RETURN n.age - 1",
    "MATCH (n) RETURN n.age * 2",
    "MATCH (n) WHERE n.active = TRUE RETURN n",
    "MATCH (n) WHERE n.active = FALSE RETURN n",
    "MATCH (n) WHERE n.value_ IS NULL RETURN n",
    "MATCH (n) WHERE n.value_ IS NOT NULL RETURN n",
]

# Aggregate queries
AGGREGATE_QUERIES = [
    "MATCH (n) RETURN COUNT(*)",
]

# Data modification queries
DATA_MOD_QUERIES = [
    "INSERT (n:Person {name: 'Bob'})",
    "MATCH (n) SET n.updated = TRUE",
    "MATCH (n) DELETE n",
    "MATCH (n) DETACH DELETE n",
]

# CASE expression queries
CASE_QUERIES = [
    "MATCH (n) RETURN CASE WHEN n.age > 21 THEN 'adult' ELSE 'minor' END",
    "MATCH (n) RETURN CASE WHEN n.age > 21 THEN 'adult' END",
    "MATCH (n) RETURN CASE WHEN n.age < 13 THEN 'child' "
    "WHEN n.age < 18 THEN 'teen' ELSE 'adult' END",
]

# Set operation queries
SET_OP_QUERIES = [
    "MATCH (n) RETURN n UNION ALL MATCH (m) RETURN m",
    "MATCH (n) RETURN n UNION MATCH (m) RETURN m",
]

# Optional MATCH queries
OPTIONAL_MATCH_QUERIES = [
    "OPTIONAL MATCH (n)-[r]->(m) RETURN n, m",
]

# Multiple ORDER BY queries
ORDER_BY_QUERIES = [
    "MATCH (n) RETURN n ORDER BY n.age DESC, n.name ASC",
    "MATCH (n) RETURN n ORDER BY n.age DESC NULLS LAST, n.name ASC NULLS FIRST",
]

# Path pattern queries
PATH_QUERIES = [
    "MATCH p = (a)-[]->(b) RETURN p",
    "MATCH p = (a)-[]->{1,3}(b) RETURN p",
    "MATCH (a)-[]->{2}(b) RETURN a, b",
    "MATCH (a)-[]->+(b) RETURN a, b",
    "MATCH (a)-[]->*(b) RETURN a, b",
]

# FILTER statement queries
FILTER_QUERIES = [
    "MATCH (n) FILTER n.active = TRUE RETURN n",
]

# Multiple pattern queries
MULTI_PATTERN_QUERIES = [
    "MATCH (a)-[r1]->(b), (b)-[r2]->(c) RETURN a, c",
]

# Label expression queries
LABEL_QUERIES = [
    "MATCH (n:Person&Employee) RETURN n",
    "MATCH (n:!Bot) RETURN n",
    "MATCH (n:%) RETURN n",
    "MATCH (n:Person WHERE n.age > 21) RETURN n",
]

# Boolean expression queries
BOOLEAN_QUERIES = [
    "MATCH (n) WHERE (n.age > 21 AND n.active = TRUE) RETURN n",
    "MATCH (n) WHERE NOT n.active = TRUE RETURN n",
    "MATCH (n) WHERE n.a = TRUE OR n.b = FALSE RETURN n",
    "MATCH (n) WHERE n.age >= 18 AND n.age <= 65 RETURN n",
]

# Edge direction queries
EDGE_QUERIES = [
    "MATCH (a)<-[r:KNOWS]-(b) RETURN a, b",
    "MATCH (a)-[r:KNOWS]-(b) RETURN a, b",
]

# RETURN with alias and multiple items
RETURN_QUERIES = [
    "MATCH (n) RETURN n.name AS personName",
    "MATCH (n:Person) RETURN n.name, n.age, n.active",
    "MATCH (n) RETURN n OFFSET 10 LIMIT 5",
]

# Literal queries
LITERAL_QUERIES = [
    "MATCH (n) RETURN TRUE, FALSE",
    "MATCH (n) RETURN NULL",
    "MATCH (n) RETURN 42, 3.14, -1",
    "MATCH (n) RETURN 'hello'",
    "MATCH (n) RETURN -n.age",
]

# Nested property and expression queries
NESTED_QUERIES = [
    "MATCH (n) RETURN n.address.city",
    "MATCH (n) WHERE n.email IS NOT NULL RETURN n",
    "MATCH (n:Person) RETURN COUNT(*)",
]

# REMOVE statement queries
REMOVE_QUERIES = [
    "MATCH (n) REMOVE n:TempLabel",
]

# Session and transaction queries
SESSION_QUERIES = [
    "SESSION CLOSE",
    "START TRANSACTION",
    "COMMIT",
    "ROLLBACK",
]

# --- Complex queries (inspired by test_feature_toggle.py) ---

# Edge direction variants
EDGE_DIRECTION_QUERIES = [
    "MATCH (a)~[r]~(b) RETURN a",
    "MATCH (a)<-(b) RETURN a",
    "MATCH (a)->(b) RETURN a",
    "MATCH (a)-(b) RETURN a",
    "MATCH (a)~(b) RETURN a",
    "MATCH (a)<~(b) RETURN a",
    "MATCH (a)~>(b) RETURN a",
    "MATCH (a)<->(b) RETURN a",
]

# Quantified and parenthesized path patterns
QUANTIFIED_PATH_QUERIES = [
    "MATCH ((a)-[e]->(b))* RETURN a",
    "MATCH (a)-[e]->(b)? RETURN a",
    "MATCH ((a)-[e]->(b)) RETURN a",
    "MATCH (n:Person){3} RETURN n",
    "MATCH (n:Person){1,5} RETURN n",
    "MATCH (n:Person)* RETURN n",
    "MATCH (n:Person){1,} RETURN n",
    "MATCH ((a)-[e]->(b)){2,4} RETURN a",
    "MATCH (p = (a)-[e]->(b)) RETURN a",
    "MATCH (WALK (a)-[e]->(b)) RETURN a",
    "MATCH ((a)-[e]->(b) WHERE e.weight > 5) RETURN a",
]

# Match mode queries
MATCH_MODE_QUERIES = [
    "MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n",
    "MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n",
    "MATCH (n)-[e]->(m) KEEP WALK RETURN n",
    "MATCH (a)-[e WHERE a.age > 5]->(b) RETURN a",
    "MATCH (a)(b) RETURN a",
]

# Composite query operations (EXCEPT, INTERSECT, OTHERWISE)
COMPOSITE_QUERIES = [
    "MATCH (n) RETURN n OTHERWISE MATCH (m) RETURN m",
    "MATCH (n) RETURN n EXCEPT MATCH (m) RETURN m",
    "MATCH (n) RETURN n EXCEPT DISTINCT MATCH (m) RETURN m",
    "MATCH (n) RETURN n EXCEPT ALL MATCH (m) RETURN m",
    "MATCH (n) RETURN n INTERSECT MATCH (m) RETURN m",
    "MATCH (n) RETURN n INTERSECT DISTINCT MATCH (m) RETURN m",
    "MATCH (n) RETURN n INTERSECT ALL MATCH (m) RETURN m",
]

# DDL / Catalog-modifying statements
DDL_QUERIES = [
    "CREATE SCHEMA /myschemas/foo",
    "DROP SCHEMA /myschemas/foo",
    "CREATE SCHEMA IF NOT EXISTS /myschemas/bar",
    "DROP SCHEMA IF EXISTS /myschemas/bar",
    "CREATE PROPERTY GRAPH my_graph ANY PROPERTY GRAPH",
    "CREATE PROPERTY GRAPH my_graph LIKE CURRENT_GRAPH",
    "DROP GRAPH my_graph",
    "DROP PROPERTY GRAPH IF EXISTS my_graph",
    "CREATE PROPERTY GRAPH TYPE my_type LIKE CURRENT_GRAPH",
    "DROP GRAPH TYPE my_type",
]

# Session commands (beyond basic CLOSE)
SESSION_COMMAND_QUERIES = [
    "SESSION SET TIME ZONE 'UTC'",
    "SESSION RESET CHARACTERISTICS",
    "SESSION RESET SCHEMA",
    "SESSION RESET GRAPH",
    "SESSION RESET TIME ZONE",
    "SESSION RESET ALL PARAMETERS",
    "SESSION RESET PARAMETER $my_param",
    "SESSION SET GRAPH $g = my_graph",
    "SESSION SET TABLE $t = my_table",
    "SESSION SET VALUE $v = 42",
    "START TRANSACTION READ ONLY",
]

# Type predicate queries
TYPE_PREDICATE_QUERIES = [
    "MATCH (n) WHERE n.age IS TYPED INT32 RETURN n",
    "MATCH (n) WHERE n.age IS NOT TYPED INT32 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED STRING RETURN n",
    "MATCH (n) WHERE n.x IS TYPED BOOL RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT64 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED INT32 NOT NULL RETURN n",
    "MATCH (n) WHERE n.x IS TYPED ANY RETURN n",
    "MATCH (n) WHERE n.x IS TYPED NULL RETURN n",
    "MATCH (n) WHERE n.x IS TYPED NOTHING RETURN n",
    "MATCH (n) WHERE n.x IS TYPED DATE RETURN n",
    "MATCH (n) WHERE n.x IS TYPED PATH RETURN n",
    "MATCH (n) WHERE n.x IS TYPED LIST<INT32> RETURN n",
    "MATCH (n) WHERE n.x IS TYPED BYTES RETURN n",
    "MATCH (n) WHERE n.x IS TYPED RECORD RETURN n",
    # Postfix list value types
    "MATCH (n) WHERE n.x IS TYPED INT LIST RETURN n",
    "MATCH (n) WHERE n.x IS TYPED STRING GROUP LIST[10] RETURN n",
]

# Predicate queries (IS DIRECTED, SOURCE/DESTINATION, ALL_DIFFERENT, SAME, etc.)
PREDICATE_QUERIES = [
    "MATCH (n)-[e]->(m) WHERE e IS DIRECTED RETURN e",
    "MATCH (n:Person) WHERE n:Person RETURN n",
    "MATCH (n)-[e]->(m) WHERE n IS SOURCE OF e RETURN n",
    "MATCH (n)-[e]->(m) WHERE m IS DESTINATION OF e RETURN m",
    "MATCH (n)-[e]->(m) WHERE n IS NOT SOURCE OF e RETURN n",
    "MATCH (a)-[e1]->(b), (c)-[e2]->(d) WHERE ALL_DIFFERENT(a,c) RETURN a",
    "MATCH (a)-[e1]->(b), (c)-[e2]->(d) WHERE SAME(a,c) RETURN a",
    "MATCH (n:Person) WHERE PROPERTY_EXISTS(n, name) RETURN n",
]

# Procedure and subquery queries
PROCEDURE_QUERIES = [
    "MATCH (n) CALL { MATCH (m) RETURN m } RETURN n",
    "MATCH (n) CALL (n) { MATCH (n)-[]->(m) RETURN m } RETURN n",
    "MATCH (n) WHERE EXISTS { MATCH (n) MATCH (m) } RETURN n",
    "MATCH (n) RETURN VALUE { MATCH (m) RETURN m.x }",
]

# YIELD clause queries
YIELD_QUERIES = [
    "MATCH (n)-[e]->(m) YIELD n, m RETURN n",
]

# Record, list, and temporal expression queries
COMPLEX_EXPRESSION_QUERIES = [
    "RETURN [1, 2, 3]",
    "RETURN LIST[1, 2, 3]",
    "RETURN [1] || [2]",
    "RETURN { name: 'Alice', age: 30 }",
    "RETURN RECORD { name: 1 }",
    "RETURN { inner: { name: 1 } }",
    "RETURN DATE '2024-01-01'",
    "RETURN DURATION 'P1Y2M'",
    "MATCH (n) WHERE TRUE XOR FALSE RETURN n",
    "MATCH (n) RETURN n GROUP BY n",
    "MATCH (n) RETURN n.name AS name ORDER BY COUNT(*)",
    "MATCH (n) LET x = n.age RETURN x",
    "MATCH (n) NEXT RETURN n",
    "OPTIONAL { MATCH (n) MATCH (m) } RETURN n, m",
    "DELETE n.prop",
    "SET n.prop = 1",
    "MATCH (n) FILTER WHERE n.age > 21 RETURN n",
]

# Complex multi-clause combinations
COMPLEX_COMBO_QUERIES = [
    "MATCH (a)-[r:KNOWS {since: 2020}]->(b) RETURN a, b",
    "MATCH (n:Person {name: 'Alice', age: 30}) RETURN n",
    "MATCH (n) WHERE n.age > 21 RETURN n ORDER BY n.name DESC LIMIT 10",
    "MATCH (n) WHERE n.age >= 18 AND n.age <= 65 RETURN n ORDER BY n.age",
    "MATCH (n WHERE n.age >= 18 AND n.age <= 65 ) RETURN n ORDER BY n.age",
    "MATCH (a)-[r:KNOWS]->(b)-[s:WORKS_AT]->(c) RETURN a, c",
    "MATCH (a)-[]->(b)-[]->(c)-[]->(d) RETURN a, d",
    "OPTIONAL MATCH (n:Person)-[r:KNOWS]->(m:Person) RETURN n, m",
    "MATCH (n) RETURN n.age + n.score * 2",
    "MATCH (n) WHERE n.name = 'Alice' OR n.name = 'Bob' RETURN n",
    "MATCH (n) WHERE NOT (n.age > 21 AND n.active = TRUE) RETURN n",
    "INSERT (:Person {name: 'Alice', age: 30})",
    "INSERT (:Person)-[:KNOWS]->(:Person)",
    "MATCH (n) SET n.name = 'Updated', n.updated = TRUE",
    "MATCH (a)-[r]->(b) WHERE r.weight > 5 RETURN a, b ORDER BY r.weight DESC",
    "MATCH p = (a)-[]->(b)-[]->(c) RETURN p",
    "MATCH (a)-[]->{2,5}(b) RETURN a, b",
    "MATCH (n:Person&Employee&Manager) RETURN n",
    "MATCH (n:Person|Employee|Manager) RETURN n",
    "MATCH (a)-[r:KNOWS|LIKES]->(b) RETURN a, b",
    (
        "MATCH (n {name: 'test'}) WHERE n.age > 21 "
        "RETURN n.name AS personName ORDER BY n.age LIMIT 5"
    ),
    "MATCH (n) WHERE n.age > 21 RETURN COUNT(*)",
    "MATCH (n) RETURN n.age + 1 AS incremented, n.name",
    "MATCH (n) WHERE n.x > 1 AND n.y < 10 OR n.z = 5 RETURN n",
    "MATCH (a)-[r1]->(b), (c)-[r2]->(d), (a)-[r3]->(c) RETURN a, b, c, d",
    "MATCH (n:Person WHERE n.age > 21 AND n.active = TRUE) RETURN n",
    "MATCH (n) WHERE n.age <> 21 RETURN n",
    "MATCH (n:Person) SET n:Employee",
    "MATCH (n:Person) REMOVE n:Person RETURN n",
    "MATCH (n:Person) WHERE n.age > 65 DELETE n",
    "MATCH (n) RETURN n UNION ALL MATCH (m:Person) RETURN m",
]

# Type variant queries (GV01-GV48, GV90)
TYPE_VARIANT_QUERIES = [
    # Unsigned integer types
    "MATCH (n) WHERE n.age IS TYPED UINT8 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UINT16 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UINT32 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UINT64 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UINT128 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UINT256 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UINT RETURN n",
    "MATCH (n) WHERE n.age IS TYPED USMALLINT RETURN n",
    "MATCH (n) WHERE n.age IS TYPED UBIGINT RETURN n",
    # Signed integer types
    "MATCH (n) WHERE n.age IS TYPED INT8 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED INT16 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED INT64 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED INT128 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED INT256 RETURN n",
    "MATCH (n) WHERE n.age IS TYPED INT(10) RETURN n",
    "MATCH (n) WHERE n.age IS TYPED SMALLINT RETURN n",
    "MATCH (n) WHERE n.age IS TYPED BIGINT RETURN n",
    # Float types
    "MATCH (n) WHERE n.age IS TYPED FLOAT16 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT32 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT64 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT128 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT256 RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT(10) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED FLOAT(10, 2) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED REAL RETURN n",
    "MATCH (n) WHERE n.x IS TYPED DOUBLE PRECISION RETURN n",
    # String types
    "MATCH (n) WHERE n.x IS TYPED STRING(100) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED STRING(1, 100) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED VARCHAR(100) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED CHAR(10) RETURN n",
    # Byte types
    "MATCH (n) WHERE n.x IS TYPED BYTES(100) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED BYTES(1, 100) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED VARBINARY(100) RETURN n",
    "MATCH (n) WHERE n.x IS TYPED BINARY(10) RETURN n",
    # Temporal types
    "MATCH (n) WHERE n.x IS TYPED LOCAL DATETIME RETURN n",
    "MATCH (n) WHERE n.x IS TYPED LOCAL TIME RETURN n",
    # Record types
    "MATCH (n) WHERE n.x IS TYPED RECORD RETURN n",
    "MATCH (n) WHERE n.x IS TYPED ANY RECORD RETURN n",
    "MATCH (n) WHERE n.x IS TYPED {name STRING} RETURN n",
    "MATCH (n) WHERE n.x IS TYPED RECORD {name STRING} RETURN n",
    "MATCH (n) WHERE n.x IS TYPED {inner {nested STRING}} RETURN n",
    # NOT NULL variants
    "MATCH (n) WHERE n.x IS TYPED STRING NOT NULL RETURN n",
    "MATCH (n) WHERE n.x IS TYPED BOOL NOT NULL RETURN n",
    "MATCH (n) WHERE n.x IS TYPED PATH NOT NULL RETURN n",
]

# Numeric function queries
NUMERIC_FUNCTION_QUERIES = [
    "RETURN ABS(-5)",
]

# Named procedure queries
NAMED_PROCEDURE_QUERIES = [
    "CALL my.namespace.proc(1, 2) YIELD x RETURN x",
]

# Procedure body queries (catalog + data statement mixing)
PROCEDURE_BODY_QUERIES = [
    "CALL { CREATE SCHEMA /s NEXT SET n.prop = 1 } RETURN 1",
]

# Session subquery queries
SESSION_SUBQUERY_QUERIES = [
    "SESSION SET TABLE $t = { MATCH (n) RETURN n }",
    "SESSION SET VALUE $v = VALUE { MATCH (n) RETURN n.prop }",
]

# Lexer edge case queries
LEXER_EDGE_CASE_QUERIES = [
    "MATCH (abcdefghijklmnopqrstuvwxyz) RETURN abcdefghijklmnopqrstuvwxyz",
]

# Complex sort queries
COMPLEX_SORT_QUERIES = [
    "MATCH (n) RETURN n.name AS name ORDER BY n.name || n.surname",
]

# Insert edge direction queries
INSERT_EDGE_QUERIES = [
    "INSERT ()~[]~()",
]

# Aggregate function queries
AGGREGATE_FUNCTION_QUERIES = [
    "MATCH (n) RETURN SUM(n.age)",
    "MATCH (n) RETURN AVG(n.age)",
    "MATCH (n) RETURN MIN(n.age)",
    "MATCH (n) RETURN MAX(n.age)",
    "MATCH (n) RETURN STDDEV_SAMP(n.age)",
    "MATCH (n) RETURN STDDEV_POP(n.age)",
    "MATCH (n) RETURN PERCENTILE_CONT(n.age, 0.5)",
    "MATCH (n) RETURN PERCENTILE_DISC(n.age, 0.5)",
]

# Decimal type queries
DECIMAL_TYPE_QUERIES = [
    "MATCH (n) WHERE n.age IS TYPED DECIMAL(10) RETURN n",
    "MATCH (n) WHERE n.age IS TYPED DEC(10) RETURN n",
]

# Closed dynamic union type queries
DYNAMIC_UNION_QUERIES = [
    "MATCH (n) WHERE n.x IS TYPED <INT32 | STRING> RETURN n",
]

# Path search queries
PATH_SEARCH_QUERIES = [
    "MATCH ALL PATHS (a)-[e]->(b) RETURN a",
    "MATCH ANY PATH (a)-[e]->(b) RETURN a",
    "MATCH ALL SHORTEST PATHS (a)-[e]->(b) RETURN a",
    "MATCH ANY SHORTEST PATH (a)-[e]->(b) RETURN a",
    "MATCH SHORTEST 3 PATHS (a)-[e]->(b) RETURN a",
    "MATCH SHORTEST 3 PATH GROUPS (a)-[e]->(b) RETURN a",
]

# NULLIF / COALESCE queries
CASE_ABBREVIATION_QUERIES = [
    "RETURN NULLIF(1, 2)",
    "RETURN COALESCE(NULL, 1, 2)",
]


class TestBasicRoundTrip:
    """Test basic pattern queries round-trip correctly."""

    @pytest.mark.parametrize("query", BASIC_QUERIES)
    def test_basic_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestPropertyRoundTrip:
    """Test property queries round-trip correctly."""

    @pytest.mark.parametrize("query", PROPERTY_QUERIES)
    def test_property_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestClauseRoundTrip:
    """Test clause queries round-trip correctly."""

    @pytest.mark.parametrize("query", CLAUSE_QUERIES)
    def test_clause_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestExpressionRoundTrip:
    """Test expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", EXPRESSION_QUERIES)
    def test_expression_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestAggregateRoundTrip:
    """Test aggregate queries round-trip correctly."""

    @pytest.mark.parametrize("query", AGGREGATE_QUERIES)
    def test_aggregate_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestDataModificationRoundTrip:
    """Test data modification queries round-trip correctly."""

    @pytest.mark.parametrize("query", DATA_MOD_QUERIES)
    def test_data_mod_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCaseExpressionRoundTrip:
    """Test CASE expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", CASE_QUERIES)
    def test_case_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestSetOperationRoundTrip:
    """Test set operation queries round-trip correctly."""

    @pytest.mark.parametrize("query", SET_OP_QUERIES)
    def test_set_op_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestOptionalMatchRoundTrip:
    """Test OPTIONAL MATCH queries round-trip correctly."""

    @pytest.mark.parametrize("query", OPTIONAL_MATCH_QUERIES)
    def test_optional_match_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestOrderByRoundTrip:
    """Test multiple ORDER BY queries round-trip correctly."""

    @pytest.mark.parametrize("query", ORDER_BY_QUERIES)
    def test_order_by_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestPathPatternRoundTrip:
    """Test path pattern queries round-trip correctly."""

    @pytest.mark.parametrize("query", PATH_QUERIES)
    def test_path_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestFilterRoundTrip:
    """Test FILTER statement queries round-trip correctly."""

    @pytest.mark.parametrize("query", FILTER_QUERIES)
    def test_filter_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestMultiPatternRoundTrip:
    """Test multiple pattern queries round-trip correctly."""

    @pytest.mark.parametrize("query", MULTI_PATTERN_QUERIES)
    def test_multi_pattern_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestLabelExpressionRoundTrip:
    """Test label expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", LABEL_QUERIES)
    def test_label_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestBooleanExpressionRoundTrip:
    """Test boolean expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", BOOLEAN_QUERIES)
    def test_boolean_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestEdgeDirectionRoundTrip:
    """Test edge direction queries round-trip correctly."""

    @pytest.mark.parametrize("query", EDGE_QUERIES)
    def test_edge_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestReturnRoundTrip:
    """Test RETURN clause queries round-trip correctly."""

    @pytest.mark.parametrize("query", RETURN_QUERIES)
    def test_return_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestLiteralRoundTrip:
    """Test literal queries round-trip correctly."""

    @pytest.mark.parametrize("query", LITERAL_QUERIES)
    def test_literal_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestNestedExpressionRoundTrip:
    """Test nested property and expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", NESTED_QUERIES)
    def test_nested_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestRemoveRoundTrip:
    """Test REMOVE statement queries round-trip correctly."""

    @pytest.mark.parametrize("query", REMOVE_QUERIES)
    def test_remove_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestSessionTransactionRoundTrip:
    """Test session and transaction queries round-trip correctly."""

    @pytest.mark.parametrize("query", SESSION_QUERIES)
    def test_session_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestEdgeDirectionRoundTrip2:
    """Test all edge direction variants round-trip correctly."""

    @pytest.mark.parametrize("query", EDGE_DIRECTION_QUERIES)
    def test_edge_direction_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestQuantifiedPathRoundTrip:
    """Test quantified and parenthesized path patterns round-trip correctly."""

    @pytest.mark.parametrize("query", QUANTIFIED_PATH_QUERIES)
    def test_quantified_path_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestMatchModeRoundTrip:
    """Test match mode queries round-trip correctly."""

    @pytest.mark.parametrize("query", MATCH_MODE_QUERIES)
    def test_match_mode_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCompositeQueryRoundTrip:
    """Test composite query operations round-trip correctly."""

    @pytest.mark.parametrize("query", COMPOSITE_QUERIES)
    def test_composite_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestDDLRoundTrip:
    """Test DDL/catalog-modifying statements round-trip correctly."""

    @pytest.mark.parametrize("query", DDL_QUERIES)
    def test_ddl_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestSessionCommandRoundTrip:
    """Test session command queries round-trip correctly."""

    @pytest.mark.parametrize("query", SESSION_COMMAND_QUERIES)
    def test_session_command_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestTypePredicateRoundTrip:
    """Test type predicate queries round-trip correctly."""

    @pytest.mark.parametrize("query", TYPE_PREDICATE_QUERIES)
    def test_type_predicate_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestPredicateRoundTrip:
    """Test predicate queries round-trip correctly."""

    @pytest.mark.parametrize("query", PREDICATE_QUERIES)
    def test_predicate_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestProcedureRoundTrip:
    """Test procedure and subquery queries round-trip correctly."""

    @pytest.mark.parametrize("query", PROCEDURE_QUERIES)
    def test_procedure_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestYieldRoundTrip:
    """Test YIELD clause queries round-trip correctly."""

    @pytest.mark.parametrize("query", YIELD_QUERIES)
    def test_yield_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestComplexExpressionRoundTrip:
    """Test complex expressions round-trip correctly."""

    @pytest.mark.parametrize("query", COMPLEX_EXPRESSION_QUERIES)
    def test_complex_expression_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestComplexComboRoundTrip:
    """Test complex multi-clause combinations round-trip correctly."""

    @pytest.mark.parametrize("query", COMPLEX_COMBO_QUERIES)
    def test_complex_combo_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestTypeVariantRoundTrip:
    """Test type variant queries round-trip correctly."""

    @pytest.mark.parametrize("query", TYPE_VARIANT_QUERIES)
    def test_type_variant_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestNumericFunctionRoundTrip:
    """Test numeric function queries round-trip correctly."""

    @pytest.mark.parametrize("query", NUMERIC_FUNCTION_QUERIES)
    def test_numeric_function_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestNamedProcedureRoundTrip:
    """Test named procedure queries round-trip correctly."""

    @pytest.mark.parametrize("query", NAMED_PROCEDURE_QUERIES)
    def test_named_procedure_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestProcedureBodyRoundTrip:
    """Test procedure body queries round-trip correctly."""

    @pytest.mark.parametrize("query", PROCEDURE_BODY_QUERIES)
    def test_procedure_body_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestSessionSubqueryRoundTrip:
    """Test session subquery queries round-trip correctly."""

    @pytest.mark.parametrize("query", SESSION_SUBQUERY_QUERIES)
    def test_session_subquery_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestLexerEdgeCaseRoundTrip:
    """Test lexer edge case queries round-trip correctly."""

    @pytest.mark.parametrize("query", LEXER_EDGE_CASE_QUERIES)
    def test_lexer_edge_case_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestComplexSortRoundTrip:
    """Test complex sort queries round-trip correctly."""

    @pytest.mark.parametrize("query", COMPLEX_SORT_QUERIES)
    def test_complex_sort_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestInsertEdgeRoundTrip:
    """Test insert edge direction queries round-trip correctly."""

    @pytest.mark.parametrize("query", INSERT_EDGE_QUERIES)
    def test_insert_edge_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCaseAbbreviationRoundTrip:
    """Test NULLIF/COALESCE queries round-trip correctly."""

    @pytest.mark.parametrize("query", CASE_ABBREVIATION_QUERIES)
    def test_case_abbreviation_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestAggregateFunctionRoundTrip:
    """Test aggregate function queries round-trip correctly."""

    @pytest.mark.parametrize("query", AGGREGATE_FUNCTION_QUERIES)
    def test_aggregate_function_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestDecimalTypeRoundTrip:
    """Test decimal type queries round-trip correctly."""

    @pytest.mark.parametrize("query", DECIMAL_TYPE_QUERIES)
    def test_decimal_type_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestDynamicUnionRoundTrip:
    """Test closed dynamic union type queries round-trip correctly."""

    @pytest.mark.parametrize("query", DYNAMIC_UNION_QUERIES)
    def test_dynamic_union_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestPathSearchRoundTrip:
    """Test path search queries round-trip correctly."""

    @pytest.mark.parametrize("query", PATH_SEARCH_QUERIES)
    def test_path_search_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


# Phase 3: Missing generator queries

NUMERIC_MATH_QUERIES = [
    "MATCH (n) RETURN MOD(n.x, 3)",
    "MATCH (n) RETURN FLOOR(n.x)",
    "MATCH (n) RETURN CEIL(n.x)",
    "MATCH (n) RETURN SQRT(n.x)",
    "MATCH (n) RETURN POWER(n.x, 2)",
    "MATCH (n) RETURN EXP(n.x)",
    "MATCH (n) RETURN LN(n.x)",
    "MATCH (n) RETURN LOG10(n.x)",
    "MATCH (n) RETURN LOG(n.x, 10)",
]

TRIG_FUNCTION_QUERIES = [
    "MATCH (n) RETURN SIN(n.x)",
    "MATCH (n) RETURN COS(n.x)",
    "MATCH (n) RETURN TAN(n.x)",
    "MATCH (n) RETURN COT(n.x)",
    "MATCH (n) RETURN ASIN(n.x)",
    "MATCH (n) RETURN ACOS(n.x)",
    "MATCH (n) RETURN ATAN(n.x)",
    "MATCH (n) RETURN DEGREES(n.x)",
    "MATCH (n) RETURN RADIANS(n.x)",
]

STRING_FUNCTION_QUERIES = [
    "MATCH (n) RETURN UPPER(n.name)",
    "MATCH (n) RETURN LOWER(n.name)",
    "MATCH (n) RETURN TRIM(LEADING ' ' FROM n.name)",
    "MATCH (n) RETURN TRIM(TRAILING ' ' FROM n.name)",
    "MATCH (n) RETURN TRIM(BOTH ' ' FROM n.name)",
    "MATCH (n) RETURN LTRIM(n.name)",
    "MATCH (n) RETURN RTRIM(n.name)",
    "MATCH (n) RETURN BTRIM(n.name)",
    "MATCH (n) RETURN CHAR_LENGTH(n.name)",
]

COLLECTION_FUNCTION_QUERIES = [
    "MATCH (n) RETURN SIZE(n.friends)",
    "MATCH p = (a)-[]->(b) RETURN ELEMENTS(p)",
    "MATCH p = (a)-[]->(b) RETURN PATH_LENGTH(p)",
]

CAST_QUERIES = [
    "MATCH (n) RETURN CAST(n.x AS INT32)",
    "MATCH (n) RETURN CAST(n.x AS STRING)",
    "MATCH (n) RETURN CAST(n.x AS BOOLEAN)",
]

LET_EXPRESSION_QUERIES = [
    "MATCH (n) RETURN LET x = n.age IN x * 2 END",
]

ELEMENT_ID_QUERIES = [
    "MATCH (n) RETURN ELEMENT_ID(n)",
]

TEMPORAL_FUNCTION_QUERIES = [
    "RETURN CURRENT_DATE",
    "RETURN CURRENT_TIME",
    "RETURN CURRENT_TIMESTAMP",
    # Explicit constructor forms with string params
    "RETURN DATE('1984-10-11')",
    "RETURN ZONED_TIME('12:31:14+01:00')",
    "RETURN ZONED_DATETIME('1984-10-11T12:31:14+01:00')",
    "RETURN LOCAL_DATETIME('1984-10-11T12:31:14')",
    "RETURN LOCAL_TIME('12:31:14')",
    # Record constructor forms (map syntax — the TCK blocker)
    "RETURN DATE({`year` : 1984, `month` : 10, `day` : 11})",
    "RETURN ZONED_TIME({`hour` : 12, `minute` : 31, `second` : 14, timezone : '+01:00'})",
    "RETURN ZONED_DATETIME({`year` : 1984, `month` : 10, `day` : 11, timezone : '+01:00'})",
    "RETURN LOCAL_DATETIME({`year` : 1984, `month` : 10, `day` : 11, `hour` : 12})",
    "RETURN LOCAL_TIME({`hour` : 12, `minute` : 31, `second` : 14})",
    # No-param forms
    "RETURN ZONED_TIME()",
    "RETURN ZONED_DATETIME()",
    "RETURN LOCAL_DATETIME()",
    "RETURN LOCAL_TIME()",
    # Bare LOCAL_TIME (no parens — spec 20.27 allows this unique form)
    "RETURN LOCAL_TIME",
]

INTERVAL_QUERIES = [
    "RETURN INTERVAL '1' YEAR",
    "RETURN INTERVAL '1-6' YEAR TO MONTH",
    "RETURN INTERVAL -'5' DAY",
    "RETURN INTERVAL '2' DAY TO SECOND",
]

COLLECT_LIST_QUERIES = [
    "MATCH (n) RETURN COLLECT_LIST(n.name)",
]

DURATION_QUERIES = [
    "RETURN DURATION 'P1Y2M'",
    "RETURN DURATION 'P1DT2H3M4S'",
]


class TestNumericMathRoundTrip:
    """Test numeric math function queries round-trip correctly."""

    @pytest.mark.parametrize("query", NUMERIC_MATH_QUERIES)
    def test_numeric_math_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestTrigFunctionRoundTrip:
    """Test trigonometric function queries round-trip correctly."""

    @pytest.mark.parametrize("query", TRIG_FUNCTION_QUERIES)
    def test_trig_function_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestStringFunctionRoundTrip:
    """Test string function queries round-trip correctly."""

    @pytest.mark.parametrize("query", STRING_FUNCTION_QUERIES)
    def test_string_function_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCollectionFunctionRoundTrip:
    """Test collection function queries round-trip correctly."""

    @pytest.mark.parametrize("query", COLLECTION_FUNCTION_QUERIES)
    def test_collection_function_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCastRoundTrip:
    """Test CAST expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", CAST_QUERIES)
    def test_cast_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestLetExpressionRoundTrip:
    """Test LET expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", LET_EXPRESSION_QUERIES)
    def test_let_expression_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestElementIdRoundTrip:
    """Test ELEMENT_ID function queries round-trip correctly."""

    @pytest.mark.parametrize("query", ELEMENT_ID_QUERIES)
    def test_element_id_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestTemporalFunctionRoundTrip:
    """Test temporal function queries round-trip correctly."""

    @pytest.mark.parametrize("query", TEMPORAL_FUNCTION_QUERIES)
    def test_temporal_function_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestIntervalRoundTrip:
    """Test SQL interval literal queries round-trip correctly."""

    @pytest.mark.parametrize("query", INTERVAL_QUERIES)
    def test_interval_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCollectListRoundTrip:
    """Test COLLECT_LIST queries round-trip correctly."""

    @pytest.mark.parametrize("query", COLLECT_LIST_QUERIES)
    def test_collect_list_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestDurationRoundTrip:
    """Test DURATION literal queries round-trip correctly."""

    @pytest.mark.parametrize("query", DURATION_QUERIES)
    def test_duration_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


# Phase 4: Additional coverage queries

DISTINCT_AGGREGATE_QUERIES = [
    "MATCH (n) RETURN COUNT(DISTINCT n.name)",
    "MATCH (n) RETURN SUM(DISTINCT n.age)",
]

PARAMETER_QUERIES = [
    "MATCH (n) WHERE n.name = $param RETURN n",
    "MATCH (n) WHERE n.age = $age AND n.name = $name RETURN n",
]

COMBINED_CLAUSE_QUERIES = [
    "MATCH (n) RETURN n LIMIT 10 OFFSET 5",
    "MATCH (a) MATCH (b) RETURN a, b",
    "MATCH (n) SET n:Person",
    "MATCH (n) REMOVE n:Person",
]

SIMPLE_CASE_QUERIES = [
    "MATCH (n) RETURN CASE n.status WHEN 'A' THEN 'Active' ELSE 'Inactive' END",
]

AGGREGATE_ALIAS_QUERIES = [
    "MATCH (n) RETURN n.city, COUNT(*) AS cnt ORDER BY cnt DESC",
]

LABEL_PATTERN_QUERIES = [
    "MATCH (n:!Person) RETURN n",
]

# Phase 5: Coverage gap queries

COVERAGE_GAP_QUERIES = [
    "RETURN DATETIME '2024-01-15T10:30:00'",
    "RETURN TIME '10:30:00'",
    "RETURN DATE '2024-01-15'",
    "RETURN -42",
    "MATCH (n) WHERE n.active IS TRUE RETURN n",
    "MATCH REPEATABLE ELEMENTS (n)-[r]->(m) RETURN n",
    "MATCH DIFFERENT EDGES (n)-[r]->(m) RETURN n",
    "INSERT ()<-[e:KNOWS]-()",
    "MATCH (n) SET n = {name: 'Alice', age: 30}",
    "MATCH (n) REMOVE n.name",
    "MATCH (a)-[r]->*(b) RETURN a, b",
    "MATCH (a)-[r]->+(b) RETURN a, b",
    "MATCH (n) RETURN COUNT(*) GROUP BY ()",
    "MATCH (n) WHERE n.name IS NORMALIZED RETURN n",
    "SESSION SET GRAPH $g = my_graph",
    "SESSION SET SCHEMA /my_schema",
    "MATCH (a)-[r:KNOWS]-(b) RETURN a",
    "MATCH (n:(Person|Employee)) RETURN n",
    "MATCH (n) RETURN *",
    "LET x = 42 RETURN x",
    "CALL my_proc(1) YIELD x RETURN x",
    "MATCH p = (a)-[]->(b) RETURN p",
    "MATCH (n) WHERE n.x IS TYPED INT128 RETURN n",
    "MATCH (n) WHERE n IS TYPED NODE RETURN n",
    "MATCH ()-[r]->() WHERE r IS TYPED EDGE RETURN r",
]


class TestCoverageGapRoundTrip:
    """Test coverage gap queries round-trip correctly."""

    @pytest.mark.parametrize("query", COVERAGE_GAP_QUERIES)
    def test_coverage_gap_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestDistinctAggregateRoundTrip:
    """Test DISTINCT aggregate queries round-trip correctly."""

    @pytest.mark.parametrize("query", DISTINCT_AGGREGATE_QUERIES)
    def test_distinct_aggregate_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestParameterRoundTrip:
    """Test parameter reference queries round-trip correctly."""

    @pytest.mark.parametrize("query", PARAMETER_QUERIES)
    def test_parameter_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestCombinedClauseRoundTrip:
    """Test combined clause queries round-trip correctly."""

    @pytest.mark.parametrize("query", COMBINED_CLAUSE_QUERIES)
    def test_combined_clause_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestSimpleCaseRoundTrip:
    """Test simple CASE expression queries round-trip correctly."""

    @pytest.mark.parametrize("query", SIMPLE_CASE_QUERIES)
    def test_simple_case_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestAggregateAliasRoundTrip:
    """Test aggregate with alias queries round-trip correctly."""

    @pytest.mark.parametrize("query", AGGREGATE_ALIAS_QUERIES)
    def test_aggregate_alias_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestLabelPatternRoundTrip:
    """Test label pattern queries round-trip correctly."""

    @pytest.mark.parametrize("query", LABEL_PATTERN_QUERIES)
    def test_label_pattern_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


# --- Plan 016: Maximize round-trip coverage ---

# Phase 1: Easy-win queries covering previously-untested types
EASY_WIN_QUERIES = [
    # DatetimeSubtraction + DatetimeSubtractionParameters
    "MATCH (n) RETURN DURATION_BETWEEN(n.d1, n.d2)",
    # FullEdgeLeftOrRight: <-[]->
    "MATCH (a)<-[r]->(b) RETURN a",
    # FullEdgeLeftOrUndirected: <~[]~
    "MATCH (a)<~[r]~(b) RETURN a",
    # SubstringFunction (LEFT mode)
    "RETURN LEFT('hello', 3)",
    # SubstringFunction (RIGHT mode)
    "RETURN RIGHT('hello', 3)",
    # SessionSetGraphClause (direct graph ref, not parameter)
    "SESSION SET GRAPH myGraph",
]

# Phase 2: Queries unlocked by generator bug fixes
BUG_FIX_QUERIES = [
    # FocusedLinearQueryStatement, FocusedPrimitiveResultStatement, UseGraphClause
    "USE myGraph RETURN 1",
    # HomeGraph
    "USE HOME_GRAPH RETURN 1",
    # YieldItemAlias
    "CALL my.proc(1) YIELD col AS alias RETURN alias",
    # AtSchemaClause + PredefinedSchemaReference + RelativeCatalogSchemaReference
    "AT HOME_SCHEMA MATCH (n) RETURN n",
    # FocusedLinearQueryStatementPart + FocusedLinearQueryAndPrimitiveResultStatementPart
    "USE myGraph MATCH (n) USE myGraph2 MATCH (m) RETURN n, m",
]


class TestEasyWinRoundTrip:
    """Test easy-win queries for previously-uncovered types."""

    @pytest.mark.parametrize("query", EASY_WIN_QUERIES)
    def test_easy_win_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


class TestBugFixRoundTrip:
    """Test queries unlocked by generator bug fixes (Plan 016)."""

    @pytest.mark.parametrize("query", BUG_FIX_QUERIES)
    def test_bug_fix_queries(self, query):
        generated, success, error = round_trip(query)
        assert success, f"Query: {query}\nGenerated: {generated}\nError: {error}"


# Phase 4: xfail tests documenting types blocked by recursion or parse errors


def round_trip_strict(query: str) -> tuple[str, bool, str]:
    """Like round_trip() but lets RecursionError and ParseError propagate."""
    lexer = Lexer()
    parser = Parser()

    tokens1 = lexer.tokenize(query)
    ast1 = parser.parse(tokens1, query)[0]
    generated = ast1.to_gql()
    tokens2 = lexer.tokenize(generated)
    ast2 = parser.parse(tokens2, generated)[0]

    if ast1 == ast2:
        return generated, True, ""
    else:
        return generated, False, f"AST mismatch:\nOriginal AST: {ast1}\nGenerated AST: {ast2}"


class TestRecursionBlockedRoundTrip:
    """Round-trip tests for types previously or currently blocked by recursion."""

    def test_for_statement(self):
        """ForStatement, ForItem, ForItemAlias."""
        _, success, error = round_trip_strict("FOR x IN [1, 2, 3] RETURN x")
        assert success, error

    def test_for_ordinality(self):
        """ForOrdinalityOrOffset."""
        _, success, error = round_trip_strict("FOR x IN [1, 2, 3] WITH ORDINALITY o RETURN x, o")
        assert success, error

    def test_byte_length(self):
        """ByteLengthExpression."""
        _, success, error = round_trip_strict("MATCH (n) RETURN BYTE_LENGTH(n.name)")
        assert success, error

    def test_byte_string_literal(self):
        """ByteStringLiteral."""
        _, success, error = round_trip_strict("RETURN X'DEADBEEF'")
        assert success, error

    def test_datetime_type(self):
        """DatetimeType."""
        _, success, error = round_trip_strict(
            "MATCH (n) WHERE n.x IS TYPED ZONED DATETIME RETURN n"
        )
        assert success, error

    def test_time_type(self):
        """TimeType."""
        _, success, error = round_trip_strict("MATCH (n) WHERE n.x IS TYPED ZONED TIME RETURN n")
        assert success, error

    def test_duration_type(self):
        """TemporalDurationType."""
        _, success, error = round_trip_strict(
            "MATCH (n) WHERE n.x IS TYPED DURATION(DAY TO SECOND) RETURN n"
        )
        assert success, error

    def test_focused_query_with_match(self):
        """FocusedLinearQueryAndPrimitiveResultStatementPart (single USE + MATCH)."""
        _, success, error = round_trip_strict("USE myGraph MATCH (n) RETURN n")
        assert success, error


class TestParseBlockedRoundTrip:
    """Round-trip tests for types blocked by parse errors."""

    def test_select_statement(self):
        """SelectStatement."""
        _, success, error = round_trip_strict("SELECT 1")
        assert success, error

    def test_full_edge_undirected_or_right(self):
        """FullEdgeUndirectedOrRight."""
        _, success, error = round_trip_strict("MATCH (a)~[r]~>(b) RETURN a")
        assert success, error


# Phase 5: Documentation of parent types and dead types
#
# The following 52 registered generator types are "parent/dispatch" types that
# simply call gen.dispatch(expr) to re-dispatch to a more specific subtype.
# They are never directly instantiated by the parser, so they cannot appear
# in round-trip tests. Their generators exist to support MRO-based dispatch.
#
# Parent/dispatch types (52):
#   BinaryExactNumericType, CaseExpression, CaseSpecification,
#   CommonValueExpression, ConstructedValueType, DynamicUnionType,
#   EdgePattern, EdgeReferenceValueType, ElementPattern,
#   ElementPatternPredicate, ExactNumericType, FullEdgePattern,
#   GraphExpression, GraphPatternQuantifier, InsertEdgePattern,
#   LabelFactor, LabelPrimary, LinearDataModifyingStatement,
#   LinearQueryStatement, MatchMode, MatchStatement,
#   NodeReferenceValueType, NonNegativeIntegerSpecification,
#   NumericType, PathFactor, PathPatternExpression, PathPrimary,
#   PathSearchPrefix, PredefinedType, PrimitiveDataModifyingStatement,
#   PrimitiveQueryStatement, ProcedureCall, ProcedureSpecification,
#   ProgramActivity, ReferenceValueType, RemoveItem,
#   SessionSetParameterClause, SetItem, ShortestPathSearch,
#   SimpleCatalogModifyingStatement, SimpleDataAccessingStatement,
#   SimpleDataModifyingStatement, SimpleQueryStatement, Statement,
#   TemporalInstantType, TemporalType, ValueExpression, ValueType
#   + 4 Union TypeAlias dispatch types (Predicate, VEP variants)
#
# The following types have registered generators but are never produced by
# the parser in any known query context (dead generator code):
#   AmbientLinearDataModifyingStatement - parser produces Body directly
#   BindingVariableDefinition - parser produces specific subtypes
#   BindingVariableDefinitionBlock - parser produces specific subtypes
#   BindingTableVariableDefinition - requires binding variable definitions
#   GraphVariableDefinition - requires binding variable definitions
#   ValueVariableDefinition - requires binding variable definitions
#   ProcedureReference - parser produces CatalogProcedureParentAndName
#   SignedNumericLiteral - parser uses UnsignedNumericLiteral + unary minus
#   SubstitutedParameterReference - requires GE08 feature flag ($$param)
#   ClosedNodeReferenceValueType - parser produces OpenNodeReferenceValueType
#   ClosedEdgeReferenceValueType - parser produces OpenEdgeReferenceValueType
#   GraphSource - AS COPY OF syntax not parseable
#   PathPatternPrefix - parser produces PathMode/PathSearchPrefix separately
#   PathElementList - PATH[] constructor produces parse errors
#   PathValueConstructorByEnumeration - requires GE06 feature flag
#   TemporalDurationQualifier - DURATION_BETWEEN qualifier not parseable
#   RelativeDirectoryPath - parser uses AbsoluteDirectoryPath for schema refs


class TestGeneratorDirect:
    """Test the generator directly without round-trip."""

    def test_simple_match(self):
        """Test that a simple MATCH generates correct GQL."""
        from graphglot.lexer import Lexer
        from graphglot.parser import Parser

        lexer = Lexer()
        parser = Parser()

        query = "MATCH (n) RETURN n"
        tokens = lexer.tokenize(query)
        ast = parser.parse(tokens, query)[0]

        generated = ast.to_gql()
        assert "MATCH" in generated
        assert "RETURN" in generated

    def test_match_with_label(self):
        """Test that MATCH with label generates correct GQL."""
        from graphglot.lexer import Lexer
        from graphglot.parser import Parser

        lexer = Lexer()
        parser = Parser()

        query = "MATCH (n:Person) RETURN n"
        tokens = lexer.tokenize(query)
        ast = parser.parse(tokens, query)[0]

        generated = ast.to_gql()
        assert "MATCH" in generated
        assert "Person" in generated
        assert "RETURN" in generated
