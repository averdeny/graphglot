"""Categorized GQL query test cases for Neo4j execution tests.

Each QueryTestCase specifies a GQL query, expected row count or value,
and metadata for test parametrization.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import Any

# Sentinel to distinguish "no expected value set" from "expected value is None"
_UNSET = object()


@dataclass(frozen=True)
class QueryTestCase:
    id: str
    gql: str
    expected_rows: int | None = None  # None = just check no error
    expected_value: Any = field(default=_UNSET)  # _UNSET = don't check value
    category: str = "basic"
    mutation: bool = False  # Run in rolled-back transaction
    xfail: str | None = None  # Known bug/limitation in our code
    unsupported: str | None = None  # Feature Neo4j doesn't support — assert FeatureError


# ---------------------------------------------------------------------------
# Basic matching
# ---------------------------------------------------------------------------
BASIC_MATCH_CASES = [
    QueryTestCase("match_all_nodes", "MATCH (n) RETURN n", expected_rows=6),
    QueryTestCase("match_person", "MATCH (n:Person) RETURN n", expected_rows=5),
    QueryTestCase(
        "match_multi_label",
        "MATCH (n:Person&Employee) RETURN n",
        expected_rows=1,
    ),
    QueryTestCase(
        "match_label_union",
        "MATCH (n:Person|Company) RETURN n",
        expected_rows=6,
    ),
    QueryTestCase(
        "match_label_negation",
        "MATCH (n:!Company) RETURN n",
        expected_rows=5,
    ),
    QueryTestCase("match_wildcard", "MATCH (n:%) RETURN n", expected_rows=6),
    QueryTestCase(
        "match_directed_edges",
        "MATCH ()-[r]->() RETURN r",
        expected_rows=7,
    ),
    QueryTestCase(
        "match_typed_knows",
        "MATCH ()-[r:KNOWS]->() RETURN r",
        expected_rows=4,
    ),
    QueryTestCase(
        "match_reverse_knows",
        "MATCH ()<-[r:KNOWS]-() RETURN r",
        expected_rows=4,
    ),
    QueryTestCase(
        "match_multi_type",
        "MATCH ()-[r:KNOWS|LIKES]->() RETURN r",
        expected_rows=5,
    ),
    QueryTestCase(
        "match_untyped_edges",
        "MATCH ()-[r]-() RETURN r",
        expected_rows=14,
        category="basic",
    ),
]

# ---------------------------------------------------------------------------
# Properties & WHERE
# ---------------------------------------------------------------------------
PROPERTY_WHERE_CASES = [
    QueryTestCase(
        "where_age_gt",
        "MATCH (n:Person) WHERE n.age > 21 RETURN n",
        expected_rows=4,
        category="where",
    ),
    QueryTestCase(
        "where_name_eq",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n",
        expected_rows=1,
        category="where",
    ),
    QueryTestCase(
        "where_active_true",
        "MATCH (n:Person) WHERE n.active = TRUE RETURN n",
        expected_rows=4,
        category="where",
    ),
    QueryTestCase(
        "where_is_null",
        "MATCH (n:Person) WHERE n.email IS NULL RETURN n",
        expected_rows=1,
        category="where",
    ),
    QueryTestCase(
        "where_is_not_null",
        "MATCH (n:Person) WHERE n.email IS NOT NULL RETURN n",
        expected_rows=4,
        category="where",
    ),
    QueryTestCase(
        "where_range_and",
        "MATCH (n:Person) WHERE n.age >= 25 AND n.age <= 45 RETURN n",
        expected_rows=4,
        category="where",
    ),
    QueryTestCase(
        "where_not_equals",
        "MATCH (n:Person) WHERE n.name <> 'Alice' RETURN n",
        expected_rows=4,
        category="where",
    ),
    QueryTestCase(
        "where_edge_property",
        "MATCH (a)-[r:KNOWS]->(b) WHERE r.weight > 0.5 RETURN r",
        expected_rows=2,
        category="where",
    ),
]

# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------
EXPRESSION_CASES = [
    QueryTestCase(
        "expr_add",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n.age + 1 AS result",
        expected_value=31,
        category="expression",
    ),
    QueryTestCase(
        "expr_sub",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n.age - 1 AS result",
        expected_value=29,
        category="expression",
    ),
    QueryTestCase(
        "expr_mul",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n.age * 2 AS result",
        expected_value=60,
        category="expression",
    ),
    QueryTestCase(
        "expr_negate",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN -n.age AS result",
        expected_value=-30,
        category="expression",
    ),
    QueryTestCase(
        "expr_precedence",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n.age + n.score * 2 AS result",
        expected_value=201.0,
        category="expression",
    ),
    QueryTestCase(
        "expr_concat",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n.name || ' Smith' AS result",
        expected_value="Alice Smith",
        category="expression",
    ),
]

# ---------------------------------------------------------------------------
# RETURN, ORDER BY, pagination
# ---------------------------------------------------------------------------
RETURN_ORDER_CASES = [
    QueryTestCase(
        "return_alias",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN n.name AS person_name",
        expected_value="Alice",
        category="return",
    ),
    QueryTestCase(
        "return_distinct",
        "MATCH (n:Person) RETURN DISTINCT n.active AS a ORDER BY n.active",
        expected_rows=2,
        category="return",
    ),
    QueryTestCase(
        "order_by_name_asc",
        "MATCH (n:Person) RETURN n.name AS name ORDER BY n.name ASC",
        expected_rows=5,
        category="return",
    ),
    QueryTestCase(
        "order_by_age_desc",
        "MATCH (n:Person) RETURN n.name AS name ORDER BY n.age DESC",
        expected_rows=5,
        category="return",
    ),
    QueryTestCase(
        "limit_3",
        "MATCH (n:Person) RETURN n ORDER BY n.name LIMIT 3",
        expected_rows=3,
        category="return",
    ),
    QueryTestCase(
        "offset_limit",
        "MATCH (n:Person) RETURN n.name AS name ORDER BY n.name OFFSET 2 LIMIT 2",
        expected_rows=2,
        category="return",
    ),
    QueryTestCase(
        "return_star",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN *",
        expected_rows=1,
        category="return",
    ),
    QueryTestCase(
        "multi_col_sort",
        "MATCH (n:Person) RETURN n.active AS a, n.name AS name ORDER BY n.active, n.name",
        expected_rows=5,
        category="return",
    ),
]

# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------
AGGREGATE_CASES = [
    QueryTestCase(
        "agg_count",
        "MATCH (n:Person) RETURN COUNT(*) AS cnt",
        expected_value=5,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_sum",
        "MATCH (n:Person) RETURN SUM(n.age) AS total",
        expected_value=154,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_avg",
        "MATCH (n:Person) RETURN AVG(n.score) AS avg_score",
        expected_value=72.74,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_min",
        "MATCH (n:Person) RETURN MIN(n.age) AS youngest",
        expected_value=19,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_max",
        "MATCH (n:Person) RETURN MAX(n.age) AS oldest",
        expected_value=45,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_count_distinct",
        "MATCH (n:Person) RETURN COUNT(DISTINCT n.active) AS cnt",
        expected_value=2,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_collect_list",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN COLLECT(n.name) AS names",
        expected_rows=1,
        category="aggregate",
    ),
    QueryTestCase(
        "agg_group_by",
        "MATCH (n:Person) RETURN n.active AS active, COUNT(*) AS cnt "
        "GROUP BY active ORDER BY n.active",
        expected_rows=2,
        category="aggregate",
        unsupported="GQ15 (GROUP BY clause) not supported by Neo4j",
    ),
]

# ---------------------------------------------------------------------------
# CASE expressions
# ---------------------------------------------------------------------------
CASE_CASES = [
    QueryTestCase(
        "case_searched",
        "MATCH (n:Person) WHERE n.name = 'Alice' "
        "RETURN CASE WHEN n.age >= 18 THEN 'adult' ELSE 'minor' END AS category",
        expected_value="adult",
        category="case",
    ),
    QueryTestCase(
        "case_multi_when",
        "MATCH (n:Person) WHERE n.name = 'Dave' "
        "RETURN CASE WHEN n.age < 13 THEN 'child' "
        "WHEN n.age < 20 THEN 'teen' ELSE 'adult' END AS category",
        expected_value="teen",
        category="case",
    ),
    QueryTestCase(
        "nullif",
        "RETURN NULLIF(1, 1) AS result",
        expected_value=None,
        category="case",
    ),
    QueryTestCase(
        "coalesce",
        "RETURN COALESCE(NULL, 1, 2) AS result",
        expected_value=1,
        category="case",
    ),
]

# ---------------------------------------------------------------------------
# Boolean
# ---------------------------------------------------------------------------
BOOLEAN_CASES = [
    QueryTestCase(
        "bool_and",
        "MATCH (n:Person) WHERE n.active = TRUE AND n.age > 25 RETURN n",
        expected_rows=3,
        category="boolean",
    ),
    QueryTestCase(
        "bool_or",
        "MATCH (n:Person) WHERE n.age < 20 OR n.age > 40 RETURN n",
        expected_rows=2,
        category="boolean",
    ),
    QueryTestCase(
        "bool_not",
        "MATCH (n:Person) WHERE NOT n.active = TRUE RETURN n",
        expected_rows=1,
        category="boolean",
    ),
    QueryTestCase(
        "bool_complex",
        "MATCH (n:Person) WHERE NOT (n.active = TRUE AND n.age > 30) RETURN n",
        expected_rows=3,
        category="boolean",
    ),
]

# ---------------------------------------------------------------------------
# Paths & variables
# ---------------------------------------------------------------------------
PATH_CASES = [
    QueryTestCase(
        "path_variable",
        "MATCH p = (a:Person)-[:KNOWS]->(b:Person) RETURN p",
        expected_rows=4,
        category="path",
    ),
    QueryTestCase(
        "multi_hop_from_alice",
        "MATCH (a:Person {name: 'Alice'})-[:KNOWS]->(b)-[:KNOWS]->(c) RETURN c.name AS name",
        expected_rows=2,
        category="path",
    ),
    QueryTestCase(
        "quantified_edge_2",
        "MATCH (a:Person {name: 'Alice'})-[:KNOWS]->{2}(b) RETURN b.name AS name",
        expected_rows=2,
        category="path",
    ),
    QueryTestCase(
        "quantified_edge_plus",
        "MATCH (a:Person {name: 'Alice'})-[:KNOWS]->{1,}(b) RETURN DISTINCT b.name AS name",
        expected_rows=3,
        category="path",
    ),
    QueryTestCase(
        "quantified_edge_star",
        "MATCH (a:Person {name: 'Alice'})-[:KNOWS]->{0,}(b) RETURN DISTINCT b.name AS name",
        expected_rows=4,
        category="path",
    ),
]

# ---------------------------------------------------------------------------
# OPTIONAL MATCH
# ---------------------------------------------------------------------------
OPTIONAL_MATCH_CASES = [
    QueryTestCase(
        "optional_match_exists",
        "MATCH (a:Person) OPTIONAL MATCH (a)-[:KNOWS]->(b) RETURN a.name AS name, b.name AS friend",
        expected_rows=6,
        category="optional_match",
    ),
    QueryTestCase(
        "optional_match_no_match",
        "MATCH (a:Person {name: 'Eve'}) OPTIONAL MATCH (a)-[:KNOWS]->(b) "
        "RETURN a.name AS name, b.name AS friend",
        expected_rows=1,
        category="optional_match",
    ),
    QueryTestCase(
        "optional_match_with_where",
        "MATCH (a:Person) OPTIONAL MATCH (a)-[r:KNOWS]->(b) WHERE r.weight > 0.5 "
        "RETURN a.name AS name, b.name AS friend ORDER BY a.name",
        expected_rows=5,
        category="optional_match",
    ),
]

# ---------------------------------------------------------------------------
# Quantified patterns
# ---------------------------------------------------------------------------
QUANTIFIED_PATTERN_CASES = [
    QueryTestCase(
        "qp_edge_range",
        "MATCH (a:Person {name: 'Alice'})-[:KNOWS]->{1,3}(b) RETURN DISTINCT b.name AS name",
        expected_rows=3,
        category="quantified_pattern",
    ),
    QueryTestCase(
        "qp_questioned",
        "MATCH (a:Person {name: 'Alice'})-[:KNOWS]->?{1,2}(b) RETURN DISTINCT b.name AS name",
        expected_rows=3,
        category="quantified_pattern",
        unsupported="G037 (questioned paths) not supported by Neo4j",
    ),
]

# ---------------------------------------------------------------------------
# Parenthesized patterns
# ---------------------------------------------------------------------------
PAREN_PATTERN_CASES = [
    QueryTestCase(
        "paren_pattern_where",
        "MATCH (a:Person)-[r:KNOWS WHERE r.weight > 0.5]->(b) RETURN a.name AS a, b.name AS b",
        expected_rows=2,
        category="paren_pattern",
    ),
]

# ---------------------------------------------------------------------------
# Numeric functions
# ---------------------------------------------------------------------------
NUMERIC_FUNC_CASES = [
    QueryTestCase(
        "func_abs",
        "RETURN ABS(-5) AS result",
        expected_value=5,
        category="numeric_func",
    ),
    QueryTestCase(
        "func_floor",
        "RETURN FLOOR(3.7) AS result",
        expected_value=3,
        category="numeric_func",
    ),
    QueryTestCase(
        "func_ceil",
        "RETURN CEIL(3.2) AS result",
        expected_value=4,
        category="numeric_func",
    ),
    QueryTestCase(
        "func_sqrt",
        "RETURN SQRT(9) AS result",
        expected_value=3.0,
        category="numeric_func",
    ),
    QueryTestCase(
        "func_round",
        "RETURN ROUND(3.7) AS result",
        expected_value=4,
        category="numeric_func",
    ),
]

# ---------------------------------------------------------------------------
# Trig functions
# ---------------------------------------------------------------------------
TRIG_FUNC_CASES = [
    QueryTestCase(
        "func_sin",
        "RETURN SIN(1 - 1) AS result",
        expected_value=0.0,
        category="trig_func",
    ),
    QueryTestCase(
        "func_cos",
        "RETURN COS(1 - 1) AS result",
        expected_value=1.0,
        category="trig_func",
    ),
    QueryTestCase(
        "func_degrees",
        "RETURN DEGREES(3.141592653589793) AS result",
        expected_value=180.0,
        category="trig_func",
    ),
    QueryTestCase(
        "func_radians",
        "RETURN RADIANS(180) AS result",
        expected_value=math.pi,
        category="trig_func",
    ),
]

# ---------------------------------------------------------------------------
# Log functions
# ---------------------------------------------------------------------------
LOG_FUNC_CASES = [
    QueryTestCase(
        "func_log10",
        "RETURN LOG10(100) AS result",
        expected_value=2.0,
        category="log_func",
    ),
    QueryTestCase(
        "func_exp_0",
        "RETURN EXP(1 - 1) AS result",
        expected_value=1.0,
        category="log_func",
    ),
    QueryTestCase(
        "func_exp_1",
        "RETURN EXP(1) AS result",
        expected_value=math.e,
        category="log_func",
    ),
]

# ---------------------------------------------------------------------------
# String functions
# ---------------------------------------------------------------------------
STRING_FUNC_CASES = [
    QueryTestCase(
        "func_upper",
        "RETURN UPPER('hello') AS result",
        expected_value="HELLO",
        category="string_func",
    ),
    QueryTestCase(
        "func_lower",
        "RETURN LOWER('HELLO') AS result",
        expected_value="hello",
        category="string_func",
    ),
    QueryTestCase(
        "func_char_length",
        "RETURN CHAR_LENGTH('hello') AS result",
        expected_value=5,
        category="string_func",
    ),
    QueryTestCase(
        "func_ltrim",
        "RETURN LTRIM('  hi') AS result",
        expected_value="hi",
        category="string_func",
    ),
    QueryTestCase(
        "func_rtrim",
        "RETURN RTRIM('hi  ') AS result",
        expected_value="hi",
        category="string_func",
    ),
    QueryTestCase(
        "func_substring",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN SUBSTRING(n.name, 0, 3) AS result",
        expected_value="Ali",
        category="string_func",
    ),
]

# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------
LITERAL_CASES = [
    QueryTestCase("lit_int", "RETURN 42 AS result", expected_value=42, category="literal"),
    QueryTestCase("lit_float", "RETURN 3.14 AS result", expected_value=3.14, category="literal"),
    QueryTestCase(
        "lit_string", "RETURN 'hello' AS result", expected_value="hello", category="literal"
    ),
    QueryTestCase("lit_true", "RETURN TRUE AS result", expected_value=True, category="literal"),
    QueryTestCase("lit_false", "RETURN FALSE AS result", expected_value=False, category="literal"),
    QueryTestCase("lit_null", "RETURN NULL AS result", expected_value=None, category="literal"),
    QueryTestCase("lit_list", "RETURN [1, 2, 3] AS result", expected_rows=1, category="literal"),
    QueryTestCase("lit_negative", "RETURN -1 AS result", expected_value=-1, category="literal"),
    QueryTestCase(
        "lit_date",
        "RETURN DATE '2024-01-15' AS result",
        expected_rows=1,
        category="literal",
        unsupported="GG:TL01 (temporal literals) not supported by Neo4j",
    ),
]

# ---------------------------------------------------------------------------
# Temporal
# ---------------------------------------------------------------------------
TEMPORAL_CASES = [
    QueryTestCase(
        "temporal_current_date",
        "RETURN CURRENT_DATE AS result",
        expected_rows=1,
        category="temporal",
        unsupported="GG:TF01 (parameterless temporal functions) not supported by Neo4j",
    ),
    QueryTestCase(
        "temporal_current_timestamp",
        "RETURN CURRENT_TIMESTAMP AS result",
        expected_rows=1,
        category="temporal",
        unsupported="GG:TF01 (parameterless temporal functions) not supported by Neo4j",
    ),
    # --- Cypher temporal constructors (string arg) ---
    QueryTestCase(
        "temporal_date_string",
        "RETURN date('2024-01-15') AS d",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_time_string",
        "RETURN time('10:30:00') AS t",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_datetime_string",
        "RETURN datetime('2024-01-15T10:30:00') AS dt",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_localdatetime_string",
        "RETURN localdatetime('2024-01-15T10:30:00') AS ldt",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_localtime_string",
        "RETURN localtime('10:30:00') AS lt",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_duration_string",
        "RETURN duration('P1Y2M3D') AS dur",
        expected_rows=1,
        category="temporal",
    ),
    # --- Cypher temporal no-arg constructors ---
    QueryTestCase(
        "temporal_date_no_arg",
        "RETURN date() AS d",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_datetime_no_arg",
        "RETURN datetime() AS dt",
        expected_rows=1,
        category="temporal",
    ),
    # --- Cypher temporal static methods ---
    QueryTestCase(
        "temporal_date_truncate",
        "RETURN date.truncate('year', date('2024-06-15')) AS d",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_duration_between",
        "RETURN duration.between(date('2024-01-01'), date('2024-06-15')) AS d",
        expected_rows=1,
        category="temporal",
    ),
    QueryTestCase(
        "temporal_datetime_realtime",
        "RETURN datetime.realtime() AS dt",
        expected_rows=1,
        category="temporal",
    ),
]

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
PARAMETER_CASES = [
    QueryTestCase(
        "param_string",
        "MATCH (n:Person) WHERE n.name = $param RETURN n",
        expected_rows=1,
        category="parameter",
    ),
    QueryTestCase(
        "param_int",
        "MATCH (n:Person) WHERE n.age = $age RETURN n",
        expected_rows=1,
        category="parameter",
    ),
    QueryTestCase(
        "param_multi",
        "MATCH (n:Person) WHERE n.name = $param AND n.age = $age RETURN n",
        expected_rows=1,
        category="parameter",
    ),
]

# Parameter values used during execution
PARAM_VALUES = {
    "param": "Alice",
    "age": 30,
}

# ---------------------------------------------------------------------------
# UNION
# ---------------------------------------------------------------------------
UNION_CASES = [
    QueryTestCase(
        "union_all",
        "MATCH (n:Person) RETURN n.name AS name UNION ALL MATCH (n:Company) RETURN n.name AS name",
        expected_rows=6,
        category="union",
    ),
    QueryTestCase(
        "union_deduplicated",
        "MATCH (n:Person) WHERE n.active = TRUE RETURN n.active AS val "
        "UNION "
        "MATCH (n:Person) WHERE n.active = TRUE RETURN n.active AS val",
        expected_rows=1,
        category="union",
    ),
]

# ---------------------------------------------------------------------------
# Subqueries
# ---------------------------------------------------------------------------
SUBQUERY_CASES = [
    QueryTestCase(
        "subquery_call",
        "MATCH (n:Person) CALL { RETURN 1 AS x } RETURN n.name AS name, x",
        expected_rows=5,
        category="subquery",
    ),
    QueryTestCase(
        "subquery_exists",
        "MATCH (n:Person) WHERE EXISTS { MATCH (n)-[:KNOWS]->() } RETURN n.name AS name",
        expected_rows=3,
        category="subquery",
    ),
]

# ---------------------------------------------------------------------------
# Mutations (rolled back)
# ---------------------------------------------------------------------------
MUTATION_CASES = [
    QueryTestCase(
        "mut_insert_node",
        "INSERT (:Person {name: 'Zara', age: 28})",
        expected_rows=0,
        category="mutation",
        mutation=True,
    ),
    QueryTestCase(
        "mut_insert_edge",
        "MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Eve'}) "
        "INSERT (a)-[:KNOWS {since: 2024}]->(b)",
        expected_rows=0,
        category="mutation",
        mutation=True,
    ),
    QueryTestCase(
        "mut_set_property",
        "MATCH (n:Person {name: 'Dave'}) RETURN n "
        "NEXT SET n.active = TRUE RETURN n.active AS active",
        expected_value=True,
        category="mutation",
        mutation=True,
    ),
    QueryTestCase(
        "mut_set_label",
        "MATCH (n:Person {name: 'Bob'}) RETURN n NEXT SET n:Employee RETURN n.name AS name",
        expected_value="Bob",
        category="mutation",
        mutation=True,
    ),
    QueryTestCase(
        "mut_remove_label",
        "MATCH (n:Person&Employee {name: 'Alice'}) REMOVE n:Employee RETURN LABELS(n) AS labels",
        expected_rows=1,
        category="mutation",
        mutation=True,
    ),
    QueryTestCase(
        "mut_delete",
        "MATCH (n:Person {name: 'Dave'}) RETURN n NEXT DETACH DELETE n",
        expected_rows=0,
        category="mutation",
        mutation=True,
    ),
]

# ---------------------------------------------------------------------------
# CAST
# ---------------------------------------------------------------------------
CAST_CASES = [
    QueryTestCase(
        "cast_to_string",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN CAST(n.age AS STRING) AS result",
        expected_value="30",
        category="cast",
    ),
    QueryTestCase(
        "cast_to_integer",
        "RETURN CAST('42' AS INTEGER) AS result",
        expected_value=42,
        category="cast",
    ),
    QueryTestCase(
        "cast_to_boolean",
        "RETURN CAST('true' AS BOOLEAN) AS result",
        expected_value=True,
        category="cast",
    ),
]

# ---------------------------------------------------------------------------
# ELEMENT_ID
# ---------------------------------------------------------------------------
ELEMENT_ID_CASES = [
    QueryTestCase(
        "element_id",
        "MATCH (n:Person) WHERE n.name = 'Alice' RETURN ELEMENTID(n) AS eid",
        expected_rows=1,
        category="element_id",
    ),
]

# ---------------------------------------------------------------------------
# Path search
# ---------------------------------------------------------------------------
PATH_SEARCH_CASES = [
    QueryTestCase(
        "any_shortest",
        "MATCH ANY SHORTEST (a:Person {name: 'Alice'})-[:KNOWS]->{1,5}(b:Person {name: 'Dave'}) "
        "RETURN b.name AS name",
        expected_rows=1,
        category="path_search",
    ),
    QueryTestCase(
        "all_shortest",
        "MATCH ALL SHORTEST (a:Person {name: 'Alice'})-[:KNOWS]->{1,5}(b:Person {name: 'Carol'}) "
        "RETURN b.name AS name",
        expected_rows=1,
        category="path_search",
    ),
]

# ---------------------------------------------------------------------------
# Cypher extension: Phase 1 (string match, IN, UNWIND, WITH)
# ---------------------------------------------------------------------------
CYPHER_STRING_MATCH_CASES = [
    QueryTestCase(
        "cy_starts_with",
        "MATCH (n:Person) WHERE n.name STARTS WITH 'Al' RETURN n.name AS name",
        expected_value="Alice",
        category="cypher",
    ),
    QueryTestCase(
        "cy_ends_with",
        "MATCH (n:Person) WHERE n.name ENDS WITH 'e' RETURN n",
        expected_rows=3,  # Alice, Dave, Eve
        category="cypher",
    ),
    QueryTestCase(
        "cy_contains",
        "MATCH (n:Person) WHERE n.name CONTAINS 'o' RETURN n",
        expected_rows=2,  # Bob, Carol
        category="cypher",
    ),
    QueryTestCase(
        "cy_starts_and_ends",
        "MATCH (n:Person) WHERE n.name STARTS WITH 'A' AND n.name ENDS WITH 'e' RETURN n",
        expected_rows=1,  # Alice
        category="cypher",
    ),
]

CYPHER_IN_CASES = [
    QueryTestCase(
        "cy_in_list",
        "MATCH (n:Person) WHERE n.age IN [25, 30] RETURN n",
        expected_rows=2,  # Alice(30), Bob(25)
        category="cypher",
    ),
    QueryTestCase(
        "cy_in_single",
        "MATCH (n:Person) WHERE n.name IN ['Eve'] RETURN n.name AS name",
        expected_value="Eve",
        category="cypher",
    ),
]

CYPHER_UNWIND_CASES = [
    QueryTestCase(
        "cy_unwind_list",
        "UNWIND [1, 2, 3] AS x RETURN x",
        expected_rows=3,
        category="cypher",
    ),
    QueryTestCase(
        "cy_unwind_single",
        "UNWIND [42] AS x RETURN x AS result",
        expected_value=42,
        category="cypher",
    ),
]

CYPHER_WITH_CASES = [
    QueryTestCase(
        "cy_with_basic",
        "MATCH (n:Person) WITH n.name AS name ORDER BY name LIMIT 3 RETURN name",
        expected_rows=3,
        category="cypher",
    ),
    QueryTestCase(
        "cy_with_where",
        "MATCH (n:Person) WITH n.name AS name WHERE name STARTS WITH 'A' RETURN name",
        expected_value="Alice",
        category="cypher",
    ),
    QueryTestCase(
        "cy_with_distinct",
        "MATCH (n:Person) WITH DISTINCT n.active AS active RETURN active",
        expected_rows=2,
        category="cypher",
    ),
    QueryTestCase(
        "cy_with_skip_limit",
        "MATCH (n:Person) WITH n ORDER BY n.name SKIP 1 LIMIT 2 RETURN n.name AS name",
        expected_rows=2,
        category="cypher",
    ),
]

# ---------------------------------------------------------------------------
# Cypher extension: Phase 2 (MERGE)
# ---------------------------------------------------------------------------
CYPHER_MERGE_CASES = [
    QueryTestCase(
        "cy_merge_existing_node",
        "MERGE (n:Person {name: 'Alice'}) RETURN n.name AS name",
        expected_value="Alice",
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_merge_create_node",
        "MERGE (n:Person {name: 'Zara'}) RETURN n.name AS name",
        expected_value="Zara",
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_merge_on_create",
        "MERGE (n:Person {name: 'Yolanda'}) ON CREATE SET n.age = 28 RETURN n.age AS age",
        expected_value=28,
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_merge_on_match",
        "MERGE (n:Person {name: 'Alice'}) ON MATCH SET n.score = 99.0 RETURN n.score AS score",
        expected_value=99.0,
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_merge_on_create_and_match",
        "MERGE (n:Person {name: 'Alice'}) "
        "ON CREATE SET n.tag = 'new' ON MATCH SET n.tag = 'existing' "
        "RETURN n.tag AS tag",
        expected_value="existing",
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_merge_relationship",
        "MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Eve'}) "
        "MERGE (a)-[r:FRIENDS]->(b) RETURN r",
        expected_rows=1,
        category="cypher",
        mutation=True,
    ),
]

# ---------------------------------------------------------------------------
# Cypher extension: Phase 3 (regex match, list comprehension, list predicates)
# ---------------------------------------------------------------------------
CYPHER_REGEX_CASES = [
    QueryTestCase(
        "cy_regex_match",
        "MATCH (n:Person) WHERE n.name =~ 'A.*' RETURN n.name AS name",
        expected_value="Alice",
        category="cypher",
    ),
    QueryTestCase(
        "cy_regex_case_insensitive",
        "MATCH (n:Person) WHERE n.name =~ '(?i)bob' RETURN n.name AS name",
        expected_value="Bob",
        category="cypher",
    ),
]

CYPHER_LIST_COMP_CASES = [
    QueryTestCase(
        "cy_list_comp_filter",
        "RETURN [x IN [1, 2, 3, 4, 5] WHERE x > 3] AS result",
        expected_value=[4, 5],
        category="cypher",
    ),
    QueryTestCase(
        "cy_list_comp_transform",
        "RETURN [x IN [1, 2, 3] | x * 10] AS result",
        expected_value=[10, 20, 30],
        category="cypher",
    ),
    QueryTestCase(
        "cy_list_comp_full",
        "RETURN [x IN [1, 2, 3, 4] WHERE x > 2 | x * 2] AS result",
        expected_value=[6, 8],
        category="cypher",
    ),
]

CYPHER_LIST_PRED_CASES = [
    QueryTestCase(
        "cy_all_predicate",
        "MATCH (n:Person) WHERE all(x IN [n.age] WHERE x > 1) RETURN n.name AS name",
        expected_rows=5,
        category="cypher",
    ),
    QueryTestCase(
        "cy_any_predicate",
        "MATCH (n:Person) WHERE any(x IN [25, 30] WHERE x = n.age) RETURN n.name AS name",
        expected_rows=2,  # Alice(30), Bob(25)
        category="cypher",
    ),
    QueryTestCase(
        "cy_none_predicate",
        "MATCH (n:Person) WHERE none(x IN [100, 200] WHERE x = n.age) RETURN n.name AS name",
        expected_rows=5,
        category="cypher",
    ),
]

# ---------------------------------------------------------------------------
# Cypher extension: CREATE clause
# ---------------------------------------------------------------------------
CYPHER_CREATE_CASES = [
    QueryTestCase(
        "cy_create_node",
        "CREATE (n:Temp {tag: 'test'}) RETURN n.tag AS tag",
        expected_value="test",
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_create_node_with_properties",
        "CREATE (n:Temp {name: 'Zoe', score: 42}) RETURN n.name AS name",
        expected_value="Zoe",
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_create_relationship",
        "MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'}) "
        "CREATE (a)-[r:TESTED]->(b) RETURN r",
        expected_rows=1,
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_create_relationship_type_func",
        "MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'}) "
        "CREATE (a)-[r:TESTED]->(b) RETURN type(r) AS t",
        expected_value="TESTED",
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_create_return_count",
        "CREATE (n:Temp) RETURN count(*) AS cnt",
        expected_value=1,
        category="cypher",
        mutation=True,
    ),
    QueryTestCase(
        "cy_match_create_return",
        "MATCH (a:Person {name: 'Alice'}) "
        "CREATE (a)-[r:LIKES]->(b:Temp {val: 1}) RETURN b.val AS v",
        expected_value=1,
        category="cypher",
        mutation=True,
    ),
]

# ---------------------------------------------------------------------------
# Feature validation: 22 optional features in _NEO4J_SUPPORTED_OPTIONAL
# that are absent from Neo4j's official GQL conformance docs.
# Each test validates a specific feature against a real Neo4j instance.
# GB03 (double solidus comments) omitted — comments stripped during lexing.
# ---------------------------------------------------------------------------
FEATURE_VALIDATION_CASES = [
    # G005 — Path search prefix (counted shortest)
    QueryTestCase(
        "fv_g005_shortest_k",
        "MATCH SHORTEST 2 (a {name: 'Alice'})-[:KNOWS]->{1,5}(b {name: 'Carol'}) "
        "RETURN b.name AS name",
        expected_rows=2,
        category="feature_validation",
    ),
    # G044 — Basic abbreviated edge patterns
    QueryTestCase(
        "fv_g044_abbrev_right",
        "MATCH (a:Person {name: 'Alice'})-->(:Person) RETURN a.name AS name",
        expected_rows=2,
        category="feature_validation",
    ),
    QueryTestCase(
        "fv_g044_abbrev_left",
        "MATCH (a:Person {name: 'Alice'})<--(:Person) RETURN a.name AS name",
        expected_rows=1,
        category="feature_validation",
    ),
    QueryTestCase(
        "fv_g044_abbrev_undirected",
        "MATCH (a:Person {name: 'Alice'})--(:Person) RETURN a.name AS name",
        expected_rows=3,
        category="feature_validation",
    ),
    # G045 — Complete abbreviated edge patterns (bidirectional <-->)
    QueryTestCase(
        "fv_g045_abbrev_any",
        "MATCH (a:Person {name: 'Bob'})<-->(b) RETURN b.name AS name",
        expected_rows=3,
        category="feature_validation",
    ),
    # G047 — Relaxed topological consistency: edges without adjacent node patterns.
    # Neo4j rejects this syntax (e.g. -->--> without nodes in between).
    # The original test used a normal chain (a)-[]->(b)-[]->(c) which was wrong.
    QueryTestCase(
        "fv_g047_chain",
        "MATCH (a {name: 'Alice'})-[:KNOWS]->-[:WORKS_AT]->(c:Company) RETURN a.name AS name",
        expected_rows=0,
        category="feature_validation",
        unsupported="G047 (relaxed topological consistency) not supported by Neo4j",
    ),
    # G111 — IS LABELED predicate (label check in WHERE)
    QueryTestCase(
        "fv_g111_label_predicate",
        "MATCH (n) WHERE n:Person RETURN n.name AS name",
        expected_rows=5,
        category="feature_validation",
    ),
    # GA05 — Cast specification (Cypher toFloat/toString → CAST AST)
    QueryTestCase(
        "fv_ga05_cast_to_float",
        "RETURN toFloat(42) AS result",
        expected_value=42.0,
        category="feature_validation",
    ),
    QueryTestCase(
        "fv_ga05_cast_to_string",
        "RETURN toString(123) AS result",
        expected_value="123",
        category="feature_validation",
    ),
    # GD02 — Graph label set changes (SET label)
    QueryTestCase(
        "fv_gd02_set_label",
        "MATCH (n:Person {name: 'Dave'}) SET n:Intern RETURN n.name AS name",
        expected_value="Dave",
        category="feature_validation",
        mutation=True,
    ),
    # GD04 — DELETE with simple expression (delete relationship)
    QueryTestCase(
        "fv_gd04_delete_rel",
        "MATCH (n {name: 'Dave'})-[r:LIKES]->() DELETE r RETURN n.name AS name",
        expected_value="Dave",
        category="feature_validation",
        mutation=True,
    ),
    # GE07 — Boolean XOR
    QueryTestCase(
        "fv_ge07_xor",
        "MATCH (n:Person) WHERE n.active = TRUE XOR n.age > 30 RETURN n.name AS name",
        expected_rows=2,
        category="feature_validation",
    ),
    # GF20 — Aggregate functions in sort keys
    QueryTestCase(
        "fv_gf20_agg_sort",
        "MATCH (n:Person)-[:KNOWS]->(m) "
        "RETURN n.name AS name, COUNT(m) AS cnt ORDER BY COUNT(m) DESC",
        expected_rows=3,
        category="feature_validation",
    ),
    # GL01 — Hexadecimal literals
    QueryTestCase(
        "fv_gl01_hex",
        "RETURN 0xFF AS result",
        expected_value=255,
        category="feature_validation",
    ),
    # GL02 — Octal literals
    QueryTestCase(
        "fv_gl02_octal",
        "RETURN 0o77 AS result",
        expected_value=63,
        category="feature_validation",
    ),
    # GL04 — Exact number in common notation (decimal float)
    QueryTestCase(
        "fv_gl04_decimal",
        "RETURN 3.14 AS result",
        expected_value=3.14,
        category="feature_validation",
    ),
    # GP02 — Inline procedure with implicit variable scope
    QueryTestCase(
        "fv_gp02_call_implicit",
        "MATCH (n:Person {name: 'Alice'}) CALL { RETURN 42 AS answer } "
        "RETURN n.name AS name, answer",
        expected_rows=1,
        category="feature_validation",
    ),
    # GQ12 — OFFSET clause (generator emits SKIP for Neo4j)
    QueryTestCase(
        "fv_gq12_offset",
        "MATCH (n:Person) RETURN n.name AS name ORDER BY n.name OFFSET 3",
        expected_rows=2,
        category="feature_validation",
    ),
    # GQ14 — Complex expressions in sort keys
    QueryTestCase(
        "fv_gq14_complex_sort",
        "MATCH (n:Person) RETURN n.name AS name ORDER BY n.age * -1",
        expected_rows=5,
        category="feature_validation",
    ),
    # GQ16 — Pre-projection aliases in sort keys
    QueryTestCase(
        "fv_gq16_alias_sort",
        "MATCH (n:Person) RETURN n.name AS person_name ORDER BY person_name",
        expected_rows=5,
        category="feature_validation",
    ),
    # GQ22 — EXISTS predicate with multiple MATCH clauses
    QueryTestCase(
        "fv_gq22_exists_multi",
        "MATCH (n:Person) WHERE EXISTS { MATCH (n)-[:KNOWS]->() "
        "MATCH (n)-[:WORKS_AT]->() } RETURN n.name AS name",
        expected_rows=2,
        category="feature_validation",
    ),
    # GV41 — Duration types
    QueryTestCase(
        "fv_gv41_duration",
        "RETURN duration('P1Y') AS d",
        expected_rows=1,
        category="feature_validation",
    ),
    # GV48 — Nested record types (nested map literals)
    QueryTestCase(
        "fv_gv48_nested_map",
        "RETURN {outer: {inner: 42}} AS result",
        expected_rows=1,
        category="feature_validation",
    ),
    QueryTestCase(
        "fv_gv48_map_access",
        "RETURN {a: {b: 'hello'}}.a.b AS result",
        expected_value="hello",
        category="feature_validation",
    ),
]

# ---------------------------------------------------------------------------
# Collect all cases
# ---------------------------------------------------------------------------
ALL_QUERY_CASES: list[QueryTestCase] = [
    *BASIC_MATCH_CASES,
    *PROPERTY_WHERE_CASES,
    *EXPRESSION_CASES,
    *RETURN_ORDER_CASES,
    *AGGREGATE_CASES,
    *CASE_CASES,
    *BOOLEAN_CASES,
    *PATH_CASES,
    *OPTIONAL_MATCH_CASES,
    *QUANTIFIED_PATTERN_CASES,
    *PAREN_PATTERN_CASES,
    *NUMERIC_FUNC_CASES,
    *TRIG_FUNC_CASES,
    *LOG_FUNC_CASES,
    *STRING_FUNC_CASES,
    *LITERAL_CASES,
    *TEMPORAL_CASES,
    *PARAMETER_CASES,
    *UNION_CASES,
    *SUBQUERY_CASES,
    *MUTATION_CASES,
    *CAST_CASES,
    *ELEMENT_ID_CASES,
    *PATH_SEARCH_CASES,
    *CYPHER_STRING_MATCH_CASES,
    *CYPHER_IN_CASES,
    *CYPHER_UNWIND_CASES,
    *CYPHER_WITH_CASES,
    *CYPHER_MERGE_CASES,
    *CYPHER_REGEX_CASES,
    *CYPHER_LIST_COMP_CASES,
    *CYPHER_LIST_PRED_CASES,
    *CYPHER_CREATE_CASES,
    *FEATURE_VALIDATION_CASES,
]

# ---------------------------------------------------------------------------
# Transformation: Cypher WITH → GQL RETURN...NEXT
# These cases are parsed as Cypher, transformed to GQL (StatementBlock/NEXT),
# then generated using the Neo4j dialect and executed.
# ---------------------------------------------------------------------------
TRANSFORM_WITH_CASES = [
    QueryTestCase(
        "tx_with_basic",
        "MATCH (n:Person) WITH n.name AS name RETURN name",
        expected_rows=5,
        category="transform",
    ),
    QueryTestCase(
        "tx_with_where",
        "MATCH (n:Person) WITH n WHERE n.age > 25 RETURN n.name AS name",
        expected_rows=3,
        category="transform",
    ),
    QueryTestCase(
        "tx_with_order_limit",
        "MATCH (n:Person) WITH n ORDER BY n.name LIMIT 2 RETURN n.name AS name",
        expected_rows=2,
        category="transform",
    ),
    QueryTestCase(
        "tx_with_distinct",
        "MATCH (n:Person) WITH DISTINCT n.active AS active RETURN active",
        expected_rows=2,
        category="transform",
    ),
    QueryTestCase(
        "tx_with_aggregation",
        "MATCH (n:Person) WITH count(n) AS c RETURN c",
        expected_value=5,
        category="transform",
    ),
    QueryTestCase(
        "tx_with_chained",
        "MATCH (n:Person) WITH n.age AS age WHERE age > 25 WITH count(age) AS c RETURN c",
        expected_value=3,
        category="transform",
    ),
]
